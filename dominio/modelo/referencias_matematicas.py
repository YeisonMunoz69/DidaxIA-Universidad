import re

from dominio.modelo.notacion_entrada import normalizar_frase_matematica

_DECLARACION = re.compile(r"\b([a-zA-Z])\s*\(\s*([a-zA-Z])\s*\)\s*(?:=|igual(?:\s+a)?\b)\s*")
_FUNCIONES = {"sin", "sen", "cos", "tan", "asin", "acos", "atan", "arctan", "sec", "csc", "cot", "exp", "ln", "log", "sqrt", "abs", "pi", "e", "E", "frac", "left", "right", "cdot", "times"}


def formula_acotada(texto, variable="x"):
    s = normalizar_frase_matematica(texto).strip().rstrip("?.! ")
    s = re.sub(rf"(?<![a-zA-Z_]){re.escape(variable.upper())}(?![a-zA-Z_])", variable, s)
    if len(s) > 2048 or s.count("$") % 2:
        return ""
    s = s.replace("$", "").replace(r"\(", "").replace(r"\)", "")
    s = s.replace(r"\left", "").replace(r"\right", "").strip()
    s = s.replace("[", "(").replace("]", ")")
    s = re.sub(r"\b(ln|log|sin|sen|cos|tan)\s+([a-zA-Z])\b", r"\1(\2)", s)
    if not s or not re.fullmatch(r"[\w\s+*/^().,{}\\|-]+", s) or re.search(rf"{re.escape(variable)}\d", s):
        return ""
    palabras = re.findall(r"[a-zA-Z_]+", s)
    if any(p not in _FUNCIONES and p != variable for p in palabras):
        return ""
    pila = []
    for c in s:
        if c in "({":
            pila.append(c)
        elif c in ")}" and (not pila or pila.pop() != {"}": "{", ")": "("}[c]):
            return ""
    return "" if pila else s

def sustituir_variable(expresion, variable, punto):
    return re.sub(rf"(?<![a-zA-Z_]){re.escape(variable)}(?![a-zA-Z_])",
                  lambda _: f"({punto})", expresion)

def propuesta_breve(texto, variable="x"):
    s = texto.strip()
    if s.startswith("¿") and s.endswith("?"):
        s = s[1:-1].strip()
    return formula_acotada(s, variable)

def _lado_declarado(texto, variable):
    s = re.split(r"[;!?¿¡]|\.(?=\s|$)|,\s*(?=[a-záéíóúñ])|\s+y\s+(?=[a-zA-Z]\s*\(|calcula|eval|deriv|explica)|\s+(?:porque|pero|ser[ií]a|respecto|cuando|resolviendo)\b", texto, maxsplit=1, flags=re.I)[0]

    for palabra in re.finditer(r"[a-zA-Z_áéíóúñÁÉÍÓÚÑ]+", s):
        if palabra.group() not in _FUNCIONES and palabra.group() not in (variable, variable.upper()):
            s = s[:palabra.start()]
            break
    s = re.sub(r"\s+y\s*$", "", s).rstrip(",; ")
    return formula_acotada(s, variable)

def _registrar_funciones(datos, texto):
    declaraciones = list(_DECLARACION.finditer(texto))
    funciones = datos.setdefault("funciones_declaradas", {})
    nuevas = []
    for i, m in enumerate(declaraciones):
        fin = declaraciones[i + 1].start() if i + 1 < len(declaraciones) else len(texto)
        variable = m[2]
        expresion = _lado_declarado(texto[m.end():fin], variable)
        if expresion:
            funciones[m[1]] = {"expresion": expresion, "variable": variable}
            nuevas.append(m[1])

    while len(funciones) > 12:
        funciones.pop(next(iter(funciones)))
    if len(nuevas) == 1:
        datos["funcion_vigente"] = nuevas[0]
    elif len(nuevas) > 1:
        datos.pop("funcion_vigente", None)
        datos.pop("ejercicio_activo", None)
    return funciones, nuevas

def _solicitud(funciones, nombre, prima, argumento, texto, *, estricto=False):
    funcion = funciones.get(nombre)
    if funcion is None and not estricto:
        alternativas = [v for k, v in funciones.items() if k.casefold() == nombre.casefold()]
        funcion = alternativas[0] if len(alternativas) == 1 else None
    if funcion is None:
        return None
    var, expr = funcion["variable"], funcion["expresion"]
    if argumento.strip() == var:
        if prima or re.search(r"\bderiv\w*\b", texto, re.I):
            return dict(tipo="derivada", expresion=expr, variable=var, destino="", **({"orden": len(prima)} if len(prima) > 1 else {}))
    elif (punto := formula_acotada(argumento, var)) and not re.search(r"[a-zA-Z]", punto):
        return dict(tipo="valor_derivada" if prima else "valor",
                    expresion=expr if prima else sustituir_variable(expr, var, punto),
                    variable=var, destino=punto if prima else "", **({"orden": len(prima)} if len(prima) > 1 else {}))
    return None

