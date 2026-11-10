from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from psycopg import sql

from infraestructura.migraciones.catalogo import Migracion
from infraestructura.migraciones.huellas import HUELLAS, Huella


class Estado(StrEnum):
    AUSENTE = "ausente"
    PRESENTE = "presente"
    PARCIAL = "parcial"

@dataclass(frozen=True, slots=True)
class Inspeccion:
    version: int
    estado: Estado
    detalle: str = ""

def _normalizar(texto: str | None, esquema: str) -> str | None:
    if texto is None:
        return None
    return re.sub(rf'(?:(?:"{re.escape(esquema)}")|{re.escape(esquema)})\.', "<local>.", texto)

def _columna(cur: Any, esquema: str, tabla: str, columna: str) -> tuple[Any, ...] | None:
    cur.execute(
        """
        SELECT format_type(a.atttypid, a.atttypmod), a.attnotnull, a.attidentity,
               pg_get_expr(d.adbin, d.adrelid), tn.nspname, t.typtype, t.typname
          FROM pg_attribute a
          JOIN pg_class c ON c.oid = a.attrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_type t ON t.oid = a.atttypid
          JOIN pg_namespace tn ON tn.oid = t.typnamespace
          LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
         WHERE n.nspname = %s AND c.relname = %s AND a.attname = %s
           AND a.attnum > 0 AND NOT a.attisdropped
        """,
        (esquema, tabla, columna),
    )
    fila = cur.fetchone()
    if not fila:
        return None
    tipo = f"<local>.{fila[6]}" if fila[5] == "d" and fila[4] == esquema else fila[0]
    return (_normalizar(tipo, esquema), fila[1], fila[2], _normalizar(fila[3], esquema))

def _indice(cur: Any, esquema: str, nombre: str) -> str | None:
    cur.execute(
        """
        SELECT pg_get_indexdef(c.oid)
          FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = %s AND c.relname = %s AND c.relkind = 'i'
        """,
        (esquema, nombre),
    )
    fila = cur.fetchone()
    return _normalizar(fila[0], esquema) if fila else None

def _dominio(cur: Any, esquema: str, nombre: str) -> tuple[Any, ...] | None:
    cur.execute(
        """
        SELECT format_type(t.typbasetype, t.typtypmod), t.typnotnull,
               coalesce(array_agg(pg_get_constraintdef(c.oid) ORDER BY c.conname)
                        FILTER (WHERE c.oid IS NOT NULL), ARRAY[]::text[])
          FROM pg_type t
          JOIN pg_namespace n ON n.oid = t.typnamespace
          LEFT JOIN pg_constraint c ON c.contypid = t.oid
         WHERE n.nspname = %s AND t.typname = %s AND t.typtype = 'd'
         GROUP BY t.oid
        """,
        (esquema, nombre),
    )
    fila = cur.fetchone()
    if not fila:
        return None
    return (_normalizar(fila[0], esquema), fila[1], tuple(fila[2]))

def _restricciones(cur: Any, esquema: str, tablas: tuple[str, ...]) -> dict[str, Any]:
    if not tablas:
        return {}
    cur.execute(
        """
        SELECT r.relname, c.conname, c.contype, pg_get_constraintdef(c.oid)
          FROM pg_constraint c
          JOIN pg_class r ON r.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = r.relnamespace
         WHERE n.nspname = %s AND r.relname = ANY(%s)
         ORDER BY r.relname, c.conname
        """,
        (esquema, list(tablas)),
    )
    return {
        f"restriccion:{tabla}.{nombre}": (
            tipo,
            (_normalizar(definicion, esquema) or "").replace("<local>.", ""),
        )
        for tabla, nombre, tipo, definicion in cur.fetchall()
    }

def _capturar(cur: Any, esquema: str, huella: Huella) -> dict[str, Any]:
    firmas: dict[str, Any] = {}
    for dominio in huella.dominios:
        firmas[f"dominio:{dominio}"] = _dominio(cur, esquema, dominio)
    for tabla, columnas in huella.columnas:
        for columna in columnas:
            firmas[f"columna:{tabla}.{columna}"] = _columna(cur, esquema, tabla, columna)
    for indice in huella.indices:
        firmas[f"indice:{indice}"] = _indice(cur, esquema, indice)
    return firmas

def _comparar(canon: dict[str, Any], actual: dict[str, Any]) -> tuple[Estado, str]:
    presentes = [nombre for nombre, firma in actual.items() if firma is not None]
    if not presentes:
        return Estado.AUSENTE, ""
    faltantes = [nombre for nombre, firma in actual.items() if firma is None]
    distintos = [nombre for nombre in canon if actual.get(nombre) not in (None, canon[nombre])]
    if faltantes or distintos:
        partes = []
        if faltantes:
            partes.append("faltan " + ", ".join(faltantes))
        if distintos:
            partes.append("forma distinta en " + ", ".join(distintos))
        return Estado.PARCIAL, "; ".join(partes)
    return Estado.PRESENTE, ""

def inspeccionar(cur: Any, migraciones: tuple[Migracion, ...], esquema: str) -> tuple[Inspeccion, ...]:
    temporal = f"didaxia_referencia_{uuid.uuid4().hex[:12]}"
    cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(temporal)))
    resultados: list[Inspeccion] = []
    try:
        for migracion in migraciones:
            huella = HUELLAS.get(migracion.version)
            if huella is None:

                resultados.append(Inspeccion(migracion.version, Estado.AUSENTE))
                continue
            tablas = tuple(dict.fromkeys(tabla for tabla, _ in huella.columnas))
            restricciones_previas = _restricciones(cur, temporal, tablas)
            cur.execute(
                sql.SQL("SET LOCAL search_path TO {}, public").format(sql.Identifier(temporal))
            )
            cur.execute(migracion.sql)
            canon = _capturar(cur, temporal, huella)
            restricciones_nuevas = {
                nombre: firma
                for nombre, firma in _restricciones(cur, temporal, tablas).items()
                if restricciones_previas.get(nombre) != firma
            }
            canon.update(restricciones_nuevas)
            actual = _capturar(cur, esquema, huella)
            restricciones_actuales = _restricciones(cur, esquema, tablas)
            for nombre in canon.keys() - actual.keys():
                actual[nombre] = restricciones_actuales.get(nombre)
            estado, detalle = _comparar(canon, actual)
            resultados.append(Inspeccion(migracion.version, estado, detalle))
    finally:
        cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(temporal)))
        cur.execute(sql.SQL("SET LOCAL search_path TO {}, public").format(sql.Identifier(esquema)))
    return tuple(resultados)
