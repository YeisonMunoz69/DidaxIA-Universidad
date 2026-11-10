from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from functools import lru_cache


_FIJOS: tuple[tuple[int, int], ...] = (
    (1, 1),
    (5, 1),
    (7, 20),
    (8, 7),
    (12, 8),
    (12, 25),
)


_EMILIANI: tuple[tuple[int, int], ...] = (
    (1, 6),
    (3, 19),
    (6, 29),
    (8, 15),
    (10, 12),
    (11, 1),
    (11, 11),
)


_DESDE_LA_PASCUA: tuple[int, ...] = (
    -3,
    -2,
    43,
    64,
    71,
)


FESTIVOS_POR_ANIO = 18

_LUNES = 0
_SABADO = 5


class PlazoInvalido(ValueError):
    pass

def pascua(anio: int) -> date:
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
    if dia.weekday() == _LUNES:
        return dia
    return dia + timedelta(days=7 - dia.weekday())

@lru_cache(maxsize=64)
def festivos_de(anio: int) -> frozenset[date]:
    domingo = pascua(anio)
    dias = {date(anio, mes, dia) for mes, dia in _FIJOS}
    dias |= {_al_lunes_siguiente(date(anio, mes, dia)) for mes, dia in _EMILIANI}
    dias |= {domingo + timedelta(days=desplazamiento) for desplazamiento in _DESDE_LA_PASCUA}
    return frozenset(dias)

def es_festivo(dia: date | datetime) -> bool:
    jornada = dia.date() if isinstance(dia, datetime) else dia
    return jornada in festivos_de(jornada.year)

def es_habil(dia: date | datetime) -> bool:
    jornada = dia.date() if isinstance(dia, datetime) else dia
    return jornada.weekday() < _SABADO and jornada not in festivos_de(jornada.year)

def sumar_dias_habiles(desde: datetime, dias: int) -> datetime:
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
    if meses < 0:
        raise PlazoInvalido("un plazo no puede ser negativo")
    total = momento.month - 1 + meses
    anio = momento.year + total // 12
    mes = total % 12 + 1
    dia = min(momento.day, calendar.monthrange(anio, mes)[1])
    return momento.replace(year=anio, month=mes, day=dia)
