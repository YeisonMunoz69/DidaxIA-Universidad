from __future__ import annotations

import argparse
import contextlib
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit

from dominio.puertos.almacen import EscrituraRechazada
from infraestructura.operacion.manifiesto_consentimiento import (
    ManifiestoInvalido,
    leer,
)

VARIABLE_ENTORNO = "AGENTE_ENTORNO"
VARIABLE_AUTORIZACION = "AGENTE_PUBLICACION_AUTORIZADA"
VARIABLE_CADENA = "AGENTE_BD_PUBLICACION"


BASES_POR_ENTORNO: dict[str, frozenset[str]] = {
    "produccion-local": frozenset({"agente"}),
    "produccion": frozenset({"agente"}),
}


class PublicacionNoAutorizada(RuntimeError):
    pass

def exigir_destino_declarado(
    entorno: Mapping[str, str] | None = None,
    *,
    exigir_autorizacion: bool = True,
) -> tuple[str, str]:

    valores = os.environ if entorno is None else entorno

    declarado = valores.get(VARIABLE_ENTORNO, "").strip().lower()
    if declarado not in BASES_POR_ENTORNO:
        raise PublicacionNoAutorizada(
            f"{VARIABLE_ENTORNO} tiene que ser uno de "
            f"{', '.join(sorted(BASES_POR_ENTORNO))}; no se publica por omisión"
        )
    if exigir_autorizacion and valores.get(VARIABLE_AUTORIZACION, "").strip() != "1":
        raise PublicacionNoAutorizada(
            f"falta {VARIABLE_AUTORIZACION}=1; ninguna otra variable autoriza esto"
        )

    cadena = valores.get(VARIABLE_CADENA, "").strip()
    if not cadena:
        raise PublicacionNoAutorizada(
            f"falta {VARIABLE_CADENA}; AGENTE_BD y las cadenas de demostración "
            "o de producción local no se reutilizan para publicar"
        )
    try:
        partes = urlsplit(cadena)
    except ValueError:
        raise PublicacionNoAutorizada(
            f"{VARIABLE_CADENA} no es una URL inspeccionable"
        ) from None
    if partes.scheme.lower() not in {"postgres", "postgresql"}:
        raise PublicacionNoAutorizada("la cadena tiene que empezar por postgresql://")

    base = partes.path.lstrip("/").lower()
    admitidas = BASES_POR_ENTORNO[declarado]
    if base not in admitidas:
        raise PublicacionNoAutorizada(
            f"la base «{base or '(ninguna)'}» no es de las admitidas para "
            f"{declarado}: {', '.join(sorted(admitidas))}"
        )
    if declarado == "produccion-local" and (partes.hostname or "").lower() not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:

        raise PublicacionNoAutorizada(
            "produccion-local sólo admite PostgreSQL en la interfaz de bucle; "
            "para un despliegue remoto declare el entorno que corresponde"
        )
    return declarado, cadena

def _describir(publicacion) -> list[str]:
    instantanea = publicacion.instantanea
    lineas = [
        f"  {publicacion.codigo}",
        f"      alcance      {publicacion.alcance.value}",
        f"      huella       {instantanea.huella}",
        f"      bytes        {len(instantanea.bytes_canonicos)}",
        f"      vigente      {publicacion.vigente_desde.isoformat()}"
        + (
            f" -> {publicacion.vigente_hasta.isoformat()}"
            if publicacion.vigente_hasta
            else " -> sin fin"
        ),
        f"      finalidades  {', '.join(sorted(f.value for f in publicacion.finalidades))}",
    ]
    return lineas

def consola_que_no_aborta() -> None:
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is None:
            continue

        with contextlib.suppress(OSError, ValueError):
            reconfigurar(errors="replace")

def main(argumentos: list[str] | None = None) -> int:
    consola_que_no_aborta()
    analizador = argparse.ArgumentParser(
        description=(
            "Publicar versiones de consentimiento con su texto canónico. En "
            "seco por defecto: sin --confirmar-publicacion no escribe nada."
        )
    )
    analizador.add_argument("--manifiesto", required=True, type=Path)
    analizador.add_argument("--textos", required=True, type=Path)
    analizador.add_argument(
        "--dry-run",
        action="store_true",
        help="explícito, aunque es lo que se hace si no se confirma",
    )
    analizador.add_argument(
        "--confirmar-publicacion",
        action="store_true",
        help="escribir de verdad; una versión publicada no se puede editar",
    )
    opciones = analizador.parse_args(argumentos)

    if opciones.dry_run and opciones.confirmar_publicacion:

        print(
            "Publicación detenida · --dry-run y --confirmar-publicacion se "
            "contradicen: elija una",
            file=sys.stderr,
        )
        return 2

    try:
        publicaciones = leer(opciones.manifiesto, opciones.textos)
    except ManifiestoInvalido as exc:
        print(f"Manifiesto rechazado · {exc}", file=sys.stderr)
        return 2

    print(f"Paquete leído · {len(publicaciones)} versión(es)")
    for publicacion in publicaciones:
        for linea in _describir(publicacion):
            print(linea)

    if not opciones.confirmar_publicacion:
        print()
        print("EN SECO · no se ha escrito nada y no se ha abierto ninguna conexión.")
        print(
            "Compruebe que cada huella corresponde al documento que se aprobó y "
            "repita con --confirmar-publicacion."
        )
        return 0

    try:
        entorno, cadena = exigir_destino_declarado()
    except PublicacionNoAutorizada as exc:
        print(f"Publicación detenida · {exc}", file=sys.stderr)
        return 2

    from adaptadores.salientes.registro.consentimiento_versionado_db import (
        AdaptadorVersionesDeConsentimientoPostgres,
    )

    adaptador = AdaptadorVersionesDeConsentimientoPostgres(cadena)
    print()
    print(f"Publicando en «{entorno}» · lote de {len(publicaciones)}")

    try:
        resultados = adaptador.publicar_lote(publicaciones)
    except EscrituraRechazada as exc:
        print(f"  RECHAZADO · {exc}", file=sys.stderr)
        print(
            "Publicación revertida · el lote es atómico, así que NO se escribió "
            "ninguna de las versiones del manifiesto.",
            file=sys.stderr,
        )
        return 2

    for resultado in resultados:
        print(f"  {resultado.codigo} · {resultado.motivo}")

    escritas = sum(1 for r in resultados if r.escrita)
    print()
    print(f"Publicación terminada · {escritas} escrita(s) de {len(publicaciones)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
