from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from dominio.modelo.contexto_de_uso import ContextoDeUso


SUBCOMPONENTES_AFECTIVOS = (
    "PS-Anx", "FAH", "autoeficacia",
    "E-Anx", "aburrimiento", "autoconcepto",
    "utilidad_percibida", "identidad_matematica_negativa",
)


ESTADOS_CONCEPTUALES = ("no_detectada", "activa", "remediada", "recurrente")


ALCANCES = ("estado", "rasgo")


@dataclass(frozen=True)
class BloqueRegistrado:

    tipo: str
    contenido: str
    sello: str
    alternativo: str = ""

    SELLOS = ("verificado", "generado")

    EXIGEN_ALTERNATIVO = ("notacion", "grafica")

    def validar(self) -> list[str]:
        fallos = []
        if self.sello not in self.SELLOS:
            fallos.append(f"sello inválido «{self.sello}»: §5.1 admite solo dos")
        if not self.contenido.strip():
            fallos.append("bloque sin contenido")
        if self.tipo in self.EXIGEN_ALTERNATIVO and not self.alternativo.strip():
            fallos.append(f"«{self.tipo}» exige alternativo (§5, accesibilidad)")
        return fallos

@dataclass(frozen=True)
class CitaRegistrada:

    marca: str
    expresion: str

    def validar(self) -> list[str]:
        fallos = []
        if not self.marca.strip():
            fallos.append("cita sin marca: no hay dónde sustituirla")
        if not self.expresion.strip():
            fallos.append(f"cita «{self.marca}» sin expresión")
        return fallos

RELACIONES_DEL_MATERIAL = (
    "recuperado",
    "soporte_del_turno",
    "cita_literal",
    "respaldo_de_afirmacion",
)


RELACION_OBSERVABLE = "recuperado"


_FRAGMENTO = re.compile(r"^F-\d{3}$")
_OBRA = re.compile(r"^[A-Z]{3}$")
_CONCEPTO = re.compile(r"^[A-Za-z0-9:._~-]{1,128}$")


@dataclass(frozen=True)
class MaterialRegistrado:

    fragmento: str
    obra: str
    orden: int
    relacion: str = RELACION_OBSERVABLE

    similitud: float | None = None

    def validar(self) -> list[str]:
        fallos = []
        if not _FRAGMENTO.match(self.fragmento or ""):
            fallos.append(f"identificador de fragmento inválido «{self.fragmento}»")
        if not _OBRA.match(self.obra or ""):
            fallos.append(f"{self.fragmento}: clave de obra inválida «{self.obra}»")
        if self.orden < 0:
            fallos.append(f"{self.fragmento}: orden negativo ({self.orden})")
        if self.relacion not in RELACIONES_DEL_MATERIAL:
            fallos.append(
                f"{self.fragmento}: relación desconocida «{self.relacion}»: "
                f"{RELACIONES_DEL_MATERIAL}"
            )
        if self.similitud is not None and not 0.0 <= self.similitud <= 1.0:
            fallos.append(f"{self.fragmento}: similitud fuera de escala ({self.similitud})")
        return fallos

@dataclass(frozen=True)
class EntradaDeTurno:

    turno: str
    identificador_sesion: str

    identificador_sujeto: str

    momento: str
    autor: str
    contenido: str

    degradado: bool = False

    bloques: tuple[BloqueRegistrado, ...] = ()

    citas: tuple[CitaRegistrada, ...] = ()

    nivel: str = ""
    procedencia_origen: str = ""
    procedencia_referencia: str = ""

    material: tuple[MaterialRegistrado, ...] = ()

    conceptos: tuple[str, ...] = ()

    consentimiento_evento: int | None = None

    contexto_de_uso: str = ContextoDeUso.APRENDIZAJE_ESTUDIANTE

    AUTORES = ("estudiante", "sistema")

    MARCA = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")

    def validar(self) -> list[str]:
        fallos = []
        if self.autor not in self.AUTORES:
            fallos.append(f"autor desconocido «{self.autor}»: {self.AUTORES}")
        if not self.contenido.strip():
            fallos.append("contenido vacío: no hay nada que reconstruir")
        if not self.identificador_sujeto.strip():
            fallos.append("identificador_sujeto vacío: la fila no se podría suprimir (DD-27)")
        if self.consentimiento_evento is not None and self.consentimiento_evento <= 0:

            fallos.append("consentimiento_evento no es un identificador de evento válido")
        fallos.extend(self._fallos_del_momento())
        fallos.extend(self._fallos_de_las_marcas())
        for bloque in self.bloques:
            fallos.extend(bloque.validar())
        for cita in self.citas:
            fallos.extend(cita.validar())
        fallos.extend(self._fallos_del_material())
        fallos.extend(self._fallos_de_los_conceptos())
        if self.degradado and self.autor != "sistema":

            fallos.append(f"degradado con autor «{self.autor}»: solo el sistema se degrada")
        return fallos

    def _fallos_de_los_conceptos(self) -> list[str]:
        fallos = [
            f"identificador de concepto inválido «{concepto}»"
            for concepto in self.conceptos
            if not _CONCEPTO.fullmatch(concepto or "")
        ]
        repetidos = sorted({c for c in self.conceptos if self.conceptos.count(c) > 1})
        if repetidos:
            fallos.append("conceptos repetidos en el mismo mensaje: " + ", ".join(repetidos))
        if self.conceptos and self.autor != "sistema":
            fallos.append(
                f"conceptos colgados del autor «{self.autor}»: los expone el sistema"
            )
        return fallos

    def _fallos_del_material(self) -> list[str]:
        fallos: list[str] = []
        for pieza in self.material:
            fallos.extend(pieza.validar())

        ordenes = [p.orden for p in self.material]
        if len(set(ordenes)) != len(ordenes):
            fallos.append("dos piezas de material comparten posición: el orden sería indefinido")

        fragmentos = [p.fragmento for p in self.material]
        repetidos = sorted({f for f in fragmentos if fragmentos.count(f) > 1})
        if repetidos:

            fallos.append("material repetido en el mismo mensaje: " + ", ".join(repetidos))

        if self.material and self.autor != "sistema":

            fallos.append(
                f"material colgado del autor «{self.autor}»: lo recupera el sistema"
            )
        return fallos

    def _fallos_de_las_marcas(self) -> list[str]:
        marcas = set(self.MARCA.findall(self.contenido))
        for bloque in self.bloques:
            marcas |= set(self.MARCA.findall(bloque.contenido))
        sin_cita = sorted(marcas - {c.marca for c in self.citas})
        if sin_cita:
            return [
                f"marcas sin cita {sin_cita}: el hilo mostraría «{{{{{sin_cita[0]}}}}}» "
                "crudo, que es el fallo de PM-B25"
            ]
        return []

    def _fallos_del_momento(self) -> list[str]:
        if not self.momento.strip():
            return ["momento vacío: RF-REG-01 pide marca temporal"]
        try:
            marca = datetime.fromisoformat(self.momento)
        except ValueError:
            return [f"momento no es ISO-8601 legible: «{self.momento}»"]
        if marca.tzinfo is None:
            return [f"momento sin zona horaria: «{self.momento}» (RF-REG-01, C-01)"]
        return []

