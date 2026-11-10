"""
matematica.py — Tipos del dominio para afirmaciones matemáticas y su veredicto
==============================================================================

Estos tipos no conocen SymPy, ni HTTP, ni base de datos. Es la regla N1 de
`ADR-009` §5.2 aplicada al modelo: el dominio define qué es una afirmación
matemática y qué es un veredicto; el adaptador decide con qué se comprueban.

Origen de cada decisión de diseño de este archivo:

- `ADR-008` V1 — sin verificación posible **no hay aprobación**. Por eso
  `Veredicto` no tiene valor por defecto favorable y `Verificacion.aprobada`
  exige que el veredicto sea explícitamente `VALIDA`.
- `ADR-008` C1 — el generador declara sus afirmaciones en bloques. Por eso
  existe `BloqueVerificable` y no una función que busque matemáticas en prosa.
- `ADR-013` §6.3 — el precómputo entrega pasos con la **regla** etiquetada,
  no solo el resultado.
- `PM-B26` — `funcion_js` y `derivada_js` en `Precomputo` son la sombra
  tipada de `PresentationHints` (`f_js`, `df_js`) de
  `Calculadora de Derivadas/repo-2/backend/ports/derivation_port.py`: datos
  que solo sirven para dibujar, y el dominio los puede ignorar. No se trae el
  tercer campo de ese origen, `graph` (`{"is_limit": bool}`): esta cadena ya
  distingue límite de derivada en `ContextoTurno.es_limite` (`PM-B24`), así
  que duplicar la señal aquí repetiría un dato que ya existe en otro sitio.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Veredicto(str, Enum):
    """Resultado de comprobar una afirmación matemática.

    **No existe un valor por defecto favorable.** `ADR-008` §1.1 documenta que
    la iteración 0 aprobaba cuando ningún patrón casaba, y que ese fue el
    defecto crítico de los seis encontrados: un verificador que no sabe qué no
    vio, aprueba lo que no entiende.
    """

    VALIDA = "valida"
    INVALIDA = "invalida"
    NO_VERIFICABLE = "no_verificable"   # no se pudo comprobar → no se aprueba


@dataclass(frozen=True)
class BloqueVerificable:
    """Una afirmación matemática que el generador declara explícitamente.

    `ADR-008` C1: la extracción pasa de reconocer matemáticas en prosa libre a
    **leer una estructura**. La consecuencia que importa es que la matemática
    fuera de bloque es detectable, y por tanto rechazable.
    """

    identificador: str
    izquierda: str
    derecha: str
    relacion: str = "="
    regla_declarada: str | None = None


@dataclass(frozen=True)
class Verificacion:
    """Veredicto sobre un bloque, con lo que `RF-REG-03` exige registrar."""

    bloque: str
    veredicto: Veredicto
    herramienta: str
    latencia_ms: float
    detalle: str = ""

    @property
    def aprobada(self) -> bool:
        return self.veredicto is Veredicto.VALIDA


@dataclass(frozen=True)
class InformeVerificacion:
    """Resultado de barrer **todas** las afirmaciones de una respuesta.

    `ADR-008` V1 fija el barrido exhaustivo: la iteración 0 usaba `search` en
    lugar de `finditer` y comprobaba solo la primera coincidencia.
    """

    verificaciones: tuple[Verificacion, ...] = ()
    matematica_fuera_de_bloque: bool = False

    @property
    def aprobada(self) -> bool:
        """Aprueba solo si **todas** las afirmaciones son válidas.

        La matemática fuera de bloque invalida el informe entero: no se puede
        afirmar que se verificó todo si hay expresiones que nadie declaró.
        """
        if self.matematica_fuera_de_bloque:
            return False
        if not self.verificaciones:
            return False          # nada que verificar tampoco es una aprobación
        return all(v.aprobada for v in self.verificaciones)

    @property
    def nada_que_verificar(self) -> bool:
        """No había ninguna afirmación que comprobar. **No es un fallo.**

        `aprobada` sigue dando `False` aquí y está bien: no se puede aprobar lo
        que no se miró. Pero **«no había nada» y «lo que había no se sostiene»
        no son lo mismo**, y hasta el 2026-08-13 el filtro 9 las trataba igual:
        descendía el nivel con el motivo «verificación no superada» en los dos
        casos. `PM-V15` lo midió — **16 turnos, 16 descensos de 16**, incluidos
        los sondeos de nivel 1, que `ADR-014` C4 declara correctos sin ninguna
        afirmación.

        Es la misma distinción que `dominio/filtros/diagnostico.py` hace desde
        la octava sesión: *«no verificable» no es «se equivocó»*. Aquí es «no
        había nada que verificar» no es «lo verificado falló».

        ⚠️ Esto **no relaja `ADR-008` V1**. Sin verificación no hay aprobación
        **de una afirmación**, y eso sigue en pie: lo que cambia es que la
        ausencia de afirmaciones deje de contarse como afirmación fallida. La
        matemática fuera de bloque tampoco entra aquí — eso sí es un fallo, y
        de los graves, porque es lo que `C1` existe para detectar.
        """
        return not self.verificaciones and not self.matematica_fuera_de_bloque

    @property
    def motivo_de_rechazo(self) -> str:
        if self.matematica_fuera_de_bloque:
            return "hay expresiones matemáticas fuera de bloque declarado"
        if not self.verificaciones:
            return "no se declaró ninguna afirmación verificable"
        fallidas = [v for v in self.verificaciones if not v.aprobada]
        if fallidas:
            return "afirmaciones no válidas: " + ", ".join(v.bloque for v in fallidas)
        return ""


# ── Precómputo (ADR-013) ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class PasoDerivacion:
    """Un paso del desarrollo, con la regla que lo justifica.

    La `regla` no es decoración: es lo que el nivel 2 de la escala de
    divulgación nombra **sin dar el resultado** (`ADR-013` §6.3).
    """

    tipo: str
    latex: str
    regla: str


@dataclass(frozen=True)
class Precomputo:
    """Lo que el motor simbólico entrega al generador antes del prompt.

    ⚠️ **No es una respuesta para el estudiante.** Entra al contexto del
    generador; la escala de divulgación decide qué fracción se revela
    (`ADR-013` §2). El riesgo de que se filtre está registrado como `R-22`.
    """

    resultado: str = ""
    #: `PM-B31` · el mismo resultado, en **notación corriente** — `2*x*cos(x^2)`,
    #: la de `ADR-014` §5.2— en vez de LaTeX.
    #:
    #: Existe porque `resultado` es LaTeX y **una afirmación no se puede
    #: declarar en LaTeX**: la regla 4 del contrato pide notación corriente, y
    #: es la única forma en que el motor puede volver a verificarla. `D-21`
    #: daba por hecho que el material del respaldo ya estaba —*«`PasoDerivacion`
    #: ya lleva `latex` y `regla`»*— y en la notación equivocada no lo estaba.
    #:
    #: Vacío si no se pudo convertir, por la misma razón que `funcion_js`: sin
    #: él no hay respaldo, y eso se declara en vez de emitir LaTeX crudo.
    resultado_corriente: str = ""
    #: Transformación algebraica opcional, comprobable por equivalencia antes
    #: de evaluar un límite. No sustituye la cadena completa de pasos.
    simplificacion_corriente: str = ""
    #: Expresiones del límite tras aplicaciones sucesivas de L'Hôpital;
    #: cada límite se verifica otra vez antes de mostrarse al estudiante.
    limites_intermedios: tuple[str, ...] = ()
    #: Primer despliegue de una regla de derivación, comprobable antes de
    #: mostrar el resultado simplificado.
    paso_intermedio_corriente: str = ""
    paso_intermedio_regla: str = ""
    #: Derivadas de partes internas calculadas por el CAS. Sólo se revelan
    #: cuando el estudiante ya acertó, y cada una vuelve a verificarse.
    componentes_derivada: tuple[tuple[str, str, str], ...] = ()
    sin_limite_bilateral: bool = False
    limite_izquierdo_corriente: str = ""
    limite_derecho_corriente: str = ""
    pasos: tuple[PasoDerivacion, ...] = ()
    regla_critica: str = ""
    concepciones_candidatas: tuple[str, ...] = ()
    error: str | None = None
    #: Expresión exacta que se entregó al adaptador simbólico para producir
    #: `funcion_js`. Evita reconstruir después la procedencia desde un contexto
    #: que pudo avanzar a otra expresión o recurrir al historial.
    expresion_fuente: str = ""
    #: `PM-B26` · la función original, como cadena JavaScript evaluable con
    #: `new Function('x', 'return ' + funcion_js)`. Vacío si no se pudo
    #: convertir. Para límites contiene la función original, nunca el valor
    #: del límite: esa distinción es esencial ante huecos y saltos.
    funcion_js: str = ""
    #: `PM-B26` · la derivada, en la misma forma. Es la mitad que **revela el
    #: resultado**: quien decide si viaja al bloque `grafica` del turno es
    #: `adaptadores/entrantes/http/turno.py`, con el mismo criterio que ya
    #: decide si un bloque de notación sella `verificado` — no este tipo.
    derivada_js: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None

    def truncado(self) -> Precomputo:
        """Versión sin resultado, pasos ni presentación, para el nivel 1 de
        divulgación.

        `ADR-013` §7.3 la propone como mitigación de `R-22`: **truncar es más
        fuerte que instruir**. Se deja disponible desde el primer incremento
        aunque su adopción sea decisión posterior, porque construirla después
        obligaría a tocar el filtro. `funcion_js`/`derivada_js` quedan fuera
        por la misma razón que `resultado`: son la respuesta, no la
        orientación privada que este método sí deja pasar.
        """
        return Precomputo(
            regla_critica=self.regla_critica,
            concepciones_candidatas=self.concepciones_candidatas,
        )
