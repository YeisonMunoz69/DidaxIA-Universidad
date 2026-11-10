from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible

if TYPE_CHECKING:
    from dominio.puertos.estado_vigente import PuertoEstadoVigente

RUTA_DEL_TRAMITE = "/api/datos/supresion"


ESTADO = "eliminacion_solicitada"


def respuesta_de_supresion(detalle: str = "") -> JSONResponse:
    return JSONResponse(
        {
            "detalle": detalle
            or (
                "tienes una solicitud de eliminación en curso: mientras dure no "
                "se registra ningún dato nuevo ni se puede usar el tutor"
            ),
            "estado": ESTADO,
            "usar": RUTA_DEL_TRAMITE,
        },
        status_code=409,
    )

class PuertaDeSupresion:

    def __init__(self, estado_vigente: PuertoEstadoVigente | None) -> None:
        self._estado_vigente = estado_vigente

    def negativa(self, sujeto_google: str) -> JSONResponse | None:
        if self._estado_vigente is None:
            return mantenimiento(
                "no se puede comprobar el estado de tu cuenta en este momento"
            )
        try:
            estado = self._estado_vigente.estado_vigente(sujeto_google)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento(
                "no se puede comprobar el estado de tu cuenta en este momento"
            )
        if estado is None:

            return None
        if estado.eliminacion_solicitada:
            return respuesta_de_supresion()
        return None
