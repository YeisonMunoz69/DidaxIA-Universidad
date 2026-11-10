from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dominio.modelo.consentimiento import FINALIDADES_OBLIGATORIAS, Alcance
from dominio.modelo.instantanea_consentimiento import huella_de
from infraestructura.operacion.manifiesto_consentimiento import (
    ManifiestoInvalido,
    leer,
)
from infraestructura.operacion.publicar_consentimiento import (
    PublicacionNoAutorizada,
    consola_que_no_aborta,
    exigir_destino_declarado,
)


FINALIDADES_ESPERADAS = len(FINALIDADES_OBLIGATORIAS)


class Veredicto(str, Enum):

    VACIA = "VACIA"
    PUBLICADA = "PUBLICADA"
    INCOMPLETA = "INCOMPLETA"
    COLISION = "COLISION"
    HISTORICA = "HISTORICA"

SALIDA = {
    Veredicto.VACIA: 0,
    Veredicto.PUBLICADA: 10,
    Veredicto.INCOMPLETA: 11,
    Veredicto.COLISION: 12,
    Veredicto.HISTORICA: 13,
}

ERROR = 2


@dataclass(frozen=True)
class Observacion:

    alcance: str
    codigo_esperado: str
    huella_esperada: str

    versiones_del_alcance: int

    codigo_presente: bool

    huella_registrada: str | None = None

    cuerpo: str | None = None

    finalidades: int = 0

    ya_comenzo: bool = False

    sigue_vigente: bool = False

    codigo_requerido: str | None = None

    @property
    def huella_recalculada(self) -> str | None:
        return None if self.cuerpo is None else huella_de(self.cuerpo)

    def motivos(self) -> list[str]:
        if not self.codigo_presente:
            if self.versiones_del_alcance:
                return [
                    f"no existe «{self.codigo_esperado}», pero el alcance ya tiene "
                    f"{self.versiones_del_alcance} versión(es)"
                ]
            return [f"no existe «{self.codigo_esperado}»"]

        fallos: list[str] = []
        if self.huella_registrada != self.huella_esperada:
            fallos.append(
                f"«{self.codigo_esperado}» existe con OTRA huella "
                f"({_corta(self.huella_registrada)} en base, "
                f"{_corta(self.huella_esperada)} en el paquete)"
            )

            return fallos

        return self._motivos_del_documento() + self._motivos_de_vigencia()

    def _motivos_del_documento(self) -> list[str]:
        fallos: list[str] = []
        if self.cuerpo is None:
            fallos.append("no tiene instantánea: el documento no se puede leer")
        elif self.huella_recalculada != self.huella_registrada:
            fallos.append(
                "el cuerpo guardado no corresponde a su huella "
                f"(recalculada {_corta(self.huella_recalculada)})"
            )
        if self.finalidades != FINALIDADES_ESPERADAS:
            fallos.append(f"declara {self.finalidades} finalidad(es) y no {FINALIDADES_ESPERADAS}")
        return fallos

    def _motivos_de_vigencia(self) -> list[str]:
        fallos: list[str] = []
        if not self.ya_comenzo:
            fallos.append("«vigente_desde» todavía no ha llegado")
        if not self.sigue_vigente:
            fallos.append("«vigente_hasta» ya pasó")
        if self.codigo_requerido is None:
            fallos.append("didaxia_version_requerida() devuelve NULL")
        elif self.codigo_requerido != self.codigo_esperado:
            fallos.append(f"gobierna «{self.codigo_requerido}», no «{self.codigo_esperado}»")
        return fallos

    @property
    def integra(self) -> bool:
        return (
            self.codigo_presente
            and self.huella_registrada == self.huella_esperada
            and self.cuerpo is not None
            and self.huella_recalculada == self.huella_esperada
            and self.finalidades == FINALIDADES_ESPERADAS
            and self.ya_comenzo
            and self.sigue_vigente
        )

    @property
    def gobierna(self) -> bool:
        return self.codigo_requerido == self.codigo_esperado

def _corta(huella: str | None) -> str:
    return "(ninguna)" if not huella else f"{huella[:12]}…"

def clasificar(observaciones: tuple[Observacion, ...]) -> Veredicto:
    if all(o.versiones_del_alcance == 0 for o in observaciones):
        return Veredicto.VACIA

    presentes = [o for o in observaciones if o.codigo_presente]
    if any(o.huella_registrada != o.huella_esperada for o in presentes):
        return Veredicto.COLISION
    if not presentes:
        return Veredicto.HISTORICA

    if len(presentes) == len(observaciones) and all(o.integra for o in observaciones):
        if all(o.gobierna for o in observaciones):
            return Veredicto.PUBLICADA
        return Veredicto.HISTORICA

    return Veredicto.INCOMPLETA

