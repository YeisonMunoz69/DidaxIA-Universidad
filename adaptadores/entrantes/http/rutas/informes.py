from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento, requerir_rol
from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from adaptadores.salientes.informes.pdf_kpi import VERSION_PLANTILLA, generar_informe_kpi
from dominio.kpi.consulta import ConsultaKPI
from dominio.kpi.contratos import Alcance, KPIInvalido, Periodo
from dominio.kpi.definiciones import ZONA_HORARIA
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible, EscrituraRechazada


class Calculo(Protocol):
    def calcular(self, consulta: ConsultaKPI) -> dict: ...

class Auditor(Protocol):
    def registrar(self, datos: dict, documento: bytes) -> None: ...

def _segmento(valor: object) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(valor or "").strip())
    return limpio.strip(".-_")[:90] or "sin-codigo"

def _instante(valor: object, predeterminado: datetime) -> datetime:
    if not valor:
        return predeterminado
    instante = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    return instante if instante.tzinfo else instante.replace(tzinfo=ZoneInfo(ZONA_HORARIA))

def _consulta(cuerpo: dict, actor: str) -> tuple[ConsultaKPI, str, str]:
    ahora = datetime.now(UTC)
    tipo = str(cuerpo.get("tipo") or "").strip()
    codigo = str(cuerpo.get("codigo") or "").strip()
    if tipo not in {"indicador", "seleccion", "completo"}:
        raise KPIInvalido("elige un informe individual, seleccionado o completo")
    if tipo == "indicador" and not codigo:
        raise KPIInvalido("el informe individual exige un código KPI")
    if tipo == "completo" and cuerpo.get("confirmado") is not True:
        raise KPIInvalido("confirma expresamente el informe completo")
    codigos = ()
    if tipo == "seleccion":
        crudos = cuerpo.get("codigos")
        if (not isinstance(crudos, list) or not 1 <= len(crudos) <= 51
                or any(not isinstance(item, str) or not item.strip() for item in crudos)):
            raise KPIInvalido("elige entre 1 y 51 códigos KPI para el informe")
        codigos = tuple(item.strip() for item in crudos)
        if len(set(codigos)) != len(codigos):
            raise KPIInvalido("la selección KPI contiene códigos repetidos")
    periodo = Periodo(
        desde=_instante(cuerpo.get("desde"), ahora - timedelta(days=30)),
        hasta=_instante(cuerpo.get("hasta"), ahora),
    )
    filtros = cuerpo.get("filtros") or {}
    if not isinstance(filtros, dict):
        raise KPIInvalido("los filtros tienen que formar un objeto")
    consulta = ConsultaKPI(
        alcance=Alcance.INSTITUCIONAL,
        actor=actor,
        periodo=periodo,
        clase=str(cuerpo.get("clase") or "").strip() or None,
        filtros=filtros,
        codigos=(codigo,) if tipo == "indicador" else codigos,
    )
    return consulta, tipo, codigo

def crear_router(
    sesiones: Sesiones,
    calculo: Calculo,
    auditor: Auditor,
    puerta: PuertaDeSupresion,
) -> APIRouter:
    router = APIRouter()

    def producir(peticion: Request, cuerpo: dict, *, descarga: bool) -> Response:
        error = requerir_rol(sesiones, peticion, "investigador")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        actor = sujeto_de(datos)
        negativa = puerta.negativa(actor)
        if negativa is not None:
            return negativa
        try:
            consulta, tipo, codigo = _consulta(cuerpo, actor)
            resultado = calculo.calcular(consulta)
            documento = generar_informe_kpi(resultado, tipo=tipo, codigo=codigo)
            auditor.registrar({
                "actor": actor,
                "operacion": (
                    "descargar_informe_kpi" if descarga else "generar_informe_kpi"
                ),
                "tipo": tipo,
                "codigo": codigo,
                "codigos": list(consulta.codigos),
                "periodo": consulta.periodo.como_json(),
                "filtros": consulta.filtros_declarados,
                "version_plantilla": VERSION_PLANTILLA,
            }, documento)
        except (KPIInvalido, ValueError) as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=400)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo generar y auditar el informe")
        disposicion = "attachment" if descarga else "inline"
        desde = consulta.periodo.desde.date().isoformat()
        hasta = consulta.periodo.hasta.date().isoformat()
        identificador = _segmento(codigo) if tipo == "indicador" else tipo
        nombre = f"didaxia-kpi-{identificador}-{desde}-{hasta}.pdf"
        return Response(
            documento,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'{disposicion}; filename="{nombre}"',
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @router.post("/api/investigacion/informes/vista-previa")
    async def vista_previa(peticion: Request) -> Response:
        cuerpo = await peticion.json()
        return producir(peticion, cuerpo if isinstance(cuerpo, dict) else {}, descarga=False)

    @router.post("/api/investigacion/informes/descargar")
    async def descargar(peticion: Request) -> Response:
        cuerpo = await peticion.json()
        return producir(peticion, cuerpo if isinstance(cuerpo, dict) else {}, descarga=True)

    return router
