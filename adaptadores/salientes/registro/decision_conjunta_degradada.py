"""
decision_conjunta_degradada.py — La decisión conjunta sin base: falla cerrada
==============================================================================

`PuertoDecisionConjunta` para un despliegue sin PostgreSQL. Levanta
`AlmacenNoConfigurado` y **no guarda nada, en ninguna parte**.

Por qué existe una implementación que sólo sabe negarse
------------------------------------------------------------------
Porque la alternativa que parece amable es la que `EQ-024` prohíbe. El adaptador
heredado de consentimiento —`consentimiento_degradado.py`— devuelve `None` sin
levantar, de modo que quien llama no distingue «no hay fila» de «no hay base». Ahí
era tolerable; aquí sería una autorización inventada: la persona vería «quedó
registrado», cerraría la pantalla y no habría ninguna fila.

Y no puede guardar en memoria «mientras tanto». Un consentimiento en el `dict` de
un proceso desaparece al reiniciar y mientras tanto responde éxito — es
exactamente la memoria ficticia que el cierre V-B retiró de
`POST /api/consentimiento`.

Qué se ve desde fuera
--------------------------
El borde traduce `AlmacenNoConfigurado` a la respuesta de mantenimiento que ya
existe, con su `Retry-After`. La persona ve que el servicio no está disponible,
que es lo cierto, y **no** una aceptación aparente.

Se distingue de `AdaptadorDecisionConjuntaPostgres("")` —que también levantaría
`AlmacenNoConfigurado` en su primera operación— en que éste no puede llegar a
abrir un socket ni aunque alguien le pase una cadena después: no tiene ninguna.


"""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from dominio.puertos.almacen import AlmacenNoConfigurado

if TYPE_CHECKING:  # pragma: no cover
    from dominio.modelo.decision_conjunta import Decision


class AdaptadorDecisionConjuntaDegradado:
    """`PuertoDecisionConjunta` que se niega, siempre y con motivo."""

    def registrar_decision(self, sujeto_google: str, decision: Decision) -> NoReturn:
        """Nunca registra. Levanta `AlmacenNoConfigurado`.

        Los parámetros se reciben y se descartan sin mirarlos: no se guardan, no
        se registran y no se devuelven en el mensaje. El sujeto de Google de una
        persona no tiene por qué aparecer en el texto de una excepción que puede
        acabar en una consola o en un registro de CI.
        """
        raise AlmacenNoConfigurado(
            "no hay base en la que registrar una decisión de consentimiento: la "
            "composición no cableó ninguna"
        )
