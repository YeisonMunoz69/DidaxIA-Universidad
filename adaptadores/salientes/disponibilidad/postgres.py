"""
postgres.py — Cuándo se avisa de que PostgreSQL no responde (`EQ-024`, `D2-B`)
===============================================================================

`EQ-024`, punto 13 del contrato humano: *«A los dos minutos se avisa al equipo y
se notifica también la recuperación; Resend no decide la salud»*.

Las dos frases son el módulo entero. La primera es una **máquina de estados con
umbral**; la segunda es una frontera: el estado sale del sondeo a la base y de
ningún otro sitio, así que un canal de correo caído deja alertas sin enviar pero
no cambia lo que el sistema cree de sí mismo.

Por qué un umbral y no un aviso por fallo
--------------------------------------------------
Porque un fallo aislado no es una caída. Un reinicio del contenedor, un `docker
compose up` o una reconexión de red producen uno o dos sondeos fallidos y se
resuelven solos; avisar de cada uno llenaría el buzón de operación de ruido
hasta que nadie lo mire —y el día de la caída de verdad, el correo llegaría a
una bandeja que ya se ignora—. Los dos minutos son el plazo que el equipo fijó.

Los cuatro estados posibles, y ninguno se confunde
--------------------------------------------------------------
| situación | `estado` | alerta |
|---|---|---|
| todavía no se ha sondeado | `desconocido` | ninguna |
| el último sondeo respondió | `saludable` | ninguna |
| falla, y lleva menos del umbral | `indisponible` | **ninguna todavía** |
| falla, y alcanzó el umbral | `indisponible` | una, y sólo una |

`desconocido` existe y no se colapsa con `indisponible`: al arrancar no se sabe
nada, y publicar «indisponible» antes del primer sondeo sería afirmar una avería
que nadie ha observado.

La recuperación es condicional, y ahí está el error fácil
--------------------------------------------------------------------
Sólo se avisa de que la base volvió **si esa misma caída llegó a alertarse**. Sin
esa condición, un fallo transitorio de treinta segundos —que nadie llegó a
saber— produciría un correo diciendo «PostgreSQL se recuperó» sobre una caída
que el equipo nunca vio: un aviso de algo que, para quien lo lee, no ocurrió.

Cada caída estrena identificador
-----------------------------------------
Y con él, sus dos claves de idempotencia. Si el identificador se reutilizara,
Resend descartaría la alerta de la segunda caída del día como duplicado de la
primera durante 24 horas y nadie se enteraría. El identificador es **opaco**: no
lleva anfitrión, usuario, base ni cadena de conexión, y no identifica a ninguna
persona.

Por qué `observar()` es síncrono y `vigilar()` es la única parte `async`
---------------------------------------------------------------------------
Porque el sondeo bloquea —`psycopg.connect` con el plazo de `T-01`— y el envío
del aviso también. Los dos juntos, en el bucle de eventos, congelarían todas las
peticiones de todos los usuarios, incluida `/api/salud`, que es justo la que
alguien miraría para saber qué está pasando; es el mismo defecto que
`conexion.py` dejó documentado. `vigilar()` los manda enteros a un hilo con
`asyncio.to_thread` y no hace nada más.

El reparto tiene además una consecuencia buena para las pruebas: la máquina de
estados se comprueba llamando a `observar()` con reloj y sondeo inyectados, sin
un solo `sleep` real y sin `asyncio`.


"""

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

#: `EQ-024` · «cuando el fallo persiste más de dos minutos».
UMBRAL_DE_ALERTA_S = 120

#: Cada cuánto se pregunta. Cuatro sondeos caben en el umbral, de modo que la
#: alerta llega con el retraso de un sondeo como mucho.
INTERVALO_DE_SONDEO_S = 30

#: Las dos claves de idempotencia. `<hecho>/<incidente>` como el resto de `D2`:
#: estables mientras dure el incidente y distintas en el siguiente.
CLAVE_CAIDA = "postgres-indisponible/{incidente}"
CLAVE_RECUPERACION = "postgres-recuperado/{incidente}"

