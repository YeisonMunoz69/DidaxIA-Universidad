from __future__ import annotations

import json
import re
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import asdict, dataclass
from dataclasses import replace as dataclasses_replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

from adaptadores.entrantes.http import aviso_legal
from adaptadores.entrantes.http.concurrencia import (
    CandadoPorConversacion,
    RegistroDeIdempotencia,
    clave_de,
)
from adaptadores.entrantes.http.contexto_conversacional import (
    contexto_de_sesion,
    reconstruir_contexto_factual,
    recordar_contexto_factual,
)
from adaptadores.entrantes.http.instrumentacion import (
    SIN_INSTRUMENTAR,
    Instrumentador,
    ResultadoDelTurno,
    SelloDelTurno,
)
from adaptadores.entrantes.http.limitador import LimitadorDePeticiones
from adaptadores.entrantes.http.progreso import EmisionDelTurno
from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, mantenimiento
from adaptadores.entrantes.http.rutas.historial import OPERACION_CONSULTA
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from adaptadores.entrantes.http.turno import AdaptadorTurno, TurnoEntrante
from dominio.arbitraje.divulgacion import Señales
from dominio.diagnostico.clasificador import RespuestaAlItem
from dominio.filtros.intencion import (
    destino_solicitado_para_limite,
    extraer_curva_solicitada,
    extraer_ejercicio_explicito,
)
from dominio.filtros.normalizacion import segmentar
from dominio.modelo.acceso import (
    AccesoCalculado,
    calcular_acceso,
    permite_tutor,
    permite_tutoria_academica,
)
from dominio.modelo.contexto_de_uso import (
    ROL_ESTUDIANTE,
    ContextoDeUso,
    PoliticaDelTurno,
    contexto_de_uso_de,
    puede_consultar_como_profesional,
)
from dominio.modelo.deteccion_matematica import hallar_matematica
from dominio.pedagogia.conversacion import EstadoDeConversacion
from dominio.pedagogia.intenciones import PETICION_SOLUCION, clasificar
from dominio.pedagogia.problema import reiniciar_por_cambio_de_problema
from dominio.pedagogia.sondeo import EstadoDeSondeo, ItemOfrecido
from dominio.puertos.almacen import ErrorDeAlmacen
from dominio.puertos.supervision import (
    TIPO_DEGRADADO,
    TIPO_SIN_FUENTE,
    NuevoItem,
)

if TYPE_CHECKING:
    from dominio.puertos.clases import PuertoClases
    from dominio.puertos.estado_vigente import PuertoEstadoVigente
    from dominio.puertos.supervision import PuertoColaDeRevision

def es_un_intento(mensaje: str) -> bool:
    intencion = clasificar(mensaje, bool(hallar_matematica(mensaje)))
    return intencion.propone_solucion

def contabilizar(datos: dict, mensaje: str) -> None:
    intencion = clasificar(mensaje, bool(hallar_matematica(mensaje)))
    if intencion.confirma_ayuda:
        datos["peticion_confirmada"] = True
    elif intencion.clase == PETICION_SOLUCION:
        datos["insistencias"] += 1
    elif intencion.propone_solucion:
        datos["intentos"] += 1

def estado_de_conversacion_de(datos: dict) -> EstadoDeConversacion:
    return EstadoDeConversacion.desde_dict(datos.get("estado_pedagogico"))

def reiniciar_si_cambio_el_problema(
    estado: EstadoDeConversacion, mensaje: str, ejercicio_activo: dict | None = None
) -> EstadoDeConversacion:

    expresiones, _ = segmentar(mensaje)
    intencion = clasificar(mensaje, bool(hallar_matematica(mensaje)))
    from dominio.filtros.intento import ejercicio_de_intento_explicito
    from dominio.pedagogia.confirmacion import base_de_ejercicio
    from dominio.pedagogia.problema import normalizar_expresion

    nuevo = extraer_ejercicio_explicito(mensaje) or ejercicio_de_intento_explicito(mensaje)
    base = base_de_ejercicio(nuevo)
    if not nuevo and ejercicio_activo and expresiones and (
        len(expresiones) >= 2 or not intencion.propone_solucion
    ) and normalizar_expresion(expresiones[0]) == normalizar_expresion(ejercicio_activo.get("expresion", "")):
        base = base_de_ejercicio(ejercicio_activo)
    problema, cambio = reiniciar_por_cambio_de_problema(
        estado.problema, intencion, expresiones, base=base
    )
    return estado.con_problema(problema) if cambio else estado

