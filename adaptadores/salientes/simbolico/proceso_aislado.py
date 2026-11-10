"""
proceso_aislado.py — Envoltura de aislamiento del motor simbólico
=================================================================

Implementa la alternativa **B** de `ADR-011`: subproceso persistente con
límites del sistema operativo.

Por qué un proceso y no un hilo
-------------------------------
El cálculo simbólico es Python puro ocupando la CPU. **Un hilo de Python no
puede interrumpirse desde fuera.** El único corte de tiempo fiable es un
proceso que se pueda terminar. La medición que lo motiva está en `ADR-011` §1.1:
una suma de veinte términos trigonométricos derivada tres veces supera los doce
segundos sin terminar, y es una entrada que un estudiante puede escribir.

Qué NO garantiza
----------------
`ADR-011` §5.2 lo declara y aquí se repite porque es donde alguien lo leerá: el
proceso hijo hereda el sistema de archivos y la red del anfitrión. Se cubren
**tiempo y memoria**, que son los dos límites del riesgo medido. La ausencia de
red y de sistema de archivos que `RI-08` pide por completo exige una frontera
del sistema operativo o un contenedor — la alternativa D del ADR.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as TiempoAgotado
from multiprocessing import get_context
from threading import Lock

from dominio.modelo.matematica import (
    BloqueVerificable,
    InformeVerificacion,
    Precomputo,
    Veredicto,
    Verificacion,
)


def _flotante(nombre: str, defecto: float) -> float:
    try:
        return float(os.environ.get(nombre, "") or defecto)
    except ValueError:
        return defecto


def _entero(nombre: str, defecto: int) -> int:
    try:
        return int(os.environ.get(nombre, "") or defecto)
    except ValueError:
        return defecto


#: Umbrales configurables sin recompilar (`RF-ADM-06` · `RI-13`).
TIEMPO_MAXIMO_S = _flotante("AGENTE_CAS_TIMEOUT_S", 8.0)
MEMORIA_MAXIMA_MB = _entero("AGENTE_CAS_MEMORIA_MB", 512)

MENSAJE_TIEMPO = (
    "el cálculo superó el tiempo máximo permitido; "
    "la respuesta desciende al nivel de sondeo"
)


def aislamiento_activo() -> bool:
    """Se lee en cada llamada para que las pruebas puedan alternarlo."""
    return os.environ.get("AGENTE_CAS_AISLAR", "").strip() in {"1", "true", "yes"}


def _preparar_hijo() -> None:
    if MEMORIA_MAXIMA_MB > 0 and sys.platform != "win32":
        try:
            import resource

            limite = MEMORIA_MAXIMA_MB * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limite, limite))
        except Exception:                                       # pragma: no cover
            pass                     # si no se puede, el corte de tiempo sigue
    os.environ["AGENTE_CAS_AISLAR"] = "0"          # evita anidar procesos


def _precomputar_hijo(expresion: str, variable: str, orden: int, notacion: str) -> Precomputo:
    from adaptadores.salientes.simbolico.adaptador import AdaptadorSimbolico

    return AdaptadorSimbolico().precomputar(expresion, variable, orden, notacion)


def _precomputar_limite_hijo(expresion: str, variable: str, valor_limite: str) -> Precomputo:
    from adaptadores.salientes.simbolico.adaptador import AdaptadorSimbolico

    return AdaptadorSimbolico().precomputar_limite(expresion, variable, valor_limite)


def _verificar_hijo(bloques: tuple) -> InformeVerificacion:
    from adaptadores.salientes.simbolico.adaptador import AdaptadorSimbolico

    return AdaptadorSimbolico().verificar(bloques)


def _capacidad_hijo(nombre, argumento):
    from adaptadores.salientes.simbolico.adaptador import AdaptadorSimbolico

    if nombre not in ('precomputar_valor', 'objetivos_conversacionales', 'citas_conversacionales_relacionadas', 'referencia_transformada'):
        raise ValueError('capacidad no admitida')
    return getattr(AdaptadorSimbolico(), nombre)(argumento)


_ejecutor: ProcessPoolExecutor | None = None
_candado_ejecutor = Lock()


def _obtener_ejecutor() -> ProcessPoolExecutor:
    global _ejecutor
    with _candado_ejecutor:
        if _ejecutor is None:
            # La ruta HTTP llama desde hilos. Fork puede heredar candados de esos
            # hilos, o del ejecutor descartado, y dejar el nuevo CAS bloqueado.
            _ejecutor = ProcessPoolExecutor(max_workers=1, initializer=_preparar_hijo,
                                            mp_context=get_context('spawn'))
        return _ejecutor


def reiniciar() -> None:
    """Descarta el proceso hijo. Es la única forma de recuperarlo si se colgó."""
    global _ejecutor
    with _candado_ejecutor:
        anterior, _ejecutor = _ejecutor, None
    if anterior is not None:
        # shutdown(wait=False) por sí solo deja vivo un cálculo atascado.
        procesos = list((anterior._processes or {}).values())
        for proceso in procesos:
            if proceso.is_alive():
                proceso.terminate()
        for proceso in procesos:
            proceso.join(timeout=0.5)
            if proceso.is_alive():
                proceso.kill()
        anterior.shutdown(wait=False, cancel_futures=True)


class SimbolicoAislado:
    """Decora un `PuertoSimbolico` con corte de tiempo y límite de memoria.

    Implementa el mismo puerto que decora, de modo que el dominio no distingue
    si está aislado o no. Es lo que permite probar la lógica de verificación sin
    pagar la frontera de proceso.
    """

    def __init__(self, interno=None):
        from adaptadores.salientes.simbolico.adaptador import AdaptadorSimbolico

        self._interno = interno or AdaptadorSimbolico()

    def precomputar_valor(self, expresion):
        return self._capacidad('precomputar_valor', expresion, Precomputo(error=MENSAJE_TIEMPO))

    def objetivos_conversacionales(self, activo):
        return self._capacidad('objetivos_conversacionales', activo, [])

    def citas_conversacionales_relacionadas(self, datos):
        return self._capacidad('citas_conversacionales_relacionadas', datos, False)

    def referencia_transformada(self, datos):
        return self._capacidad('referencia_transformada', datos, None)

    def _capacidad(self, nombre, argumento, fallo):
        if not aislamiento_activo():
            return getattr(self._interno, nombre)(argumento)
        try:
            futuro = _obtener_ejecutor().submit(_capacidad_hijo, nombre, argumento)
            return futuro.result(timeout=TIEMPO_MAXIMO_S or None)
        except Exception:  # noqa: BLE001 — una capacidad opcional no bloquea el chat
            reiniciar()
            return fallo

    def precomputar(
        self,
        expresion: str,
        variable: str = "x",
        orden: int = 1,
        notacion: str = "",
    ) -> Precomputo:
        if not aislamiento_activo():
            return self._interno.precomputar(expresion, variable, orden, notacion)
        try:
            futuro = _obtener_ejecutor().submit(
                _precomputar_hijo, expresion, variable, orden, notacion
            )
            return futuro.result(timeout=TIEMPO_MAXIMO_S or None)
        except TiempoAgotado:
            reiniciar()
            return Precomputo(error=MENSAJE_TIEMPO)
        except Exception as e:                                  # noqa: BLE001
            reiniciar()
            return Precomputo(error=f"el cálculo no pudo completarse: {e}")

    def precomputar_limite(self, expresion: str, variable: str = "x", valor_limite: str = "0") -> Precomputo:
        """Igual que `precomputar`, para la capacidad de límites de `PM-B22`.

        No está en `PuertoSimbolico` (ver el docstring del adaptador), pero
        el aislamiento es del mismo tipo de riesgo —cálculo determinista que
        puede ser caro— así que se decora igual, por duck typing.
        """
        if not aislamiento_activo():
            return self._interno.precomputar_limite(expresion, variable, valor_limite)
        try:
            futuro = _obtener_ejecutor().submit(
                _precomputar_limite_hijo, expresion, variable, valor_limite
            )
            return futuro.result(timeout=TIEMPO_MAXIMO_S or None)
        except TiempoAgotado:
            reiniciar()
            return Precomputo(error=MENSAJE_TIEMPO)
        except Exception as e:                                  # noqa: BLE001
            reiniciar()
            return Precomputo(error=f"el cálculo no pudo completarse: {e}")

    def verificar(self, bloques: Sequence[BloqueVerificable]) -> InformeVerificacion:
        if not aislamiento_activo():
            return self._interno.verificar(bloques)
        try:
            futuro = _obtener_ejecutor().submit(_verificar_hijo, tuple(bloques))
            return futuro.result(timeout=TIEMPO_MAXIMO_S or None)
        except TiempoAgotado:
            reiniciar()
            return self._informe_de_fallo(bloques, MENSAJE_TIEMPO)
        except Exception as e:                                  # noqa: BLE001
            reiniciar()
            return self._informe_de_fallo(bloques, f"fallo del motor: {e}")

    @staticmethod
    def _informe_de_fallo(bloques, motivo: str) -> InformeVerificacion:
        """Un fallo del motor **no aprueba**. `ADR-008` V1.

        El modo seguro no hubo que inventarlo: la respuesta desciende al nivel 1
        de la escala de divulgación, y una pregunta socrática no contiene
        afirmaciones que verificar (`ADR-008` §6.1).
        """
        return InformeVerificacion(
            verificaciones=tuple(
                Verificacion(
                    bloque=b.identificador,
                    veredicto=Veredicto.NO_VERIFICABLE,
                    herramienta="sympy",
                    latencia_ms=0.0,
                    detalle=motivo,
                )
                for b in bloques
            )
        )
