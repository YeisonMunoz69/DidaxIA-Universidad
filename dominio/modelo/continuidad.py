"""Estado operativo por hilo. Ninguna definición/propuesta es una operación implícita."""
import hashlib
import json
import re
from copy import deepcopy

from dominio.modelo.lectura_oral import leer_tarea_oral
from dominio.modelo.notacion_entrada import normalizar_frase_matematica
from dominio.modelo.referencias_matematicas import (
    formula_acotada,
    recordar_funciones_y_resolver,
)
from dominio.modelo.respuesta_en_contexto import (
    consulta_sin_entrega,
    leer_propuesta,
    respuesta_en_contexto,
)

VERSION = "continuidad.v1"
OPERACIONES = {"derivada", "valor", "valor_derivada", "limite"}


def nuevo():
    return dict(version=VERSION, revision=0, funciones={}, tareas=[], activa="", objetivos={},
                evidencias=[], voces=[], pedagogia={}, ultima_expresion="")


def tarea_actual(estado):
    return next((t for t in estado.get("tareas", []) if t["id"] == estado.get("activa")), None)


def ejercicio(estado):
    tarea = tarea_actual(estado)
    return {**deepcopy(tarea["ejercicio"]), "_tarea_id": tarea["id"]} if tarea else None


def para_interpretacion(estado):
    """Proyección acotada: nunca enviar cachés de respuestas ni perfiles al proveedor."""
    tareas = estado.get("tareas", [])
    seleccion = tareas[:2] + tareas[-6:]
    actual = tarea_actual(estado)
    if actual:
        seleccion.append(actual)
    referencias = {t["id"]: {k: deepcopy(t[k]) for k in
                             ("id", "ejercicio", "nombre", "completada") if k in t}
                   for t in seleccion}
    from dominio.modelo.foco_conversacional import materiales_para_prompt

    return dict(version=VERSION, activa=estado.get("activa", ""),
                tarea=deepcopy(actual["ejercicio"]) if actual else None,
                tareas=list(referencias.values()), objetivo=objetivo_actual(estado),
                acto=estado.get("acto", ""), aclaracion=estado.get("aclaracion", ""),
                propuesta=estado.get("propuesta", ""), materiales=materiales_para_prompt(estado), evidencias=[
                    {k: deepcopy(e[k]) for k in ("tarea", "alcance", "propuesta", "veredicto") if k in e}
                    for e in estado.get("evidencias", [])[-4:]])


def clave_tarea(activo):
    objeto = {k: str(activo.get(k) or "") for k in
              ("tipo", "expresion", "variable", "destino", "lado", "orden", "supuestos", "referencia")}
    objeto["variable"] = objeto["variable"] or "x"
    objeto["expresion"] = re.sub(r"\s+", "", normalizar_frase_matematica(objeto["expresion"]))
    objeto["expresion"] = re.sub(r"\^\(([-+]?\d+)\)", r"^\1", objeto["expresion"]).replace("**", "^")
    return hashlib.sha256(json.dumps(objeto, sort_keys=True).encode()).hexdigest()[:24]


def activar(estado, activo, origen, nombre=""):
    identidad = clave_tarea(activo)
    if not any(t["id"] == identidad for t in estado["tareas"]):
        estado["tareas"].append(dict(id=identidad, ejercicio=deepcopy(activo), origen=origen,
                                    nombre=nombre, completada=False, pasos_resueltos=[]))
        estado["tareas"] = estado["tareas"][-32:]
        ids = {t["id"] for t in estado["tareas"]}
        estado["objetivos"] = {k: v for k, v in estado["objetivos"].items() if k in ids}
    estado["activa"] = identidad
    estado["ultima_expresion"] = activo["expresion"]
    estado.pop('representacion', None)


