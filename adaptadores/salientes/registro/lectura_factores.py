"""Recuperación de trazas para pendientes; no infiere evidencia ausente."""

from adaptadores.salientes.registro.lectura_trazas_anteproyecto import leer_trazas


def completar_trazas(registros):
    salida = []
    for registro in registros:
        fila = dict(registro)
        if fila.get("trazas") is None:
            trazas, _ = leer_trazas([fila])
            fila["trazas"] = trazas[0]["trazas"] if trazas else []
            fila["trazas_faltantes"] = not bool(trazas)
        salida.append(fila)
    return salida