#: Los textos del aviso operativo. Sin cadena de conexión, sin anfitrión, sin
#: usuario de base y sin nombres: quien los reciba entra a la aplicación.
_ASUNTO_CAIDA = "DidaxIa · la base de datos no responde"
_ASUNTO_RECUPERACION = "DidaxIa · la base de datos volvió a responder"


class EstadoDisponibilidad(StrEnum):
    """Lo que se sabe de la base, que no es lo mismo que lo que ocurre."""

    DESCONOCIDO = "desconocido"
    SALUDABLE = "saludable"
    INDISPONIBLE = "indisponible"


def sondear_postgres(cadena: str) -> bool:
    """`SELECT 1` contra la base. `True` si respondió.

    Usa el `conectar()` de siempre —con el plazo de `T-01`— en vez de abrir su
    propia conexión: dos formas de conectarse serían dos plazos distintos, y el
    día que alguien tocara uno el monitor mediría otra cosa que el resto del
    sistema (`adaptadores/salientes/conexion.py`).

    **Bloquea.** Quien la llame desde código `async` tiene que sacarla del bucle
    de eventos; `vigilar()` lo hace.

    Nunca levanta: cualquier fallo —conexión, autenticación, esquema, plazo
    agotado— significa lo mismo para este módulo, que es «no respondió». El
    detalle no se registra: una excepción de `psycopg` trae la cadena de
    conexión dentro.
    """
    from adaptadores.salientes.conexion import conectar  # noqa: PLC0415

    try:
        with conectar(cadena) as cnx, cnx.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone() is not None
    except Exception:  # noqa: BLE001 — el motivo no se publica; ver el docstring
        return False


def _identificador_de_incidente() -> str:
    """Un identificador opaco, corto y no personal.

    Dieciséis caracteres hexadecimales: suficiente para que dos incidentes no
    coincidan y muy por debajo de los 256 que admite `Idempotency-Key`.
    """
    return secrets.token_hex(8)