def corregir_inferencia_si_lo_pide(
    estado: EstadoDeConversacion, mensaje: str
) -> EstadoDeConversacion:

    intencion = clasificar(mensaje, bool(hallar_matematica(mensaje)))
    if not intencion.corrige_inferencia:
        return estado
    return estado.con_inferencia_corregida()

def anotar_el_estado(datos: dict, estado: EstadoDeConversacion) -> None:
    datos["estado_pedagogico"] = estado.como_dict()

    datos["intentos"] = estado.problema.intentos
    datos["insistencias"] = estado.problema.insistencias
    datos["peticion_confirmada"] = estado.problema.peticion_confirmada
    datos["sin_adaptacion"] = estado.sin_adaptacion
    datos["estrategia_previa"] = estado.estrategia_previa

def recordar_preferencias(datos: dict, mensaje: str) -> None:
    intencion = clasificar(mensaje, bool(hallar_matematica(mensaje)))
    if intencion.sin_adaptacion:
        datos["sin_adaptacion"] = True
    elif intencion.reactiva_adaptacion:
        datos["sin_adaptacion"] = False

def claves_del_titular(datos: dict) -> tuple[str, str]:
    titular = sujeto_de(datos)
    return titular, (titular if aviso_legal.modulo_conductual_habilitado(datos) else "")

def clase_de_la_sesion(clases_almacen: PuertoClases, sujeto: str) -> str | None:
    propias = clases_almacen.mias(sujeto)
    if len(propias) == 1:
        return propias[0].identificador
    return None

def rechazo_previo(
    sesiones: Sesiones,
    limitador: LimitadorDePeticiones,
    peticion: Request,
    estado_vigente: PuertoEstadoVigente | None = None,
) -> tuple[dict | None, JSONResponse | None]:

    datos = sesiones.leer(peticion.cookies.get(COOKIE))
    if datos is None:
        return None, JSONResponse({"detalle": "sin sesión"}, status_code=401)

    negativa = _puerta_del_turno(datos, estado_vigente)
    if negativa is not None:
        return None, negativa

    ip = peticion.client.host if peticion.client else "desconocida"

    if not limitador.admite_turno(ip, datos["sesion_autenticada"], sujeto_de(datos)):

        return None, JSONResponse({"detalle": "demasiadas peticiones"}, status_code=429)

    return datos, None

def _puerta_del_turno(
    datos: dict, estado_vigente: PuertoEstadoVigente | None
) -> JSONResponse | None:

    rol = datos.get("rol")
    if rol == ROL_ESTUDIANTE:
        return _rechazo_por_acceso(datos, estado_vigente)
    if puede_consultar_como_profesional(rol):
        return _apertura_profesional(datos)
    return JSONResponse(
        {
            "detalle": "esta cuenta no tiene el tutor habilitado",
            "estado": "rol_sin_tutor",
        },
        status_code=403,
    )

def _apertura_profesional(datos: dict) -> None:
    datos["consentimiento_evento"] = None
    datos["acceso_calculado"] = None
    datos["contexto_de_uso_turno"] = ContextoDeUso.CONSULTA_PROFESIONAL
    return None

_CODIGO_POR_ACCESO = {
    AccesoCalculado.ONBOARDING_PENDIENTE: 409,
    AccesoCalculado.ESPERANDO_REPRESENTANTE: 409,
    AccesoCalculado.BLOQUEADO_POR_RECHAZO: 403,
    AccesoCalculado.BLOQUEADO_POR_REVOCACION: 403,
    AccesoCalculado.ELIMINACION_SOLICITADA: 403,
    AccesoCalculado.MANTENIMIENTO: 503,
}


