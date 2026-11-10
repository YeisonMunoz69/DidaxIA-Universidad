from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento, requerir_sesion
from adaptadores.entrantes.http.sesiones import Sesiones
from dominio.modelo.evidencia_revisable import (
    ConsultaInvalida,
    EvidenciaRevisable,
    cursor_desde,
    filtro_desde,
    limite_desde,
)
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    EscrituraRechazada,
    ReferenciaDesconocida,
)
from dominio.puertos.almacenamiento_privado import (
    AlmacenamientoNoConfigurado,
    AlmacenamientoNoDisponible,
    DocumentoAusente,
    DocumentoPendienteDeConfirmacion,
)

if TYPE_CHECKING:
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.almacenamiento_privado import PuertoAlmacenamientoPrivado
    from dominio.puertos.menores import PuertoEvidenciaDelRepresentante

MOTIVO_SIN_ROL = "esta consulta la reserva EQ-023 a un investigador administrador vigente"


MOTIVO_NO_EXISTE = "esa evidencia no existe"


CABECERAS_DEL_ARCHIVO = {
    "Cache-Control": "no-store, private, max-age=0, must-revalidate",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'",
    "X-Download-Options": "noopen",
}


TIPO_DEL_ARCHIVO = "application/pdf"


@dataclass(frozen=True)
class DependenciasDeEvidencias:

    evidencias: PuertoEvidenciaDelRepresentante
    almacenamiento: PuertoAlmacenamientoPrivado

def _evidencia_como_json(evidencia: EvidenciaRevisable) -> dict:
    return {
        "evidencia": evidencia.evidencia,
        "sujeto": evidencia.sujeto_google,
        "intento": evidencia.intento,
        "version": evidencia.version,
        "sha256": evidencia.sha256,
        "tamano_bytes": evidencia.tamano_bytes,
        "tipo_mime": evidencia.tipo_mime,
        "recibido_en": evidencia.recibido_en.isoformat(),
        "estado": evidencia.estado.value,
        "resultado": evidencia.resultado.value if evidencia.resultado else None,
        "revisada_en": evidencia.revisada_en.isoformat() if evidencia.revisada_en else None,
        "estudiante": {
            "nombre": evidencia.estudiante_nombre,
            "clases": list(evidencia.clases),
        },
    }

def _detalle_como_json(evidencia: EvidenciaRevisable) -> dict:
    return {**_evidencia_como_json(evidencia), "motivo": evidencia.motivo or None}

def _sin_rol() -> JSONResponse:
    return JSONResponse({"detalle": MOTIVO_SIN_ROL, "estado": "sin_rol"}, status_code=403)

def _no_existe() -> JSONResponse:
    return JSONResponse(
        {"detalle": MOTIVO_NO_EXISTE, "estado": "no_encontrada"}, status_code=404
    )

def _peticion_invalida(error: ConsultaInvalida) -> JSONResponse:
    return JSONResponse({"detalle": str(error), "estado": "peticion_invalida"}, status_code=400)

def crear_router(
    sesiones: Sesiones,
    deps: DependenciasDeEvidencias,
    puerta: PuertaDeSupresion,
) -> APIRouter:

    router = APIRouter()

    def _congelada(datos) -> JSONResponse | None:
        return puerta.negativa(datos["identificador_estable"])

    @router.get("/api/representante/evidencias")
    def cola_de_evidencias(peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa

        congelada = _congelada(datos)
        if congelada is not None:
            return congelada

        parametros = peticion.query_params
        try:
            filtro = filtro_desde(parametros.get("estado"))
            limite = limite_desde(parametros.get("limite"))
            cursor = cursor_desde(parametros.get("cursor"))
        except ConsultaInvalida as error:
            return _peticion_invalida(error)

        try:
            pagina = deps.evidencias.cola(
                actor=datos["identificador_estable"],
                filtro=filtro,
                limite=limite,
                cursor=cursor,
            )
        except EscrituraRechazada:

            return _sin_rol()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la cola de evidencias")

        return JSONResponse(
            {
                "filtro": filtro.value,
                "limite": limite,
                "evidencias": [_evidencia_como_json(e) for e in pagina.evidencias],
                "cursor_siguiente": pagina.cursor_siguiente,
                "hay_mas": pagina.hay_mas,
            }
        )

    @router.get("/api/representante/evidencias/{evidencia}")
    def detalle_de_evidencia(evidencia: int, peticion: Request) -> JSONResponse:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa

        congelada = _congelada(datos)
        if congelada is not None:
            return congelada

        try:
            revisable = deps.evidencias.detalle(
                evidencia, actor=datos["identificador_estable"]
            )
        except ReferenciaDesconocida:

            return _no_existe()
        except EscrituraRechazada:
            return _sin_rol()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la evidencia")

        return JSONResponse(_detalle_como_json(revisable))

    @router.get("/api/representante/evidencias/{evidencia}/archivo")
    def archivo_de_evidencia(evidencia: int, peticion: Request) -> Response:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa

        congelada = _congelada(datos)
        if congelada is not None:
            return congelada

        try:
            referencia = deps.evidencias.referencia_del_documento(
                evidencia, actor=datos["identificador_estable"]
            )
        except ReferenciaDesconocida:
            return _no_existe()
        except EscrituraRechazada:
            return _sin_rol()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la evidencia")

        try:
            contenido = deps.almacenamiento.recuperar(referencia)
        except AlmacenamientoNoConfigurado:
            return mantenimiento(
                "el almacenamiento privado de la autorización no está configurado"
            )
        except DocumentoPendienteDeConfirmacion:

            return mantenimiento(
                "la carga de esta evidencia quedó sin confirmar y no se puede "
                "revisar hasta que una reconciliación la complete o la retire"
            )
        except DocumentoAusente:

            return mantenimiento(
                "la evidencia está registrada y su archivo no se pudo recuperar "
                "del almacenamiento privado"
            )
        except AlmacenamientoNoDisponible:
            return mantenimiento("el almacenamiento privado no está disponible")

        return Response(
            content=contenido,
            media_type=TIPO_DEL_ARCHIVO,
            headers={

                "Content-Disposition": f'inline; filename="evidencia-{evidencia}.pdf"',
                **CABECERAS_DEL_ARCHIVO,
            },
        )

    return router
