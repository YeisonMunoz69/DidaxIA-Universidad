from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from adaptadores.salientes.corpus.cargador import FragmentoLeido, leer_todos
from dominio.puertos.biblioteca import (
    Canal,
    Disponibilidad,
    Indisponible,
    Localizacion,
    MotivoIndisponible,
    Obra,
    Parte,
    Permiso,
    clave_de_obra_valida,
    identificador_de_fragmento_valido,
    identificador_de_parte_valido,
    nombre_de_archivo_admisible,
)


@dataclass(frozen=True)
class FichaDeFragmento:

    fragmento: FragmentoLeido
    obra: Obra

    localizacion: Localizacion | None = None
    motivo_sin_localizacion: MotivoIndisponible | None = None

@dataclass(frozen=True)
class InformeDelCatalogo:

    obras: int = 0
    partes: int = 0
    fragmentos: int = 0
    fallos: tuple[str, ...] = ()

    sin_fila_de_permiso: tuple[str, ...] = ()

    obras_md_presente: bool = False

@dataclass(frozen=True)
class DatosDelCatalogo:

    obras: dict[str, Obra]
    partes: dict[str, Parte]
    desfases: dict[str, int | None]
    pdf_completo: dict[str, str]
    fragmentos: dict[str, FragmentoLeido]

