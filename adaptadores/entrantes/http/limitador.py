"""Topes por ventana fija para un servidor de un solo proceso.

El tutor exige una identidad verificada y consume juntos sus cupos de sesión,
persona e IP. El cupo del aula permite 50 cuentas compartiendo una red, mientras
el tope por persona sobrevive a renovar la sesión. Un rechazo individual no
consume saldo del aula. Los métodos independientes conservan el límite heredado
para otros consumidores. Ningún contador acepta una identidad enviada en el
cuerpo del turno.

Los contadores viven en memoria, como las sesiones de este despliegue. Varios
workers o réplicas requerirían coordinar ambos almacenes. La ventana fija puede
admitir dos ráfagas próximas si caen a ambos lados de su frontera.
"""

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


#: Peticiones admitidas por clave dentro de la ventana. `RF-ADM-06`: se lee
#: del entorno, no queda fijado en código.
MAX_PETICIONES_POR_SESION = _entero_de_entorno("AGENTE_LIMITE_SESION", 20)
MAX_PETICIONES_POR_IP = _entero_de_entorno("AGENTE_LIMITE_IP", 60)
VENTANA_S = _entero_de_entorno("AGENTE_LIMITE_VENTANA_S", 60)
# Un aula comparte la IP de salida: 50 personas pueden hacer seis preguntas
# por minuto, conservando el tope individual aunque renueven su sesión.
MAX_PETICIONES_POR_IP_AUTENTICADA = _entero_de_entorno("AGENTE_LIMITE_IP_AUTENTICADA", 300)


@dataclass
class _Contador:
    bloque: int = -1
    peticiones: int = 0


@dataclass
class LimitadorDePeticiones:
    """Cuenta peticiones por clave en bloques de `ventana_s` segundos.

    Una sola instancia por aplicación — es el estado que hace el tope
    efectivo entre peticiones. Inyectado, no un singleton de módulo, para
    que las pruebas puedan usar su propio reloj y su propia instancia sin
    interferir entre casos.
    """

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
        """Consume los tres cupos juntos, sólo para una identidad verificada.

        Una cuenta que insiste después de su tope no gasta el cupo del aula.
        El sujeto procede de la sesión del servidor, nunca del cuerpo HTTP.
        """
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
