from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from io import StringIO
from typing import Protocol
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento, requerir_rol
from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from adaptadores.salientes.informes.pdf_consumo_ia import generar_informe_consumo_ia
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible, EscrituraRechazada

ZONA = ZoneInfo("America/Bogota")


class ConsumoIA(Protocol):
    def resumen(self, actor: str, desde: datetime, hasta: datetime) -> dict: ...
    def auditar_exportacion(
        self, actor: str, desde: datetime, hasta: datetime, formato: str, documento: bytes
    ) -> None: ...

def _periodo(peticion: Request) -> tuple[datetime, datetime]:
    hoy = datetime.now(ZONA).date()
    desde_crudo = peticion.query_params.get("desde") or (hoy - timedelta(days=29)).isoformat()
    hasta_crudo = peticion.query_params.get("hasta") or (hoy + timedelta(days=1)).isoformat()
    try:
        desde_fecha = date.fromisoformat(desde_crudo)
        hasta_fecha = date.fromisoformat(hasta_crudo)
    except ValueError as exc:
        raise ValueError("desde y hasta deben tener formato AAAA-MM-DD") from exc
    if hasta_fecha <= desde_fecha:
        raise ValueError("hasta debe ser posterior a desde; el intervalo es [desde,hasta)")
    if (hasta_fecha - desde_fecha).days > 366:
        raise ValueError("el intervalo no puede superar 366 días")
    return (
        datetime.combine(desde_fecha, datetime.min.time(), ZONA),
        datetime.combine(hasta_fecha, datetime.min.time(), ZONA),
    )

SECCIONES = frozenset({"totales", "modelos", "diaria", "horarios", "metodologia"})


def _secciones(peticion: Request) -> frozenset[str]:
    crudo = peticion.query_params.get("secciones")
    seleccion = SECCIONES if crudo is None else frozenset(crudo.split(","))
    if not seleccion or not seleccion <= SECCIONES:
        raise ValueError("selección de secciones no válida")
    return seleccion

def _csv(datos: dict, secciones: frozenset[str] = SECCIONES) -> bytes:
    salida = StringIO(newline="")
    escritor = csv.writer(salida)
    periodo = datos["periodo"]
    escritor.writerow(["DidaxIA · consumo institucional de IA"])
    escritor.writerow(["periodo_desde", periodo["desde"], "periodo_hasta_exclusivo", periodo["hasta"]])
    escritor.writerow(["naturaleza", datos["naturaleza"]])
    escritor.writerow([])
    escritor.writerow(["secciones", ",".join(sorted(secciones))])
    if "modelos" in secciones:
        escritor.writerow(["proveedor", "modelo", "llamadas", "medidas", "cache_hit", "cache_miss", "entrada", "salida"])
        for fila in datos.get("por_modelo", []):
            escritor.writerow(
                [fila.get(campo) for campo in (
                    "proveedor", "modelo", "llamadas", "medidas", "entrada_cache_hit",
                    "entrada_cache_miss", "entrada_total", "salida"
                )]
            )
        escritor.writerow([])
    if "totales" in secciones:
        escritor.writerow(["estimado_usd", datos["costos"].get("estimado_usd")])
        escritor.writerow(["estimado_cop", datos["costos"].get("estimado_cop")])
        escritor.writerow(["trm_fecha", datos["trm_actual"].get("fecha")])
        for clave, valor in datos.get("totales", {}).items():
            escritor.writerow([clave, valor])
    for seccion, campo, columnas in (
        ("diaria", "serie_diaria", ("fecha", "llamadas", "costo_usd", "estado")),
        ("horarios", "distribucion_hora_local", ("hora", "llamadas", "estado")),
    ):
        if seccion in secciones:
            escritor.writerow([])
            escritor.writerow([seccion])
            escritor.writerow(columnas)
            for fila in datos.get(campo, []):
                escritor.writerow([fila.get(clave) for clave in columnas])
    escritor.writerow(["trm_fuente", datos["trm_actual"].get("fuente")])
    if "metodologia" in secciones:
        for aviso in datos.get("advertencias", []):
            escritor.writerow(["metodologia", aviso])
    escritor.writerow(["advertencia", "estimación reproducible; no es cargo real de facturación"])
    escritor.writerow(["regla_supresion", datos["regla_supresion"]])
    return ("\ufeff" + salida.getvalue()).encode("utf-8")

def crear_router(sesiones: Sesiones, consumo: ConsumoIA, puerta: PuertaDeSupresion) -> APIRouter:
    router = APIRouter()

    def producir(peticion: Request, formato: str | None = None) -> Response:
        error = requerir_rol(sesiones, peticion, "investigador")
        if error is not None:
            return error
        datos_sesion = sesiones.leer(peticion.cookies.get(COOKIE))
        actor = sujeto_de(datos_sesion)
        negativa = puerta.negativa(actor)
        if negativa is not None:
            return negativa
        try:
            desde, hasta = _periodo(peticion)
            secciones = _secciones(peticion) if formato is not None else SECCIONES
            resumen = consumo.resumen(actor, desde, hasta)
            if formato is None:
                return JSONResponse(resumen)
            documento = (
                _csv(resumen, secciones) if formato == "csv"
                else generar_informe_consumo_ia(resumen, secciones=secciones)
            )
            consumo.auditar_exportacion(actor, desde, hasta, formato, documento)
        except ValueError as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=400)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("el consumo institucional de IA no está disponible")
        media = "text/csv; charset=utf-8" if formato == "csv" else "application/pdf"
        nombre = f"didaxia-consumo-ia-{desde.date()}-{hasta.date()}.{formato}"
        return Response(
            documento,
            media_type=media,
            headers={
                "Content-Disposition": f'attachment; filename="{nombre}"',
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @router.get("/api/investigacion/consumo-ia")
    def consultar(peticion: Request) -> Response:
        return producir(peticion)

    @router.get("/api/investigacion/consumo-ia/exportar.csv")
    def exportar_csv(peticion: Request) -> Response:
        return producir(peticion, "csv")

    @router.get("/api/investigacion/consumo-ia/exportar.pdf")
    def exportar_pdf(peticion: Request) -> Response:
        return producir(peticion, "pdf")

    return router