def _entrega_rotulada(estado, texto):
    actual = tarea_actual(estado)
    entrega = re.fullmatch(r"\s*([a-zA-Z])\s*('*)\s*\(\s*([^()]+)\s*\)\s*=\s*(.+?)[?.!]*", texto)
    cambio = bool(re.search(r"\b(?:redefine|cambia|corrijo|correcci[oó]n|otra\s+funci[oó]n|nuevo\s+ejercicio)\b", texto, re.I))
    # Entregar f(x)=... en el objetivo actual no redefine una función a escondidas.
    if actual and entrega and not cambio and (
        entrega[1] == actual.get("nombre") or (not actual.get("nombre") and bool(entrega[2]))
    ):
        tarea = actual["ejercicio"]
        if entrega[2] and len(entrega[2]) != tarea.get("orden", 1):
            estado["aclaracion"] = "El orden que escribiste no coincide con el ejercicio activo. ¿Quieres responder al ejercicio actual o cambiar el orden de derivación?"
            return True
        if entrega[3].strip().isdigit() and tarea.get("destino") and entrega[3].strip() != tarea["destino"]:
            estado["aclaracion"] = "El punto que escribiste es diferente del que estamos trabajando. ¿Quieres evaluar en ese nuevo punto o responder a la tarea actual?"
            return True
        propuesta = formula_acotada(entrega[4], actual["ejercicio"].get("variable", "x"))
        if propuesta:
            estado.update(acto="responder", propuesta=propuesta,
                          alcance="final" if entrega[2] or entrega[3].strip().isdigit() else "auto")
            return True
    return False


def _retomar(estado, texto):
    retoma = re.search(r"\b(?:retom|volv|vuelv|regres|seguimos|est[aá]bamos|anterior|primera?\s+(?:ecuaci[oó]n|funci[oó]n|ejercicio))", texto, re.I)
    # «Calcula F(3) de la función anterior» pide otra operación sobre una
    # referencia conocida; la palabra anterior no anula esa petición.
    if retoma and not _resolver_tarea(deepcopy(estado), texto)[0]:
        tareas = estado["tareas"]
        destino = None
        candidatos = _tareas_referidas(tareas, texto)
        if candidatos is not None:
            destino = candidatos[0] if len(candidatos) == 1 else None
        elif re.search(r"\bprimer[ao]?\b", texto, re.I):
            destino = tareas[0] if tareas else None
        elif re.search(r"\bsegund[ao]\b", texto, re.I):
            destino = tareas[1] if len(tareas) > 1 else None
        elif re.search(r"\banterior\b", texto, re.I):
            destino = next((t for t in reversed(tareas) if t["id"] != estado["activa"]), None)
        else:
            destino = tarea_actual(estado)
        if destino:
            estado.update(activa=destino["id"], acto="retomar")
        else:
            estado["aclaracion"] = "¿Cuál ejercicio quieres retomar? Puedes copiar su enunciado."
        return True
    return False


def _tareas_referidas(tareas, texto):
    nombre = re.search(r'\bfunci[oó]n\s+([a-zA-Z])\b', texto, re.I)
    if nombre:
        return [t for t in tareas if t.get('nombre', '').casefold() == nombre[1].casefold()]
    if re.search(r'\bl[ií]mite\b', texto, re.I):
        return [t for t in tareas if t['ejercicio']['tipo'] == 'limite']
    return None


def _desde_representacion(estado, texto):
    curva = estado.get('representacion', {})
    if curva and re.search(r'\b(?:su\s+derivada|derivada\s+de\s+(?:esa|esta)(?:\s+funci[oó]n)?)\b', texto, re.I):
        return dict(tipo='derivada', expresion=curva['expresion'], variable=curva['variable'])
    return None


def _con_formula_valida(tarea):
    return tarea if tarea and formula_acotada(tarea['expresion'], tarea.get('variable', 'x')) else None


