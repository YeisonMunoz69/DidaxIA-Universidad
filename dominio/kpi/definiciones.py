from __future__ import annotations

from typing import Final


VERSION_DEFINICIONES: Final = "definiciones.v1.4"


ZONA_HORARIA: Final = "America/Bogota"


INTERVALO: Final = "[desde,hasta)"


TURNO_VALIDO: Final = (
    "unidad lógica (sujeto, sesión, turno) con las dos voces registradas, "
    "contexto de uso 'aprendizaje_estudiante' e instante dentro del periodo; "
    "un turno degradado cuenta como válido y se marca aparte"
)


SESION: Final = (
    "el hilo persistido identificador_sesion; no la sesión de autenticación "
    "ni una ventana de inactividad inferida"
)


REGRESO: Final = (
    "al menos un turno válido en una sesión distinta de la primera, dentro de "
    "(primera sesión, primera sesión + d días]"
)


POBLACION_ELEGIBLE: Final = (
    "matrículas cuyo intervalo de vigencia se solapa con el periodo consultado; "
    "cada turno se atribuye a la clase vigente en su instante y se excluye todo "
    "uso profesional (EQ-031), cuentas de prueba y clases archivadas"
)


ACTIVIDAD: Final = (
    "al menos un turno válido cuyo instante, en America/Bogota, cae en la fecha"
)


MUESTRA_MINIMA: Final = 5


MUESTRA_MINIMA_DISTRIBUCION: Final = 10
