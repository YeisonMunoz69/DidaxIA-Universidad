import json
import re
from copy import deepcopy
from dataclasses import replace

from dominio.filtros.base import Filtro
from dominio.modelo.continuidad import (
    aplicar_actos,
    cerrar,
    ejercicio,
    objetivo_actual,
    preparar,
    tarea_actual,
)
from dominio.modelo.foco_conversacional import (
    enfocar,
    materiales_para_prompt,
    recordar_material,
    recuperar_materiales_emitidos,
)
from dominio.modelo.respuesta import ExpresionCitada, RespuestaGenerada
from dominio.pedagogia.intenciones import Intencion


def proyectar(ctx, estado):
    activo = ejercicio(estado)
    curva = estado.get('representacion', {}) if estado.get('acto') == 'representar' else {}
    expr = curva.get('expresion') or (activo["expresion"] if activo else estado.get('ultima_expresion', ''))
    return replace(ctx, continuidad=estado, ejercicio_activo=activo,
                   expresion_previa=expr, expresiones=(expr,) if expr else (),
                   expresiones_heredadas=bool(expr),
                   es_limite=bool(activo and activo["tipo"] == "limite"),
                   limite_expresion=expr if activo and activo["tipo"] == "limite" else "",
                   limite_destino=activo.get("destino", "") if activo else "",
                   limite_variable=activo.get("variable", "x") if activo else "x")

class FiltroContinuidadEntrada(Filtro):
    nombre = "carga de tarea conversacional"
    ruta = "caliente"

    def _procesar(self, ctx):
        estado = preparar(ctx.continuidad, ctx.texto_estudiante)
        recuperar_materiales_emitidos(estado, ctx.historial_reciente)
        return proyectar(ctx, estado), {"version": estado["version"], "revision": estado["revision"],
                                       "tarea": estado["activa"], "acto": estado["acto"]}

class FiltroContinuidadResolver(Filtro):
    nombre = "alineación de tarea y respuesta"
    ruta = "caliente"

    def _procesar(self, ctx):
        from dominio.pedagogia.problema import reiniciar_por_cambio_de_problema

        estado = aplicar_actos(ctx.continuidad, ctx.actos_conversacionales, ctx.texto_estudiante)
        estado = _practica_contextual(estado, ctx.texto_estudiante, ctx.historial_reciente)
        intencion = ctx.intencion_detalle or Intencion()
        estado, intencion = enfocar(estado, intencion, ctx.actos_conversacionales, ctx.texto_estudiante)
        ctx = proyectar(ctx, estado)
        if estado["acto"] == "responder" and estado.get("propuesta"):
            intencion = replace(intencion, clase="intento_resolucion", propone_solucion=True)
        elif estado["acto"] in ("iniciar", "definir", "retomar") and intencion.clase in ('ambigua', 'practica_guiada'):
            intencion = replace(intencion, clase="practica_guiada", propone_solucion=False)
        pedagogia = ctx.estado_conversacion
        if pedagogia and estado.get("activa"):
            problema, _ = reiniciar_por_cambio_de_problema(
                pedagogia.problema, intencion, (), base="tarea:" + estado["activa"],
            )
            pedagogia = pedagogia.con_problema(problema)
        return replace(ctx, intencion=intencion.clase, intencion_detalle=intencion,
                       estado_conversacion=pedagogia), {
            "tarea": estado["activa"], "acto": estado["acto"],
            "aclaracion": bool(estado.get("aclaracion")),
        }

