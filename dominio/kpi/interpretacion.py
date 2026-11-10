from __future__ import annotations

from typing import Final

from dominio.kpi.contratos import DefinicionKPI, EstadoKPI, Medicion, Unidad


VERSION_INTERPRETACION: Final = "interpretacion.v1.1"


SIN_CAUSALIDAD: Final = (
    "Describe una diferencia observada entre dos periodos; no permite inferir "
    "una causa."
)


def _porcentaje(valor: float) -> str:
    return f"{valor * 100:.1f}".replace(".", ",")

def _cifra(valor: float) -> str:
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.1f}".replace(".", ",")

def _cifra_tiempo(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")

def _frase_disponible(definicion: DefinicionKPI, medicion: Medicion) -> str:
    valor = medicion.valor
    if valor is None:
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
