from __future__ import annotations

from dataclasses import dataclass, field, replace

from dominio.modelo.estudiante import EstadoAfectivo
from dominio.pedagogia.problema import EstadoDelProblema


@dataclass(frozen=True)
class EstadoDeConversacion:

    afectivo: EstadoAfectivo = field(default_factory=EstadoAfectivo)

    problema: EstadoDelProblema = field(default_factory=EstadoDelProblema)

    sin_adaptacion: bool = False

    estrategia_previa: str = ""

    def como_dict(self) -> dict:
        return {
            "afectivo": dict(self.afectivo.valores),
            "problema": self.problema.como_dict(),
            "sin_adaptacion": self.sin_adaptacion,
            "estrategia_previa": self.estrategia_previa,
        }

    @classmethod
    def desde_dict(cls, crudo: dict | None) -> EstadoDeConversacion:
        if not isinstance(crudo, dict):
            return cls()
        afectivo = crudo.get("afectivo")
        return cls(
            afectivo=EstadoAfectivo(
                valores={k: float(v) for k, v in afectivo.items()}
                if isinstance(afectivo, dict)
                else {}
            ),
            problema=EstadoDelProblema.desde_dict(crudo.get("problema") or {}),
            sin_adaptacion=bool(crudo.get("sin_adaptacion", False)),
            estrategia_previa=str(crudo.get("estrategia_previa", "")),
        )

    def con_afectivo(self, afectivo: EstadoAfectivo) -> EstadoDeConversacion:
        return replace(self, afectivo=afectivo)

    def con_problema(self, problema: EstadoDelProblema) -> EstadoDeConversacion:
        return replace(self, problema=problema)

    def con_inferencia_corregida(self) -> EstadoDeConversacion:
        return replace(self, afectivo=EstadoAfectivo())