def _rechazo_por_acceso(
    datos: dict, estado_vigente: PuertoEstadoVigente | None
) -> JSONResponse | None:

    datos["consentimiento_evento"] = None
    datos["acceso_calculado"] = None
    datos["contexto_de_uso_turno"] = None
    if estado_vigente is None:
        return mantenimiento("no se puede comprobar el consentimiento en este momento")
    try:
        estado = estado_vigente.estado_vigente(datos["identificador_estable"])
    except ErrorDeAlmacen:
        return mantenimiento("no se puede comprobar el consentimiento en este momento")
    if estado is None:

        return mantenimiento("la identidad de esta sesión no está disponible")

    acceso = calcular_acceso(estado)

    datos["acceso_calculado"] = acceso
    if permite_tutor(acceso) or permite_tutoria_academica(estado):
        if acceso is AccesoCalculado.HABILITADO:
            datos["consentimiento_evento"] = estado.evento_consentimiento
            datos["contexto_de_uso_turno"] = ContextoDeUso.APRENDIZAJE_ESTUDIANTE
        else:
            datos["contexto_de_uso_turno"] = (
                ContextoDeUso.TUTORIA_ACADEMICA_SIN_INVESTIGACION
            )
        return None
    return JSONResponse(
        {"detalle": "el tutor no está habilitado para esta cuenta", "acceso": acceso.value},
        status_code=_CODIGO_POR_ACCESO.get(acceso, 403),
    )

def respuesta_al_item_de(cuerpo: dict) -> RespuestaAlItem | None:
    crudo = cuerpo.get("dos_niveles")
    if not isinstance(crudo, dict):
        return None
    nodo = str(crudo.get("nodo") or "").strip()
    resultado = str(crudo.get("resultado") or "").strip()
    razon = str(crudo.get("razon") or "").strip()
    if not (nodo and resultado and razon):

        return None
    return RespuestaAlItem(nodo=nodo, resultado=resultado, razon=razon)

def recordar_expresion(datos: dict, mensaje: str) -> None:
    activo = datos.get("ejercicio_activo") or {}
    if activo and activo.get("tipo") != "limite":

        datos["expresion_previa"] = activo.get("expresion", "")
        return
    if activo and extraer_ejercicio_explicito(mensaje) is None:

        return
    expresiones, _ = segmentar(mensaje)
    if expresiones:
        datos["expresion_previa"] = expresiones[0]

def recordar_ejercicio(datos: dict, mensaje: str) -> None:
    from dominio.filtros.intento import ejercicio_de_intento_explicito
    from dominio.modelo.referencias_matematicas import recordar_funciones_y_resolver

    ejercicio = recordar_funciones_y_resolver(datos, mensaje)
    if ejercicio is None:
        ejercicio = extraer_ejercicio_explicito(mensaje) or ejercicio_de_intento_explicito(mensaje)
        if ejercicio is not None:
            datos.pop("funcion_vigente", None)
    if ejercicio is not None:
        datos["ejercicio_activo"] = ejercicio
        datos.pop("ejercicio_en_pausa", None)
    elif not datos.get("ejercicio_activo") and datos.get("ejercicio_en_pausa"):

        previo = datos["ejercicio_en_pausa"]
        nombre = r"l[ií]mite" if previo.get("tipo") == "limite" else r"derivada"
        retoma = re.search(
            r"\b(?:resultado|respuesta|valor|retomemos|retomar|volver|vuelvo|antes)\b",
            mensaje, re.I,
        )
        if retoma and re.search(rf"\b{nombre}\b", mensaje, re.I):
            datos["ejercicio_activo"] = datos.pop("ejercicio_en_pausa")
            destino = destino_solicitado_para_limite(mensaje, previo.get("destino", ""))
            if destino and previo.get("tipo") == "limite":
                datos["ejercicio_activo"] = {**previo, "destino": destino}
    elif (datos.get("ejercicio_activo") or {}).get("tipo") == "limite":
        destino = destino_solicitado_para_limite(mensaje, datos["ejercicio_activo"].get("destino", ""))
        if destino:
            datos["ejercicio_activo"] = {**datos["ejercicio_activo"], "destino": destino}
        elif (re.search(r"\b(?:grafica|graficar|dibuja|simplifica|factoriza|integra)\b", mensaje, re.I)
              and segmentar(mensaje)[0]
              and not re.search(r"\b(?:a[nñ]ade|agrega|compara)\b", mensaje, re.I)
              and extraer_curva_solicitada(mensaje) != datos["ejercicio_activo"].get("expresion")):
            datos["ejercicio_en_pausa"] = datos.pop("ejercicio_activo")
    elif (re.search(r"\b(?:grafica|graficar|dibuja|simplifica|factoriza|integra)\b", mensaje, re.I)
          and segmentar(mensaje)[0]
          and not re.search(r"\b(?:a[nñ]ade|agrega|compara)\b", mensaje, re.I)
          and extraer_curva_solicitada(mensaje) != (datos.get("ejercicio_activo") or {}).get("expresion")):

        datos["ejercicio_en_pausa"] = datos.pop("ejercicio_activo", None)