CONSEJO = {
    Veredicto.VACIA: (
        "No hay ninguna versión publicada. Continúe con el ensayo en seco y "
        "después con la publicación."
    ),
    Veredicto.PUBLICADA: (
        "El paquete YA está publicado, íntegro y gobernando los tres alcances. "
        "NO publique de nuevo: pase a la verificación y al recorrido."
    ),
    Veredicto.INCOMPLETA: (
        "La publicación está a medias o algo no cuadra. NO publique encima: "
        "avise al equipo con esta salida. Una versión publicada no se edita, "
        "así que la salida suele ser publicar una versión NUEVA."
    ),
    Veredicto.COLISION: (
        "Un código del paquete ya existe con OTRO contenido. DETÉNGASE. "
        "Publicar destruiría la prueba de qué leyó quien aceptó. Hace falta "
        "un código nuevo, decidido por el equipo."
    ),
    Veredicto.HISTORICA: (
        "Hay versiones publicadas que no son las que gobiernan este paquete. "
        "No es un error: EQ-021 prevé versiones nuevas sin borrar las "
        "anteriores. NO publique sin confirmar con el equipo cuál debe regir."
    ),
}


def _observar(cur, publicacion) -> Observacion:
    alcance = publicacion.alcance.value
    codigo = publicacion.codigo
    huella = publicacion.instantanea.huella

    cur.execute(
        "SELECT count(1) FROM consentimiento_version WHERE alcance = %s",
        (alcance,),
    )
    total = int(cur.fetchone()[0])

    cur.execute("SELECT didaxia_version_requerida(%s)", (alcance,))
    requerido = cur.fetchone()[0]

    cur.execute(
        """
        SELECT v.huella_contenido,
               t.cuerpo,
               (SELECT count(1) FROM consentimiento_version_finalidad f
                 WHERE f.version = v.codigo),
               v.vigente_desde <= now(),
               v.vigente_hasta IS NULL OR v.vigente_hasta > now()
          FROM consentimiento_version v
          LEFT JOIN consentimiento_version_texto t ON t.version = v.codigo
         WHERE v.codigo = %s AND v.alcance = %s
        """,
        (codigo, alcance),
    )
    fila = cur.fetchone()
    if fila is None:
        return Observacion(
            alcance=alcance,
            codigo_esperado=codigo,
            huella_esperada=huella,
            versiones_del_alcance=total,
            codigo_presente=False,
            codigo_requerido=requerido,
        )

    registrada, cuerpo, finalidades, ya_comenzo, sigue_vigente = fila
    return Observacion(
        alcance=alcance,
        codigo_esperado=codigo,
        huella_esperada=huella,
        versiones_del_alcance=total,
        codigo_presente=True,
        huella_registrada=registrada,
        cuerpo=cuerpo,
        finalidades=int(finalidades),
        ya_comenzo=bool(ya_comenzo),
        sigue_vigente=bool(sigue_vigente),
        codigo_requerido=requerido,
    )

def informar(observaciones: tuple[Observacion, ...], veredicto: Veredicto) -> list[str]:
    lineas = [f"Estado del consentimiento · {veredicto.value}", ""]
    for o in sorted(observaciones, key=lambda x: x.alcance):
        motivos = o.motivos()

        marca = "--  " if veredicto is Veredicto.VACIA else ("ok  " if not motivos else "MAL ")
        lineas.append(f"  {marca}{o.alcance}")
        lineas.append(f"      esperado     {o.codigo_esperado}")
        lineas.append(f"      huella       {_corta(o.huella_esperada)}")
        lineas.append(f"      en base      {o.versiones_del_alcance} versión(es)")
        lineas.append(f"      gobierna     {o.codigo_requerido or '(ninguna)'}")
        for motivo in motivos:
            lineas.append(f"      · {motivo}")
    lineas.extend(["", CONSEJO[veredicto]])
    return lineas

def main(argumentos: list[str] | None = None) -> int:
    consola_que_no_aborta()

    analizador = argparse.ArgumentParser(
        description=(
            "Qué hay publicado frente al paquete declarado. Sólo lectura: no "
            "escribe nada y no acepta ninguna confirmación."
        )
    )
    analizador.add_argument("--manifiesto", required=True, type=Path)
    analizador.add_argument("--textos", required=True, type=Path)
    opciones = analizador.parse_args(argumentos)

    try:
        publicaciones = leer(opciones.manifiesto, opciones.textos)
    except ManifiestoInvalido as exc:
        print(f"Manifiesto rechazado · {exc}", file=sys.stderr)
        return ERROR

    alcances = {p.alcance for p in publicaciones}
    if alcances != set(Alcance):
        faltan = ", ".join(sorted(a.value for a in set(Alcance) - alcances))
        print(
            f"Paquete incompleto · faltan alcances: {faltan}. Los tres se publican juntos.",
            file=sys.stderr,
        )
        return ERROR

    try:
        entorno, cadena = exigir_destino_declarado(exigir_autorizacion=False)
    except PublicacionNoAutorizada as exc:
        print(f"Consulta detenida · {exc}", file=sys.stderr)
        return ERROR

    import psycopg

    try:
        with psycopg.connect(cadena) as conexion, conexion.cursor() as cur:
            observaciones = tuple(_observar(cur, p) for p in publicaciones)
    except psycopg.Error as exc:
        print(f"No se pudo consultar la base · {exc}", file=sys.stderr)
        return ERROR

    veredicto = clasificar(observaciones)
    print(f"Consultando «{entorno}»")
    for linea in informar(observaciones, veredicto):
        print(linea)
    return SALIDA[veredicto]

if __name__ == "__main__":
    raise SystemExit(main())
