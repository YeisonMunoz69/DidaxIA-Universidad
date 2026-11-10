"""Lee sólo los archivos de registro autorizados por la consulta SQL."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

RAIZ_TRAZAS = Path(__file__).resolve().parents[3] / "infraestructura" / "registro_turnos"


def _ruta_local(referencia: dict, raiz: Path) -> Path | None:
    ruta_cruda, turno = referencia.get("ruta"), referencia.get("turno")
    if not isinstance(ruta_cruda, str) or not isinstance(turno, str):
        return None
    # El productor escribe un archivo por turno. Un traslado Linux→Windows o
    # cambio de raíz no debe exigir modificar las filas históricas de la BD.
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", turno):
        return None
    partes = PurePosixPath(ruta_cruda.replace("\\", "/")).parts
    if len(partes) < 2 or partes[-2:] != ("registro_turnos", f"{turno}.json"):
        return None
    ruta = (raiz / f"{turno}.json").resolve()
    return ruta if ruta.is_relative_to(raiz) else None


def leer_trazas(referencias: list[dict], *, raiz_trazas: Path | None = None) -> tuple[list[dict], int]:
    registros = []
    faltantes = 0
    raiz = (raiz_trazas or RAIZ_TRAZAS).resolve()
    for referencia in referencias:
        ruta = _ruta_local(referencia, raiz)
        if ruta is None:
            faltantes += 1
            continue
        try:
            crudo = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            faltantes += 1
            continue
        if (not isinstance(crudo, dict)
                or crudo.get("turno") != referencia.get("turno")
                or crudo.get("identificador_sesion") != referencia.get("sesion")
                or (referencia.get("estudiante") is not None
                    and crudo.get("identificador_sujeto") != referencia["estudiante"])
                or not isinstance(crudo.get("trazas"), list)):
            faltantes += 1
            continue
        registros.append({"estudiante": referencia.get("estudiante"),
                          "sesion": referencia["sesion"], "trazas": crudo["trazas"],
                          "turno": referencia.get("turno"), "momento": referencia.get("momento")})
    return registros, faltantes
