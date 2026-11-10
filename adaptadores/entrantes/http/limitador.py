from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock


def _entero_de_entorno(nombre: str, defecto: int) -> int:
    try:
        return int(os.environ.get(nombre, "") or defecto)
    except ValueError:
        return defecto

MAX_PETICIONES_POR_SESION = _entero_de_entorno("AGENTE_LIMITE_SESION", 20)
MAX_PETICIONES_POR_IP = _entero_de_entorno("AGENTE_LIMITE_IP", 60)
VENTANA_S = _entero_de_entorno("AGENTE_LIMITE_VENTANA_S", 60)


MAX_PETICIONES_POR_IP_AUTENTICADA = _entero_de_entorno("AGENTE_LIMITE_IP_AUTENTICADA", 300)


@dataclass
class _Contador:
    bloque: int = -1
    peticiones: int = 0

@dataclass
class LimitadorDePeticiones:

    maximo_por_sesion: int = MAX_PETICIONES_POR_SESION
    maximo_por_ip: int = MAX_PETICIONES_POR_IP
    ventana_s: int = VENTANA_S
    maximo_por_ip_autenticada: int = MAX_PETICIONES_POR_IP_AUTENTICADA
    _reloj: Callable[[], float] = field(default=time.time, repr=False)
    _por_sesion: dict[str, _Contador] = field(default_factory=dict, repr=False)
    _por_ip: dict[str, _Contador] = field(default_factory=dict, repr=False)
    _por_persona: dict[str, _Contador] = field(default_factory=dict, repr=False)
    _por_ip_autenticada: dict[str, _Contador] = field(default_factory=dict, repr=False)
    _candado: Lock = field(default_factory=Lock, repr=False)

    def admite_turno(self, ip: str, sesion: str, sujeto: str) -> bool:
        if not sujeto:
            return False
        with self._candado:
            bloque = int(self._reloj() // self.ventana_s)
            limites = (
                (self._por_sesion, sesion, self.maximo_por_sesion),
                (self._por_persona, sujeto, self.maximo_por_sesion),
                (self._por_ip_autenticada, ip, self.maximo_por_ip_autenticada),
            )
            contadores = []
            for tabla, clave, maximo in limites:
                contador = tabla.setdefault(clave, _Contador())
                if contador.bloque != bloque:
                    contador.bloque, contador.peticiones = bloque, 0
                if contador.peticiones >= maximo:
                    return False
                contadores.append(contador)
            for contador in contadores:
                contador.peticiones += 1
            return True

    def admite_sesion(self, sesion: str) -> bool:
        return self._admite(self._por_sesion, sesion, self.maximo_por_sesion)

    def admite_ip(self, ip: str) -> bool:
        return self._admite(self._por_ip, ip, self.maximo_por_ip)

    def _admite(self, tabla: dict[str, _Contador], clave: str, maximo: int) -> bool:
        bloque_actual = int(self._reloj() // self.ventana_s)
        contador = tabla.setdefault(clave, _Contador())
        if contador.bloque != bloque_actual:
            contador.bloque = bloque_actual
            contador.peticiones = 0
        if contador.peticiones >= maximo:
            return False
        contador.peticiones += 1
        return True
