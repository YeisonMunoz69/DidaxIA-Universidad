"""Instrumentos preliminares: especificación y puntuación, sin recolector implícito.

Los casos sintéticos prueban aritmética, no validan constructos. Ninguna función
de este módulo lee personas ni activa recolección o cambia permisos.
"""
from __future__ import annotations

from math import isfinite
from statistics import median

VERSION = "instrumentos.prototipo.v1.1"
ETIQUETA = "Instrumento-Prototipo"
FUNDAMENTO = (
    "Construcción técnica fundamentada en definiciones operacionales, fuentes explícitas, "
    "reglas reproducibles y pruebas de casos límite. Fórmulas preliminares: todavía "
    "requieren revisión académica, contraste externo y calibración; no son escalas validadas."
)

# Cada familia tiene una única fórmula, usada por la ficha y el puntuador.
FAMILIAS = {
    "proporcion": (r"p=\frac{x}{n}", "p = x / n", {"x": "casos que cumplen el criterio", "n": "oportunidades elegibles con seguimiento completo"}, "6 de 10 oportunidades: 6/10 = 0,60 (60%)."),
    "ordinal": (r"\begin{aligned}S_i&=100\frac{\sum_{j=1}^{m}(r_{ij}-1)}{4m}\\M&=\operatorname{mediana}_i(S_i)\end{aligned}", "S_i = 100 × suma(r_ij − 1) / (4m); M = mediana(S_i)", {"r_{ij}": "respuesta de la persona i al ítem j, de 1 (nunca) a 5 (siempre)", "m": "tres ítems respondidos; todos orientados en el mismo sentido", "S_i": "puntuación individual completa", "M": "mediana entre personas; cada persona pesa igual"}, "Respuestas 2, 3 y 4: 100 × (1+2+3)/12 = 50 puntos. Si las puntuaciones individuales son 25, 50 y 75, la mediana del grupo es 50."),
    "transferencia": (r"T=\frac{1}{n}\sum_{i=1}^{n}\frac{\min(a_i,b_i)}{2}", "T = media(min(a_i,b_i) / 2)", {"a_i": "rúbrica de conversión de representación, 0–2", "b_i": "rúbrica de justificación de la correspondencia, 0–2", "n": "estudiantes con ambos criterios observados"}, "Dos estudiantes: (2,1) y (2,2) dan (0,5+1)/2 = 0,75. La justificación limita el resultado."),
    "preferencia": (r"\begin{aligned}P_l&=\frac{n_l}{\sum_k n_k}\\l^*&=\arg\max_l n_l\end{aligned}", "P_l = n_l / total; salida principal = proporción del nivel modal", {"n_l": "solicitudes voluntarias del nivel l: sondeo, regla o desarrollo"}, "2 sondeos, 3 reglas y 5 desarrollos: 20%, 30%, 50%; nivel modal desarrollo. Un empate se conserva."),
    "pareado": (r"\Delta=\operatorname{mediana}_{i\in P}(S_{i,2}-S_{i,1})", "Δ = mediana de diferencias individuales pareadas", {"P": "personas con dos mediciones del mismo constructo, instrumento y versión", "S_{i,t}": "puntuación de la persona i en el momento t"}, "Pares 40→50, 60→55, 30→40: diferencias 10, −5, 10; mediana 10 puntos."),
}


def _ficha(familia, pregunta, criterio, recoleccion, items=()):
    latex, formula, simbolos, ejemplo = FAMILIAS[familia]
    return dict(familia=familia, pregunta=pregunta, criterio=criterio,
                recoleccion=recoleccion, items=list(items), formula_latex=latex,
                formula=formula, simbolos=simbolos, ejemplo=ejemplo, version=VERSION)


