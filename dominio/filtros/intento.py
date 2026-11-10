"""
intento.py — Filtro 6.6 · ¿lo que el estudiante propuso, cuadra?
====================================================================

La política C de la fase 4 dice de `intento_resolucion`: *«verificar primero;
si es correcto, reconocerlo y reducir apoyo; si hay concepción sustentada, usar
KQ/conflicto conceptual; si es error local, orientar el paso concreto»*. Las
tres ramas empiezan por **verificar**, y hasta ahora nadie verificaba lo que el
estudiante escribía: el motor simbólico sólo miraba la respuesta del generador
(filtro 9) y el turno 1 de un ítem de dos niveles (filtro 6.75).

La consecuencia estaba medida en el banco: una **respuesta correcta escrita en
forma no canónica** —`cos(x)^2 - sen(x)^2` donde el libro dice `cos(2x)`— era
indistinguible de un error, y la concepción candidata del motor simbólico
—que es *«una señal para S5, no un diagnóstico»*— era lo único que quedaba para
decidir. Remediar una concepción a quien acaba de acertar es el peor resultado
posible de los que este sistema puede producir.

Dónde está y por qué ahí
---------------------------
Entre el precómputo (6.5) y el diagnóstico de dos niveles (6.75). Después del
6.5 porque comparte con él el mismo adaptador simbólico —`ADR-013` §6.1: un
puerto, dos operaciones— y antes del selector porque su veredicto es una
entrada de la política.

Cómo saca las dos mitades · `DEC-R2`/paquete G · **por rol, no por posición**
--------------------------------------------------------------------------------
🔴 **Hasta la revisión R1 esto era posicional**: `expresiones[0]` era la base y
`expresiones[1]` la propuesta, «porque es el orden en el que se escribe una
propuesta en español». No siempre lo es, y el propio módulo lo declaraba como
límite asumido: *«me da `2x` derivando `x^2`»* salía **al revés**, y un
veredicto invertido tiene la misma pinta que uno bueno.

Ahora los dos roles se **resuelven del texto**, con los marcadores que la frase
ya trae:

| Marcador delante de la expresión | Rol |
|---|---|
| `derivando`, `derivada de`, `derivar`, `deriva`, `derivo`, `d/dx` | **base** |
| `me da`, `me dio`, `me sale`, `dando`, `es`, `queda`, `resulta`, `obtengo` | **propuesta** |

Gana el marcador **más cercano** a la expresión, y se busca sólo en el tramo de
texto que va desde la expresión anterior hasta ésta: así una frase larga
—*«estuve toda la tarde… derivando `cos(x)^3`, me terminó dando `-3*…`»*— no
confunde marcadores de dos mitades distintas.

Los marcadores se buscan **con frontera de palabra**, y no es un detalle: `es`
y `da` son marcadores legítimos y están dentro de «esto», «expresiones»,
«cada» y «duda». Como subcadena, casi cualquier prosa anunciaba un rol.

Cuando una sola de las dos queda marcada y hay **exactamente** otra expresión,
la otra toma el rol libre: si el estudiante dijo cuál deriva, la que queda es
lo que propuso. Con más de dos, con ninguna marcada, o con **dos marcadas del
mismo rol** —«esto **es** `cos(x)^3` y me **da** `3*cos(x)^2`»—, no hay certeza
y el veredicto es `no_verificable`. Ese último caso importa más de lo que
parece: rellenar el rol que faltaba con la expresión sobrante las habría puesto
al revés, y el veredicto habría acusado a quien acertó.

🐛 **`R2-A`, revisión R2 · el rol libre se resuelve por posición, no por
valor.** Hasta la R1 «la que queda» se buscaba por su texto —«la expresión que
no sea ni la base ni la propuesta»—, y con las dos mitades escritas **igual**
—«derivando `x^2` y luego `x^2`», «derivando `cos(x)^3` y `cos(x)^3`»— no hay
ninguna que no lo sea: la búsqueda se agotaba y lanzaba `StopIteration`. La
excepción no se quedaba aquí. Subía por la cadena, el orquestador la traducía a
degradación y el estudiante recibía *«no se pudo generar una respuesta:»* —con
la causa vacía, porque `StopIteration` no lleva mensaje—: un fallo interno
disfrazado de fallo del sistema, y **sin veredicto**, que es peor que el
`no_verificable` que le correspondía. Con dos expresiones sólo hay dos
posiciones y la libre es «la otra», que no puede faltar.

Y cuando las dos mitades resultan ser la **misma** expresión, el veredicto es
`no_verificable` **con motivo propio**: los roles sí se resolvieron, lo que no
hay es algo distinto que comparar. No se verifica `d/dx x^2 = x^2` aunque se
pudiera: eso emitiría `invalida`, y en este filtro `invalida` es una acusación
—la del error caro—; que alguien repita una expresión, o que el segmentador lea
dos veces la misma, explica ese mensaje mejor que atribuirle la afirmación.

**No adivina la base de turnos anteriores.** Podría —`ctx.expresion_previa`
existe— y no lo hace: la expresión que la sesión recuerda puede ser de otro
ejercicio, y verificar contra una base equivocada produciría un veredicto con
la misma pinta que uno bueno. Decirle a alguien que su respuesta correcta está
mal es el error caro de este filtro, así que sin las dos mitades **en el mismo
mensaje** el veredicto es `no_verificable` y se dice.

**No corrige.** Emite `valida`, `invalida` o `no_verificable`; qué se hace con
cada uno lo decide `dominio/pedagogia/politica.py`. Y `no_verificable` nunca
abre una remediación: es la rama segura, igual que `None` lo es en el arbitraje.

⚠️ Su límite, declarado
--------------------------
Los marcadores son una lista de formas del español escrito, no un analizador
sintáctico: es la misma limitación que `R-20` declara para el segmentador. Lo
que cambia respecto de la versión posicional es **hacia dónde falla**: antes
una redacción no prevista producía un veredicto invertido —una acusación—, y
ahora produce `no_verificable`, que no afirma nada. Ésa es la propiedad que
importa, porque el error caro de este filtro es decirle a alguien que su
respuesta correcta está mal.


"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

from dominio.filtros.base import Filtro
from dominio.filtros.normalizacion import segmentar
from dominio.modelo.matematica import BloqueVerificable, InformeVerificacion, Veredicto
from dominio.modelo.notacion_entrada import (
    normalizar_escritura_matematica,
    normalizar_frase_matematica,
    numero_verbal_al_inicio,
    quitar_delimitadores_matematicos,
)
from dominio.modelo.referencias_matematicas import (
    igualdades_explicitas,
    paso_preguntado,
    propuesta_breve,
)
from dominio.modelo.turno import ContextoTurno
from dominio.pedagogia.intenciones import INTENTO_RESOLUCION, PETICION_SOLUCION
from dominio.pedagogia.politica import INVALIDA, NO_VERIFICABLE, VALIDA

#: Lo que, delante de una expresión, dice que esa expresión es **lo que se
#: deriva**. Ordenados de más largo a más corto: se busca el más cercano, y
#: entre dos que empiecen en el mismo sitio gana el más específico.
_MARCAN_BASE = (
    "derivada final de",
    "derivada de",
    "derivando",
    "derivar",
    "derivo",
    "deriva",
    "d/dx",
)

#: Lo que dice que la expresión es **lo que el estudiante propone**. `es` y
#: `da` van al final por cortos: cualquier marcador más largo que empiece
#: después gana por cercanía, y éstos sólo deciden cuando no hay otro.
_MARCAN_PROPUESTA = (
    "me termino dando",
    "me esta dando",
    "me termina dando",
    "me sale",
    "me salio",
    "me dio",
    "me da",
    "obtengo",
    "obtuve",
    "resulta",
    "dando",
    "queda",
    "es",
    "da",
)

_BASE = "base"
_PROPUESTA = "propuesta"

_RESULTADO_ANUNCIADO = re.compile(
    r"\b(?:(?:el|mi|ese|este)\s+resultado(?:\s+final)?"
    r"(?:\s+(?:de|del)\s+(?:(?:ese|esa|este|esta)\s+)?"
    r"(?:l[ií]mite|ecuaci[oó]n|ejercicio|problema|cuenta|operaci[oó]n))?"
    r"(?:\s+(?:como\s+que|que))?\s+(?:es|da|queda|sale)|"
    r"(?:la\s+)?respuesta(?:\s+(?:final|original))?(?:\s+(?:de|para|al)\s+"
    r"(?:(?:ese|esa|este|esta)\s+)?(?:l[ií]mite|ecuaci[oó]n|ejercicio|problema))?\s+es|"
    r"(?:el|del|ese|este)\s+l[ií]mite\s+(?:es|era|da|vale)|"
    r"(?:el\s+c[aá]lculo|la\s+cuenta)\s+(?:da|sale|queda)|"
    r"(?:me|nos)\s+sigue\s+dando|(?:me|nos)\s+(?:da|dio|sale|sali[oó]|queda|qued[oó])"
    r"(?:\s+como\s+resultado)?|(?:me\s+)?(?:termina|acaba)\s+dando|"
    r"(?:al\s+final|finalmente)\s+(?:me\s+)?(?:da|dio|es|queda|sale|sali[oó])|"
    r"(?:y\s+)?luego\s+da|(?:yo\s+)?dir[ií]a\s+que\s+(?:el\s+l[ií]mite\s+)?(?:es|vale)|"
    r"(?:entonces\s+)?debe\s+ser|"
    r"o\s+sea\s+(?:da|es|sale)|"
    r"^\s*(?:(?:entonces|pues|creo\s+que|yo\s+creo\s+que)\s+)?(?:es|da|sale|queda)\b|"
    r"queda|salio|sali[oó]|"
    r"yo\s+digo\s+que|(?:y\s+)?pues(?=\s+(?:[-+]?\d|\$|menos\b|negativo\b))|"
    r"obtengo|obtuve|propongo|(?:mi|la)\s+derivada\s+es|igual\s+a|es\s+igual\s+a|ser[ií]a|ser[aá])\s*[:=]?\s*",
    re.IGNORECASE,
)
_RESPUESTA_SOLA = re.compile(
    r"(?:\$\$?.+?\$\$?|\\\(.+?\\\)|[-+]?(?:\d+(?:[.,]\d+)?|∞|oo)|"
    r"[a-zA-Z](?:\s*[+\-*/^=()]\s*[a-zA-Z0-9_+\-*/^().]+)+)"
)
_CANTIDAD_CON_DUDA = re.compile(
    r"[-+]?\d+(?:[.,]\d+)?\s*,?\s*(?:creo\s+yo|creo|pienso|dir[ií]a\s+yo)\b",
    re.I,
)


def anuncia_resultado(texto: str) -> bool:
    """Hay una respuesta propia explícita, incluso si la intención general es ambigua.

    El tutor puede comprobar «queda -1» sin exigir «el resultado final es».
    Una fórmula dentro de una petición de gráfica o una negación («no me da»)
    no se convierte en un acierto del estudiante.
    """
    from dominio.modelo.respuesta_en_contexto import consulta_sin_entrega

    if consulta_sin_entrega(texto):
        return False
    normalizado = normalizar_escritura_matematica(texto).strip().rstrip(". ")
    if (completas := _roles_de_expresiones_completas(normalizado)) and completas.resueltos:
        return True
    if _resultado_de_derivada_explicita(normalizado) is not None:
        return True
    if re.fullmatch(r"(?:entonces\s+)?(?:el\s+)?l[ií]mite\s+(?:por\s+)?(?:ambos|los\s+dos)\s+lados\s+no\s+existe", normalizado, re.I):
        return True
    marcas = list(_RESULTADO_ANUNCIADO.finditer(normalizado))
    if marcas:
        ultima = marcas[-1]
        if re.search(r"\bno\s*$", normalizado[:ultima.start()], re.I):
            return False
        cola = normalizado[ultima.end():].lstrip(" :=¿¡")
        cola = re.sub(r"^en\s+", "", cola, flags=re.I)
        return bool(
            _cantidad_anunciada(cola)
            or _expresion_anunciada(cola, tiene_marca=True)
            or re.match(r"(?:\$|\\\(|[-+]?[xyzt](?=[\s+\-*/^=()]|$)|"
                        r"no\s+existe\b|infinito\b|(?:sen|sin|cos|tan|ln|log|sqrt|exp)\s*\()", cola, re.I)
        )
    return bool(_RESPUESTA_SOLA.fullmatch(normalizado) or _CANTIDAD_CON_DUDA.fullmatch(normalizado))


def niega_resultado(texto: str) -> bool:
    """«No me da −1» comunica duda, no propone −1 como respuesta."""
    normalizado = normalizar_escritura_matematica(texto)
    marcas = list(_RESULTADO_ANUNCIADO.finditer(normalizado))
    return bool(marcas and re.search(r"\bno\s*$", normalizado[:marcas[-1].start()], re.I))
def _cantidad_anunciada(tramo: str) -> str:
    verbal = numero_verbal_al_inicio(tramo)
    if verbal:
        return verbal
    infinito = re.match(r"(?:(menos|negativo)\s+)?infinito\b", tramo, re.I)
    if infinito:
        return "-oo" if infinito.group(1) else "oo"
    numero = re.match(r"[-+]?(?:\d+(?:[.,]\d+)?|∞|oo)(?=$|[\s,.;!?])", tramo)
    return numero.group().replace(",", ".") if numero else ""


def _expresion_anunciada(tramo: str, tiene_marca: bool) -> str:
    expresion_completa = re.split(
        r"\s+(?:porque|por\s+qu[eé]|pq|expl[ií]came|ya\s+que|pues|cuando|pero|ser[ií]a|al\s+simplificar)\b",
        tramo, maxsplit=1, flags=re.I,
    )[0].rstrip("?,;.! ")
    expresion_completa = re.split(r"[?!¿¡]|\.(?!\d)", expresion_completa, maxsplit=1)[0].strip()
    if re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?,?", expresion_completa):
        return ""  # Un número con coma final es puntuación, no «-1.» algebraico.
    expresion_normalizada = normalizar_frase_matematica(expresion_completa)
    if re.fullmatch(r"[+-]?[xyzt]", expresion_normalizada):
        return expresion_normalizada
    cola_numerica = re.match(r"^[-+]?\d+(?:[.,]\d+)?\s+([a-zA-Z]+)", expresion_normalizada)
    if cola_numerica and cola_numerica.group(1).lower() not in ("x", "y", "t"):
        return ""
    if re.fullmatch(r"[0-9a-zA-Z_+\-*/^().,\s]+", expresion_normalizada) and re.search(
        r"[+\-*/^()]", expresion_normalizada
    ):
        return expresion_normalizada.replace(",", ".")
    if tiene_marca and re.search(r"\b(?:seno|coseno|tangente|raíz|equis)\b", expresion_normalizada, re.I):
        # Si queda vocabulario sin traducir, la frase es ambigua. Pasarla
        # completa al CAS fuerza NO_VERIFICABLE en lugar de verificar un
        # fragmento aislado, como x^2 dentro de «seno de x^2».
        return expresion_normalizada
    return ""


def _resultado_de_derivada_explicita(normalizado: str) -> str | None:
    s = quitar_delimitadores_matematicos(normalizado)
    s = re.sub(r"\\(?:left|right)\s*", "", s)
    s = re.sub(r"\^?\s*(?:\{\s*)?\\prime\s*\}?|′", "'", s)
    patron = r"\b[a-zA-Z]\s*'\s*\(\s*x\s*\)\s*=\s*(.+)"
    igualdad = re.fullmatch(patron, s.strip())
    if igualdad:
        return quitar_delimitadores_matematicos(igualdad.group(1).strip().rstrip("?.! "))
    igualdad = re.search(patron, s)
    return _expresion_anunciada(igualdad.group(1), True) if igualdad else None


def _propuesta_con_notacion_explicita(normalizado: str) -> str | None:
    if completas := _roles_de_expresiones_completas(normalizado):
        return completas.propuesta
    return _resultado_de_derivada_explicita(normalizado)


def propuesta_en_el_turno(texto: str) -> str:
    """Extrae una propuesta explícita; no usa la última fórmula por defecto.

    Se prefieren las expresiones tras «me da»/«resultado es». Un número dicho
    con palabras se admite cuando es inequívoco. El motor simbólico seguirá
    siendo quien compruebe el valor, nunca este extractor.
    """
    normalizado = normalizar_escritura_matematica(texto)
    derivada_explicita = _propuesta_con_notacion_explicita(normalizado)
    if derivada_explicita is not None:
        return derivada_explicita
    if re.fullmatch(r"(?:entonces\s+)?(?:el\s+)?l[ií]mite\s+(?:por\s+)?(?:ambos|los\s+dos)\s+lados\s+no\s+existe[.!]?", normalizado.strip(), re.I):
        return "no existe"
    marcas = list(_RESULTADO_ANUNCIADO.finditer(normalizado))
    if not marcas and re.search(r"\b[a-zA-Z]\s*\(\s*x\s*\)\s*=", normalizado):
        # La función del ejercicio no es una respuesta del estudiante.
        return ""
    tramo = normalizado[marcas[-1].end():] if marcas else normalizado
    tramo = tramo.lstrip(" :={").strip()
    tramo = re.sub(r"^como\s+(?:resultado|respuesta)\s+", "", tramo, flags=re.I)
    tramo = re.sub(r"^en\s+(?=(?:[-+]?\d|menos\b|negativo\b|\$))", "", tramo, flags=re.I)
    if re.match(r"(?:el\s+l[ií]mite\s+)?(?:no\s+existe|no\s+hay\s+l[ií]mite|diverge)\b", tramo, re.I):
        return "no existe"
    formula = re.match(r"\$\$?(.+?)\$\$?|\\\((.+?)\\\)", tramo)
    if formula:
        return (formula.group(1) or formula.group(2)).strip()
    if _CANTIDAD_CON_DUDA.fullmatch(tramo.strip().rstrip(". ")):
        return _cantidad_anunciada(tramo)
    expresion = _expresion_anunciada(tramo, bool(marcas))
    if expresion:
        return expresion
    cantidad = _cantidad_anunciada(tramo)
    if cantidad:
        return cantidad
    expresiones, _ = segmentar(tramo)
    if expresiones:
        return expresiones[0]
    return _propuesta_segmentada(normalizado, marcas)


def _propuesta_segmentada(normalizado, marcas):
    if marcas:
        previas, _ = segmentar(normalizado[:marcas[-1].start()])
        if previas:
            return previas[-1]
    if not marcas:
        expresiones, _ = segmentar(normalizado)
        if expresiones:
            return expresiones[-1]
    return ""


@dataclass(frozen=True)
class RolesDelIntento:
    """Qué se deriva y qué se propone, **dicho**, no supuesto por posición.

    `motivo` va siempre, también cuando no se resolvieron: sin él no se puede
    distinguir «el mensaje no traía dos expresiones» de «traía dos y ninguna
    dijo cuál era cuál», y las dos se atienden igual pero se leen distinto en
    una traza.
    """

    base: str = ""
    propuesta: str = ""
    motivo: str = ""

    @property
    def resueltos(self) -> bool:
        return bool(self.base) and bool(self.propuesta) and self.base != self.propuesta


def _plano(texto: str) -> str:
    """Minúsculas y sin tildes: «me terminó dando» y «me termino dando» son lo
    mismo, y un estudiante escribe sin tildes la mitad de las veces."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _rol_del_tramo(tramo: str) -> str:
    """El rol que anuncia el texto que precede a una expresión, o `""`.

    Gana el marcador que **acaba más cerca** de la expresión. Si dos acaban en
    el mismo sitio —`derivada de` contiene `deriva`— gana el más largo, que es
    el más específico.
    """
    plano = _plano(tramo)
    mejor_fin, mejor_largo, mejor_rol = -1, 0, ""
    for marcadores, rol in ((_MARCAN_BASE, _BASE), (_MARCAN_PROPUESTA, _PROPUESTA)):
        for marcador in marcadores:
            # ⚠️ **Con frontera de palabra, y no es un detalle.** `es` y `da`
            # son marcadores legítimos y están dentro de «esto», «expresiones»,
            # «cada» y «duda». Buscándolos como subcadena, casi cualquier
            # tramo de prosa anunciaba un rol, y un rol inventado es peor que
            # ninguno: lleva a un veredicto, y un veredicto es una acusación.
            hallado = None
            for coincidencia in re.finditer(
                rf"(?<![a-z0-9]){re.escape(marcador)}(?![a-z0-9])", plano
            ):
                hallado = coincidencia
            if hallado is None:
                continue
            fin = hallado.end()
            if fin > mejor_fin or (fin == mejor_fin and len(marcador) > mejor_largo):
                mejor_fin, mejor_largo, mejor_rol = fin, len(marcador), rol
    return mejor_rol


