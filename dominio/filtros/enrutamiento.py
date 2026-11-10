"""
enrutamiento.py — Filtro 4 · enrutamiento y compuerta de contexto
=====================================================================

`ADR-001` §6.3 le da dos responsabilidades: fijar `ctx.nodo_activo` —que el
filtro 5 **ya sabe recibir** (`dominio/filtros/recuperacion.py` lo consume
desde `PM-B02`)— y decidir si procede recuperar contexto para este turno.

Por qué reutiliza el criterio de `RecuperadorJerarquico` y no inventa otro
----------------------------------------------------------------------------
`adaptadores/salientes/recuperacion/jerarquico.py` ya identifica el nodo por
coincidencia léxica con la etiqueta (`identificar_nodo`), y **`R-17` mide que
falla en el 14,5 %** de los casos. Escribir un segundo criterio aquí no
mejoraría esa cifra: la duplicaría con la posibilidad añadida de que
diverjan. Este filtro no importa el adaptador —**N1** lo prohíbe, el dominio
no depende de infraestructura—, así que recibe la capacidad por inyección: el
protocolo `IdentificadorDeNodo` describe exactamente el método que
`RecuperadorJerarquico` ya implementa, y en producción es **la misma
instancia** la que se inyecta aquí y en el filtro 5. Es la misma disciplina
que el filtro 5 aplica con `PuertoCorpus`.

Por qué no se amplía `PuertoCorpus` con este método
------------------------------------------------------
Se pudo añadir `identificar_nodo` al puerto de recuperación en vez de definir
un protocolo aparte. Se descarta: `PuertoCorpus` ya tiene un contrato
estrecho —recuperar fragmentos— y los dobles que las pruebas de `test_corpus.py`
y `test_filtro_recuperacion.py` ya declaran dejarían de satisfacerlo sin
ganar nada a cambio. Un protocolo dedicado, del tamaño exacto de lo que este
filtro necesita, no obliga a tocar lo que ya funciona.

**Que no se identifique nodo es una rama normal**, no un error: es la entrada
de la configuración D de `ADR-002`, *«respaldo automático a vectorial puro
cuando no se identifica nodo de entrada»*.

La compuerta de contexto, y sus límites en esta sesión
----------------------------------------------------------
`ADR-007` I3: la intención **nunca decide sola**, pero si el filtro 2 ya
corrió y clasificó el turno como `emocional` **sin contenido matemático**,
recuperar contexto del corpus no aporta nada al turno — es la única
reducción que esta sesión implementa. Cualquier otra combinación,
**incluida `ambigua`**, toma la ruta segura: `procede_recuperar = True`. Si el
filtro 2 no corrió (`ctx.intencion == ""`), también se recupera: la rama seria
es la que menos asume.

**Este filtro no salta el filtro 5 por sí mismo.** Fija la compuerta en el
contexto; es el orquestador quien decide, con esa señal, si invoca el filtro
5. Repetir aquí esa decisión duplicaría la política de encadenado, que es
responsabilidad de `dominio/orquestador.py`.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol, runtime_checkable

from dominio.filtros.base import Filtro
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.intenciones import EMOCIONAL, familia_de
from dominio.puertos.plantillas import PuertoPlantillas


@runtime_checkable
class IdentificadorDeNodo(Protocol):
    """Lo que este filtro necesita del adaptador de recuperación, y nada más.

    `RecuperadorJerarquico` ya lo implementa; este protocolo no se satisface
    por herencia sino por forma, así que no hace falta declarar el vínculo
    en ningún lado — la misma instancia sirve para este filtro y para el 5.
    """

    def identificar_nodo(self, consulta: str) -> str | None:
        """Nodo de entrada por coincidencia léxica, o `None` si no se halla."""
        ...


class FiltroEnrutamiento(Filtro):
    """Filtro 4 de `ADR-001` §6.3."""

    nombre = "enrutamiento y compuerta de contexto"
    ruta = "caliente"

    def __init__(
        self,
        identificador: IdentificadorDeNodo,
        plantillas: PuertoPlantillas | None = None,
    ) -> None:
        self._identificador = identificador
        self._plantillas = plantillas

    def _ejercicio_declarado(self, ctx: ContextoTurno) -> str | None:
        """El nodo cuyo ítem plantea el ejercicio que este turno trae.

        🔴 **Paquete B, fase 4 R1.** Tiene precedencia sobre la coincidencia
        léxica, y el orden es la corrección: `cos(x)^3` iba a `N14` porque el
        perfil léxico ve «cos» y ése es el nodo trigonométrico, cuando
        `p-two-tier.md` declara esa composición como el ejercicio de `N08`. El
        tutor planteaba *«Deriva sen(x)·cos(x)»* a quien preguntaba por
        `cos(x)^3` — otro ejercicio, con otras cuatro razones.

        **Reconocer el ejercicio es más fuerte que reconocer su vocabulario**,
        y por eso va delante: el vocabulario dice de qué familia se habla, la
        expresión dice qué se está resolviendo. Cuando el contenido no declara
        ese ejercicio —el caso normal, hay tres ítems escritos— no dice nada y
        decide el léxico, exactamente como antes.
        """
        if self._plantillas is None:
            return None
        for expresion in self._candidatas(ctx):
            nodo = self._plantillas.nodo_del_ejercicio(expresion)
            if nodo:
                return nodo
        return None

    @staticmethod
    def _candidatas(ctx: ContextoTurno) -> tuple[str, ...]:
        """Las expresiones que pueden nombrar el ejercicio, en orden.

        Primero las de **este** mensaje, y después la del **problema activo**.
        La segunda no es un adorno: un turno como *«sigo sin verlo»* no trae
        ninguna expresión propia, y sin ella el enrutamiento perdía el
        ejercicio abierto y volvía a decidir por vocabulario — que es
        exactamente cómo `cos(x)^3` acababa en `N14` tres turnos después de
        haberse reconocido bien.

        El problema activo lo mantiene `dominio/pedagogia/problema.py` y llega
        aquí tal como estaba **al empezar el turno**; este filtro sólo lo lee.
        """
        del_turno = tuple(ctx.expresiones)
        estado = ctx.estado_conversacion
        activo = estado.problema.unidad.expresion if estado is not None else ""
        return (*del_turno, activo) if activo else del_turno

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        lexico = self._identificador.identificar_nodo(ctx.texto_estudiante)
        declarado = self._ejercicio_declarado(ctx)
        nodo = declarado or lexico

        # La FAMILIA de `ADR-007`, derivada de la clase del catálogo v1: la
        # compuerta razona sobre «esto es afectivo», no sobre cuál de las diez
        # clases es. Ver `dominio/pedagogia/intenciones.py::familia_de`.
        familia = familia_de(ctx.intencion)
        procede = not (familia == EMOCIONAL and not ctx.expresiones)

        meta = {
            "nodo_activo": nodo or "",
            "nodo_identificado": nodo is not None,
            # `RF-REG-06` · las dos lecturas quedan, no sólo la que ganó: sin
            # esto no se puede auditar cuándo el ejercicio declarado corrigió
            # al léxico ni cuándo coincidieron.
            "nodo_por_ejercicio_declarado": declarado or "",
            "nodo_por_coincidencia_lexica": lexico or "",
            "procede_recuperar": procede,
            "intencion_considerada": ctx.intencion,
            "familia_considerada": familia,
        }
        nuevo = replace(ctx, nodo_activo=nodo or "", procede_recuperar=procede)
        return nuevo, meta
