PALETAS = frozenset(["ambar", "zafiro", "electrico", "esmeralda", "jade", "amatista", "indigo", "rubi", "coral", "ocre", "terracota", "turquesa", "orquidea", "caramelo", "grafito", "vinotinto", "salvia", "lino", "oliva", "lavanda", "noche", "oceano", "bosque", "ciruela", "cobre", "cereza"])
COLORES = frozenset(
    parte + modo for modo in ("Claro", "Oscuro")
    for parte in ("main", "hover", "light", "surface", "surfaceHover", "glow", "gradient", "contraste")
)
PORCENTAJES = {"intensidadFondoConversacion", "opacidadPregunta", "opacidadRespuesta"}
CAMPOS = COLORES | PORCENTAJES | {"paleta", "tema", "escalaTexto", "animaciones", "fondoConversacion"}


def validar_cambios(cambios):
    if not isinstance(cambios, dict) or not cambios or set(cambios) - CAMPOS:
        raise ValueError("preferencias desconocidas o vacías")
    for clave, valor in cambios.items():
        if clave in COLORES and (not isinstance(valor, str) or valor not in PALETAS):
            raise ValueError("elige un tono del catálogo")
        if clave == "paleta" and (not isinstance(valor, str) or valor not in PALETAS):
            raise ValueError("paleta no admisible")
        if clave == "tema" and valor not in ("sistema", "claro", "oscuro"):
            raise ValueError("tema no admisible")
        if clave == "escalaTexto" and valor not in ("normal", "comoda", "grande"):
            raise ValueError("escala no admisible")
        if clave in ("animaciones", "fondoConversacion") and type(valor) is not bool:
            raise ValueError("movimiento no admisible")
        if clave in PORCENTAJES and (type(valor) is not int or not 0 <= valor <= 100):
            raise ValueError("porcentaje no admisible")
    return dict(cambios)

class RevisionDesactualizada(ValueError):
    pass
