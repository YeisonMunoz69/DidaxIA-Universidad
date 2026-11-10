"""
instantaneas.py — Contrato para publicar y leer el documento de una versión
=============================================================================

Dos operaciones, y la primera es una sola por un motivo concreto.

Por qué publicar es UNA operación y no dos
----------------------------------------------
Una versión sin su instantánea es exactamente el estado roto que todo esto
existe para cerrar: la fila dice que hay un documento publicado, la pantalla
enseña su huella, y no hay nada que leer. Si publicar fueran dos llamadas
—«registra la versión» y luego «guarda el texto»— ese estado sería alcanzable
con que la segunda fallara, y quedaría escrito en una tabla inmutable donde no
se puede corregir: habría que publicar otro código para arreglarlo.

Por eso `publicar()` recibe una `PublicacionDeVersion` —metadatos **y** cuerpo—
y el adaptador la escribe en **una transacción**. O están las dos cosas o no
está ninguna.

Idempotencia y colisión · las dos mitades de `§8.6`/`§8.7`
--------------------------------------------------------------
Son la misma comprobación mirada desde los dos lados, y por eso las decide el
mismo método en vez de repartirlas entre la herramienta y la base:

- **mismo código, mismo contenido** → no se escribe nada y se informa. Publicar
  dos veces desde un guion que se reintenta no puede fallar ni duplicar;
- **mismo código, contenido distinto** → se **detiene**. Sobrescribir borraría
  la prueba de qué leyó quien ya aceptó, y es el caso que más importa fallar
  cerrado: significa que alguien está publicando otro documento bajo un nombre
  que ya se usó.

La segunda es la que hace cierta la regla de `§8.5` —cambiar una coma exige un
código nuevo— sin depender de que quien publique se acuerde.

Leer no exige autorización de escritura
-------------------------------------------
`instantanea_de()` es una lectura por **código**, nunca por ruta. Es lo que la
ruta HTTP sirve para que la persona pueda leer el documento antes de decidir, y
lo que permite que un tercero recalcule el SHA-256 y compruebe la huella años
después. Quién puede llamarla lo decide el borde, no este contrato.


"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from dominio.modelo.instantanea_consentimiento import (
    InstantaneaDeVersion,
    PublicacionDeVersion,
)


@dataclass(frozen=True, slots=True)
class ResultadoDePublicacion:
    """En qué acabó una publicación, para poder informarlo sin adivinarlo.

    `escrita` distingue «se publicó ahora» de «ya estaba, idéntica». Las dos son
    éxito y la herramienta las imprime distinto: quien ejecuta necesita saber si
    su comando cambió algo o si estaba repitiendo uno anterior.
    """

    codigo: str
    escrita: bool
    motivo: str = ""


@runtime_checkable
class PuertoInstantaneasDeConsentimiento(Protocol):
    """Publicar una versión con su documento, y leer el documento publicado."""

    def publicar(self, publicacion: PublicacionDeVersion) -> ResultadoDePublicacion:
        """Escribe versión, finalidades e instantánea en una sola transacción.

        Idempotente para el mismo código con el mismo contenido: no escribe y
        devuelve `escrita=False`. Levanta `EscrituraRechazada` si el código ya
        existe con **otro** contenido u otra huella — ver la cabecera.
        """
        ...

    def publicar_lote(
        self, publicaciones: Sequence[PublicacionDeVersion]
    ) -> tuple[ResultadoDePublicacion, ...]:
        """El paquete entero en **una sola** transacción · `C1-D`.

        🔴 **No es azúcar sobre `publicar()`, es la unidad de atomicidad.** Un
        manifiesto de consentimiento se aprueba como conjunto —titular,
        asentimiento y representante—, y publicar la mitad deja el recorrido del
        menor a medias y un documento rigiendo suelto que nadie aprobó así.

        Publicar uno a uno no se puede compensar después: estas tablas son
        deliberadamente inmutables, así que lo escrito no se deshace con un
        `DELETE`. O entra todo en la misma transacción, o no hay atomicidad.

        Una entrada rechazada deja **cero** cambios del lote. Repetir un lote
        idéntico escribe cero. Un lote mixto —algunas ya publicadas idénticas y
        otras nuevas— escribe sólo las nuevas, que es lo que permite completar
        un paquete que se cortó a medias.
        """
        ...

    def instantanea_de(self, codigo: str) -> InstantaneaDeVersion | None:
        """El documento publicado bajo ese código, o `None` si no hay ninguno.

        `None` no es un error: una versión de antes de que existiera esta tabla
        no tiene instantánea, y quien llame tiene que poder distinguir eso de un
        código inexistente sin recibir una excepción por algo previsible.
        """
        ...