def recuperar_ejercicio_del_historial(datos: dict, contexto: list[dict]) -> None:
    datos.pop("ejercicio_activo", None)
    datos.pop("ejercicio_en_pausa", None)
    datos.pop("funciones_declaradas", None)
    datos.pop("funcion_vigente", None)
    datos.pop("expresion_previa", None)
    for par in contexto:
        mensaje = str(par.get("estudiante", ""))
        recordar_ejercicio(datos, mensaje)
        recordar_expresion(datos, mensaje)

def estado_de_sondeo_de(datos: dict) -> EstadoDeSondeo:
    return EstadoDeSondeo(
        turnos_desde_el_ultimo=int(datos.get("turnos_desde_el_sondeo", 0)),
        ofrecidos=tuple(
            ItemOfrecido(nodo=str(o.get("nodo", "")), razones=tuple(o.get("razones", ())))
            for o in datos.get("sondeos_ofrecidos", ())
            if isinstance(o, dict)
        ),
        contestados=tuple(str(n) for n in datos.get("sondeos_contestados", ())),
    )

def anotar_el_item_contestado(datos: dict, desenlace) -> None:
    if not desenlace.cierra_el_item:
        return
    contestados = list(datos.get("sondeos_contestados", ()))
    if desenlace.nodo and desenlace.nodo not in contestados:
        contestados.append(desenlace.nodo)
    datos["sondeos_contestados"] = contestados

def anotar_el_sondeo(datos: dict, salida) -> None:
    sondeo = salida.cuerpo.sondeo if salida.cuerpo is not None else None
    if sondeo is None:
        datos["turnos_desde_el_sondeo"] = int(datos.get("turnos_desde_el_sondeo", 0)) + 1
        return
    datos["turnos_desde_el_sondeo"] = 0

    ofrecidos = list(datos.get("sondeos_ofrecidos", ()))
    if all(o.get("nodo") != sondeo.nodo for o in ofrecidos):
        ofrecidos.append(
            {"nodo": sondeo.nodo, "razones": [r.id for r in sondeo.razones]}
        )
    datos["sondeos_ofrecidos"] = ofrecidos

def encolar_si_es_excepcion(
    cola: PuertoColaDeRevision,
    mensaje: str,
    salida,
    clase: str | None = None,
    estudiante: str = "",
    sesion: str = "",
):

    if salida.degradado is not None:
        return cola.agregar(NuevoItem(
            urgencia="normal", clase=clase, tipo=TIPO_DEGRADADO, mensaje=mensaje,
            turno={"situacion": "degradado", **asdict(salida.degradado)},
            estudiante=estudiante, sesion=sesion,
        ))
    if salida.cuerpo is not None and salida.cuerpo.procedencia.origen == "sin-fuente":
        return cola.agregar(NuevoItem(
            urgencia="normal", clase=clase, tipo=TIPO_SIN_FUENTE, mensaje=mensaje,
            turno=asdict(salida.cuerpo),
            estudiante=estudiante, sesion=sesion,
        ))
    return None

