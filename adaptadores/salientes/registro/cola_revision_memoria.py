"""
cola_revision_memoria.py — La cola de revisión docente en memoria (`RU-12`)
================================================================================

El respaldo de `AdaptadorColaDeRevisionPostgres`: mismo
`PuertoColaDeRevision` (`dominio/puertos/supervision.py`), mismos modelos, sin
base. `aplicacion.py` construye uno u otro según `AGENTE_BD`, y
`GET /api/salud` declara cuál cayó.

DISEÑADA PARA MUESTREO Y EXCEPCION, no para revisar todo. Con cuatro cursos
reales revisar cada respuesta es insostenible, y las docentes lo confirmaron en
la consulta: «sí sería una carga, pero se pueden seleccionar algunos, como una
muestra».

Aquí SI viajan los campos que el árbol del estudiante tiene prohibidos. La
frontera es estudiante frente a no-estudiante, y la impone `requerir_rol` en
`rutas/supervision.py`.

Dónde vivía antes, y por qué se movió
--------------------------------------------
Hasta la Fase 2 · sesión 3 esta clase y sus modelos vivían en
`adaptadores/entrantes/http/supervision.py`, y el adaptador de PostgreSQL los
importaba desde ahí. Un almacén es un adaptador **saliente**; los modelos son
del contrato. Ver `dominio/puertos/supervision.py`.
`adaptadores/entrantes/http/supervision.py` conserva una reexportación
explícita para no romper a quien todavía importe de allí.

Qué la alimenta hoy, y qué no
--------------------------------
**Solo la excepción, no el muestreo.** `rutas/turno.py` añade a la cola un
turno cuando degrada (`situacion=degradado`) o cuando responde sin fuente
(`procedencia.origen=sin-fuente`) — son los dos casos que
`FiltrosDeCola.svelte` ya declara como `tipo`. El muestreo aleatorio de turnos
que salieron bien **no está implementado**: no hay una tasa de muestreo
decidida en ningún documento, y inventarla aquí sería una decisión de producto
disfrazada de código.

**No hay urgencia calculada.** `urgencia` se deja en `"normal"` para todo lo
que entra por esta vía — no hay señal hoy de la que derivar `"alta"` o
`"baja"` sin el modelo del estudiante (filtro 3, no construido).


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from dominio.puertos.supervision import (
    ESTADO_APROBADO,
    ESTADO_EDITADO,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADO,
    AclaracionDocente,
    ItemDeRevision,
    NuevoItem,
)


@dataclass
class _Filtros:
    urgencia: str = ""
    clase: str = ""
    tipo: str = ""
    tope: int | None = None
    desde: int = 0


class ColaDeRevision:
    """Almacén en memoria. Ver el docstring del módulo sobre qué la alimenta."""

    def __init__(self) -> None:
        self._items: dict[str, ItemDeRevision] = {}
        self._aclaraciones: dict[str, AclaracionDocente] = {}

    def agregar(self, nuevo: NuevoItem) -> ItemDeRevision:
        item = ItemDeRevision(
            identificador=secrets.token_urlsafe(8),
            recibido=datetime.now(UTC).isoformat(timespec="seconds"),
            urgencia=nuevo.urgencia,
            clase=nuevo.clase,
            tipo=nuevo.tipo,
            mensaje=nuevo.mensaje,
            turno=nuevo.turno,
            concepcion_candidata=nuevo.concepcion_candidata,
            ansiedad_estimada=nuevo.ansiedad_estimada,
            estudiante=nuevo.estudiante,
            sesion=nuevo.sesion,
        )
        self._items[item.identificador] = item
        return item

    def listar_pendientes(
        self,
        urgencia: str = "",
        clase: str = "",
        tipo: str = "",
        tope: int | None = None,
        desde: int = 0,
        clases_permitidas: tuple[str, ...] = (),
    ) -> list[ItemDeRevision]:
        """Sin `"aprobar todo"` en la interfaz de este módulo tampoco — la
        ausencia es la misma decisión que `ColaDeSupervision.svelte` ya toma,
        y este almacén no ofrece un método que la deshaga por atrás.

        `desde` pagina sobre el mismo orden que `tope` ya recortaba —
        `PM-B?`, 2026-08-22, para que `ColaDeSupervision.svelte` pueda pedir
        «página 2» sin traer de vuelta lo que ya se vio."""
        filtros = _Filtros(urgencia=urgencia, clase=clase, tipo=tipo, tope=tope, desde=desde)
        pendientes = [i for i in self._items.values() if i.estado == ESTADO_PENDIENTE]
        if clases_permitidas:
            pendientes = [i for i in pendientes if i.clase in clases_permitidas]
        if filtros.urgencia:
            pendientes = [i for i in pendientes if i.urgencia == filtros.urgencia]
        if filtros.clase:
            pendientes = [i for i in pendientes if i.clase == filtros.clase]
        if filtros.tipo:
            pendientes = [i for i in pendientes if i.tipo == filtros.tipo]
        pendientes.sort(key=lambda i: i.recibido)
        if filtros.desde:
            pendientes = pendientes[filtros.desde :]
        if filtros.tope is not None:
            pendientes = pendientes[: filtros.tope]
        return pendientes

    def total_pendientes(
        self, urgencia: str = "", clase: str = "", tipo: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> int:
        return len(self.listar_pendientes(
            urgencia, clase, tipo, clases_permitidas=clases_permitidas
        ))

    def aprobar(
        self, identificador: str, actor: str = "", clases_permitidas: tuple[str, ...] = ()
    ) -> bool:
        return self._resolver(identificador, ESTADO_APROBADO, clases_permitidas)

    def editar(
        self, identificador: str, texto: str, actor: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> bool:
        """Emite `texto` en vez de lo propuesto. El texto se guarda en el
        propio ítem para que `RP-17` pueda reconstruir qué se emitió — no se
        descarta al resolver, a diferencia de `aprobar()` y `rechazar()`."""
        item = self._items.get(identificador)
        if (item is None or item.estado != ESTADO_PENDIENTE
                or (clases_permitidas and item.clase not in clases_permitidas)):
            return False
        if not item.estudiante or not item.sesion or not item.clase:
            return False
        item.turno = {**item.turno, "editado_por_docente": texto}
        item.estado = ESTADO_EDITADO
        self._aclaraciones[identificador] = AclaracionDocente(
            identificador=identificador, sesion=item.sesion, texto=texto,
            docente=actor, creada_en=datetime.now(UTC).isoformat(timespec="seconds"),
            turno=str(item.turno.get("turno") or ""),
        )
        return True

    def rechazar(
        self, identificador: str, motivo: str, actor: str = "",
        clases_permitidas: tuple[str, ...] = (),
    ) -> bool:
        """Rechaza la propuesta y publica el texto docente que la corrige."""
        item = self._items.get(identificador)
        if (item is None or item.estado != ESTADO_PENDIENTE
                or (clases_permitidas and item.clase not in clases_permitidas)):
            return False
        if not item.estudiante or not item.sesion or not item.clase or not actor:
            return False
        item.turno = {**item.turno, "motivo_de_rechazo": motivo}
        item.estado = ESTADO_RECHAZADO
        self._aclaraciones[identificador] = AclaracionDocente(
            identificador=identificador, sesion=item.sesion, texto=motivo,
            docente=actor, creada_en=datetime.now(UTC).isoformat(timespec="seconds"),
            turno=str(item.turno.get("turno") or ""),
        )
        return True

    def _resolver(
        self, identificador: str, estado: str, clases_permitidas: tuple[str, ...] = ()
    ) -> bool:
        item = self._items.get(identificador)
        if (item is None or item.estado != ESTADO_PENDIENTE
                or (clases_permitidas and item.clase not in clases_permitidas)):
            return False
        item.estado = estado
        return True

    def listar_aclaraciones(self, estudiante: str, sesion: str) -> list[AclaracionDocente]:
        return [
            aclaracion for clave, aclaracion in self._aclaraciones.items()
            if self._items[clave].estudiante == estudiante and aclaracion.sesion == sesion
        ]
