from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from adaptadores.salientes.notificacion.registrada import NotificacionRegistrada

if TYPE_CHECKING:
    from dominio.puertos.gobierno import PuertoNotificacion

VARIABLE_CLAVE = "RESEND_API_KEY"
VARIABLE_REMITENTE = "RESEND_REMITENTE"
VARIABLE_DESTINO_OPERATIVO = "CORREO_PRIVACIDAD"
VARIABLE_DESTINO_INVESTIGACION = "CORREO_INVESTIGACION"


@dataclass(frozen=True, slots=True)
class Canal:

    puerto: PuertoNotificacion

    nombre: str

    clave: bool

    remitente: bool

    destino_operativo: str = ""

    destino_investigacion: str = ""

    @property
    def envia(self) -> bool:
        return self.nombre == "resend"

    @property
    def parcial(self) -> bool:
        return self.clave != self.remitente

    def como_json(self) -> dict:
        return {
            "canal": self.nombre,
            "configurado": self.envia,
            "clave_presente": self.clave,
            "remitente_presente": self.remitente,
            "destino_operativo_presente": bool(self.destino_operativo),
            "destino_investigacion_presente": bool(self.destino_investigacion),
        }

    def faltantes(self) -> list[str]:
        lineas: list[str] = []
        if self.parcial:
            falta = VARIABLE_CLAVE if not self.clave else VARIABLE_REMITENTE
            lineas.append(
                f"el canal de avisos de EQ-022 está configurado a medias: falta {falta}. "
                "Los avisos se registran y no se envían"
            )
        elif not self.envia:
            lineas.append(
                f"el canal de avisos de EQ-022 no está configurado ({VARIABLE_CLAVE} y "
                f"{VARIABLE_REMITENTE}): los avisos al titular se registran y no se envían"
            )
        if not self.destino_operativo:
            lineas.append(
                f"{VARIABLE_DESTINO_OPERATIVO} no está en el entorno: las alertas de "
                "disponibilidad de EQ-024 no tienen destino y no se envían"
            )
        if not self.destino_investigacion:
            lineas.append(
                f"{VARIABLE_DESTINO_INVESTIGACION} no está en el entorno: el equipo de "
                "investigación no recibe por correo las solicitudes de matrícula"
            )
        return lineas

def componer_canal(entorno: dict | None = None) -> Canal:
    valores = os.environ if entorno is None else entorno
    clave = (valores.get(VARIABLE_CLAVE) or "").strip()
    remitente = (valores.get(VARIABLE_REMITENTE) or "").strip()
    destino = (valores.get(VARIABLE_DESTINO_OPERATIVO) or "").strip()
    destino_investigacion = (valores.get(VARIABLE_DESTINO_INVESTIGACION) or "").strip()

    if clave and remitente:
        from adaptadores.salientes.notificacion.resend import (
            AdaptadorResend,
        )

        return Canal(
            puerto=AdaptadorResend(remitente=remitente, clave=clave),
            nombre="resend",
            clave=True,
            remitente=True,
            destino_operativo=destino,
            destino_investigacion=destino_investigacion,
        )

    return Canal(
        puerto=NotificacionRegistrada(),
        nombre="registrada",
        clave=bool(clave),
        remitente=bool(remitente),
        destino_operativo=destino,
        destino_investigacion=destino_investigacion,
    )
