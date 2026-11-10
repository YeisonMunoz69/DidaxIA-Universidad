"""
consentimiento_versionado.py — Contrato de versiones y eventos (`EQ-021`)
==========================================================================

La frontera nueva del consentimiento. Convive con
`dominio/puertos/consentimiento.py` —el heredado, que las rutas HTTP consumen— y
**no lo modifica**: cambiar aquel puerto habría cambiado el comportamiento
observable de `POST /api/consentimiento`, que es de la sesión 3.

En qué se diferencia del heredado, punto por punto
-----------------------------------------------------------
| | heredado | éste |
|---|---|---|
| forma | una fila por titular, `ON CONFLICT DO UPDATE` | una fila por acto |
| estados | `otorgado` / `rechazado` | los cuatro de `EQ-016` |
| versión | no existe | obligatoria, con huella del contenido |
| finalidades | no existen | catálogo cerrado por versión |
| reaceptar | pisa el rechazo anterior | evento nuevo; el anterior se conserva |
| fallo del almacén | se registra un aviso y se devuelve `None` | levanta |

Esa última fila es la que más cambia. El adaptador heredado captura cualquier
excepción y devuelve `None`, de modo que «no hay fila», «no hay base» y «la base
falló» llegan iguales a quien pregunta. Aquí no: `None` es sólo ausencia de
registro y todo lo demás levanta (ver `dominio/puertos/almacen.py`).

Dos puertos y no uno
------------------------
Las versiones las publica el equipo y se consultan; los eventos los produce cada
persona. Tienen consumidores, frecuencias y permisos distintos —`EQ-023` reserva
publicar una política a la doble aprobación— y juntarlos habría obligado a
cualquier implementación futura a ofrecer las dos capacidades a la vez.

Alcance y vigencia son de la base, no de un `if`
---------------------------------------------------------
Una versión de alcance `asentimiento` no puede recibir un consentimiento del
titular, y una versión futura o vencida no puede recibir ningún acto. Las dos
reglas viven en `11-identidad-consentimiento.sql` —clave foránea compuesta contra
`(codigo, alcance)` y disparador de vigencia—, y el repositorio las comprueba
además antes de escribir para poder dar un motivo: `AlcanceIncorrecto` y
`VersionNoVigente` en vez de una violación de clave.

⚠️ Ninguna versión se define en este árbol. El texto final sigue abierto en
`DECISIONES.md`; `registrar_version()` existe para cuando el equipo lo apruebe.


"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dominio.modelo.consentimiento import (
    Alcance,
    EstadoConsentimiento,
    EventoConsentimiento,
    HistorialDeConsentimiento,
    VersionDeConsentimiento,
)


@runtime_checkable
class PuertoVersionesDeConsentimiento(Protocol):
    """El catálogo de documentos publicados: qué se firmó, no quién lo firmó."""

    def registrar_version(self, version: VersionDeConsentimiento) -> None:
        """Publica una versión con su alcance, finalidades, huella y vigencia.

        Levanta `EscrituraRechazada` si el código ya existe: una versión
        publicada no se reescribe, porque su huella es la prueba de qué texto
        leyó quien la aceptó. Una corrección es una versión nueva.
        """
        ...

    def consultar_version(self, codigo: str) -> VersionDeConsentimiento | None:
        """La versión y sus finalidades, o `None` si ese código no existe."""
        ...

    def versiones(self, alcance: Alcance | None = None) -> tuple[VersionDeConsentimiento, ...]:
        """Todas, o las de un alcance, ordenadas por `vigente_desde` descendente."""
        ...

    def version_requerida(self, alcance: Alcance) -> VersionDeConsentimiento | None:
        """La versión que rige AHORA en ese alcance, o `None` si no rige ninguna.

        La selección es determinista y su regla es parte del contrato, no del
        adaptador:

        - `vigente_desde <= ahora`;
        - `vigente_hasta` es NULL **o** `ahora < vigente_hasta`;
        - si hubiera más de una candidata, `vigente_desde DESC, codigo DESC`.

        `None` es un resultado normal y hoy es el único posible en este árbol: el
        equipo todavía no ha publicado ningún texto. Quien lo reciba **no puede
        presentar el acceso como habilitado** — no hay nada que aceptar.
        """
        ...


@runtime_checkable
class PuertoEventosDeConsentimiento(Protocol):
    """El historial inmutable del titular."""

    def registrar(
        self,
        sujeto_google: str,
        version: str,
        estado: EstadoConsentimiento,
        comprobante: str,
    ) -> EventoConsentimiento:
        """Añade un acto y devuelve el evento con su secuencia ya asignada.

        Comprueba la transición contra el estado vigente **dentro de la misma
        transacción** y levanta `TransicionInvalida` si no procede: hacerlo fuera
        dejaría una ventana en la que dos peticiones simultáneas escriben dos
        actos incompatibles.

        Levanta `ReferenciaDesconocida` si el sujeto o la versión no existen.
        Nunca actualiza una fila anterior.
        """
        ...


    def version_de_la_concesion(self, sujeto_google: str) -> str | None:
        """La versión de la última concesión **otorgada**, o `None`.

        Es lo que permite revocar sin que el cliente elija versión (hito R3).
        `EQ-022` separa dos vigencias y ésta es la segunda: quien otorgó conserva
        el derecho a retirar **esa** concesión aunque su documento haya vencido o
        haya sido desplazado por uno posterior.

        `None` significa que no hay ninguna concesión otorgada que retirar —ni un
        rechazo ni una revocación previa lo son—, y quien llame debe responder un
        rechazo con motivo, no un error. Un almacén caído levanta.

        ⚠️ No sustituye a la comprobación de la escritura. `registrar()` vuelve a
        exigir que la versión sea la de la concesión otorgada dentro de su propia
        transacción, así que una revocación concurrente entre esta lectura y
        aquella escritura se rechaza limpiamente en vez de retirar otra cosa.
        """
        ...

    def historial(self, sujeto_google: str) -> HistorialDeConsentimiento:
        """Todos los eventos, del más antiguo al más reciente.

        Devuelve un historial **vacío** —no `None`— para un sujeto sin eventos:
        su estado derivado es `pendiente`, que es un estado real y distinto de
        «esta persona no existe». Quien necesite esa otra distinción consulta la
        identidad.

        El orden es determinista aunque dos eventos compartan `momento`: la
        secuencia monótona del almacén desempata.
        """
        ...
