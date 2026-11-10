"""
kpi.py — Las rutas del catálogo KPI v1.1
=========================================

Cuatro caminos y tres roles.

| ruta | quién | qué devuelve |
|---|---|---|
| `GET /api/kpi/catalogo` | docente | las definiciones que su alcance admite |
| `GET /api/kpi` | docente | los indicadores de **una clase suya** |
| `GET /api/investigacion/kpi/catalogo` | investigador | el catálogo completo |
| `GET /api/investigacion/kpi` | investigador | los indicadores institucionales |

**El estudiante no aparece.** No es que se le filtre: no hay ruta que le
corresponda, y `requerir_rol()` cierra las cuatro. Un estudiante no consulta
indicadores de grupo, ni suyos ni ajenos.

Las dos barreras, y por qué hacen falta las dos
--------------------------------------------------------
1. **El catálogo** decide qué indicadores puede nombrar un alcance. Un docente
   no puede pedir `institucion.*` porque esas definiciones no están en
   `para_alcance(DOCENTE)`, así que no llegan ni al adaptador.
2. **El adaptador** decide de quién son los datos, dentro de la transacción que
   los lee. La primera evita nombrar; la segunda evita leer. Sin la segunda,
   un docente que pasara la clase de otro por la cadena de consulta recibiría
   sus cifras aunque el catálogo estuviera bien.

El periodo, y por qué se rechaza en vez de recortarse
--------------------------------------------------------------
Un periodo invertido o ilegible responde `400`. Recortarlo a un valor por
defecto habría devuelto cifras de un intervalo que nadie pidió, y quien las
leyera creería estar mirando el suyo.


"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento, requerir_rol
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from dominio.kpi import catalogo as cat
from dominio.kpi.consulta import ConsultaKPI
from dominio.kpi.contratos import Alcance, KPIInvalido, Periodo
from dominio.kpi.definiciones import ZONA_HORARIA
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    EscrituraRechazada,
)

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.kpi import PuertoCalculoKPI

#: Ventana por defecto cuando no se pide periodo. Treinta días, igual que el
#: resto de superficies analíticas del sistema: cambiarla sólo aquí habría
#: hecho que dos paneles del mismo curso mostraran ventanas distintas.
DIAS_POR_DEFECTO = 30

#: Tope de códigos por petición. Sin él, una lista larguísima obligaría a
#: recorrer el catálogo entero por cada uno.
TOPE_DE_CODIGOS = 60

ZONA_LOCAL = ZoneInfo(ZONA_HORARIA)


def _instante(valor: str | None, predeterminado: datetime) -> datetime | None:
    if not valor:
        return predeterminado
    try:
        instante = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Una fecha o fecha-hora sin desplazamiento viene de los controles de
    # periodo del navegador. Es una hora civil de Colombia, no UTC.
    return instante if instante.tzinfo is not None else instante.replace(tzinfo=ZONA_LOCAL)


def _periodo(peticion: Request) -> Periodo | None:
    ahora = datetime.now(UTC)
    desde = _instante(
        peticion.query_params.get("desde"), ahora - timedelta(days=DIAS_POR_DEFECTO)
    )
    hasta = _instante(peticion.query_params.get("hasta"), ahora)
    if desde is None or hasta is None:
        return None
    try:
        return Periodo(desde=desde, hasta=hasta)
    except KPIInvalido:
        return None


def _codigos(peticion: Request) -> tuple[str, ...] | None:
    """Los códigos pedidos, o `None` si alguno no existe.

    Un código inexistente se rechaza en vez de ignorarse: quien pide cinco
    indicadores y recibe cuatro sin aviso cree que el quinto no tuvo datos.
    """
    crudo = (peticion.query_params.get("codigos") or "").strip()
    if not crudo:
        return ()
    codigos = tuple(c.strip() for c in crudo.split(",") if c.strip())
    if len(codigos) > TOPE_DE_CODIGOS:
        return None
    if any(cat.buscar(codigo) is None for codigo in codigos):
        return None
    return codigos


def _filtros(peticion: Request) -> dict:
    """Los filtros presentes en la consulta, sin inventar los ausentes.

    Se recogen todos los nombres que el cliente pudo escribir —incluidos los
    que todavía no se pueden honrar— para que `ConsultaKPI` los rechace con su
    motivo. Filtrar aquí los desconocidos los habría hecho desaparecer en
    silencio, que es justo lo que no puede pasar.
    """
    reservados = {"desde", "hasta", "codigos", "clase"}
    return {
        nombre: valor
        for nombre, valor in peticion.query_params.items()
        if nombre not in reservados and valor.strip()
    }


def crear_router(
    sesiones: Sesiones,
    calculo: PuertoCalculoKPI,
    puerta: PuertaDeSupresion,
) -> APIRouter:
    router = APIRouter()

    def _autorizar(peticion: Request, rol: str):
        error = requerir_rol(sesiones, peticion, rol)
        if error is not None:
            return None, error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        return datos, puerta.negativa(sujeto_de(datos))

    def _responder(consulta_valida) -> Response:
        try:
            return JSONResponse(calculo.calcular(consulta_valida))
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("el catálogo KPI no está disponible en este momento")

    def _construir(peticion: Request, alcance: Alcance, actor: str, clase: str | None):
        periodo = _periodo(peticion)
        if periodo is None:
            return None, JSONResponse(
                {"detalle": "el periodo no es válido"}, status_code=400
            )
        codigos = _codigos(peticion)
        if codigos is None:
            return None, JSONResponse(
                {"detalle": "la lista de códigos no es válida"}, status_code=400
            )
        try:
            consulta = ConsultaKPI(
                alcance=alcance,
                actor=actor,
                periodo=periodo,
                clase=clase,
                filtros=_filtros(peticion),
                codigos=codigos,
            )
        except KPIInvalido as error:
            return None, JSONResponse({"detalle": str(error)}, status_code=400)
        return consulta, None

    # ── Docente ─────────────────────────────────────────────────────────────

    @router.get("/api/kpi/catalogo")
    def catalogo_docente(peticion: Request) -> Response:
        _datos, error = _autorizar(peticion, "docente")
        if error is not None:
            return error
        return JSONResponse(cat.como_json(Alcance.DOCENTE))

    @router.get("/api/kpi")
    def kpi_docente(peticion: Request) -> Response:
        """Los indicadores de una clase del docente autenticado.

        La clase es obligatoria: sin ella habría que decidir qué significa el
        agregado de varias clases a la vez —qué población, qué denominador— y
        esa decisión no está tomada. Se exige elegir en vez de inventar la
        unión.
        """
        datos, error = _autorizar(peticion, "docente")
        if error is not None:
            return error
        clase = (peticion.query_params.get("clase") or "").strip()
        if not clase:
            return JSONResponse({"detalle": "elige una clase"}, status_code=400)
        consulta, invalida = _construir(peticion, Alcance.DOCENTE, sujeto_de(datos), clase)
        if invalida is not None:
            return invalida
        return _responder(consulta)

    # ── Investigador ────────────────────────────────────────────────────────

    @router.get("/api/investigacion/kpi/catalogo")
    def catalogo_institucional(peticion: Request) -> Response:
        _datos, error = _autorizar(peticion, "investigador")
        if error is not None:
            return error
        return JSONResponse(cat.como_json(Alcance.INSTITUCIONAL))

    @router.get("/api/investigacion/kpi")
    def kpi_institucional(peticion: Request) -> Response:
        datos, error = _autorizar(peticion, "investigador")
        if error is not None:
            return error
        clase = (peticion.query_params.get("clase") or "").strip() or None
        consulta, invalida = _construir(
            peticion, Alcance.INSTITUCIONAL, sujeto_de(datos), clase
        )
        if invalida is not None:
            return invalida
        return _responder(consulta)

    return router