def _practica_contextual(estado, mensaje, voces):
    if (estado.get('acto') != 'definir' or not voces
            or not re.search(r'\bpracticar\b', mensaje, re.I)
            or re.search(r'\bl[ií]mite|\bevalua|\bintegr', mensaje, re.I)):
        return estado
    anterior = voces[-1]
    invitacion = anterior.get('tutor', '')
    peticion = anterior.get('estudiante', '')
    invita_a_derivar = re.search(r'\bderiv\w*\b', invitacion, re.I)
    if not invita_a_derivar and re.search(r'\bregla\s+de\s+la\s+potencia\b', invitacion, re.I):

        previo = voces[-2] if len(voces) > 1 else {}
        invita_a_derivar = re.search(r'\bderiv\w*\b',
            previo.get('estudiante', '') + ' ' + previo.get('tutor', ''), re.I)
    if (not re.search(r'\b(?:deriv\w*|potencia)\b', peticion, re.I)
            or not invita_a_derivar
            or re.search(r'\bl[ií]mite|\bevalua|\bintegr', peticion, re.I)):
        return estado
    nombre = estado.get('funcion_vigente', '')
    funcion = estado.get('funciones', {}).get(nombre)
    if not funcion:
        return estado
    from dominio.modelo.continuidad import activar
    activar(estado, dict(tipo='derivada', expresion=funcion['expresion'],
                        variable=funcion['variable'], referencia=f"{nombre}:{funcion['revision']}"), mensaje, nombre)
    estado.update(acto='iniciar', aclaracion='')
    return estado

class FiltroContinuidadObjetivo(Filtro):
    nombre = "selección del objetivo conversacional"
    ruta = "caliente"

    def __init__(self, cas):
        self.cas = cas

    def _procesar(self, ctx):
        estado = deepcopy(ctx.continuidad)
        tarea = tarea_actual(estado)
        if estado.get('acto') in ('paso_usuario', 'dialogar', 'consultar', 'representar'):
            if tarea and (estado.get('foco') or {}).get('clase') == 'bloqueo_explicito' and not objetivo_actual(estado):
                planes = self.cas.objetivos_conversacionales(tarea['ejercicio'])
                if planes:
                    estado['objetivos'][tarea['id']] = {**planes[0], 'tarea_id': tarea['id']}
            return replace(ctx, continuidad=estado, siguiente_objetivo=None), {'motivo': 'seguir el procedimiento elegido por el estudiante'}
        if not tarea or tarea.get("completada") or estado.get("aclaracion") or ctx.resultado_verificado:
            return ctx, {"objetivo": "", "motivo": "sin pregunta matemática pendiente"}
        if ctx.paso_verificado and ctx.paso_pendiente and not ctx.paso_pendiente.get("negada"):
            ident = ctx.paso_pendiente.get("id")
            if ident and ident not in tarea["pasos_resueltos"]:
                tarea["pasos_resueltos"].append(ident)
        planes = self.cas.objetivos_conversacionales(tarea["ejercicio"])
        objetivo = next((p for p in planes if p["id"] not in tarea["pasos_resueltos"]), None)
        if objetivo:
            objetivo = {**objetivo, "tarea_id": tarea["id"]}

        preguntar = (estado["acto"] in ("iniciar", "responder", "retomar")
                     and not (ctx.intencion_detalle and ctx.intencion_detalle.pide_menos_preguntas)
                     and ctx.necesidad_pedagogica not in ("resumir", "explicar_razon", "ver_grafica"))
        if objetivo and preguntar:
            estado["objetivos"][tarea["id"]] = objetivo
        return replace(ctx, continuidad=estado, siguiente_objetivo=objetivo if preguntar else None), {
            "tarea": estado["activa"], "objetivo": objetivo["id"] if objetivo else "",
            "pregunta": bool(objetivo and preguntar),
        }