def _resolver_solicitudes(datos, funciones, texto, *, estricto=False):
    peticiones = re.findall(r"\b([a-zA-Z])\s*(?:('+)|prima\s+de\s+)?\s*\(\s*([^()]*)\s*\)(?!\s*=)", texto)
    peticiones += re.findall(r"\b([a-zA-Z])\s+prima\s+de\s+(x|y|t|\d+)\b", texto)
    for p in peticiones:
        nombre, prima, argumento = p if len(p) == 3 else (p[0], "'", p[1])
        if solicitud := _solicitud(funciones, nombre, prima, argumento, texto, estricto=estricto):
            datos["funcion_vigente"] = nombre if nombre in funciones else next(
                k for k in funciones if k.casefold() == nombre.casefold()
            )
            return solicitud
    return None

def recordar_funciones_y_resolver(datos, mensaje, *, asumir_derivada=True, nombres_estrictos=False):
    texto = normalizar_frase_matematica(mensaje).replace("′", "'")
    texto = re.sub(r"\^?\s*(?:\{\s*)?\\prime\s*\}?", "'", texto)
    funciones, nuevas = _registrar_funciones(datos, texto)
    if re.search(r"\b(?:a[nñ]ade|agrega|superp[oó]n)\b.*\bcompar\w*", texto, re.I):
        return None

    if solicitud := _resolver_solicitudes(datos, funciones, texto, estricto=nombres_estrictos):
        return solicitud
    if anafora := _derivada_de_funcion_anterior(datos, funciones, texto):
        return anafora
    if len(nuevas) == 1 and asumir_derivada:
        f = funciones[nuevas[0]]
        return dict(tipo="derivada", expresion=f["expresion"], variable=f["variable"], destino="")
    return None

def _derivada_de_funcion_anterior(datos, funciones, texto):
    if not (re.search(r"\bderiv\w*\b", texto, re.I) and re.search(r"\b(?:derivarla|derivarlo|su\s+derivada|(?:esa|esta|la anterior)\s+funci[oó]n)\b", texto, re.I)):
        return None
    anterior = datos.get("ejercicio_activo") or {}
    funcion = funciones.get(datos.get("funcion_vigente", ""))
    if funcion:
        return dict(tipo="derivada", expresion=funcion["expresion"], variable=funcion["variable"], destino="")
    if anterior.get("tipo") == "derivada":
        return anterior
    if not anterior and (expresion := formula_acotada(datos.get("expresion_previa", ""))):
        return dict(tipo="derivada", expresion=expresion, variable="x", destino="")
    return None

def paso_preguntado(texto, variable="x"):
    preguntas = re.findall(r"¿([^?]+)\?", texto)
    if len(preguntas) != 1:
        return None
    pregunta = preguntas[0]
    derivada = re.search(r"derivada\s+de\s+(.+)$", pregunta, re.I)
    valor = re.search(r"(?:cu[aá]nto\s+(?:es|vale|da|queda)|resultado\s+de|qu[eé]\s+n[uú]mero\s+obtienes\s+al\s+elevar)\s+(.+)$", pregunta, re.I)
    if derivada or valor:
        expresion = formula_acotada((derivada or valor)[1], variable)
        if expresion:
            return dict(tipo="derivada" if derivada else "valor", expresion=expresion, variable=variable)
    if re.search(r"(?:su\s+derivada|al\s+derivarlo)", pregunta, re.I):
        anteriores = re.findall(r"\$([^$]+)\$", texto[:texto.index("¿")])
        if anteriores and (expresion := formula_acotada(anteriores[-1], variable)):
            return dict(tipo="derivada", expresion=expresion, variable=variable)
    return None

def igualdades_explicitas(texto, variable="x"):
    formulas = re.findall(r"\$([^$]+)\$", texto)
    if not formulas:
        formulas = [texto.strip().rstrip("?.! ")]
    igualdades = []
    for formula in formulas:
        if "=" not in formula:
            continue
        lados = formula.split("=")
        canonicos = [formula_acotada(lado, variable) for lado in lados]
        if not all(canonicos):
            return []
        igualdades.extend(zip(canonicos, canonicos[1:], strict=False))
    return igualdades
