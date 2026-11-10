from __future__ import annotations

import asyncio
import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass


MAXIMO_RECORDADAS = 256


class CandadoPorConversacion:

    def __init__(self) -> None:
        self._candados: dict[tuple[int, str], asyncio.Lock] = {}

    def obtener(self, conversacion: str) -> asyncio.Lock:
        clave = (self._bucle_actual(), conversacion)
        candado = self._candados.get(clave)
        if candado is None:
            candado = asyncio.Lock()
            self._candados[clave] = candado
        return candado

    @staticmethod
    def _bucle_actual() -> int:
        try:
            return id(asyncio.get_running_loop())
        except RuntimeError:

            return 0

    def olvidar(self, conversacion: str) -> None:
        for clave in [k for k in self._candados if k[1] == conversacion]:
            del self._candados[clave]

@dataclass(frozen=True)
class Recordada:

    huella: str
    lineas: tuple[bytes, ...]

class RegistroDeIdempotencia:

    def __init__(self, maximo: int = MAXIMO_RECORDADAS) -> None:
        self._maximo = maximo
        self._recordadas: OrderedDict[tuple[str, str], Recordada] = OrderedDict()

    @staticmethod
    def huella_de(cuerpo: dict) -> str:
        significativo = {
            "mensaje": cuerpo.get("mensaje") or "",
            "sesion": cuerpo.get("sesion") or "",
            "dos_niveles": cuerpo.get("dos_niveles"),
            "retomar_sesion": cuerpo.get("retomar_sesion") or "",
            "notacion": cuerpo.get("notacion") or "",
        }
        crudo = json.dumps(significativo, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(crudo.encode("utf-8")).hexdigest()

    def recordada(self, conversacion: str, clave: str) -> Recordada | None:
        return self._recordadas.get((conversacion, clave))

    def recordar(
        self, conversacion: str, clave: str, huella: str, lineas: tuple[bytes, ...]
    ) -> None:
        self._recordadas[(conversacion, clave)] = Recordada(huella=huella, lineas=lineas)
        self._recordadas.move_to_end((conversacion, clave))
        while len(self._recordadas) > self._maximo:
            self._recordadas.popitem(last=False)

    def olvidar_conversacion(self, conversacion: str) -> None:
        for llave in [k for k in self._recordadas if k[0] == conversacion]:
            del self._recordadas[llave]

def clave_de(cuerpo: dict) -> str:
    clave = str(cuerpo.get("idempotencia") or "").strip()
    return clave[:128]