PROPUESTAS = {
    "aprendizaje.cobertura_conceptual": _ficha("proporcion", "¿Qué parte de los conceptos planificados tuvo trabajo verificable?", "x: conceptos distintos del plan con intento vinculado; n: conceptos del plan congelado de la clase. No usar el corpus completo como denominador.", "Plan conceptual versionado por clase y evento intento vinculado a concepto; revisión de la atribución automática."),
    "aprendizaje.recurrencia_concepciones": _ficha("proporcion", "¿Reaparece la misma concepción en otra oportunidad comparable?", "Una unidad por pareja estudiante–concepción; seguimiento en una sesión posterior con ítem comparable. x: recurrencias confirmadas; n: parejas reevaluadas.", "Diagnóstico con rúbrica, código de concepción, sesión y una segunda comprobación; conservar no reevaluados aparte."),
    "aprendizaje.resolucion_posterior": _ficha("proporcion", "¿Se resuelve una dificultad previamente comprobada?", "x: parejas estudiante–concepción con respuesta y justificación correctas en la siguiente comprobación; n: parejas reevaluadas. La unidad no es cada intento.", "Banco de ítems equivalentes posteriores, versión, rúbrica, ayudas recibidas y evaluación humana o simbólica verificable."),
    "aprendizaje.transferencia_representacion": _ficha("transferencia", "¿Puede convertir una representación y justificar su correspondencia?", "0: respuesta incorrecta; 1: parcial; 2: completa. El mínimo evita compensar una justificación ausente con una conversión correcta.", "Tarea con registros origen/destino, rúbrica doble, evaluador y versión. Un blanco se registra ausente, no como 0."),
    "recuperacion.precision_auditada": _ficha("proporcion", "¿Qué proporción del material recuperado es pertinente según revisión independiente?", "x: fragmentos pertinentes; n: fragmentos con juicio resuelto. Muestrear turnos antes de conocer el resultado; conservar desacuerdos y no revisados.", "Juicios ciegos de dos revisores sobre pareja turno–fragmento, versión de corpus, criterio de pertinencia y adjudicación. Similaridad vectorial no es pertinencia."),
    "supervision.reincidencia_posterior": _ficha("proporcion", "¿Reaparece la dificultad después de una aclaración docente comprobada?", "x: parejas estudiante–concepción que reinciden; n: parejas con aclaración entregada y reevaluación comparable posterior.", "Vínculo aclaración–estudiante–concepción y reevaluación; aprobar una respuesta en la cola no prueba que se entregó una aclaración."),
    "conductual.ansiedad_matematica": _ficha("ordinal", "¿Qué tensión declara la persona durante esta actividad matemática?", "Resumen descriptivo de tres respuestas; no diagnóstico. Alto: más tensión declarada. No combinar con el detector léxico.", "Autoinforme voluntario al cierre de una actividad; revisión de comprensión, autorización y contraste externo.", ("Sentí tensión al intentar resolver esta actividad.", "Me preocupó equivocarme mientras la resolvía.", "Los nervios dificultaron que explicara mi procedimiento.")),
    "conductual.miedo_a_preguntar": _ficha("ordinal", "¿Qué inhibición declara al pedir ayuda cuando la necesita?", "Aplicar solo cuando necesitó ayuda. Alto: mayor inhibición declarada; N/A si no necesitó ayuda.", "Tres ítems voluntarios sobre una actividad delimitada; distinguir ayuda humana y ayuda del tutor.", ("Me costó expresar una duda por temor a que pareciera obvia.", "Evité preguntar por preocupación sobre cómo juzgarían mi duda.", "Me dio vergüenza mostrar el paso que no entendía.")),
    "conductual.evitacion": _ficha("ordinal", "¿Declara posponer la tarea por la dificultad percibida?", "No confundir bloqueo de acceso, falta de tiempo o cierre de clase con evitación. Alto: más evitación declarada.", "Autoinforme de actividad y registro separado de barreras técnicas/tiempo.", ("Pospuse comenzar porque la tarea me parecía difícil.", "Preferí alejarme de la actividad antes de intentar un paso.", "Dejé de intentar por querer evitar la dificultad de la tarea.")),
    "conductual.persistencia": _ficha("proporcion", "¿Continúa con otro intento después de un error comprobado?", "x: tareas con nuevo intento en 24 horas desde el primer error; n: tareas con primer error y 24 horas observadas. Una oportunidad por tarea.", "actividad.iniciada, intento.evaluado, intento.enviado; exclusión explícita de retiro, fin programado y fallo técnico. Ventana preliminar 24 h: revisar antes de recoger datos."),
    "conductual.busqueda_de_ayuda": _ficha("proporcion", "¿Solicita ayuda voluntaria antes de ver la solución completa?", "x: tareas con solicitud autónoma previa a solución; n: tareas iniciadas con ayuda disponible. Una oportunidad por tarea.", "ayuda.solicitada con nivel elegido, instante, tarea y origen voluntario; registrar exposición a solución completa."),
    "conductual.abandono_de_conversacion": _ficha("proporcion", "¿Qué conversaciones no registran otro turno durante siete días?", "x: conversaciones sin otro turno educativo en el mismo hilo durante siete días desde la primera respuesta; n: conversaciones con seguimiento íntegro de siete días antes del corte. Un hilo terminado correctamente también puede quedar sin retorno.", "Historial de turnos educativos completos, sesión y matrícula vigente. La ventana de siete días es preliminar; la medida describe ausencia de retorno, no intención ni tarea inconclusa."),
    "conductual.tolerancia_al_error": _ficha("ordinal", "¿Cómo declara afrontar el error durante esta actividad?", "Alto: mayor tolerancia declarada; aplicar solo si reconoce un error. N/A si no hubo error observado por la persona.", "Autoinforme breve voluntario tras una oportunidad de error; contraste con observación independiente.", ("Pude revisar mi procedimiento después de equivocarme.", "Acepté el error como parte de intentar resolver la actividad.", "Pude considerar otra forma de resolver después del error.")),
    "conductual.recuperacion_tras_error": _ficha("proporcion", "¿Alcanza una respuesta justificada después de un error comprobado?", "x: tareas con respuesta y justificación correctas dentro de 24 h; n: tareas con primer error y seguimiento completo de 24 h. Informar ayudas aparte.", "Intentos evaluados con tarea y rúbrica estable; no sustituir por confirmación de autocorrección de interfaz."),
    "conductual.preferencia_niveles_ayuda": _ficha("preferencia", "¿Qué nivel elige cuando se le ofrece una elección real?", "Publicar distribución y todos los niveles empatados en la moda; no promediar categorías ordinales ni sustituir elección por nivel recibido.", "ayuda.solicitada con elección explícita sondeo/regla/desarrollo y opciones realmente disponibles."),
    "conductual.cambio_longitudinal_cohorte": _ficha("pareado", "¿Cómo cambia el mismo indicador en las mismas personas?", "Un constructo por análisis; dos aplicaciones equivalentes. Publicar pares completos y pérdidas. Sin medida inicial no hay cambio estimable.", "Dos aplicaciones del mismo instrumento/versionado, vínculo autorizado y ventanas predefinidas. La ficha final sola no proporciona el par."),
}

