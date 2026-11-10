from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from adaptadores.salientes.biblioteca.catalogo import CatalogoDeFuentes
from dominio.puertos.biblioteca import Canal, Permiso


_NOMBRE_DE_FRAGMENTO = re.compile(r"^f-(\d{3})\.md$")


@dataclass
class InventarioDeObra:

    clave: str
    titulo: str
    fragmentos: int = 0

    pagina_minima: int | None = None
    pagina_maxima: int | None = None

    paginas_exactas: int = 0
    paginas_en_rango: int = 0

    permisos: dict[str, str] = field(default_factory=dict)
    partes_catalogadas: int = 0
    partes_con_markdown_presente: int = 0
    partes_con_pdf_presente: int = 0
    pdf_completo_presente: bool = False

    desfase_medido: bool = False

@dataclass
class Inventario:

    raiz: str = ""
    archivos_md: int = 0
    fragmentos_leidos: int = 0
    identificadores_unicos: int = 0
    identificador_minimo: str = ""
    identificador_maximo: str = ""

    ausentes_en_el_rango: list[str] = field(default_factory=list)
    duplicados: list[str] = field(default_factory=list)

    nombre_desalineado: list[str] = field(default_factory=list)

    ilegibles: list[str] = field(default_factory=list)

    huerfanos: list[str] = field(default_factory=list)

    sin_marca_dd02: list[str] = field(default_factory=list)

    fuera_del_catalogo: list[str] = field(default_factory=list)

    enlaces: list[str] = field(default_factory=list)

    capturas: dict[str, int] = field(default_factory=dict)
    obras: list[InventarioDeObra] = field(default_factory=list)

    directorios_ausentes: list[str] = field(default_factory=list)

    canales_autorizados: int = 0
    fallos_del_catalogo: list[str] = field(default_factory=list)

    def como_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True)

def _enlaces_bajo(raiz: Path) -> list[str]:
    _REPARSE = 0x400
    hallados: list[str] = []
    if not raiz.is_dir():
        return hallados
    for actual, directorios, archivos in os.walk(raiz):
        for nombre in list(directorios) + list(archivos):
            ruta = Path(actual) / nombre
            try:
                if ruta.is_symlink():
                    hallados.append(str(ruta.relative_to(raiz)))
                    continue
                atributos = getattr(ruta.lstat(), "st_file_attributes", 0)
                if atributos & _REPARSE:
                    hallados.append(str(ruta.relative_to(raiz)))
            except OSError:
                continue
    return hallados

def auditar(raiz_corpus: Path) -> Inventario:
    raiz = Path(raiz_corpus)
    catalogo = CatalogoDeFuentes.desde_directorio(raiz)
    inventario = Inventario(
        raiz=str(raiz),
        fallos_del_catalogo=list(catalogo.informe.fallos),
    )

    directorio = raiz / "fragmentos"
    if not directorio.is_dir():
        inventario.directorios_ausentes.append(str(directorio))
        return inventario

    _auditar_fragmentos(directorio, catalogo, inventario)
    _auditar_obras(catalogo, inventario)
    _auditar_entorno(raiz, inventario)
    return inventario

def _auditar_fragmentos(
    directorio: Path, catalogo: CatalogoDeFuentes, inventario: Inventario
) -> None:

    for ruta in sorted(directorio.iterdir()):
        if ruta.is_dir():
            inventario.huerfanos.append(ruta.name + "/")
        elif ruta.suffix != ".md" or not _NOMBRE_DE_FRAGMENTO.match(ruta.name):
            inventario.huerfanos.append(ruta.name)
        else:
            inventario.archivos_md += 1

    numeros: list[int] = []
    vistos: Counter[str] = Counter()
    capturas: Counter[str] = Counter()

    for leido in catalogo.fragmentos():
        identificador = leido.fragmento.identificador
        vistos[identificador] += 1
        if leido.archivo != identificador.lower() + ".md":
            inventario.nombre_desalineado.append(f"{leido.archivo} declara {identificador}")
        numeros.append(int(identificador.split("-")[1]))
        capturas[leido.fragmento.procedencia.captura] += 1
        if not leido.verificacion_dd02:
            inventario.sin_marca_dd02.append(identificador)

    inventario.fragmentos_leidos = len(catalogo.fragmentos())
    inventario.identificadores_unicos = len(vistos)
    inventario.duplicados = sorted(i for i, n in vistos.items() if n > 1)
    inventario.capturas = dict(sorted(capturas.items()))

    if numeros:
        inventario.identificador_minimo = f"F-{min(numeros):03d}"
        inventario.identificador_maximo = f"F-{max(numeros):03d}"
        presentes = set(numeros)

        inventario.ausentes_en_el_rango = [
            f"F-{n:03d}"
            for n in range(min(numeros), max(numeros) + 1)
            if n not in presentes
        ]

    inventario.ilegibles = [
        f for f in inventario.fallos_del_catalogo if "no está en fuentes.json" not in f
    ]
    inventario.fuera_del_catalogo = [
        f for f in inventario.fallos_del_catalogo if "no está en fuentes.json" in f
    ]

