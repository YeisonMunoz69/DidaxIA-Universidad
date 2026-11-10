from __future__ import annotations

import hashlib

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from adaptadores.entrantes.http import formato_representante, pdf
from adaptadores.entrantes.http.rutas import decision_conjunta as rutas_decision
from adaptadores.entrantes.http.rutas.comun import (
    json_del_cuerpo,
    mantenimiento,
    requerir_sesion,
)
from adaptadores.entrantes.http.rutas.consentimiento_comun import (
    Repositorios,
    estado_como_json,
    leer_estado,
    recibo_de,
    version_como_json,
)
from adaptadores.entrantes.http.rutas.puerta_de_supresion import (
    ESTADO as ESTADO_SUPRESION,
)
from adaptadores.entrantes.http.rutas.puerta_de_supresion import (
    RUTA_DEL_TRAMITE,
    PuertaDeSupresion,
    respuesta_de_supresion,
)
from adaptadores.entrantes.http.sesiones import Sesiones
from dominio.modelo.comprobante import comprobante_de
from dominio.modelo.consentimiento import Alcance, EstadoConsentimiento
from dominio.modelo.identidad import IdentidadInvalida
from dominio.modelo.menores import (
    TAMANO_MAXIMO_BYTES,
    TIPO_MIME_ESPERADO,
    EstadoAsentimiento,
    EvidenciaInvalida,
    ResultadoDeRevision,
)
from dominio.modelo.oferta_academica import OfertaAcademicaInvalida
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    DatoNoAdmitido,
    EscrituraRechazada,
)
from dominio.puertos.almacenamiento_privado import (
    AlmacenamientoNoConfigurado,
    AlmacenamientoNoDisponible,
)
from dominio.puertos.gobierno import SupresionEnCurso


__all__ = ["Repositorios", "comprobante_de", "crear_router"]


def _entero(valor: object) -> int | None:
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        if not valor.lstrip("-").isdigit():
            return None
        valor = int(valor)
    return valor if isinstance(valor, int) else None

def _campos_de_perfil(cuerpo: dict, vigente: object) -> tuple[dict, JSONResponse | None]:
    edad = _entero(cuerpo.get("edad")) if "edad" in cuerpo else None
    semestre = _entero(cuerpo.get("semestre")) if "semestre" in cuerpo else None
    if "edad" in cuerpo and edad is None:
        return {}, JSONResponse({"detalle": "edad no admitida"}, status_code=400)
    if "semestre" in cuerpo and semestre is None:
        return {}, JSONResponse({"detalle": "semestre no admitido"}, status_code=400)

    facultad = str(cuerpo.get("facultad") or "").strip()
    programa = str(cuerpo.get("programa") or "").strip()
    if not facultad and (
        vigente is None
        or not getattr(vigente, "programa", "")
        or getattr(vigente, "semestre", None) is None
    ):
        return {}, JSONResponse({"detalle": "facultad no admitida"}, status_code=400)

    campos = {"edad": edad, "programa": programa, "semestre": semestre}

    if facultad:
        campos["facultad"] = facultad
    if "motivo" in cuerpo:
        campos["motivo"] = str(cuerpo.get("motivo") or "").strip()
    campos["origen"] = "onboarding_estudiante"
    return campos, None

def _ruta_retirada(alcance: str) -> JSONResponse:
    return JSONResponse(
        {
            "detalle": (
                f"esta ruta registraba el acto de alcance «{alcance}» por separado "
                "y permitía decisiones parciales. La decisión es una sola y sus "
                "actos se guardan atómicamente en el servidor"
            ),
            "estado": "ruta_retirada",
            "ruta_vigente": rutas_decision.CAMINO,
        },
        status_code=410,
    )

