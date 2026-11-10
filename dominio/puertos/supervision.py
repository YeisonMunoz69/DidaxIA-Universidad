"""
supervision.py — Contrato de la cola de revisión docente (`RU-12`)
=======================================================================

Los estados, los tipos, los dos modelos y el puerto que comparten las **dos**
implementaciones de la cola: la de memoria del proceso
(`adaptadores/salientes/registro/cola_revision_memoria.py`) y la de PostgreSQL
(`adaptadores/salientes/registro/cola_revision_db.py`).

Por qué el contrato vive aquí
-----------------------------------
Mismo motivo que `dominio/puertos/clases.py`: hasta la Fase 2 · sesión 3 estos
tipos se definían en `adaptadores/entrantes/http/supervision.py` y el adaptador
de PostgreSQL los importaba desde ahí, invirtiendo la dirección de dependencia
que `ADR-001` §7.2 fija.

Qué NO decide este puerto, y se declara en vez de inventarse
-------------------------------------------------------------------
**No decide qué entra en la cola.** Hoy la alimenta sólo la excepción
—`situacion=degradado` y `procedencia.origen=sin-fuente`—; el muestreo
aleatorio de turnos que salieron bien no está implementado porque no hay tasa
de muestreo decidida en ningún documento. Ver `rutas/turno.py`.

**No calcula urgencia.** `urgencia` es un campo transportado, no derivado: sin
el modelo del estudiante (filtro 3) no hay señal de la que sacar `"alta"` o
`"baja"`, y un cálculo inventado aquí sería una decisión de producto
disfrazada de código.

**No ofrece «aprobar todo».** La ausencia es la decisión, la misma que toma
`ColaDeSupervision.svelte`; un puerto que la declarara la desharía por atrás.


"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

#: Las tres acciones sobre un elemento. `TarjetaDeRevision.svelte` las declara
#: como tres y no dos: editar no es aprobar con un paso intermedio, es una
#: emisión distinta y `RP-17` pide poder reconstruir cuál fue.
ESTADO_PENDIENTE = "pendiente"
ESTADO_APROBADO = "aprobado"
ESTADO_EDITADO = "editado"
ESTADO_RECHAZADO = "rechazado"

#: Los tres tipos que `FiltrosDeCola.svelte` ya declara. Un tipo nuevo aquí
#: exige un tipo nuevo allá — no se inventan sueltos.
TIPO_RESPUESTA = "respuesta"
TIPO_SIN_FUENTE = "sin-fuente"
TIPO_DEGRADADO = "degradado"


@dataclass
class ItemDeRevision:
    """`{ id, recibido, urgencia, clase, tipo, mensaje, turno }` — la forma
    exacta que `TarjetaDeRevision.svelte` desestructura de sus props."""

    identificador: str
    recibido: str
    urgencia: str
    clase: str | None
    tipo: str
    mensaje: str
    turno: dict
    estado: str = ESTADO_PENDIENTE
    # Campos que el árbol del estudiante tiene prohibidos (`08-Contrato-del-
    # Turno.md` §9) y que aquí SÍ pueden viajar — hoy no los llena nadie
    # (el filtro 3, modelo del estudiante, no existe), así que quedan en
    # `None` en vez de inventar un valor. `None` no es lo mismo que "no
    # aplica"; es "no hay de dónde sacarlo todavía".
    concepcion_candidata: str | None = None
    ansiedad_estimada: float | None = None
    estudiante: str = ""
    sesion: str = ""

    def como_elemento(self) -> dict:
        return {
            "id": self.identificador,
            "recibido": self.recibido,
            "urgencia": self.urgencia,
            "clase": self.clase,
            "tipo": self.tipo,
            "mensaje": self.mensaje,
            "turno": self.turno,
            "concepcion_candidata": self.concepcion_candidata,
            "ansiedad_estimada": self.ansiedad_estimada,
            "estudiante": self.estudiante,
            "sesion": self.sesion,
        }


@dataclass
class NuevoItem:
    """Lo que hace falta para encolar un turno. Aparte de `agregar()` —que si
    no, junta siete parámetros y `PLR0913` lo prohíbe con razón: siete
    posiciones sueltas es más fácil de invocar mal que un objeto con nombre."""

    urgencia: str
    clase: str | None
    tipo: str
    mensaje: str
    turno: dict
    concepcion_candidata: str | None = None
    ansiedad_estimada: float | None = None
    estudiante: str = ""
    sesion: str = ""


@dataclass(frozen=True)
class AclaracionDocente:
    """Una voz docente añadida después del turno, sin reescribirlo."""

    identificador: str
    sesion: str
    texto: str
    docente: str
    creada_en: str
    # El identificador estable de `CuerpoTurno.turno`. Permite insertar la
    # aclaración inmediatamente después de la respuesta que corrige, incluso
    # cuando el hilo recibe turnos nuevos antes de volver a abrirse.
    turno: str = ""

    def como_elemento(self) -> dict:
        return {
            "id": self.identificador,
            "sesion": self.sesion,
            "texto": self.texto,
            "docente": self.docente,
            "creada_en": self.creada_en,
            "turno": self.turno,
        }


@runtime_checkable
class PuertoColaDeRevision(Protocol):
    """Las seis operaciones que el borde consume: una de escritura desde el
    turno y cinco desde las rutas de supervisión."""

    def agregar(self, nuevo: NuevoItem) -> ItemDeRevision:
        """Encola el turno y devuelve el ítem ya sellado —identificador y
        `recibido` los pone la implementación, no quien llama."""
        ...

    def listar_pendientes(
        self,
        urgencia: str = "",
        clase: str = "",
        tipo: str = "",
        tope: int | None = None,
        desde: int = 0,
        clases_permitidas: tuple[str, ...] = (),
    ) -> list[ItemDeRevision]:
        """Sólo lo pendiente, ordenado por `recibido`. Una cadena vacía en un
        filtro significa «sin filtrar por ese campo», no «igual a vacío».

        `desde` pagina sobre el mismo orden que `tope` recorta, para que
        `ColaDeSupervision.svelte` pueda pedir «página 2» sin traer de vuelta
        lo que ya se vio.
        """
        ...

    def total_pendientes(
        self, urgencia: str = "", clase: str = "", tipo: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> int:
        """Cuántos pendientes hay con esos filtros, sin paginar."""
        ...

    def aprobar(
        self, identificador: str, actor: str = "", clases_permitidas: tuple[str, ...] = ()
    ) -> bool:
        """`False` si no existe o ya estaba resuelto — no es un error, es que
        otra persona llegó antes."""
        ...

    def editar(
        self, identificador: str, texto: str, actor: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> bool:
        """Emite `texto` en vez de lo propuesto. El texto se conserva en el
        propio ítem para que `RP-17` pueda reconstruir qué se emitió."""
        ...

    def rechazar(
        self, identificador: str, motivo: str, actor: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> bool:
        """Rechaza la propuesta y emite `motivo` como corrección docente.

        Rechazar se distingue de editar en la auditoría, pero no deja al
        estudiante sin orientación: ambas decisiones producen una aclaración
        visible y anclada al turno revisado.
        """
        ...

    def listar_aclaraciones(self, estudiante: str, sesion: str) -> list[AclaracionDocente]:
        """Aclaraciones de un hilo propio, en orden de emisión."""
        ...
