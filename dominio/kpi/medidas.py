"""
medidas.py — Las fábricas que convierten cifras crudas en un `ResultadoKPI`
=============================================================================

El adaptador de cálculo hace `SELECT` y trae números. Aquí se decide **qué
estado merecen**, y esa decisión no puede vivir en la consulta: si cada `SELECT`
resolviera por su cuenta cuándo un denominador vacío es `sin_datos` y cuándo es
`datos_incompletos`, cuarenta indicadores tendrían cuarenta criterios.

Las tres reglas del encargo, aplicadas en un solo sitio
--------------------------------------------------------------
- **No se divide por cero.** `proporcion()` mira el denominador antes de
  dividir y devuelve `SIN_DATOS`.
- **La ausencia no se representa con cero.** Ningún camino de este módulo
  construye un `Medicion(valor=0.0)` que no venga de una división real.
- **Una muestra pequeña no se publica.** Por debajo de `muestra_minima` el
  estado es `MUESTRA_INSUFICIENTE` y el valor se retira, aunque la división
  haya salido bien.

El orden de las comprobaciones es la parte que importa
--------------------------------------------------------------
1. instrumentación —si nadie produce el dato, lo demás no se llegó a medir—;
2. faltantes —un hueco conocido invalida la cifra aunque la muestra baste—;
3. denominador cero;
4. muestra mínima;
5. y sólo entonces, el valor.

Invertir 2 y 4 publicaría una proporción calculada sobre una base incompleta
por el mero hecho de que la parte observada fuera grande.


"""

from __future__ import annotations

from dominio.kpi.contratos import (
    ContextoDeCalculo,
    DefinicionKPI,
    EstadoKPI,
    Instrumentacion,
    KPIInvalido,
    Medicion,
    ResultadoKPI,
    Unidad,
)
from dominio.kpi.interpretacion import VERSION_INTERPRETACION, redactar

#: La limitación que acompaña a todo indicador de este catálogo. Se añade
#: siempre porque describe cómo se atribuye la actividad, y esa atribución es
#: la misma para los cuarenta.
LIMITACION_ATRIBUCION = (
    "La actividad se atribuye mediante clase_matricula_historial al intervalo "
    "vigente en el instante del turno; las filas preexistentes a la migración 18 "
    "no prueban una clase anterior a la fecha que conservan."
)

#: La limitación de todo resultado que se publica con muestra pequeña pero
#: suficiente. Es honestidad, no una excusa: un piloto trabaja con cursos de
#: pocas decenas y una proporción sobre seis casos se mueve mucho.
LIMITACION_MUESTRA_PEQUENA = (
    "La muestra publicada es pequeña: una observación más o menos mueve el "
    "resultado de forma apreciable."
)


def _exigir_unidad(definicion: DefinicionKPI, esperada: bool, fabrica: str) -> None:
    """Que la fábrica corresponda a la unidad declarada en el catálogo.

    ⚠️ **Lo encontró una prueba, y no es cosmético.** `conteo()` aplicado a un
    indicador declarado como proporción redactó «Clases sin actividad: 300,0 %»
    a partir de tres clases: la interpretación elige su plantilla por la unidad
    del catálogo, así que una fábrica equivocada no produce un número raro,
    produce **otra magnitud** con aspecto correcto.

    Levanta `KPIInvalido` porque es un error de programación del adaptador, no
    un desenlace del dato: no hay ningún estado de los siete que describa «el
    cálculo llamó a la fábrica equivocada».
    """
    es_proporcion = definicion.unidad is Unidad.PROPORCION
    if es_proporcion is not esperada:
        raise KPIInvalido(
            f"«{definicion.codigo}» está declarado en unidad "
            f"«{definicion.unidad.value}» y se calculó con {fabrica}()"
        )


def _armar(
    definicion: DefinicionKPI,
    contexto: ContextoDeCalculo,
    estado: EstadoKPI,
    medicion: Medicion,
) -> ResultadoKPI:
    """El único sitio donde se construye un `ResultadoKPI`.

    Une las limitaciones del catálogo con las transversales y pide la
    interpretación. Que sea el único camino es lo que garantiza que ninguna
    cifra llegue sin frase ni sin límites.
    """
    limitaciones = [*definicion.limitaciones, LIMITACION_ATRIBUCION]
    if (
        estado is EstadoKPI.DISPONIBLE
        and medicion.muestra
        and medicion.muestra < definicion.muestra_minima * 2
    ):
        limitaciones.append(LIMITACION_MUESTRA_PEQUENA)
    return ResultadoKPI(
        definicion=definicion,
        contexto=contexto,
        estado=estado,
        medicion=medicion,
        interpretacion=redactar(definicion, estado, medicion),
        version_interpretacion=VERSION_INTERPRETACION,
        limitaciones=tuple(limitaciones),
    )


def no_instrumentado(definicion: DefinicionKPI, contexto: ContextoDeCalculo) -> ResultadoKPI:
    """El indicador existe en el catálogo y nadie produce todavía su dato.

    Se construye desde la propia definición y no recibe cifras: si las
    recibiera, alguien acabaría pasándole el cero que el encargo prohíbe.
    """
    estado = (
        EstadoKPI.CALCULO_NO_APLICABLE
        if definicion.instrumentacion is Instrumentacion.EXCLUIDO_POR_DECISION
        else EstadoKPI.NO_INSTRUMENTADO
    )
    return _armar(definicion, contexto, estado, Medicion())


