from __future__ import annotations

from dataclasses import dataclass, field, replace

from dominio.puertos.registro import ESTADOS_CONCEPTUALES
from dominio.puertos.registro import RegistroAfectivo as EntradaAfectiva
from dominio.puertos.registro import RegistroConceptual as EntradaConceptual
from dominio.puertos.registro import RegistroEstrategico as EntradaEstrategica


LAMBDA_ESTADO_POR_DEFECTO = 0.85


LAMBDA_RASGO_POR_DEFECTO = 0.85


LAMBDA_POR_ALCANCE: dict[str, float] = {
    "estado": LAMBDA_ESTADO_POR_DEFECTO,
    "rasgo": LAMBDA_RASGO_POR_DEFECTO,
}


VENTANA_ESTRATEGICA_POR_DEFECTO = 3


@dataclass(frozen=True)
class EstadoAfectivo:

    valores: dict[str, float] = field(default_factory=dict)

    def valor(self, subcomponente: str) -> float | None:
        return self.valores.get(subcomponente)

    def actualizar(
        self,
        subcomponente: str,
        obs_t: float,
        turno: str,
        señal: str,
        certeza: float = 1.0,
        lam: float = LAMBDA_ESTADO_POR_DEFECTO,
    ) -> tuple[EstadoAfectivo, EntradaAfectiva]:

        if not 0.0 <= obs_t <= 1.0:
            raise ValueError(f"obs_t fuera de [0,1]: {obs_t}")
        previo = self.valores.get(subcomponente, 0.0)
        nuevo = min(1.0, lam * previo + (1.0 - lam) * obs_t)
        estado = replace(self, valores={**self.valores, subcomponente: nuevo})
        entrada = EntradaAfectiva(
            turno=turno,
            subcomponente=subcomponente,
            senal=señal,
            regla_aplicada="N2 · decaimiento con saturación",
            valor_previo=previo,
            valor_nuevo=nuevo,
            lambda_aplicado=lam,
            certeza=certeza,
            alcance="estado",
        )
        return estado, entrada

_TRANSICION_CONCEPTUAL = {
    ("no_detectada", "detectada"): "activa",
    ("activa", "detectada"): "activa",
    ("activa", "remediada"): "remediada",
    ("remediada", "detectada"): "recurrente",
    ("remediada", "remediada"): "remediada",
    ("recurrente", "detectada"): "recurrente",
    ("recurrente", "remediada"): "remediada",
}


@dataclass(frozen=True)
class EstadoConceptual:

    estados: dict[str, str] = field(default_factory=dict)

    def estado_de(self, elemento: str) -> str:
        return self.estados.get(elemento, "no_detectada")

    def registrar_evento(
        self, elemento: str, evento: str, turno: str
    ) -> tuple[EstadoConceptual, EntradaConceptual]:
        if evento not in ("detectada", "remediada"):
            raise ValueError(f"evento desconocido «{evento}»: detectada | remediada")
        previo = self.estado_de(elemento)
        nuevo = _TRANSICION_CONCEPTUAL[(previo, evento)]
        estado = replace(self, estados={**self.estados, elemento: nuevo})
        entrada = EntradaConceptual(
            turno=turno,
            elemento=elemento,
            estado_previo=previo,
            estado_nuevo=nuevo,
            evento_diagnostico=evento,
        )
        assert nuevo in ESTADOS_CONCEPTUALES
        return estado, entrada

@dataclass(frozen=True)
class Episodio:

    retroalimentacion_correctiva: bool = False
    reincide_en_la_estrategia: bool = False
    confusion: bool = False
    afecto_negativo: bool = False
    evitacion_o_bajo_esfuerzo: bool = False

@dataclass(frozen=True)
class EstadoEstrategico:

    ventana: int = VENTANA_ESTRATEGICA_POR_DEFECTO
    episodios: tuple[Episodio, ...] = ()

    def registrar(
        self, episodio: Episodio, turno: str
    ) -> tuple[EstadoEstrategico, EntradaEstrategica]:
        episodios = (self.episodios + (episodio,))[-self.ventana :]
        estado = replace(self, episodios=episodios)
        entrada = EntradaEstrategica(
            turno=turno,
            tipo_evento="episodio_registrado",
            ventana=self.ventana,
            contador=len(episodios),
            ciclo_negativo=estado.ciclo_negativo,
        )
        return estado, entrada

    @property
    def sesgo_de_confirmacion(self) -> bool:
        reincidencias = sum(
            1
            for e in self.episodios
            if e.retroalimentacion_correctiva and e.reincide_en_la_estrategia
        )
        return reincidencias >= 2

    @property
    def ciclo_negativo(self) -> bool:
        if len(self.episodios) < self.ventana:
            return False
        recientes = self.episodios[-self.ventana :]
        confusion_recurrente = sum(1 for e in recientes if e.confusion) >= 2
        hay_afecto_negativo = any(e.afecto_negativo for e in recientes)
        hay_evitacion = any(e.evitacion_o_bajo_esfuerzo for e in recientes)
        return confusion_recurrente and hay_afecto_negativo and hay_evitacion

@dataclass(frozen=True)
class PerfilEstudiante:

    afectivo: EstadoAfectivo = field(default_factory=EstadoAfectivo)
    conceptual: EstadoConceptual = field(default_factory=EstadoConceptual)
    estrategico: EstadoEstrategico = field(default_factory=EstadoEstrategico)
