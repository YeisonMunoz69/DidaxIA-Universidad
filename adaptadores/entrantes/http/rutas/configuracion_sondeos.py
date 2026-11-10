"""Gobierno curricular de sondeos, exclusivo del equipo investigador."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import (
    json_del_cuerpo, mantenimiento, requerir_rol, requerir_sesion,
)
from adaptadores.entrantes.http.sesiones import Sesiones, sujeto_de
from dominio.pedagogia.configuracion_sondeos import NODOS_CONFIGURABLES
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible


def crear_router(sesiones: Sesiones, configuracion, puerta) -> APIRouter:
    router = APIRouter()

    def _investigador(peticion: Request):
        negativa = requerir_rol(sesiones, peticion, "investigador")
        if negativa is not None:
            return None, negativa
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return None, negativa
        if (bloqueo := puerta.negativa(sujeto_de(datos))) is not None:
            return None, bloqueo
        return datos, None

    def _respuesta(vigente):
        return JSONResponse(vigente.como_json(), headers={"Cache-Control": "no-store"})

    @router.get("/api/sondeos/configuracion")
    def consultar(peticion: Request):
        _, negativa = _investigador(peticion)
        if negativa is not None:
            return negativa
        if configuracion is None:
            return mantenimiento("no se puede consultar la configuración curricular")
        try:
            return _respuesta(configuracion.consultar())
        except (AlmacenNoConfigurado, AlmacenNoDisponible, RuntimeError):
            return mantenimiento("no se puede consultar la configuración curricular")

    @router.patch("/api/sondeos/configuracion/nodos/{nodo}")
    async def cambiar_nodo(nodo: str, peticion: Request):
        datos, negativa = _investigador(peticion)
        if negativa is not None:
            return negativa
        if nodo not in NODOS_CONFIGURABLES:
            return JSONResponse({"detalle": "nodo no configurable"}, status_code=404)
        cuerpo = await json_del_cuerpo(peticion)
        if set(cuerpo) != {"habilitado"} or not isinstance(cuerpo.get("habilitado"), bool):
            return JSONResponse({"detalle": "envía únicamente el booleano «habilitado»"}, status_code=400)
        if configuracion is None:
            return mantenimiento("no se puede guardar la configuración curricular")
        try:
            return _respuesta(configuracion.cambiar_nodo(nodo, cuerpo["habilitado"], sujeto_de(datos)))
        except (AlmacenNoConfigurado, AlmacenNoDisponible, RuntimeError):
            return mantenimiento("no se puede guardar la configuración curricular")

    @router.patch("/api/sondeos/configuracion/umbral")
    async def cambiar_umbral(peticion: Request):
        datos, negativa = _investigador(peticion)
        if negativa is not None:
            return negativa
        cuerpo = await json_del_cuerpo(peticion)
        valor = cuerpo.get("umbral_intentos")
        if set(cuerpo) != {"umbral_intentos"} or type(valor) is not int or valor not in (1, 2):
            return JSONResponse({"detalle": "el umbral debe ser 1 o 2"}, status_code=400)
        if configuracion is None:
            return mantenimiento("no se puede guardar la configuración curricular")
        try:
            return _respuesta(configuracion.cambiar_umbral(valor, sujeto_de(datos)))
        except (AlmacenNoConfigurado, AlmacenNoDisponible, RuntimeError):
            return mantenimiento("no se puede guardar la configuración curricular")

    return router
