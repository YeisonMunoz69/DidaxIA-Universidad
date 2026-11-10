from dominio.modelo.factores_conductuales import VERSION, validar_factores


def lectura_guardada(datos, mensaje):
    if not isinstance(datos, dict) or datos.get("version") != VERSION or datos.get("error"):
        return {}
    try:
        return {o.factor: o.como_dict() for o in validar_factores(datos.get("observaciones"), mensaje)}
    except ValueError:
        return {}

def combinar(factor, regla, semantica, oportunidad):
    estado = "no_concluyente"
    fuente = "pendiente"
    motivo = "Sin análisis semántico evaluable; el silencio de las reglas no demuestra ausencia."
    evidencia = ""
    if semantica:
        evidencia, motivo = semantica["evidencia"], semantica["motivo"]
        if factor == "preconcepciones":
            oportunidad = semantica["oportunidad"]
        estado = semantica["estado"]
        fuente = "semantica"
        if estado != "no_concluyente" and regla == (estado == "detectado"):
            fuente = "acuerdo"
    if estado == "no_concluyente" and regla:
        fuente = "reglas_provisional"
        motivo = "Coincidencia de reglas pendiente de corroboración semántica."
    if not oportunidad:
        estado, motivo = "sin_oportunidad", "No existe una oportunidad evaluable para este factor en el turno."
    return {"estado": estado, "fuente": fuente, "regla": regla,
            'contraste_matematico': semantica.get('contraste_matematico', False),
            "semantica": semantica.get("estado") if semantica else None,
            "oportunidad": oportunidad, "evidencia": evidencia, "motivo": motivo}
