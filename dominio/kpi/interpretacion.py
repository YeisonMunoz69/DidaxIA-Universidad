"""
interpretacion.py — La frase que acompaña a una cifra, escrita por reglas
==========================================================================

El encargo de la Fase 8 es tajante: *«la interpretación no puede ser una frase
genérica ni texto inventado por un modelo sin trazabilidad. Implementa reglas
versionadas y comprobables»*.

Este módulo es esa implementación. Recibe un estado, unas cifras y una
definición, y devuelve una frase. **La misma entrada produce siempre la misma
salida**, así que una prueba puede afirmar el texto exacto y un informe puede
reproducirse dentro de un año.

Por qué no la escribe el proveedor de lenguaje
--------------------------------------------------------
Porque una interpretación es una afirmación sobre datos de personas, y el
sistema ya distingue en cada bloque de respuesta lo `verificado` de lo
`generado` (`ADR-014` §5.1). Una frase generada dentro de un informe
institucional no llevaría ese sello, no se podría reproducir y no se podría
auditar. Se elige perder matiz a cambio de poder responder «¿de dónde salió esta
frase?» con un número de versión y una regla.

Lo que estas reglas NO dicen, y es deliberado
-----------------------------------------------------
**Nunca una causa.** «Subió después de actualizar el corpus» describe dos
hechos en orden; «subió porque se actualizó el corpus» afirma una causalidad
que un agregado observacional no sostiene. `comparar()` redacta lo primero y
añade siempre el límite explícito.

**Nunca un juicio sobre una persona.** Las frases hablan de proporciones,
denominadores y periodos. Ningún texto de aquí califica a un estudiante o a un
docente, y por eso tampoco existe una redacción de «bajo rendimiento».


"""

from __future__ import annotations

from typing import Final

from dominio.kpi.contratos import DefinicionKPI, EstadoKPI, Medicion, Unidad

#: Sube cuando cambia una redacción. Viaja dentro de cada resultado para que
#: dos informes con textos distintos se puedan distinguir sin compararlos letra
#: a letra.
VERSION_INTERPRETACION: Final = "interpretacion.v1.1"

#: El límite que acompaña a toda comparación entre periodos. Se repite en cada
#: frase a propósito: una advertencia que sólo aparece en el pie del informe no
#: viaja con la cifra cuando alguien la copia a una diapositiva.
SIN_CAUSALIDAD: Final = (
    "Describe una diferencia observada entre dos periodos; no permite inferir "
    "una causa."
)


def _porcentaje(valor: float) -> str:
    """Una proporción con un decimal, en coma decimal como se escribe aquí."""
    return f"{valor * 100:.1f}".replace(".", ",")


def _cifra(valor: float) -> str:
    """Un número sin decimales cuando es entero; con uno cuando no lo es."""
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.1f}".replace(".", ",")


def _cifra_tiempo(valor: float) -> str:
    """La mediana en horas conserva dos decimales, igual que la tarjeta.

    Con un solo decimal, una decisión de 0,02 horas se describía como 0,0
    horas, en aparente contradicción con el valor publicado.
    """
    return f"{valor:.2f}".replace(".", ",")


def _frase_disponible(definicion: DefinicionKPI, medicion: Medicion) -> str:
    valor = medicion.valor
    if valor is None:  # pragma: no cover — `_exigir_coherencia` ya lo impide
        raise ValueError("un resultado disponible sin valor no debería existir")
    if definicion.unidad is Unidad.PROPORCION:
        cuerpo = f"{_porcentaje(valor)} %"
        if medicion.numerador is not None and medicion.denominador is not None:
            cuerpo += (
                f" ({_cifra(medicion.numerador)} de {_cifra(medicion.denominador)})"
            )
        return f"{definicion.nombre}: {cuerpo} en el periodo consultado."
    sufijo = {
        Unidad.CONTEO: "",
        Unidad.DIAS: " días",
        Unidad.HORAS: " horas",
        Unidad.TURNOS: " turnos",
        Unidad.PUNTUACION: " puntos",
    }[definicion.unidad]
    cifra = _cifra_tiempo(valor) if definicion.unidad is Unidad.HORAS else _cifra(valor)
    return f"{definicion.nombre}: {cifra}{sufijo} en el periodo consultado."


