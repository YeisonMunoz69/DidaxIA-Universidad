"""
definiciones.py — Qué significa exactamente cada palabra del catálogo KPI v1.1
==============================================================================

El encargo de la Fase 8 pide *«definir cuidadosamente qué significa turno
válido, sesión, regreso y población elegible»*. Estas cuatro palabras aparecen
en siete indicadores de adopción y en la mitad de los de recuperación; escritas
en cada consulta SQL habrían acabado significando cuatro cosas distintas.

Aquí están una sola vez, como constantes de dominio, y el adaptador de cálculo
las cita en vez de reinventarlas. Cambiar una definición es cambiar el catálogo,
y por eso `VERSION_DEFINICIONES` acompaña a `VERSION_CATALOGO`: dos resultados
producidos con definiciones distintas no son comparables aunque compartan
código.

Por qué el periodo se interpreta en America/Bogota
--------------------------------------------------------
Los instantes se persisten con zona (`timestamptz`) y son inequívocos. Lo que
la zona decide es dónde cae el **día local**: «días activos por estudiante»
cuenta fechas, y una conversación de las 23:40 en Popayán pertenece a ese día y
no al siguiente, que es lo que diría UTC. La conversión se aplica sólo al
derivar la fecha, nunca al guardar.


"""

from __future__ import annotations

from typing import Final

#: Sube cuando cambia el significado de una de estas palabras, no cuando cambia
#: una consulta. Viaja dentro de cada resultado.
VERSION_DEFINICIONES: Final = "definiciones.v1.4"

#: La zona en la que se interpretan periodos y fechas locales. Los instantes
#: siguen persistidos con zona; esto sólo decide a qué día pertenece cada uno.
ZONA_HORARIA: Final = "America/Bogota"

#: El intervalo es semiabierto en las dos direcciones del catálogo: `desde`
#: entra, `hasta` no. Así dos periodos consecutivos no cuentan dos veces el
#: mismo turno, que es el error clásico de un intervalo cerrado.
INTERVALO: Final = "[desde,hasta)"

#: **Turno válido.** Una unidad lógica `(sujeto, sesión, turno)` en la que:
#:
#: 1. existe la voz del estudiante **y** la voz del sistema —un turno con una
#:    sola voz quedó a medias y no se cuenta como uso;
#: 2. las dos voces declaran `contexto_de_uso = 'aprendizaje_estudiante'`
#:    (`EQ-031`); y
#: 3. el instante del turno cae dentro del periodo.
#:
#: Un turno **degradado** SÍ es válido: el estudiante lo usó y el sistema
#: respondió explicando que no podía. Excluirlo inflaría artificialmente la
#: calidad medida en `recuperacion.*`, que es justo lo que esos indicadores
#: existen para vigilar.
TURNO_VALIDO: Final = (
    "unidad lógica (sujeto, sesión, turno) con las dos voces registradas, "
    "contexto de uso 'aprendizaje_estudiante' e instante dentro del periodo; "
    "un turno degradado cuenta como válido y se marca aparte"
)

#: **Sesión.** El hilo `identificador_sesion` del historial: la conversación que
#: el estudiante ve como una charla. NO es la sesión de autenticación ni una
#: ventana de inactividad inferida.
#:
#: Se elige el hilo y no una ventana temporal porque el hilo **está
#: persistido** y una ventana habría exigido fijar un umbral de inactividad que
#: ninguna decisión del equipo ha aprobado. Inventarlo aquí sería decidir
#: producto dentro de una consulta.
SESION: Final = (
    "el hilo persistido identificador_sesion; no la sesión de autenticación "
    "ni una ventana de inactividad inferida"
)

#: **Regreso.** Un estudiante regresa a `d` días si tiene al menos un turno
#: válido en una sesión **distinta** de la primera, cuyo instante cae en
#: `(primera_sesión, primera_sesión + d días]`.
#:
#: Dos exigencias, y las dos importan: sesión distinta —seguir escribiendo en la
#: misma charla es continuar, no volver— y ventana medida desde la PRIMERA
#: sesión de la persona, no desde el inicio del periodo consultado.
REGRESO: Final = (
    "al menos un turno válido en una sesión distinta de la primera, dentro de "
    "(primera sesión, primera sesión + d días]"
)

#: **Población elegible.** Matrículas aprobadas cuyo intervalo se solapa con el
#: periodo consultado, contadas únicamente mientras estuvieron vigentes.
#:
#: «Aprobada» se lee de `clase_matricula_historial`: la migración 18 hizo de la
#: aprobación un hecho persistido y marcó lo anterior como `preexistente`. Las
#: dos cuentan como matrícula vigente; el catálogo distingue su procedencia para
#: poder decir cuánta población viene de un hecho verificable y cuánta es
#: herencia.
#:
#: Una cuenta marcada explícitamente como prueba, o una clase archivada, queda
#: fuera del piloto aunque su matrícula histórica se conserve para auditoría.
#: Nadie sin matrícula vigente entra en un denominador de adopción, y ninguna
#: cuenta profesional entra en ninguno (`EQ-031`).
POBLACION_ELEGIBLE: Final = (
    "matrículas cuyo intervalo de vigencia se solapa con el periodo consultado; "
    "cada turno se atribuye a la clase vigente en su instante y se excluye todo "
    "uso profesional (EQ-031), cuentas de prueba y clases archivadas"
)

#: **Actividad.** Existe actividad de un estudiante en una fecha local si tiene
#: al menos un turno válido cuyo instante, convertido a `ZONA_HORARIA`, cae en
#: esa fecha.
ACTIVIDAD: Final = (
    "al menos un turno válido cuyo instante, en America/Bogota, cae en la fecha"
)

#: El mínimo de observaciones por debajo del cual un indicador **no se publica**
#: y devuelve `muestra_insuficiente`.
#:
#: Cinco, y no un número mayor, porque el piloto trabaja con cursos pequeños y
#: un mínimo alto dejaría el tablero entero en blanco sin proteger a nadie más:
#: el resultado es un agregado sin identidades. Cinco es lo bastante para que
#: una proporción no la decida una sola persona.
#:
#: ⚠️ NO es una regla de anonimato aprobada por el equipo. Es un umbral de
#: legibilidad estadística, y así se declara en las limitaciones de cada
#: resultado. Una política de supresión por tamaño de celda pertenece al equipo.
MUESTRA_MINIMA: Final = 5

#: El mínimo para un indicador **distribucional** —medianas y percentiles—, que
#: necesita más observaciones que una proporción para no describir el ruido.
MUESTRA_MINIMA_DISTRIBUCION: Final = 10
