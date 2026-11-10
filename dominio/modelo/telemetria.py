from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Final

from dominio.modelo.contexto_de_uso import ContextoDeUso


class EventoInvalido(ValueError):
    pass

class ConflictoDeIdempotencia(EventoInvalido):
    pass

class OrigenDeEvento(StrEnum):

    BACKEND = "backend"
    INTERFAZ = "interfaz"

class TipoDeEvento(StrEnum):

    TURNO_ENVIADO = "turno.enviado"

    TURNO_RESPONDIDO = "turno.respondido"

    SUPERVISION_DERIVADA = "supervision.derivada"

    SUPERVISION_DECIDIDA = "supervision.decidida"

    CURRICULAR_ACTUALIZADO = "curricular.actualizado"

    FUENTES_ABIERTAS = "fuentes.abiertas"
    RESPUESTA_COPIADA = "respuesta.copiada"
    GRAFICA_GENERADA = "grafica.generada"
    GRAFICA_ABIERTA = "grafica.abierta"
    GRAFICA_INTERACCION = "grafica.interaccion"
    GRAFICA_RANGO_CAMBIADO = "grafica.rango_cambiado"
    GRAFICA_EXPORTADA = "grafica.exportada"
    SUPERVISION_ABIERTA = "supervision.abierta"
    INFORME_GENERADO = "informe.generado"
    INFORME_DESCARGADO = "informe.descargado"

    AUTOCORRECCION_DETECTADA = "autocorreccion.detectada"

    AUTOCORRECCION_CONFIRMADA = "autocorreccion.confirmada"

ORIGEN_DE: Final[dict[TipoDeEvento, OrigenDeEvento]] = {
    TipoDeEvento.TURNO_ENVIADO: OrigenDeEvento.BACKEND,
    TipoDeEvento.TURNO_RESPONDIDO: OrigenDeEvento.BACKEND,
    TipoDeEvento.SUPERVISION_DERIVADA: OrigenDeEvento.BACKEND,
    TipoDeEvento.SUPERVISION_DECIDIDA: OrigenDeEvento.BACKEND,
    TipoDeEvento.CURRICULAR_ACTUALIZADO: OrigenDeEvento.BACKEND,
    TipoDeEvento.FUENTES_ABIERTAS: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.RESPUESTA_COPIADA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.GRAFICA_GENERADA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.GRAFICA_ABIERTA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.GRAFICA_INTERACCION: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.GRAFICA_RANGO_CAMBIADO: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.GRAFICA_EXPORTADA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.SUPERVISION_ABIERTA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.INFORME_GENERADO: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.INFORME_DESCARGADO: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.AUTOCORRECCION_DETECTADA: OrigenDeEvento.INTERFAZ,
    TipoDeEvento.AUTOCORRECCION_CONFIRMADA: OrigenDeEvento.INTERFAZ,
}


TIPOS_DE_INTERFAZ: Final[frozenset[TipoDeEvento]] = frozenset(
    tipo for tipo, origen in ORIGEN_DE.items() if origen is OrigenDeEvento.INTERFAZ
)


METADATOS_ADMITIDOS: Final[dict[TipoDeEvento, dict[str, frozenset[str] | None]]] = {
    TipoDeEvento.TURNO_ENVIADO: {"notacion": frozenset({"sen", "sin"})},
    TipoDeEvento.TURNO_RESPONDIDO: {
        "nivel": frozenset({"sondeo", "regla", "desarrollo"}),
        "procedencia": frozenset({"corpus", "sin-fuente", "mixta", ""}),
        "degradado": None,
    },
    TipoDeEvento.SUPERVISION_DERIVADA: {
        "tipo_de_item": frozenset({"respuesta", "sin-fuente", "degradado"}),
        "urgencia": None,
    },
    TipoDeEvento.SUPERVISION_DECIDIDA: {
        "decision": frozenset({"aprobado", "editado", "rechazado"}),
        "item": None,
    },
    TipoDeEvento.CURRICULAR_ACTUALIZADO: {
        "notacion": frozenset({"sen", "sin"}),
        "tiene_unidad": None,
    },
    TipoDeEvento.FUENTES_ABIERTAS: {"materiales": None},
    TipoDeEvento.RESPUESTA_COPIADA: {"alcance": frozenset({"bloque", "respuesta"})},
    TipoDeEvento.GRAFICA_GENERADA: {"grafica": None},
    TipoDeEvento.GRAFICA_ABIERTA: {"grafica": None, "vista": frozenset({"normal", "ampliada"})},
    TipoDeEvento.GRAFICA_INTERACCION: {
        "grafica": None,
        "gesto": frozenset({"desplazar", "acercar", "alejar", "puntero"}),
    },
    TipoDeEvento.GRAFICA_RANGO_CAMBIADO: {
        "grafica": None,
        "eje": frozenset({"x", "y", "ambos"}),
    },
    TipoDeEvento.GRAFICA_EXPORTADA: {
        "grafica": None,

        "formato": frozenset({"png", "jpg", "svg", "html", "pdf"}),
        "tema": frozenset({"claro", "oscuro"}),
    },
    TipoDeEvento.SUPERVISION_ABIERTA: {"item": None},
    TipoDeEvento.INFORME_GENERADO: {
        "informe": frozenset({"indicador", "completo"}),
        "codigo": None,
    },
    TipoDeEvento.INFORME_DESCARGADO: {
        "informe": frozenset({"indicador", "completo"}),
        "formato": frozenset({"pdf"}),
    },
    TipoDeEvento.AUTOCORRECCION_DETECTADA: {},
    TipoDeEvento.AUTOCORRECCION_CONFIRMADA: {},
}


