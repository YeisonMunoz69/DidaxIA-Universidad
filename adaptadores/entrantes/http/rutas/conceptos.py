"""
conceptos.py — El banco de conceptos · `DD-13`
========================================================

Dos rutas, y las únicas del sistema que **no piden sesión**: es material del
curso, no un dato del estudiante. Pedir sesión aquí convertiría una
explicación pública en algo que hay que autorizar para leer.

Se sirven a los **dos** árboles, y por eso no viven ni en el del estudiante ni
en el del docente.


"""

from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from adaptadores.salientes.conceptos import BancoDeConceptos


def crear_router(banco: BancoDeConceptos) -> APIRouter:
    router = APIRouter()

    @router.get("/api/conceptos")
    def listar_conceptos() -> JSONResponse:
        return JSONResponse([c.como_resumen() for c in banco.listar()])

    @router.get("/api/conceptos/{identificador}")
    def ficha_de_concepto(identificador: str) -> Response:
        ficha = banco.ficha(identificador)
        if ficha is None:
            return JSONResponse({"detalle": "no hay un concepto con ese id"}, status_code=404)
        return JSONResponse(ficha)

    return router
