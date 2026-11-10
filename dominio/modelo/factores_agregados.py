from collections import defaultdict
from dataclasses import replace

from dominio.kpi import catalogo, medidas
from dominio.kpi.dimensiones.hibridos import CODIGOS
from dominio.modelo.analisis_conductual import analizar_conversacion
from dominio.modelo.factores_conductuales import NOMBRES, VERSION
from dominio.modelo.fusion_conductual import lectura_guardada


def resumir_factores(registros, *, desde, hasta):
    lecturas = [
        r
        for r in registros
        if desde <= r["momento"] < hasta
        and lectura_guardada(r.get("analisis_semantico"), r["mensaje"])
    ]
    fechas = [r["analizado_en"].isoformat() for r in lecturas if r.get("analizado_en")]
    origenes = {
        o: sum(r.get("origen_analisis") == o for r in lecturas) for o in ("turno", "relectura")
    }
    modelos = sorted({r["analisis_semantico"].get("modelo", "") for r in lecturas})
    hilos = defaultdict(list)
    for r in registros:
        hilos[(r["estudiante"], r["sesion"])].append(r)
    totales = {
        f: dict(
            factor=f,
            numerador=0,
            denominador=0,
            oportunidades=0,
            no_concluyentes=0,
            provisionales=0,
            analizados_semantica=0,
            reglas_numerador=0,
            mensajes=0,
            sin_lectura=0,
            sin_oportunidad=0,
            rectificaciones_matematicas=0,
            origenes_lecturas=origenes,
            ultima_lectura=max(fechas, default=None),
            modelos_analisis=modelos,
        )
        for f in NOMBRES
    }
    for hilo in hilos.values():
        turnos = sorted(hilo, key=lambda r: (r["momento"], r.get("historial", r["turno"])))
        resumen = analizar_conversacion(turnos, desde=desde, hasta=hasta)
        for f in resumen["factores"]:
            total = totales[f["factor"]]
            for k in (
                "numerador",
                "denominador",
                "oportunidades",
                "no_concluyentes",
                "provisionales",
                "analizados_semantica",
                'sin_lectura',
                'sin_oportunidad',
                'rectificaciones_matematicas',
            ):
                total[k] += f[k]
            total["reglas_numerador"] += f["reglas"]["numerador"]
            total["mensajes"] += resumen["mensajes_completos"]
    return totales

def calcular_factores(resumen, contexto, *, individual=False):
    resultados = []
    for factor, codigo in CODIGOS.items():
        dato = resumen.get(factor, {})
        definicion = catalogo.buscar(codigo)
        if individual:
            definicion = replace(
                definicion,
                muestra_minima=1,
                instrumento=replace(definicion.instrumento, minimo_de_observaciones=1),
            )
        resultado = medidas.proporcion(
            definicion, contexto, (dato.get("numerador", 0), dato.get("denominador", 0))
        )
        pendientes = dato.get("no_concluyentes", 0)
        n, x = dato.get("denominador", 0), dato.get("numerador", 0)
        detalle = {
            **dato,
            "version_analisis": VERSION,
            'revision_calculo': 'contraste-matematico.v2',
            "motivo_cobertura": f"{x} detecciones corroboradas de {n} oportunidades concluyentes. "
            f"{dato.get('analizados_semantica', 0)} de {dato.get('mensajes', 0)} mensajes tienen lectura semántica; "
            f"{dato.get('sin_lectura', 0)} aún no tienen lectura y {dato.get('sin_oportunidad', 0)} no ofrecen una oportunidad para este factor. "
            f"{dato.get('rectificaciones_matematicas', 0)} detecciones iniciales se rectificaron mediante contrastes matemáticos explícitos. "
            f"{pendientes} oportunidades pendientes o no concluyentes y "
            f"{dato.get('provisionales', 0)} coincidencias provisionales quedan fuera del porcentaje. "
            "Sin oportunidades concluyentes no se publica un porcentaje; cero no demuestra ausencia del factor.",
            "cobertura_semantica": (
                dato.get("analizados_semantica", 0) / dato["mensajes"]
                if dato.get("mensajes")
                else None
            ),
        }
        resultados.append(replace(resultado, medicion=replace(resultado.medicion, detalle=detalle)))
    return resultados
