"""Reintento acotado antes de establecer una conexión con el proveedor."""

import socket
import time
import urllib.error
import urllib.request


def abrir_con_reintento_dns(peticion, tiempo_maximo_s):
    """Reintenta sólo una resolución DNS fallida, sin reenviar un POST aceptado.

    HTTP 429/5xx, TLS y tiempos de lectura conservan su tratamiento habitual.
    Todos los intentos comparten el presupuesto de apertura original.
    """
    limite = time.monotonic() + tiempo_maximo_s
    for intento in range(3):
        restante = limite - time.monotonic()
        if restante <= 0:
            raise TimeoutError()
        try:
            return urllib.request.urlopen(peticion, timeout=restante)
        except urllib.error.URLError as exc:
            if not isinstance(exc.reason, socket.gaierror) or intento == 2:
                raise
            pausa = min(0.2 * (intento + 1), max(0, limite - time.monotonic()))
            time.sleep(pausa)
    raise TimeoutError()  # Los tres intentos fallidos siempre lanzan antes.
