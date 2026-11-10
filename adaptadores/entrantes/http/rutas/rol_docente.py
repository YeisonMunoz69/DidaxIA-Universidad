from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.docentes import RegistroDeDocentes
from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, requerir_lista_manual
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de

if TYPE_CHECKING:
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion

def crear_router(
    sesiones: Sesiones,
    registro_docentes: RegistroDeDocentes,
    puerta: PuertaDeSupresion,
) -> APIRouter:

    router = APIRouter()

    def _congelada(peticion: Request) -> Response | None:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return None
        return puerta.negativa(sujeto_de(datos))

    @router.post("/api/rol-docente/solicitar")
    def solicitar_rol_docente(peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        correo = datos.get("correo") or ""
        if not correo:

            return JSONResponse(
                {"detalle": "requiere una sesión autenticada con Google"}, status_code=403
            )
        congelada = _congelada(peticion)
        if congelada is not None:
            return congelada
        solicitud = registro_docentes.solicitar(correo)
        return JSONResponse(solicitud.como_elemento(), status_code=201)

    @router.get("/api/rol-docente/solicitudes")
    def listar_solicitudes_rol_docente(peticion: Request) -> Response:
        error = requerir_lista_manual(sesiones, registro_docentes, peticion)
        if error is not None:
            return error
        congelada = _congelada(peticion)
        if congelada is not None:
            return congelada
        return JSONResponse([s.como_elemento() for s in registro_docentes.listar_pendientes()])

    @router.post("/api/rol-docente/solicitudes/{identificador}/aprobar")
    def aprobar_solicitud_rol_docente(identificador: str, peticion: Request) -> Response:
        error = requerir_lista_manual(sesiones, registro_docentes, peticion)
        if error is not None:
            return error
        congelada = _congelada(peticion)
        if congelada is not None:
            return congelada
        if not registro_docentes.aprobar(identificador):
            return JSONResponse({"detalle": "no encontrada o ya resuelta"}, status_code=404)
        return Response(status_code=204)

    @router.post("/api/rol-docente/solicitudes/{identificador}/rechazar")
    async def rechazar_solicitud_rol_docente(identificador: str, peticion: Request) -> Response:
        error = requerir_lista_manual(sesiones, registro_docentes, peticion)
        if error is not None:
            return error
        congelada = _congelada(peticion)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        motivo = str(cuerpo.get("motivo") or "").strip()
        if not motivo:
            return JSONResponse({"detalle": "el rechazo exige un motivo"}, status_code=400)
        if not registro_docentes.rechazar(identificador, motivo):
            return JSONResponse({"detalle": "no encontrada o ya resuelta"}, status_code=404)
        return Response(status_code=204)

    @router.post("/api/rol-docente/solicitudes/{identificador}/pedir-mas-informacion")
    async def pedir_mas_informacion_rol_docente(
        identificador: str, peticion: Request
    ) -> Response:
        error = requerir_lista_manual(sesiones, registro_docentes, peticion)
        if error is not None:
            return error
        congelada = _congelada(peticion)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        mensaje = str(cuerpo.get("mensaje") or "").strip()
        if not mensaje:
            return JSONResponse(
                {"detalle": "falta el mensaje para quien solicitó"}, status_code=400
            )
        if not registro_docentes.pedir_mas_informacion(identificador, mensaje):
            return JSONResponse({"detalle": "no encontrada o ya resuelta"}, status_code=404)
        return Response(status_code=204)

    return router
