from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from psycopg import Error as ErrorPostgres
from pydantic import BaseModel, ConfigDict, Field, field_validator

from adaptadores.entrantes.http.rutas.comun import mantenimiento, requerir_rol
from adaptadores.entrantes.http.sesiones import COOKIE, sujeto_de
from adaptadores.salientes.registro.trabajos_relectura import ConflictoRelectura
from dominio.puertos.almacen import AlmacenNoConfigurado, EscrituraRechazada


class AlcanceRelectura(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clase: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    desde: datetime | None = None
    hasta: datetime | None = None

class ConfirmacionRelectura(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmar: Literal[True]
    maximo_llamadas: Annotated[int, Field(strict=True, ge=1, le=200)]

    @field_validator("confirmar", mode="before")
    @classmethod
    def confirmacion_explicita(cls, valor):
        if valor is not True:
            raise ValueError("se requiere confirmación explícita")
        return valor

def crear_router(sesiones, trabajos, puerta):
    router = APIRouter()

    def responder(peticion, accion):
        error = requerir_rol(sesiones, peticion, "investigador")
        if error is not None:
            return error
        actor = sujeto_de(sesiones.leer(peticion.cookies.get(COOKIE)))
        error = puerta.negativa(actor)
        if error is not None:
            return error
        try:
            return accion(actor)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except ConflictoRelectura as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=409)
        except ValueError as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=400)
        except (AlmacenNoConfigurado, ErrorPostgres):
            return mantenimiento("la relectura no está disponible en este momento")

    @router.post("/api/investigacion/factores/relectura/vista-previa")
    def prever(peticion: Request, alcance: AlcanceRelectura):
        return responder(peticion, lambda actor: trabajos.prever(actor, **alcance.model_dump()))

    @router.post("/api/investigacion/factores/relectura/trabajos/{identificador}")
    def confirmar(
        peticion: Request,
        identificador: UUID,
        datos: ConfirmacionRelectura,
        tareas: BackgroundTasks,
    ):
        def accion(actor):
            trabajo, nuevo = trabajos.confirmar(
                actor, str(identificador), maximo_llamadas=datos.maximo_llamadas
            )
            if nuevo:
                tareas.add_task(trabajos.procesar, actor, str(identificador))
            return JSONResponse(trabajo, status_code=202)

        return responder(peticion, accion)

    @router.get("/api/investigacion/factores/relectura/ultimo")
    def ultimo(peticion: Request):
        return responder(peticion, lambda actor: dict(trabajo=trabajos.consultar(actor)))

    @router.get("/api/investigacion/factores/relectura/trabajos/{identificador}")
    def consultar(peticion: Request, identificador: UUID):
        def accion(actor):
            trabajo = trabajos.consultar(actor, str(identificador))
            return (
                trabajo
                if trabajo
                else JSONResponse({"detalle": "trabajo no disponible"}, status_code=404)
            )

        return responder(peticion, accion)

    return router
