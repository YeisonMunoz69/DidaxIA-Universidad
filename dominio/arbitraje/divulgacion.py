"""
divulgacion.py — La escala de divulgación de tres niveles (`RF-GEN-05`)
=======================================================================

`ERS-07` §T2 la definió y `RF-GEN-05` la exige:

    (1) sondeo socrático sin revelar
    (2) pista dirigida al principio matemático violado
    (3) corrección verificada explícita

Su criterio de aceptación, tal como se escribió, decía: *«nivel 2 tras 2
intentos fallidos en el mismo paso o ante FAH/PS-Anx alto; nivel 3 tras 3
intentos, ante petición explícita confirmada, o ante ciclo negativo
detectado»*.

🔴 `DEC-R1` · ninguna señal conductual aumenta la divulgación
--------------------------------------------------------------
**Ese criterio y la política F.3 no podían ser ciertos a la vez**, y la entrega
anterior lo dejó dicho por escrito en vez de resolverlo: retiró el ciclo
negativo del nivel 3 y dejó FAH/PS-Anx abriendo el nivel 2.

`DEC-R1` lo cierra en la dirección de la política: **ninguna señal conductual
—PS-Anx, FAH, autoeficacia, ansiedad expresada, ciclo negativo— puede aumentar
la cantidad de matemática revelada.** Las cinco siguen leyéndose y siguen
sirviendo: son la jerarquía `T6` de `intervencion.py` y producen tono, apoyo,
cambio de representación, grado de detalle y densidad de preguntas. Lo que
dejan de mover es la palanca que no les tocaba.

El motivo no es de estilo. Escalar por ansiedad entrega **más** matemática a
quien peor puede evaluarla, y lo hace por una inferencia sobre su estado en vez
de por su trabajo. Es la misma puerta que `RF-GEN-04` cierra del otro lado: si
insistir no basta, sentirse mal tampoco.

Las señales que se cumplen y no escalan quedan en `no_escalan`, no se pierden:
sin eso, «no escaló» no permite distinguir que la regla se aplicó de que el
resultado coincidió.

🔴 `DEC-R3` · explicación y ejemplo, con alcance acotado
---------------------------------------------------------
Una solicitud **explícita** de teoría o de ejemplo autoriza nivel 2. No es una
excepción a `DEC-R1`: no es una señal conductual sino **una petición
pedagógica del estudiante**, y confundir las dos era el otro error del diseño
anterior —«pidió que le expliquen» no es un estado afectivo inferido, es algo
que escribió—.

Lo que autoriza es acotado, y el alcance viaja con la decisión:

| `alcance` | Qué permite |
|---|---|
| `ejercicio_activo` | lo que la escala por trabajo autorice sobre el ejercicio que se está resolviendo |
| `analogo` | explicación conceptual o procedimental, y ejemplos **de otro caso** |

Pedir una explicación **no** autoriza resolver el ejercicio activo ni revelar
su resultado. Esa puerta sigue siendo una sola —tres intentos o confirmación
explícita— y sigue produciendo alcance `ejercicio_activo`. El filtro 7 escribe
el alcance en el prompt, así que la restricción llega al generador en vez de
quedarse en este módulo.

Por qué esto es un módulo de dominio y no un `if` en el filtro
----------------------------------------------------------------
Porque **`RF-REG-06` pide registrar el estrato de decisión pedagógica**: la
intención, la estrategia, el nivel alcanzado y *«las intervenciones descartadas
por el arbitraje»*. Un `if` devuelve un número; esto devuelve el número **y por
qué**, y qué otras señales pedían otra cosa. Sin eso, auditar la jerarquía de
`T6` con datos del piloto —que es para lo que existe el requisito— sería
imposible.

La tensión que hay que resolver, y no es evidente
--------------------------------------------------
`RF-GEN-05` escala a nivel 3 *«ante petición explícita confirmada»*. Pero
`RF-GEN-04` dice que el generador **no revelará la respuesta ante la mera
insistencia**, y lo comprueba con cinco *«solo dime la respuesta»* seguidos.

Los dos requisitos solo son compatibles si **insistir no es intentar**. Aquí se
modelan como cosas distintas:

- `intentos_en_el_problema` cuenta **intentos de resolver**: el estudiante propuso
  algo y no salió. Es lo que la escala mide.
- `insistencias` cuenta **peticiones de la respuesta**. No escalan nada por sí
  solas, y ese es justo el punto de `RF-GEN-04`.
- `peticion_confirmada` es otra cosa: el sistema preguntó *«¿seguro que
  quieres verlo resuelto?»* y el estudiante dijo que sí. Eso **sí** escala,
  porque ya no es insistencia sino una elección informada.

Lo que este módulo NO decide, y es de `PM-B13`
-----------------------------------------------
**La jerarquía de intervención de `T6`** —bloqueo sin intento, ciclo negativo,
autoeficacia, ansiedad explícita, autorregulación— que decide *qué se hace*,
no *cuánto se revela*. Las dos viven en el filtro 6 y son separables: esta
escala responde «cuánto», aquélla responde «qué». `PM-B13` la escribirá y este
módulo no la estorba.

⚠️ Y hay señales que hoy **no tienen fuente**
----------------------------------------------
`FAH` (miedo a pedir ayuda), `PS-Anx` (ansiedad) y el ciclo negativo salen del
modelo del estudiante, que es el **filtro 3** y no está construido. Se
representan con `None` —que no es `False`— y el arbitraje lo dice en su motivo:
que una condición no se pueda evaluar es información distinta de que no se
cumpla, y confundirlas dejaría creer que la escala está completa.

`Señales` es compartida con `intervencion.py` · `PM-B13`
-----------------------------------------------------------
Las dos mitades del filtro 6 miran el mismo turno, así que leen el mismo tipo
de señales en vez de que cada una pida las suyas por separado —dos lecturas
del mismo estado del estudiante podrían desincronizarse—. `autoeficacia_baja`
y `ansiedad_explicita` no los usa esta escala: los añade `PM-B13` para la
jerarquía de intervención de `T6`, que sí los necesita. `ansiedad_explicita`
**no es** `ansiedad_alta`: el segundo es la puntuación continua que el
sub-componente `PS-Anx` acumula turno a turno; el primero es que el estudiante
lo haya dicho con palabras en *este* turno. `T6` distingue las dos a
propósito —ver `intervencion.py`—.
"""