def _roles_de_expresiones_completas(texto: str) -> RolesDelIntento | None:
    """Con dos marcas inequívocas, conserva los paréntesis y productos enteros."""
    marcas_base = '|'.join(re.escape(m) for m in sorted(_MARCAN_BASE, key=len, reverse=True))
    marcas_propuesta = '|'.join(re.escape(m) for m in sorted(_MARCAN_PROPUESTA, key=len, reverse=True))
    patron = rf"(?<![a-z0-9])(?:(?P<base>{marcas_base})|(?P<propuesta>{marcas_propuesta}))(?![a-z0-9])"
    marcas = list(re.finditer(patron, _plano(texto)))
    if len(marcas) != 2 or marcas[0].lastgroup == marcas[1].lastgroup:
        return None
    expresiones = {}
    for i, marca in enumerate(marcas):
        fin = marcas[i+1].start() if i+1 < len(marcas) else len(texto)
        tramo = texto[marca.end():fin]
        if i + 1 < len(marcas):
            # «Derivo sen(x^2) y me da ...»: la conjunción separa los roles;
            # una segunda fórmula dentro de la base sigue siendo ambigua.
            tramo = re.sub(r"\s+y\s*$", "", tramo, flags=re.I)
        if marca.lastgroup == 'propuesta':
            tramo = re.split(r",?\s*¿(?=[a-záéíóúñ])|(?:,\s*|\s+)(?:pero|porque|ya\s+que|pues)\b", tramo, maxsplit=1, flags=re.I)[0]
        tramo = quitar_delimitadores_matematicos(tramo.strip(' :;,?.!'))
        if marca.lastgroup == 'base':
            # La declaración nombra la función; no forma parte del operando.
            # Sólo se retira una declaración inicial, nunca una igualdad interna.
            tramo = re.sub(r'^\s*[a-zA-Z]\s*\(\s*x\s*\)\s*=\s*', '', tramo)
        tramo = normalizar_frase_matematica(normalizar_escritura_matematica(tramo))
        if not tramo or re.search(r"\by\b", tramo) or not re.fullmatch(r"[0-9a-zA-Z_+\-*/^().,{}\[\]\\|\s]+", tramo):
            return RolesDelIntento(motivo="la base o propuesta contiene más información que una fórmula inequívoca; no se verifica un fragmento")
        expresiones[marca.lastgroup] = tramo
    if expresiones['base'] == expresiones['propuesta']:
        return None
    return RolesDelIntento(**expresiones, motivo="la base y la propuesta están marcadas explícitamente; se conservan completas")


