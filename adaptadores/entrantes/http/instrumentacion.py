from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from dominio.modelo.contexto_de_uso import ContextoDeUso
from dominio.modelo.telemetria import EventoInvalido, EventoTelemetria, TipoDeEvento
from dominio.puertos.almacen import ErrorDeAlmacen

if TYPE_CHECKING:
    from dominio.puertos.telemetria import PuertoTelemetria

def _clave(tipo: TipoDeEvento, *partes: str) -> str:
    resumen = hashlib.sha256("\x1f".join(partes).encode("utf-8")).hexdigest()[:32]
    return f"{tipo.value.replace('.', '-')}:{resumen}"

@dataclass(frozen=True, slots=True)
class SelloDelTurno:

    sujeto: str
    conversacion: str
    turno: str
    contexto_de_uso: ContextoDeUso = ContextoDeUso.APRENDIZAJE_ESTUDIANTE
    clase: str | None = None

@dataclass(frozen=True, slots=True)
class ResultadoDelTurno:

    nivel: str = ""
    procedencia: str = ""
    degradado: bool = False
    version_modelo: str = ""
    version_corpus: str = ""

class Instrumentador:

    def __init__(
        self,
        telemetria: PuertoTelemetria | None = None,
        version_del_corpus: object | None = None,
    ) -> None:
        self._telemetria = telemetria
        self._version_del_corpus = version_del_corpus

    def anotar(self, evento: EventoTelemetria) -> bool:
        if self._telemetria is None:
            return False
        try:
            return self._telemetria.registrar(evento)
        except (ErrorDeAlmacen, EventoInvalido, OSError):
            return False

    def version_del_corpus(self) -> str:
        if self._version_del_corpus is None:
            return ""
        try:
            return str(self._version_del_corpus.actual() or "")
        except (ErrorDeAlmacen, OSError):
            return ""

    def turno_enviado(
        self, sello: SelloDelTurno, notacion: str = "", ocurrido_en: datetime | None = None
    ) -> bool:

        metadatos = {"notacion": notacion} if notacion in ("sen", "sin") else {}
        return self._anotar_del_turno(
            TipoDeEvento.TURNO_ENVIADO, sello, metadatos, ocurrido_en=ocurrido_en
        )

    def turno_respondido(self, sello: SelloDelTurno, resultado: ResultadoDelTurno) -> bool:
        metadatos = {
            "nivel": resultado.nivel,
            "procedencia": resultado.procedencia,
            "degradado": resultado.degradado,
        }

        if metadatos["nivel"] not in ("sondeo", "regla", "desarrollo"):
            metadatos.pop("nivel")
        if metadatos["procedencia"] not in ("corpus", "sin-fuente", "mixta", ""):
            metadatos.pop("procedencia")
        return self._anotar_del_turno(
            TipoDeEvento.TURNO_RESPONDIDO,
            sello,
            metadatos,
            versiones=(resultado.version_modelo, resultado.version_corpus),
        )

    def supervision_derivada(
        self, sello: SelloDelTurno, item: str, tipo_de_item: str, urgencia: str = ""
    ) -> bool:
        metadatos: dict = {"tipo_de_item": tipo_de_item}
        if urgencia:
            metadatos["urgencia"] = urgencia
        return self._anotar(
            TipoDeEvento.SUPERVISION_DERIVADA,
            _clave(TipoDeEvento.SUPERVISION_DERIVADA, item),
            sello=sello,
            metadatos=metadatos,
        )

    def supervision_decidida(
        self, sello: SelloDelTurno, item: str, decision: str
    ) -> bool:

        return self._anotar(
            TipoDeEvento.SUPERVISION_DECIDIDA,
            _clave(TipoDeEvento.SUPERVISION_DECIDIDA, item),
            sello=sello,
            metadatos={"decision": decision, "item": item},
        )

    def curricular_actualizado(
        self, sujeto: str, clase: str, notacion: str, tiene_unidad: bool
    ) -> bool:

        ahora = datetime.now(UTC)
        evento = self._construir(
            TipoDeEvento.CURRICULAR_ACTUALIZADO,
            _clave(TipoDeEvento.CURRICULAR_ACTUALIZADO, clase, ahora.isoformat()),
            identificador_sujeto=sujeto,
            ocurrido_en=ahora,
            clase=clase,
            contexto_de_uso=ContextoDeUso.CONSULTA_PROFESIONAL,
            metadatos={"notacion": notacion, "tiene_unidad": tiene_unidad},
        )
        return self.anotar(evento) if evento is not None else False

    def _anotar_del_turno(
        self,
        tipo: TipoDeEvento,
        sello: SelloDelTurno,
        metadatos: dict,
        ocurrido_en: datetime | None = None,
        versiones: tuple[str, str] = ("", ""),
    ) -> bool:
        return self._anotar(
            tipo,
            _clave(tipo, sello.turno),
            sello=sello,
            metadatos=metadatos,
            ocurrido_en=ocurrido_en,
            versiones=versiones,
        )

    def _anotar(
        self,
        tipo: TipoDeEvento,
        clave: str,
        *,
        sello: SelloDelTurno,
        metadatos: dict,
        ocurrido_en: datetime | None = None,
        versiones: tuple[str, str] = ("", ""),
    ) -> bool:

        version_modelo, version_corpus = versiones
        evento = self._construir(
            tipo,
            clave,
            identificador_sujeto=sello.sujeto,
            ocurrido_en=ocurrido_en or datetime.now(UTC),
            clase=sello.clase,
            metadatos=metadatos,
            conversacion=sello.conversacion,
            turno=sello.turno,
            contexto_de_uso=sello.contexto_de_uso,
            version_modelo=version_modelo,
            version_corpus=version_corpus,
        )
        return self.anotar(evento) if evento is not None else False

    @staticmethod
    def _construir(
        tipo: TipoDeEvento, clave: str, **campos: object
    ) -> EventoTelemetria | None:

        try:
            return EventoTelemetria(clave_idempotencia=clave, tipo=tipo, **campos)
        except (EventoInvalido, TypeError):

            return None

SIN_INSTRUMENTAR = Instrumentador()
