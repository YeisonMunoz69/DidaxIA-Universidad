"""
cargador.py — Lee los fragmentos del corpus desde `contenido/corpus/fragmentos/`
================================================================================

Cierra el hueco real del incremento 1: el puerto `PuertoCorpus` y el tipo
`Fragmento` existían desde el principio y **nada leía los archivos**. Sin este
adaptador el contenido escrito por el equipo no llega al sistema, y el
incremento 2 no tiene contra qué probar la recuperación.

Por qué es un adaptador y no dominio
------------------------------------

`ADR-001` §6.2: el dominio no toca el sistema de archivos. Aquí sí, y esa es
toda la diferencia. La consecuencia práctica se ve en cómo se reparte la
validación de la clave de obra:

| Quién | Qué comprueba | Por qué ahí |
|---|---|---|
| `Procedencia.validar()` · dominio | Que la clave tenga **forma** de clave: tres mayúsculas | No necesita leer nada |
| Este adaptador | Que la clave **exista** en `FUENTES.md` | Requiere abrir un archivo |

Separarlo así evita duplicar el catálogo de obras dentro del código, que es la
regla de `COMO-TRABAJAMOS.md` §1: *si el dato existe en un archivo, se lee de
ese archivo*. `FUENTES.md` es la única lista de obras del proyecto.

Por qué el analizador de cabecera se escribe a mano
---------------------------------------------------

La cabecera es YAML de tres niveles y sin sorpresas. Añadir una dependencia
para eso costaría más de lo que ahorra, y el analizador falla de forma explícita
ante cualquier cosa que no reconozca en lugar de aceptarla en silencio — que es
lo que aquí importa, porque un fragmento mal leído entra al índice y ya no se
distingue de uno correcto.

Qué NO hace este módulo
-----------------------

**No verifica la matemática.** `DD-02` la exige al ingerir y la ejerce el puerto
simbólico, no este cargador. Un fragmento puede cargarse bien y contener una
fórmula falsa; por eso `cargar` devuelve los fragmentos y sus fallos por
separado, y quien indexe decide qué hacer con cada cosa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from dominio.puertos.corpus import Fragmento, Procedencia

#: Delimitador de la cabecera de metadatos, como en cualquier archivo con
#: *front matter*.
_CERCA = "---"

#: Claves de obra declaradas en `FUENTES.md`. Se extraen de los encabezados
#: `### `CLA` · Autor`, que es donde vive la ficha de cada una.
_CLAVE_EN_FUENTES = re.compile(r"^###\s+`([A-Z]{3})`", re.M)


@dataclass(frozen=True)
class ResultadoDeCarga:
    """Lo que produce una pasada sobre el directorio de fragmentos.

    Los fallos **no** interrumpen la carga. Un archivo mal escrito no puede
    impedir que los demás entren, del mismo modo que un bloque que no verifica
    no corta el barrido del adaptador simbólico (`ADR-008`).
    """

    fragmentos: tuple[Fragmento, ...] = ()
    fallos: tuple[str, ...] = ()
    #: `DD-02`: un fragmento sin la marca `verificacion_dd02` en su cabecera no
    #: entra en `fragmentos`. `verificado` y `sin matemática` cuentan como
    #: pasados —son los dos únicos estados que `verificar-matematica.py
    #: --marcar` escribe—; lo que bloquea es la ausencia de marca. No es un
    #: fallo de lectura —el archivo está bien formado— así que no cuenta
    #: contra `utilizable`; es una condición de ingreso al índice, y se
    #: cuenta y se nombra aquí para que quien ingiera no tenga que
    #: descubrirlo en silencio.
    excluidos_por_dd02: tuple[str, ...] = ()

    @property
    def utilizable(self) -> bool:
        """Hay material y ningún archivo quedó mal leído."""
        return bool(self.fragmentos) and not self.fallos


def claves_de_obra(ruta_fuentes: Path) -> frozenset[str]:
    """Las claves declaradas en `FUENTES.md`.

    Devuelve un conjunto vacío si el archivo no existe. **No inventa un
    catálogo por defecto**: sin fuentes declaradas, ninguna procedencia es
    comprobable y `cargar` lo dirá archivo por archivo.
    """
    if not ruta_fuentes.is_file():
        return frozenset()
    return frozenset(_CLAVE_EN_FUENTES.findall(ruta_fuentes.read_text(encoding="utf-8")))


def _partir(texto: str) -> tuple[str, str]:
    """Separa cabecera y cuerpo. Lanza `ValueError` si no hay cabecera."""
    if not texto.lstrip().startswith(_CERCA):
        raise ValueError("no empieza con una cabecera de metadatos")
    partes = texto.lstrip().split(_CERCA, 2)
    if len(partes) < 3:
        raise ValueError("la cabecera de metadatos no está cerrada")
    return partes[1], partes[2]


def _leer_cabecera(cabecera: str) -> tuple[dict[str, str], dict[str, str]]:
    """Campos sueltos y campos de `procedencia`, en dos diccionarios."""
    campos: dict[str, str] = {}
    procedencia: dict[str, str] = {}
    en_procedencia = False
    for linea in cabecera.splitlines():
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        anidada = linea.startswith((" ", "\t"))
        if en_procedencia and anidada:
            clave, _, valor = linea.strip().partition(":")
            procedencia[clave.strip()] = valor.split("#")[0].strip()
            continue
        en_procedencia = False
        clave, sep, valor = linea.partition(":")
        if not sep:
            raise ValueError(f"línea sin «clave: valor»: {linea.strip()!r}")
        clave, valor = clave.strip(), valor.split("#")[0].strip()
        if clave == "procedencia" and not valor:
            en_procedencia = True
            continue
        campos[clave] = valor
    return campos, procedencia


def _construir(campos: dict[str, str], proc: dict[str, str], cuerpo: str) -> Fragmento:
    """Arma el `Fragmento`. Lanza `KeyError` o `ValueError` si falta algo."""
    for obligatorio in ("identificador", "nivel_apos", "registro_duval"):
        if obligatorio not in campos:
            raise KeyError(f"falta el campo obligatorio «{obligatorio}»")
    if not proc:
        raise KeyError("falta «procedencia», que `DD-15` §Corpus exige")
    for obligatorio in ("obra", "pagina"):
        if obligatorio not in proc:
            raise KeyError(f"falta «procedencia.{obligatorio}»")
    try:
        pagina = int(proc["pagina"])
    except ValueError as exc:
        raise ValueError(f"página no numérica: {proc['pagina']!r}") from exc

    # `DD-21` · página aproximada. Ausente significa que `pagina` es exacta; no
    # se infiere ni se rellena por defecto, porque el valor por defecto sería
    # justo la afirmación que la decisión quiere evitar: dar por exacta una
    # página que no lo es.
    pagina_hasta = None
    if "pagina_hasta" in proc:
        try:
            pagina_hasta = int(proc["pagina_hasta"])
        except ValueError as exc:
            raise ValueError(
                f"«procedencia.pagina_hasta» no numérica: {proc['pagina_hasta']!r}"
            ) from exc

    return Fragmento(
        identificador=campos["identificador"],
        texto=cuerpo.strip(),
        nivel_apos=campos["nivel_apos"],
        registro_duval=campos["registro_duval"],
        concepcion_asociada=campos.get("concepcion_asociada") or None,
        nodo_grafo=campos.get("nodo_grafo") or None,
        procedencia=Procedencia(
            obra=proc["obra"],
            pagina=pagina,
            pagina_hasta=pagina_hasta,
            captura=proc.get("captura", "mixta"),
        ),
    )


def cargar(directorio: Path, obras: frozenset[str] | None = None) -> ResultadoDeCarga:
    """Lee todos los `.md` del directorio y devuelve fragmentos y fallos.

    `obras` es el catálogo contra el que se comprueba la procedencia. Si se
    omite, la comprobación de pertenencia se salta y **se dice en los fallos**:
    saltarla en silencio dejaría entrar fragmentos que citan obras inexistentes,
    y son precisamente los que después no se pueden retirar.
    """
    fragmentos: list[Fragmento] = []
    fallos: list[str] = []
    excluidos: list[str] = []
    vistos: dict[str, str] = {}

    if not directorio.is_dir():
        return ResultadoDeCarga(fallos=(f"no existe el directorio {directorio}",))

    for ruta in sorted(directorio.glob("*.md")):
        try:
            cabecera, cuerpo = _partir(ruta.read_text(encoding="utf-8"))
            campos, proc = _leer_cabecera(cabecera)
            fragmento = _construir(campos, proc, cuerpo)
        except (ValueError, KeyError) as exc:
            fallos.append(f"{ruta.name}: {exc}")
            continue

        fallos.extend(f"{ruta.name}: {f}" for f in fragmento.validar())

        anterior = vistos.get(fragmento.identificador)
        if anterior:
            fallos.append(
                f"{ruta.name}: identificador «{fragmento.identificador}» "
                f"repetido, ya estaba en {anterior}"
            )
        vistos[fragmento.identificador] = ruta.name

        if obras is None:
            fallos.append(f"{ruta.name}: no se comprobó la obra, falta el catálogo")
        elif fragmento.procedencia.obra not in obras:
            fallos.append(
                f"{ruta.name}: la obra «{fragmento.procedencia.obra}» no está "
                f"en FUENTES.md"
            )

        # `DD-02`: la verificación matemática al ingerir es condición de
        # ingreso, no un fallo de lectura. `verificar-matematica.py --marcar`
        # solo escribe dos estados que cuentan como pasados —«verificado» y
        # «sin matemática» (un fragmento de prosa no tiene fórmula que
        # comprobar)—; lo que bloquea es la marca **ausente**, que es lo que
        # `PM-C08` llama «sin marca». Se cuenta y se nombra, nunca se salta en
        # silencio, y por eso vive en su propia lista, aparte de `fallos`, que
        # sí invalidaría `utilizable` sin que el archivo tenga ningún
        # problema real de forma.
        if not campos.get("verificacion_dd02", "").strip():
            excluidos.append(f"{fragmento.identificador} ({ruta.name})")
            continue

        fragmentos.append(fragmento)

    return ResultadoDeCarga(tuple(fragmentos), tuple(fallos), tuple(excluidos))


@dataclass(frozen=True)
class FragmentoLeido:
    """Un fragmento del disco **con su marca de verificación**, sin filtrar.

    `cargar()` existe para alimentar el índice y por eso aplica la condición de
    ingreso de `DD-02`: lo que no lleva `verificacion_dd02` no entra. La
    biblioteca de Fase 5 necesita lo contrario —ver **todo** lo que hay para
    poder auditarlo, y mostrar al estudiante en qué estado de verificación está
    lo que lee—, así que lee por aquí.

    Es una función aparte y no un parámetro de `cargar()` a propósito: un
    `incluir_no_verificados=True` mal puesto metería material sin verificar en
    el índice de recuperación, que es justo lo que `DD-02` impide.
    """

    fragmento: Fragmento
    #: Lo que dice la cabecera: `verificado`, `sin matemática` o cadena vacía
    #: cuando la marca falta. La cadena vacía **no** se traduce a un estado
    #: inventado; se muestra como «sin marca».
    verificacion_dd02: str
    #: Nombre del archivo del que salió, para poder señalarlo en un informe.
    archivo: str


@dataclass(frozen=True)
class ResultadoDeLectura:
    """Todo lo que hay en el directorio, leído y contado."""

    leidos: tuple[FragmentoLeido, ...] = ()
    fallos: tuple[str, ...] = ()
    #: Archivos `.md` que no se pudieron interpretar, con su nombre.
    ilegibles: tuple[str, ...] = ()


def leer_todos(directorio: Path) -> ResultadoDeLectura:
    """Lee **todos** los `.md` del directorio, verificados o no.

    No comprueba el catálogo de obras: eso lo hace quien construye la
    biblioteca, que es quien tiene el catálogo. Aquí sólo se lee y se dice qué
    no se pudo leer.
    """
    leidos: list[FragmentoLeido] = []
    fallos: list[str] = []
    ilegibles: list[str] = []

    if not directorio.is_dir():
        return ResultadoDeLectura(fallos=(f"no existe el directorio {directorio}",))

    for ruta in sorted(directorio.glob("*.md")):
        try:
            cabecera, cuerpo = _partir(ruta.read_text(encoding="utf-8"))
            campos, proc = _leer_cabecera(cabecera)
            fragmento = _construir(campos, proc, cuerpo)
        except (ValueError, KeyError) as exc:
            fallos.append(f"{ruta.name}: {exc}")
            ilegibles.append(ruta.name)
            continue

        fallos.extend(f"{ruta.name}: {f}" for f in fragmento.validar())
        leidos.append(
            FragmentoLeido(
                fragmento=fragmento,
                verificacion_dd02=campos.get("verificacion_dd02", "").strip(),
                archivo=ruta.name,
            )
        )

    return ResultadoDeLectura(tuple(leidos), tuple(fallos), tuple(ilegibles))
