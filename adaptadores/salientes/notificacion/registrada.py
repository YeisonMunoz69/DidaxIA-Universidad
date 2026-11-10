from __future__ import annotations

import logging

_LOG = logging.getLogger(__name__)


class NotificacionRegistrada:

    def __init__(self) -> None:
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

        del correo, cuerpo, html, adjuntos
        self.pendientes.append((asunto, clave_idempotencia))
        _LOG.info(
            "aviso sin canal configurado: %s [%s]", asunto, clave_idempotencia
        )
        return False
