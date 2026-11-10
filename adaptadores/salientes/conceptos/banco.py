from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


SECCIONES_PUBLICAS = (
    "Qué es",
    "La explicación",
    "Qué muestra la simulación",
)


SECCION_PREVIOS = "Qué hay que entender antes"


_CAMPOS = {
    "Identificador": "id",
    "Nodo del grafo": "nodo",
    "Concepción errónea asociada": "concepcion",
    "Estado": "estado",
}

_TITULO = re.compile(r"^#\s+(\S+)\s+·\s+(.+?)\s*$", re.M)
_FILA = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*$", re.M)
_SECCION = re.compile(r"^##\s+(.+?)\s*$", re.M)

_PREVIO = re.compile(r"^\|\s*`(C-[A-Za-z0-9-]+)`\s*\|\s*(.+?)\s*\|\s*$", re.M)


_IDENT_NODO = re.compile(r"N\d+")


_PALABRAS_VACIAS = {
    "ahi", "algo", "ante", "aqui", "cada", "como", "con", "cual", "cuando",
    "del", "desde", "donde", "dos", "el", "ella", "entre", "esa", "ese",
    "esta", "este", "esto", "hay", "las", "los", "mas", "mismo", "muy",
    "para", "pero", "por", "porque", "que", "ser", "sin", "solo", "son",
    "sus", "tambien", "tiene", "una", "uno", "unas", "unos",
}
_CODIGO_INTERNO = re.compile(r"\b(?:C-[A-Z0-9-]+|[NFM]-?\d+)\b", re.I)


def _normalizar_busqueda(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")

def _terminos_de_busqueda(concepto: "Concepto") -> list[str]:
    contenido = " ".join(
        [concepto.nombre, *(f"{titulo} {cuerpo}" for titulo, cuerpo in concepto.secciones)]
    )
    contenido = _CODIGO_INTERNO.sub(" ", contenido)
    palabras = re.findall(r"[a-záéíóúüñ]{3,}", contenido, flags=re.I)
    normalizadas = {_normalizar_busqueda(p) for p in palabras}
    return sorted(p for p in normalizadas if p not in _PALABRAS_VACIAS)

@dataclass(frozen=True)
class Concepto:

    identificador: str
    nombre: str
    nodo: str
    concepcion: str
    estado: str
    secciones: tuple[tuple[str, str], ...]
    previos: tuple[tuple[str, str], ...]

    def como_resumen(self) -> dict:
        return {
            "id": self.identificador,
            "nombre": self.nombre,
            "nodo": self.nodo,
            "estado": self.estado,
            "terminos_busqueda": _terminos_de_busqueda(self),
        }

    def como_ficha(self) -> dict:
        return {
            **self.como_resumen(),
            "concepcion": self.concepcion,
            "secciones": [{"titulo": t, "texto": c} for t, c in self.secciones],
            "previos": [{"id": i, "motivo": m} for i, m in self.previos],
        }

def _limpiar_estado(valor: str) -> str:
    sin_marcado = valor.replace("**", "").replace("`", "")
    return re.sub(r"^[^A-Za-zÁÉÍÓÚÑáéíóúñ]+", "", sin_marcado).strip()

def _sin_notas_al_equipo(cuerpo: str) -> str:
    lineas = [ln for ln in cuerpo.splitlines() if not ln.lstrip().startswith(">")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lineas))

def _secciones(texto: str) -> dict[str, str]:
    encontradas: dict[str, str] = {}
    marcas = list(_SECCION.finditer(texto))
    for i, m in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        cuerpo = texto[m.end():fin]

        cuerpo = re.split(r"^---\s*$", cuerpo, maxsplit=1, flags=re.M)[0]
        encontradas[m.group(1).strip()] = _sin_notas_al_equipo(cuerpo).strip()
    return encontradas

def leer(ruta: Path) -> Concepto | None:
    texto = ruta.read_text(encoding="utf-8")

    titulo = _TITULO.search(texto)
    if titulo is None:
        return None

    campos = {}
    for fila in _FILA.finditer(texto):
        clave = _CAMPOS.get(fila.group(1).strip())
        if clave:
            campos[clave] = fila.group(2).strip()

    todas = _secciones(texto)
    previos = [
        (m.group(1), m.group(2))
        for m in _PREVIO.finditer(todas.get(SECCION_PREVIOS, ""))
    ]

    return Concepto(
        identificador=campos.get("id", titulo.group(1)).replace("`", ""),
        nombre=titulo.group(2),

        nodo=(m.group(0) if (m := _IDENT_NODO.search(campos.get("nodo", ""))) else ""),
        concepcion=campos.get("concepcion", "").replace("`", ""),
        estado=_limpiar_estado(campos.get("estado", "")),
        secciones=tuple(
            (t, todas[t]) for t in SECCIONES_PUBLICAS if todas.get(t)
        ),
        previos=tuple(previos),
    )

class BancoDeConceptos:

    def __init__(self, carpeta: Path) -> None:
        self._por_id: dict[str, Concepto] = {}

        self._por_nodo: dict[str, list[Concepto]] = {}
        if not carpeta.is_dir():
            return
        for ruta in sorted(carpeta.glob("c-*.md")):
            concepto = leer(ruta)
            if concepto is not None:
                self._por_id[concepto.identificador.upper()] = concepto
                if concepto.nodo:
                    self._por_nodo.setdefault(concepto.nodo.upper(), []).append(concepto)

        for paginas in self._por_nodo.values():
            paginas.sort(key=lambda c: c.identificador)

    def __len__(self) -> int:
        return len(self._por_id)

    def listar(self) -> list[Concepto]:
        return sorted(self._por_id.values(), key=lambda c: c.identificador)

    def obtener(self, identificador: str) -> Concepto | None:
        return self._por_id.get((identificador or "").upper())

    def ficha(self, identificador: str) -> dict | None:
        concepto = self.obtener(identificador)
        if concepto is None:
            return None
        ficha = concepto.como_ficha()
        for previo in ficha["previos"]:
            relacionado = self.obtener(previo["id"])
            previo["nombre"] = relacionado.nombre if relacionado else "Concepto relacionado"
        return ficha

    def por_nodo(self, nodo: str) -> tuple[Concepto, ...]:
        return tuple(self._por_nodo.get((nodo or "").upper(), ()))
