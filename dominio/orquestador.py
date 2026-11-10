"""
orquestador.py — Encadena los filtros del turno, en ruta caliente y fría
==========================================================================

`ADR-001` §6.3: la cadena de tuberías y filtros procesa el turno en secuencia,
y cada filtro deja su traza. Este módulo es lo que convierte una lista de
filtros ya construidos en **un turno**: entra `ContextoTurno` con el texto del
estudiante, sale el mismo tipo con la respuesta y las trazas que `RF-ORQ-14`
exige poder reconstruir.

Por qué no arma los filtros él mismo
--------------------------------------
**N1** prohíbe que el dominio importe adaptadores. Cada filtro ya recibe sus
dependencias por inyección —`FiltroRecuperacion` un `PuertoCorpus`,
`FiltroEnrutamiento` un `IdentificadorDeNodo`—, así que armarlos con sus
adaptadores reales es asunto de quien compone el sistema, nunca de este
módulo. El orquestador solo sabe **encadenar** `Filtro`, no **construir**
ninguno.

`PM-B13` · la separación de ruta caliente y fría
----------------------------------------------------
`RF-ORQ-03` exige que el orquestador separe **ruta caliente** (dentro del
presupuesto de latencia del turno, `RNF-EFI-01`) de **ruta fría** (asíncrona,
fuera del camino crítico). Hasta esta sesión, `Orquestador` recibía una lista
y la corría entera con un solo método: la ruta de cada filtro solo se leía
para la traza (`Filtro.ruta`, `dominio/filtros/base.py`), nunca para decidir
**cuándo** correr.

Ahora la partición ocurre **al construir**, por la misma razón que `ADR-001`
§6.3 fija la ruta en el propio filtro y no en quien lo llama: es una
propiedad del filtro. `ejecutar()` corre solo los de `ruta == "caliente"` —el
camino que bloquea la respuesta del turno—; `ejecutar_fria()` corre solo los
de `ruta == "fría"` —el que `ADR-003` §6.5 S2 asigna a las consolidaciones que
no necesitan estar listas antes de responder—. Quien compone la cadena sigue
pasando una sola lista, en el orden que quiera dentro de cada ruta; no tiene
que separarlas él mismo.

Hoy, con la cadena que existe, `ejecutar_fria()` no hace nada: **ningún
filtro construido hasta ahora es `"fría"`** —`PM-B10` y `PM-B11` son quienes
traerán el primero, cuando el filtro 3 y la persistencia del perfil
existan—. Eso no es una limitación de este método: es la cadena de hoy, dicha
tal como es.

`RF-ORQ-03` §S3 (`ADR-003` §6.5): la ruta fría no debe modificar los
componentes de nivel 1 de la sesión en curso, o el arbitraje dejaría de ser
reproducible desde el registro de turnos. Ese es un compromiso de **cada**
filtro frío al escribirse, no algo que este módulo pueda vigilar sin conocer
qué campo es «nivel 1» — queda anotado para quien escriba el primero.

El presupuesto de latencia se mide por componente, no solo en total
-----------------------------------------------------------------------
`PM-B13` cierra con esto: `RF-ORQ-04`/`K4` piden que la actualización de ruta
caliente quepa en ≤300 ms, y `R-19` exige un diseño experimental propio para
medirlo —**la medición de tiempo de `E01` no es válida para esto**, y no se
inventa una cifra sin medir—. Lo que sí entrega esta sesión es la
instrumentación completa para hacer esa medición cuando corresponda:
`TrazaFiltro.latencia_ms` ya llega por filtro (`dominio/filtros/base.py`), y
`ContextoTurno.latencia_por_ruta` (`dominio/modelo/turno.py`) ya la agrega por
ruta. Ningún componente puede pasar por la cadena sin dejar su latencia
propia, así que «por componente» es una propiedad de la forma de la cadena,
no una funcionalidad aparte que haya que acordarse de añadir — el mismo
argumento que ya vale para `RF-ORQ-14`.

Qué pasa cuando un filtro lanza
----------------------------------
Hasta el 2026-08-08 la excepción se propagaba tal cual, y con ella se perdía
el `ContextoTurno` a medio construir: sus trazas —de qué fases sí llegó a
pasar el turno— desaparecían con la pila. `08-Contrato-del-Turno.md` §8.3
promete `ultima_fase` en toda degradación, y sin el contexto parcial ese
campo no se podía rellenar.

Cada ejecución —caliente o fría— atrapa la excepción, la envuelve en
`ErrorDeOrquestacion` —que lleva la causa original **y** el `ContextoTurno`
tal como quedó justo antes del filtro que falló— y la relanza. Quien reciba
el error tiene las trazas de todo lo que sí corrió, y de ahí sale
`ultima_fase`. La excepción original no se esconde: `causa` la conserva
entera y `raise ... from exc` mantiene la cadena de trazado de Python.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress

from dominio.filtros.base import Filtro
from dominio.filtros.recuperacion import FiltroRecuperacion
from dominio.modelo.turno import ContextoTurno, TrazaFiltro


class ErrorDeOrquestacion(Exception):
    """Un filtro lanzó a mitad de la cadena.

    Lleva el `ContextoTurno` **tal como quedó justo antes del filtro que
    falló** —con las trazas de todo lo que sí corrió—, para que quien reciba
    el error pueda reconstruir dónde se detuvo el turno (`RF-ORQ-14`,
    `08-Contrato-del-Turno.md` §8.3). Sin esto, un fallo a mitad de camino no
    se puede diagnosticar: se sabe que algo falló, pero no hasta dónde llegó.
    """

    def __init__(self, causa: Exception, ctx_parcial: ContextoTurno) -> None:
        super().__init__(str(causa))
        self.causa = causa
        self.ctx_parcial = ctx_parcial


class Orquestador:
    """Ejecuta una cadena de filtros ya construida, separando ruta caliente y
    fría según `Filtro.ruta` (`PM-B13`, `RF-ORQ-03`)."""

    def __init__(self, filtros: Sequence[Filtro]) -> None:
        self._calientes = tuple(f for f in filtros if f.ruta == "caliente")
        self._frias = tuple(f for f in filtros if f.ruta == "fría")

    def ejecutar(self, ctx: ContextoTurno, *, al_iniciar=None) -> ContextoTurno:
        """La ruta caliente: lo que corre dentro del presupuesto del turno.

        La única decisión que toma este método —y no cada filtro— es si un
        filtro de recuperación se ejecuta: `FiltroEnrutamiento` ya dejó la
        compuerta en `ctx.procede_recuperar`, y aquí se respeta. Omitir
        dejando traza es lo que distingue esto de un salto silencioso: la
        cadena original queda reconstruible aunque un paso no se haya
        ejecutado.
        """
        return self._ejecutar_lista(self._calientes, ctx, al_iniciar=al_iniciar)

    def ejecutar_fria(self, ctx: ContextoTurno) -> ContextoTurno:
        """La ruta fría: consolidaciones fuera del camino crítico (S2).

        Se llama **después** de que la respuesta del turno ya salió —nunca
        antes, o dejaría de ser fría—. Recibe el `ContextoTurno` final de
        `ejecutar()`, para que un filtro frío pueda leer lo que el turno
        completo produjo.
        """
        return self._ejecutar_lista(self._frias, ctx)

    def _ejecutar_lista(
        self, filtros: tuple[Filtro, ...], ctx: ContextoTurno, *, al_iniciar=None
    ) -> ContextoTurno:
        for filtro in filtros:
            if isinstance(filtro, FiltroRecuperacion) and not ctx.procede_recuperar:
                ctx = ctx.con_traza(
                    TrazaFiltro(
                        filtro=filtro.nombre,
                        latencia_ms=0.0,
                        ruta=filtro.ruta,
                        metadatos={
                            "omitido": True,
                            "motivo": "la compuerta de contexto del filtro 4 "
                            "decidió no recuperar para este turno",
                        },
                    )
                )
                continue
            if al_iniciar is not None:
                with suppress(Exception):  # La observación no gobierna el cálculo.
                    al_iniciar(filtro.nombre)
            try:
                ctx = filtro.ejecutar(ctx)
            except Exception as exc:
                raise ErrorDeOrquestacion(exc, ctx) from exc
        return ctx
