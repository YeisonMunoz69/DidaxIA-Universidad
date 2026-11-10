from __future__ import annotations

import json
from typing import Any


_SQL = """
INSERT INTO auditoria_operacion
    (operacion, actor, sujeto_afectado, detalle, exige_doble_aprobacion, aprobada_por)
VALUES (%s, %s, %s, %s::jsonb, %s, %s)
RETURNING id, momento
"""


def anotar(
    cur: Any,
    operacion: str,
    *,
    actor: str,
    sujeto_afectado: str | None = None,
    detalle: dict | None = None,
    aprobada_por: str | None = None,
) -> tuple[int, Any]:

    cur.execute(
        _SQL,
        (
            operacion,
            actor,
            sujeto_afectado,
            json.dumps(detalle or {}),
            aprobada_por is not None,
            aprobada_por,
        ),
    )
    return cur.fetchone()