class CatalogoDeFuentes:

    def __init__(
        self, raiz_corpus: Path, datos: DatosDelCatalogo, informe: InformeDelCatalogo
    ) -> None:
        self._raiz = Path(raiz_corpus)
        self._obras = dict(datos.obras)
        self._partes = dict(datos.partes)
        self._desfases = dict(datos.desfases)
        self._pdf_completo = dict(datos.pdf_completo)
        self._fragmentos = dict(datos.fragmentos)
        self.informe = informe

    @classmethod
    def desde_directorio(cls, raiz_corpus: Path) -> CatalogoDeFuentes:
        raiz = Path(raiz_corpus)
        fallos: list[str] = []

        obras, sin_fila = _leer_obras(raiz / "fuentes.json", fallos)
        partes, desfases, pdf_completo = _leer_partes(raiz / "partes.json", obras.keys(), fallos)
        fragmentos = _leer_fragmentos(raiz / "fragmentos", obras.keys(), fallos)

        obras_md = raiz / "_obras-md"
        informe = InformeDelCatalogo(
            obras=len(obras),
            partes=len(partes),
            fragmentos=len(fragmentos),
            fallos=tuple(fallos),
            sin_fila_de_permiso=tuple(sorted(sin_fila)),
            obras_md_presente=obras_md.is_dir(),
        )
        return cls(
            raiz,
            DatosDelCatalogo(obras, partes, desfases, pdf_completo, fragmentos),
            informe,
        )

    def obras(self) -> tuple[Obra, ...]:
        return tuple(self._obras[c] for c in sorted(self._obras))

    def obra(self, clave: str) -> Obra:
        if not clave_de_obra_valida(clave):
            raise Indisponible(
                MotivoIndisponible.RECURSO_NO_CATALOGADO,
                f"«{clave}» no tiene forma de clave de obra",
            )
        obra = self._obras.get(clave)
        if obra is None:
            raise Indisponible(
                MotivoIndisponible.RECURSO_NO_CATALOGADO,
                f"la obra «{clave}» no está en el catálogo de obras",
            )
        return obra

    def parte(self, identificador: str) -> Parte:
        if not identificador_de_parte_valido(identificador):
            raise Indisponible(
                MotivoIndisponible.RECURSO_NO_CATALOGADO,
                f"«{identificador}» no tiene forma de identificador de parte",
            )
        parte = self._partes.get(identificador)
        if parte is None:
            raise Indisponible(
                MotivoIndisponible.RECURSO_NO_CATALOGADO,
                f"la parte «{identificador}» no está en el catálogo de partes",
            )
        return parte

    def partes_de(self, clave: str) -> tuple[Parte, ...]:
        self.obra(clave)
        return tuple(
            sorted(
                (p for p in self._partes.values() if p.obra == clave),
                key=lambda p: (p.pagina_impresa_inicial, p.identificador),
            )
        )

    def localizar(
        self, clave: str, pagina_impresa: int, pagina_hasta: int | None = None
    ) -> Localizacion:

        self.obra(clave)
        if pagina_impresa < 1:
            raise Indisponible(
                MotivoIndisponible.PAGINA_SIN_MAPEO,
                f"la numeración empieza en 1 y llegó {pagina_impresa}",
            )

        partes = self.partes_de(clave)
        if not partes:

            raise Indisponible(
                MotivoIndisponible.RECURSO_NO_CATALOGADO,
                f"«{clave}» no tiene ninguna parte catalogada",
            )

        for parte in partes:
            if parte.contiene(pagina_impresa):
                return Localizacion(
                    obra=clave,
                    parte=parte.identificador,
                    pagina_impresa=pagina_impresa,
                    pagina_interna_en_parte=(pagina_impresa - parte.pagina_impresa_inicial + 1),
                    pagina_interna_en_obra=self._pagina_en_obra(clave, pagina_impresa),
                    pagina_impresa_hasta=pagina_hasta,
                )

        raise Indisponible(
            MotivoIndisponible.PAGINA_SIN_MAPEO,
            f"ninguna parte catalogada de «{clave}» contiene la página impresa {pagina_impresa}",
        )

    def desfase_medido(self, clave: str) -> bool:
        return self._desfases.get(clave) is not None

    def _pagina_en_obra(self, clave: str, pagina_impresa: int) -> int | None:
        desfase = self._desfases.get(clave)
        if desfase is None:
            return None
        interna = pagina_impresa + desfase
        return interna if interna >= 1 else None

    def disponibilidad(self, clave: str, canal: Canal) -> Disponibilidad:
        obra = self.obra(clave)
        permiso = obra.permiso_de(canal)

        if canal is Canal.FRAGMENTO:

            hay = any(f.fragmento.procedencia.obra == clave for f in self._fragmentos.values())
            return Disponibilidad(canal, permiso, catalogado=hay, archivo_presente=hay)

        partes = self.partes_de(clave)
        if canal is Canal.PDF_COMPLETO:

            ruta = self.ruta_del_pdf_completo(clave)
            return Disponibilidad(
                canal,
                permiso,
                catalogado=bool(self._pdf_completo.get(clave)),
                archivo_presente=ruta is not None,
            )

        catalogado = any(
            p.archivo_markdown if canal is Canal.MARKDOWN_CONTINUO else p.archivo_pdf
            for p in partes
        )
        presente = any(self.ruta_de_parte(p, canal) is not None for p in partes)
        return Disponibilidad(canal, permiso, catalogado=catalogado, archivo_presente=presente)

    def ruta_del_pdf_completo(self, clave: str) -> Path | None:
        nombre = self._pdf_completo.get(clave, "")
        if not nombre or not nombre_de_archivo_admisible(nombre):
            return None
        if not clave_de_obra_valida(clave):
            return None
        base = (self._raiz / "_obras").resolve()
        ruta = (base / nombre).resolve()
        if not ruta.is_file() or base not in ruta.parents:
            return None
        return ruta

    def ruta_de_parte(self, parte: Parte, canal: Canal) -> Path | None:
        nombre = parte.archivo_markdown if canal is Canal.MARKDOWN_CONTINUO else parte.archivo_pdf
        if not nombre or not nombre_de_archivo_admisible(nombre):
            return None
        if not clave_de_obra_valida(parte.obra):
            return None

        carpeta = "_obras-md" if canal is Canal.MARKDOWN_CONTINUO else "_obras"
        base = (self._raiz / carpeta / parte.obra).resolve()
        ruta = (base / nombre).resolve()

        if not ruta.is_file() or base not in ruta.parents:
            return None
        return ruta

    def fragmentos(self) -> tuple[FragmentoLeido, ...]:
        return tuple(self._fragmentos[i] for i in sorted(self._fragmentos))

    def titulo_de_fragmento(self, identificador: str) -> str:
        leido = self._fragmentos.get(identificador)
        if leido is None:
            return identificador
        obra = self._obras.get(leido.fragmento.procedencia.obra)
        nombre = (obra.autoria if obra else "") or leido.fragmento.procedencia.obra
        procedencia = leido.fragmento.procedencia
        if procedencia.exacta:
            return f"{nombre}, página {procedencia.pagina}"
        return f"{nombre}, páginas {procedencia.pagina}–{procedencia.pagina_hasta}"

    def ficha_de_fragmento(self, identificador: str) -> FichaDeFragmento:
        if not identificador_de_fragmento_valido(identificador):
            raise Indisponible(
                MotivoIndisponible.FRAGMENTO_INEXISTENTE,
                f"«{identificador}» no tiene forma de identificador de fragmento",
            )
        leido = self._fragmentos.get(identificador)
        if leido is None:

            raise Indisponible(
                MotivoIndisponible.FRAGMENTO_INEXISTENTE,
                f"no hay ningún fragmento «{identificador}»",
            )

        procedencia = leido.fragmento.procedencia
        obra = self.obra(procedencia.obra)
        try:
            localizacion = self.localizar(
                procedencia.obra, procedencia.pagina, procedencia.pagina_hasta
            )
            motivo = None
        except Indisponible as exc:
            localizacion, motivo = None, exc.motivo
        return FichaDeFragmento(leido, obra, localizacion, motivo)