class MonitorDeDisponibilidad:
    """La máquina de estados de `EQ-024`, sin red y sin reloj propio.

    Todo lo que varía entra por el constructor —el sondeo, el reloj, el
    notificador, el generador de identificadores— para que las transiciones se
    puedan comprobar exactamente, incluido el instante justo del umbral, sin
    esperar dos minutos reales.
    """

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
        #: Cuándo se observó el **primer** fallo de la caída en curso, o `None`.
        self.incidente_desde: datetime | None = None
        self.incidente: str = ""
        #: Si ya se intentó la alerta de esta caída. **Intentado, no enviado**:
        #: ver `_alertar()` sobre por qué un envío fallido no se reintenta.
        self.aviso_intentado = False

    def observar(self) -> None:
        """Un sondeo y las transiciones que provoque. Bloquea; no levanta.

        Es el método entero del monitor: `vigilar()` no hace más que llamarlo en
        bucle. Que el sondeo y el aviso ocurran aquí —y no repartidos— es lo que
        permite comprobar «falla, pasan dos minutos, sale una alerta» como una
        secuencia de llamadas y no como una espera.
        """
        try:
            respondio = self._sondear()
        except Exception:  # noqa: BLE001
            # `sondear_postgres()` ya devuelve `False`, pero un sondeo inyectado
            # podría levantar. Un monitor que se muriera por eso dejaría de
            # observar justo cuando algo va mal.
            respondio = False
        self.ultimo_sondeo = self._reloj()

        if respondio:
            self._recuperar()
            return
        self._fallar()

    def _fallar(self) -> None:
        ahora = self.ultimo_sondeo
        if self.incidente_desde is None:
            # `EQ-024` · el incidente empieza en el **primer fallo observado**,
            # no cuando se alerta. Si empezara al alertar, el umbral se contaría
            # desde el aviso y nunca se cumpliría.
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
            # Un fallo transitorio que nunca se alertó no produce «se recuperó»:
            # sería un correo sobre una caída que, para quien lo lee, no ocurrió.
            return
        self._enviar(
            _ASUNTO_RECUPERACION,
            CLAVE_RECUPERACION.format(incidente=incidente),
            "La base de datos volvió a responder y el servicio quedó restablecido.\n\n"
            f"Incidente {incidente}. El estado actual está en /api/salud.",
        )

    def _alertar(self, asunto: str, plantilla: str, cuerpo: str) -> None:
        # ⚠️ Se marca **antes** de enviar, y por eso el campo se llama
        # «intentado». Marcarlo después dejaría que un canal caído produjera un
        # intento por sondeo —uno cada treinta segundos mientras dure la
        # caída—, que es la tormenta de reintentos que `EQ-024` no quiere: el
        # correo informa, y no vale la pena insistir a costa de inundar.
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
        """Intenta el aviso. Su resultado **no toca el estado** (`EQ-024`).

        Sin destino no se intenta: `CORREO_PRIVACIDAD` es el canal operativo
        aprobado y no hay ninguno fijado en el código —`ESTADO-ACTUAL.md` §10.9
        deja su ratificación pendiente, y escribir aquí una dirección la
        convertiría en una decisión del ejecutor—.
        """
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
        except Exception:  # noqa: BLE001
            # El puerto promete no levantar y sus dos adaptadores lo cumplen.
            # Esto cubre al tercero que alguien componga: que el canal reviente
            # no puede matar la tarea que vigila la base.
            _LOG.exception("el canal de avisos falló al enviar %s", clave)
            return
        _LOG.info("alerta de disponibilidad %s enviada=%s", clave, salio)

    def como_json(self) -> dict:
        """Lo que `GET /api/salud` publica de la disponibilidad.

        Cinco campos y ninguno es un valor sensible: no hay cadena de conexión,
        ni anfitrión, ni usuario, ni destino del aviso, ni el texto de ninguna
        excepción. El identificador de incidente sí sale, porque es opaco y es lo
        que permite cruzar la salud con el correo que llegó.
        """
        return {
            "configurado": True,
            "estado": self.estado.value,
            "ultimo_sondeo": self.ultimo_sondeo.isoformat() if self.ultimo_sondeo else None,
            "incidente_desde": (
                self.incidente_desde.isoformat() if self.incidente_desde else None
            ),
            "aviso_intentado": self.aviso_intentado,
        }


#: Lo que `GET /api/salud` publica cuando no hay monitor. Sin `AGENTE_BD` no hay
#: nada que sondear, y decir `estado: "indisponible"` sería afirmar una avería
#: que nadie observó: lo cierto es que no se está mirando.
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
    """Sondea cada `intervalo_s` hasta que cancelen la tarea.

    `observar()` va a un hilo porque bloquea —conexión y, cuando toca, envío—;
    ver el docstring del módulo. `dormir` se inyecta para que la prueba del bucle
    no espere de verdad.

    La cancelación se propaga: `CancelledError` sale de aquí sin capturarse, que
    es lo que permite a `aplicacion.py` esperar a que la tarea termine al apagar
    en vez de dejarla huérfana.
    """
    while True:
        await asyncio.to_thread(monitor.observar)
        await dormir(intervalo_s)


@contextlib.asynccontextmanager
async def vigilancia(monitor: MonitorDeDisponibilidad | None, **opciones):
    """El ciclo de vida de la tarea, para el `lifespan` de FastAPI.

    Con `monitor=None` —sin `AGENTE_BD`— **no crea ninguna tarea**: no hay nada
    que sondear, y una tarea que comprobara una cadena vacía cada treinta
    segundos sería trabajo para producir siempre el mismo fallo.

    Al salir cancela y **espera**. Sin el `await`, apagar dejaría la tarea a
    medio cancelar y el proceso terminaría con un aviso de tarea pendiente —o,
    peor, con una conexión abierta en un hilo—.
    """
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
