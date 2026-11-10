"""
telemetria.py — La API autenticada de eventos de interfaz
==========================================================

`POST /api/telemetria/eventos`. Los hechos de interacción ocurren en el navegador y el
servidor no puede verlos: abrir el panel de fuentes, copiar una respuesta,
generar o exportar una gráfica, abrir un elemento de supervisión, generar o
descargar un informe. Esta ruta es su contrato.

El emisor vive en `frontend/src/nucleo/api/telemetria.js` y conserva en memoria
la clave de idempotencia mientras reintenta. Las piezas de turno, gráfica y
supervisión sólo mandan referencias y metadatos cerrados; nunca duplican el
texto de la conversación ni guardan una bitácora en `localStorage`.

Qué pone el cliente y qué pone el servidor
---------------------------------------------------
El cliente pone **el hecho**: tipo, clave de idempotencia, referencias y
metadatos. El servidor pone **quién y en qué contexto**: el sujeto sale de la
sesión autenticada y el contexto de uso, del rol real. Ninguno de los dos llega
por el cuerpo, y no es una comodidad: si el cliente pudiera declarar el sujeto,
cualquier sesión podría escribir actividad a nombre de otra persona; si pudiera
declarar el contexto, un profesional podría marcar su uso como aprendizaje y
`EQ-031` quedaría sin efecto justo donde importa.

Tampoco puede declarar un evento del backend. `exigir_tipo_de_interfaz()` lo
rechaza: sin esa barrera, un cliente podría escribir `turno.respondido` con la
versión de modelo que quisiera y envenenar dos indicadores institucionales.

Por qué el instante del cliente se acota en vez de creerse o descartarse
--------------------------------------------------------------------------------
El reloj del navegador puede ir mal. Creerlo dejaría entrar eventos fechados en
2019 o en el futuro, y una serie temporal con eso dentro no se puede leer.
Descartarlo del todo haría que `ocurrido_en` y `registrado_en` coincidieran
siempre, y entonces el retraso de telemetría —que la superficie de calidad de
datos necesita— sería inobservable por construcción.

Se acepta si cae en una ventana razonable y, si no, se usa la hora del
servidor. Nunca se rechaza el evento por eso: perder la observación sería peor
que fecharla con un instante que sí es correcto.


"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import (
    json_del_cuerpo,
    mantenimiento,
    requerir_sesion,
)
from adaptadores.entrantes.http.sesiones import sujeto_de
from dominio.modelo.contexto_de_uso import contexto_de_uso_de
from dominio.modelo.telemetria import (
    ConflictoDeIdempotencia,
    EventoInvalido,
    EventoTelemetria,
    TipoDeEvento,
    exigir_tipo_de_interfaz,
)
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    EscrituraRechazada,
)

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from adaptadores.entrantes.http.sesiones import Sesiones
    from dominio.puertos.telemetria import PuertoTelemetria

#: Cuánto hacia atrás se admite el reloj del cliente. Un día cubre de sobra una
#: pestaña abierta desde ayer y una zona horaria mal configurada; más allá, la
#: fecha ya no describe el hecho.
VENTANA_HACIA_ATRAS = timedelta(days=1)

#: Y cuánto hacia delante. Cinco minutos absorben un reloj adelantado sin
#: admitir eventos del futuro, que romperían cualquier consulta por periodo.
VENTANA_HACIA_DELANTE = timedelta(minutes=5)

SOLO_ESTUDIANTE = frozenset(
    {
        TipoDeEvento.AUTOCORRECCION_DETECTADA,
        TipoDeEvento.AUTOCORRECCION_CONFIRMADA,
    }
)
SOLO_DOCENCIA_O_INVESTIGACION = frozenset({TipoDeEvento.SUPERVISION_ABIERTA})
SOLO_INVESTIGACION = frozenset(
    {TipoDeEvento.INFORME_GENERADO, TipoDeEvento.INFORME_DESCARGADO}
)


def _tipo_admitido_para_rol(tipo: TipoDeEvento, rol: str) -> bool:
    """Impide que una sesión fabrique hechos de una superficie que no posee."""
    if tipo in SOLO_ESTUDIANTE:
        return rol == "estudiante"
    if tipo in SOLO_DOCENCIA_O_INVESTIGACION:
        return rol in {"docente", "investigador"}
    if tipo in SOLO_INVESTIGACION:
        return rol == "investigador"
    return rol in {"estudiante", "docente", "investigador"}


def _instante(valor: object, ahora: datetime) -> datetime:
    """El instante del cliente si es creíble; la hora del servidor si no."""
    if not isinstance(valor, str) or not valor.strip():
        return ahora
    try:
        propuesto = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return ahora
    if propuesto.tzinfo is None:
        return ahora
    if not (ahora - VENTANA_HACIA_ATRAS <= propuesto <= ahora + VENTANA_HACIA_DELANTE):
        return ahora
    return propuesto


def _referencia(cuerpo: dict, clave: str) -> str | None:
    valor = cuerpo.get(clave)
    return valor.strip() if isinstance(valor, str) and valor.strip() else None


def crear_router(
    sesiones: Sesiones,
    telemetria: PuertoTelemetria,
    puerta: PuertaDeSupresion,
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/telemetria/eventos")
    async def registrar_evento(peticion: Request) -> Response:
        """Un hecho de interfaz. `201` si es nuevo, `200` si ya estaba.

        Los dos son éxito, y distinguirlos importa: un cliente que reintenta
        necesita saber que su evento ya cuenta, y una prueba de idempotencia
        necesita poder afirmar que la segunda llamada no creó nada.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        sujeto = sujeto_de(datos)
        # `EQ-022` · quien tiene su propio trámite de supresión abierto no usa
        # el producto, y medir su uso sería seguir tratándolo.
        congelada = puerta.negativa(sujeto)
        if congelada is not None:
            return congelada

        cuerpo = await json_del_cuerpo(peticion)
        ahora = datetime.now(UTC)
        try:
            tipo = exigir_tipo_de_interfaz(str(cuerpo.get("tipo") or ""))
            rol = str(datos.get("rol") or "")
            if not _tipo_admitido_para_rol(tipo, rol):
                return JSONResponse(
                    {"detalle": "el rol de la sesión no puede declarar ese evento"},
                    status_code=403,
                )
            metadatos = cuerpo.get("metadatos") or {}
            if not isinstance(metadatos, dict):
                raise EventoInvalido("«metadatos» tiene que ser un objeto")
            evento = EventoTelemetria(
                clave_idempotencia=str(cuerpo.get("clave_idempotencia") or ""),
                tipo=tipo,
                ocurrido_en=_instante(cuerpo.get("ocurrido_en"), ahora),
                # Del servidor, nunca del cuerpo. Ver la cabecera.
                identificador_sujeto=sujeto,
                contexto_de_uso=contexto_de_uso_de(datos.get("rol")),
                clase=_referencia(cuerpo, "clase"),
                conversacion=_referencia(cuerpo, "conversacion"),
                turno=_referencia(cuerpo, "turno"),
                concepto=_referencia(cuerpo, "concepto"),
                metadatos=metadatos,
            )
        except EventoInvalido as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)

        try:
            creado = (
                telemetria.registrar(evento, alcance_institucional=True)
                if rol == "investigador"
                else telemetria.registrar(evento)
            )
        except ConflictoDeIdempotencia as error:
            return JSONResponse({"detalle": str(error)}, status_code=409)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except EventoInvalido as error:
            # La comprobación de referencias del adaptador: la clase no existe o
            # no es de quien escribe. Es un 400 y no un 403 a propósito — decir
            # «no tienes permiso» confirmaría que ese identificador de clase es
            # real.
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("la telemetría no está disponible en este momento")

        return JSONResponse(
            {"registrado": True, "nuevo": creado, "tipo": tipo.value},
            status_code=201 if creado else 200,
        )

    return router
