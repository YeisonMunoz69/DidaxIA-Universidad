"""
consentimiento_degradado.py — El consentimiento cuando no hay base
=======================================================================

La implementación de `PuertoConsentimiento` que ocupa el lugar de
`AdaptadorConsentimientoPostgres` cuando `AGENTE_BD` no está en el entorno.

Por qué NO guarda nada en memoria
----------------------------------------
Porque tiene que reproducir **exactamente** el comportamiento que ya existía,
y el que existía no guardaba nada: sin `AGENTE_BD`, `guardar_consentimiento()`
salía sin escribir y `consultar_consentimiento()` devolvía `None` siempre. Un
almacén en memoria que sí recordara la decisión cambiaría lo que responde
`POST /api/sesion/reiniciar` a quien tiene identidad estable —le devolvería un
consentimiento que hoy no le devuelve—, y eso es una decisión de la Fase 3
(`EQ-016`), no una consolidación de contrato.

Se escribe como clase, y no como un `if` en la ruta, para que la degradación
sea una implementación del mismo puerto y no una rama de la lógica del borde:
la ruta llama igual en los dos casos y no pregunta si hay base.

Qué NO significa
-----------------------
**No significa «consentimiento denegado» ni «pendiente».** El estado de la
sesión lo sigue llevando `Sesiones`, en memoria del proceso, exactamente como
antes. Esto solo dice que **no hay dónde persistirlo**, que es lo que
`GET /api/salud` ya declara para las otras piezas que dependen de la base.


"""

from __future__ import annotations


class AdaptadorConsentimientoDegradado:
    """`PuertoConsentimiento` sin almacén. Ver el docstring del módulo."""

    def guardar(
        self,
        identificador_sujeto: str,
        correo: str,
        decision: str,
        edad: int | None = None,
    ) -> None:
        """No hay dónde escribir. Se descarta en silencio, igual que antes."""

    def consultar(self, identificador_sujeto: str, correo: str = "") -> dict | None:
        """Nunca hay fila previa que recuperar: sin base no se guardó ninguna."""
        return None