def _auditar_obras(catalogo: CatalogoDeFuentes, inventario: Inventario) -> None:
    por_obra: dict[str, list] = {}
    for leido in catalogo.fragmentos():
        por_obra.setdefault(leido.fragmento.procedencia.obra, []).append(leido)

    autorizados = 0
    for obra in catalogo.obras():
        suyos = por_obra.get(obra.clave, [])
        paginas = [x.fragmento.procedencia.pagina for x in suyos]
        partes = catalogo.partes_de(obra.clave)
        inventario.obras.append(
            InventarioDeObra(
                clave=obra.clave,
                titulo=obra.titulo,
                fragmentos=len(suyos),
                pagina_minima=min(paginas) if paginas else None,
                pagina_maxima=max(paginas) if paginas else None,
                paginas_exactas=sum(1 for x in suyos if x.fragmento.procedencia.exacta),
                paginas_en_rango=sum(
                    1 for x in suyos if not x.fragmento.procedencia.exacta
                ),
                permisos={c.value: obra.permiso_de(c).value for c in Canal},
                partes_catalogadas=len(partes),
                partes_con_markdown_presente=sum(
                    1 for p in partes if catalogo.ruta_de_parte(p, Canal.MARKDOWN_CONTINUO)
                ),
                partes_con_pdf_presente=sum(
                    1 for p in partes if catalogo.ruta_de_parte(p, Canal.PDF_DIVIDIDO)
                ),
                pdf_completo_presente=catalogo.disponibilidad(
                    obra.clave, Canal.PDF_COMPLETO
                ).archivo_presente,
                desfase_medido=catalogo.desfase_medido(obra.clave),
            )
        )
        autorizados += sum(1 for c in Canal if obra.permiso_de(c) is Permiso.PERMITIDO)

    inventario.canales_autorizados = autorizados

def _auditar_entorno(raiz: Path, inventario: Inventario) -> None:
    for nombre in ("_obras", "_obras-md"):
        if not (raiz / nombre).is_dir():
            inventario.directorios_ausentes.append(str(raiz / nombre))
    inventario.enlaces = _enlaces_bajo(raiz)

def como_texto(inventario: Inventario) -> str:
    lineas = [
        "INVENTARIO DEL CORPUS · sólo lectura",
        f"raíz: {inventario.raiz}",
        "",
        "FRAGMENTOS",
        f"  archivos .md con nombre válido : {inventario.archivos_md}",
        f"  fragmentos leídos              : {inventario.fragmentos_leidos}",
        f"  identificadores únicos         : {inventario.identificadores_unicos}",
        f"  rango                          : {inventario.identificador_minimo}"
        f"–{inventario.identificador_maximo}",
        f"  ausentes dentro del rango      : {', '.join(inventario.ausentes_en_el_rango) or '(ninguno)'}",
        f"  duplicados                     : {', '.join(inventario.duplicados) or '(ninguno)'}",
        f"  nombre desalineado             : {len(inventario.nombre_desalineado)}",
        f"  ilegibles                      : {len(inventario.ilegibles)}",
        f"  huérfanos en el directorio     : {', '.join(inventario.huerfanos) or '(ninguno)'}",
        f"  sin marca DD-02 (no indexados) : {len(inventario.sin_marca_dd02)}",
        f"  citan obra fuera del catálogo  : {len(inventario.fuera_del_catalogo)}",
        f"  modos de captura               : {inventario.capturas}",
        "",
        "OBRAS",
    ]
    for o in inventario.obras:
        lineas += [
            f"  {o.clave} · {o.titulo[:58]}",
            f"      fragmentos {o.fragmentos:>3} · páginas impresas "
            f"{o.pagina_minima}–{o.pagina_maxima} "
            f"(exactas {o.paginas_exactas}, en rango {o.paginas_en_rango})",
            f"      desfase medido: {'sí' if o.desfase_medido else 'NO'} · "
            f"partes catalogadas {o.partes_catalogadas} "
            f"(markdown presente {o.partes_con_markdown_presente}, "
            f"pdf presente {o.partes_con_pdf_presente}) · "
            f"pdf completo presente: {'sí' if o.pdf_completo_presente else 'no'}",
            f"      permisos: {o.permisos}",
        ]
    lineas += [
        "",
        "PUERTA DE PUBLICACIÓN",
        f"  canales autorizados en total   : {inventario.canales_autorizados}",
        "",
        "ENTORNO",
        f"  directorios ausentes           : {', '.join(inventario.directorios_ausentes) or '(ninguno)'}",
        f"  enlaces / uniones bajo el corpus: {', '.join(inventario.enlaces) or '(ninguno)'}",
        "",
        "FALLOS DEL CATÁLOGO",
    ]
    lineas += [f"  · {f}" for f in inventario.fallos_del_catalogo] or ["  (ninguno)"]
    return "\n".join(lineas)
