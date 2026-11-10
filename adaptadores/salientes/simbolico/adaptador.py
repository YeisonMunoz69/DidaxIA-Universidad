from __future__ import annotations

import os
import re
import time
from collections.abc import Sequence

import sympy as sp

from adaptadores.salientes.simbolico.analizador import analizar
from adaptadores.salientes.simbolico.guardia import (
    EntradaNoAdmitida,
)
from adaptadores.salientes.simbolico.limites import (
    LimiteBilateralInexistente,
    analizar_destino_del_limite,
    evaluar_limite_con_pasos,
    evaluar_valor_del_limite,
)
from adaptadores.salientes.simbolico.pasos import (
    NOTACION_POR_DEFECTO,
    NOTACIONES,
    MotorDePasos,
)
from adaptadores.salientes.simbolico.presentacion import expr_to_js
from dominio.filtros.intencion import _intento_de_limite
from dominio.modelo.matematica import (
    BloqueVerificable,
    InformeVerificacion,
    PasoDerivacion,
    Precomputo,
    Veredicto,
    Verificacion,
)

HERRAMIENTA = "sympy"


_REGLAS = (
    ("cadena", "regla de la cadena"),
    ("cociente", "regla del cociente"),
    ("producto", "regla del producto"),
    ("trigonometrica", "derivada de función trigonométrica"),
    ("exponencial", "derivada de función exponencial"),
    ("logaritmica", "derivada de función logarítmica"),
    ("potencia", "regla de la potencia"),
    ("constante", "derivada de una constante"),
)


_CONCEPCIONES = {
    "M21": "composición de funciones · regla de la cadena",
    "M22": "derivada del coseno · signo",
    "M23": "constante simbólica frente a variable",
    "M16": "conjugados en la derivada por definición",
}


_VARIABLES_CONOCIDAS = {"x", "y", "z", "t", "u", "v", "a", "b", "c", "n", "k"}


_PATRON_DERIVADA = re.compile(r"^d\s*/\s*d([A-Za-z])\b\s*(.+)$")


def _entero_de_entorno(nombre: str, defecto: int) -> int:
    try:
        return int(os.environ.get(nombre, "") or defecto)
    except ValueError:
        return defecto

ORDEN_MAXIMO = _entero_de_entorno("AGENTE_CAS_ORDEN_MAXIMO", 8)


def _como_derivada(texto: str) -> tuple[str, str] | None:
    coincidencia = _PATRON_DERIVADA.match(texto.strip())
    if not coincidencia:
        return None
    variable, resto = coincidencia.group(1), coincidencia.group(2).strip()
    if resto and resto[0] in "([" and resto[-1] == (")" if resto[0] == "(" else "]"):
        abrir, cerrar = resto[0], resto[-1]
        nivel = 0
        for i, caracter in enumerate(resto):
            nivel += (caracter == abrir) - (caracter == cerrar)
            if nivel == 0:

                if i == len(resto)-1:
                    resto = resto[1:-1].strip()
                break
    return variable, resto

def _a_notacion_corriente(expr) -> str:
    try:
        texto = sp.sstr(expr)
    except Exception:
        return ""
    return texto.replace("**", "^").replace("sin(", "sen(")

def _desplegar_primera_regla(expr: sp.Expr, variable: sp.Symbol) -> tuple[str, str]:
    try:
        numerador, denominador = sp.fraction(expr)
        if denominador != 1 and denominador.has(variable):
            intermedio = (sp.diff(numerador, variable) * denominador -
                          numerador * sp.diff(denominador, variable)) / denominador**2
            return _a_notacion_corriente(intermedio), "regla del cociente"
        if expr.is_Mul and len(expr.args) >= 2:
            primero = expr.args[0]
            resto = sp.Mul(*expr.args[1:])
            intermedio = sp.diff(primero, variable) * resto + primero * sp.diff(resto, variable)
            return _a_notacion_corriente(intermedio), "regla del producto"
        if expr.is_Pow and expr.base.has(variable) and not expr.exp.has(variable):
            intermedio = expr.exp * expr.base**(expr.exp - 1) * sp.diff(expr.base, variable)
            return _a_notacion_corriente(intermedio), "regla de la cadena"
        if expr.is_Function and len(expr.args) == 1 and expr.args[0].has(variable):
            interna = expr.args[0]
            auxiliar = sp.Symbol("_u")
            intermedio = sp.diff(expr.func(auxiliar), auxiliar).subs(auxiliar, interna) * sp.diff(interna, variable)
            return _a_notacion_corriente(intermedio), "regla de la cadena"
    except Exception:
        pass
    return "", ""