def _resolver_tarea(estado, texto):
    from dominio.filtros.intencion import extraer_ejercicio_explicito
    from dominio.filtros.intento import ejercicio_de_intento_explicito

    texto = _notacion_de_tarea(texto)
    if curva := _desde_representacion(estado, texto):
        return curva, ''
    funciones = dict(funciones_declaradas=deepcopy(estado["funciones"]),
                     ejercicio_activo=ejercicio(estado), expresion_previa=estado["ultima_expresion"],
                     funcion_vigente=estado.get("funcion_vigente", ""))
    # La alternativa de caja sólo resuelve el mismo nombre si es único.
    # Nunca reutiliza f para una petición sobre g ni fusiona F y f declaradas.
    resuelto = recordar_funciones_y_resolver(funciones, texto, asumir_derivada=False)
    nombre = funciones.get("funcion_vigente", "") if resuelto else ""
    for n, f in funciones.get("funciones_declaradas", {}).items():
        previa = estado["funciones"].get(n, {})
        distinta = any(f.get(k) != previa.get(k) for k in ("expresion", "variable"))
        f["revision"] = previa.get("revision", 0) + int(distinta)
    estado["funciones"] = funciones.get("funciones_declaradas", {})
    estado["funcion_vigente"] = funciones.get("funcion_vigente", "")
    texto = _referencias_con_mayusculas(estado, texto)
    explicito = ejercicio_de_intento_explicito(texto) or extraer_ejercicio_explicito(texto)
    # Una referencia resuelta prevalece sobre la llamada literal sin sustituir.
    resuelto = resuelto or explicito
    if resuelto and not nombre:
        coincidentes = [n for n, f in estado['funciones'].items()
                       if f.get('expresion') == resuelto['expresion']]
        if len(coincidentes) == 1:
            nombre = coincidentes[0]
            resuelto['variable'] = estado['funciones'][nombre]['variable']
    resuelto = _con_formula_valida(resuelto)
    if resuelto and re.search(r"\b[a-zA-Z]\s*\(", resuelto["expresion"]):
        # Una llamada sin definición no es una expresión autónoma del CAS.
        resuelto = None
    if resuelto and nombre:
        resuelto["referencia"] = f"{nombre}:{estado['funciones'][nombre]['revision']}"
        punto = re.search(rf"\b{re.escape(nombre)}\s*\(\s*([-+]?\d+(?:\.\d+)?)\s*\)(?!\s*=)", texto)
        if resuelto["tipo"] == "valor" and punto:
            resuelto["destino"] = punto[1]
    if resuelto and resuelto["tipo"] in ("derivada", "valor_derivada"):
        orden = 3 if re.search(r"\btercera\s+derivada\b", texto, re.I) else (2 if re.search(r"\bsegunda\s+derivada\b", texto, re.I) else resuelto.get("orden", 1))
        if orden > 1:
            resuelto["orden"] = orden
    return resuelto, nombre


def _referencias_con_mayusculas(estado, texto):
    """Resolver cambios de caja sólo cuando hay una definición inequívoca.

    F y f siguen siendo nombres diferentes si ambos fueron definidos. No se
    convierte una declaración nueva ni se sustituye una función desconocida.
    """
    funciones = estado.get("funciones", {})

    def referencia(m):
        nombre, prima, argumento = m[1], m[2], m[3]
        candidatos = [n for n in funciones if n.casefold() == nombre.casefold()]
        elegido = nombre if nombre in funciones else candidatos[0] if len(candidatos) == 1 else ""
        if not elegido:
            return m[0]
        variable = funciones[elegido]["variable"]
        if argumento.strip().casefold() == variable.casefold():
            argumento = variable
        return f"{elegido}{prima}({argumento})"

    return re.sub(r"\b([a-zA-Z])\s*('*)\s*\(\s*([^()]*)\s*\)(?!\s*=)", referencia, texto)


def _notacion_de_tarea(texto):
    texto = texto.replace("′", "'").replace("’", "'").replace("″", "''").replace("‴", "'''")
    texto = re.sub(r"\$([^$]*)\$", r"\1", texto)
    texto = re.sub(r"\^?\s*(?:\{\s*)?\\prime\s*\}?", "'", texto)
    texto = re.sub(r"\b([a-zA-Z])`(?=\s*\()", r"\1'", texto)
    texto = re.sub(r"\b([a-zA-Z])('+)[ \t]*([a-zA-Z])\b", r"\1\2(\3)", texto)
    texto = re.sub(r"\b([a-zA-Z])\s+prima\s+de\s+([a-zA-Z]|[-+]?\d+(?:\.\d+)?)\b", r"\1'(\2)", texto)
    texto = re.sub(r"\b([a-zA-Z]\s*\(\s*[a-zA-Z]\s*\))\s*:\s*", r"\1=", texto)
    # y=... y dy/dx son una definición explícita y su referencia, no una ecuación implícita.
    texto = re.sub(r"\by\s*=", "y(x)=", texto)
    texto = re.sub(r"\bdy\s*/\s*dx\b", "y'(x)", texto)
    texto = re.sub(r"\by('+)(?!'|\s*\()", lambda m: "y" + m[1] + "(x)", texto)
    return texto


