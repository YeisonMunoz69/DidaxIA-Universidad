from __future__ import annotations

import re

from dominio.diagnostico.clasificador import OpcionRazon
from dominio.puertos.plantillas import ItemDosNiveles


_SECCION = re.compile(r"^###\s+", re.M)


_NODO_DE_SECCION = re.compile(r"\|\s*\*\*Nodo\*\*\s*\|\s*`(N\d{2})`", re.I)


_CORRIENTE = re.compile(r"notaci[óo]n\s+corriente\*\*\s*\|\s*`([^`]+)`", re.I)


_PRIMERA_CITA = re.compile(r"^>\s*(.+)$", re.M)


_FORMULA = re.compile(r"\$([^$]+)\$")


_FILA_DE_OPCION = re.compile(r"^\|\s*\*\*([a-z])\*\*\s*\|(.*)$", re.M)


_ENTRECOMILLADO = re.compile(r"«([^»]+)»")


_CONCEPCION = re.compile(r"\bM(\d{2})\b")


_FUNCIONES = {
    r"\sin": "sen", r"\cos": "cos", r"\tan": "tan",
    r"\ln": "ln", r"\log": "log", r"\sqrt": "sqrt",
}


_ADORNOS = (r"\left", r"\right", r"\,", r"\;", r"\!", r"\ ")


_POTENCIA_DE_FUNCION = re.compile(
    r"\b(sen|sin|cos|tan|ln|log)\^\{?(\d+)\}?\s*([a-zA-Z])(?![\w(])"
)


_FUNCION_SIN_PARENTESIS = re.compile(r"\b(sen|sin|cos|tan|ln|log)\s+([a-zA-Z])(?![\w(])")


_YUXTAPOSICION = re.compile(r"(?<=[\w)\]])\s+(?=[\w(\[])")


_ADMISIBLE = re.compile(r"^[A-Za-z0-9+\-*/^() ]+$")


def _a_notacion_corriente(formula: str) -> str:
    texto = formula.strip()

    if texto.count("=") == 1:
        texto = texto.split("=", 1)[1]
    for adorno in _ADORNOS:
        texto = texto.replace(adorno, " ")
    for latex, corriente in _FUNCIONES.items():
        texto = texto.replace(latex, corriente)

    texto = _POTENCIA_DE_FUNCION.sub(r"\1(\3)^\2", texto)
    texto = _FUNCION_SIN_PARENTESIS.sub(r"\1(\2)", texto)
    texto = _YUXTAPOSICION.sub("*", texto)
    texto = " ".join(texto.split())

    if not texto or not _ADMISIBLE.match(texto):
        return ""
    return texto

def _sin_latex(texto: str) -> str:
    salida = texto
    for formula in _FORMULA.findall(texto):
        corriente = _a_notacion_corriente(formula)
        if not corriente:
            return ""
        salida = salida.replace(f"${formula}$", corriente)
    return salida

def _limpiar(celda: str) -> str:
    limpia = " ".join(celda.split()).strip()
    for adorno in ("**", "`"):
        limpia = limpia.replace(adorno, "")
    entrecomillada = _ENTRECOMILLADO.search(limpia)
    if entrecomillada is not None:
        limpia = entrecomillada.group(1)

    return _sin_latex(limpia.strip("* ").strip())

def _opciones(texto: str) -> tuple[OpcionRazon, ...]:
    salida: list[OpcionRazon] = []
    for letra, resto in _FILA_DE_OPCION.findall(texto):
        celdas = [c.strip() for c in resto.split("|") if c.strip()]

        delata = _CONCEPCION.search(celdas[-1]) if celdas else None
        salida.append(
            OpcionRazon(
                identificador=letra,
                es_correcta=delata is None,
                concepcion=f"M{delata.group(1)}" if delata else None,
                texto=_limpiar(celdas[0]) if len(celdas) >= 2 else "",
            )
        )
    return tuple(salida)

def _enunciado(texto: str) -> str:
    cita = _PRIMERA_CITA.search(texto)
    if cita is None:
        return ""
    return _limpiar(cita.group(1))

def _derivar(seccion: str) -> str:
    declarada = _CORRIENTE.search(seccion)
    if declarada is not None:
        texto = " ".join(declarada.group(1).split())
        return texto if _ADMISIBLE.match(texto) else ""

    cita = _PRIMERA_CITA.search(seccion)
    formula = _FORMULA.search(cita.group(1)) if cita else None
    return _a_notacion_corriente(formula.group(1)) if formula else ""

def items_desde_texto(texto: str) -> tuple[ItemDosNiveles, ...]:
    salida: list[ItemDosNiveles] = []
    for seccion in _SECCION.split(texto)[1:]:
        nodo = _NODO_DE_SECCION.search(seccion)
        if nodo is None:
            continue
        salida.append(
            ItemDosNiveles(
                nodo=nodo.group(1).upper(),
                derivar=_derivar(seccion),
                opciones=_opciones(seccion),
                enunciado=_enunciado(seccion),
            )
        )
    return tuple(salida)
