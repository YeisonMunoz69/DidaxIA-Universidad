"""
propuestas.py — La doble aprobación de `EQ-023`, como tipo del dominio
========================================================================

`EQ-023` reserva tres cosas a la aprobación de **dos** administradores:

    «Nuevas políticas, exportaciones masivas y eliminaciones excepcionales
    requieren aprobación de ambos.»

⚠️ Qué estaba mal antes, porque explica la forma de este módulo
------------------------------------------------------------------------
La primera implementación pedía en el cuerpo de la petición un campo
`aprobada_por` con el identificador del segundo administrador, comprobaba que
tuviera el rol y daba la operación por aprobada. La auditoría V-B lo devolvió:

    «Dos aprobaciones significan dos actos autenticados. El primer administrador
    no puede escribir `aprobada_por` con el identificador de otro.»

El defecto no era de validación —el rol se comprobaba de verdad— sino de
naturaleza: **quien aprueba tiene que ser quien hace la petición**. Un campo de
texto rellenado por el primero prueba que el primero sabe cómo se llama el
segundo, y nada más.

De ahí salen las dos piezas de aquí:

- **`Propuesta`**, que existe *entre* las dos peticiones. Sin algo que persista
  en medio no hay forma de que el segundo acto sea de otra persona en otra
  sesión.
- **`huella_de()`**, que fija qué se propuso. Sin ella, «lo aprobado es lo
  propuesto» sería una comparación de diccionarios repetida en cada sitio que
  aprobara algo.

Por qué la huella y no comparar el `payload`
------------------------------------------------------
Porque un `dict` no tiene un orden y dos serializaciones del mismo contenido no
son la misma cadena. `huella_de()` fija una **forma canónica** —claves ordenadas,
sin espacios, UTF-8— y la resume en un SHA-256. Dos propuestas con el mismo
contenido dan la misma huella aunque se hayan escrito en distinto orden, y
cualquier cambio en el contenido la cambia entera.

La huella se guarda al proponer y **se recomputa al aprobar**. Si alguien
alterase la fila entre las dos peticiones, la comparación fallaría y la
aprobación no procedería — que es lo que convierte «se aprobó esto» en una
afirmación comprobable y no en una confianza en la base.

Qué NO decide este módulo
--------------------------------------
Qué operaciones exigen doble aprobación y qué hace cada una al aprobarse. Eso
vive donde se aplica el efecto (`adaptadores/salientes/registro/gobierno_db.py`),
porque aplicarlo es hablar con la base y el dominio no lo hace.


"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class PropuestaInvalida(ValueError):
    """Una propuesta que no se puede aceptar o aprobar tal como llega."""


class EstadoPropuesta(StrEnum):
    """Los tres estados. `rechazada` existe porque un segundo administrador
    puede negarse, y omitirlo obligaría a dejar pendiente para siempre lo que
    ya se decidió que no."""

    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


#: Las operaciones que `EQ-023` reserva a la doble aprobación **y que el sistema
#: ya sabe hacer**. Lista cerrada a propósito: una propuesta con una operación
#: desconocida quedaría pendiente para siempre, porque nadie sabría qué aplicar
#: al aprobarla. Ampliarla es una decisión deliberada, no un valor de entrada.
#:
#: ⚠️ Hoy sólo hay una. Las exportaciones masivas y las eliminaciones
#: excepcionales de `EQ-023` **no están construidas** —la cascada irreversible es
#: la decisión humana que el cierre V-B reserva al equipo—, y anotarlas aquí
#: antes de que existan haría creer que se pueden proponer.
OPERACIONES_CON_DOBLE_APROBACION: frozenset[str] = frozenset({"retencion.fijar"})


def huella_de(operacion: str, payload: dict) -> str:
    """El SHA-256 de la forma canónica de lo que se propone.

    `sort_keys` y separadores sin espacios hacen que el mismo contenido dé
    siempre la misma cadena, independientemente de cómo se escribiera el `dict`.
    `ensure_ascii=False` conserva los caracteres tal cual: una tilde no puede
    cambiar la huella según el escape que use quien serialice.

    La operación entra en el resumen y no sólo el contenido: dos operaciones
    distintas con el mismo `payload` son dos propuestas distintas, y una huella
    que no las distinguiera permitiría aprobar una creyendo aprobar la otra.
    """
    canonico = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(f"{operacion}␟{canonico}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Propuesta:
    """Una operación propuesta por un administrador, a la espera de otro."""

    operacion: str
    payload: dict = field(default_factory=dict)
    propuesta_por: str = ""
    propuesta_en: datetime | None = None
    estado: EstadoPropuesta = EstadoPropuesta.PENDIENTE
    aprobada_por: str | None = None
    aprobada_en: datetime | None = None
    secuencia: int = 0

    def __post_init__(self) -> None:
        operacion = (self.operacion or "").strip()
        if operacion not in OPERACIONES_CON_DOBLE_APROBACION:
            raise PropuestaInvalida(
                f"{operacion!r} no es una operación que exija doble aprobación (EQ-023)"
            )
        object.__setattr__(self, "operacion", operacion)
        if not isinstance(self.payload, dict):
            raise PropuestaInvalida("el contenido propuesto tiene que ser un objeto")
        object.__setattr__(self, "estado", EstadoPropuesta(self.estado))
        if self.aprobada_por is not None and self.aprobada_por == self.propuesta_por:
            raise PropuestaInvalida("nadie puede aprobar su propia propuesta")

    @property
    def huella(self) -> str:
        """La huella de **este** contenido, recalculada cada vez.

        Propiedad y no campo a propósito: un campo se puede quedar viejo respecto
        del `payload` que acompaña, y entonces la garantía de «lo aprobado es lo
        propuesto» dependería de que alguien acordara actualizarlo.
        """
        return huella_de(self.operacion, self.payload)

    @property
    def pendiente(self) -> bool:
        return self.estado is EstadoPropuesta.PENDIENTE

    def exigir_aprobable_por(self, aprobador: str) -> None:
        """Que esta propuesta pueda aprobarla **esa** persona, o el motivo.

        Las dos condiciones que no dependen de la base, juntas y con nombre: si
        vivieran sueltas en el repositorio, la segunda implementación que
        aprobara algo se dejaría una.
        """
        if not (aprobador or "").strip():
            raise PropuestaInvalida("una aprobación necesita quién la hace")
        if aprobador == self.propuesta_por:
            raise PropuestaInvalida("nadie puede aprobar su propia propuesta")
        if not self.pendiente:
            raise PropuestaInvalida(
                f"esta propuesta ya está {self.estado.value}: no se aprueba dos veces"
            )
