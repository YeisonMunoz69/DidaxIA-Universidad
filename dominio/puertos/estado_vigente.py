"""
estado_vigente.py — Contrato de la consulta determinista del estado vigente
=============================================================================

Un solo método, y es el que sostiene toda la Fase 3. `dominio/modelo/acceso.py`
sabe calcular el acceso a partir de un `EstadoVigente`; este puerto es quien lo
produce leyendo los eventos.

Por qué es un puerto aparte y no un método más de los otros cuatro
--------------------------------------------------------------------------
Porque cruza las tres dimensiones: perfil, consentimiento, asentimiento y
evidencia del representante. Colgarlo de cualquiera de los cuatro almacenes le
habría dado a ese almacén autoridad sobre los otros tres. Colgarlo aquí deja la
composición libre de resolverlo con una sola consulta —que es lo que hace el
adaptador PostgreSQL— o combinando los otros puertos.

Determinismo, y qué significa exactamente
--------------------------------------------------
Dos eventos del mismo sujeto con marcas temporales próximas —incluso idénticas—
tienen que producir siempre el mismo estado. No basta con `ORDER BY momento`: dos
filas escritas en la misma transacción pueden compartir `now()` al microsegundo.
La implementación desempata con la secuencia monótona del almacén, y
`pruebas/integracion/test_identidad_consentimiento_postgres.py` lo comprueba
escribiendo dos eventos con el mismo `momento` a propósito.

Los tres desenlaces que este método distingue
------------------------------------------------------
- **`None`** · esa persona no está registrada. No existe fila de identidad.
- **un `EstadoVigente`** · existe, y su `consentimiento` puede ser `pendiente`,
  que es un estado real y no una ausencia.
- **`AlmacenNoDisponible`** · no se sabe. Quien llama muestra mantenimiento
  (`EQ-024`), nunca un onboarding que la persona ya completó.


"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dominio.modelo.acceso import EstadoVigente


@runtime_checkable
class PuertoEstadoVigente(Protocol):
    """La lectura que `dominio/modelo/acceso.py` consume."""

    def estado_vigente(self, sujeto_google: str) -> EstadoVigente | None:
        """El estado de las tres dimensiones, o `None` si no hay persona.

        No calcula el acceso: eso es del dominio, y hacerlo aquí ataría la regla
        de `EQ-016` a la implementación del almacén. Devuelve los hechos; la
        regla los interpreta.

        `eliminacion_solicitada` llega siempre en `False` en esta sesión: el
        trámite de `EQ-022` es la sesión 4 y no tiene almacén todavía. El campo
        existe para que añadirlo no cambie ni este contrato ni el cálculo.
        """
        ...
