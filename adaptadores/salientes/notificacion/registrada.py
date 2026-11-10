"""
registrada.py — El aviso que se anota y no se envía (`EQ-022`, `EQ-024`)
=========================================================================

`PuertoNotificacion` cuando **no hay canal configurado**: sin clave de Resend,
sin remitente, o con sólo uno de los dos.

Por qué sigue existiendo después de `D2`
----------------------------------------------------
Porque la ausencia de configuración no puede bloquear el trámite. `D2` añade
`AdaptadorResend`, pero la regla de `EQ-024` no cambia: un despliegue sin clave
—el de quien desarrolla, el de la primera puesta en marcha— tiene que poder
registrar una supresión y una decisión conjunta igual. Este adaptador es lo que
hace que «sin canal» sea un estado declarado y no un `None` que revienta en la
primera llamada.

Por qué devuelve `False` y no levanta
-------------------------------------------------
`EQ-024`: *«Resend será un canal de notificación, no una dependencia del
diagnóstico ni una garantía de disponibilidad»*. Una solicitud de supresión
**queda registrada** aunque el aviso no salga, y hacer fallar el trámite porque
el correo no se pudo enviar convertiría el canal en la garantía que la decisión
dice que no es.

Qué NO guarda, y es la mitad de su contrato
-----------------------------------------------------
No guarda ni registra **correo, cuerpo, clave de API, cabeceras ni cadena de
conexión**. Conserva el asunto y la clave de idempotencia, que son los dos
únicos valores del aviso sin datos personales dentro: el asunto es una constante
del código y la clave es `<hecho>/<secuencia>`, un identificador de fila.

`_LOG.info` con el texto del aviso dejaría un correo institucional en el
registro del proceso; a quién iba dirigido ya lo sabe la fila persistida.


"""

from __future__ import annotations

import logging

_LOG = logging.getLogger(__name__)


class NotificacionRegistrada:
    """`PuertoNotificacion` que anota la intención y no envía nada."""

    def __init__(self) -> None:
        #: Los avisos que no salieron, como `(asunto, clave)`, para que una
        #: prueba pueda comprobarlos sin leer el registro del proceso. **No
        #: guarda destinatario ni cuerpo**: ver el docstring del módulo.
        self.pendientes: list[tuple[str, str]] = []

    def avisar(
        self,
        correo: str,
        asunto: str,
        cuerpo: str,
        *,
        clave_idempotencia: str,
        html: str = "",
        adjuntos: tuple[dict[str, str], ...] = (),
    ) -> bool:
        """Nunca envía. Ver el docstring del módulo.

        `correo` y `cuerpo` se reciben porque el puerto los define, y se
        descartan aquí mismo: son los dos parámetros que este adaptador tiene
        prohibido conservar.
        """
        del correo, cuerpo, html, adjuntos
        self.pendientes.append((asunto, clave_idempotencia))
        _LOG.info(
            "aviso sin canal configurado: %s [%s]", asunto, clave_idempotencia
        )
        return False
