from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.instrumentacion import SIN_INSTRUMENTAR, Instrumentador
from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, mantenimiento, requerir_rol
from adaptadores.entrantes.http.rutas.puerta_de_supresion import respuesta_de_supresion
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from adaptadores.salientes.informes.pdf_ficha_estudiante import generar_ficha_estudiante
from adaptadores.salientes.informes.pdf_sesion_clase import (
    armar_reporte,
    generar_pdf,
    parametros_reporte,
)
from dominio.kpi.consulta import ConsultaKPI
from dominio.kpi.contratos import Alcance, Periodo
from dominio.modelo.identidad import IdentidadInvalida
from dominio.modelo.oferta_academica import OfertaAcademicaInvalida
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible, EscrituraRechazada
from dominio.puertos.gobierno import SupresionEnCurso

if TYPE_CHECKING:
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.analitica_docente import PuertoAnaliticaDocente
    from dominio.puertos.clases import PuertoClases

def _instante(valor: str | None, predeterminado: datetime) -> datetime | None:
    if not valor:
        return predeterminado
    try:
        instante = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    return instante if instante.tzinfo is not None else instante.replace(tzinfo=UTC)

def _pagina_solicitada(peticion: Request) -> int | None:
    try:
        pagina = int(peticion.query_params.get("pagina") or "1")
    except ValueError:
        return None
    return pagina if 1 <= pagina <= 1_000_000 else None

