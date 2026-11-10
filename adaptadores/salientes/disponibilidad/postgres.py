from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum

from adaptadores.salientes.notificacion.plantillas import alerta_operativa

_LOG = logging.getLogger(__name__)


UMBRAL_DE_ALERTA_S = 120


INTERVALO_DE_SONDEO_S = 30


CLAVE_CAIDA = "postgres-indisponible/{incidente}"
CLAVE_RECUPERACION = "postgres-recuperado/{incidente}"


_ASUNTO_CAIDA = "DidaxIa · la base de datos no responde"
_ASUNTO_RECUPERACION = "DidaxIa · la base de datos volvió a responder"


class EstadoDisponibilidad(StrEnum):

    DESCONOCIDO = "desconocido"
    SALUDABLE = "saludable"
    INDISPONIBLE = "indisponible"

def sondear_postgres(cadena: str) -> bool:
    from adaptadores.salientes.conexion import conectar

    try:
        with conectar(cadena) as cnx, cnx.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone() is not None
    except Exception:
        return False

def _identificador_de_incidente() -> str:
    return secrets.token_hex(8)

class MonitorDeDisponibilidad:

    def __init__(
        self,
        *,
        sondear: Callable[[], bool],
        notificar,
        destino: str,
        reloj: Callable[[], datetime] = lambda: datetime.now(UTC),
        umbral_s: int = UMBRAL_DE_ALERTA_S,
        identificador: Callable[[], str] = _identificador_de_incidente,
    ) -> None:
        self._sondear = sondear
        self._notificar = notificar
        self._destino = destino
        self._reloj = reloj
        self._umbral_s = umbral_s
        self._identificador = identificador

        self.estado = EstadoDisponibilidad.DESCONOCIDO
        self.ultimo_sondeo: datetime | None = None

        self.incidente_desde: datetime | None = None
        self.incidente: str = ""

        self.aviso_intentado = False

    def observar(self) -> None:
        try:
            respondio = self._sondear()
        except Exception:

            respondio = False
        self.ultimo_sondeo = self._reloj()

        if respondio:
            self._recuperar()
            return
        self._fallar()

    def _fallar(self) -> None:
        ahora = self.ultimo_sondeo
        if self.incidente_desde is None:

            self.incidente_desde = ahora
            self.incidente = self._identificador()
            self.aviso_intentado = False
            _LOG.warning("la base no responde; incidente %s abierto", self.incidente)
        self.estado = EstadoDisponibilidad.INDISPONIBLE

        if self.aviso_intentado:
            return
        transcurrido = (ahora - self.incidente_desde).total_seconds()
        if transcurrido >= self._umbral_s:
            self._alertar(_ASUNTO_CAIDA, CLAVE_CAIDA, self._cuerpo_de_caida(transcurrido))

    def _recuperar(self) -> None:
        alertada = self.incidente_desde is not None and self.aviso_intentado
        incidente = self.incidente
        self.estado = EstadoDisponibilidad.SALUDABLE
        self.incidente_desde = None
        self.incidente = ""
        self.aviso_intentado = False
        if not alertada:

            return
        self._enviar(
            _ASUNTO_RECUPERACION,
            CLAVE_RECUPERACION.format(incidente=incidente),
            "La base de datos volvió a responder y el servicio quedó restablecido.\n\n"
            f"Incidente {incidente}. El estado actual está en /api/salud.",
        )

    def _alertar(self, asunto: str, plantilla: str, cuerpo: str) -> None:
        self.aviso_intentado = True
        self._enviar(asunto, plantilla.format(incidente=self.incidente), cuerpo)

    def _cuerpo_de_caida(self, transcurrido: float) -> str:
        return (
            "La base de datos lleva más de "
            f"{int(self._umbral_s // 60)} minutos sin responder "
            f"({int(transcurrido)} s desde el primer fallo observado).\n\n"
            f"Incidente {self.incidente}. Mientras dure, la aplicación muestra "
            "mantenimiento y no crea sesiones ni escrituras.\n\n"
            "El estado actual está en /api/salud."
        )

    def _enviar(self, asunto: str, clave: str, cuerpo: str) -> None:
        if not self._destino:
            _LOG.warning("sin destino operativo: la alerta %s no se envía", clave)
            return
        try:
            salio = self._notificar.avisar(
                self._destino,
                asunto,
                cuerpo,
                clave_idempotencia=clave,
                html=alerta_operativa(
                    titulo=asunto,
                    mensaje=cuerpo,
                    recuperado=clave.startswith("postgres-recuperado/"),
                ),
            )
        except Exception:

            _LOG.exception("el canal de avisos falló al enviar %s", clave)
            return
        _LOG.info("alerta de disponibilidad %s enviada=%s", clave, salio)

    def como_json(self) -> dict:
        return {
            "configurado": True,
            "estado": self.estado.value,
            "ultimo_sondeo": self.ultimo_sondeo.isoformat() if self.ultimo_sondeo else None,
            "incidente_desde": (
                self.incidente_desde.isoformat() if self.incidente_desde else None
            ),
            "aviso_intentado": self.aviso_intentado,
        }

SIN_MONITOR = {
    "configurado": False,
    "estado": EstadoDisponibilidad.DESCONOCIDO.value,
    "ultimo_sondeo": None,
    "incidente_desde": None,
    "aviso_intentado": False,
}


async def vigilar(
    monitor: MonitorDeDisponibilidad,
    *,
    intervalo_s: float = INTERVALO_DE_SONDEO_S,
    dormir=asyncio.sleep,
) -> None:

    while True:
        await asyncio.to_thread(monitor.observar)
        await dormir(intervalo_s)

@contextlib.asynccontextmanager
async def vigilancia(monitor: MonitorDeDisponibilidad | None, **opciones):
    if monitor is None:
        yield
        return
    tarea = asyncio.create_task(vigilar(monitor, **opciones))
    try:
        yield
    finally:
        tarea.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tarea
