"""
estudiante.py — El estado actual de los tres registros de `ADR-003` §6.2 (`PM-B09`)
======================================================================================

`dominio/puertos/registro.py` declaró, sin construirlo, quién calcula lo que él
solo conserva: *«No calcula nada. No aplica la fórmula de decaimiento de
`ADR-003` N2, no avanza la máquina de estados de R-C ni cuenta la ventana de
R-E — eso es `dominio/modelo/estudiante.py` (todavía 🆕)»*. Este módulo es eso.

**No es un refactor del vector del prototipo: es otro modelo** — la propia
tarea lo advierte, y `ADR-003` §1 explica por qué: `ansiedad`, `preconcepciones`
y `confirmacion` compartían un espacio `[0,1]` con la misma fórmula y el mismo
umbral, y esa era la premisa que `ADR-003` retira. Aquí los tres tipos son
**tres clases distintas**, sin conversión entre ellas, ni siquiera interna.

Por qué las clases de aquí no se llaman igual que las de `dominio/puertos/registro.py`
-------------------------------------------------------------------------------------------
Ese puerto ya usa `RegistroAfectivo`, `RegistroConceptual` y `RegistroEstrategico`
para la **entrada de auditoría de un evento** —un turno, una señal, una regla,
un valor previo y uno nuevo—. Lo que este módulo mantiene es distinto: el
**estado acumulado actual**, del que cada actualización deriva la siguiente
entrada de auditoría. Llamarlos igual habría chocado en cualquier módulo que
necesitara los dos a la vez —y `dominio/filtros/deteccion.py`, `PM-B10`, es
exactamente ese módulo—. Por eso aquí son `EstadoAfectivo`, `EstadoConceptual`
y `EstadoEstrategico`, y cada método de actualización devuelve el estado nuevo
**y** la entrada de auditoría del puerto, lista para persistir.

`R-18`, que esta sesión hereda de `PM-B13`
------------------------------------------------
`ADR-003` C1: no hay índice agregado. `T6` (`dominio/arbitraje/intervencion.py`)
ya decide qué intervención aplicar sin sumar nada; este módulo no le da ningún
motivo para empezar — cada sub-componente vive y decae por separado.

Qué cubre esta sesión, y qué queda en ruta fría (`ADR-003` §6.5)
------------------------------------------------------------------
Solo **S1**: los sub-componentes de nivel 1 de R-A —`PS-Anx`, `FAH`,
`autoeficacia`— y la detección barata de ciclo negativo de R-E. Los
sub-componentes de nivel 2 de R-A (`E-Anx`, aburrimiento, autoconcepto…) y las
consolidaciones de R-C/R-E son **S2**, ruta fría, y no tienen todavía el
filtro frío que las alimente —`PM-B13` dejó `Orquestador.ejecutar_fria()`
listo para recibirlo, pero ningún filtro lo usa aún—. Este módulo declara los
campos de nivel 2 en `SUBCOMPONENTES_AFECTIVOS` (heredados de
`dominio/puertos/registro.py`) pero `EstadoAfectivo` de esta sesión solo los
acepta si alguien los actualiza explícitamente; nada los inicializa por sí
mismo.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from dominio.puertos.registro import ESTADOS_CONCEPTUALES
from dominio.puertos.registro import RegistroAfectivo as EntradaAfectiva
from dominio.puertos.registro import RegistroConceptual as EntradaConceptual
from dominio.puertos.registro import RegistroEstrategico as EntradaEstrategica

#: `ADR-003` **N5**: *«el estado se actualiza por turno con λ de sesión; el rasgo
#: se actualiza al cierre de sesión, a partir de agregados, con λ mucho más
#: alto»*. **Son dos λ y llevan decididos desde el principio.**
#:
#: Hasta el 2026-08-15 aquí había uno solo, `LAMBDA_POR_DEFECTO = 0,85`, aplicado
#: al estado. **Eso no era una elección pendiente: era N5 sin implementar**, y el
#: número que se aplicaba al estado es el que N5 reserva para el rasgo — mucha
#: inercia, cambia despacio, estable entre sesiones. Aplicado al estado lo vuelve
#: sordo dentro de una conversación: con `λ = 0,85` y el umbral `0,6` de
#: `deteccion.py`, la señal más fuerte que el detector produce **no cruza el
#: umbral en ninguna conversación de la longitud que tienen las de `E04`**.
#:
#: ⚠️ **Hoy los dos valen lo mismo, y eso es deliberado.** `PM-B33` separa; elegir
#: el valor del estado es otra cosa y va después, con la tabla de sensibilidad
#: delante —`PM-V16`, `D-22` tras la revisión del 2026-08-14—. Elegirlo aquí
#: mismo *porque da ~3 turnos* sería ajustar un parámetro para producir el
#: resultado que se busca, que es lo que `DD-25` prohíbe por escrito.
#:
#: Lo que la separación compra hoy, aunque no cambie ni un número: **el día que
#: el λ del estado se mueva, el del rasgo no se moverá con él.** Que valgan lo
#: mismo es la coincidencia que hay que poder deshacer.

#: El de la ruta caliente, turno a turno. **Provisional**: el valor sale de la
#: tabla de sensibilidad, no de este archivo.
LAMBDA_ESTADO_POR_DEFECTO = 0.85

#: El del rasgo, que se actualiza al cierre de sesión. **Se queda alto a
#: propósito**: es lo que N5 pide y para lo que 0,85 sirve. Queda declarado
#: aunque el filtro 11 —la ruta fría que lo actualizará— todavía no exista, para
#: que el día que se construya no haya que volver a decidir esto.
LAMBDA_RASGO_POR_DEFECTO = 0.85

#: Qué λ le toca a cada alcance de `dominio/puertos/registro.py`. Existe para que
#: el filtro 11 lo lea en vez de repetir la constante, que es como se acaba
#: teniendo dos valores para lo mismo en dos archivos.
LAMBDA_POR_ALCANCE: dict[str, float] = {
    "estado": LAMBDA_ESTADO_POR_DEFECTO,
    "rasgo": LAMBDA_RASGO_POR_DEFECTO,
}

#: `DD-06`: la ventana del registro estratégico se mide en EPISODIOS, no en
#: turnos, y el valor inicial es 3. Rige tanto `RF-DET-21` (sesgo de
#: confirmación, activo desde el segundo episodio) como `RF-DET-22` (ciclo
#: negativo, ventana ≥3): `DD-06` fija una sola ventana para «el registro
#: estratégico», no dos.
VENTANA_ESTRATEGICA_POR_DEFECTO = 3


@dataclass(frozen=True)
class EstadoAfectivo:
    """R-A · el valor **actual** por sub-componente, continuo en `[0,1]`.

    Solo el estado (`ADR-003` N5); el rasgo es ruta fría y no vive aquí
    todavía — por eso `actualizar` toma `LAMBDA_ESTADO_POR_DEFECTO` y no el
    del rasgo, y por eso la entrada de auditoría sale con `alcance="estado"`. `valores` empieza vacío: un sub-componente sin evidencia no
    tiene un cero implícito, tiene **ausencia** — la misma distinción que
    `dominio/arbitraje/divulgacion.py` ya hace con `None`.
    """

    valores: dict[str, float] = field(default_factory=dict)

    def valor(self, subcomponente: str) -> float | None:
        return self.valores.get(subcomponente)

    def actualizar(
        self,
        subcomponente: str,
        obs_t: float,
        turno: str,
        señal: str,
        certeza: float = 1.0,
        lam: float = LAMBDA_ESTADO_POR_DEFECTO,
    ) -> tuple[EstadoAfectivo, EntradaAfectiva]:
        """`ADR-003` N2: `v_t = min(1, λ·v_{t-1} + (1−λ)·obs_t)`.

        `obs_t` **nunca es negativo** — viene siempre de
        `dominio/deteccion/patrones.py`, que solo produce evidencia de
        presencia en `[0,1]` (N3, la regla del máximo) — así que la única vía
        por la que el valor baja es el decaimiento cuando `obs_t` es bajo,
        nunca una resta directa. Es `ADR-003` N4 (asimetría descendente) como
        propiedad de la fórmula, no como comprobación aparte.
        """
        if not 0.0 <= obs_t <= 1.0:
            raise ValueError(f"obs_t fuera de [0,1]: {obs_t}")
        previo = self.valores.get(subcomponente, 0.0)
        nuevo = min(1.0, lam * previo + (1.0 - lam) * obs_t)
        estado = replace(self, valores={**self.valores, subcomponente: nuevo})
        entrada = EntradaAfectiva(
            turno=turno,
            subcomponente=subcomponente,
            senal=señal,
            regla_aplicada="N2 · decaimiento con saturación",
            valor_previo=previo,
            valor_nuevo=nuevo,
            lambda_aplicado=lam,
            certeza=certeza,
            alcance="estado",
        )
        return estado, entrada


#: `ADR-003` §6.2: transición por evento diagnóstico. Cuatro posiciones,
#: `RF-MEV-13`. `PM-B08` es la fuente natural del evento «detectada» —su
#: estado `E4` señala exactamente una concepción activa sobre un nodo— y
#: `E1`/`E3` sobre un elemento antes activo son la fuente de «remediada».
#: No es una tabla arbitraria: es la que hace que un evento «detectada» sobre
#: algo YA remediado se distinga de la primera vez —`recurrente` no es
#: `activa`, porque RF-MEV-13 exige poder verlas distinto.
_TRANSICION_CONCEPTUAL = {
    ("no_detectada", "detectada"): "activa",
    ("activa", "detectada"): "activa",
    ("activa", "remediada"): "remediada",
    ("remediada", "detectada"): "recurrente",
    ("remediada", "remediada"): "remediada",
    ("recurrente", "detectada"): "recurrente",
    ("recurrente", "remediada"): "remediada",
}


@dataclass(frozen=True)
class EstadoConceptual:
    """R-C · una máquina de estados de cuatro posiciones por elemento, **sin
    decaimiento** — la naturaleza que `ADR-003` §6.2 más distingue de R-A.

    `elemento` no se restringe a `M01`–`M24`: hereda de
    `dominio/puertos/registro.py` la misma libertad —dominio por nodo, el
    patrón grados↔radianes— por la misma razón que ese puerto la declara.
    """

    estados: dict[str, str] = field(default_factory=dict)

    def estado_de(self, elemento: str) -> str:
        return self.estados.get(elemento, "no_detectada")

    def registrar_evento(
        self, elemento: str, evento: str, turno: str
    ) -> tuple[EstadoConceptual, EntradaConceptual]:
        if evento not in ("detectada", "remediada"):
            raise ValueError(f"evento desconocido «{evento}»: detectada | remediada")
        previo = self.estado_de(elemento)
        nuevo = _TRANSICION_CONCEPTUAL[(previo, evento)]
        estado = replace(self, estados={**self.estados, elemento: nuevo})
        entrada = EntradaConceptual(
            turno=turno,
            elemento=elemento,
            estado_previo=previo,
            estado_nuevo=nuevo,
            evento_diagnostico=evento,
        )
        assert nuevo in ESTADOS_CONCEPTUALES  # nunca puede no estarlo: es la tabla
        return estado, entrada


@dataclass(frozen=True)
class Episodio:
    """Un episodio de problema, tal como `DD-06` lo mide — no un turno.

    Los cinco campos cubren las dos detecciones que comparten la ventana de
    `DD-06`: `retroalimentacion_correctiva` + `reincide_en_la_estrategia` son
    el par de `RF-DET-21`; `confusion` + `afecto_negativo` +
    `evitacion_o_bajo_esfuerzo` son las tres señales de `RF-DET-22`.
    """

    retroalimentacion_correctiva: bool = False
    reincide_en_la_estrategia: bool = False
    confusion: bool = False
    afecto_negativo: bool = False
    evitacion_o_bajo_esfuerzo: bool = False


@dataclass(frozen=True)
class EstadoEstrategico:
    """R-E · secuencia de episodios sobre la ventana deslizante de `DD-06`.

    Ni valor continuo ni estado discreto: un contador sobre ventana, el
    tercer molde que `ADR-003` exige no forzar a los otros dos.
    """

    ventana: int = VENTANA_ESTRATEGICA_POR_DEFECTO
    episodios: tuple[Episodio, ...] = ()

    def registrar(
        self, episodio: Episodio, turno: str
    ) -> tuple[EstadoEstrategico, EntradaEstrategica]:
        episodios = (self.episodios + (episodio,))[-self.ventana :]
        estado = replace(self, episodios=episodios)
        entrada = EntradaEstrategica(
            turno=turno,
            tipo_evento="episodio_registrado",
            ventana=self.ventana,
            contador=len(episodios),
            ciclo_negativo=estado.ciclo_negativo,
        )
        return estado, entrada

    @property
    def sesgo_de_confirmacion(self) -> bool:
        """`RF-DET-21`: activo desde el **segundo** episodio de reincidencia
        tras retroalimentación correctiva, dentro de la ventana."""
        reincidencias = sum(
            1
            for e in self.episodios
            if e.retroalimentacion_correctiva and e.reincide_en_la_estrategia
        )
        return reincidencias >= 2

    @property
    def ciclo_negativo(self) -> bool:
        """`RF-DET-22`, sobre una ventana de `self.ventana` episodios (≥3, `DD-06`).

        La confusión tiene que ser **recurrente** —al menos dos de la
        ventana, no un pico aislado—; el afecto negativo y la evitación o
        bajo esfuerzo, presentes al menos una vez en la misma ventana. Es la
        lectura literal del requisito —*«confusión recurrente + afecto
        negativo + evitación… a lo largo de una secuencia de turnos»*— sin
        exigir que las tres coincidan en el mismo episodio exacto, que el
        requisito no pide. **Declarado, calibrable en el OE4** como los demás
        umbrales de esta sesión.
        """
        if len(self.episodios) < self.ventana:
            return False
        recientes = self.episodios[-self.ventana :]
        confusion_recurrente = sum(1 for e in recientes if e.confusion) >= 2
        hay_afecto_negativo = any(e.afecto_negativo for e in recientes)
        hay_evitacion = any(e.evitacion_o_bajo_esfuerzo for e in recientes)
        return confusion_recurrente and hay_afecto_negativo and hay_evitacion


@dataclass(frozen=True)
class PerfilEstudiante:
    """Los tres registros juntos, sin fundirse — `ADR-003` K1.

    No es una clase que combine nada: es la unidad de paso conveniente para
    quien necesita los tres a la vez, como `dominio/filtros/deteccion.py`.
    """

    afectivo: EstadoAfectivo = field(default_factory=EstadoAfectivo)
    conceptual: EstadoConceptual = field(default_factory=EstadoConceptual)
    estrategico: EstadoEstrategico = field(default_factory=EstadoEstrategico)
