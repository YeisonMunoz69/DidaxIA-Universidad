from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, mantenimiento, requerir_rol
from adaptadores.entrantes.http.rutas.puerta_de_supresion import respuesta_de_supresion
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from adaptadores.salientes.almacenamiento.fotos_perfil import AlmacenFotosPerfil
from adaptadores.salientes.notificacion.plantillas import solicitud_de_matricula
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible, EscrituraRechazada
from dominio.puertos.clases import ConflictoDeMatricula
from dominio.puertos.gobierno import SupresionEnCurso
from dominio.puertos.preferencias_notificacion import SOLICITUDES_MATRICULA

if TYPE_CHECKING:
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.clases import PuertoClases
    from dominio.puertos.gobierno import PuertoNotificacion
    from dominio.puertos.preferencias_notificacion import PuertoPreferenciasDeNotificacion

_ASUNTO_SOLICITUD = "Nueva solicitud para tu clase en DidaxIa"
_URL_CLASES = "https://app.didaxia.pro/mis-clases"
_URL_SOLICITUDES = "https://app.didaxia.pro/solicitudes-matricula"


def _mensaje_de_solicitud(solicitud) -> str:
    estudiante = solicitud.nombre_estudiante.strip() or "Un estudiante"
    docente = solicitud.nombre_docente.strip()
    saludo = f"Hola, {docente}." if docente else "Hola."
    return (
        f"{saludo}\n\n{estudiante} solicitó ingresar a "
        f"«{solicitud.nombre_destino}».\n\n"
        "Revisa la solicitud desde tu panel de clases en DidaxIa. Allí podrás "
        "confirmar la identidad y ver su foto de perfil, cuando esté disponible, "
        "antes de aprobar o rechazar el ingreso.\n\n"
        "Este mensaje es informativo: la matrícula no cambia hasta que una persona autorizada la apruebe."
    )

def _destinos_de_investigacion(configuracion: str) -> tuple[str, ...]:
    unicos: dict[str, str] = {}
    for fragmento in configuracion.replace(";", ",").split(","):
        correo = fragmento.strip()
        if correo and "@" in correo:
            unicos.setdefault(correo.casefold(), correo)
    return tuple(unicos.values())