@dataclass(frozen=True)
class TrazaRegistrada:

    filtro: str
    latencia_ms: float
    ruta: str
    metadatos: dict

@dataclass(frozen=True)
class RegistroDeTurno:

    turno: str
    identificador_sesion: str

    identificador_sujeto: str
    nivel_divulgacion: int
    trazas: tuple[TrazaRegistrada, ...]

    contexto_de_uso: str = ContextoDeUso.APRENDIZAJE_ESTUDIANTE

    def validar(self) -> list[str]:
        fallos = []
        if not self.turno.strip():
            fallos.append("turno vacío: no hay qué reconstruir")
        if not self.identificador_sujeto.strip():

            fallos.append("identificador_sujeto vacío: la fila no se podría suprimir (DD-27)")
        if not self.trazas:
            fallos.append("sin trazas: RF-ORQ-14 promete al menos una por turno")
        return fallos

    @property
    def latencia_total_ms(self) -> float:
        return sum(t.latencia_ms for t in self.trazas)

    @property
    def latencia_por_componente(self) -> dict[str, float]:
        return {t.filtro: t.latencia_ms for t in self.trazas}

@dataclass(frozen=True)
class RegistroAfectivo:

    turno: str
    subcomponente: str
    senal: str
    regla_aplicada: str
    valor_previo: float
    valor_nuevo: float
    lambda_aplicado: float
    certeza: float
    alcance: str

    def validar(self) -> list[str]:
        fallos = []
        if self.subcomponente not in SUBCOMPONENTES_AFECTIVOS:
            fallos.append(
                f"sub-componente desconocido «{self.subcomponente}»: "
                f"{SUBCOMPONENTES_AFECTIVOS}"
            )
        if self.alcance not in ALCANCES:
            fallos.append(f"alcance desconocido «{self.alcance}»: {ALCANCES}")
        for nombre, valor in (
            ("valor_previo", self.valor_previo),
            ("valor_nuevo", self.valor_nuevo),
            ("lambda_aplicado", self.lambda_aplicado),
            ("certeza", self.certeza),
        ):
            if not 0.0 <= valor <= 1.0:
                fallos.append(f"{nombre} fuera de [0,1]: {valor}")
        if not self.regla_aplicada.strip():

            fallos.append("regla_aplicada vacía: la actualización deja de ser auditable")
        return fallos

@dataclass(frozen=True)
class RegistroConceptual:

    turno: str
    elemento: str
    estado_previo: str
    estado_nuevo: str
    evento_diagnostico: str = ""

    def validar(self) -> list[str]:
        fallos = []
        if self.estado_previo not in ESTADOS_CONCEPTUALES:
            fallos.append(f"estado_previo desconocido «{self.estado_previo}»: {ESTADOS_CONCEPTUALES}")
        if self.estado_nuevo not in ESTADOS_CONCEPTUALES:
            fallos.append(f"estado_nuevo desconocido «{self.estado_nuevo}»: {ESTADOS_CONCEPTUALES}")
        if not self.elemento.strip():
            fallos.append("elemento vacío: no hay sobre qué transiciona el estado")
        return fallos

@dataclass(frozen=True)
class RegistroEstrategico:

    turno: str
    tipo_evento: str
    ventana: int
    contador: int
    ciclo_negativo: bool = False

    def validar(self) -> list[str]:
        fallos = []
        if not self.tipo_evento.strip():
            fallos.append("tipo_evento vacío")
        if self.ventana <= 0:
            fallos.append(f"ventana inválida: {self.ventana} (debe ser positiva)")
        if self.contador < 0:
            fallos.append(f"contador inválido: {self.contador} (no puede ser negativo)")
        return fallos

@runtime_checkable
class PuertoRegistro(Protocol):

    def registrar_turno(self, entrada: EntradaDeTurno) -> None:
        ...

    def registrar_turno_completo(self, registro: RegistroDeTurno) -> None:
        ...

    def registrar_afectivo(self, registro: RegistroAfectivo) -> None:
        ...

    def registrar_conceptual(self, registro: RegistroConceptual) -> None:
        ...

    def registrar_estrategico(self, registro: RegistroEstrategico) -> None:
        ...
