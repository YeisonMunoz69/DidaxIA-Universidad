"""
publicar_consentimiento.py — Publicar una versión real, con su texto y su huella
==================================================================================

    # 1 · siempre primero, y es lo que ocurre si no se dice otra cosa
    python -m infraestructura.operacion.publicar_consentimiento \\
        --manifiesto <ruta-externa>/manifiesto.json --textos <ruta-externa>

    # 2 · sólo cuando lo de arriba se leyó y se aprobó
    python -m infraestructura.operacion.publicar_consentimiento \\
        --manifiesto <ruta-externa>/manifiesto.json --textos <ruta-externa> \\
        --confirmar-publicacion

Qué la separa de la otra siembra que queda
------------------------------------------------------
| Herramienta | Qué publica | Dónde |
|---|---|---|
| `infraestructura.demostracion.semilla` | textos **de borrador** con código `demo-…` | base de demostración |
| ~~`infraestructura.operacion.semilla`~~ | **retirada** · se detiene con código 2 | — |
| ésta | el texto que una persona aprobó, leído de un manifiesto externo | el despliegue que se declare |

⚠️ **Por qué la segunda fila está tachada** · `C1-C`. Aquella herramienta
**importaba** `sembrar` de la siembra de demostración y **publicaba** los textos
rotulados `BORRADOR DE DEMOSTRACIÓN`, con códigos `demo-…-borrador-…`, en una
base llamada `agente`. Su barrera exigía interfaz de bucle, y eso impide apuntar
a la VPS **desde un portátil**; no impedía nada ejecutado **dentro** de la VPS,
donde `127.0.0.1` es su propio PostgreSQL y la base se llama exactamente
`agente`. Allí la barrera se cumplía entera y los borradores quedaban delante de
estudiantes reales.

El antecedente se conserva porque es lo único que impide reconstruirla creyendo
que el loopback bastaba: **protege de apuntar lejos, no de ejecutar cerca**.
`EQ-027` decide que los textos de demostración viven exclusivamente en la
demostración aislada, así que esa vía no necesitaba una barrera mejor sino no
existir. Esta herramienta nunca reutilizó esa barrera; la suya se declara abajo.

La barrera de ésta · `§8.10`
--------------------------------
No hay «bypass local» que reaprovechar: se exige que el operador **declare a qué
despliegue apunta** y que esa declaración concuerde con la cadena.

1. `AGENTE_ENTORNO` — el entorno, explícito. No se deduce.
2. `AGENTE_PUBLICACION_AUTORIZADA=1` — una autorización propia. `AGENTE_BD`,
   `AGENTE_BD_DEMO` y `AGENTE_BD_PRODUCCION_LOCAL` **no** sirven aquí, y es
   deliberado: una variable que ya está puesta en la terminal por otra tarea no
   puede autorizar ésta.
3. `AGENTE_BD_PUBLICACION` — la cadena, en su propia variable.
4. La base tiene que ser una de las nombradas para ese entorno. Publicar en
   `agente_pruebas` desde `AGENTE_ENTORNO=produccion` es un error de dedo que
   aquí se detiene.

Y sobre todo: **`--dry-run` es el comportamiento por defecto**, no una opción.
Sin `--confirmar-publicacion` no se abre ninguna transacción de escritura. El
argumento no es que publicar sea peligroso —que lo es— sino que un texto legal
publicado bajo un código **no se puede editar**: corregirlo exige otro código, y
las decisiones ya tomadas quedan apuntando al anterior.

Lo que esta herramienta NO decide
--------------------------------------
No decide si el texto es verdadero, completo o suficiente, y no lo comprueba:
no puede. Lee lo que una persona aprobó y escribió en un archivo, comprueba que
el paquete está **bien formado**, y lo publica cuando esa misma persona lo
confirma. Que el documento diga la verdad sobre el tratamiento es una
responsabilidad humana, y ninguna bandera de este archivo la sustituye.


"""

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

#: Qué base admite cada entorno. Es una lista blanca y no una comprobación de
#: forma: «que la base se llame `agente`» no distingue la producción local de la
#: VPS, y ésa es justamente la distinción que hay que poder hacer.
#:
#: `demostracion` NO está. Para la demostración ya existe su siembra, con sus
#: textos de borrador rotulados; publicar ahí un texto real mezclaría los dos
#: y haría que la pantalla de la demostración dejara de decir «borrador».
BASES_POR_ENTORNO: dict[str, frozenset[str]] = {
    "produccion-local": frozenset({"agente"}),
    "produccion": frozenset({"agente"}),
}