def _frase_sin_datos(definicion: DefinicionKPI) -> str:
    return (
        f"{definicion.nombre}: no hubo observaciones en el periodo consultado. "
        f"No es un cero: la población elegible ({definicion.poblacion_elegible}) "
        f"no produjo ninguna."
    )


def _frase_no_instrumentado(definicion: DefinicionKPI) -> str:
    return (
        f"{definicion.nombre}: no se calcula porque todavía no se produce el "
        f"dato que necesita. Falta: {definicion.falta}"
    )


def _frase_muestra_insuficiente(definicion: DefinicionKPI, medicion: Medicion) -> str:
    return (
        f"{definicion.nombre}: se observaron {medicion.muestra} casos y el "
        f"mínimo publicable es {definicion.muestra_minima}. El valor no se "
        f"publica para no describir el ruido de una muestra pequeña."
    )


def _frase_datos_incompletos(definicion: DefinicionKPI, medicion: Medicion) -> str:
    return (
        f"{definicion.nombre}: faltan {medicion.faltantes} registros necesarios "
        f"para el cálculo, de {_cifra(medicion.denominador or 0)} considerados. "
        f"El valor no se publica mientras el hueco no se pueda acotar."
    )


def _frase_no_aplicable(definicion: DefinicionKPI) -> str:
    return f"{definicion.nombre}: no aplica a esta consulta. Motivo: {definicion.falta}"


def _frase_error_de_calidad(definicion: DefinicionKPI, medicion: Medicion) -> str:
    detalle = "; ".join(medicion.advertencias) or "la base devolvió cifras incompatibles"
    return (
        f"{definicion.nombre}: los datos se contradicen y el valor no se "
        f"publica. {detalle}."
    )


def redactar(definicion: DefinicionKPI, estado: EstadoKPI, medicion: Medicion) -> str:
    """La frase de este resultado. Determinista, y probada por igualdad exacta.

    Un `match` y no un diccionario de funciones: los siete estados están
    enumerados aquí, de modo que añadir un octavo rompa esta función en vez de
    caer en una rama por defecto que redactaría algo plausible y falso.
    """
    match estado:
        case EstadoKPI.DISPONIBLE:
            return _frase_disponible(definicion, medicion)
        case EstadoKPI.SIN_DATOS:
            return _frase_sin_datos(definicion)
        case EstadoKPI.NO_INSTRUMENTADO:
            return _frase_no_instrumentado(definicion)
        case EstadoKPI.MUESTRA_INSUFICIENTE:
            return _frase_muestra_insuficiente(definicion, medicion)
        case EstadoKPI.DATOS_INCOMPLETOS:
            return _frase_datos_incompletos(definicion, medicion)
        case EstadoKPI.CALCULO_NO_APLICABLE:
            return _frase_no_aplicable(definicion)
        case EstadoKPI.ERROR_DE_CALIDAD:
            return _frase_error_de_calidad(definicion, medicion)


def comparar(definicion: DefinicionKPI, actual: float | None, previo: float | None) -> str:
    """La frase de una comparación entre dos periodos, sin afirmar una causa.

    Devuelve texto vacío cuando falta cualquiera de los dos valores: una
    comparación con un lado ausente no es una comparación, y redactar «no hay
    datos del periodo anterior» dentro del mismo campo mezclaría dos cosas que
    el consumidor tiene que poder distinguir.
    """
    if actual is None or previo is None:
        return ""
    if definicion.unidad is Unidad.PROPORCION:
        diferencia = (actual - previo) * 100
        magnitud = f"{abs(diferencia):.1f}".replace(".", ",") + " puntos porcentuales"
    else:
        diferencia = actual - previo
        magnitud = _cifra(abs(diferencia))
    if diferencia == 0:
        return f"{definicion.nombre}: igual que en el periodo anterior. {SIN_CAUSALIDAD}"
    sentido = "mayor" if diferencia > 0 else "menor"
    return (
        f"{definicion.nombre}: {magnitud} {sentido} que en el periodo anterior. "
        f"{SIN_CAUSALIDAD}"
    )