def contexto_retomado(
    adaptador_historial, identificador_sesion: str, datos: dict
) -> list[dict] | None:

    if adaptador_historial is None:
        return None
    sujeto = datos.get("identificador_estable") or ""
    if not sujeto:
        return None
    try:

        mensajes = adaptador_historial.hilo_de(
            identificador_sesion, sujeto, actor=sujeto, operacion=OPERACION_CONSULTA
        )
    except ErrorDeAlmacen:
        return None
    if not mensajes:
        return None

    pares: dict[int, dict] = {}
    for m in mensajes:
        par = pares.setdefault(m["turno"], {})
        if m["autor"] == "estudiante":
            par["estudiante"] = m["contenido"]
        else:

            par["tutor"] = " ".join(
                b["contenido"] for b in m.get("bloques", [])
                if b.get("tipo") in ("prosa", "notacion", "expresion-citada")
            )

    recuperar_ejercicio_del_historial(datos, list(pares.values()))
    completos = [p for p in pares.values() if p.get("estudiante") and p.get("tutor")]
    reconstruir_contexto_factual(datos, identificador_sesion, [
        {**par, "turno_id": str(turno)} for turno, par in pares.items()
        if par.get("estudiante") and par.get("tutor")
    ])
    return completos[-6:]

@dataclass(frozen=True)
class DependenciasDelTurno:

    sesiones: Sesiones
    adaptador: AdaptadorTurno
    limitador: LimitadorDePeticiones
    clases_almacen: PuertoClases
    cola: PuertoColaDeRevision
    adaptador_historial: object | None = None
    estado_vigente: PuertoEstadoVigente | None = None

    instrumentador: Instrumentador = SIN_INSTRUMENTAR

def _turno_emitido(salida) -> str:
    if salida.cuerpo is not None:
        return salida.cuerpo.turno
    if salida.degradado is not None:
        return salida.degradado.turno
    return ""

def _instrumentar_el_turno(
    instrumentador: Instrumentador,
    sello: SelloDelTurno,
    salida,
    instante_envio,
    encolado,
    notacion: str,
) -> None:

    if not sello.turno:
        return
    instrumentador.turno_enviado(sello, notacion=notacion, ocurrido_en=instante_envio)
    instrumentador.turno_respondido(
        sello,
        ResultadoDelTurno(
            nivel=salida.cuerpo.nivel if salida.cuerpo is not None else "",
            procedencia=(
                salida.cuerpo.procedencia.origen if salida.cuerpo is not None else ""
            ),
            degradado=salida.degradado is not None,
            version_modelo=getattr(salida, "version_modelo", ""),
            version_corpus=instrumentador.version_del_corpus(),
        ),
    )
    if encolado is not None:
        instrumentador.supervision_derivada(
            sello,
            item=encolado.identificador,
            tipo_de_item=encolado.tipo,
            urgencia=encolado.urgencia,
        )