from __future__ import annotations

from dataclasses import dataclass

from dominio.pedagogia.intenciones import (
    CONSULTA_CONCEPTUAL,
    EXPLICACION_DIRECTA,
    SOLICITUD_EJEMPLO,
    Intencion,
)

#: Los tres niveles de `ERS-07` §T2. El 1 es el piso y el defecto.
SONDEO, PISTA, CORRECCION = 1, 2, 3

#: Cómo se llama cada nivel donde se lee. El contrato del turno usa estas
#: mismas palabras (`08-Contrato-del-Turno.md` §6), así que traducir en el
#: borde es cambiar de idioma, no de significado.
NOMBRE = {SONDEO: "sondeo", PISTA: "regla", CORRECCION: "desarrollo"}

#: `DEC-R3` · sobre QUÉ se puede revelar lo que el nivel autoriza. El nivel
#: dice cuánto; el alcance dice de qué. Sin los dos, un nivel 2 concedido por
#: pedir un ejemplo autorizaría resolver el ejercicio que el estudiante tiene
#: delante, que es exactamente lo que `DEC-R3` no concede.
ALCANCE_EJERCICIO_ACTIVO = "ejercicio_activo"
ALCANCE_ANALOGO = "analogo"


@dataclass(frozen=True)
class Señales:
    """Lo que la escala mira. Nada más, y por eso se lee de una vez.

    `None` en las tres últimas significa **«no se puede evaluar»**, no «no».
    El filtro 3 las alimentará; hasta entonces la escala opera con lo que hay
    y lo declara.
    """

    #: Intentos de RESOLVER fallidos en el PROBLEMA activo (`DEC-R2`). No
    #: cuenta pedir ayuda, y no cuenta intentos de otro ejercicio.
    intentos_en_el_problema: int = 0
    #: Veces que ha pedido la respuesta. **No escala por sí sola** (`RF-GEN-04`).
    insistencias: int = 0
    #: El sistema preguntó si quería verlo resuelto y dijo que sí.
    peticion_confirmada: bool = False
    #: Del modelo del estudiante · filtro 3. `None` = sin fuente todavía.
    ansiedad_alta: bool | None = None
    miedo_a_pedir_ayuda_alto: bool | None = None
    ciclo_negativo: bool | None = None
    #: `PM-B13` · `T6` nivel 3. Autoeficacia estimada baja. `None` = sin fuente.
    autoeficacia_baja: bool | None = None
    #: `PM-B13` · `T6` nivel 4. El estudiante EXPRESÓ ansiedad en este turno —
    #: no es `ansiedad_alta` (la puntuación acumulada de `PS-Anx`). `None` =
    #: sin fuente.
    ansiedad_explicita: bool | None = None


