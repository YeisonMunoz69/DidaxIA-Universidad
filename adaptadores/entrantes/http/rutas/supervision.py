"""
supervision.py — La cola de revisión del docente · `RU-12`
====================================================================

Listar lo pendiente y las **tres acciones distintas** que `RU-12` fija:
aprobar, editar, rechazar. No hay «aprobar todo», ni aquí ni en el almacén —
la ausencia es la decisión, y `supervision.py` no ofrece un método que la
deshaga por atrás.

Las cuatro exigen rol docente. Aquí SÍ viajan los campos que el árbol del
estudiante tiene prohibidos (`08-Contrato-del-Turno.md` §9): la frontera es
estudiante frente a no-estudiante, y `requerir_rol` es quien la impone.

⚠️ No confundir con el almacén. Desde la Fase 2 · sesión 3, el contrato es
`dominio/puertos/supervision.py::PuertoColaDeRevision` y las dos
implementaciones viven en `adaptadores/salientes/registro/`
—`cola_revision_memoria.py` y `cola_revision_db.py`—. Estas rutas dependen del
puerto y no saben cuál recibieron. Ver `rutas/__init__.py`.


"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.instrumentacion import (
    SIN_INSTRUMENTAR,
    Instrumentador,
    SelloDelTurno,
)
from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, requerir_rol
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from dominio.modelo.contexto_de_uso import ContextoDeUso

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.clases import PuertoClases
    from dominio.puertos.supervision import PuertoColaDeRevision


def crear_router(
    sesiones: Sesiones,
    cola: PuertoColaDeRevision,
    puerta: PuertaDeSupresion,
    clases_almacen: PuertoClases | None = None,
    instrumentador: Instrumentador = SIN_INSTRUMENTAR,
) -> APIRouter:
    """La cola de revisión docente, con la puerta de `EQ-022` en las cuatro.

    ⚠️ **Listar también**, y es la corrección de esta tanda. Estaba abierto por
    «consultar es un derecho», y no lo es: el derecho del titular es ver **sus**
    datos, no la cola de trabajo de un docente. Es uso del producto.
    """
    router = APIRouter()

    def _congelada(peticion: Request) -> Response | None:
        """La negativa si el ACTOR tiene su propio trámite abierto, o `None`.

        ⚠️ **El actor, no la persona afectada.** `cola_revision` no identifica al
        titular de cada elemento —ver el informe de esta corrección—, así que
        aquí no se puede comprobar nada sobre él. Lo que sí se comprueba, y es lo
        que `ESTADO-ACTUAL.md` §10.2 pide, es que quien ejecuta la acción no
        tenga su propia cuenta congelada.
        """
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return None  # sin sesión ya respondió `requerir_rol()`
        return puerta.negativa(sujeto_de(datos))

    def _alcance_docente(peticion: Request) -> tuple[str, tuple[str, ...]]:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        actor = sujeto_de(datos)
        if clases_almacen is None:
            return actor, ()
        return actor, tuple(c.identificador for c in clases_almacen.mias(actor))

    def _anotar_decision(actor: str, identificador: str, decision: str) -> None:
        """Fase 8 · la decisión del docente, medida sin tocar la cola.

        El sujeto del evento es el **docente que decide**, no el estudiante del
        elemento: lo que se mide aquí es el trabajo de supervisión, y atribuirlo
        al estudiante convertiría la carga del docente en actividad de la
        persona supervisada.

        Sin clase: `cola_revision` la admite nula y el elemento puede no
        tenerla. Un evento sin clase es legítimo; inventarle una a partir de
        las del docente sería atribuir un hecho a un curso que quizá no es el
        suyo.
        """
        instrumentador.supervision_decidida(
            SelloDelTurno(
                sujeto=actor,
                conversacion="",
                turno=identificador,
                contexto_de_uso=ContextoDeUso.CONSULTA_PROFESIONAL,
            ),
            item=identificador,
            decision=decision,
        )


    @router.get("/api/supervision")
    def listar_supervision(peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        congelada = _congelada(peticion)
        if congelada is not None:
            return congelada
        q = peticion.query_params
        actor, permitidas = _alcance_docente(peticion)
        del actor
        clase_pedida = q.get("clase", "")
        if clases_almacen is not None and clase_pedida and clase_pedida not in permitidas:
            return JSONResponse({"detalle": "clase no encontrada o ajena"}, status_code=404)
        if clases_almacen is not None and not permitidas:
            return JSONResponse({"elementos": [], "total": 0})
        tope = q.get("tope")
        desde = q.get("desde")
        elementos = cola.listar_pendientes(
            urgencia=q.get("urgencia", ""), clase=q.get("clase", ""), tipo=q.get("tipo", ""),
            tope=int(tope) if tope and tope.isdigit() else None,
            desde=int(desde) if desde and desde.isdigit() else 0,
            clases_permitidas=permitidas,
        )
        return JSONResponse({
            "elementos": [e.como_elemento() for e in elementos],
            "total": cola.total_pendientes(
                q.get("urgencia", ""), q.get("clase", ""), q.get("tipo", ""),
                clases_permitidas=permitidas,
            ),
        })

    @router.post("/api/supervision/{identificador}/aprobar")
    def aprobar_supervision(identificador: str, peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        congelada = _congelada(peticion)
        if congelada is not None:
            return congelada
        actor, permitidas = _alcance_docente(peticion)
        if clases_almacen is not None and not permitidas:
            return JSONResponse({"detalle": "no encontrado o ya resuelto"}, status_code=404)
        if not cola.aprobar(identificador, actor, permitidas):
            return JSONResponse({"detalle": "no encontrado o ya resuelto"}, status_code=404)
        _anotar_decision(actor, identificador, "aprobado")
        return Response(status_code=204)

    @router.post("/api/supervision/{identificador}/editar")
    async def editar_supervision(identificador: str, peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        congelada = _congelada(peticion)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        texto = str(cuerpo.get("texto") or "").strip()
        if not texto:
            return JSONResponse({"detalle": "falta el texto corregido"}, status_code=400)
        actor, permitidas = _alcance_docente(peticion)
        if clases_almacen is not None and not permitidas:
            return JSONResponse({"detalle": "no encontrado o ya resuelto"}, status_code=404)
        if not cola.editar(identificador, texto, actor, permitidas):
            return JSONResponse({"detalle": "no encontrado o ya resuelto"}, status_code=404)
        _anotar_decision(actor, identificador, "editado")
        return Response(status_code=204)

    @router.post("/api/supervision/{identificador}/rechazar")
    async def rechazar_supervision(identificador: str, peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        congelada = _congelada(peticion)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        # `motivo` se admite durante la transición para clientes ya abiertos;
        # el contrato nuevo lo llama `texto` porque llega al estudiante como
        # una corrección, no queda escondido como una nota administrativa.
        motivo = str(cuerpo.get("texto") or cuerpo.get("motivo") or "").strip()
        if not motivo:
            return JSONResponse(
                {"detalle": "el rechazo exige una respuesta corregida"}, status_code=400
            )
        actor, permitidas = _alcance_docente(peticion)
        if clases_almacen is not None and not permitidas:
            return JSONResponse({"detalle": "no encontrado o ya resuelto"}, status_code=404)
        if not cola.rechazar(identificador, motivo, actor, permitidas):
            return JSONResponse({"detalle": "no encontrado o ya resuelto"}, status_code=404)
        _anotar_decision(actor, identificador, "rechazado")
        return Response(status_code=204)

    @router.get("/api/supervision/mis-aclaraciones")
    def aclaraciones_del_hilo(peticion: Request) -> Response:
        """Sólo el titular puede recuperar las aclaraciones de su conversación."""
        error = requerir_rol(sesiones, peticion, "estudiante")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        congelada = _congelada(peticion)
        if congelada is not None:
            return congelada
        sesion = (peticion.query_params.get("sesion") or "").strip()
        if not sesion:
            return JSONResponse({"detalle": "falta la conversación"}, status_code=400)
        aclaraciones = cola.listar_aclaraciones(sujeto_de(datos), sesion)
        return JSONResponse({"elementos": [a.como_elemento() for a in aclaraciones]})

    return router