class PublicacionNoAutorizada(RuntimeError):
    """El destino no satisface las barreras de publicación."""


def exigir_destino_declarado(
    entorno: Mapping[str, str] | None = None,
    *,
    exigir_autorizacion: bool = True,
) -> tuple[str, str]:
    """`(entorno, cadena)` sólo si el operador declaró a dónde publica.

    Devuelve el entorno además de la cadena para que quien informe pueda
    nombrarlo sin volver a leer el ambiente — y para que la salida diga a qué
    despliegue se apuntó, que es lo primero que se revisa en un informe.

    `exigir_autorizacion=False` es para las herramientas que **sólo leen**
    (`estado_consentimiento`). Siguen teniendo que declarar entorno y cadena
    —apuntar a la base equivocada es un error aunque sea para mirar—, pero no
    `AGENTE_PUBLICACION_AUTORIZADA`: esa variable autoriza a **escribir**, y
    pedirla para una consulta enseñaría a ponerla cuando no hace falta, que es
    justo la costumbre que la barrera existe para no crear.

    ⚠️ **Nunca devuelve la cadena en un mensaje de error.** Lleva credenciales.
    Lo que se nombra es la variable que falta y, como mucho, el nombre de la
    base y el anfitrión.
    """
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
        # La producción local es local. Si alguien declara `produccion-local` y
        # apunta a un anfitrión remoto, lo que hay es una confusión sobre a qué
        # despliegue se está escribiendo — que es el error que más caro sale.
        raise PublicacionNoAutorizada(
            "produccion-local sólo admite PostgreSQL en la interfaz de bucle; "
            "para un despliegue remoto declare el entorno que corresponde"
        )
    return declarado, cadena


def _describir(publicacion) -> list[str]:
    """Lo que se enseña de una versión, **sin su cuerpo**.

    El documento no se imprime: puede llevar datos de contacto y la salida de
    esta herramienta acaba pegada en un informe. Lo que se enseña es lo que
    permite comprobar que el paquete es el que se quería —código, alcance,
    huella, vigencia, finalidades y tamaño— y la huella es lo que ata esa
    comprobación al texto exacto.
    """
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
    """Que la consola no pueda tumbar el ensayo en seco. `C4`

    🔴 El defecto: en Windows, `sys.stdout` toma la página de códigos de la
    consola —`cp1252` en el equipo del equipo— y **cualquier carácter que no
    esté en ella lanza `UnicodeEncodeError`**. El ensayo en seco imprimía una
    flecha y varios `·`, así que moría a mitad de la primera versión:

        UnicodeEncodeError: 'charmap' codec can't encode character '→'

    Con código de salida 1, después de haber impreso una huella y antes de las
    otras dos. El ensayo en seco es **obligatorio** antes de publicar
    (`C4.4`), así que un fallo aquí bloquea el procedimiento entero en la
    única máquina donde se ejecuta.

    La usan `publicar_consentimiento` y `estado_consentimiento`: las dos se
    ejecutan en la misma consola y por el mismo operador.

    Se degrada a `?` en lugar de forzar UTF-8: escribir bytes UTF-8 en una
    consola `cp1252` no falla, pero se ve mal, y lo que el operador tiene que
    leer sin ambigüedad —códigos, huellas, bytes, fechas— es **todo ASCII** y
    sobrevive intacto a la sustitución.
    """
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is None:  # pragma: no cover - flujo ya sustituido
            continue
        # pragma: no cover - un flujo no reconfigurable no puede fallar aquí
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
        # Pedir las dos cosas a la vez no es un matiz que convenga resolver
        # eligiendo una: quien lo escribe no sabe cuál va a pasar.
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

    # El adaptador se importa aquí y no arriba a propósito: en seco esta
    # herramienta no debe siquiera necesitar el controlador de PostgreSQL, y así
    # un `--dry-run` funciona en un equipo que no lo tenga instalado.
    from adaptadores.salientes.registro.consentimiento_versionado_db import (
        AdaptadorVersionesDeConsentimientoPostgres,
    )

    adaptador = AdaptadorVersionesDeConsentimientoPostgres(cadena)
    print()
    print(f"Publicando en «{entorno}» · lote de {len(publicaciones)}")

    # `C1-D` · UNA transacción para el paquete entero.
    #
    # Aquí se recorría el manifiesto llamando a `publicar()` una vez por
    # versión, y cada llamada abría su propia transacción: si la primera
    # escribía y la segunda colisionaba, quedaba publicado un SUBCONJUNTO. Un
    # paquete titular/asentimiento/representante se aprueba como conjunto, y
    # estas tablas son inmutables, así que lo escrito no se podía deshacer.
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