def roles_de(texto: str) -> RolesDelIntento:
    """Los dos roles del intento, resueltos del texto. Ver la cabecera.

    Se llama a `segmentar()` —el mismo segmentador del filtro 1— para tener a
    la vez la forma canónica y **dónde estaba** cada expresión: el rol se lee
    del tramo de prosa que la precede, y sin desplazamientos no hay tramo.
    """
    if completas := _roles_de_expresiones_completas(texto):
        return completas
    expresiones, segmentos = segmentar(texto)
    if len(expresiones) < 2:
        return RolesDelIntento(
            motivo=(
                "el mensaje no trae la base y la propuesta a la vez; no se adivina "
                "la base de un turno anterior"
            )
        )

    asignados: list[str] = []
    anterior = 0
    for segmento in segmentos:
        asignados.append(_rol_del_tramo(texto[anterior : segmento["inicio"]]))
        anterior = segmento["fin"]

    # 🔴 **Se trabaja con POSICIONES y no con los textos.** Ver `R2-A` abajo:
    # dos expresiones pueden ser la misma cadena, y entonces identificarlas por
    # su valor no distingue una de otra.
    marcadas_base = [i for i, rol in enumerate(asignados) if rol == _BASE]
    marcadas_propuesta = [i for i, rol in enumerate(asignados) if rol == _PROPUESTA]

    # 🔴 **Dos del mismo rol es una contradicción, no una pista.** «esto es
    # cos(x)^3 y me da 3*cos(x)^2» marca las dos como propuesta; rellenar la
    # que falta con la sobrante las habría puesto **al revés** y el veredicto
    # habría acusado a quien acertó. Sin certeza, `no_verificable`.
    if len(marcadas_base) > 1 or len(marcadas_propuesta) > 1:
        return RolesDelIntento(
            motivo=(
                "el mensaje marca dos expresiones con el mismo rol: no se puede "
                "decir cuál se deriva y cuál se propone"
            )
        )

    # Una sola marcada y exactamente otra expresión: la que queda toma el rol
    # libre. Con tres o más no se completa — no hay forma de saber cuál de las
    # otras es, y elegir sería volver a adivinar por posición.
    #
    # 🐛 **`R2-A`, revisión R2 · aquí se lanzaba `StopIteration`.** La expresión
    # libre se buscaba por valor —«la que no sea ni la base ni la propuesta»—, y
    # con las dos mitades escritas igual —«derivando `x^2` y luego `x^2`»— no
    # existe ninguna que no lo sea: el generador se agotaba, la excepción subía
    # por la cadena y el turno salía como degradación genérica, sin causa. Con
    # dos expresiones sólo hay dos posiciones, así que la libre es «la otra»
    # —`1 - marcada`— y eso no puede fallar ni depende de lo que digan.
    if len(marcadas_base) + len(marcadas_propuesta) == 1 and len(expresiones) == 2:
        (marcada,) = marcadas_base or marcadas_propuesta
        libre = 1 - marcada
        if marcadas_base:
            marcadas_propuesta = [libre]
        else:
            marcadas_base = [libre]

    if not (marcadas_base and marcadas_propuesta):
        return RolesDelIntento(
            motivo=(
                "el mensaje trae expresiones pero ninguna dice cuál se deriva y "
                "cuál se propone: sin roles no se acusa un error"
            )
        )

    base = expresiones[marcadas_base[0]]
    propuesta = expresiones[marcadas_propuesta[0]]

    # 🔴 **Las dos mitades son la misma expresión.** No es lo mismo que no
    # saber cuál es cuál —los roles sí se resolvieron— y por eso lleva motivo
    # propio: lo que falta es algo que comparar. «Derivando `x^2` y luego
    # `x^2`» se explica mejor porque el estudiante repitió, o porque el
    # segmentador leyó dos veces la misma, que porque afirme que la derivada de
    # `x^2` es `x^2`; y verificarlo igualmente emitiría `invalida`, que en este
    # filtro es una acusación. La rama segura es la de siempre.
    if base == propuesta:
        return RolesDelIntento(
            motivo=(
                "las dos mitades del mensaje son la misma expresión: no hay "
                "propuesta distinta de la base que comprobar"
            )
        )

    return RolesDelIntento(
        base=base,
        propuesta=propuesta,
        motivo=f"«{base}» es lo que se deriva y «{propuesta}» lo que propone",
    )