@dataclass(frozen=True)
class Decision:
    """El nivel, por qué, y qué se descartó. `RF-REG-06`."""

    nivel: int
    motivo: str
    #: `DEC-R3` · sobre qué se puede revelar. `ejercicio_activo` cuando el
    #: nivel lo abrió el trabajo del estudiante; `analogo` cuando lo abrió una
    #: petición de teoría o de ejemplo, que no autoriza el ejercicio de delante.
    alcance: str = ALCANCE_EJERCICIO_ACTIVO
    #: Condiciones que pedían escalar y no fueron las que decidieron. Se
    #: conservan porque `RF-REG-06` pide las intervenciones descartadas, y
    #: porque el análisis contrafactual del OE4 las necesita.
    descartadas: tuple[str, ...] = ()
    #: Condiciones que no se pudieron evaluar por falta de fuente.
    sin_evaluar: tuple[str, ...] = ()
    #: Condiciones que se cumplen y que la política dice que **no escalan**.
    #: `RF-GEN-04` para la insistencia y `G4` de la fase 4 para el ciclo
    #: negativo. Se registran porque «no escaló» sin decir qué se cumplía no
    #: permite auditar que la regla se aplicó — sólo que el resultado coincidió.
    no_escalan: tuple[str, ...] = ()

    @property
    def nombre(self) -> str:
        return NOMBRE.get(self.nivel, NOMBRE[SONDEO])


#: `DEC-R3` · las tres clases del catálogo v1 que son una petición explícita de
#: teoría o de ejemplo. Se nombran aquí y no se deducen de una familia: la
#: familia `PROCEDIMENTAL` incluye también pedir la solución, y confundirlas
#: convertiría `RF-GEN-04` en una regla que se rodea eligiendo bien las
#: palabras.
_PIDEN_CONTENIDO = frozenset({CONSULTA_CONCEPTUAL, EXPLICACION_DIRECTA, SOLICITUD_EJEMPLO})

#: `DEC-R1` · las señales conductuales, con el nombre que se escribe en la
#: traza. Ninguna escala; todas se registran cuando se cumplen.
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
    """El nivel de divulgación de este turno, con su motivo y su alcance.

    `peticion` es **lo que el estudiante pidió**, no una señal sobre él:
    `DEC-R3` distingue las dos a propósito, porque una petición de teoría es
    algo que escribió y una señal conductual es algo que se infirió. Es
    opcional para que el módulo siga decidiendo con lo que haya, igual que
    con `Señales`.

    El orden de comprobación es **de mayor a menor**, y no es indiferente: si
    varias condiciones se cumplen, gana la que más revela, porque el estudiante
    que lleva tres intentos y además pide verlo confirmado no necesita que se le
    devuelva una pista. Las demás quedan en `descartadas`.
    """
    razones_3: list[str] = []
    razones_2: list[str] = []
    sin_evaluar: list[str] = []
    #: Condiciones que se cumplen y **deliberadamente no escalan**. No es lo
    #: mismo que `sin_evaluar` —aquello es «no se pudo saber»— ni que
    #: `descartadas` —aquello es «pedía escalar y otra ganó»—: esto es «pedía
    #: escalar y la política dice que no le toca».
    no_escalan: list[str] = []

    # ── nivel 3 · corrección verificada explícita ──────────────────────────
    #
    # Las dos únicas puertas, y las dos salen del TRABAJO del estudiante: lo
    # que intentó y lo que confirmó. Ninguna inferencia sobre su estado entra
    # aquí — `DEC-R1`.
    if señales.intentos_en_el_problema >= 3:
        razones_3.append(f"{señales.intentos_en_el_problema} intentos en el mismo problema")
    if señales.peticion_confirmada:
        razones_3.append("petición explícita confirmada")

    # ── nivel 2 · pista dirigida al principio ──────────────────────────────
    if señales.intentos_en_el_problema >= 2:
        razones_2.append(f"{señales.intentos_en_el_problema} intentos en el mismo problema")

    # `DEC-R1` · las cinco señales conductuales se leen, se registran y **no
    # escalan ninguna de las dos escaleras**. Ver la cabecera sobre por qué.
    for campo, etiqueta, ausencia in _CONDUCTUALES:
        valor = getattr(señales, campo)
        if valor:
            no_escalan.append(
                f"{etiqueta}: cambia el tono, el apoyo o la representación, "
                f"nunca cuánta matemática se revela (DEC-R1)"
            )
        elif valor is None and ausencia:
            sin_evaluar.append(ausencia)

    # `RF-GEN-04`: insistir no escala. Se anota para que el registro lo vea y
    # para que quien audite el piloto pueda comprobar que no escaló.
    if señales.insistencias:
        no_escalan.append(
            f"{señales.insistencias} insistencia(s): no escalan por sí solas (RF-GEN-04)"
        )

    # ── `DEC-R3` · la petición de teoría o de ejemplo ──────────────────────
    #
    # Autoriza nivel 2 y **sólo de alcance análogo**. Va después de las dos
    # escaleras porque no compite con ellas: si el trabajo del estudiante ya
    # abrió un nivel, ese nivel manda y su alcance es el ejercicio activo.
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