def _sin_tarea_nueva(estado, anterior, texto, aclaracion_anterior):
    from dominio.filtros.intento import propuesta_en_el_turno

    if consulta_sin_entrega(texto):
        return
    desconocida = re.search(r"\b([a-zA-Z])\s*'*\s*\(\s*[^()]+\s*\)", texto)
    if desconocida and desconocida[1] not in estado["funciones"]:
        estado["aclaracion"] = "No tengo la definición de esa función en esta charla. ¿Puedes escribirla?"
        if "'" in desconocida[0]:
            estado["aclaracion"] += " Si querías derivar directamente la expresión entre paréntesis, escribe «deriva» seguido de esa expresión."
    elif estado["funciones"] != (anterior or {}).get("funciones", {}):
        estado["acto"] = "definir"
        estado["activa"] = ""
        vigente = estado["funciones"].get(estado.get("funcion_vigente", ""), {})
        estado["ultima_expresion"] = vigente.get("expresion", "")
        estado["aclaracion"] = "¿Quieres evaluar la función en un punto o calcular su derivada?"
    elif aclaracion_anterior:
        estado["aclaracion"] = aclaracion_anterior
    else:
        variable = (ejercicio(estado) or {}).get("variable", "x")
        propuesta = formula_acotada(texto.rstrip("?"), variable) or propuesta_en_el_turno(texto)
        propuesta = formula_acotada(propuesta, variable) or (propuesta if propuesta == "no existe" else "")
        if tarea_actual(estado) and propuesta:
            estado.update(acto="responder", propuesta=propuesta)
        elif formula_acotada(texto, variable):
            estado["ultima_expresion"] = formula_acotada(texto, variable)
            estado["aclaracion"] = "¿Qué operación quieres realizar con esta expresión?"


def _recordar_agenda(estado, texto, mensaje):
    """Guardar apartados explícitos, sin deducir tareas de una respuesta."""
    if not re.search(r"\b(?:calcula|hallar?|resolv\w*|obt[eé]n)\b", texto, re.I):
        return
    peticiones = list(re.finditer(r"\b[a-zA-Z]\s*'*\s*\(\s*[^()]*\s*\)(?!\s*=)", texto))
    if not 2 <= len(peticiones) <= 6:
        return
    activa = estado["activa"]
    vigente = estado.get("funcion_vigente", "")
    expresion = estado["ultima_expresion"]
    agenda = []
    for peticion in peticiones:
        resuelto, nombre = _resolver_tarea(estado, peticion[0])
        if resuelto:
            activar(estado, resuelto, mensaje, nombre)
            if estado["activa"] not in agenda:
                agenda.append(estado["activa"])
    estado["activa"] = activa
    estado["funcion_vigente"] = vigente
    estado["ultima_expresion"] = expresion
    if len(agenda) > 1:
        estado["agenda"] = agenda


def _retomar_apartado(estado, mensaje):
    """Una petición de otro apartado no es una propuesta para el anterior."""
    agenda = estado.get("agenda", [])
    if len(agenda) < 2:
        return False
    ordinal = re.search(r"\b(primer[o]?|segund[oa]|tercer[o]?|[123])\s+(?:punto|apartado|ejercicio)\b", mensaje, re.I)
    destino = None
    if ordinal:
        indice = {"primer": 0, "primero": 0, "1": 0, "segundo": 1, "segunda": 1,
                  "2": 1, "tercer": 2, "tercero": 2, "3": 2}[ordinal[1].lower()]
        destino = agenda[indice] if indice < len(agenda) else None
    elif re.search(r"\b(?:siguiente\s+(?:punto|apartado|ejercicio|paso)|sigamos|continuemos)\b", mensaje, re.I):
        actual = tarea_actual(estado)
        if actual and actual["completada"] and actual["id"] in agenda:
            indice = agenda.index(actual["id"]) + 1
            destino = agenda[indice] if indice < len(agenda) else None
    if destino and any(t["id"] == destino for t in estado["tareas"]):
        estado.update(activa=destino, acto="retomar", aclaracion="", propuesta="")
        return True
    return False


def _continuacion_del_hilo(estado, mensaje):
    if _retomar_apartado(estado, mensaje) or respuesta_en_contexto(estado, mensaje):
        return True
    if consulta_sin_entrega(mensaje):
        estado['acto'] = 'consultar'
        return True
    return False


