"""Telemetría cerrada cuando PostgreSQL no está configurado.

Falla cerrada y **no en silencio**, igual que el resto de piezas que dependen de
la base: un `registrar()` que devolviera `True` sin escribir informaría de una
medición que no existe, y el indicador construido encima parecería instrumentado.

Quien absorbe este fallo es el instrumentador del borde HTTP, no este adaptador:
ahí es donde se decide que un turno vale más que su medición, y esa decisión
tiene que estar en un solo sitio visible.
"""

from __future__ import annotations

from dominio.puertos.almacen import AlmacenNoConfigurado


class TelemetriaNoConfigurada:
    def registrar(self, *_args, **_kwargs) -> bool:
        raise AlmacenNoConfigurado("la telemetría de la Fase 8 necesita PostgreSQL")
