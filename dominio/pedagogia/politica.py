"""
politica.py — La tabla que elige estrategia, intervención y modificadores
============================================================================

**Ésta es la regla pedagógica del sistema y está escrita para poder leerse sin
leer código alrededor**, igual que `andamiaje.py` lo estaba para la elección de
plantilla. Quien quiera revisar la pedagogía —una docente, el jurado— lee la
tabla `POLITICA` de abajo y ningún archivo más.

Qué sustituye, y por qué no era suficiente
---------------------------------------------
Hasta la fase 4 la elección estaba repartida en tres sitios que no se hablaban:
la escala de divulgación (`dominio/arbitraje/divulgacion.py`), la jerarquía de
intervención (`dominio/arbitraje/intervencion.py`) y la tabla de plantillas
(`dominio/pedagogia/andamiaje.py`). Ninguno de los tres decidía **qué clase de
respuesta** era el turno, así que la respuesta era siempre la misma: preguntar.
Medido sobre el banco congelado, **37 de 43 prompts mandaban preguntar** y
**los 43 salían con el nivel de intervención 5**.

Cómo está escrita, y por qué así
-----------------------------------
Una **tupla de reglas ordenada**, no una cascada de `if`. Cada regla declara su
nombre, su condición sobre una `Situacion` —que es todo lo observable del
turno— y qué estrategia produce. `decidir()` las recorre entera, se queda con
la primera que se cumple y **conserva las demás que también se cumplían** como
descartadas, con su motivo.

Eso es lo que `RF-REG-06` pide y lo que un `if/elif` no puede dar: la decisión
se puede reconstruir sin mirar la forma del código, y el análisis contrafactual
del OE4 tiene qué mirar.

El orden de la tabla, justificado fila a fila
------------------------------------------------
| # | Regla | Por qué está donde está |
|---|---|---|
| 1 | preferencia del estudiante | Si pidió otra forma y esa forma es segura, manda él. Va primero porque cualquier otra regla que ganara le estaría ignorando |
| 2 | desarrollo autorizado | `RF-GEN-05`: tres intentos o confirmación explícita, **y sobre el ejercicio activo** (`DEC-R3`). Es la ÚNICA puerta al desarrollo, y va antes que el diagnóstico para que un `E4` recién visto no devuelva a preguntar a quien ya se ganó la respuesta (`D-20`) |
| 3 | bloqueo | Quien declara bloqueo no pide teoría: dice dónde está. Antes que las peticiones de contenido |
| 4-7 | el diagnóstico `E1`–`E4` | Es un dato sobre lo que el estudiante eligió, no una conjetura sobre la forma de su expresión. Manda sobre la lectura del motor simbólico |
| 8 | intento correcto | Verificado por el motor. Antes que las demás lecturas del intento: reconocerlo y reducir apoyo |
| 9 | sondeo de dos niveles | Cuando hay ítem escrito y la duda está sostenida, la jugada es preguntar por la razón |
| 10-11 | intento incorrecto | Con concepción candidata, conflicto conceptual; sin ella, señalar lo que escribió |
| 12 | intento sin verificar | La incertidumbre se declara y se acompaña, no se convierte en corrección |
| 13-18 | las peticiones de contenido | De la intención directa a la respuesta directa |
| 19 | ambigua | **Una** pregunta de aclaración. Nunca socrática por defecto |

La regla que la política F impone sobre toda la tabla · `DEC-R1`
-------------------------------------------------------------------
**Ninguna señal conductual elige una estrategia que revele matemática, ni
aumenta cuánta se revela.** Se comprueba estructuralmente y en dos sitios:

- aquí, porque la única regla que produce `DESARROLLO_GUIADO` es la 2 y su
  condición sólo mira `nivel_divulgacion` y `alcance_divulgacion`;
- en `dominio/arbitraje/divulgacion.py`, porque ese nivel lo abren únicamente
  los intentos y la confirmación —el **trabajo** del estudiante—, y las cinco
  señales conductuales quedan registradas en `no_escalan`.

Las señales entran por `nivel_intervencion`, que en esta tabla sólo produce
`PRIMER_PASO_ANTE_BLOQUEO` —que no revela nada— y **modificadores**: tono,
apoyo afectivo, cambio de representación, grado de detalle y densidad de
preguntas.

✅ La contradicción que la revisión R1 cerró
-----------------------------------------------
Aquí decía que la política F.3 y el criterio de aceptación de `RF-GEN-05`
—*«nivel 2 tras 2 intentos fallidos en el mismo paso o ante FAH/PS-Anx alto»*—
no podían ser ciertos a la vez, y que la entrega dejaba el fragmento detenido
con la contradicción dicha.

**`DEC-R1` la resuelve en la dirección de la política**, y esta sección
sustituye a aquélla porque una contradicción declarada y resuelta que se sigue
documentando como abierta es peor que no haberla escrito: quien lea el módulo
buscará una tensión que ya no existe. FAH y PS-Anx dejan de abrir el nivel 2.

Y `DEC-R3` añade la mitad que faltaba: una petición **explícita** de teoría o
de ejemplo sí autoriza nivel 2, con alcance `analogo`. No es una excepción a
`DEC-R1` —una petición escrita no es una inferencia sobre el estudiante— y no
autoriza el ejercicio activo, que es lo que la regla 2 comprueba.


"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from dominio.arbitraje.divulgacion import (
    ALCANCE_EJERCICIO_ACTIVO,
    CORRECCION,
    Señales,
)
from dominio.arbitraje.intervencion import (
    ANSIEDAD_EXPLICITA,
    AUTOEFICACIA_BAJA,
    BLOQUEO_SIN_INTENTO,
    CICLO_NEGATIVO,
    NOMBRE_INTERVENCION,
)
from dominio.arbitraje.intervencion import (
    AUTORREGULACION as T6_AUTORREGULACION,
)
from dominio.diagnostico.clasificador import (
    AVANZAR,
    REMEDIAR,
    SEÑALAR_PASO,
    SONDEO_KQ2,
    Diagnostico,
)
from dominio.pedagogia import estrategias as E
from dominio.pedagogia.intenciones import (
    AMBIGUA,
    APLICACION_TRANSFERENCIA,
    BLOQUEO_EXPLICITO,
    CAMBIO_ESTRATEGIA,
    CONSULTA_CONCEPTUAL,
    EXPLICACION_DIRECTA,
    INTENTO_RESOLUCION,
    PETICION_SOLUCION,
    PRACTICA_GUIADA,
    SOLICITUD_EJEMPLO,
    Intencion,
)

# ── Los veredictos del intento del estudiante ───────────────────────────────
#
# Los produce `dominio/filtros/intento.py` con el motor simbólico. `""` es «no
# se intentó comprobar»; `no_verificable` es «se intentó y no se pudo», que no
# es lo mismo y no se trata igual.
VALIDA = "valida"
INVALIDA = "invalida"
NO_VERIFICABLE = "no_verificable"

# ── De dónde salió lo que se sabe del estado conceptual ─────────────────────
DE_DOS_NIVELES = "diagnostico_two_tier"
DE_VERIFICACION = "verificacion_del_intento"
DE_PRECOMPUTO = "concepcion_candidata_del_motor_simbolico"
SIN_DIAGNOSTICO = "sin_diagnostico"


@dataclass(frozen=True)
class Situacion:
    """Todo lo observable del turno, y **nada más**.

    Es el contrato de entrada del selector. Que sea un tipo cerrado y no un
    `ContextoTurno` es deliberado: la política no puede mirar el texto del
    estudiante ni el prompt, sólo lo que los filtros anteriores ya decidieron.
    Si mañana necesita algo nuevo, ese algo tiene que producirlo un filtro y
    declararse aquí — no leerse por debajo.
    """

    intencion: Intencion
    señales: Señales = field(default_factory=Señales)
    nivel_divulgacion: int = 1
    #: `DEC-R3` · sobre qué autoriza revelar el nivel. La regla del desarrollo
    #: lo exige: un nivel 2 concedido por pedir un ejemplo no puede convertirse
    #: en el desarrollo del ejercicio que el estudiante tiene delante.
    alcance_divulgacion: str = ALCANCE_EJERCICIO_ACTIVO
    nivel_intervencion: int = T6_AUTORREGULACION
    diagnostico: Diagnostico | None = None
    concepciones_candidatas: tuple[str, ...] = ()
    veredicto_del_intento: str = ""
    #: Si el banco tiene un ítem de dos niveles planteable para el nodo activo
    #: y el tope de frecuencia lo permite. Lo resuelve `dominio/pedagogia/
    #: sondeo.py`, que es donde está la regla.
    hay_item_ofrecible: bool = False
    #: La preferencia del estudiante de que el estilo NO se adapte a sus
    #: expresiones. Es de la conversación, la aporta el borde, y suprime los
    #: modificadores que salen de señales conductuales.
    sin_adaptacion: bool = False
    #: La estrategia del turno anterior de esta conversación, para saber si
    #: hay cambio que anunciar. Vacía en el primero.
    estrategia_previa: str = ""
    hay_ejercicio_activo: bool = False

    @property
    def procedencia_del_diagnostico(self) -> str:
        if self.diagnostico is not None:
            return DE_DOS_NIVELES
        if self.veredicto_del_intento in (VALIDA, INVALIDA):
            return DE_VERIFICACION
        if self.concepciones_candidatas:
            return DE_PRECOMPUTO
        return SIN_DIAGNOSTICO


@dataclass(frozen=True)
class DecisionPedagogica:
    """La decisión del turno, entera. `RF-REG-06`, `G1`.

    Con esto se puede reconstruir por qué el sistema respondió como respondió
    **sin consultar ningún log**: qué se evaluó, qué ganó, qué más se cumplía,
    qué no se pudo saber y qué se habría hecho si la ganadora no hubiera
    aplicado.
    """

    estrategia: str = E.ACLARACION_BREVE
    motivo: str = ""
    #: Todas las reglas evaluadas, en el orden de la tabla.
    candidatas: tuple[str, ...] = ()
    #: `(regla, por qué no ganó)` de las que también se cumplían.
    descartadas: tuple[tuple[str, str], ...] = ()
    #: Lo que no se pudo saber en este turno y habría cambiado la decisión.
    incertidumbre: tuple[str, ...] = ()
    #: Qué se habría hecho si la ganadora no hubiera aplicado.
    fallback: str = E.ACLARACION_BREVE
    procedencia_del_diagnostico: str = SIN_DIAGNOSTICO
    #: La intervención de `T6` que gobierna los modificadores.
    nivel_intervencion: int = T6_AUTORREGULACION
    modificadores: tuple[str, ...] = ()
    #: Los modificadores que se habrían aplicado y la preferencia del
    #: estudiante suprimió. Se conservan porque la preferencia tiene que
    #: quedar **trazada**, no sólo obedecida.
    modificadores_suprimidos: tuple[str, ...] = ()
    #: La frase neutral que puede verse cuando la estrategia cambia. Vacía si
    #: no cambió o si la estrategia no lleva anuncio. Nunca nombra una señal.
    frase_visible: str = ""

    @property
    def nombre_de_la_intervencion(self) -> str:
        return NOMBRE_INTERVENCION.get(self.nivel_intervencion, "")

    def como_dict(self) -> dict:
        return {
            "estrategia": self.estrategia,
            "motivo": self.motivo,
            "candidatas": list(self.candidatas),
            "descartadas": [list(d) for d in self.descartadas],
            "incertidumbre": list(self.incertidumbre),
            "fallback": self.fallback,
            "procedencia_del_diagnostico": self.procedencia_del_diagnostico,
            "nivel_intervencion": self.nivel_intervencion,
            "intervencion": self.nombre_de_la_intervencion,
            "modificadores": list(self.modificadores),
            "modificadores_suprimidos": list(self.modificadores_suprimidos),
            "frase_visible": self.frase_visible,
        }


@dataclass(frozen=True)
class Regla:
    """Una fila de la tabla: nombre, condición, estrategia y por qué."""

    nombre: str
    condicion: Callable[[Situacion], bool]
    estrategia: str
    motivo: str


def _clase(situacion: Situacion) -> str:
    return situacion.intencion.clase


def _estrategia_pedida_segura(situacion: Situacion) -> bool:
    """Pidió una estrategia concreta y esa estrategia no revela matemática.

    Pedir «explícamelo» es seguro y se respeta. Pedir el desarrollo por la vía
    del cambio de estrategia **no** lo es: `RF-GEN-04` fija que la insistencia
    no abre esa puerta, y renombrarla no la abre tampoco.
    """
    pedida = situacion.intencion.estrategia_solicitada
    return bool(pedida) and pedida not in E.ESTRATEGIAS_QUE_REVELAN


def _diagnostico_es(situacion: Situacion, etiqueta: str) -> bool:
    return situacion.diagnostico is not None and situacion.diagnostico.siguiente == etiqueta


#: 🔴 **La tabla.** Ver la cabecera del módulo sobre por qué el orden es el que
#: es. Cada fila se puede leer sola: nombre, cuándo, qué produce y por qué.
POLITICA: tuple[Regla, ...] = (
    Regla(
        "preferencia_del_estudiante",
        lambda s: _clase(s) == CAMBIO_ESTRATEGIA and _estrategia_pedida_segura(s),
        "",  # la estrategia la dice el propio estudiante · ver `decidir()`
        "el estudiante pidió una estrategia concreta y es segura",
    ),
    Regla(
        "cambio_de_estrategia_sin_concretar",
        lambda s: _clase(s) == CAMBIO_ESTRATEGIA,
        E.EXPLICACION_TEORICA_DIRECTA,
        "pidió otra forma sin decir cuál: se explica directamente y se cambia de "
        "representación",
    ),
    Regla(
        "desarrollo_autorizado",
        # `DEC-R3` · las DOS condiciones, y la segunda es la que impide que una
        # explicación o un ejemplo se conviertan por accidente en el desarrollo
        # del ejercicio activo. Hoy sólo el trabajo del estudiante produce el
        # nivel 3, así que la segunda es redundante **por construcción** y se
        # escribe igual: la redundancia es la que sobrevive a que mañana
        # aparezca otra puerta al nivel 3 con otro alcance.
        lambda s: (
            s.nivel_divulgacion >= CORRECCION
            and s.alcance_divulgacion == ALCANCE_EJERCICIO_ACTIVO
        ),
        E.DESARROLLO_GUIADO,
        "la escala de divulgación autorizó el desarrollo del ejercicio activo "
        "(RF-GEN-05)",
    ),
    Regla(
        "grafica_solicitada",
        lambda s: s.intencion.estrategia_solicitada == E.CAMBIO_DE_REPRESENTACION,
        E.EXPLICACION_TEORICA_DIRECTA,
        "pidió una gráfica: se atiende en este turno y se explica cómo leerla, "
        "sin exigir otra respuesta previa",
    ),
    Regla(
        "bloqueo_declarado",
        lambda s: _clase(s) == BLOQUEO_EXPLICITO,
        E.PRIMER_PASO_ANTE_BLOQUEO,
        "declaró bloqueo: se le da un primer paso concreto, no otra pregunta",
    ),
    Regla(
        "bloqueo_sin_intento",
        lambda s: s.nivel_intervencion == BLOQUEO_SIN_INTENTO,
        E.PRIMER_PASO_ANTE_BLOQUEO,
        "T6 nivel 1: señal de bloqueo sostenida y ningún intento en el problema",
    ),
    Regla(
        "diagnostico_E1_comprension",
        lambda s: _diagnostico_es(s, AVANZAR),
        E.RESPUESTA_FACTUAL_BREVE,
        "E1: comprensión demostrada. No se explica lo que ya se entendió",
    ),
    Regla(
        "diagnostico_E2_acierto_sin_comprension",
        lambda s: _diagnostico_es(s, SONDEO_KQ2),
        E.SCAFFOLDING_KQ,
        "E2: acertó sin poder decir por qué. Hay que hacer explícita la regla que usó",
    ),
    Regla(
        "diagnostico_E3_error_de_ejecucion",
        lambda s: _diagnostico_es(s, SEÑALAR_PASO),
        E.DIALOGO_SOCRATICO_APOS,
        "E3: sabe lo que hace y falló al hacerlo. Se señala el paso; no hay "
        "concepción que remediar",
    ),
    Regla(
        "diagnostico_E4_concepcion_erronea",
        lambda s: _diagnostico_es(s, REMEDIAR),
        E.CONFLICTO_CONCEPTUAL,
        "E4: la razón que eligió delata una concepción. Se contrasta, no se corrige",
    ),
    Regla(
        "intento_correcto",
        lambda s: s.veredicto_del_intento == VALIDA,
        E.RESPUESTA_FACTUAL_BREVE,
        "el motor simbólico comprobó que su propuesta es correcta: se reconoce y "
        "se reduce el apoyo",
    ),
    Regla(
        "sondeo_de_dos_niveles",
        lambda s: s.hay_item_ofrecible,
        E.DIAGNOSTICO_TWO_TIER,
        "la duda está sostenida y el nodo tiene ítem escrito: se pregunta por la razón",
    ),
    Regla(
        "intento_incorrecto_con_concepcion",
        lambda s: s.veredicto_del_intento == INVALIDA and bool(s.concepciones_candidatas),
        E.CONFLICTO_CONCEPTUAL,
        "su propuesta no cuadra y la forma de la expresión sugiere una concepción: "
        "se contrasta con un caso donde no se sostiene",
    ),
    Regla(
        "intento_incorrecto",
        lambda s: s.veredicto_del_intento == INVALIDA,
        E.SCAFFOLDING_KQ,
        "su propuesta no cuadra: se señala el trozo concreto que escribió",
    ),
    Regla(
        "intento_sin_verificar",
        lambda s: _clase(s) == INTENTO_RESOLUCION,
        E.PRACTICA_GUIADA,
        "propuso algo que no se pudo comprobar: se acompaña el paso sin afirmar "
        "que esté mal",
    ),
    Regla(
        "consulta_conceptual",
        lambda s: _clase(s) == CONSULTA_CONCEPTUAL,
        E.EXPLICACION_TEORICA_DIRECTA,
        "preguntó qué es o por qué: se explica, no se le devuelve otra pregunta",
    ),
    Regla(
        "explicacion_directa",
        lambda s: _clase(s) == EXPLICACION_DIRECTA,
        E.EXPLICACION_TEORICA_DIRECTA,
        "pidió que se le explicara: se explica sin exigirle contestar antes",
    ),
    Regla(
        "solicitud_ejemplo",
        lambda s: _clase(s) == SOLICITUD_EJEMPLO,
        E.EJEMPLO_TRABAJADO,
        "pidió un ejemplo: se le da uno resuelto diciendo qué ilustra",
    ),
    Regla(
        "aplicacion_transferencia",
        lambda s: _clase(s) == APLICACION_TRANSFERENCIA,
        E.EXPLICACION_TEORICA_DIRECTA,
        "pregunta cómo aplicar lo mismo a otro caso: se explica la relación con el "
        "problema anterior",
    ),
    Regla(
        "practica_guiada",
        lambda s: _clase(s) == PRACTICA_GUIADA,
        E.PRACTICA_GUIADA,
        "quiere resolverlo él: se sostiene el paso y el trabajo principal se queda "
        "en el estudiante",
    ),
    Regla(
        "peticion_de_solucion",
        lambda s: _clase(s) == PETICION_SOLUCION,
        E.PRACTICA_GUIADA,
        "pidió la respuesta y la escala no la autoriza (RF-GEN-04): se ofrece "
        "resolverlo juntos",
    ),
    Regla(
        "ambigua_con_ejercicio",
        lambda s: _clase(s) == AMBIGUA and s.hay_ejercicio_activo and not s.intencion.es_cortesia,
        E.PRIMER_PASO_ANTE_BLOQUEO,
        "hay un ejercicio explícito: aporta un paso explicado y una sola pregunta opcional; no atribuye bloqueo",
    ),
    Regla(
        "ambigua",
        lambda s: _clase(s) == AMBIGUA,
        E.ACLARACION_BREVE,
        "no hay evidencia suficiente de qué necesita: una sola pregunta breve",
    ),
)


# ── Los modificadores que produce cada nivel de `T6` ────────────────────────
#
# **Esto es lo que hace productivo `nivel_intervencion`.** Hasta la fase 4 se
# calculaba, se registraba y no lo leía nadie: los 43 turnos del banco salían
# con el nivel 5 y el nivel no cambiaba nada. Cada fila de aquí es un efecto
# comprobable sobre el prompt.
_MODIFICADORES_DE_T6 = {
    BLOQUEO_SIN_INTENTO: (E.APOYO_AFECTIVO_NEUTRAL, E.MENOS_PREGUNTAS),
    CICLO_NEGATIVO: (E.CAMBIO_DE_REPRESENTACION, E.MENOS_PREGUNTAS),
    AUTOEFICACIA_BAJA: (E.TONO_NO_EVALUATIVO, E.GRADO_DE_DETALLE),
    ANSIEDAD_EXPLICITA: (E.TONO_NO_EVALUATIVO, E.APOYO_AFECTIVO_NEUTRAL),
    T6_AUTORREGULACION: (E.AUTORREGULACION,),
}


def _modificadores(situacion: Situacion, estrategia: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Los modificadores del turno, y los que la preferencia suprimió.

    Los de `T6` salen de una señal conductual; los que el estudiante pide
    —menos preguntas, otra representación— salen de lo que escribió. La
    preferencia de no adaptación suprime **los primeros y sólo los primeros**:
    respetar «no te adaptes a cómo escribo» no puede llevarse por delante
    «hazme menos preguntas», que es una petición suya.
    """
    de_señal = list(_MODIFICADORES_DE_T6.get(situacion.nivel_intervencion, ()))
    suprimidos: list[str] = []
    if situacion.sin_adaptacion:
        suprimidos = de_señal
        de_señal = []

    pedidos: list[str] = []
    if situacion.intencion.pide_menos_preguntas:
        pedidos.append(E.MENOS_PREGUNTAS)
    if situacion.intencion.estrategia_solicitada == E.CAMBIO_DE_REPRESENTACION:
        pedidos.append(E.CAMBIO_DE_REPRESENTACION)
    if situacion.intencion.clase == CAMBIO_ESTRATEGIA and not situacion.intencion.estrategia_solicitada:
        pedidos.append(E.CAMBIO_DE_REPRESENTACION)

    # `MENOS_PREGUNTAS` sobre una aclaración sería contradictorio: la aclaración
    # ES una pregunta. Se retira y se dice.
    aplicados = []
    for modificador in de_señal + pedidos:
        # Una invitación de autorregulación no debe convertir explicación,
        # ejemplo o primer paso en una exigencia de contestar antes de ayudar.
        if modificador == E.AUTORREGULACION and (
            estrategia not in E.ESTRATEGIAS_SOCRATICAS
            or situacion.intencion.pide_menos_preguntas
        ):
            suprimidos.append(modificador)
            continue
        if modificador == E.MENOS_PREGUNTAS and estrategia == E.ACLARACION_BREVE:
            continue
        if modificador not in aplicados:
            aplicados.append(modificador)
    return tuple(aplicados), tuple(dict.fromkeys(suprimidos))