def crear_router(deps: DependenciasDelTurno) -> APIRouter:
    sesiones = deps.sesiones
    adaptador = deps.adaptador
    limitador = deps.limitador
    clases_almacen = deps.clases_almacen
    cola = deps.cola
    adaptador_historial = deps.adaptador_historial
    estado_vigente = deps.estado_vigente
    instrumentador = deps.instrumentador

    candados = CandadoPorConversacion()
    registro_idempotencia = RegistroDeIdempotencia()
    router = APIRouter()

    def _ndjson(emitidas: tuple[bytes, ...]) -> Response:
        return StreamingResponse(iter(emitidas), media_type="application/x-ndjson")

    @router.post("/api/turno")
    async def turno(peticion: Request) -> Response:
        datos, rechazo = rechazo_previo(sesiones, limitador, peticion, estado_vigente)
        if datos is None:

            return rechazo or JSONResponse({"detalle": "sin sesión"}, status_code=401)

        cuerpo = await json_del_cuerpo(peticion)
        conversacion_activa = str(datos.get("conversacion") or "")
        if getattr(adaptador, "continuidad", False):
            conversacion_activa = str(cuerpo.get("retomar_sesion") or cuerpo.get("sesion") or conversacion_activa)
            if conversacion_activa != datos.get("conversacion"):
                sujeto = datos.get("identificador_estable", "")
                try:
                    mensajes = await run_in_threadpool(
                        adaptador_historial.hilo_de, conversacion_activa, sujeto,
                        actor=sujeto, operacion=OPERACION_CONSULTA,
                    ) if adaptador_historial else []
                except ErrorDeAlmacen:
                    return JSONResponse({"detalle": "No se pudo recuperar esta charla. Reintenta."}, status_code=503)
                if not mensajes:
                    return JSONResponse({"detalle": "No se pudo recuperar esta charla."}, status_code=404)
        clave = clave_de(cuerpo)
        huella = RegistroDeIdempotencia.huella_de(cuerpo)

        candado = candados.obtener(conversacion_activa)
        await candado.acquire()
        try:
            if clave:
                recordada = registro_idempotencia.recordada(conversacion_activa, clave)
                if recordada is not None and recordada.huella != huella:

                    candado.release()
                    return JSONResponse(
                        {
                            "detalle": (
                                "esa clave de idempotencia ya se usó en esta "
                                "conversación con otro mensaje"
                            )
                        },
                        status_code=409,
                    )
                if recordada is not None:
                    candado.release()
                    return _ndjson(recordada.lineas)

        except BaseException:
            candado.release()
            raise

        def recordar(emitidas):
            if clave:
                registro_idempotencia.recordar(conversacion_activa, clave, huella, emitidas)

        emision = EmisionDelTurno(
            lambda al_iniciar: _turno_completo(datos, cuerpo, al_iniciar),
            recordar, candado.release,
        )
        return emision.respuesta()

    async def _turno_completo(datos: dict, cuerpo: dict, al_iniciar=None) -> tuple[bytes, ...]:
        if not getattr(adaptador, "continuidad", False):
            return await _procesar_turno(datos, cuerpo, al_iniciar)
        from dominio.modelo.continuidad import ejercicio

        destino = str(cuerpo.get("retomar_sesion") or cuerpo.get("sesion") or datos["conversacion"])
        if adaptador_historial is None or not hasattr(adaptador_historial, "abrir_estado_operativo"):
            raise RuntimeError("continuidad requiere almacenamiento operativo")
        checkpoint = await run_in_threadpool(
            adaptador_historial.abrir_estado_operativo, datos["identificador_estable"], destino,
        )
        try:
            recordada = checkpoint.respuesta_recordada(clave_de(cuerpo), RegistroDeIdempotencia.huella_de(cuerpo))
            if recordada is not None:
                return recordada
            trabajo = deepcopy(datos)
            trabajo.pop("continuidad_completada", None)
            estado = deepcopy(checkpoint.estado)

            if not estado.get("voces") and destino != datos.get("conversacion"):
                mensajes = await run_in_threadpool(
                    adaptador_historial.hilo_de, destino, datos["identificador_estable"],
                    actor=datos["identificador_estable"], operacion=OPERACION_CONSULTA,
                )
                from dominio.modelo.continuidad import preparar
                voces = []
                for m in mensajes:
                    if m["autor"] == "estudiante":
                        estado = preparar(estado, m["contenido"])
                        voces.append({"estudiante": m["contenido"]})
                    elif voces and m.get("bloques"):
                        voces[-1]["tutor"] = " ".join(
                            f"${b['contenido']}$" if b.get("tipo") in ("notacion", "expresion-citada") else b["contenido"]
                            for b in m["bloques"] if b.get("tipo") in ("prosa", "notacion", "expresion-citada")
                        )
                estado["voces"] = voces[-6:]
                estado["aclaracion"] = ""
            trabajo.update(conversacion=destino, estado_operativo=estado,
                           ejercicio_activo=ejercicio(estado),
                           expresion_previa=(ejercicio(estado) or {}).get("expresion", ""),
                           estado_pedagogico=estado.get("pedagogia", {}),
                           sin_adaptacion=bool(estado.get("pedagogia", {}).get("sin_adaptacion")),
                           historial_reciente=deepcopy(estado.get("voces", [])),
                           contexto_factual={"total": 0, "turnos": []}, sesion_contexto_factual="")
            trabajo.pop("retomando_activo", None)
            lineas = await _procesar_turno(trabajo, {**cuerpo, "retomar_sesion": ""}, al_iniciar)
            resuelto = trabajo.get("estado_operativo")
            if resuelto is not None and trabajo.get("continuidad_completada"):
                resuelto["pedagogia"] = trabajo.get("estado_pedagogico", {})

                resuelto["pedagogia"].pop("afectivo", None)
                resuelto["voces"] = trabajo.get("historial_reciente", [])[-6:]
                checkpoint.recordar_respuesta(resuelto, clave_de(cuerpo), RegistroDeIdempotencia.huella_de(cuerpo), lineas)
                await run_in_threadpool(checkpoint.guardar, resuelto)
            return lineas
        finally:
            await run_in_threadpool(checkpoint.cerrar)

    async def _procesar_turno(datos: dict, cuerpo: dict, al_iniciar=None) -> tuple[bytes, ...]:
        mensaje = str(cuerpo.get("mensaje") or "")

        politica = PoliticaDelTurno.del_contexto(
            datos.get("contexto_de_uso_turno")
            or contexto_de_uso_de(datos.get("rol"))
        )

        identificador_sesion_turno = datos["conversacion"]
        retomar_sesion = str(cuerpo.get("retomar_sesion") or "").strip()
        if retomar_sesion:
            if datos.get("retomando_activo") == retomar_sesion:

                identificador_sesion_turno = retomar_sesion
            else:

                contexto = await run_in_threadpool(
                    contexto_retomado, adaptador_historial, retomar_sesion, datos
                )

                if contexto is not None:
                    datos["historial_reciente"] = contexto
                    datos["retomando_activo"] = retomar_sesion
                    identificador_sesion_turno = retomar_sesion

        estado_pedagogico = _preparar_estado_del_turno(datos, mensaje, getattr(adaptador, "continuidad", False))

        clase = clase_de_la_sesion(clases_almacen, sujeto_de(datos)) if politica.resuelve_matricula else None

        identificador_titular, identificador_sujeto = claves_del_titular(datos)

        if not politica.escribe_perfil_longitudinal:
            identificador_sujeto = ""
        entrante = TurnoEntrante(
            sesion=identificador_sesion_turno,
            mensaje=mensaje,
            continuidad=datos.get("estado_operativo") if getattr(adaptador, "continuidad", False) else None,

            consentimiento_evento=datos.get("consentimiento_evento"),
            momento=str(cuerpo.get("momento") or ""),
            señales=Señales(

                intentos_en_el_problema=estado_pedagogico.problema.intentos,
                insistencias=estado_pedagogico.problema.insistencias,
                peticion_confirmada=estado_pedagogico.problema.peticion_confirmada,
            ),
            estado_conversacion=estado_pedagogico,

            escritura_longitudinal_permitida=(
                politica.escribe_perfil_longitudinal
                and aviso_legal.permite_escritura_conductual(
                    datos, datos.get("acceso_calculado")
                )
            ),
            clase=clase or "",
            identificador_sujeto=identificador_sujeto,

            identificador_titular=identificador_titular,

            respuesta_al_item=respuesta_al_item_de(cuerpo) if politica.diagnostica else None,

            estado_de_sondeo=estado_de_sondeo_de(datos) if politica.diagnostica else None,
            expresion_previa=str(datos.get("expresion_previa", "")),
            ejercicio_activo=datos.get("ejercicio_activo"),

            notacion=str(cuerpo.get("notacion") or ""),
            historial_reciente=tuple(datos.get("historial_reciente", [])),
            contexto_conversacional=(contexto_de_sesion(
                datos, identificador_sesion_turno, mensaje, datos.get("ejercicio_activo"),
            ) if getattr(adaptador, "contexto_reforzado", False) else {}),

            contexto_de_uso=politica.contexto,
        )

        instante_envio = datetime.now(UTC)
        manejar_con_progreso = getattr(
            adaptador, "manejar_con_progreso", lambda entrada, _: adaptador.manejar(entrada),
        )
        salida = (await run_in_threadpool(manejar_con_progreso, entrante, al_iniciar)
                  if al_iniciar is not None
                  else await run_in_threadpool(adaptador.manejar, entrante))
        _anotar_continuidad(datos, salida)
        recordar_contexto_factual(
            datos, identificador_sesion_turno, mensaje, salida,
            habilitado=getattr(adaptador, "contexto_reforzado", False),
        )
        if salida.estado_conversacion is not None:
            anotar_el_estado(datos, salida.estado_conversacion)

        if politica.diagnostica:
            anotar_el_sondeo(datos, salida)

            anotar_el_item_contestado(datos, salida.desenlace_del_sondeo)
        encolado = None
        if politica.encola_supervision:
            encolado = encolar_si_es_excepcion(
                cola, mensaje, salida, clase=clase,
                estudiante=identificador_titular,
                sesion=identificador_sesion_turno,
            )

        _instrumentar_el_turno(
            instrumentador,
            SelloDelTurno(
                sujeto=identificador_titular,
                conversacion=identificador_sesion_turno,
                turno=_turno_emitido(salida),
                contexto_de_uso=politica.contexto,
                clase=clase or None,
            ),
            salida,
            instante_envio,
            encolado,
            str(cuerpo.get("notacion") or ""),
        )

        if "historial_reciente" not in datos:
            datos["historial_reciente"] = []
        texto_tutor = ""
        if salida.cuerpo and salida.cuerpo.bloques:
            texto_tutor = " ".join(
                (f"${b.contenido}$" if getattr(adaptador, "continuidad", False) and b.tipo in ("notacion", "expresion-citada") else b.contenido)
                for b in salida.cuerpo.bloques if b.tipo in ("prosa", "notacion", "expresion-citada")
            )
        elif salida.degradado:
            texto_tutor = salida.degradado.explicacion
        if texto_tutor:
            datos["historial_reciente"].append({"estudiante": mensaje, "tutor": texto_tutor})
            datos["historial_reciente"] = datos["historial_reciente"][-6:]

        def lineas() -> Iterator[bytes]:
            for fase in salida.fases:
                yield (json.dumps(asdict(fase), ensure_ascii=False) + "\n").encode()
            final: dict = {}
            if salida.cuerpo is not None:
                final["cuerpo"] = asdict(salida.cuerpo)
            if salida.degradado is not None:

                final["degradado"] = {"situacion": "degradado", **asdict(salida.degradado)}
            yield (json.dumps(final, ensure_ascii=False) + "\n").encode()

        return tuple(lineas())

    return router

def _preparar_estado_del_turno(datos, mensaje, continuidad):
    estado_pedagogico = estado_de_conversacion_de(datos)
    if not continuidad:
        estado_pedagogico = reiniciar_si_cambio_el_problema(
            estado_pedagogico, mensaje, datos.get("ejercicio_activo")
        )
    recordar_preferencias(datos, mensaje)

    estado_pedagogico = dataclasses_replace(
        estado_pedagogico, sin_adaptacion=bool(datos.get("sin_adaptacion"))
    )

    estado_pedagogico = corregir_inferencia_si_lo_pide(estado_pedagogico, mensaje)

    if not continuidad:
        recordar_ejercicio(datos, mensaje)
        recordar_expresion(datos, mensaje)
    return estado_pedagogico

def _anotar_continuidad(datos, salida):
    if getattr(salida, "continuidad", None) is not None and salida.cuerpo is not None:
        from dominio.modelo.continuidad import ejercicio
        datos["estado_operativo"] = salida.continuidad
        datos["ejercicio_activo"] = ejercicio(salida.continuidad)
        datos["continuidad_completada"] = True
