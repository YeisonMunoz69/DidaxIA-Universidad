from __future__ import annotations

from dataclasses import dataclass

from dominio.arbitraje.divulgacion import Señales


BLOQUEO_SIN_INTENTO = 1
CICLO_NEGATIVO = 2
AUTOEFICACIA_BAJA = 3
ANSIEDAD_EXPLICITA = 4
AUTORREGULACION = 5

NOMBRE_INTERVENCION = {
    BLOQUEO_SIN_INTENTO: "andamiaje de primer paso",
    CICLO_NEGATIVO: "ruptura del ciclo, formato Intérprete",
    AUTOEFICACIA_BAJA: "refuerzo vinculado a un logro concreto",
    ANSIEDAD_EXPLICITA: "reencuadre no punitivo del error",
    AUTORREGULACION: "autorregulación o metacognición",
}


@dataclass(frozen=True)
class DecisionIntervencion:

    nivel: int
    motivo: str
    descartadas: tuple[str, ...] = ()
    sin_evaluar: tuple[str, ...] = ()

    @property
    def nombre(self) -> str:
        return NOMBRE_INTERVENCION.get(self.nivel, NOMBRE_INTERVENCION[AUTORREGULACION])

def _nivel_1_bloqueo_sin_intento(
    señales: Señales, sin_evaluar: list[str]
) -> tuple[int, str] | None:

    if señales.miedo_a_pedir_ayuda_alto is None:
        sin_evaluar.append("miedo a pedir ayuda (sin modelo del estudiante · filtro 3)")
    if señales.ansiedad_alta is None:
        sin_evaluar.append("ansiedad alta (sin modelo del estudiante · filtro 3)")

    elevada = bool(señales.miedo_a_pedir_ayuda_alto) or bool(señales.ansiedad_alta)
    if elevada and señales.intentos_en_el_problema == 0:
        return BLOQUEO_SIN_INTENTO, "FAH o PS-Anx elevado sin intento"
    return None

def _nivel_de_un_campo(
    valor: bool | None, nivel: int, motivo: str, campo: str, sin_evaluar: list[str]
) -> tuple[int, str] | None:

    if valor:
        return nivel, motivo
    if valor is None:
        sin_evaluar.append(f"{campo} (sin modelo del estudiante · filtro 3)")
    return None

def decidir_intervencion(señales: Señales) -> DecisionIntervencion:
    sin_evaluar: list[str] = []
    candidatos = (
        _nivel_1_bloqueo_sin_intento(señales, sin_evaluar),
        _nivel_de_un_campo(
            señales.ciclo_negativo,
            CICLO_NEGATIVO,
            "ciclo de retroalimentación negativa",
            "ciclo negativo",
            sin_evaluar,
        ),
        _nivel_de_un_campo(
            señales.autoeficacia_baja,
            AUTOEFICACIA_BAJA,
            "autoeficacia estimada baja",
            "autoeficacia",
            sin_evaluar,
        ),

        _nivel_de_un_campo(
            señales.ansiedad_explicita,
            ANSIEDAD_EXPLICITA,
            "ansiedad expresada explícitamente",
            "ansiedad explícita",
            sin_evaluar,
        ),
    )
    activas = [c for c in candidatos if c is not None]

    if not activas:
        return DecisionIntervencion(
            nivel=AUTORREGULACION,
            motivo="ninguna condición de T6 se cumple: la autorregulación es el defecto",
            sin_evaluar=tuple(sin_evaluar),
        )

    ganadora = min(activas, key=lambda par: par[0])
    descartadas = tuple(
        motivo for nivel, motivo in activas if (nivel, motivo) != ganadora
    )
    return DecisionIntervencion(
        nivel=ganadora[0],
        motivo=ganadora[1],
        descartadas=descartadas,
        sin_evaluar=tuple(sin_evaluar),
    )