def ejercicio_de_intento_explicito(texto: str) -> dict[str, str] | None:
    """Recuerda la base dicha junto a una propuesta, sin usar una respuesta sola."""
    completas = _roles_de_expresiones_completas(normalizar_escritura_matematica(texto))
    if completas is None or not completas.resueltos:
        return None
    return {'tipo': 'derivada', 'expresion': completas.base, 'variable': 'x', 'destino': ''}


@runtime_checkable
class _PuertoDeCorreccion(Protocol):
    """Lo único de `PuertoSimbolico` que este filtro necesita.

    Declarado aparte —igual que hacen el 6.5 y el 6.75— porque este filtro no
    precomputa nada: darle el puerto entero le daría una capacidad que no le
    toca ejercer.
    """

    def verificar(self, bloques: Sequence[BloqueVerificable]) -> InformeVerificacion: ...


def _consulta_sin_propuesta(ctx, respuesta_explicita):
    detalle = ctx.intencion_detalle
    pide_curva = bool(detalle and detalle.estrategia_solicitada == "cambio_de_representacion") or bool(re.search(
        r"\b(?:agrega|a[nñ]ade|superp[oó]n|agr[eé]gale)\b.*(?:[a-z]\s*\(\s*x\s*\)\s*=|comparar|contrastar)",
        ctx.texto_estudiante, re.I,
    ))
    if pide_curva and not respuesta_explicita:
        return True
    texto = normalizar_escritura_matematica(ctx.texto_estudiante)
    return bool(("?" in texto or "¿" in texto) and re.search(
        r"\b(?:o|u)\s+(?:[-+]?\d|[-+]?∞|[-+]?oo\b|L\b|"
        r"(?:el\s+)?l[ií]mite\b|no\s+existe\b|falta\b|infinito\b)", texto, re.I,
    ))


