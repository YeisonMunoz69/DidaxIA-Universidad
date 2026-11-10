"""
calendario.py — Días hábiles colombianos y meses calendario (`EQ-022`)
=======================================================================

Los plazos de `EQ-022` están escritos en dos unidades que no son días naturales:

    «El plazo operativo es de 15 días **hábiles**, con extensión excepcional
    informada de hasta 8 días hábiles adicionales.»

    «Los datos identificables o seudonimizados se conservan como máximo hasta
    seis **meses** después de la sustentación.»

Este módulo las calcula. Vive en el dominio porque «qué día es hábil» y «qué
significa sumar seis meses» son reglas de negocio, no detalles de almacén: un
`INTERVAL` de SQL las escondería dentro de una consulta y las dejaría fuera del
alcance de las pruebas que las fijan.

⚠️ Qué se corrigió, y por qué importaba
------------------------------------------------
Hasta el cierre V-B había dos aproximaciones declaradas y ninguna inocente:

1. `supresion.es_habil()` sólo descartaba sábado y domingo. Los 15 días hábiles
   que se le comunican a alguien que ejerce un derecho quedaban **cortos**
   respecto del plazo legal cada vez que el tramo cruzaba Semana Santa o un
   puente. Un plazo comunicado de menos no es conservador: es incumplible por el
   propio equipo y engañoso para quien espera.
2. `Retencion.limite` sumaba `30 × meses`. Seis meses desde el 31 de agosto
   caían el 27 de febrero en vez del 28. Sobre un plazo de retención, unos días
   de menos significan borrar antes de lo comprometido y unos de más,
   conservar más de lo autorizado.

De dónde sale el calendario, y por qué no se consulta a nadie
----------------------------------------------------------------------
De la ley, no de un servicio. Se calcula aquí, en el proceso, sin red:

- **Ley 51 de 1983 («Ley Emiliani»)** traslada siete festivos al **lunes
  siguiente** cuando no caen en lunes: Reyes (6 ene), San José (19 mar), San
  Pedro y San Pablo (29 jun), Asunción (15 ago), Día de la Raza (12 oct), Todos
  los Santos (1 nov) e Independencia de Cartagena (11 nov).
- **Seis festivos no se trasladan nunca**: Año Nuevo (1 ene), Día del Trabajo
  (1 may), Independencia (20 jul), Batalla de Boyacá (7 ago), Inmaculada
  Concepción (8 dic) y Navidad (25 dic).
- **Cinco cuelgan de la Pascua**: Jueves Santo (−3) y Viernes Santo (−2), que no
  se trasladan, y Ascensión (+43), Corpus Christi (+64) y Sagrado Corazón (+71),
  cuyos desplazamientos ya incorporan el traslado al lunes que la misma ley les
  aplica.

La Pascua se obtiene con el **algoritmo gregoriano anónimo** (Meeus/Jones/
Butcher), que es aritmética entera y da el mismo resultado en cualquier equipo y
cualquier año. Depender de una API remota durante la petición habría hecho que
un plazo legal dependiera de la disponibilidad de un tercero — exactamente lo
que `EQ-024` dice de Resend: un canal no decide un trámite.

El resultado son **18 festivos al año**, que es el número que publica Colombia.

El borde de fin de mes, resuelto y no evitado
--------------------------------------------------------
`sumar_meses()` fija la convención que el encargo pide nombrar: si el día no
existe en el mes destino, se usa **el último día de ese mes**. 31 de enero + 1
mes es el 28 de febrero (29 en bisiesto), y 31 de enero + 3 meses es el 30 de
abril. Es la regla habitual de los plazos en meses y la única que no inventa un
día que no existe ni salta al mes siguiente.


"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from functools import lru_cache

#: Los seis que la ley no mueve. `(mes, día)`.
_FIJOS: tuple[tuple[int, int], ...] = (
    (1, 1),    # Año Nuevo
    (5, 1),    # Día del Trabajo
    (7, 20),   # Grito de Independencia
    (8, 7),    # Batalla de Boyacá
    (12, 8),   # Inmaculada Concepción
    (12, 25),  # Navidad
)

#: Los siete que la Ley 51 de 1983 traslada al lunes siguiente. `(mes, día)`.
_EMILIANI: tuple[tuple[int, int], ...] = (
    (1, 6),    # Reyes Magos
    (3, 19),   # San José
    (6, 29),   # San Pedro y San Pablo
    (8, 15),   # Asunción de la Virgen
    (10, 12),  # Día de la Raza
    (11, 1),   # Todos los Santos
    (11, 11),  # Independencia de Cartagena
)

#: Desplazamientos en días desde el Domingo de Pascua.
#:
#: Los negativos son Semana Santa y **no** se trasladan. Los tres positivos ya
#: incorporan el traslado al lunes que la Ley Emiliani les aplica: la fiesta
#: litúrgica cae en +39, +60 y +68, y el festivo civil en +43, +64 y +71 —los
#: tres, lunes—. Se escriben ya trasladados para que no haya dos reglas
#: aplicándose al mismo día.
_DESDE_LA_PASCUA: tuple[int, ...] = (
    -3,   # Jueves Santo
    -2,   # Viernes Santo
    43,   # Ascensión del Señor
    64,   # Corpus Christi
    71,   # Sagrado Corazón de Jesús
)

#: Cuántos festivos tiene un año colombiano. No se usa para calcular: es la
#: comprobación de que las tres listas de arriba siguen completas.
FESTIVOS_POR_ANIO = 18

_LUNES = 0
_SABADO = 5


class PlazoInvalido(ValueError):
    """Un plazo que no se puede calcular. Un número de días negativo, por ejemplo."""


def pascua(anio: int) -> date:
    """El Domingo de Pascua de ese año, por el algoritmo gregoriano anónimo.

    Aritmética entera pura: mismo resultado en cualquier equipo, sin red y sin
    tabla que mantener. Es la referencia de la que cuelgan cinco festivos.
    """
    a = anio % 19
    siglo, resto = divmod(anio, 100)
    b, c = divmod(siglo, 4)
    d = (siglo + 8) // 25
    e = (siglo - d + 1) // 3
    f = (19 * a + siglo - b - e + 15) % 30
    g, h = divmod(resto, 4)
    i = (32 + 2 * c + 2 * g - f - h) % 7
    k = (a + 11 * f + 22 * i) // 451
    mes, dia = divmod(f + i - 7 * k + 114, 31)
    return date(anio, mes, dia + 1)


def _al_lunes_siguiente(dia: date) -> date:
    """El lunes de la Ley Emiliani. Si ya es lunes, el mismo día."""
    if dia.weekday() == _LUNES:
        return dia
    return dia + timedelta(days=7 - dia.weekday())


@lru_cache(maxsize=64)
def festivos_de(anio: int) -> frozenset[date]:
    """Los 18 festivos colombianos de ese año.

    `lru_cache` porque `sumar_dias_habiles()` pregunta día a día y un plazo de 15
    hábiles cruza el conjunto dos o tres decenas de veces. El caché es correcto
    porque la respuesta sólo depende del año: no hay estado ni reloj de por medio.

    El Domingo de Pascua **no** está en el conjunto: es domingo, así que no es
    hábil por serlo, y meterlo aquí lo contaría dos veces el día que alguien use
    esta lista para otra cosa.
    """
    domingo = pascua(anio)
    dias = {date(anio, mes, dia) for mes, dia in _FIJOS}
    dias |= {_al_lunes_siguiente(date(anio, mes, dia)) for mes, dia in _EMILIANI}
    dias |= {domingo + timedelta(days=desplazamiento) for desplazamiento in _DESDE_LA_PASCUA}
    return frozenset(dias)


def es_festivo(dia: date | datetime) -> bool:
    """Si ese día es festivo nacional en Colombia."""
    jornada = dia.date() if isinstance(dia, datetime) else dia
    return jornada in festivos_de(jornada.year)


def es_habil(dia: date | datetime) -> bool:
    """Si ese día cuenta para un plazo de `EQ-022`.

    Ni sábado, ni domingo, ni festivo nacional. No contempla festivos locales ni
    de sector: no existen para un plazo administrativo nacional, y añadirlos sin
    una fuente aprobada sería inventar días de más.
    """
    jornada = dia.date() if isinstance(dia, datetime) else dia
    return jornada.weekday() < _SABADO and jornada not in festivos_de(jornada.year)


def sumar_dias_habiles(desde: datetime, dias: int) -> datetime:
    """`desde` más `dias` hábiles, conservando hora y zona.

    Cuenta hacia adelante día a día en vez de estimar con una fórmula: para 15 y
    23 días el coste es irrelevante y una fórmula se equivoca justo en los bordes
    —empezar en sábado, cruzar dos fines de semana, caer en un puente— que son
    los que importan.

    El día de partida **no cuenta**, sea hábil o no: el plazo empieza a correr al
    día siguiente, que es como se cuenta un término administrativo.
    """
    if dias < 0:
        raise PlazoInvalido("un plazo no puede ser negativo")
    momento = desde
    restantes = dias
    while restantes > 0:
        momento += timedelta(days=1)
        if es_habil(momento):
            restantes -= 1
    return momento


def sumar_meses(momento: datetime, meses: int) -> datetime:
    """`momento` más `meses` **calendario**, conservando hora y zona.

    Cuando el día no existe en el mes destino se usa el último día de ese mes.
    Ver la cabecera del módulo sobre por qué ésta es la convención y no otra.
    """
    if meses < 0:
        raise PlazoInvalido("un plazo no puede ser negativo")
    total = momento.month - 1 + meses
    anio = momento.year + total // 12
    mes = total % 12 + 1
    dia = min(momento.day, calendar.monthrange(anio, mes)[1])
    return momento.replace(year=anio, month=mes, day=dia)