class FiltroContinuidadPrompt(Filtro):
    nombre = "contrato conversacional del generador"
    ruta = "caliente"

    def _procesar(self, ctx):
        estado = ctx.continuidad
        contrato = dict(tarea=tarea_actual(estado), objetivo=ctx.siguiente_objetivo,
                        acto=estado["acto"], propuesta=estado.get("propuesta"),
                        aclaracion=estado.get("aclaracion"), evidencias=estado["evidencias"][-4:],
                        foco=estado.get('foco'), materiales=materiales_para_prompt(estado))
        seccion = (
            "ESTADO OPERATIVO AUTORITATIVO DEL TURNO (datos del servidor):\n"
            + json.dumps(contrato, ensure_ascii=False) + "\n"
            "La operación, expresión, punto y alcance de esta tarea prevalecen sobre referencias del historial. "
            "Conserva la actividad y sus avances, pero atiende primero la petición ACTUAL del estudiante. "
            "Una consulta, ejemplos, una explicación o una gráfica pueden ser paralelos a la actividad; "
            "no exijas contestar la pregunta pendiente para atenderlos. Una definición no pide derivar por defecto. "
            "Respeta la cantidad y detalle solicitados: si pide varios ejemplos, entrega todos, no una promesa "
            "ni solamente el primero. Usa los materiales emitidos cuando pregunte por sus soluciones o procesos. "
            "No confundas esos ejemplos con la función de la actividad. Comprueba las afirmaciones declaradas. "
            "Si pide una gráfica, representa la función solicitada: no hace falta un punto de aproximación "
            "salvo que pida específicamente un límite. Señala las restricciones del dominio cuando existan. "
            "Si hay objetivo del servidor, éste añadirá UNA pregunta; no la dupliques. Cuando el foco sea consulta, "
            "puedes orientar con una pregunta pertinente sin imponer el objetivo suspendido. "
            "No conviertas un paso parcial ni una solución de ejemplo en resultado final de la actividad.\n\n"
            "Cuando pida reglas o una tabla de derivadas, escribe las fórmulas completas en afirmaciones "
            "y cita cada identificador en la narración. Para reglas generales, usa funciones diferenciables "
            "u(x), v(x), f(x), g(x), constantes a, b, c, k, m, n y el operador d/dx (...). "
            "Las primas u'(x), v'(x) y f'(g(x)) se comprueban como derivadas formales. "
            "Aclara que los parámetros no dependen de x, que las funciones deben ser diferenciables "
            "y que el denominador del cociente no puede ser cero. No resuelvas la actividad pendiente "
            "cuando lo solicitado sea una tabla de referencia.\n\n"
            "En un ejemplo cuya función eliges tú, cita la expresión concreta y comprueba su derivada "
            "con d/dx (expresión), en lugar de afirmar f'(x) = resultado sin definir f. "
            "Para evaluar ese ejemplo en un punto, declara la sustitución explícita en la fórmula, "
            "por ejemplo 2*3 = 6, no f'(3) = 6 sin una definición formal disponible.\n\n"
            "No uses igualdades tautológicas como 6=6 para presentar evaluaciones: conserva la sustitución "
            "en el lado izquierdo. Si explicas la cadena por capas, deriva la exterior respecto a una "
            "variable auxiliar t y luego muestra la derivada completa respecto a x. No omitas la derivada "
            "interior al escribir d/dx de la composición. Usa notación con funciones vinculadas: "
            "en la cadena escribe f'(g(x))*g'(x), no df/du ni du/dx sin su definición dentro de "
            "la misma afirmación. Los valores y el significado descritos en palabras deben coincidir "
            "con las fórmulas; una tasa de cambio es local, no el cambio exacto de cualquier "
            "intervalo. Al explicar una evaluación, referencia su afirmación y di «ese valor»; "
            "evita repetir la cifra calculada en prosa, donde podrías contradecir la fórmula. "
            "Cuando pidan lenguaje sencillo, usa frases cortas y un solo ejemplo por regla.\n\n"
            "Si pide una explicación cotidiana más fácil, evita introducir límites y símbolos nuevos "
            "salvo que los pida. No uses alias como v_prom o velocidad en una igualdad: explica esos "
            "conceptos en palabras, y para una definición formal usa f(t) y f'(t).\n\n"
        )
        from dominio.filtros.prompt import _historial

        politica = ctx.prompt.replace(_historial(ctx.historial_reciente), "") if ctx.historial_reciente else ctx.prompt
        politica = politica.replace("MENSAJE DEL ESTUDIANTE:\n" + ctx.texto_estudiante.strip(), "La petición actual se proporciona en el último mensaje user.")
        cantidad = (estado.get('foco') or {}).get('cantidad', 0)
        if cantidad > 1:
            politica += (f'\nPETICIÓN ACTUAL: entrega los {cantidad} ejemplos o ejercicios solicitados en una '
                         f'lista numerada de 1 a {cantidad}. La estrategia de ejemplo trabajado se aplica a '
                         'todos los ejemplos solicitados; no se limita a un único ejemplo. '
                         'No condiciones la entrega a contestar antes la pregunta de la actividad.\n')
        mensajes = [{"role": "system", "content": seccion + politica}]
        for voz in ctx.historial_reciente[-6:]:
            for autor, role in (("estudiante", "user"), ("tutor", "assistant")):
                if voz.get(autor):
                    mensajes.append({"role": role, "content": str(voz[autor])[:6000]})
        mensajes.append({"role": "user", "content": ctx.texto_estudiante})
        return replace(ctx, prompt=seccion + ctx.prompt, mensajes_generacion=tuple(mensajes)), {"tarea": estado["activa"], "version": estado["version"]}

