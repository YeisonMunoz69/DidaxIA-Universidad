import socket
import time
import urllib.error
import urllib.request


def abrir_con_reintento_dns(peticion, tiempo_maximo_s):
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
    raise TimeoutError()