def crear_router(
    sesiones: Sesiones,
    clases_almacen: PuertoClases,
    puerta: PuertaDeSupresion,
    fotos: AlmacenFotosPerfil | None = None,
    notificacion: PuertoNotificacion | None = None,
    preferencias_notificacion: PuertoPreferenciasDeNotificacion | None = None,
    *,
    correo_investigacion: str = "",
) -> APIRouter:

    router = APIRouter()

    def _congelada(datos) -> Response | None:
        return puerta.negativa(sujeto_de(datos))

    def _correo_habilitado(*, sujeto: str = "", correo: str = "") -> bool:
        if preferencias_notificacion is None:
            return False
        try:
            if sujeto:
                return preferencias_notificacion.habilitada(
                    sujeto, SOLICITUDES_MATRICULA
                )
            if correo:
                return preferencias_notificacion.habilitada_para_correo(
                    correo, SOLICITUDES_MATRICULA
                )
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return False
        return False

    @router.get("/api/clases")
    def listar_clases(peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)

        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        return JSONResponse([c.como_resumen() for c in clases_almacen.mias(sujeto_de(datos))])

    @router.post("/api/clases")
    async def crear_clase(peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))

        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        nombre = str(cuerpo.get("nombre") or "").strip()
        if not nombre:
            return JSONResponse({"detalle": "falta el nombre de la clase"}, status_code=400)
        try:
            clase = clases_almacen.crear(nombre, sujeto_de(datos))
        except SupresionEnCurso:

            return respuesta_de_supresion()
        return JSONResponse(clase.como_resumen(), status_code=201)

    @router.post("/api/clases/unirse")
    async def unirse_a_clase(peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        error = requerir_rol(sesiones, peticion, "estudiante")
        if error is not None:
            return error
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        codigo = str(cuerpo.get("codigo") or "").strip()
        try:
            solicitud = clases_almacen.unirse(codigo, sujeto_de(datos)) if codigo else None
        except SupresionEnCurso:
            return respuesta_de_supresion()
        except ConflictoDeMatricula as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=409)
        if solicitud is None:
            return JSONResponse({"detalle": "código no reconocido"}, status_code=404)
        aviso_enviado = False
        if (
            notificacion is not None
            and solicitud.correo_docente
            and _correo_habilitado(
                sujeto=solicitud.docente,
                correo=solicitud.correo_docente,
            )
        ):
            aviso_enviado = notificacion.avisar(
                solicitud.correo_docente,
                _ASUNTO_SOLICITUD,
                _mensaje_de_solicitud(solicitud),
                clave_idempotencia=f"solicitud-matricula/{solicitud.identificador}",
                html=solicitud_de_matricula(
                    destinatario=solicitud.nombre_docente,
                    estudiante=solicitud.nombre_estudiante,
                    clase=solicitud.nombre_destino,
                    url_accion=_URL_CLASES,
                ),
            )
        avisos_investigacion = []
        destinos_investigacion = (
            _destinos_de_investigacion(correo_investigacion)
            if notificacion is not None
            else ()
        )
        for destino in destinos_investigacion:
            if destino.casefold() == solicitud.correo_docente.casefold():
                continue
            if not _correo_habilitado(correo=destino):
                continue
            huella_destino = sha256(destino.casefold().encode("utf-8")).hexdigest()[:12]
            avisos_investigacion.append(notificacion.avisar(
                destino,
                "Nueva solicitud institucional de matrícula en DidaxIa",
                _mensaje_de_solicitud(solicitud),
                clave_idempotencia=(
                    f"solicitud-matricula/{solicitud.identificador}/"
                    f"investigacion/{huella_destino}"
                ),
                html=solicitud_de_matricula(
                    destinatario="Equipo de investigación",
                    estudiante=solicitud.nombre_estudiante,
                    clase=solicitud.nombre_destino,
                    url_accion=_URL_SOLICITUDES,
                ),
            ))
        salida = solicitud.como_elemento()
        salida["aviso_docente_enviado"] = aviso_enviado
        salida["aviso_investigacion_enviado"] = bool(avisos_investigacion) and all(
            avisos_investigacion
        )
        salida["avisos_investigacion_enviados"] = sum(avisos_investigacion)
        return JSONResponse(salida, status_code=202)

    @router.get("/api/clases/solicitudes")
    def solicitudes_de_matricula(peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        if datos.get("rol") not in {"estudiante", "docente", "investigador"}:
            return JSONResponse({"detalle": "rol sin acceso a solicitudes"}, status_code=403)
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        try:
            solicitudes = clases_almacen.solicitudes(sujeto_de(datos), datos["rol"])
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento()
        return JSONResponse([s.como_elemento() for s in solicitudes])

    def _resolver_matricula(identificador: str, peticion: Request, decision: str) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        roles = {"estudiante"} if decision == "cancelada" else {"docente", "investigador"}
        if datos["rol"] not in roles:
            return JSONResponse({"detalle": "sin permiso para esta decisión"}, status_code=403)
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        try:
            solicitud = clases_almacen.resolver_solicitud(
                identificador, sujeto_de(datos), datos["rol"], decision,
            )
        except SupresionEnCurso:
            return respuesta_de_supresion()
        except ConflictoDeMatricula as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=409)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento()
        if solicitud is None:
            return JSONResponse({"detalle": "solicitud no encontrada o sin permiso"}, status_code=404)
        return JSONResponse(solicitud.como_elemento())

    @router.post("/api/clases/solicitudes/{identificador}/aprobar")
    def aprobar_matricula(identificador: str, peticion: Request) -> Response:
        return _resolver_matricula(identificador, peticion, "aprobada")

    @router.post("/api/clases/solicitudes/{identificador}/rechazar")
    def rechazar_matricula(identificador: str, peticion: Request) -> Response:
        return _resolver_matricula(identificador, peticion, "rechazada")

    @router.post("/api/clases/solicitudes/{identificador}/cancelar")
    def cancelar_matricula(identificador: str, peticion: Request) -> Response:
        return _resolver_matricula(identificador, peticion, "cancelada")

    @router.get("/api/clases/{identificador}/integrantes")
    def integrantes_de_clase(identificador: str, peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        integrantes = clases_almacen.integrantes(identificador, sujeto_de(datos))
        if integrantes is None:
            return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
        return JSONResponse([m.como_fila() for m in integrantes])

    @router.delete("/api/clases/{identificador}/integrantes/{sujeto}")
    async def retirar_integrante_de_clase(
        identificador: str, sujeto: str, peticion: Request
    ) -> Response:

        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if (congelada := _congelada(datos)) is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        motivo = str(cuerpo.get("motivo") or "").strip()
        if not 5 <= len(motivo) <= 240:
            return JSONResponse(
                {"detalle": "explica el retiro en entre 5 y 240 caracteres"},
                status_code=400,
            )
        try:
            retirada = clases_almacen.retirar_integrante(
                identificador, sujeto_de(datos), sujeto, motivo
            )
        except SupresionEnCurso:
            return respuesta_de_supresion()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo retirar la matrícula")
        if retirada is None:
            return JSONResponse(
                {"detalle": "no encontrada, no es tuya o la persona ya no está matriculada"},
                status_code=404,
            )
        return JSONResponse({
            "clase": identificador,
            "retirado": retirada.como_fila(),
            "resultado": "matrícula cerrada; la cuenta y su historia se conservaron",
        })

    @router.get("/api/clases/{identificador}/integrantes/{sujeto}")
    def ficha_de_integrante(identificador: str, sujeto: str, peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)

        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        integrantes = clases_almacen.integrantes(identificador, sujeto_de(datos))
        if integrantes is None:
            return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
        matricula = next((m for m in integrantes if m.identificador == sujeto), None)
        if matricula is None:
            return JSONResponse(
                {"detalle": "esa persona no está matriculada en esta clase"},
                status_code=404,
            )
        clase = next(
            (c for c in clases_almacen.mias(sujeto_de(datos)) if c.identificador == identificador),
            None,
        )
        return JSONResponse(
            {
                "clase": {
                    "id": identificador,
                    "nombre": clase.nombre if clase is not None else "",
                },
                "estudiante": matricula.como_fila(),
            }
        )

    @router.get("/api/clases/{identificador}/integrantes/{sujeto}/foto")
    def foto_de_integrante(identificador: str, sujeto: str, peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        if datos.get("rol") not in {"docente", "investigador"}:
            return JSONResponse({"detalle": "rol sin acceso a esta foto"}, status_code=403)
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        if datos["rol"] == "investigador":
            try:
                matricula = clases_almacen.integrante_para_investigacion(
                    identificador, sujeto_de(datos), sujeto
                )
            except EscrituraRechazada:
                return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
            except (AlmacenNoConfigurado, AlmacenNoDisponible):
                return mantenimiento("la foto institucional no está disponible")
        else:
            integrantes = clases_almacen.integrantes(identificador, sujeto_de(datos))
            if integrantes is None:
                return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
            matricula = next((m for m in integrantes if m.identificador == sujeto), None)
        if matricula is None or not matricula.foto_referencia:
            return JSONResponse({"detalle": "este integrante no tiene foto"}, status_code=404)
        if fotos is None or not fotos.configurado:
            return JSONResponse({"detalle": "las fotos no están disponibles"}, status_code=503)
        try:
            cuerpo = fotos.recuperar(matricula.foto_referencia)
        except (OSError, ValueError):
            cuerpo = None
        if cuerpo is None:
            return JSONResponse({"detalle": "la foto no está disponible"}, status_code=503)
        return Response(
            content=cuerpo,
            media_type="image/webp",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    @router.post("/api/clases/{identificador}/codigo")
    def regenerar_codigo_de_clase(identificador: str, peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        try:
            nuevo = clases_almacen.regenerar_codigo(identificador, sujeto_de(datos))
        except SupresionEnCurso:
            return respuesta_de_supresion()
        if nuevo is None:
            return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
        return JSONResponse({"codigo": nuevo})

    @router.patch("/api/clases/{identificador}")
    async def renombrar_clase(identificador: str, peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        nombre = str(cuerpo.get("nombre") or "").strip()
        if not nombre:
            return JSONResponse({"detalle": "falta el nombre de la clase"}, status_code=400)
        if len(nombre) > 120:
            return JSONResponse(
                {"detalle": "el nombre de la clase no puede superar 120 caracteres"},
                status_code=400,
            )
        try:
            clase = clases_almacen.renombrar(identificador, sujeto_de(datos), nombre)
        except SupresionEnCurso:
            return respuesta_de_supresion()
        if clase is None:
            return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
        return JSONResponse(clase.como_resumen())

    @router.delete("/api/clases/{identificador}")
    async def archivar_clase(identificador: str, peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        if datos.get("rol") not in {"docente", "investigador"}:
            return JSONResponse({"detalle": "sin permiso para eliminar clases"}, status_code=403)
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        motivo = str(cuerpo.get("motivo") or "").strip()
        if len(motivo) < 5 or len(motivo) > 240:
            return JSONResponse(
                {"detalle": "explica el motivo en 5 a 240 caracteres"}, status_code=400,
            )
        try:
            archivada = clases_almacen.archivar(identificador, sujeto_de(datos), motivo, datos["rol"])
        except SupresionEnCurso:
            return respuesta_de_supresion()
        except ConflictoDeMatricula as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=409)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento()
        if not archivada:
            return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
        return JSONResponse({"estado": "archivada", "clase": identificador})

    return router