def _incertidumbre(situacion: Situacion) -> tuple[str, ...]:
    """Lo que no se pudo saber y habría cambiado la decisión.

    No es una lista de avisos: es la mitad de la decisión que dice **hasta
    dónde llega lo que se sabe**. Un selector que sólo publicara su resultado
    haría creer que decidió con la información completa.
    """
    faltas: list[str] = []
    if situacion.diagnostico is None:
        faltas.append(
            "sin diagnóstico de dos niveles: el estado conceptual no está medido "
            "en este turno"
        )
    if situacion.veredicto_del_intento == NO_VERIFICABLE:
        faltas.append(
            "el intento del estudiante no se pudo comprobar con el motor simbólico"
        )
    if situacion.concepciones_candidatas and situacion.diagnostico is None:
        faltas.append(
            "la concepción es una lectura probabilística de la forma de la "
            "expresión, no un diagnóstico"
        )
    if situacion.intencion.origen != "regla":
        faltas.append("la intención no la resolvió ninguna regla del catálogo v1")
    return tuple(faltas)


def decidir(situacion: Situacion) -> DecisionPedagogica:
    """La estrategia, la intervención y los modificadores de este turno.

    Recorre `POLITICA` entera —no corta en la primera— para poder decir qué más
    se cumplía. Es lo que separa una decisión trazable de un `if` con suerte.
    """
    activas: list[tuple[Regla, str]] = []
    for regla in POLITICA:
        if regla.condicion(situacion):
            estrategia = regla.estrategia or situacion.intencion.estrategia_solicitada
            activas.append((regla, estrategia))

    if not activas:
        # No puede ocurrir con la tabla de hoy —`ambigua` cierra el catálogo—
        # pero si alguien añade una clase y olvida su fila, el sistema pregunta
        # en vez de inventarse una estrategia. Es el mismo piso que `ADR-007` I4
        # fija para la intención.
        ganadora_estrategia = E.ACLARACION_BREVE
        motivo = "ninguna regla de la política se cumple: se pide una aclaración"
        descartadas: tuple[tuple[str, str], ...] = ()
        fallback = E.ACLARACION_BREVE
    else:
        regla, ganadora_estrategia = activas[0]
        motivo = regla.motivo
        descartadas = tuple(
            (otra.nombre, f"también se cumplía, pero «{regla.nombre}» tiene precedencia")
            for otra, _ in activas[1:]
        )
        fallback = activas[1][1] if len(activas) > 1 else E.ACLARACION_BREVE

    modificadores, suprimidos = _modificadores(situacion, ganadora_estrategia)

    cambia = bool(situacion.estrategia_previa) and situacion.estrategia_previa != ganadora_estrategia
    frase = E.frase_visible(ganadora_estrategia) if cambia else ""

    return DecisionPedagogica(
        estrategia=ganadora_estrategia,
        motivo=motivo,
        candidatas=tuple(r.nombre for r in POLITICA),
        descartadas=descartadas,
        incertidumbre=_incertidumbre(situacion),
        fallback=fallback,
        procedencia_del_diagnostico=situacion.procedencia_del_diagnostico,
        nivel_intervencion=situacion.nivel_intervencion,
        modificadores=modificadores,
        modificadores_suprimidos=suprimidos,
        frase_visible=frase,
    )
