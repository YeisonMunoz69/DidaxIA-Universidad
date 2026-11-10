from __future__ import annotations

from dataclasses import dataclass

from dominio.pedagogia.intenciones import (
    CONSULTA_CONCEPTUAL,
    EXPLICACION_DIRECTA,
    SOLICITUD_EJEMPLO,
    Intencion,
)


SONDEO, PISTA, CORRECCION = 1, 2, 3


NOMBRE = {SONDEO: "sondeo", PISTA: "regla", CORRECCION: "desarrollo"}


ALCANCE_EJERCICIO_ACTIVO = "ejercicio_activo"
ALCANCE_ANALOGO = "analogo"


@dataclass(frozen=True)
class Señales:

    intentos_en_el_problema: int = 0

    insistencias: int = 0

    peticion_confirmada: bool = False

    ansiedad_alta: bool | None = None
    miedo_a_pedir_ayuda_alto: bool | None = None
    ciclo_negativo: bool | None = None

    autoeficacia_baja: bool | None = None

    ansiedad_explicita: bool | None = None

@dataclass(frozen=True)
class Decision:

    nivel: int
    motivo: str

    alcance: str = ALCANCE_EJERCICIO_ACTIVO

    descartadas: tuple[str, ...] = ()

    sin_evaluar: tuple[str, ...] = ()

    no_escalan: tuple[str, ...] = ()

    @property
    def nombre(self) -> str:
        return NOMBRE.get(self.nivel, NOMBRE[SONDEO])

_PIDEN_CONTENIDO = frozenset({CONSULTA_CONCEPTUAL, EXPLICACION_DIRECTA, SOLICITUD_EJEMPLO})


_CONDUCTUALES = (
    ("ansiedad_alta", "ansiedad alta", "ansiedad (sin modelo del estudiante · filtro 3)"),
    (
        "miedo_a_pedir_ayuda_alto",
        "miedo a pedir ayuda alto",
        "miedo a pedir ayuda (sin modelo del estudiante · filtro 3)",
    ),
    ("ciclo_negativo", "ciclo negativo detectado", "ciclo negativo (sin modelo del estudiante · filtro 3)"),
    ("autoeficacia_baja", "autoeficacia estimada baja", "autoeficacia (sin modelo del estudiante · filtro 3)"),
    ("ansiedad_explicita", "ansiedad expresada en el turno", ""),
)


def decidir(señales: Señales, peticion: Intencion | None = None) -> Decision:
    razones_3: list[str] = []
    razones_2: list[str] = []
    sin_evaluar: list[str] = []

    no_escalan: list[str] = []

    if señales.intentos_en_el_problema >= 3:
        razones_3.append(f"{señales.intentos_en_el_problema} intentos en el mismo problema")
    if señales.peticion_confirmada:
        razones_3.append("petición explícita confirmada")

    if señales.intentos_en_el_problema >= 2:
        razones_2.append(f"{señales.intentos_en_el_problema} intentos en el mismo problema")

    for campo, etiqueta, ausencia in _CONDUCTUALES:
        valor = getattr(señales, campo)
        if valor:
            no_escalan.append(
                f"{etiqueta}: cambia el tono, el apoyo o la representación, "
                f"nunca cuánta matemática se revela (DEC-R1)"
            )
        elif valor is None and ausencia:
            sin_evaluar.append(ausencia)

    if señales.insistencias:
        no_escalan.append(
            f"{señales.insistencias} insistencia(s): no escalan por sí solas (RF-GEN-04)"
        )

    pide_contenido = peticion is not None and peticion.clase in _PIDEN_CONTENIDO

    if razones_3:
        return Decision(
            nivel=CORRECCION,
            motivo=razones_3[0],
            alcance=ALCANCE_EJERCICIO_ACTIVO,
            descartadas=tuple(razones_3[1:] + razones_2),
            sin_evaluar=tuple(sin_evaluar),
            no_escalan=tuple(no_escalan),
        )
    if razones_2:
        return Decision(
            nivel=PISTA,
            motivo=razones_2[0],
            alcance=ALCANCE_EJERCICIO_ACTIVO,
            descartadas=tuple(razones_2[1:]),
            sin_evaluar=tuple(sin_evaluar),
            no_escalan=tuple(no_escalan),
        )
    if pide_contenido:
        return Decision(
            nivel=PISTA,
            motivo=(
                "pidió explícitamente una explicación o un ejemplo: se autoriza "
                "explicación conceptual o procedimental y ejemplo análogo, nunca "
                "resolver el ejercicio activo (DEC-R3)"
            ),
            alcance=ALCANCE_ANALOGO,
            sin_evaluar=tuple(sin_evaluar),
            no_escalan=tuple(no_escalan),
        )
    return Decision(
        nivel=SONDEO,
        motivo="ninguna condición de escalada se cumple: el sondeo es el defecto",
        alcance=ALCANCE_EJERCICIO_ACTIVO,
        sin_evaluar=tuple(sin_evaluar),
        no_escalan=tuple(no_escalan),
    )
