from __future__ import annotations

import hashlib
import re


SHA256 = re.compile(r"^[0-9a-f]{64}$")


SEPARADOR = "␟"


def comprobante_de(*partes: str) -> str:
    return hashlib.sha256(SEPARADOR.join(partes).encode("utf-8")).hexdigest()
