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


VALIDA = "valida"
INVALIDA = "invalida"
NO_VERIFICABLE = "no_verificable"


DE_DOS_NIVELES = "diagnostico_two_tier"
DE_VERIFICACION = "verificacion_del_intento"
DE_PRECOMPUTO = "concepcion_candidata_del_motor_simbolico"
SIN_DIAGNOSTICO = "sin_diagnostico"


@dataclass(frozen=True)
class Situacion:

    intencion: Intencion
    señales: Señales = field(default_factory=Señales)
    nivel_divulgacion: int = 1

    alcance_divulgacion: str = ALCANCE_EJERCICIO_ACTIVO
    nivel_intervencion: int = T6_AUTORREGULACION
    diagnostico: Diagnostico | None = None
    concepciones_candidatas: tuple[str, ...] = ()
    veredicto_del_intento: str = ""

    hay_item_ofrecible: bool = False

    sin_adaptacion: bool = False

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

    estrategia: str = E.ACLARACION_BREVE
    motivo: str = ""

    candidatas: tuple[str, ...] = ()

    descartadas: tuple[tuple[str, str], ...] = ()

    incertidumbre: tuple[str, ...] = ()

    fallback: str = E.ACLARACION_BREVE
    procedencia_del_diagnostico: str = SIN_DIAGNOSTICO

    nivel_intervencion: int = T6_AUTORREGULACION
    modificadores: tuple[str, ...] = ()

    modificadores_suprimidos: tuple[str, ...] = ()

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

    nombre: str
    condicion: Callable[[Situacion], bool]
    estrategia: str
    motivo: str

def _clase(situacion: Situacion) -> str:
    return situacion.intencion.clase

def _estrategia_pedida_segura(situacion: Situacion) -> bool:
    pedida = situacion.intencion.estrategia_solicitada
    return bool(pedida) and pedida not in E.ESTRATEGIAS_QUE_REVELAN

def _diagnostico_es(situacion: Situacion, etiqueta: str) -> bool:
    return situacion.diagnostico is not None and situacion.diagnostico.siguiente == etiqueta

POLITICA: tuple[Regla, ...] = (
    Regla(
        "preferencia_del_estudiante",
        lambda s: _clase(s) == CAMBIO_ESTRATEGIA and _estrategia_pedida_segura(s),
        "",
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


_MODIFICADORES_DE_T6 = {
    BLOQUEO_SIN_INTENTO: (E.APOYO_AFECTIVO_NEUTRAL, E.MENOS_PREGUNTAS),
    CICLO_NEGATIVO: (E.CAMBIO_DE_REPRESENTACION, E.MENOS_PREGUNTAS),
    AUTOEFICACIA_BAJA: (E.TONO_NO_EVALUATIVO, E.GRADO_DE_DETALLE),
    ANSIEDAD_EXPLICITA: (E.TONO_NO_EVALUATIVO, E.APOYO_AFECTIVO_NEUTRAL),
    T6_AUTORREGULACION: (E.AUTORREGULACION,),
}


def _modificadores(situacion: Situacion, estrategia: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
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

    aplicados = []
    for modificador in de_señal + pedidos:

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
    activas: list[tuple[Regla, str]] = []
    for regla in POLITICA:
        if regla.condicion(situacion):
            estrategia = regla.estrategia or situacion.intencion.estrategia_solicitada
            activas.append((regla, estrategia))

    if not activas:

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