def _derivada_escrita(estado, texto):
    """Lectura estudiantil explícita: prima aplicada al enunciado, no composición.

    Sólo se admite si la función no está declarada, el argumento contiene una
    expresión no trivial con una única variable y la sintaxis es comprobable.
    La respuesta comunica esta interpretación antes del resultado del CAS.
    """
    izquierda, separador, derecha = texto.partition('=')
    llamada = re.fullmatch(r"\s*([a-zA-Z])('+)[ \t]*\((.+)\)\s*", izquierda.strip().rstrip('?.!'))
    if not llamada or any(n.casefold() == llamada[1].casefold() for n in estado['funciones']):
        return False
    variables = re.findall(r'\b[xtyu]\b', llamada[3])
    if len(set(variables)) != 1 or len(llamada[2]) > 3:
        return False
    variable = variables[0]
    expresion = formula_acotada(llamada[3], variable)
    if not expresion or expresion == variable:
        return False
    activar(estado, dict(tipo='derivada', expresion=expresion, variable=variable,
                        orden=len(llamada[2])), texto)
    estado.update(acto='iniciar', lectura_derivada=expresion, aclaracion='')
    propuesta = leer_propuesta(derecha, variable) if separador else ''
    if propuesta:
        estado.update(acto='responder', propuesta=propuesta, alcance='final')
    return True


def _referencia_del_turno(estado, texto):
    return _derivada_escrita(estado, texto) or _entrega_rotulada(estado, texto) or _retomar(estado, texto)


def _representar(estado, texto):
    from dominio.filtros.intencion import extraer_curva_solicitada

    curva = formula_acotada(extraer_curva_solicitada(texto))
    if curva:
        estado['representacion'] = dict(expresion=curva, variable='x')
        estado['ultima_expresion'] = curva
    estado.update(acto='representar', aclaracion='')


def preparar(anterior, mensaje):
    estado = deepcopy(anterior or nuevo())
    if estado.get("version") != VERSION:
        raise ValueError("versión de continuidad desconocida")
    aclaracion_anterior = estado.get("aclaracion", "")
    estado.update(acto="continuar", propuesta="", aclaracion="", alcance="auto", lectura_oral="", lectura_derivada="", paso_usuario=None)
    if _continuacion_del_hilo(estado, mensaje):
        return estado
    oral, duda = leer_tarea_oral(mensaje)
    if duda:
        estado["aclaracion"] = duda
        return estado
    texto = _referencias_con_mayusculas(estado, _notacion_de_tarea(
        oral or normalizar_frase_matematica(mensaje).strip()))
    if "=" in texto and re.search(r"\by\s*(?:\^|\*|[+])|\bxy\b", texto) and not re.search(r"\by\s*=", texto):
        estado["aclaracion"] = "Este ejercicio requiere derivación implícita. Ese tipo de comprobación todavía no está habilitado; no lo verificaré como una derivada explícita. Puedes trabajar una función despejada o pedirme una explicación conceptual."
        return estado
    # No reutilizar una derivada previa para una operación que no está soportada.
    if re.search(r"\b(?:integra[rl]?|integral|antiderivada)\b|∫", texto, re.I):
        estado["aclaracion"] = "La verificación de integrales aún no está disponible. Puedo ayudarte con derivadas, evaluaciones y límites. ¿Qué quieres trabajar?"
        return estado
    if _referencia_del_turno(estado, texto):
        return estado
    resuelto, nombre = _resolver_tarea(estado, texto)
    if resuelto:
        activar(estado, resuelto, mensaje, nombre)
        estado["acto"] = "iniciar"
        estado["lectura_oral"] = resuelto["expresion"] if oral else ""
        _propuesta_junto_a_tarea(estado, texto)
        _recordar_agenda(estado, texto, mensaje)
    elif re.search(r"\b(?:gr[aá]fic\w*|dibuj\w*|representa\w*)\b", texto, re.I):
        _representar(estado, texto)
    else:
        _sin_tarea_nueva(estado, anterior, texto, aclaracion_anterior)
    if re.search(r"\bresultado\s+final\b|\brespuesta\s+final\b", texto, re.I):
        estado["alcance"] = "final"
    return estado


def _propuesta_junto_a_tarea(estado, texto):
    from dominio.filtros.intento import anuncia_resultado, propuesta_en_el_turno

    if anuncia_resultado(texto):
        variable = ejercicio(estado).get("variable", "x")
        propuesta = formula_acotada(propuesta_en_el_turno(texto), variable)
        if propuesta:
            estado.update(acto="responder", propuesta=propuesta)


