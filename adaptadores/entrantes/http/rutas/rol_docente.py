"""
rol_docente.py — Pedir y resolver el rol docente · `D-16` opción C · `PM-B15` B
=========================================================================================

Cinco rutas: una para pedir el rol y cuatro para resolverlo, con las **tres
acciones distintas** que `RU-12` fija —aprobar, rechazar, pedir más
información—, nunca «aprobar todo».

Quién puede resolver: `requerir_lista_manual`, NO `requerir_rol`
------------------------------------------------------------------------
Y la diferencia es la razón de que esa guarda exista aparte. Una cuenta que
llegó a `docente` **por la cola de aprobación** es docente para todo lo demás
—crea clases, ve la cola de supervisión— pero **no hereda permiso para
resolver la cola de otros**: eso sigue siendo solo de quien está en la lista a
mano. `docentes.py` lo explica entero; aquí solo se aplica.

Pedir el rol exige identidad verificada, y no es una comprobación de más:
sin haber entrado por `/api/sesion/google` no hay correo del que colgar la
solicitud, y el registro es por correo.


"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.docentes import RegistroDeDocentes
from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, requerir_lista_manual
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion


def crear_router(
    sesiones: Sesiones,
    registro_docentes: RegistroDeDocentes,
    puerta: PuertaDeSupresion,
) -> APIRouter:
    """Pedir el rol y resolver solicitudes, con la puerta de `EQ-022`.

    ⚠️ **Se aplica también a quien resuelve, no sólo a quien pide.** Aprobar,
    rechazar o pedir más información son acciones de producto de una cuenta, y
    `ESTADO-ACTUAL.md` §10.2 las suspende mientras su propio trámite esté
    abierto. Quien tiene la supresión en curso es el ACTOR; la persona sobre la
    que decide no entra en esta comprobación.
    """
    router = APIRouter()

    def _congelada(peticion: Request) -> Response | None:
        """La negativa si el ACTOR tiene su trámite abierto, o `None`.

        Lee la sesión otra vez en vez de recibir `datos`: las rutas de resolución
        pasan por `requerir_lista_manual()`, que no devuelve la sesión, y
        rehacerla aquí es más barato que cambiar aquella firma para todos.
        """
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return None  # sin sesión ya respondió quien correspondía
        return puerta.negativa(sujeto_de(datos))

    @router.post("/api/rol-docente/solicitar")
    def solicitar_rol_docente(peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        correo = datos.get("correo") or ""
        if not correo:
            # Sin identidad verificada no hay correo del que colgar la
            # solicitud — pedir el rol exige haber entrado por
            # `/api/sesion/google` primero.
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
