"""
rol_docente.py — Contrato de la cola de solicitudes de rol docente (`D-16` C)
==================================================================================

Los estados, el modelo y el puerto que comparten las **dos** implementaciones
de la cola de solicitud y aprobación: la de memoria del proceso
(`adaptadores/salientes/registro/solicitudes_docente_memoria.py`) y la de
PostgreSQL (`adaptadores/salientes/registro/solicitudes_docente_db.py`).

La mitad que este puerto cubre, y la que no
--------------------------------------------------
`D-16` opción C describe **dos mecanismos que alimentan un mismo registro**:
la lista a mano de `DOCENTES_AUTORIZADOS` y esta cola. Aquí sólo está la
segunda. La lista a mano es configuración del borde —la lee
`RegistroDeDocentes`, que es quien compone las dos mitades— y no tiene
almacén que contratar.

Por eso `aprobada()` está en el puerto y `es_docente()` no: lo primero es una
consulta al almacén, lo segundo es la política que combina almacén y lista.
Meter la política en el puerto obligaría a cada implementación a conocer la
variable de entorno, que es exactamente lo que un contrato de persistencia no
debe saber.

Qué NO decide este puerto
-------------------------------
**Ni límite de reintentos ni enfriamiento.** Una solicitud rechazada se puede
volver a pedir tantas veces como quiera quien la pide; un tope sería una
decisión de producto que nadie ha tomado.

**Ni jerarquía de permisos.** Quién puede resolver una solicitud lo decide
`RegistroDeDocentes.es_de_la_lista_manual()`, no este contrato.


"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

#: Las tres acciones sobre una solicitud — igual que `supervision.py`, no dos.
ESTADO_PENDIENTE = "pendiente"
ESTADO_APROBADA = "aprobada"
ESTADO_RECHAZADA = "rechazada"


@dataclass
class Solicitud:
    """`{ id, correo, creada, estado, nota }` — lo que una ruta de
    resolución necesita para decidir y lo que quien pidió el rol necesita
    para saber en qué quedó."""

    identificador: str
    correo: str
    creada: str
    estado: str = ESTADO_PENDIENTE
    # Motivo de rechazo, o el mensaje de «pedir más información». Nunca los
    # dos a la vez porque son estados/acciones distintos.
    nota: str | None = None

    def como_elemento(self) -> dict:
        return {
            "id": self.identificador,
            "correo": self.correo,
            "creada": self.creada,
            "estado": self.estado,
            "nota": self.nota,
        }


@runtime_checkable
class PuertoSolicitudesDocentes(Protocol):
    """Las seis operaciones que `RegistroDeDocentes` delega en el almacén."""

    def solicitar(self, correo: str) -> Solicitud:
        """Reutiliza la solicitud pendiente si ya existe una — pedirlo dos
        veces seguidas no duplica la cola. Una rechazada sí crea una nueva."""
        ...

    def listar_pendientes(self) -> list[Solicitud]:
        """Sólo las pendientes, ordenadas por `creada`."""
        ...

    def aprobar(self, identificador: str) -> bool:
        """`False` si no existe o ya estaba resuelta."""
        ...

    def rechazar(self, identificador: str, motivo: str) -> bool:
        """El motivo se conserva como `nota`. Que no esté vacío lo valida el
        borde, no el almacén."""
        ...

    def pedir_mas_informacion(self, identificador: str, mensaje: str) -> bool:
        """La tercera acción, distinta de aprobar y de rechazar: la solicitud
        **sigue pendiente** y sólo gana una nota visible para quien la pidió."""
        ...

    def aprobada(self, correo: str) -> bool:
        """Si hay alguna solicitud aprobada para ese correo. Es la mitad de
        `RegistroDeDocentes.es_docente()` que depende del almacén."""
        ...
