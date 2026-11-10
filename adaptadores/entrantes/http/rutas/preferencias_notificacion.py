"""Preferencias propias de correo para docentes e investigadores."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, mantenimiento, requerir_sesion
from adaptadores.entrantes.http.sesiones import Sesiones, sujeto_de
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    ReferenciaDesconocida,
)
from dominio.puertos.gobierno import SupresionEnCurso
from dominio.puertos.preferencias_notificacion import CATEGORIAS

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.preferencias_notificacion import PuertoPreferenciasDeNotificacion


def _representar(preferencias: dict[str, bool]) -> dict:
    return {
        "canal": "correo",
        "preferencias": preferencias,
        "opciones": [categoria.como_json() for categoria in CATEGORIAS.values()],
        "nota": (
            "Los avisos esenciales de seguridad, privacidad, recuperación de cuenta y "
            "gobierno de datos no se desactivan desde este panel."
        ),
    }


def crear_router(
    sesiones: Sesiones,
    preferencias: PuertoPreferenciasDeNotificacion,
    puerta: PuertaDeSupresion,
) -> APIRouter:
    router = APIRouter()

    def _profesional(peticion: Request):
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return None, negativa
        if datos.get("rol") not in {"docente", "investigador"}:
            return None, JSONResponse(
                {"detalle": "esta preferencia es de docentes e investigadores"}, status_code=403
            )
        return datos, None

    @router.get("/api/preferencias-notificacion")
    def consultar(peticion: Request):
        datos, negativa = _profesional(peticion)
        if negativa is not None:
            return negativa
        try:
            actuales = preferencias.consultar(sujeto_de(datos))
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudieron consultar las preferencias de correo")
        return _representar(actuales)

    @router.patch("/api/preferencias-notificacion/{categoria}")
    async def guardar(categoria: str, peticion: Request):
        datos, negativa = _profesional(peticion)
        if negativa is not None:
            return negativa
        if categoria not in CATEGORIAS:
            return JSONResponse({"detalle": "categoría de notificación no admisible"}, status_code=404)
        if (congelada := puerta.negativa(sujeto_de(datos))) is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        if set(cuerpo) != {"habilitada"} or not isinstance(cuerpo.get("habilitada"), bool):
            return JSONResponse(
                {"detalle": "envía únicamente el booleano «habilitada»"}, status_code=400
            )
        try:
            actuales = preferencias.guardar(
                sujeto_de(datos), categoria, cuerpo["habilitada"]
            )
        except SupresionEnCurso:
            return puerta.negativa(sujeto_de(datos)) or JSONResponse(
                {"detalle": "hay un trámite de supresión en curso"}, status_code=409
            )
        except ReferenciaDesconocida:
            return JSONResponse({"detalle": "la cuenta no está registrada"}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo guardar la preferencia de correo")
        return _representar(actuales)

    return router
