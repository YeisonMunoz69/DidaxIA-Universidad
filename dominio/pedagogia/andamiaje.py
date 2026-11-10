from __future__ import annotations

from dataclasses import dataclass, field

from dominio.pedagogia import estrategias as E
from dominio.puertos.plantillas import (
    AUTOCONCEPTO,
    AUTORREGULACION,
    SCAFFOLDING_KQ,
    SOCRATICA_APOS,
    Plantilla,
    PuertoPlantillas,
)


_REPERTORIO_DE_LA_ESTRATEGIA = {
    E.DIALOGO_SOCRATICO_APOS: SOCRATICA_APOS,
    E.SCAFFOLDING_KQ: SCAFFOLDING_KQ,
    E.CONFLICTO_CONCEPTUAL: SCAFFOLDING_KQ,
}


_USAN_LA_SECUENCIA = frozenset({E.SCAFFOLDING_KQ, E.CONFLICTO_CONCEPTUAL})


_TONO_DEL_MODIFICADOR = {
    E.TONO_NO_EVALUATIVO: AUTOCONCEPTO,
    E.AUTORREGULACION: AUTORREGULACION,
}


@dataclass(frozen=True)
class Andamiaje:

    principal: Plantilla | None = None
    tono: tuple[Plantilla, ...] = ()

    motivo: str = ""
    concepcion: str = ""
    tonos_omitidos: tuple[str, ...] = field(default_factory=tuple)

    @property
    def utilizable(self) -> bool:
        return (self.principal is not None and self.principal.utilizable) or bool(self.tono)

def elegir(
    plantillas: PuertoPlantillas | None,
    *,
    estrategia: str,
    modificadores: tuple[str, ...] = (),
    concepcion: str = "",
    concepciones_candidatas: tuple[str, ...] = (),
) -> Andamiaje:

    if plantillas is None:
        return Andamiaje(motivo="sin adaptador de plantillas")

    principal, motivo, usada = _principal(
        plantillas, estrategia, concepcion, concepciones_candidatas
    )
    tono, omitidos = _tono(plantillas, modificadores)
    return Andamiaje(
        principal=principal,
        tono=tono,
        motivo=motivo,
        concepcion=usada,
        tonos_omitidos=omitidos,
    )

def _principal(
    plantillas: PuertoPlantillas,
    estrategia: str,
    concepcion: str,
    candidatas: tuple[str, ...],
) -> tuple[Plantilla | None, str, str]:

    clave = _REPERTORIO_DE_LA_ESTRATEGIA.get(estrategia)
    if clave is None:
        return (
            None,
            f"la estrategia «{estrategia}» no lleva repertorio de preguntas: "
            "inyectarlo produciría una respuesta que pregunta",
            "",
        )

    if estrategia in _USAN_LA_SECUENCIA:

        for cual, procedencia in [(concepcion, "diagnosticada")] + [
            (c, "candidata") for c in candidatas
        ]:
            if not cual:
                continue
            secuencia = plantillas.secuencia_de(cual)
            if secuencia is not None and secuencia.utilizable:
                return secuencia, f"secuencia de la concepción {procedencia} {cual}", cual

    generica = plantillas.plantilla(clave)
    cual = concepcion or (candidatas[0] if candidatas else "")
    if cual:
        return (
            generica,
            f"la concepción «{cual}» no tiene secuencia escrita: repertorio genérico",
            cual,
        )
    return generica, f"repertorio de «{estrategia}»", ""

def _tono(
    plantillas: PuertoPlantillas, modificadores: tuple[str, ...]
) -> tuple[tuple[Plantilla, ...], tuple[str, ...]]:

    elegidas: list[Plantilla] = []
    omitidas: list[str] = []
    for modificador in modificadores:
        clave = _TONO_DEL_MODIFICADOR.get(modificador)
        if clave is None:
            continue
        plantilla = plantillas.plantilla(clave)
        if plantilla is not None and plantilla.utilizable:
            if plantilla not in elegidas:
                elegidas.append(plantilla)
        else:
            omitidas.append(clave)
    return tuple(elegidas), tuple(dict.fromkeys(omitidas))
