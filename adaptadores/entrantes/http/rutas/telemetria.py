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

if TYPE_CHECKING:
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from adaptadores.entrantes.http.sesiones import Sesiones
    from dominio.puertos.telemetria import PuertoTelemetria

VENTANA_HACIA_ATRAS = timedelta(days=1)


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
    if tipo in SOLO_ESTUDIANTE:
        return rol == "estudiante"
    if tipo in SOLO_DOCENCIA_O_INVESTIGACION:
        return rol in {"docente", "investigador"}
    if tipo in SOLO_INVESTIGACION:
        return rol == "investigador"
    return rol in {"estudiante", "docente", "investigador"}

def _instante(valor: object, ahora: datetime) -> datetime:
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
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        sujeto = sujeto_de(datos)

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

            return JSONResponse({"detalle": str(error)}, status_code=400)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("la telemetría no está disponible en este momento")

        return JSONResponse(
            {"registrado": True, "nuevo": creado, "tipo": tipo.value},
            status_code=201 if creado else 200,
        )

    return router