class FiltroIntento(Filtro):
    """Filtro 6.6 · comprueba la propuesta del estudiante contra el motor.

    `simbolico` es opcional y por inyección, igual que los puertos de los
    filtros vecinos: sin él no hay veredicto y el turno sigue exactamente como
    iba, con la incertidumbre declarada en la traza.
    """

    nombre = "verificación del intento del estudiante"
    ruta = "caliente"

    def __init__(self, simbolico: _PuertoDeCorreccion | None = None) -> None:
        self._simbolico = simbolico

    def _procesar(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        if (ctx.continuidad or {}).get('paso_usuario'):
            return self._verificar_transformacion_del_estudiante(ctx)
        if ctx.continuidad is not None and ctx.continuidad.get("aclaracion"):
            return replace(ctx, veredicto_del_intento=NO_VERIFICABLE), {
                "veredicto": NO_VERIFICABLE, "motivo": "referente o alcance sin resolver",
            }
        if (ctx.continuidad is not None and not ctx.continuidad.get("propuesta")
                and ctx.continuidad.get("acto") in ("iniciar", "definir", "retomar", "representar", "dialogar", "consultar")):
            return replace(ctx, veredicto_del_intento=""), {
                "veredicto": "", "motivo": "petición de ayuda o enunciado; no hay entrega que calificar",
            }
        ctx = self._con_pregunta_pendiente(ctx)
        respuesta_explicita = anuncia_resultado(ctx.texto_estudiante) or bool(
            igualdades_explicitas(ctx.texto_estudiante, (ctx.ejercicio_activo or {}).get("variable", "x"))
        ) or bool(ctx.ejercicio_activo and propuesta_breve(ctx.texto_estudiante, ctx.ejercicio_activo.get("variable", "x")))
        if _consulta_sin_propuesta(ctx, respuesta_explicita):
            return replace(ctx, veredicto_del_intento=NO_VERIFICABLE), {
                "veredicto": NO_VERIFICABLE,
                "motivo": "pide una representación o compara alternativas; no afirma una respuesta propia",
            }
        pregunta_abierta = ctx.texto_estudiante.lstrip().startswith("¿") or bool(re.match(
            r"^\s*(?:qu[eé]|c[oó]mo|cu[aá]l|por\s+qu[eé])\b",
            ctx.texto_estudiante, re.I,
        ))
        if (ctx.ejercicio_activo and (not niega_resultado(ctx.texto_estudiante) or self._respuesta_del_paso(ctx)[1]) and
                not (pregunta_abierta and not respuesta_explicita) and
                (ctx.intencion == INTENTO_RESOLUCION or respuesta_explicita or self._respuesta_del_paso(ctx)[0]) and
                (ctx.intencion != PETICION_SOLUCION or respuesta_explicita)):
            return self._verificar_ejercicio_activo(ctx)
        veredicto, motivo, base, propuesta = self._verificar(ctx)
        meta = {
            "veredicto": veredicto,
            "motivo": motivo,
        }
        if base:
            meta["base"] = base
            meta["propuesta"] = propuesta
        if not veredicto:
            return ctx, meta
        return replace(ctx, veredicto_del_intento=veredicto), meta

    def _verificar_transformacion_del_estudiante(self, ctx):
        transformacion = ctx.continuidad['paso_usuario']
        paso = (dict(tipo='equivalencia', expresion=transformacion['izquierda'],
                     variable=ctx.ejercicio_activo.get('variable', 'x'))
                if transformacion['transformacion'] == 'igualdad' else
                self._simbolico.referencia_transformada((ctx.ejercicio_activo, transformacion['transformacion'])))
        if paso:
            paso['transformacion'] = transformacion['transformacion']
            for candidata in transformacion.get('transiciones', []):
                informe = self._simbolico.verificar((BloqueVerificable(
                    identificador='transicion_logaritmica', izquierda=paso['expresion'], derecha=candidata,
                ),))
                if not informe.verificaciones or informe.verificaciones[0].veredicto is not Veredicto.VALIDA:
                    return self._verificar_paso(replace(ctx, paso_pendiente=paso), candidata, False,
                                               {'alcance': 'transicion_logaritmica_no_acreditada'})
            return self._verificar_paso(replace(ctx, paso_pendiente={**paso, 'tarea_id': ctx.continuidad['activa']}),
                                        ctx.continuidad['propuesta'], False, {'alcance': 'transformacion_logaritmica'})
        return replace(ctx, veredicto_del_intento=NO_VERIFICABLE), {
            'veredicto': NO_VERIFICABLE, 'motivo': 'no se estableció un dominio real para esta transformación',
        }

    def _verificar_ejercicio_activo(self, ctx: ContextoTurno) -> tuple[ContextoTurno, dict]:
        activo = ctx.ejercicio_activo or {}
        propuesta, negada = self._respuesta_del_paso(ctx)
        propuesta = propuesta or (ctx.continuidad or {}).get("propuesta") or propuesta_breve(ctx.texto_estudiante, activo.get("variable", "x")) or propuesta_en_el_turno(ctx.texto_estudiante)
        igualdades = igualdades_explicitas(ctx.texto_estudiante, activo.get("variable", "x"))
        if igualdades:
            propuesta = igualdades[-1][1]
        from dominio.pedagogia.confirmacion import base_de_ejercicio

        meta = {"ejercicio_activo": activo, "base": base_de_ejercicio(activo), "propuesta": propuesta}
        if not propuesta:
            return ctx, {**meta, "veredicto": NO_VERIFICABLE, "motivo": "no se extrajo una propuesta inequívoca"}
        if self._simbolico is None or ctx.precomputo is None or not ctx.precomputo.ok:
            return replace(ctx, veredicto_del_intento=NO_VERIFICABLE), {
                **meta, "veredicto": NO_VERIFICABLE, "motivo": "no hay precómputo simbólico válido del ejercicio activo",
            }
        if ctx.precomputo.sin_limite_bilateral:
            correcto = propuesta == "no existe"
            return replace(
                ctx, veredicto_del_intento=VALIDA if correcto else INVALIDA,
                resultado_verificado=propuesta if correcto else "",
                nivel_divulgacion=3 if correcto else ctx.nivel_divulgacion,
            ), {
                **meta, "veredicto": VALIDA if correcto else INVALIDA,
                "motivo": "los límites laterales no definen un valor bilateral",
                "cierre_por_acierto": correcto,
            }

        def equivale(referencia: str) -> Veredicto:
            informe = self._simbolico.verificar((BloqueVerificable(
                identificador="propuesta", izquierda=referencia, derecha=propuesta,
            ),))
            return informe.verificaciones[0].veredicto if informe.verificaciones else Veredicto.NO_VERIFICABLE

        try:
            previa = self._comprobar_transiciones(ctx, igualdades, propuesta, negada, meta)
            if previa is not None:
                return previa
            final = equivale(ctx.precomputo.resultado_corriente)
            if final is Veredicto.VALIDA:
                return self._cerrar_resultado(ctx, propuesta, meta)
            parcial = self._comprobar_parcial(ctx, equivale, propuesta, meta)
            if parcial is not None:
                return parcial
            veredicto = NO_VERIFICABLE if final is Veredicto.NO_VERIFICABLE else INVALIDA
            return replace(ctx, veredicto_del_intento=veredicto), {
                **meta, "veredicto": veredicto,
                "motivo": "la propuesta no coincide con el resultado simbólico" if veredicto == INVALIDA
                else "el CAS no pudo comprobar la propuesta",
            }
        except Exception:  # noqa: BLE001 — una comprobación fallida nunca acusa
            return replace(ctx, veredicto_del_intento=NO_VERIFICABLE), {
                **meta, "veredicto": NO_VERIFICABLE, "motivo": "falló la comprobación simbólica",
            }

    def _cerrar_resultado(self, ctx, propuesta, meta):
        if ctx.continuidad is not None and ctx.paso_pendiente and ctx.continuidad.get("alcance") != "final":
            parcial = self._verificar_paso(ctx, propuesta, False, meta)
            if parcial[0].paso_verificado:
                return parcial
        # El acierto verificable abre la explicación del ejercicio que
        # el propio estudiante acaba de resolver, sin tres preguntas
        # adicionales. La traza deja esta excepción explícita.
        return replace(
            ctx, veredicto_del_intento=VALIDA,
            resultado_verificado=propuesta, nivel_divulgacion=3,
        ), {
            **meta, "veredicto": VALIDA, "motivo": "resultado final comprobado por el CAS",
            "nivel_divulgacion": 3, "cierre_por_acierto": True,
        }

    def _pregunta_por_resultado_final(self, ctx):
        paso, activo = ctx.paso_pendiente, ctx.ejercicio_activo
        if paso.get("tipo") != activo.get("tipo"):
            return False
        informe = self._simbolico.verificar((BloqueVerificable(
            identificador="alcance_de_pregunta", izquierda=paso["expresion"], derecha=activo["expresion"],
        ),))
        return bool(informe.verificaciones and informe.verificaciones[0].veredicto is Veredicto.VALIDA)

    def _comprobar_transiciones(self, ctx, igualdades, propuesta, negada, meta):
        for izquierda, derecha in igualdades:
            informe = self._simbolico.verificar((BloqueVerificable(
                identificador="paso_escrito", izquierda=izquierda, derecha=derecha,
            ),))
            estado = informe.verificaciones[0].veredicto if informe.verificaciones else Veredicto.NO_VERIFICABLE
            if estado is not Veredicto.VALIDA:
                paso = dict(tipo="valor", expresion=izquierda, variable=ctx.ejercicio_activo.get("variable", "x"))
                return self._verificar_paso(replace(ctx, paso_pendiente=paso), derecha, False, meta)
        if negada:
            return self._verificar_paso(ctx, propuesta, True, meta)
        if ctx.continuidad is None and ctx.paso_pendiente and not self._pregunta_por_resultado_final(ctx):
            return self._verificar_paso(ctx, propuesta, False, meta)
        return None

    def _comprobar_parcial(self, ctx, equivale, propuesta, meta):
        activo = ctx.ejercicio_activo
        if activo.get("tipo") == "limite" and equivale(activo.get("expresion", "")) is Veredicto.VALIDA:
            return replace(ctx, veredicto_del_intento=NO_VERIFICABLE,
                           transformacion_verificada=propuesta), {
                **meta, "veredicto": NO_VERIFICABLE,
                "motivo": "transformación correcta; todavía no es el valor del límite",
                "transformacion_verificada": True,
            }
        return self._verificar_paso(ctx, propuesta, False, meta) if ctx.paso_pendiente else None

    @staticmethod
    def _con_pregunta_pendiente(ctx):
        if ctx.continuidad is not None:
            from dominio.modelo.continuidad import objetivo_actual

            if ctx.continuidad.get("alcance") == "final":
                return replace(ctx, paso_pendiente=None)
            objetivo = objetivo_actual(ctx.continuidad)
            if objetivo and objetivo.get("tarea_id") == ctx.continuidad.get("activa") and objetivo.get("alcance") == "parcial":
                return replace(ctx, paso_pendiente=objetivo)
            return ctx
        recientes = (ctx.contexto_conversacional or {}).get("historial_reciente_con_origen", [])
        if not recientes or not ctx.ejercicio_activo:
            return ctx
        ultimo = recientes[-1]
        if ultimo.get("ejercicio") != ctx.ejercicio_activo or ultimo.get("respuesta_degradada"):
            return ctx
        paso = paso_preguntado(ultimo.get("tutor", ""), ctx.ejercicio_activo.get("variable", "x"))
        return replace(ctx, paso_pendiente=paso) if paso else ctx

    @staticmethod
    def _respuesta_del_paso(ctx):
        if not ctx.paso_pendiente:
            return "", False
        texto = normalizar_frase_matematica(ctx.texto_estudiante).strip().rstrip("?.! ")
        negada = re.fullmatch(r"no\s+(?:es|ser[ií]a)\s+([-+]?\d+(?:\.\d+)?)", texto, re.I)
        if negada:
            return negada[1], True
        misma = re.fullmatch(r"(?:el\s+)?mismo\s+([-+]?\d+(?:\.\d+)?)", texto, re.I)
        return (misma[1], False) if misma else ("", False)

    def _verificar_paso(self, ctx, propuesta, negada, meta):
        paso = ctx.paso_pendiente or {}
        if paso.get('tipo') == 'equivalencia':
            informe = self._simbolico.verificar((BloqueVerificable(
                identificador='transformacion_del_estudiante', izquierda=paso['expresion'], derecha=propuesta,
            ),))
            estado = informe.verificaciones[0].veredicto if informe.verificaciones else Veredicto.NO_VERIFICABLE
            paso = {**paso, 'propuesta': propuesta, 'negada': False,
                    'resultado_corriente': paso['expresion'], 'veredicto': estado.value}
            return replace(ctx, paso_pendiente=paso, veredicto_del_intento=NO_VERIFICABLE,
                           paso_verificado=propuesta if estado is Veredicto.VALIDA else ''), {
                **meta, 'veredicto_del_paso': estado.value, 'paso': paso, 'cierre_por_acierto': False,
            }
        operador = getattr(self._simbolico, "precomputar" if paso.get("tipo") == "derivada" else "precomputar_valor", None)
        if operador is None:
            return replace(ctx, veredicto_del_intento=NO_VERIFICABLE), {
                **meta, "veredicto": NO_VERIFICABLE, "motivo": "sin capacidad de comprobar el paso preguntado",
            }
        pre = (operador(paso["expresion"], variable=paso.get("variable", "x"))
               if paso.get("tipo") == "derivada" else operador(paso["expresion"]))
        if not pre.ok:
            return replace(ctx, veredicto_del_intento=NO_VERIFICABLE), {
                **meta, "veredicto": NO_VERIFICABLE, "motivo": "el paso preguntado no tiene referencia simbólica válida",
            }
        informe = self._simbolico.verificar((BloqueVerificable(
            identificador="respuesta_del_paso", izquierda=pre.resultado_corriente, derecha=propuesta,
        ),))
        estado = informe.verificaciones[0].veredicto if informe.verificaciones else Veredicto.NO_VERIFICABLE
        if negada and estado is not Veredicto.NO_VERIFICABLE:
            estado = Veredicto.INVALIDA if estado is Veredicto.VALIDA else Veredicto.VALIDA
        paso = {**paso, "propuesta": propuesta, "negada": negada,
                "resultado_corriente": pre.resultado_corriente, "veredicto": estado.value}
        return replace(ctx, paso_pendiente=paso, veredicto_del_intento=NO_VERIFICABLE,
                       paso_verificado=propuesta if estado is Veredicto.VALIDA else ""), {
            **meta, "veredicto": NO_VERIFICABLE, "veredicto_del_paso": estado.value,
            "alcance": "paso_preguntado", "paso": paso, "cierre_por_acierto": False,
            "motivo": "comprobación del paso parcial; no califica ni cierra el ejercicio completo",
        }

    def _verificar(self, ctx: ContextoTurno) -> tuple[str, str, str, str]:
        """`(veredicto, motivo, base, propuesta)`. Veredicto vacío = no se intentó."""
        if ctx.intencion != INTENTO_RESOLUCION:
            return "", "el turno no propone ninguna solución que comprobar", "", ""
        if self._simbolico is None:
            return (
                NO_VERIFICABLE,
                "sin motor simbólico: no se puede comprobar lo que propuso",
                "",
                "",
            )
        # Paquete G · los roles se leen del texto, no de la posición. Ver la
        # cabecera: sin certeza sobre cuál se deriva, `no_verificable`.
        roles = roles_de(ctx.texto_estudiante)
        if not roles.resueltos:
            return NO_VERIFICABLE, roles.motivo, "", ""

        base, propuesta = roles.base, roles.propuesta
        try:
            informe = self._simbolico.verificar(
                [
                    BloqueVerificable(
                        identificador="intento",
                        izquierda=f"d/dx ({base})",
                        derecha=propuesta,
                        relacion="=",
                    )
                ]
            )
        except Exception:  # noqa: BLE001 — comprobar no puede tumbar el turno
            return NO_VERIFICABLE, "el motor simbólico no pudo evaluarlo", base, propuesta

        if not informe.verificaciones:
            return NO_VERIFICABLE, "el motor no devolvió veredicto", base, propuesta
        veredicto = informe.verificaciones[0].veredicto
        if veredicto is Veredicto.NO_VERIFICABLE:
            return NO_VERIFICABLE, "el motor lo declaró no verificable", base, propuesta
        if veredicto is Veredicto.VALIDA:
            return VALIDA, f"la derivada de «{base}» sí es «{propuesta}»", base, propuesta
        return INVALIDA, f"la derivada de «{base}» no es «{propuesta}»", base, propuesta