TOPE_IDENTIFICADOR: Final = 128


TOPE_METADATO: Final = 64


TOPE_METADATOS = 8


PATRON_CLAVE = re.compile(r"^[A-Za-z0-9:._~-]{8,160}$")


PATRON_REFERENCIA = re.compile(r"^[A-Za-z0-9:._~-]{1,128}$")


def _exigir_referencia(valor: str | None, campo: str) -> str | None:
    if valor is None:
        return None
    limpio = valor.strip()
    if not limpio:
        return None
    if not PATRON_REFERENCIA.fullmatch(limpio):
        raise EventoInvalido(f"{campo} no tiene la forma de un identificador")
    return limpio

def _exigir_metadato(tipo: TipoDeEvento, clave: str, valor: object) -> None:
    admitidos = METADATOS_ADMITIDOS.get(tipo, {})
    if clave not in admitidos:
        raise EventoInvalido(
            f"«{clave}» no es un metadato de «{tipo.value}»: el esquema no "
            f"admite metadatos arbitrarios"
        )
    cerrados = admitidos[clave]
    if cerrados is not None:
        if not isinstance(valor, str) or valor not in cerrados:
            raise EventoInvalido(f"«{valor}» no es un valor admitido de «{clave}»")
        return
    if isinstance(valor, float) and not math.isfinite(valor):
        raise EventoInvalido(f"«{clave}» tiene que ser un número finito")
    if isinstance(valor, bool | int | float):
        return
    if not isinstance(valor, str):
        raise EventoInvalido(f"«{clave}» tiene que ser un escalar, no {type(valor).__name__}")
    if len(valor) > TOPE_METADATO or "@" in valor:
        raise EventoInvalido(
            f"«{clave}» excede lo que un metadato puede llevar: la telemetría "
            f"no transporta texto libre ni datos de contacto"
        )

@dataclass(frozen=True, slots=True)
class EventoTelemetria:

    clave_idempotencia: str
    tipo: TipoDeEvento
    ocurrido_en: datetime
    identificador_sujeto: str
    contexto_de_uso: ContextoDeUso = ContextoDeUso.APRENDIZAJE_ESTUDIANTE
    clase: str | None = None
    conversacion: str | None = None
    turno: str | None = None
    concepto: str | None = None
    version_corpus: str = ""
    version_modelo: str = ""
    metadatos: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not PATRON_CLAVE.fullmatch(self.clave_idempotencia or ""):
            raise EventoInvalido(
                "la clave de idempotencia tiene que ser opaca, imprimible y de "
                "entre 8 y 160 caracteres"
            )
        if self.ocurrido_en.tzinfo is None:
            raise EventoInvalido("un evento sin zona horaria no es un instante inequívoco")
        sujeto = (self.identificador_sujeto or "").strip()
        if not sujeto or len(sujeto) > TOPE_IDENTIFICADOR:
            raise EventoInvalido("el evento no declara un sujeto utilizable")
        object.__setattr__(self, "identificador_sujeto", sujeto)
        for campo in ("clase", "conversacion", "turno", "concepto"):
            object.__setattr__(self, campo, _exigir_referencia(getattr(self, campo), campo))
        for campo in ("version_corpus", "version_modelo"):
            valor = (getattr(self, campo) or "").strip()
            if len(valor) > TOPE_METADATO:
                raise EventoInvalido(f"{campo} excede {TOPE_METADATO} caracteres")
            object.__setattr__(self, campo, valor)
        if len(self.metadatos) > TOPE_METADATOS:
            raise EventoInvalido(f"un evento no lleva más de {TOPE_METADATOS} metadatos")
        for clave, valor in self.metadatos.items():
            _exigir_metadato(self.tipo, clave, valor)

    @property
    def origen(self) -> OrigenDeEvento:
        return ORIGEN_DE[self.tipo]

    @property
    def alimenta_kpi(self) -> bool:
        return self.contexto_de_uso is ContextoDeUso.APRENDIZAJE_ESTUDIANTE

def exigir_tipo_de_interfaz(nombre: str) -> TipoDeEvento:
    try:
        tipo = TipoDeEvento(nombre)
    except ValueError:
        raise EventoInvalido(f"«{nombre}» no es un evento del vocabulario") from None
    if tipo not in TIPOS_DE_INTERFAZ:
        raise EventoInvalido(
            f"«{nombre}» lo declara el servidor desde su punto canónico y no "
            f"se acepta desde la interfaz"
        )
    return tipo