PROPUESTAS["conductual.abandono_de_conversacion"].update(
    numerador="conversaciones elegibles sin otro turno educativo completo del mismo hilo durante los siete días posteriores a su primera respuesta",
    denominador="conversaciones educativas con primera respuesta en el periodo y siete días completos antes del corte",
    simbolos={
        "x": "conversaciones elegibles sin retorno registrado en el mismo hilo durante siete días",
        "n": "conversaciones con ventana íntegra de siete días desde la primera respuesta",
        "p": "fracción x/n; se presenta como porcentaje",
    },
    ejemplo="Cuatro hilos sin retorno entre diez con seguimiento completo: p=4/10=0,40 (40%). Dos hilos recientes quedan censurados y no entran en n.",
    alto="Más conversaciones no registraron otro turno durante siete días; puede incluir tareas terminadas y barreras de acceso.",
    bajo="Más conversaciones sí registraron continuidad en siete días; por sí solo tampoco demuestra persistencia ante errores.",
)


def _puntuar_criterios(familia, obs):
    cantidad = 3 if familia == "ordinal" else 2
    if not isinstance(obs, (list, tuple)) or len(obs) != cantidad:
        raise ValueError("cantidad de criterios incorrecta")
    presentes = [v for v in obs if v is not None]
    if any(type(v) not in (int, float) or not isfinite(v) for v in presentes):
        raise ValueError("puntuaciones finitas requeridas")
    limite = 5 if familia == "ordinal" else 2 if familia == "transferencia" else 100
    piso = 1 if familia == "ordinal" else 0
    if any(not piso <= v <= limite or (familia != "pareado" and int(v) != v) for v in presentes):
        raise ValueError("puntuación fuera de escala")
    if len(presentes) != cantidad:
        return None
    if familia == "ordinal":
        return 100 * sum(v - 1 for v in obs) / 12
    if familia == "transferencia":
        return min(obs) / 2
    return obs[1] - obs[0]


def _puntuar_observacion(familia, obs, niveles):
    if obs is None:
        return None
    if familia == "proporcion":
        if type(obs) is not bool:
            raise ValueError("se requiere un juicio booleano por oportunidad")
        return float(obs)
    if familia == "preferencia":
        if not isinstance(obs, str) or obs not in niveles:
            raise ValueError("nivel no válido")
        niveles[obs] += 1
        return 1
    return _puntuar_criterios(familia, obs)


def puntuar(codigo: str, observaciones: list, *, minimo: int = 1) -> dict:
    """Puntuador prospectivo de datos YA rubricados; no infiere etiquetas.

    None es faltante. La preparación de oportunidades y la autorización son
    responsabilidad de un recolector futuro, que todavía no se activa.
    """
    familia = PROPUESTAS[codigo]["familia"]
    if type(minimo) is not int or minimo < 1:
        raise ValueError("mínimo debe ser entero positivo")
    valores = []
    faltantes = 0
    niveles = dict.fromkeys(("sondeo", "regla", "desarrollo"), 0)
    for obs in observaciones:
        puntuacion = _puntuar_observacion(familia, obs, niveles)
        if puntuacion is None:
            faltantes += 1
        else:
            valores.append(puntuacion)
    n = len(valores)
    estado = "sin_datos" if not n else "muestra_insuficiente" if n < minimo else "disponible"
    valor = None
    if estado == "disponible":
        valor = median(valores) if familia in ("ordinal", "pareado") else sum(valores) / n
        if familia == "preferencia":
            valor = max(niveles.values()) / n
    return dict(version=VERSION, estado=estado, valor=valor, muestra=n,
                faltantes=faltantes, valores_individuales=valores,
                distribucion={k: v / n if n else None for k, v in niveles.items()} if familia == "preferencia" else {},
                niveles_modales=[k for k, v in niveles.items() if v == max(niveles.values())] if familia == "preferencia" and n else [])
