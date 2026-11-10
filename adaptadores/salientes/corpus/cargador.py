from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from dominio.puertos.corpus import Fragmento, Procedencia


_CERCA = "---"


_CLAVE_EN_FUENTES = re.compile(r"^###\s+`([A-Z]{3})`", re.M)


@dataclass(frozen=True)
class ResultadoDeCarga:

    fragmentos: tuple[Fragmento, ...] = ()
    fallos: tuple[str, ...] = ()

    excluidos_por_dd02: tuple[str, ...] = ()

    @property
    def utilizable(self) -> bool:
        return bool(self.fragmentos) and not self.fallos

def claves_de_obra(ruta_fuentes: Path) -> frozenset[str]:
    if not ruta_fuentes.is_file():
        return frozenset()
    texto = ruta_fuentes.read_text(encoding="utf-8")
    if ruta_fuentes.suffix == ".md":
        return frozenset(_CLAVE_EN_FUENTES.findall(texto))
    fuentes = json.loads(texto)
    if not isinstance(fuentes, dict):
        raise ValueError("se esperaba un objeto JSON con las claves de obra")
    return frozenset(clave for clave in fuentes if re.fullmatch(r"[A-Z]{3}", clave))

def _partir(texto: str) -> tuple[str, str]:
    if not texto.lstrip().startswith(_CERCA):
        raise ValueError("no empieza con una cabecera de metadatos")
    partes = texto.lstrip().split(_CERCA, 2)
    if len(partes) < 3:
        raise ValueError("la cabecera de metadatos no está cerrada")
    return partes[1], partes[2]

def _leer_cabecera(cabecera: str) -> tuple[dict[str, str], dict[str, str]]:
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
                f"en el catálogo de fuentes"
            )

        if not campos.get("verificacion_dd02", "").strip():
            excluidos.append(f"{fragmento.identificador} ({ruta.name})")
            continue

        fragmentos.append(fragmento)

    return ResultadoDeCarga(tuple(fragmentos), tuple(fallos), tuple(excluidos))

@dataclass(frozen=True)
class FragmentoLeido:

    fragmento: Fragmento

    verificacion_dd02: str

    archivo: str

@dataclass(frozen=True)
class ResultadoDeLectura:

    leidos: tuple[FragmentoLeido, ...] = ()
    fallos: tuple[str, ...] = ()

    ilegibles: tuple[str, ...] = ()

def leer_todos(directorio: Path) -> ResultadoDeLectura:
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