def crear_router(sesiones: Sesiones, repos: Repositorios) -> APIRouter:
    router = APIRouter()

    puerta = PuertaDeSupresion(repos.estado_vigente)

    rutas_decision.registrar_en(router, sesiones, repos)

    def _estado(sujeto: str):
        return leer_estado(repos, sujeto)

    @router.get("/api/onboarding/estado")
    def estado_de_onboarding(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        estado, acceso, fallo = _estado(datos["identificador_estable"])
        if fallo is not None:
            return fallo
        return JSONResponse(estado_como_json(estado, acceso))

    @router.post("/api/onboarding/perfil")
    async def declarar_perfil(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        congelada = puerta.negativa(datos["identificador_estable"])
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)

        try:
            vigente = repos.identidades.consultar(datos["identificador_estable"])
            campos, negativa_del_perfil = _campos_de_perfil(cuerpo, vigente)
            if negativa_del_perfil is not None:
                return negativa_del_perfil
            perfil = repos.identidades.declarar_perfil(
                datos["identificador_estable"], **campos
            )

            if perfil is not None:
                datos["edad"] = perfil.edad
        except (IdentidadInvalida, OfertaAcademicaInvalida) as error:

            return JSONResponse({"detalle": str(error)}, status_code=400)
        except SupresionEnCurso:

            return respuesta_de_supresion()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo guardar el perfil")

        estado, acceso, fallo = _estado(datos["identificador_estable"])
        if fallo is not None:
            return fallo
        return JSONResponse(estado_como_json(estado, acceso))

    @router.get("/api/consentimiento/versiones")
    def versiones_requeridas(peticion: Request) -> JSONResponse:
        _datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        try:
            requeridas = {
                alcance.value: repos.versiones.version_requerida(alcance)
                for alcance in Alcance
            }
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudieron leer las versiones vigentes")
        respuesta = {
            alcance: (version_como_json(v) if v is not None else None)
            for alcance, v in requeridas.items()
        }
        if respuesta["representante"] is not None:
            respuesta["representante"]["formato_disponible"] = (
                formato_representante.disponibilidad(requeridas["representante"])
                == "disponible"
            )
        return JSONResponse(respuesta)

    @router.get("/api/consentimiento/version/{codigo}/texto")
    def texto_de_la_version(codigo: str, peticion: Request) -> JSONResponse:
        _datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if repos.instantaneas is None:

            return mantenimiento("esta instalación no puede servir el documento")
        try:
            version = repos.versiones.consultar_version(codigo)
            instantanea = repos.instantaneas.instantanea_de(codigo)
        except DatoNoAdmitido:

            version = instantanea = None
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer el documento de la versión")

        if version is None or instantanea is None:
            return JSONResponse(
                {"detalle": "no hay documento publicado con ese código"},
                status_code=404,
            )
        if not instantanea.coincide_con(version.huella_contenido):

            return JSONResponse(
                {
                    "detalle": (
                        "el documento almacenado no corresponde a la huella "
                        "publicada; no se muestra"
                    )
                },
                status_code=409,
            )
        return JSONResponse(
            {
                "codigo": version.codigo,
                "alcance": version.alcance.value,
                "medio": instantanea.medio,
                "huella_contenido": version.huella_contenido,
                "cuerpo": instantanea.cuerpo,
            }
        )

    def _responder_con_estado(sujeto: str, evento, alcance: Alcance) -> JSONResponse:
        estado, acceso, fallo = _estado(sujeto)
        if fallo is not None:
            return fallo
        salida = estado_como_json(estado, acceso)
        salida["recibo"] = recibo_de(evento, alcance)
        salida["comprobante"] = evento.comprobante
        return JSONResponse(salida)

    def _revocar(sujeto: str, alcance: Alcance, es_asentimiento: bool) -> JSONResponse:
        repositorio = repos.asentimientos if es_asentimiento else repos.eventos
        try:
            codigo = repositorio.version_de_la_concesion(sujeto)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la concesión vigente")
        if codigo is None:
            return JSONResponse(
                {
                    "detalle": "no hay ninguna concesión otorgada que revocar",
                    "estado": "sin_concesion",
                },
                status_code=409,
            )
        try:
            version = repos.versiones.consultar_version(codigo)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la versión de la concesión")
        if version is None:

            return mantenimiento("la versión de esa concesión no está disponible")

        estado_nuevo = (
            EstadoAsentimiento.REVOCADO if es_asentimiento else EstadoConsentimiento.REVOCADO
        )
        comprobante = comprobante_de(
            sujeto, version.codigo, version.huella_contenido, estado_nuevo.value
        )
        try:
            evento = repositorio.registrar(sujeto, version.codigo, estado_nuevo, comprobante)
        except EscrituraRechazada as error:

            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo registrar la revocación")
        return _responder_con_estado(sujeto, evento, alcance)

    @router.post("/api/consentimiento/titular")
    def decidir_consentimiento() -> JSONResponse:
        return _ruta_retirada(Alcance.TITULAR.value)

    @router.post("/api/consentimiento/titular/revocar")
    def revocar_consentimiento(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        return _revocar(datos["identificador_estable"], Alcance.TITULAR, es_asentimiento=False)

    @router.post("/api/consentimiento/asentimiento")
    def decidir_asentimiento() -> JSONResponse:
        return _ruta_retirada(Alcance.ASENTIMIENTO.value)

    @router.post("/api/consentimiento/asentimiento/revocar")
    def revocar_asentimiento(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        return _revocar(
            datos["identificador_estable"], Alcance.ASENTIMIENTO, es_asentimiento=True
        )

    def _quien_puede_cargar(peticion: Request) -> tuple[str, JSONResponse | None]:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return "", negativa
        sujeto = datos["identificador_estable"]

        estado, _acceso, fallo = _estado(sujeto)
        if fallo is not None:
            return "", fallo
        if estado.eliminacion_solicitada:
            return "", respuesta_de_supresion(
                "tienes una solicitud de eliminación en curso: mientras dure no "
                "se acepta ninguna autorización nueva"
            )
        if not estado.es_menor:
            return "", JSONResponse(
                {"detalle": "la autorización del representante sólo aplica a un menor de edad"},
                status_code=409,
            )
        return sujeto, None

    @router.get("/api/representante/formato")
    def descargar_formato(peticion: Request) -> Response:
        _sujeto, negativa = _quien_puede_cargar(peticion)
        if negativa is not None:
            return negativa

        try:
            version = repos.versiones.version_requerida(Alcance.REPRESENTANTE)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la versión vigente")
        disponibilidad = formato_representante.disponibilidad(version)
        if disponibilidad == "sin_version":
            return JSONResponse(
                {
                    "detalle": "no hay ninguna versión vigente del documento del representante",
                    "estado": "sin_version",
                },
                status_code=409,
            )
        if disponibilidad == "version_no_corresponde":
            return JSONResponse(
                {
                    "detalle": (
                        "la versión vigente del representante no corresponde al "
                        "formato aprobado disponible para descarga"
                    ),
                    "estado": "formato_no_corresponde",
                },
                status_code=409,
            )

        if disponibilidad == "plantilla_no_disponible":
            return mantenimiento("el formato de autorización no está disponible")

        fecha = formato_representante.fecha_del_piloto()
        try:
            contenido = formato_representante.generar_pdf(fecha)
        except formato_representante.FormatoNoDisponible:
            return mantenimiento("el formato de autorización no está disponible")

        nombre = f"autorizacion-representante-menor-{fecha.isoformat()}.pdf"
        return Response(
            content=contenido,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{nombre}"',
                "Cache-Control": "no-store, private",
                "X-Content-Type-Options": "nosniff",
                "X-DidaxIA-Version-Representante": version.codigo,
                "X-DidaxIA-Fecha-Descarga": fecha.isoformat(),
            },
        )

    def _rechazar_archivo(contenido: bytes, declarado: str) -> JSONResponse | None:
        if declarado != TIPO_MIME_ESPERADO:
            return JSONResponse(
                {"detalle": f"la evidencia se recibe como {TIPO_MIME_ESPERADO}"},
                status_code=415,
            )
        if not contenido:
            return JSONResponse({"detalle": "el archivo llegó vacío"}, status_code=400)
        if len(contenido) > TAMANO_MAXIMO_BYTES:
            return JSONResponse(
                {"detalle": f"el archivo excede {TAMANO_MAXIMO_BYTES} bytes"},
                status_code=413,
            )
        try:
            pdf.exigir_pdf_utilizable(contenido)
        except pdf.PdfInutilizable as error:

            return JSONResponse({"detalle": str(error)}, status_code=415)
        return None

    @router.post("/api/representante/evidencia")
    async def cargar_evidencia(peticion: Request) -> JSONResponse:
        sujeto, negativa = _quien_puede_cargar(peticion)
        if negativa is not None:
            return negativa

        contenido = await peticion.body()
        declarado = peticion.headers.get("content-type", "").split(";")[0].strip().lower()
        rechazo = _rechazar_archivo(contenido, declarado)
        if rechazo is not None:
            return rechazo

        try:
            version = repos.versiones.version_requerida(Alcance.REPRESENTANTE)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la versión vigente")
        if version is None:
            return JSONResponse(
                {
                    "detalle": "no hay ninguna versión vigente del documento del representante",
                    "estado": "sin_version",
                },
                status_code=409,
            )

        try:
            referencia = repos.almacenamiento.reservar(
                contenido,
                sujeto_google=sujeto,
                intento=len(_intentos_o_vacio(repos, sujeto)) + 1,
            )
        except (AlmacenamientoNoConfigurado, AlmacenamientoNoDisponible):
            return mantenimiento("el almacenamiento privado no está disponible")

        try:
            intento = repos.evidencias.registrar_intento(
                sujeto,
                version.codigo,
                referencia,
                hashlib.sha256(contenido).hexdigest(),
                len(contenido),
            )
        except EvidenciaInvalida as error:
            return _compensar(repos, referencia, {"detalle": str(error)}, 400)
        except SupresionEnCurso as error:

            return _compensar(
                repos,
                referencia,
                {
                    "detalle": str(error),
                    "estado": ESTADO_SUPRESION,
                    "usar": RUTA_DEL_TRAMITE,
                },
                409,
            )
        except EscrituraRechazada as error:
            return _compensar(repos, referencia, {"detalle": str(error)}, 409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return _compensar(
                repos,
                referencia,
                {"detalle": "no se pudo registrar la evidencia", "estado": "mantenimiento"},
                503,
            )

        try:
            repos.almacenamiento.confirmar(referencia)
        except (AlmacenamientoNoConfigurado, AlmacenamientoNoDisponible):

            return JSONResponse(
                {
                    "detalle": (
                        "la evidencia quedó como reserva pendiente: se registró la "
                        "carga pero no se pudo completar su custodia"
                    ),
                    "estado": "mantenimiento",
                    "reserva_pendiente": True,
                },
                status_code=503,
                headers={"Retry-After": "30"},
            )

        estado, acceso, fallo = _estado(sujeto)
        if fallo is not None:
            return fallo
        salida = estado_como_json(estado, acceso)
        salida["intento"] = intento.intento
        salida["sha256"] = intento.sha256
        return JSONResponse(salida)

    @router.post("/api/representante/evidencia/{evidencia}/revisar")
    async def revisar_evidencia(evidencia: int, peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        congelada = puerta.negativa(datos["identificador_estable"])
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        resultado = {
            "aprobada": ResultadoDeRevision.APROBADA,
            "rechazada": ResultadoDeRevision.RECHAZADA,
        }.get(str(cuerpo.get("resultado") or ""))
        if resultado is None:
            return JSONResponse({"detalle": "resultado no admitido"}, status_code=400)

        try:
            revision = repos.evidencias.revisar(
                evidencia,
                datos["identificador_estable"],
                resultado,
                str(cuerpo.get("motivo") or ""),
            )
        except EvidenciaInvalida as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except EscrituraRechazada as error:

            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo registrar la revisión")

        return JSONResponse(
            {
                "resultado": revision.resultado.value,
                "revisada_en": revision.revisada_en.isoformat(),
                "motivo": revision.motivo,
            }
        )

    return router

def _intentos_o_vacio(repos: Repositorios, sujeto: str) -> tuple:
    try:
        return repos.evidencias.intentos(sujeto)
    except (AlmacenNoConfigurado, AlmacenNoDisponible):
        return ()

def _compensar(
    repos: Repositorios, referencia: str, cuerpo: dict, codigo: int
) -> JSONResponse:

    salida = dict(cuerpo)
    try:
        repos.almacenamiento.retirar(referencia)
    except (AlmacenamientoNoConfigurado, AlmacenamientoNoDisponible):
        salida["reserva_pendiente"] = True
    cabeceras = {"Retry-After": "30"} if codigo == 503 else None
    return JSONResponse(salida, status_code=codigo, headers=cabeceras)
