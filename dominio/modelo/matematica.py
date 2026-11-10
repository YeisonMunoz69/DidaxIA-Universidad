from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Veredicto(str, Enum):

    VALIDA = "valida"
    INVALIDA = "invalida"
    NO_VERIFICABLE = "no_verificable"

@dataclass(frozen=True)
class BloqueVerificable:

    identificador: str
    izquierda: str
    derecha: str
    relacion: str = "="
    regla_declarada: str | None = None

@dataclass(frozen=True)
class Verificacion:

    bloque: str
    veredicto: Veredicto
    herramienta: str
    latencia_ms: float
    detalle: str = ""

    @property
    def aprobada(self) -> bool:
        return self.veredicto is Veredicto.VALIDA

@dataclass(frozen=True)
class InformeVerificacion:

    verificaciones: tuple[Verificacion, ...] = ()
    matematica_fuera_de_bloque: bool = False

    @property
    def aprobada(self) -> bool:
        if self.matematica_fuera_de_bloque:
            return False
        if not self.verificaciones:
            return False
        return all(v.aprobada for v in self.verificaciones)

    @property
    def nada_que_verificar(self) -> bool:
        return not self.verificaciones and not self.matematica_fuera_de_bloque

    @property
    def motivo_de_rechazo(self) -> str:
        if self.matematica_fuera_de_bloque:
            return "hay expresiones matemáticas fuera de bloque declarado"
        if not self.verificaciones:
            return "no se declaró ninguna afirmación verificable"
        fallidas = [v for v in self.verificaciones if not v.aprobada]
        if fallidas:
            return "afirmaciones no válidas: " + ", ".join(v.bloque for v in fallidas)
        return ""

@dataclass(frozen=True)
class PasoDerivacion:

    tipo: str
    latex: str
    regla: str

@dataclass(frozen=True)
class Precomputo:

    resultado: str = ""

    resultado_corriente: str = ""

    simplificacion_corriente: str = ""

    limites_intermedios: tuple[str, ...] = ()

    paso_intermedio_corriente: str = ""
    paso_intermedio_regla: str = ""

    componentes_derivada: tuple[tuple[str, str, str], ...] = ()
    sin_limite_bilateral: bool = False
    limite_izquierdo_corriente: str = ""
    limite_derecho_corriente: str = ""
    pasos: tuple[PasoDerivacion, ...] = ()
    regla_critica: str = ""
    concepciones_candidatas: tuple[str, ...] = ()
    error: str | None = None

    expresion_fuente: str = ""

    funcion_js: str = ""

    derivada_js: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None

    def truncado(self) -> Precomputo:
        return Precomputo(
            regla_critica=self.regla_critica,
            concepciones_candidatas=self.concepciones_candidatas,
        )
