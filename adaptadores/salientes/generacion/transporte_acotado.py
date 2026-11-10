"""Transporte optativo que acota la lectura incluso si llegan fragmentos vacíos."""

import time
import urllib.error
import urllib.request

from adaptadores.salientes.generacion.deepseek import ResultadoHTTP
from adaptadores.salientes.generacion.red import abrir_con_reintento_dns


class TransporteAcotado:
    def __init__(self, url, clave, tiempo_maximo_s):
        if tiempo_maximo_s <= 0:
            raise ValueError("el plazo total debe ser positivo")
        self.url, self.clave, self.tiempo = url, clave, tiempo_maximo_s

    def enviar(self, cuerpo):
        limite = time.monotonic() + self.tiempo
        peticion = urllib.request.Request(self.url, data=cuerpo, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self.clave}",
        })
        try:
            with abrir_con_reintento_dns(peticion, self.tiempo) as respuesta:
                return ResultadoHTTP(respuesta.status, self._leer(respuesta, limite))
        except urllib.error.HTTPError as exc:
            # Acotar también los cuerpos de error; no revelar ni imprimir el cuerpo.
            try:
                with exc:
                    return ResultadoHTTP(exc.code, self._leer(exc.fp, limite))
            except TimeoutError:
                return ResultadoHTTP(0, fallo="plazo total agotado al leer el proveedor")
        except TimeoutError:
            return ResultadoHTTP(0, fallo="plazo total agotado al leer el proveedor")
        except urllib.error.URLError:
            return ResultadoHTTP(0, fallo="no se pudo contactar al proveedor")

    @staticmethod
    def _leer(respuesta, limite):
        partes, longitud = [], 0
        while True:
            restante = limite - time.monotonic()
            if restante <= 0:
                raise TimeoutError()
            # HTTPResponse expone read1: devuelve el fragmento disponible en vez
            # de esperar a reunir todo el cuerpo. Ajustar el socket por lectura
            # evita que los espacios de keep-alive renueven el presupuesto.
            socket = getattr(getattr(respuesta.fp, "raw", None), "_sock", None)
            if socket is not None:
                socket.settimeout(restante)
            fragmento = respuesta.read1(65536)
            if not fragmento:
                return b"".join(partes)
            longitud += len(fragmento)
            if longitud > 2_000_000:
                raise urllib.error.URLError("respuesta demasiado grande")
            partes.append(fragmento)
