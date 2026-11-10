from __future__ import annotations

import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http import formato_representante, identidad
from adaptadores.entrantes.http.composicion import Composicion
from dominio.modelo.consentimiento import Alcance
from dominio.modelo.factores_conductuales import VERSION as VERSION_FACTORES


def _estado_formato_representante(versiones) -> dict:
    if versiones is None:
        return {"comprobado": False, "descargable": False, "motivo": "sin_almacen"}
    try:
        version = versiones.version_requerida(Alcance.REPRESENTANTE)
    except Exception:
        return {"comprobado": False, "descargable": False, "motivo": "consulta_fallida"}
    motivo = formato_representante.disponibilidad(version)
    return {
        "comprobado": True,
        "descargable": motivo == "disponible",
        "motivo": None if motivo == "disponible" else motivo,
    }

def _sin_monitor() -> dict:
    from adaptadores.salientes.disponibilidad.postgres import SIN_MONITOR

    return dict(SIN_MONITOR)

_SIN_MONITOR = _sin_monitor()


def faltantes_del_borde() -> list[str]:
    if identidad.esta_configurado():
        return []
    return [
        "GOOGLE_CLIENT_ID no está en el entorno: el login de Google (PM-B15) "
        "rechaza cualquier token con 401. El resto del sistema funciona; el "
        "rol docente solo se puede alcanzar por esa vía."
    ]

def _generacion_configurada() -> dict:
    from adaptadores.salientes.generacion.deepseek import _MODELO_POR_DEFECTO

    pedido = os.environ.get("AGENTE_LLM_MODELO", "").strip()
    return {
        "proveedor": os.environ.get("AGENTE_LLM", "").strip() or None,
        "modelo": pedido or _MODELO_POR_DEFECTO,
        "modelo_del_entorno": bool(pedido),

        "nota": "modelo pedido; RF-REG-04 registra el que responde el proveedor",
    }

SIN_CUSTODIA = {
    "declarado": False,
    "configurado": False,
    "tipo": None,
    "disponible": False,
}


def _custodia(almacenamiento) -> dict:
    if almacenamiento is None:
        return dict(SIN_CUSTODIA)
    publicable = getattr(almacenamiento, "estado_publicable", None)
    if publicable is None:
        return {
            "declarado": True,
            "configurado": bool(almacenamiento.esta_configurado()),
            "tipo": None,
            "disponible": False,
        }
    return {"declarado": True, **publicable()}

def crear_router(
    composicion: Composicion,
    faltantes_almacenes: list[str] | tuple[str, ...] = (),
    *,
    canal=None,
    monitor=None,
    almacenamiento=None,
    versiones=None,
) -> APIRouter:

    router = APIRouter()

    @router.get("/api/salud")
    def salud() -> JSONResponse:
        cuerpo = {
            "faltantes": [*composicion.faltantes, *faltantes_del_borde(), *faltantes_almacenes],

            "generacion": _generacion_configurada(),
            "tutor": {
                "interpretacion": composicion.interpretacion,
                "contexto": "reforzado" if composicion.contexto_reforzado else "actual",
            "retroalimentacion_directa": composicion.retroalimentacion_directa,
            "continuidad": "estado_operativo.v1" if composicion.continuidad else "anterior",
            "factores_conductuales": composicion.factores_conductuales,
            "version_factores": VERSION_FACTORES,
                "progreso_en_vivo": True,
            },
        }
        if canal is not None:

            cuerpo["notificacion"] = canal.como_json()

        cuerpo["disponibilidad"] = (
            monitor.como_json() if monitor is not None else _SIN_MONITOR
        )

        cuerpo["almacenamiento_privado"] = _custodia(almacenamiento)
        cuerpo["formato_representante"] = _estado_formato_representante(versiones)
        return JSONResponse(cuerpo)

    return router
