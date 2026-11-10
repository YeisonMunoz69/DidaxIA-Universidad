"""Agregados institucionales auditados para el rol investigador."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.investigadores import es_propietario
from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, mantenimiento, requerir_rol
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
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    ErrorDeAlmacen,
    EscrituraRechazada,
    ReferenciaDesconocida,
)

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.analitica_docente import PuertoAnaliticaDocente
    from dominio.puertos.roles import PuertoAsignacionDeRoles


def _instante(valor: str | None, predeterminado: datetime) -> datetime | None:
    if not valor:
        return predeterminado
    try:
        instante = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    return instante if instante.tzinfo else instante.replace(tzinfo=UTC)


def _pagina_solicitada(peticion: Request) -> int | None:
    try:
        pagina = int(peticion.query_params.get("pagina") or "1")
    except ValueError:
        return None
    return pagina if 1 <= pagina <= 1_000_000 else None


def crear_router(  # noqa: PLR0913 — factoría del borde con dependencias explícitas
    sesiones: Sesiones,
    analitica: PuertoAnaliticaDocente,
    puerta: PuertaDeSupresion,
    roles: PuertoAsignacionDeRoles | None = None,
    identidades=None,
    fotos=None,
    calculo_kpi=None,
    consumo_ia=None,
) -> APIRouter:
    router = APIRouter()

    def _autorizar_y_periodo(peticion: Request):
        error = requerir_rol(sesiones, peticion, "investigador")
        if error is not None:
            return None, None, None, error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        congelada = puerta.negativa(sujeto_de(datos))
        if congelada is not None:
            return None, None, None, congelada
        ahora = datetime.now(UTC)
        desde = _instante(peticion.query_params.get("desde"), ahora - timedelta(days=30))
        hasta = _instante(peticion.query_params.get("hasta"), ahora)
        if desde is None or hasta is None or desde >= hasta:
            return None, None, None, JSONResponse(
                {"detalle": "el periodo no es válido"}, status_code=400
            )
        return datos, desde, hasta, None

    @router.get("/api/investigacion/resumen")
    def resumen(peticion: Request) -> Response:
        datos, desde, hasta, error = _autorizar_y_periodo(peticion)
        if error is not None:
            return error
        try:
            cuerpo = analitica.resumen_institucional(
                sujeto_de(datos), desde, hasta
            )
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("la analítica institucional no está disponible")
        return JSONResponse(cuerpo)

    @router.get("/api/investigacion/estudiantes")
    def directorio_de_estudiantes(peticion: Request) -> Response:
        """Directorio institucional paginado, autorizado y auditado."""
        datos, _desde, _hasta, error = _autorizar_y_periodo(peticion)
        if error is not None:
            return error
        pagina = _pagina_solicitada(peticion)
        if pagina is None:
            return JSONResponse({"detalle": "página no válida"}, status_code=400)
        buscar = peticion.query_params.get("buscar", "").strip()
        if len(buscar) > 200:
            return JSONResponse({"detalle": "la búsqueda admite hasta 200 caracteres"}, status_code=400)
        try:
            cuerpo = analitica.directorio_de_estudiantes(
                sujeto_de(datos), pagina, 10, alcance_institucional=True,
                **({"buscar": buscar} if buscar else {}),
            )
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("el directorio institucional no está disponible")
        return JSONResponse(cuerpo)

    @router.get("/api/investigacion/cursos/{clase}")
    def detalle_de_clase(clase: str, peticion: Request) -> Response:
        datos, desde, hasta, error = _autorizar_y_periodo(peticion)
        if error is not None:
            return error
        try:
            cuerpo = analitica.detalle_institucional_de_clase(
                clase, sujeto_de(datos), desde, hasta
            )
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("el detalle institucional no está disponible")
        if cuerpo is None:
            return JSONResponse({"detalle": "curso no encontrado"}, status_code=404)
        return JSONResponse(cuerpo)

    @router.get("/api/investigacion/cursos/{clase}/estudiantes/{estudiante}")
    def ficha_de_estudiante(clase: str, estudiante: str, peticion: Request) -> Response:
        datos, desde, hasta, error = _autorizar_y_periodo(peticion)
        if error is not None:
            return error
        try:
            cuerpo = analitica.ficha_institucional_de_estudiante(
                clase, sujeto_de(datos), estudiante, desde, hasta
            )
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("la ficha institucional no está disponible")
        if cuerpo is None:
            return JSONResponse({"detalle": "ficha no encontrada"}, status_code=404)
        if peticion.query_params.get("formato") == "pdf":
            return Response(
                generar_ficha_estudiante(cuerpo), media_type="application/pdf",
                headers={
                    "Content-Disposition": 'attachment; filename="didaxia-ficha-estudiante.pdf"',
                    "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                },
            )
        return JSONResponse(cuerpo)

    @router.get("/api/investigacion/cursos/{clase}/actividad")
    def actividad_de_clase(clase: str, peticion: Request) -> Response:
        datos, desde, hasta, error = _autorizar_y_periodo(peticion)
        if error is not None:
            return error
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
                alcance_institucional=True,
            )
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except ValueError as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("la actividad de la clase no está disponible")
        if cuerpo is None:
            return JSONResponse({"detalle": "curso no encontrado"}, status_code=404)
        return JSONResponse(cuerpo)

    def reporte_de_sesion(clase: str, peticion: Request, pdf: bool = False) -> Response:
        datos, _desde, _hasta, error = _autorizar_y_periodo(peticion)
        if error is not None:
            return error
        try:
            desde, hasta, metricas, codigos_kpi = parametros_reporte(
                peticion.query_params.get("desde"), peticion.query_params.get("hasta"),
                peticion.query_params.get("metricas"), peticion.query_params.get("kpis"),
            )
            actividad = analitica.actividad_de_clase(
                clase, sujeto_de(datos), desde, hasta, limite=500,
                alcance_institucional=True,
            )
            if actividad is None:
                return JSONResponse({"detalle": "curso no encontrado"}, status_code=404)
            if codigos_kpi and calculo_kpi is None:
                return mantenimiento("los KPI oficiales no están disponibles")
            kpi = calculo_kpi.calcular(ConsultaKPI(
                alcance=Alcance.INSTITUCIONAL, actor=sujeto_de(datos),
                periodo=Periodo(desde=desde, hasta=hasta), clase=clase,
                codigos=codigos_kpi,
            )) if codigos_kpi else None
            incluir_ia = peticion.query_params.get("ia") == "1"
            if incluir_ia and consumo_ia is None:
                return mantenimiento("el consumo institucional de IA no está disponible")
            ia = consumo_ia.resumen_deepseek(sujeto_de(datos), desde, hasta) if incluir_ia else None
            reporte = armar_reporte(actividad, metricas, desde, hasta, kpi, ia)
            if not pdf:
                return JSONResponse(reporte)
            return Response(
                generar_pdf(reporte), media_type="application/pdf",
                headers={
                    "Content-Disposition": 'attachment; filename="didaxia-reporte-sesion.pdf"',
                    "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                },
            )
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except ValueError as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=400)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("el reporte de clase no está disponible")

    @router.get("/api/investigacion/cursos/{clase}/reporte-sesion")
    def consultar_reporte_de_sesion(clase: str, peticion: Request) -> Response:
        return reporte_de_sesion(clase, peticion)

    @router.get("/api/investigacion/cursos/{clase}/reporte-sesion.pdf")
    def descargar_reporte_de_sesion(clase: str, peticion: Request) -> Response:
        return reporte_de_sesion(clase, peticion, pdf=True)

    @router.patch("/api/investigacion/cursos/{clase}/estudiantes/{estudiante}/perfil")
    async def corregir_perfil(clase: str, estudiante: str, peticion: Request) -> Response:
        datos, _desde, _hasta, error = _autorizar_y_periodo(peticion)
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
                alcance_institucional=True,
            )
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (IdentidadInvalida, OfertaAcademicaInvalida) as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo corregir el perfil académico")
        if perfil is None:
            return JSONResponse({"detalle": "ficha no encontrada"}, status_code=404)
        return JSONResponse({"perfil": perfil})

    @router.post("/api/investigacion/cursos/{clase}/estudiantes/{estudiante}/rectificacion-edad")
    async def rectificar_edad(clase: str, estudiante: str, peticion: Request) -> Response:
        datos, _desde, _hasta, error = _autorizar_y_periodo(peticion)
        if error is not None:
            return error
        cuerpo = await json_del_cuerpo(peticion)
        if isinstance(cuerpo.get("edad_nueva"), bool):
            return JSONResponse({"detalle": "edad nueva no admitida"}, status_code=400)
        try:
            edad = int(cuerpo.get("edad_nueva"))
        except (TypeError, ValueError):
            return JSONResponse({"detalle": "edad nueva no admitida"}, status_code=400)
        try:
            rectificacion = analitica.rectificar_edad(
                clase, sujeto_de(datos), estudiante, edad, str(cuerpo.get("motivo") or "")
            )
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (IdentidadInvalida, ValueError) as error_edad:
            return JSONResponse({"detalle": str(error_edad)}, status_code=400)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo registrar la rectificación")
        if rectificacion is None:
            return JSONResponse({"detalle": "ficha no encontrada"}, status_code=404)
        return JSONResponse({"rectificacion": rectificacion}, status_code=201)

    @router.get("/api/investigacion/equipo")
    def equipo(peticion: Request) -> Response:
        datos, _desde, _hasta, error = _autorizar_y_periodo(peticion)
        if error is not None:
            return error
        if roles is None:
            return mantenimiento("el gobierno del equipo institucional no está disponible")
        try:
            personas = roles.directorio_institucional(
                sujeto_de(datos), peticion.query_params.get("buscar") or "",
                peticion.query_params.get("pertenencia") or "todas",
                peticion.query_params.get("clase") or "",
            )
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except ValueError as error_filtro:
            return JSONResponse({"detalle": str(error_filtro)}, status_code=400)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo consultar el equipo institucional")
        return JSONResponse(
            {
                "actor_propietario": es_propietario(str(datos.get("correo") or "")),
                "personas": [
                    {**persona, "propietario": es_propietario(persona["correo"])}
                    for persona in personas
                ]
            }
        )

    @router.patch("/api/investigacion/equipo/{sujeto}/facultad")
    async def facultad_profesional(sujeto: str, peticion: Request) -> Response:
        datos, _desde, _hasta, error = _autorizar_y_periodo(peticion)
        if error is not None:
            return error
        cuerpo = await json_del_cuerpo(peticion)
        if roles is None:
            return mantenimiento("el gobierno del equipo institucional no está disponible")
        try:
            perfil = roles.asignar_facultad_profesional(
                sujeto_de(datos), sujeto, str(cuerpo.get("facultad") or "")
            )
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except ValueError as error_facultad:
            return JSONResponse({"detalle": str(error_facultad)}, status_code=400)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo asignar la facultad")
        if perfil is None:
            return JSONResponse(
                {"detalle": "la cuenta no tiene función docente"}, status_code=404
            )
        return JSONResponse({"perfil": perfil})

    @router.get("/api/investigacion/equipo/{sujeto}/foto")
    def foto_del_equipo(sujeto: str, peticion: Request) -> Response:
        """Fotografía privada visible sólo dentro del directorio investigador."""
        _datos, _desde, _hasta, error = _autorizar_y_periodo(peticion)
        if error is not None:
            return error
        if identidades is None or fotos is None or not fotos.configurado:
            return mantenimiento("las fotografías del equipo no están disponibles")
        try:
            referencia = identidades.referencia_foto(sujeto)
            cuerpo = fotos.recuperar(referencia) if referencia else None
        except ReferenciaDesconocida:
            return JSONResponse({"detalle": "cuenta no encontrada"}, status_code=404)
        except (ErrorDeAlmacen, OSError):
            return mantenimiento("no se pudo recuperar la fotografía")
        if cuerpo is None:
            return JSONResponse({"detalle": "esta cuenta no tiene foto"}, status_code=404)
        return Response(
            content=cuerpo,
            media_type="image/webp",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    return router
