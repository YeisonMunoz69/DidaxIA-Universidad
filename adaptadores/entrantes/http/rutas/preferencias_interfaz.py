from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, mantenimiento, requerir_sesion
from adaptadores.entrantes.http.sesiones import sujeto_de
from dominio.modelo.preferencias_interfaz import RevisionDesactualizada, validar_cambios
from dominio.puertos.almacen import ErrorDeAlmacen
from dominio.puertos.gobierno import SupresionEnCurso


def crear_router(sesiones, repositorio, puerta):
    router = APIRouter()

    @router.get("/api/preferencias-interfaz")
    def consultar(peticion: Request):
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if repositorio is None:
            return mantenimiento("no se pueden recuperar los ajustes de la cuenta")
        try:
            return repositorio.consultar(sujeto_de(datos))
        except ErrorDeAlmacen:
            return mantenimiento("no se pudieron recuperar los ajustes de la cuenta")

    @router.patch("/api/preferencias-interfaz")
    async def guardar(peticion: Request):
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        sujeto = sujeto_de(datos)
        if (negativa := puerta.negativa(sujeto)) is not None:
            return negativa
        cuerpo = await json_del_cuerpo(peticion)
        try:
            if not isinstance(cuerpo, dict) or set(cuerpo) != {"cambios", "revision"} or type(cuerpo["revision"]) is not int or cuerpo["revision"] < 0:
                raise ValueError("envía cambios y su revisión")
            validar_cambios(cuerpo["cambios"])
        except ValueError as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=400)
        if repositorio is None:
            return mantenimiento("no se pueden guardar los ajustes de la cuenta")
        try:
            return repositorio.guardar(sujeto, cuerpo["cambios"], cuerpo["revision"])
        except RevisionDesactualizada:
            return JSONResponse({"detalle": "Los ajustes cambiaron en otro dispositivo. Recupera su revisión y vuelve a guardar."}, status_code=409)
        except SupresionEnCurso:
            return JSONResponse({"detalle": "hay un trámite de supresión en curso"}, status_code=409)
        except ErrorDeAlmacen:
            return mantenimiento("no se pudieron guardar los ajustes de la cuenta")

    return router