def _componentes_de_derivacion(expr: sp.Expr, variable: sp.Symbol) -> tuple[tuple[str, str, str], ...]:
    numerador, denominador = sp.fraction(expr)
    if denominador != 1 and denominador.has(variable):
        principales = (numerador, denominador)
    elif expr.is_Mul or expr.is_Add or expr.is_Function or expr.is_Pow:
        principales = tuple(arg for arg in expr.args if arg.has(variable))
    else:
        principales = ()

    candidatos: list[sp.Expr] = []
    def añadir(parte: sp.Expr, profundidad: int = 0) -> None:
        if profundidad < 3 and (parte.is_Function or parte.is_Pow):
            for interna in parte.args:
                if interna.has(variable):
                    añadir(interna, profundidad + 1)
        if parte != expr and parte.has(variable) and not parte.is_Symbol and parte not in candidatos:
            candidatos.append(parte)

    for principal in principales[:5]:
        añadir(principal)
    salida: list[tuple[str, str, str]] = []
    for parte in candidatos[:5]:
        try:
            fuente = _a_notacion_corriente(parte)
            valor = _a_notacion_corriente(sp.diff(parte, variable))
            if not fuente or not valor:
                continue
            if sp.simplify(sp.diff(analizar(fuente), variable) - analizar(valor)) != 0:
                continue
            salida.append((fuente, valor, AdaptadorSimbolico._regla_dominante(parte, variable)))
        except Exception:
            continue
    return tuple(salida)

def _racionalizacion_comprobable(expr: sp.Expr) -> str:
    try:
        numerador, denominador = sp.fraction(expr)
        if not numerador.is_Add or len(numerador.args) != 2:
            return ""
        primero, segundo = numerador.args
        raiz = next((p for p in (primero, segundo) if p.is_Pow and p.exp == sp.Rational(1, 2)), None)
        if raiz is None:
            return ""
        otro = segundo if raiz == primero else primero
        conjugada = sp.cancel((raiz**2 - otro**2) / (denominador * (raiz - otro)))
        if conjugada == expr or sp.simplify(conjugada - expr) != 0:
            return ""
        corriente = _a_notacion_corriente(conjugada)
        if corriente and sp.simplify(analizar(corriente) - expr) == 0:
            return corriente
    except Exception:
        pass
    return ""

def _pasos_lhopital_comprobables(
    expr: sp.Expr, variable: sp.Symbol, destino_texto: str, resultado: sp.Expr, cantidad: int
) -> tuple[str, ...]:

    if cantidad == 0:
        return ()
    try:
        destino, direccion = analizar_destino_del_limite(destino_texto, str(variable))
        numerador, denominador = sp.fraction(sp.together(expr))
        salida = []
        for _ in range(min(cantidad, 3)):
            numerador = sp.diff(numerador, variable)
            denominador = sp.diff(denominador, variable)
            if denominador == 0:
                break
            transformada = sp.cancel(numerador / denominador)
            valor = evaluar_valor_del_limite(transformada, variable, destino, direccion)
            if valor != resultado and sp.simplify(valor - resultado) != 0:
                break
            corriente = _a_notacion_corriente(transformada)
            if not corriente or sp.simplify(analizar(corriente, str(variable)) - transformada) != 0:
                break
            salida.append(corriente)
        return tuple(salida)
    except Exception:
        return ()

