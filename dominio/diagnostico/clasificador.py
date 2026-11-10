from __future__ import annotations

from dataclasses import dataclass


COMPRENSION = "E1"
ACIERTO_SIN_COMPRENSION = "E2"
ERROR_DE_EJECUCION = "E3"
CONCEPCION_ERRONEA = "E4"

NOMBRE_ESTADO = {
    COMPRENSION: "comprensión",
    ACIERTO_SIN_COMPRENSION: "acierto sin comprensión",
    ERROR_DE_EJECUCION: "error de ejecución",
    CONCEPCION_ERRONEA: "concepción errónea",
}


AVANZAR = "avanzar"
SONDEO_KQ2 = "sondeo_kq2"
SEÑALAR_PASO = "señalar_paso"
REMEDIAR = "remediar"


_SIGUIENTE = {
    COMPRENSION: AVANZAR,
    ACIERTO_SIN_COMPRENSION: SONDEO_KQ2,
    ERROR_DE_EJECUCION: SEÑALAR_PASO,
    CONCEPCION_ERRONEA: REMEDIAR,
}


@dataclass(frozen=True)
class OpcionRazon:

    identificador: str
    es_correcta: bool
    concepcion: str | None = None

    texto: str = ""

@dataclass(frozen=True)
class RespuestaAlItem:

    nodo: str
    resultado: str
    razon: str

@dataclass(frozen=True)
class RespuestaDosNiveles:

    nodo: str
    respuesta_correcta: bool
    opcion: OpcionRazon

@dataclass(frozen=True)
class Diagnostico:

    estado: str
    nodo: str
    siguiente: str
    concepcion: str | None = None
    motivo: str = ""

    @property
    def nombre(self) -> str:
        return NOMBRE_ESTADO[self.estado]

def clasificar(respuesta: RespuestaDosNiveles) -> Diagnostico:
    if respuesta.respuesta_correcta and respuesta.opcion.es_correcta:
        return Diagnostico(
            estado=COMPRENSION,
            nodo=respuesta.nodo,
            siguiente=_SIGUIENTE[COMPRENSION],
            motivo="resultado correcto y razón correcta",
        )
    if respuesta.respuesta_correcta and not respuesta.opcion.es_correcta:
        return Diagnostico(
            estado=ACIERTO_SIN_COMPRENSION,
            nodo=respuesta.nodo,
            siguiente=_SIGUIENTE[ACIERTO_SIN_COMPRENSION],
            concepcion=respuesta.opcion.concepcion,
            motivo="resultado correcto con razón incorrecta: el estado que "
            "un ítem de un solo nivel no puede ver",
        )
    if not respuesta.respuesta_correcta and respuesta.opcion.es_correcta:
        return Diagnostico(
            estado=ERROR_DE_EJECUCION,
            nodo=respuesta.nodo,
            siguiente=_SIGUIENTE[ERROR_DE_EJECUCION],
            motivo="resultado incorrecto con razón correcta: sabe lo que "
            "hace y se equivocó al hacerlo, no hay concepción que remediar",
        )

    if respuesta.opcion.concepcion is None:
        motivo = (
            "resultado y razón incorrectos, pero la opción elegida no llegó "
            "tipificada con una concepción — se declara, no se inventa una"
        )
    else:
        motivo = f"resultado y razón incorrectos: delata {respuesta.opcion.concepcion}"
    return Diagnostico(
        estado=CONCEPCION_ERRONEA,
        nodo=respuesta.nodo,
        siguiente=_SIGUIENTE[CONCEPCION_ERRONEA],
        concepcion=respuesta.opcion.concepcion,
        motivo=motivo,
    )
