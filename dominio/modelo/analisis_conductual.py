from collections import Counter

from dominio.deteccion.patrones import extraer
from dominio.modelo.contraste_conceptual import contrastar
from dominio.modelo.factores_conductuales import NOMBRES, VERSION
from dominio.modelo.fenomenos_anteproyecto import _intento_verificable, _metadatos, resumir_trazas
from dominio.modelo.fusion_conductual import combinar, lectura_guardada
from dominio.modelo.senales_interaccion import observar


def analizar_conversacion(turnos, *, desde=None, hasta=None):
    pendientes, decisiones, registros = {}, [], []
    for numero, turno in enumerate(turnos, 1):
        if turno.get("error") or turno.get("degradado") or not turno.get("mensaje", "").strip():
            continue
        trazas = turno.get("trazas", [])
        registros.append({"estudiante": "ensayo", "sesion": "hilo", "trazas": trazas})
        intento = _intento_verificable(trazas)
        par = _par_verificable(pendientes, intento)
        anterior = par.get("anterior")
        semantica = lectura_guardada(turno.get("analisis_semantico"), turno["mensaje"])
        if 'preconcepciones' in semantica:
            semantica['preconcepciones'] = contrastar(turno['mensaje'], semantica['preconcepciones'])
        reglas = {"PS-Anx": "PS-Anx" in extraer(turno["mensaje"]),
                  "preconcepciones": bool(observar(turno["mensaje"])["conceptos_candidatos"]),
                  "confirmacion": par.get("misma", False)}
        oportunidades = {"PS-Anx": True, "preconcepciones": reglas["preconcepciones"],
                         "confirmacion": anterior is not None}
        fila = {"turno": numero, "factores": {}}
        for factor in NOMBRES:
            fila["factores"][factor] = combinar(factor, reglas[factor], semantica.get(factor, {}), oportunidades[factor])
        if reglas["confirmacion"]:
            fila["factores"]["confirmacion"].update(
                estado="detectado", fuente="verificacion_matematica",
                motivo="Repite la misma propuesta incorrecta comprobada tras una corrección entregada.")
        if intento and intento[2] == "valida" and anterior is not None:
            fila["factores"]["confirmacion"].update(
                estado="no_detectado", fuente="verificacion_matematica",
                motivo="El nuevo resultado fue comprobado como correcto; no reitera el error.")
        if anterior is not None:
            fila["factores"]["confirmacion"]["correccion_turno"] = anterior["turno"]
        _guardar_correccion(pendientes, intento, trazas, numero)
        momento = turno.get("momento", "")
        if (desde is None or momento >= desde) and (hasta is None or momento < hasta):
            decisiones.append(fila)
    return {"version": VERSION, "alcance": "observables del diálogo; indicios, no diagnóstico personal",
            "mensajes_completos": len(decisiones), "factores": _resumir(decisiones),
            "decisiones": decisiones, "instrumento_original": resumir_trazas(registros)}

def _par_verificable(pendientes, intento):
    if intento is None:
        return {}
    base, propuesta, veredicto = intento
    anterior = pendientes.pop("".join(base.lower().split()), None)
    return {"anterior": anterior,
            "misma": bool(anterior and veredicto == "invalida"
                          and "".join(propuesta.lower().split()) == anterior["propuesta"])}

def _guardar_correccion(pendientes, intento, trazas, numero):
    if intento is None or intento[2] != "invalida":
        return

    if _metadatos(trazas, "verificación simbólica").get("correccion_del_resultado_entregada") is True:
        pendientes["".join(intento[0].lower().split())] = {
            "propuesta": "".join(intento[1].lower().split()), "turno": numero,
        }

def _resumir(decisiones):
    salida = []
    for factor, nombre in NOMBRES.items():
        filas = [d["factores"][factor] for d in decisiones]
        evaluables = [f for f in filas if f["oportunidad"]]
        concluyentes = [f for f in evaluables if f["estado"] in ("detectado", "no_detectado")]
        x = sum(f["estado"] == "detectado" for f in concluyentes)
        reglas_n = len(evaluables)
        reglas_x = sum(f["regla"] and f["oportunidad"] for f in filas)
        salida.append({"factor": factor, "nombre": nombre,
                       "numerador": x, "denominador": len(concluyentes),
                       "valor": x / len(concluyentes) if concluyentes else None,
                       "estado": "experimental" if concluyentes else "sin_datos",
                       "oportunidades": len(evaluables), "no_concluyentes": len(evaluables) - len(concluyentes),
                       "analizados_semantica": sum(f["semantica"] is not None for f in filas),
                       "sin_lectura": sum(f['semantica'] is None for f in filas),
                       "sin_oportunidad": sum(not f['oportunidad'] for f in filas),
                       'rectificaciones_matematicas': sum(f['contraste_matematico'] for f in filas),
                       "provisionales": sum(f["fuente"] == "reglas_provisional" for f in evaluables),
                       "fuentes": dict(Counter(f["fuente"] for f in evaluables)),
                       "reglas": {"numerador": reglas_x, "denominador": reglas_n,
                                  "valor": reglas_x / reglas_n if reglas_n else None}})
    return salida