def _iniciar_por_acto(estado, acto, evidencia):
    # La lectura semántica completa huecos, nunca borra un punto u orden ya leído.
    if estado.get("acto") == "iniciar" and tarea_actual(estado):
        return
    operacion = acto.get("operacion")
    literal = acto.get("expresion", "")
    indicadores = {"derivada": r"deriv|d/d|prima", "valor": r"calcul|eval|valor|sustitu",
                   "valor_derivada": r"deriv|prima", "limite": r"l[ií]m|tiende|aproxima"}
    if operacion not in OPERACIONES or literal not in evidencia:
        return
    if not re.search(indicadores[operacion], evidencia, re.I):
        return
    variable = acto.get("variable", "x")
    if variable not in ("x", "t", "y", "u") or not (expr := formula_acotada(literal, variable)):
        return
    destino = acto.get("destino", "")
    if destino and (destino not in evidencia or not formula_acotada(destino)):
        return
    if operacion in ("limite", "valor_derivada") and not destino:
        return
    activar(estado, dict(tipo=operacion, expresion=expr, variable=variable, destino=destino), evidencia)
    estado.update(acto="iniciar", aclaracion="")


def aplicar_actos(estado, actos, mensaje):
    """Solo aplicar spans actuales y referencias conocidas; el LLM no acredita verdad."""
    estado = deepcopy(estado)
    if estado.get('acto') in ('dialogar', 'paso_usuario'):
        return estado
    for acto in actos[:4]:
        evidencia = acto.get("evidencia", "")
        if not evidencia or evidencia not in mensaje:
            continue
        tipo = acto.get("tipo")
        if (tipo == "retomar" and not estado.get('propuesta') and not leer_propuesta(evidencia)
                and acto.get("tarea_id") in {t["id"] for t in estado["tareas"]}):
            estado.update(activa=acto["tarea_id"], acto="retomar", aclaracion="")
        elif tipo == "responder" and tarea_actual(estado) and not estado.get("propuesta") and not estado.get("aclaracion"):
            # La traducción matemática se deriva del span citado, no de una fórmula inventada.
            s = normalizar_frase_matematica(evidencia).strip().rstrip("?.! ")
            s = re.sub(r"\s+(?:quedar[ií]a|queda|creo|pienso|ser[ií]a)$", "", s, flags=re.I)
            s = re.sub(r"^(?:ser[ií]a|queda|da|es)\s+", "", s, flags=re.I)
            if propuesta := leer_propuesta(s, ejercicio(estado).get("variable", "x")):
                estado.update(acto="responder", propuesta=propuesta, aclaracion="")
        elif tipo == "iniciar" and not estado.get("propuesta"):
            _iniciar_por_acto(estado, acto, evidencia)
    return estado


def objetivo_actual(estado):
    return deepcopy(estado.get("objetivos", {}).get(estado.get("activa", "")))


def cerrar(estado, ctx):
    estado = deepcopy(estado)
    tarea = tarea_actual(estado)
    if tarea:
        if ctx.resultado_verificado:
            tarea["completada"] = True
            estado["objetivos"].pop(tarea["id"], None)
        elif ctx.paso_verificado and ctx.paso_pendiente and not ctx.paso_pendiente.get("negada"):
            identificador = ctx.paso_pendiente.get("id")
            if identificador and identificador not in tarea["pasos_resueltos"]:
                tarea["pasos_resueltos"].append(identificador)
    if ctx.veredicto_del_intento in ("valida", "invalida") or ctx.paso_pendiente:
        estado["evidencias"].append(dict(turno=ctx.identificador_turno, tarea=estado["activa"],
                                        alcance="paso" if ctx.paso_pendiente and not ctx.resultado_verificado else "final",
                                        propuesta=estado.get("propuesta", ""), veredicto=ctx.veredicto_del_intento,
                                        paso=deepcopy(ctx.paso_pendiente),
                                        referencia=ctx.precomputo.resultado_corriente if ctx.precomputo else "",
                                        operacion=deepcopy((tarea or {}).get("ejercicio"))))
        estado["evidencias"] = estado["evidencias"][-48:]
    estado["revision"] += 1
    return estado