def _con_pregunta(ctx, respuesta, objetivo, cas):
    compatible = respuesta is not None
    if respuesta and not ctx.retroalimentacion_del_intento:
        permitidas = [ctx.ejercicio_activo["expresion"], objetivo["expresion"],
                      ctx.continuidad.get("propuesta", "")]
        otras = [c.expresion for c in respuesta.citadas if c.expresion not in permitidas]
        if otras and not cas.citas_conversacionales_relacionadas((ctx.ejercicio_activo, otras)):
            compatible = False
        if ctx.ejercicio_activo["tipo"] == "valor" and re.search(r"\bderiv\w*", respuesta.narracion, re.I):
            compatible = False
    if not compatible:
        respuesta = RespuestaGenerada(narracion="Continuemos con la tarea que estamos trabajando.", nivel_divulgacion=1)

    narracion = re.sub(r"¿[^?]*\?", "", respuesta.narracion).strip()
    narracion = re.sub(r"[^.!?]*\?", "", narracion).strip()
    identificador = "c_objetivo_activo"
    citadas = respuesta.citadas
    if objetivo["alcance"] == "final" and objetivo["tipo"] in ("limite", "valor_derivada"):
        pregunta = "Para cerrar el ejercicio, ¿qué resultado obtienes para la operación solicitada?"
    else:
        orden = objetivo.get("orden", 1)
        derivada = "derivada" if orden == 1 else f"derivada de orden {orden}"
        pregunta = (f"¿Cuál es la {derivada} de " if objetivo["tipo"] == "derivada" else "¿Cuánto vale ") + "{{" + identificador + "}}?"
        citadas = tuple(c for c in citadas if c.identificador != identificador) + (
            ExpresionCitada(identificador, objetivo["expresion"]),
        )
    narracion += " " + pregunta

    citadas = tuple(c for c in citadas if "{{" + c.identificador + "}}" in narracion)
    afirmaciones = tuple(a for a in respuesta.afirmaciones if "{{" + a.identificador + "}}" in narracion)
    respuesta = replace(respuesta, narracion=narracion, citadas=citadas, afirmaciones=afirmaciones)
    return respuesta

def _con_lectura_explicita(respuesta, estado):
    if estado.get('aclaracion'):
        return respuesta
    lecturas = (('lectura_oral', 'oral1', 'Interpreto tu expresión como {{oral1}}. '),
                ('lectura_derivada', 'lectura1', 'Interpreto esa notación como una petición de derivar {{lectura1}}. '))
    for clave, identificador, prefijo in lecturas:
        if estado.get(clave):
            respuesta = replace(respuesta, narracion=prefijo + respuesta.narracion,
                citadas=respuesta.citadas + (ExpresionCitada(identificador, estado[clave]),))
    return respuesta

