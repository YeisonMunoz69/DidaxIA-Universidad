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


LIMITACION_ATRIBUCION = (
    "La actividad se atribuye mediante clase_matricula_historial al intervalo "
    "vigente en el instante del turno; las filas preexistentes a la migración 18 "
    "no prueban una clase anterior a la fecha que conservan."
)


LIMITACION_MUESTRA_PEQUENA = (
    "La muestra publicada es pequeña: una observación más o menos mueve el "
    "resultado de forma apreciable."
)


def _exigir_unidad(definicion: DefinicionKPI, esperada: bool, fabrica: str) -> None:
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
    estado = (
        EstadoKPI.CALCULO_NO_APLICABLE
        if definicion.instrumentacion is Instrumentacion.EXCLUIDO_POR_DECISION
        else EstadoKPI.NO_INSTRUMENTADO
    )
    return _armar(definicion, contexto, estado, Medicion())

def sin_datos(definicion: DefinicionKPI, contexto: ContextoDeCalculo) -> ResultadoKPI:
    return _armar(definicion, contexto, EstadoKPI.SIN_DATOS, Medicion())

def error_de_calidad(
    definicion: DefinicionKPI, contexto: ContextoDeCalculo, motivo: str
) -> ResultadoKPI:

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
