from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, requerir_sesion
from adaptadores.entrantes.http.sesiones import Sesiones
from adaptadores.salientes.simbolico.graficadora_aislada import preparar_curvas_acotadas


def crear_router(sesiones: Sesiones) -> APIRouter:
    router = APIRouter()

    @router.post("/api/graficadora/curvas")
    async def curvas(peticion: Request) -> JSONResponse:
        _datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        cuerpo = await json_del_cuerpo(peticion)
        try:
            preparadas = await run_in_threadpool(preparar_curvas_acotadas, cuerpo.get("curvas"))
            return JSONResponse({"curvas": preparadas})
        except ValueError as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)

    return router