class FiltroContinuidadSalida(Filtro):
    nombre = "validación de continuidad y progreso"
    ruta = "caliente"

    def __init__(self, cas):
        self.cas = cas

    def _procesar(self, ctx):
        estado = ctx.continuidad
        respuesta = ctx.respuesta_generada
        aclaracion = estado.get("aclaracion")
        if aclaracion:
            respuesta = RespuestaGenerada(narracion=aclaracion, nivel_divulgacion=1)
        elif ctx.resultado_verificado and respuesta:
            narracion = re.sub(r"¿[^?]*\?", "", respuesta.narracion).strip()
            narracion = re.sub(r"[^.!?]*\?", "", narracion).strip()
            respuesta = replace(respuesta, narracion=narracion or "Tu resultado es correcto.")
        elif ctx.siguiente_objetivo and not ctx.resultado_verificado:
            objetivo = ctx.siguiente_objetivo
            if objetivo.get("tarea_id") != estado.get("activa"):
                raise ValueError("objetivo de una tarea ajena")
            respuesta = _con_pregunta(ctx, respuesta, objetivo, self.cas)
        if respuesta is None or not respuesta.narracion.strip():
            respuesta = _orientacion_sin_respuesta(ctx)
        respuesta = _con_lectura_explicita(respuesta, estado)

        problemas = respuesta.problemas()
        if problemas:
            respuesta = _recuperar_contrato(ctx, self.cas)
        if respuesta.problemas():
            raise ValueError("el respaldo de continuidad incumple el contrato")
        if respuesta.afirmaciones and not self.cas.verificar(respuesta.bloques()).aprobada:
            raise ValueError("continuidad no puede emitir afirmaciones sin comprobar")
        estado = cerrar(estado, ctx)
        recordar_material(estado, respuesta, ctx.texto_estudiante)
        return replace(ctx, continuidad=estado, respuesta_generada=respuesta,
                       respuesta=respuesta.narracion, nivel_divulgacion=respuesta.nivel_divulgacion), {
            "tarea": estado["activa"], "revision": estado["revision"],
            "objetivo": (objetivo_actual(estado) or {}).get("id", ""),
            "cierre": bool(ctx.resultado_verificado),
            "respaldo_contrato": bool(problemas), "motivos_respaldo": problemas,
        }

def _orientacion_sin_respuesta(ctx):
    texto = ctx.texto_estudiante.lower()
    if (ctx.continuidad or {}).get('acto') == 'dialogar' and ('ln' in texto or 'logaritmo' in texto):
        narracion = ('Podemos continuar con derivación logarítmica manteniendo la función original. '
                     'Separa el logaritmo del producto y del cociente en sumas y restas; '
                     'al derivar cada logaritmo compuesto, incluye la derivada de su argumento. '
                     'Escribe el paso que quieres comprobar y lo revisamos antes de cerrar el ejercicio.')
    elif ctx.ejercicio_activo:
        narracion = ('Conservo el ejercicio y los avances comprobados. Esta explicación no superó la revisión '
                     'matemática, así que necesito un paso más preciso. Escribe la expresión que estás '
                     'derivando o la propuesta que quieres comprobar.')
    else:
        narracion = 'Necesito el enunciado y la operación que quieres trabajar para ayudarte con precisión.'
    return RespuestaGenerada(narracion=narracion, nivel_divulgacion=1)

def _recuperar_contrato(ctx, cas):
    if ctx.resultado_verificado:
        cierre = RespuestaGenerada.desde_acierto_verificado(ctx)
        if cierre and not cierre.problemas() and cas.verificar(cierre.bloques()).aprobada:
            return cierre
        return RespuestaGenerada(narracion=(
            "Tu resultado es correcto. La explicación automática no superó la revisión; "
            "conservo tu acierto y el ejercicio completado."), nivel_divulgacion=1)
    respuesta = _orientacion_sin_respuesta(ctx)
    objetivo = ctx.siguiente_objetivo
    if objetivo and objetivo.get('tarea_id') == ctx.continuidad.get('activa'):
        respuesta = _con_pregunta(ctx, respuesta, objetivo, cas)
    return respuesta
