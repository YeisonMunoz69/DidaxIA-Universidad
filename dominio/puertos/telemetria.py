"""
telemetria.py — El contrato de escritura de eventos históricos
================================================================

Un solo método, y su valor de retorno es la mitad del contrato.

`registrar()` devuelve `True` si la fila es nueva y `False` si esa clave de
idempotencia ya estaba. **No levanta por duplicado**: un reintento no es un
error, es el caso normal de un cliente que no recibió la respuesta. Quien
llama necesita distinguirlos —la API de la interfaz responde `201` o `200`— y
una excepción habría obligado a capturarla para tratar lo esperado.

Por qué la telemetría NO comparte transacción con lo que mide
---------------------------------------------------------------------
Es la diferencia con `auditoria_sql.anotar()`, y conviene decirla entera.

**La auditoría sí es atómica**, porque `EQ-023` lo exige: *«una operación
auditable no puede informar éxito sin auditoría»*. Consultar KPI
institucionales es una lectura sensible y su constancia va dentro de la misma
transacción que la lectura.

**La telemetría no lo es**, y es deliberado: mide el producto, no lo autoriza.
Si la escritura del evento fallara dentro de la transacción del turno, la
alternativa sería perder el turno del estudiante para no perder una medición.
Ese intercambio está al revés. El instrumentador de
`adaptadores/entrantes/http/instrumentacion.py` absorbe el fallo, el turno
sigue y el hueco se ve luego como retraso o ausencia en la superficie de
calidad de datos —que es exactamente para lo que sirve `registrado_en`—.

⚠️ La consecuencia se declara en vez de descubrirse: **un indicador construido
sobre telemetría puede subestimar**. Nunca sobreestima, porque un evento no se
inventa; puede faltar. Las definiciones del catálogo que dependen de
`evento_telemetria` lo llevan escrito en sus limitaciones.


"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from dominio.modelo.telemetria import EventoTelemetria


@runtime_checkable
class PuertoTelemetria(Protocol):
    def registrar(
        self, evento: EventoTelemetria, *, alcance_institucional: bool = False
    ) -> bool:
        """Persiste el hecho. `True` si es nuevo, `False` si ya estaba.

        La implementación tiene que comprobar, **en la misma transacción en la
        que escribe**, que la clase referida existe y que el sujeto puede
        escribir en ella. ``alcance_institucional`` exige además comprobar el
        rol investigador persistido dentro de esa transacción. Comprobarlo antes
        en otra conexión dejaría el hueco
        que `autorizacion_sql.py` documenta para los roles: entre la
        comprobación y el efecto cabe un cambio.
        """
        ...