def _leer_objeto(ruta: Path, fallos: list[str]) -> dict:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if not isinstance(datos, dict):
            raise ValueError("se esperaba un objeto JSON")
    except (OSError, ValueError) as exc:
        fallos.append(f"no se pudo leer {ruta.name}: {exc}")
        return {}
    return datos

def _leer_obras(ruta: Path, fallos: list[str]) -> tuple[dict[str, Obra], set[str]]:
    obras = {}
    sin_fila = set()
    for clave, datos in _leer_objeto(ruta, fallos).items():
        if not clave_de_obra_valida(clave) or not isinstance(datos, dict):
            fallos.append(f"{ruta.name}: ficha inválida para «{clave}»")
            continue
        permisos = datos.get("permisos")
        if not isinstance(permisos, dict):
            sin_fila.add(clave)
            fallos.append(f"{ruta.name}: «{clave}» carece de permisos por canal")
            permisos = {}
        disponibilidad = {}
        for canal in Canal:
            origen = Canal.PDF_COMPLETO if canal is Canal.PDF_DIVIDIDO else canal
            try:
                permiso = Permiso(permisos.get(origen, Permiso.BLOQUEADO))
            except ValueError:
                fallos.append(f"{ruta.name}: permiso inválido para «{clave}» en {origen}")
                permiso = Permiso.BLOQUEADO
            disponibilidad[canal] = Disponibilidad(canal, permiso)
        titulo = datos.get("titulo", "")
        autoria = datos.get("autoria", "")
        paginas = datos.get("paginas_del_archivo")
        if not isinstance(titulo, str) or not isinstance(autoria, str) or (
            paginas is not None and (type(paginas) is not int or paginas < 1)
        ):
            fallos.append(f"{ruta.name}: metadatos inválidos para «{clave}»")
            continue
        obra = Obra(clave, titulo, autoria, paginas, disponibilidad=disponibilidad)
        problemas = obra.validar()
        if problemas:
            fallos.extend(problemas)
            continue
        obras[clave] = obra
    return obras, sin_fila

def _leer_partes(
    ruta: Path, claves: object, fallos: list[str]
) -> tuple[dict[str, Parte], dict[str, int | None], dict[str, str]]:
    datos = _leer_objeto(ruta, fallos)
    partes = {}
    desfases = {}
    pdf_completo = {}
    conocidas = set(claves)
    filas = datos.get("partes", [])
    paginas = datos.get("desfases", {})
    archivos = datos.get("pdf_completo", {})
    if not isinstance(filas, list) or not isinstance(paginas, dict) or not isinstance(archivos, dict):
        fallos.append(f"{ruta.name}: formato de catálogo inválido")
        return partes, desfases, pdf_completo

    for clave, valor in paginas.items():
        if clave in conocidas and (valor is None or type(valor) is int):
            desfases[clave] = valor
        else:
            fallos.append(f"{ruta.name}: desfase inválido para «{clave}»")

    for clave, nombre in archivos.items():
        if clave in conocidas and isinstance(nombre, str) and (
            not nombre or nombre_de_archivo_admisible(nombre)
        ):
            pdf_completo[clave] = nombre
        else:
            fallos.append(f"{ruta.name}: PDF completo inválido para «{clave}»")

    for fila in filas:
        try:
            parte = Parte(**fila)
            problemas = parte.validar()
            if parte.obra not in conocidas:
                problemas.append(f"«{parte.identificador}» cita una obra desconocida")
            if parte.identificador in partes:
                problemas.append(f"parte repetida «{parte.identificador}»")
        except (AttributeError, TypeError):
            problemas = ["fila de parte inválida"]
        if problemas:
            fallos.extend(f"{ruta.name}: {problema}" for problema in problemas)
            continue
        partes[parte.identificador] = parte

    return partes, desfases, pdf_completo

def _leer_fragmentos(
    directorio: Path, claves: object, fallos: list[str]
) -> dict[str, FragmentoLeido]:

    conocidas = set(claves)
    lectura = leer_todos(directorio)
    fallos.extend(lectura.fallos)

    indice: dict[str, FragmentoLeido] = {}
    for leido in lectura.leidos:
        identificador = leido.fragmento.identificador
        if identificador in indice:
            fallos.append(f"identificador repetido «{identificador}» en {leido.archivo}")
            continue
        if conocidas and leido.fragmento.procedencia.obra not in conocidas:
            fallos.append(
                f"{leido.archivo}: la obra «{leido.fragmento.procedencia.obra}» "
                f"no está en fuentes.json"
            )
            continue
        indice[identificador] = leido
    return indice
