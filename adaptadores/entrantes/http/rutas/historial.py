from __future__ import annotations

import re
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento, requerir_sesion
from adaptadores.entrantes.http.sesiones import Sesiones, sujeto_de
from dominio.puertos.almacen import ErrorDeAlmacen

if TYPE_CHECKING:
    from datetime import datetime

LARGO_DEL_TITULO = 60
LARGO_FORMULA_TITULO = 512
FORMULA_TITULO = re.compile(r"\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$([^$\n]+?)\$|`([^`\n]+)`")


OPERACION_CONSULTA = "conversacion.consultada"


def titulo_de(primer_mensaje: str) -> str:
    limpio = " ".join((primer_mensaje or '').split())
    if re.fullmatch(r'(?:hola|buenos días|buenas tardes|buenas noches|gracias|muchas gracias|ok|vale)[!,.:;\s]*', limpio, flags=re.I):
        return 'Conversación de cálculo'
    limpio = re.sub(r'^(?:hola|buenos días|buenas tardes|buenas noches)[!,.:;\s]+', '', limpio, flags=re.I)
    formula = FORMULA_TITULO.search(limpio)
    if formula:
        expresion = next(g for g in formula.groups() if g is not None)

        es_codigo = formula.group(5) is not None
        if not es_codigo or re.search(r'[=^_]|\\(?:frac|lim|sqrt|int|sum)\b', expresion):
            asunto = 'Consulta'
            if re.search(r'deriv', limpio, re.I):
                asunto = 'Derivada'
            elif re.search(r'l[ií]mit|\\lim\b', limpio, re.I):
                asunto = 'Límite'
            elif re.search(r'integral|\\int\b', limpio, re.I):
                asunto = 'Integral'
            if len(expresion) <= LARGO_FORMULA_TITULO:
                return f'{asunto} · ${expresion}$'
            return f'{asunto} · expresión matemática extensa'

    if len(limpio) > LARGO_DEL_TITULO and ('$' in limpio or '\\(' in limpio or '\\[' in limpio):
        prosa = re.split(r'\$|\\\(|\\\[', limpio, maxsplit=1)[0].strip()
        limpio = prosa or 'Consulta de cálculo'
    if len(limpio) <= LARGO_DEL_TITULO:
        return limpio
    return limpio[: LARGO_DEL_TITULO - 1].rstrip() + "…"

def _momento(valor: datetime | str | None) -> str | None:
    if valor is None:
        return None
    return valor if isinstance(valor, str) else valor.isoformat()

def _material_como_contrato(piezas: list[dict], catalogo) -> list[dict]:
    return [
        {
            "id": pieza["fragmento"],
            "obra": pieza["obra"],
            "titulo": (
                catalogo.titulo_de_fragmento(pieza["fragmento"])
                if catalogo is not None
                else pieza["fragmento"]
            ),
            "relacion": pieza["relacion"],
        }
        for pieza in piezas
    ]

def conversaciones_como_contrato(filas: list[dict]) -> dict:
    return {
        "conversaciones": [
            {
                "sesion": fila["sesion"],
                "titulo": titulo_de(fila.get("mensaje_para_titulo") or fila["primer_mensaje"]),
                "inicio": _momento(fila["inicio"]),
                "ultimo": _momento(fila["ultimo"]),
                "turnos": fila["turnos"],
            }
            for fila in filas
        ]
    }

def hilo_como_contrato(
    identificador_sesion: str, mensajes: list[dict], catalogo=None
) -> dict:

    return {
        "sesion": identificador_sesion,
        "mensajes": [
            {
                "turno": m["turno"],
                "momento": _momento(m["momento"]),
                "autor": m["autor"],
                "contenido": m["contenido"],

                **({"bloques": m["bloques"]} if m.get("bloques") else {}),
                **({"citas": m["citas"]} if m.get("citas") else {}),
                **({"nivel": m["nivel"]} if m.get("nivel") else {}),
                **(
                    {
                        "procedencia": {
                            **m["procedencia"],

                            "material": _material_como_contrato(
                                m.get("material", []), catalogo
                            ),
                        }
                    }
                    if m.get("procedencia", {}).get("origen")
                    else {}
                ),
                **({"degradado": True} if m["degradado"] else {}),
            }
            for m in mensajes
        ],
    }

def crear_router(sesiones: Sesiones, adaptador_historial, catalogo=None) -> APIRouter:
    router = APIRouter()

    def _sin_almacen() -> Response:
        return mantenimiento("el historial no está disponible en este despliegue")

    @router.get("/api/historial")
    def listar_historial(peticion: Request) -> Response:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if adaptador_historial is None:
            return _sin_almacen()
        try:
            filas = adaptador_historial.historial_de(sujeto_de(datos))
        except ErrorDeAlmacen:
            return mantenimiento("no se pudo leer el historial en este momento")
        return JSONResponse(conversaciones_como_contrato(filas))

    @router.get("/api/historial/{identificador_sesion}")
    def leer_hilo(identificador_sesion: str, peticion: Request) -> Response:
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if adaptador_historial is None:
            return _sin_almacen()

        sujeto = sujeto_de(datos)
        try:
            mensajes = adaptador_historial.hilo_de(
                identificador_sesion, sujeto, actor=sujeto, operacion=OPERACION_CONSULTA
            )
        except ErrorDeAlmacen:
            return mantenimiento("no se pudo leer la conversación en este momento")

        if not mensajes:

            return JSONResponse({"detalle": "no se encontró esa conversación"}, status_code=404)
        return JSONResponse(hilo_como_contrato(identificador_sesion, mensajes, catalogo))

    @router.delete("/api/historial/{identificador_sesion}")
    def borrar_hilo(identificador_sesion: str) -> Response:
        return JSONResponse(
            {
                "detalle": (
                    "esta ruta fue retirada: durante el piloto el historial es "
                    "obligatorio (EQ-016) y ninguna conversación se borra por "
                    "separado. Toda eliminación pasa por el trámite reversible"
                ),
                "estado": "retirada",
                "usar": "/api/datos/supresion",
            },
            status_code=410,
        )

    return router
