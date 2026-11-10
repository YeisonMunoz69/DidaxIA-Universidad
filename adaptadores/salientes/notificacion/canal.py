"""
canal.py — Qué adaptador de aviso se compone, y cómo se declara (`D2`)
========================================================================

Un sitio donde se leen las variables de `EQ-024`/`Guia-Resend.md` §5 y se
decide con cuál de los dos adaptadores queda cableado `PuertoNotificacion`:

    RESEND_API_KEY      secreta · la clave de envío restringida al dominio
    RESEND_REMITENTE    pública · «Nombre <buzón@subdominio-verificado>»
    CORREO_PRIVACIDAD   pública · a dónde van las alertas de operación
    CORREO_INVESTIGACION pública · buzones, separados por coma, que revisan matrícula

Las credenciales y el remitente no se escriben aquí ni en ninguna otra parte
del código: viven en el `.env` ignorado. Los tres destinos de investigación sí
son direcciones institucionales públicas ratificadas por el equipo y tienen un
valor predeterminado en Compose; el `.env` puede sustituir la lista completa.

Por qué un módulo y no cuatro líneas en `aplicacion.py`
--------------------------------------------------------------
Porque el resultado tiene **tres consumidores** —gobierno, decisión conjunta y
el monitor de disponibilidad— y dos de ellos necesitan además saber *cómo quedó
configurado* para publicarlo en `GET /api/salud`. Repartir la lectura del
entorno entre los tres habría permitido que uno mirara `RESEND_API_KEY` y otro
no, y que la salud dijera una cosa mientras el envío hacía otra.

`Canal` es lo que sale de aquí: el puerto ya elegido, el destino operativo y la
descripción publicable. **No es un contenedor de servicios**; es el resultado de
una decisión de composición, con nombre.

La regla, entera
------------------------
| clave | remitente | qué se compone |
|---|---|---|
| sí | sí | `AdaptadorResend` |
| no | sí | `NotificacionRegistrada` + línea de configuración parcial |
| sí | no | `NotificacionRegistrada` + línea de configuración parcial |
| no | no | `NotificacionRegistrada` + línea de canal no configurado |

La ausencia **nunca** bloquea el arranque ni el trámite: `EQ-024` dice que el
canal informa y no decide, así que un despliegue sin clave registra la supresión
igual y responde `aviso_enviado: false`, que es la verdad.

⚠️ `CORREO_PRIVACIDAD` es una cuarta fila del cuadro, no una quinta columna. No
interviene en qué adaptador se compone —los avisos al titular van a **su** correo
verificado, no a este— y sólo decide si el monitor de `D2-B` tiene a dónde
alertar. Se declara aparte por eso.

Qué NO sale de aquí
---------------------------
Ningún valor. `como_json()` publica banderas y el nombre del canal; el correo de
privacidad, el remitente y la clave no se copian a la salud, a una respuesta ni
a un registro. Es el mismo criterio con el que `/api/salud` publica que falta
`GOOGLE_CLIENT_ID` sin publicar ningún identificador.


"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from adaptadores.salientes.notificacion.registrada import NotificacionRegistrada

if TYPE_CHECKING:  # pragma: no cover
    from dominio.puertos.gobierno import PuertoNotificacion

#: Los nombres decididos en `Guia-Resend.md` §5. No se inventa `CANAL_PRIVACIDAD`
#: ni ninguna otra: las variables que el equipo decidió para este canal.
VARIABLE_CLAVE = "RESEND_API_KEY"
VARIABLE_REMITENTE = "RESEND_REMITENTE"
VARIABLE_DESTINO_OPERATIVO = "CORREO_PRIVACIDAD"
VARIABLE_DESTINO_INVESTIGACION = "CORREO_INVESTIGACION"


@dataclass(frozen=True, slots=True)
class Canal:
    """El canal de avisos ya compuesto, con lo que de él se puede publicar."""

    #: El adaptador que las rutas y el monitor consumen. Siempre hay uno.
    puerto: PuertoNotificacion
    #: `"resend"` o `"registrada"`. Es el nombre del adaptador, no un secreto.
    nombre: str
    #: Si había clave. **Nunca la clave.**
    clave: bool
    #: Si había remitente. **Nunca el remitente.**
    remitente: bool
    #: A dónde alerta el monitor de `D2-B`. Se usa, no se publica.
    destino_operativo: str = ""
    #: Lista de buzones institucionales que reciben solicitudes para revisión.
    destino_investigacion: str = ""

    @property
    def envia(self) -> bool:
        """Si este canal puede llegar a enviar algo de verdad."""
        return self.nombre == "resend"

    @property
    def parcial(self) -> bool:
        """Configurado a medias: uno de los dos valores, no los dos.

        Se distingue de «no configurado» porque se arregla de otra forma —falta
        **una** variable, no el canal entero— y porque es el estado que más
        fácilmente pasa por bueno: alguien puso la clave, vio que el sistema
        arrancaba y dio el canal por hecho.
        """
        return self.clave != self.remitente

    def como_json(self) -> dict:
        """Lo que `GET /api/salud` publica. Banderas, nunca valores."""
        return {
            "canal": self.nombre,
            "configurado": self.envia,
            "clave_presente": self.clave,
            "remitente_presente": self.remitente,
            "destino_operativo_presente": bool(self.destino_operativo),
            "destino_investigacion_presente": bool(self.destino_investigacion),
        }

    def faltantes(self) -> list[str]:
        """Las líneas de `GET /api/salud` que describen lo que falta.

        Van a la misma lista que el resto de carencias del despliegue porque es
        donde quien opera el sistema ya mira, y porque una carencia que sólo
        aparece en un bloque nuevo es una carencia que nadie ve hasta que la
        busca.
        """
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
    """Lee las variables del canal y devuelve la composición ya decidida.

    `entorno` se inyecta en las pruebas —un diccionario, no `monkeypatch`— para
    poder comprobar las cuatro combinaciones sin tocar el proceso.

    ⚠️ **No levanta nunca.** Una configuración ausente o parcial es un estado
    válido del despliegue, no un error de arranque: `EQ-024` exige que el
    sistema siga registrando trámites sin canal.
    """
    valores = os.environ if entorno is None else entorno
    clave = (valores.get(VARIABLE_CLAVE) or "").strip()
    remitente = (valores.get(VARIABLE_REMITENTE) or "").strip()
    destino = (valores.get(VARIABLE_DESTINO_OPERATIVO) or "").strip()
    destino_investigacion = (valores.get(VARIABLE_DESTINO_INVESTIGACION) or "").strip()

    if clave and remitente:
        from adaptadores.salientes.notificacion.resend import (  # noqa: PLC0415
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
