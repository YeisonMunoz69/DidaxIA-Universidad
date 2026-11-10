import re

_OFERTA = re.compile(
    r"(?:quieres|deseas|te\s+muestre|segur[oa]).{0,100}"
    r"(?:soluci[oó]n|desarrollo|resuelt[oa]|resolverlo|verlo\s+completo).{0,60}\?",
    re.I,
)
_ACEPTA = re.compile(
    r"^\s*(?:s[ií](?:\s*,?\s*por\s+favor)?(?:\s*,?\s*(?:mu[eé]stramelo|"
    r"resu[eé]lvelo|ens[eé]ñamelo|quiero\s+(?:verlo|la\s+soluci[oó]n)))?|"
    r"confirmo|adelante\s*,?\s*mu[eé]stramelo)[.!\s]*$", re.I,
)


def confirma_oferta(texto: str, historial: tuple[dict, ...]) -> bool:
    if not historial or not _ACEPTA.fullmatch(texto):
        return False
    ultimo = str(historial[-1].get("tutor", ""))
    return bool(_OFERTA.search(ultimo))

def base_de_ejercicio(activo: dict | None) -> str:
    if not activo or not activo.get("expresion"):
        return ""
    if activo.get("_tarea_id"):
        return "tarea:" + activo["_tarea_id"]
    expresion = str(activo["expresion"])
    if activo.get("tipo") == "limite":
        return f"lim {activo.get('variable', 'x')}->{activo.get('destino', '')} {expresion}"
    if activo.get("tipo") == "valor_derivada":
        return f"valor_derivada {activo.get('variable', 'x')}={activo.get('destino', '')} {expresion}"
    return f"{activo.get('tipo', 'calculo')} {expresion}"