def sin_datos(definicion: DefinicionKPI, contexto: ContextoDeCalculo) -> ResultadoKPI:
    """La consulta corrió y no encontró observaciones. No es un cero."""
    return _armar(definicion, contexto, EstadoKPI.SIN_DATOS, Medicion())


def error_de_calidad(
    definicion: DefinicionKPI, contexto: ContextoDeCalculo, motivo: str
) -> ResultadoKPI:
    """Los datos se contradicen: publicar el valor afirmaría lo que la base niega."""
    return _armar(
        definicion,
        contexto,
        EstadoKPI.ERROR_DE_CALIDAD,
        Medicion(advertencias=(motivo,)),
    )


def proporcion(
    definicion: DefinicionKPI,
    contexto: ContextoDeCalculo,
    partes: tuple[float, float],
    faltantes: int = 0,
) -> ResultadoKPI:
    """Un numerador sobre un denominador, con las cinco comprobaciones en orden.

    `partes` es `(numerador, denominador)` y viaja junta porque una de las dos
    sin la otra no dice nada; separarlas en dos parámetros invitaba a llamarlas
    al revés.
    """
    numerador, denominador = partes
    _exigir_unidad(definicion, True, "proporcion")
    if not definicion.calculable:
        return no_instrumentado(definicion, contexto)
    base = Medicion(
        numerador=numerador,
        denominador=denominador,
        muestra=int(denominador),
        faltantes=faltantes,
    )
    if faltantes:
        return _armar(definicion, contexto, EstadoKPI.DATOS_INCOMPLETOS, base)
    if denominador <= 0:
        # Conservar los conteos observados permite explicar la falta de
        # oportunidades; el porcentaje permanece nulo, nunca cero inventado.
        if definicion.codigo in {"conductual.ansiedad_matematica", "aprendizaje.concepciones_dos_niveles", "conductual.reiteracion_tras_correccion"}:
            return _armar(definicion, contexto, EstadoKPI.SIN_DATOS, base)
        return sin_datos(definicion, contexto)
    if numerador > denominador:
        return error_de_calidad(
            definicion,
            contexto,
            f"el numerador ({_entero(numerador)}) supera al denominador "
            f"({_entero(denominador)})",
        )
    if int(denominador) < definicion.muestra_minima:
        return _armar(definicion, contexto, EstadoKPI.MUESTRA_INSUFICIENTE, base)
    return _armar(
        definicion,
        contexto,
        EstadoKPI.DISPONIBLE,
        Medicion(
            valor=numerador / denominador,
            numerador=numerador,
            denominador=denominador,
            muestra=int(denominador),
        ),
    )


def conteo(
    definicion: DefinicionKPI,
    contexto: ContextoDeCalculo,
    valor: int,
    poblacion: int,
    detalle: dict | None = None,
) -> ResultadoKPI:
    """Un recuento sobre una población declarada.

    ⚠️ **`poblacion` es obligatoria, y lo encontró una prueba.** Un conteo de
    cero significa dos cosas distintas y sólo quien llama sabe cuál: «ninguna
    de las doce clases quedó sin actividad» es una medición, y «no hay ninguna
    clase» es la ausencia de población. Sin este parámetro, los dos casos
    salían como `DISPONIBLE` con valor `0`, que es exactamente el cero
    silencioso que el encargo prohíbe.

    Con población, el cero que se publica es siempre el primero: se contó, y
    dio cero. El segundo caso responde `sin_datos`.
    """
    _exigir_unidad(definicion, False, "conteo")
    if not definicion.calculable:
        return no_instrumentado(definicion, contexto)
    if poblacion <= 0:
        return sin_datos(definicion, contexto)
    base = Medicion(muestra=poblacion, detalle=detalle or {})
    if poblacion < definicion.muestra_minima:
        return _armar(definicion, contexto, EstadoKPI.MUESTRA_INSUFICIENTE, base)
    return _armar(
        definicion,
        contexto,
        EstadoKPI.DISPONIBLE,
        Medicion(valor=float(valor), muestra=poblacion, detalle=detalle or {}),
    )


def distribucion(
    definicion: DefinicionKPI,
    contexto: ContextoDeCalculo,
    mediana: float | None,
    percentiles: dict,
) -> ResultadoKPI:
    """Una mediana con sus percentiles. El valor publicado es la mediana.

    `percentiles` lleva `observaciones` porque una mediana sin saber sobre
    cuántos casos se calculó no se puede leer, y es lo que decide si la muestra
    alcanza el mínimo distribucional del indicador.
    """
    _exigir_unidad(definicion, False, "distribucion")
    if not definicion.calculable:
        return no_instrumentado(definicion, contexto)
    observaciones = int(percentiles.get("observaciones") or 0)
    if observaciones <= 0 or mediana is None:
        return sin_datos(definicion, contexto)
    base = Medicion(muestra=observaciones, detalle=dict(percentiles))
    if observaciones < definicion.muestra_minima:
        return _armar(definicion, contexto, EstadoKPI.MUESTRA_INSUFICIENTE, base)
    return _armar(
        definicion,
        contexto,
        EstadoKPI.DISPONIBLE,
        Medicion(valor=float(mediana), muestra=observaciones, detalle=dict(percentiles)),
    )


def _entero(valor: float) -> str:
    return str(int(valor)) if float(valor).is_integer() else f"{valor:.2f}"