def crear_router(
    sesiones: Sesiones,
    analitica: PuertoAnaliticaDocente,
    puerta: PuertaDeSupresion,
    clases: PuertoClases,
    instrumentador: Instrumentador = SIN_INSTRUMENTAR,
    calculo_kpi=None,
) -> APIRouter:
    router = APIRouter()

    def _autorizar(peticion: Request) -> tuple[dict | None, Response | None]:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return None, error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        congelada = puerta.negativa(sujeto_de(datos))
        return datos, congelada

    @router.get("/api/grupo/estudiantes")
    def directorio_de_estudiantes(peticion: Request) -> Response:
        datos, error = _autorizar(peticion)
        if error is not None:
            return error
        pagina = _pagina_solicitada(peticion)
        if pagina is None:
            return JSONResponse({"detalle": "página no válida"}, status_code=400)
        try:
            cuerpo = analitica.directorio_de_estudiantes(
                sujeto_de(datos), pagina, 10
            )
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("el directorio de estudiantes no está disponible")
        return JSONResponse(cuerpo)

    @router.get("/api/contexto-curricular")
    def contexto(peticion: Request) -> Response:
        datos, error = _autorizar(peticion)
        if error is not None:
            return error
        clase = (peticion.query_params.get("clase") or "").strip()
        if not clase:
            return JSONResponse({"detalle": "elige una clase"}, status_code=400)
        try:
            vigente = clases.contexto_curricular(clase, sujeto_de(datos))
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("el contexto curricular no está disponible en este momento")
        if vigente is None:
            return JSONResponse({"detalle": "clase no encontrada o ajena"}, status_code=404)
        return JSONResponse(vigente.como_json())

    @router.put("/api/contexto-curricular")
    async def guardar_contexto(peticion: Request) -> Response:
        datos, error = _autorizar(peticion)
        if error is not None:
            return error
        cuerpo = await json_del_cuerpo(peticion)
        clase = str(cuerpo.get("clase") or "").strip()
        unidad = str(cuerpo.get("unidad") or "").strip()
        notacion = str(cuerpo.get("notacion") or "sen").strip()
        observaciones = str(cuerpo.get("observaciones") or "").strip()
        if not clase:
            return JSONResponse({"detalle": "elige una clase"}, status_code=400)
        if notacion not in {"sen", "sin"}:
            return JSONResponse({"detalle": "notación no válida"}, status_code=400)
        if len(unidad) > 160 or len(observaciones) > 2000:
            return JSONResponse({"detalle": "el contexto supera el tamaño permitido"}, status_code=400)
        try:
            vigente = clases.guardar_contexto_curricular(
                clase, sujeto_de(datos), unidad, notacion, observaciones
            )
        except SupresionEnCurso:
            return respuesta_de_supresion()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("el contexto curricular no está disponible en este momento")
        if vigente is None:
            return JSONResponse({"detalle": "clase no encontrada o ajena"}, status_code=404)

        instrumentador.curricular_actualizado(
            sujeto_de(datos), clase, notacion, bool(unidad)
        )
        return JSONResponse(vigente.como_json())

    @router.get("/api/grupo")
    def grupo(peticion: Request) -> Response:
        datos, error = _autorizar(peticion)
        if error is not None:
            return error
        clase = (peticion.query_params.get("clase") or "").strip()
        if not clase:
            return JSONResponse({"detalle": "elige una clase"}, status_code=400)
        ahora = datetime.now(UTC)
        desde = _instante(peticion.query_params.get("desde"), ahora - timedelta(days=30))
        hasta = _instante(peticion.query_params.get("hasta"), ahora)
        if desde is None or hasta is None or desde >= hasta:
            return JSONResponse({"detalle": "el periodo no es válido"}, status_code=400)
        try:
            resumen = analitica.resumen_de_clase(
                clase, sujeto_de(datos), desde, hasta
            )
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("la analítica docente no está disponible en este momento")
        if resumen is None:
            return JSONResponse(
                {"detalle": "clase no encontrada o ajena"}, status_code=404
            )
        return JSONResponse(resumen)

    @router.get("/api/grupo/{clase}/estudiantes/{estudiante}")
    def ficha_analitica(clase: str, estudiante: str, peticion: Request) -> Response:
        datos, error = _autorizar(peticion)
        if error is not None:
            return error
        ahora = datetime.now(UTC)
        desde = _instante(peticion.query_params.get("desde"), ahora - timedelta(days=30))
        hasta = _instante(peticion.query_params.get("hasta"), ahora)
        if desde is None or hasta is None or desde >= hasta:
            return JSONResponse({"detalle": "el periodo no es válido"}, status_code=400)
        try:
            ficha = analitica.ficha_de_estudiante(
                clase, sujeto_de(datos), estudiante, desde, hasta
            )
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("la ficha analítica no está disponible en este momento")
        if ficha is None:
            return JSONResponse(
                {"detalle": "ficha no encontrada o ajena"}, status_code=404
            )
        if peticion.query_params.get("formato") == "pdf":
            return Response(
                generar_ficha_estudiante(ficha), media_type="application/pdf",
                headers={
                    "Content-Disposition": 'attachment; filename="didaxia-ficha-estudiante.pdf"',
                    "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                },
            )
        return JSONResponse(ficha)

    @router.get("/api/grupo/{clase}/actividad")
    def actividad_de_clase(clase: str, peticion: Request) -> Response:
        datos, error = _autorizar(peticion)
        if error is not None:
            return error
        ahora = datetime.now(UTC)
        desde = _instante(peticion.query_params.get("desde"), ahora - timedelta(days=30))
        hasta = _instante(peticion.query_params.get("hasta"), ahora)
        if desde is None or hasta is None or desde >= hasta:
            return JSONResponse({"detalle": "el periodo no es válido"}, status_code=400)
        metrica = (peticion.query_params.get("metrica") or "turnos").strip()
        busqueda = (peticion.query_params.get("busqueda") or "").strip()[:120]
        solo_activos = peticion.query_params.get("activos") == "1"
        try:
            cuerpo = analitica.actividad_de_clase(
                clase,
                sujeto_de(datos),
                desde,
                hasta,
                metrica=metrica,
                busqueda=busqueda,
                solo_activos=solo_activos,
            )
        except ValueError as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("la actividad de la clase no está disponible")
        if cuerpo is None:
            return JSONResponse({"detalle": "clase no encontrada o ajena"}, status_code=404)
        return JSONResponse(cuerpo)

    def reporte_de_sesion(clase: str, peticion: Request, pdf: bool = False) -> Response:
        datos, error = _autorizar(peticion)
        if error is not None:
            return error
        try:
            desde, hasta, metricas, codigos_kpi = parametros_reporte(
                peticion.query_params.get("desde"), peticion.query_params.get("hasta"),
                peticion.query_params.get("metricas"), peticion.query_params.get("kpis"),
            )
            actividad = analitica.actividad_de_clase(
                clase, sujeto_de(datos), desde, hasta, limite=500,
            )
            if actividad is None:
                return JSONResponse({"detalle": "clase no encontrada o ajena"}, status_code=404)
            if codigos_kpi and calculo_kpi is None:
                return mantenimiento("los KPI oficiales no están disponibles")
            kpi = calculo_kpi.calcular(ConsultaKPI(
                alcance=Alcance.DOCENTE, actor=sujeto_de(datos),
                periodo=Periodo(desde=desde, hasta=hasta), clase=clase,
                codigos=codigos_kpi,
            )) if codigos_kpi else None
            reporte = armar_reporte(actividad, metricas, desde, hasta, kpi)
            if not pdf:
                return JSONResponse(reporte)
            return Response(
                generar_pdf(reporte), media_type="application/pdf",
                headers={
                    "Content-Disposition": 'attachment; filename="didaxia-reporte-sesion.pdf"',
                    "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                },
            )
        except ValueError as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=400)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("el reporte de clase no está disponible")

    @router.get("/api/grupo/{clase}/reporte-sesion")
    def consultar_reporte_de_sesion(clase: str, peticion: Request) -> Response:
        return reporte_de_sesion(clase, peticion)

    @router.get("/api/grupo/{clase}/reporte-sesion.pdf")
    def descargar_reporte_de_sesion(clase: str, peticion: Request) -> Response:
        return reporte_de_sesion(clase, peticion, pdf=True)

    @router.patch("/api/grupo/{clase}/estudiantes/{estudiante}/perfil")
    async def corregir_perfil(clase: str, estudiante: str, peticion: Request) -> Response:
        datos, error = _autorizar(peticion)
        if error is not None:
            return error
        cuerpo = await json_del_cuerpo(peticion)
        try:
            semestre = int(cuerpo.get("semestre"))
        except (TypeError, ValueError):
            return JSONResponse({"detalle": "semestre no admitido"}, status_code=400)
        try:
            perfil = analitica.corregir_perfil_de_estudiante(
                clase,
                sujeto_de(datos),
                estudiante,
                {
                    "facultad": str(cuerpo.get("facultad") or ""),
                    "programa": str(cuerpo.get("programa") or ""),
                    "semestre": semestre,
                },
            )
        except (IdentidadInvalida, OfertaAcademicaInvalida) as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo corregir el perfil académico")
        if perfil is None:
            return JSONResponse({"detalle": "ficha no encontrada o ajena"}, status_code=404)
        return JSONResponse({"perfil": perfil})

    return router