def _a_js_o_vacio(expr) -> str:
    try:
        return expr_to_js(expr)
    except Exception:
        return ""

class AdaptadorSimbolico:
    def objetivos_conversacionales(self, activo):
        from adaptadores.salientes.simbolico.objetivos import objetivos

        return objetivos(activo)

    def citas_conversacionales_relacionadas(self, datos):
        from adaptadores.salientes.simbolico.objetivos import citas_relacionadas

        return citas_relacionadas(datos)

    def referencia_transformada(self, datos):
        from adaptadores.salientes.simbolico.objetivos import referencia_transformada

        return referencia_transformada(datos)

    """Implementa `dominio.puertos.simbolico.PuertoSimbolico`."""

    def precomputar_valor(self, expresion: str) -> Precomputo:
        try:
            expr = analizar(expresion)
            if expr.free_symbols:
                return Precomputo(error="faltan valores para las variables de la expresión")
            valor = sp.simplify(expr)
            if valor in (sp.nan, sp.zoo) or valor.is_finite is False:
                return Precomputo(error="la expresión no tiene un valor finito")
            return Precomputo(
                resultado=sp.latex(valor), resultado_corriente=_a_notacion_corriente(valor),
                pasos=(PasoDerivacion("evaluacion", sp.latex(expr), "Evaluación exacta"),),
                expresion_fuente=expresion,
            )
        except EntradaNoAdmitida as e:
            return Precomputo(error=str(e))
        except Exception as e:
            return Precomputo(error=f"no se pudo evaluar la expresión: {e}")

    def precomputar(
        self,
        expresion: str,
        variable: str = "x",
        orden: int = 1,
        notacion: str = "",
    ) -> Precomputo:

        notacion = notacion if notacion in NOTACIONES else NOTACION_POR_DEFECTO
        try:
            var = sp.Symbol(variable)

            expr = analizar(expresion, variable)
        except EntradaNoAdmitida as e:
            return Precomputo(error=str(e))
        except Exception as e:
            return Precomputo(error=f"no se pudo interpretar la expresión: {e}")

        if not 1 <= orden <= ORDEN_MAXIMO:
            return Precomputo(error=f"el orden de derivación debe estar entre 1 y {ORDEN_MAXIMO}")

        try:
            actual = expr
            pasos_totales: list[dict] = []
            for _ in range(orden):
                _, actual, pasos_de_este_orden = MotorDePasos(actual, var, notacion).ejecutar()
                pasos_totales.extend(pasos_de_este_orden)
        except Exception as e:
            return Precomputo(error=f"el desarrollo no pudo completarse: {e}")

        pasos = tuple(PasoDerivacion(p["tipo"], p["latex"], p["regla"]) for p in pasos_totales)
        intermedio, regla_intermedia = _desplegar_primera_regla(expr, var)
        return Precomputo(
            resultado=sp.latex(actual),
            resultado_corriente=_a_notacion_corriente(actual),
            paso_intermedio_corriente=intermedio,
            paso_intermedio_regla=regla_intermedia,
            componentes_derivada=_componentes_de_derivacion(expr, var) if orden == 1 else (),
            pasos=pasos,
            regla_critica=self._regla_dominante(expr, var),
            concepciones_candidatas=self._concepciones(expr, var),
            expresion_fuente=expresion,
            funcion_js=_a_js_o_vacio(expr),
            derivada_js=_a_js_o_vacio(actual),
        )

    def precomputar_limite(self, expresion: str, variable: str = "x", valor_limite: str = "0") -> Precomputo:
        try:
            var = sp.Symbol(variable)
            expr = analizar(expresion, variable)
            evaluacion = evaluar_limite_con_pasos(expr, var, valor_limite)
        except LimiteBilateralInexistente as e:
            return Precomputo(
                resultado="\\nexists", resultado_corriente="no existe",
                sin_limite_bilateral=True,
                limite_izquierdo_corriente=(
                    _a_notacion_corriente(e.izquierdo) if e.izquierdo.is_number else ""
                ),
                limite_derecho_corriente=(
                    _a_notacion_corriente(e.derecho) if e.derecho.is_number else ""
                ),
                pasos=(PasoDerivacion("contraste_lateral", "", "Comparar los dos lados"),),
                expresion_fuente=expresion,
                funcion_js=_a_js_o_vacio(expr.xreplace({var: sp.Symbol("x")})),
            )
        except EntradaNoAdmitida as e:
            return Precomputo(error=str(e))
        except Exception as e:
            return Precomputo(error=f"el límite no pudo evaluarse: {e}")

        pasos = tuple(PasoDerivacion(p["tipo"], p["latex"], p["regla"]) for p in evaluacion.pasos)
        simplificada = sp.cancel(expr)
        racionalizada = _racionalizacion_comprobable(expr)
        simplificacion_corriente = racionalizada or (
            _a_notacion_corriente(simplificada) if simplificada != expr else ""
        )
        if racionalizada and not any(p.tipo == "tecnica" and "conjugado" in p.regla.lower() for p in pasos):
            pasos = (*pasos, PasoDerivacion("tecnica", "", "Multiplicar por el conjugado"))
        repeticiones_lhopital = sum(
            p.tipo == "tecnica" and "L'Hôpital" in p.regla for p in pasos
        )
        return Precomputo(
            resultado=sp.latex(evaluacion.resultado),

            resultado_corriente=_a_notacion_corriente(evaluacion.resultado),
            simplificacion_corriente=simplificacion_corriente,
            limites_intermedios=_pasos_lhopital_comprobables(
                expr, var, valor_limite, evaluacion.resultado, repeticiones_lhopital
            ),
            pasos=pasos,
            expresion_fuente=expresion,

            funcion_js=_a_js_o_vacio(expr.xreplace({var: sp.Symbol("x")})),
        )

    def verificar(self, bloques: Sequence[BloqueVerificable]) -> InformeVerificacion:
        salida: list[Verificacion] = []
        for b in bloques:
            salida.append(self._verificar_uno(b))
        return InformeVerificacion(verificaciones=tuple(salida))

    def _verificar_uno(self, b: BloqueVerificable) -> Verificacion:
        inicio = time.perf_counter()

        def cerrar(v: Veredicto, detalle: str = "") -> Verificacion:
            return Verificacion(
                bloque=b.identificador,
                veredicto=v,
                herramienta=HERRAMIENTA,
                latencia_ms=(time.perf_counter() - inicio) * 1000,
                detalle=detalle,
            )

        if b.relacion in ('!=', '≠'):
            try:
                izq, der = analizar(b.izquierda), analizar(b.derecha)
                if any(e.free_symbols or e.is_real is not True or e.is_finite is not True for e in (izq, der)):
                    return cerrar(Veredicto.NO_VERIFICABLE, 'la desigualdad requiere dos números reales finitos')
                cero = sp.simplify(izq - der).is_zero
                if cero is not None:
                    return cerrar(Veredicto.INVALIDA if cero else Veredicto.VALIDA,
                                  'comparación exacta de números; no desigualdad universal de funciones')
            except (ValueError, TypeError, sp.SympifyError):
                pass
            return cerrar(Veredicto.NO_VERIFICABLE, 'no se pudo demostrar la diferencia numérica')
        if b.relacion != "=":
            return cerrar(Veredicto.NO_VERIFICABLE,
                          f"relación «{b.relacion}» no comprobable por equivalencia")

        from adaptadores.salientes.simbolico.reglas_formales import comprobar_regla, es_regla_formal

        if es_regla_formal(b.izquierda, b.derecha):
            comprobada = comprobar_regla(b.izquierda, b.derecha)
            if comprobada is not None:
                return cerrar(Veredicto.VALIDA if comprobada else Veredicto.INVALIDA,
                              'identidad entre funciones diferenciables y parámetros constantes')
            return cerrar(Veredicto.NO_VERIFICABLE, 'la regla formal no se pudo demostrar')

        como_derivada = _como_derivada(b.izquierda)
        if como_derivada is not None:
            return self._verificar_derivada(b, como_derivada, cerrar)
        superior = re.fullmatch(r"d\^([2-8])/d([a-zA-Z])\^\1\s*\((.+)\)", b.izquierda.strip())
        if superior:
            return self._verificar_derivada(b, (superior[2], superior[3]), cerrar, orden=int(superior[1]))
        como_limite = _intento_de_limite(b.izquierda)
        if como_limite is not None:
            return self._verificar_limite(b, como_limite, cerrar)
        return self._verificar_por_equivalencia(b, cerrar)

    def _verificar_limite(self, b: BloqueVerificable, extraido, cerrar) -> Verificacion:
        expresion, destino_texto, variable_texto = extraido
        try:
            variable = sp.Symbol(variable_texto)
            funcion = analizar(expresion, variable_texto)
            destino, direccion = analizar_destino_del_limite(destino_texto, variable_texto)
            try:
                calculado = evaluar_valor_del_limite(funcion, variable, destino, direccion)
            except LimiteBilateralInexistente:
                return cerrar(
                    Veredicto.VALIDA if b.derecha.strip().lower() == "no existe" else Veredicto.INVALIDA,
                    "los laterales no coinciden o no convergen",
                )
            if b.derecha.strip().lower() == "no existe":
                return cerrar(Veredicto.INVALIDA, "sí existe un límite")
            afirmado = analizar(b.derecha, variable_texto)
            if self._simbolos_espurios(calculado) | self._simbolos_espurios(afirmado):
                return cerrar(Veredicto.NO_VERIFICABLE, "símbolos no reconocidos en el límite")
            if calculado == afirmado or sp.simplify(calculado - afirmado) == 0:
                return cerrar(Veredicto.VALIDA)
            return cerrar(Veredicto.INVALIDA, "el resultado declarado no coincide con el límite calculado")
        except EntradaNoAdmitida as e:
            return cerrar(Veredicto.NO_VERIFICABLE, f"entrada no admitida: {e}")
        except Exception as e:
            return cerrar(Veredicto.NO_VERIFICABLE, f"no se pudo verificar el límite: {e}")

    def _verificar_por_equivalencia(self, b: BloqueVerificable, cerrar) -> Verificacion:
        try:

            izq = analizar(b.izquierda)
            der = analizar(b.derecha)
        except EntradaNoAdmitida as e:
            return cerrar(Veredicto.NO_VERIFICABLE, f"entrada no admitida: {e}")
        except Exception as e:
            return cerrar(Veredicto.NO_VERIFICABLE, f"no se pudo analizar: {e}")

        espurios = self._simbolos_espurios(izq) | self._simbolos_espurios(der)
        if espurios:
            return cerrar(
                Veredicto.NO_VERIFICABLE,
                "la expresión introduce símbolos que no son variable ni constante "
                f"conocida: {', '.join(sorted(espurios))} — probablemente notación "
                "sin resolver (p.ej. «d/dx» sin reconocer)",
            )

        if self._contraejemplo_exacto(izq, der):
            return cerrar(Veredicto.INVALIDA, "la igualdad falla en un punto exacto del dominio común")
        try:
            diferencia = sp.simplify(izq - der)
        except Exception as e:
            return cerrar(Veredicto.NO_VERIFICABLE, f"no se pudo comparar: {e}")

        if izq == der or diferencia == 0:
            return cerrar(Veredicto.VALIDA)

        if diferencia.free_symbols and not diferencia.is_number:
            try:
                if sp.simplify(sp.expand(izq) - sp.expand(der)) == 0:
                    return cerrar(Veredicto.VALIDA)
            except Exception:
                pass
        return cerrar(Veredicto.INVALIDA, f"la diferencia no es nula: {sp.srepr(diferencia)[:80]}")

    def _verificar_derivada(self, b: BloqueVerificable, extraido: tuple[str, str], cerrar, orden=1) -> Verificacion:
        variable, expresion_texto = extraido
        try:

            expr = analizar(expresion_texto, variable)
            derivada_calculada = sp.diff(expr, sp.Symbol(variable), orden)
            afirmado = analizar(b.derecha, variable)
        except EntradaNoAdmitida as e:
            return cerrar(Veredicto.NO_VERIFICABLE, f"entrada no admitida: {e}")
        except Exception as e:
            return cerrar(Veredicto.NO_VERIFICABLE, f"no se pudo derivar «{expresion_texto}»: {e}")

        espurios = self._simbolos_espurios(derivada_calculada) | self._simbolos_espurios(afirmado)
        if espurios:
            return cerrar(
                Veredicto.NO_VERIFICABLE,
                f"símbolos no reconocidos tras derivar: {', '.join(sorted(espurios))}",
            )

        if self._contraejemplo_exacto(derivada_calculada, afirmado):
            return cerrar(Veredicto.INVALIDA, "la derivada propuesta falla en un punto exacto del dominio común")
        try:
            diferencia = sp.simplify(derivada_calculada - afirmado)
        except Exception as e:
            return cerrar(Veredicto.NO_VERIFICABLE, f"no se pudo comparar: {e}")

        if diferencia == 0:
            return cerrar(Veredicto.VALIDA)
        return cerrar(
            Veredicto.INVALIDA,
            f"la derivada de «{expresion_texto}» respecto a {variable} no es «{b.derecha}»: "
            f"la diferencia es {sp.srepr(diferencia)[:80]}",
        )

    @staticmethod
    def _contraejemplo_exacto(izq, der):
        if izq == der or izq.has(sp.Float) or der.has(sp.Float):
            return False
        simbolos = izq.free_symbols | der.free_symbols
        for punto in (0, 1, 2):
            valores = {s: sp.Integer(punto) for s in simbolos}
            a, b = izq.subs(valores), der.subs(valores)
            if (a.is_real is True and b.is_real is True and a.is_finite is True
                    and b.is_finite is True and (a - b).is_zero is False):
                return True
        return False

    @staticmethod
    def _simbolos_espurios(expr) -> set[str]:
        return {str(s) for s in expr.free_symbols} - _VARIABLES_CONOCIDAS

    @staticmethod
    def _regla_dominante(expr, var) -> str:
        funciones = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc,
                     sp.asin, sp.acos, sp.atan, sp.sinh, sp.cosh, sp.tanh)

        def compuesta(e) -> bool:
            for f in e.atoms(sp.Function):
                if f.args and f.args[0].has(var) and not f.args[0].is_Symbol:
                    return True
            return any(
                p.base.has(var) and not p.base.is_Symbol for p in e.atoms(sp.Pow)
            )

        if not expr.has(var):
            return "derivada de una constante"
        if compuesta(expr):
            return "regla de la cadena"
        if any(isinstance(a, sp.Pow) and a.exp.is_negative for a in expr.atoms(sp.Pow)):
            return "regla del cociente"
        if isinstance(expr, sp.Mul) and sum(1 for a in expr.args if a.has(var)) > 1:
            return "regla del producto"
        if any(isinstance(f, funciones) for f in expr.atoms(sp.Function)):
            return "derivada de función trigonométrica"
        if expr.atoms(sp.exp):
            return "derivada de función exponencial"
        if expr.atoms(sp.log):
            return "derivada de función logarítmica"
        if expr.atoms(sp.Pow):
            return "regla de la potencia"
        return "regla de la potencia"

    @staticmethod
    def _concepciones(expr, var) -> tuple[str, ...]:
        salida = []
        if any(f.args and f.args[0].has(var) and not f.args[0].is_Symbol
               for f in expr.atoms(sp.Function)):
            salida.append("M21")
        if expr.atoms(sp.cos) or expr.atoms(sp.sin):
            salida.append("M22")
        if [s for s in expr.free_symbols if s != var]:
            salida.append("M23")
        return tuple(salida)
