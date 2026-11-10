"""
contexto_de_uso.py — Para qué se usó el tutor en este turno · `EQ-031`
=========================================================================

`EQ-031` (Yeison, 2026-09-06) concede a docente e investigador un **modo Tutor**
con las herramientas del estudiante, y pone una frontera que no es de interfaz:

    *«ese uso queda excluido de matrícula, evaluación estudiantil, vectores
    conductuales o afectivos, inferencias, alertas, supervisión docente, KPI,
    conjuntos de investigación y entrenamiento»*

y, en la misma decisión, la razón por la que este módulo existe y no basta con
ocultar botones:

    *«una preferencia guardada sólo en el frontend no basta: la API debe derivar
    la elegibilidad desde el rol autenticado, persistir el contexto y aplicar la
    exclusión en cada productor de señales y agregados»*

Este es el «contexto» que esa frase nombra: un dato del dominio, derivado del
rol real, que viaja con el turno y se persiste con él.

POR QUÉ ES UN CONCEPTO DEL DOMINIO Y NO UN `if` EN LA RUTA
------------------------------------------------------------
Porque la misma pregunta la hacen sitios que no son una petición HTTP: el filtro
que registra, el que agregaría KPI, la consulta que arma un conjunto de
investigación y las pruebas. Escrita como una condición dentro de
`rutas/turno.py`, cada uno habría acabado con su propia versión — que es
exactamente cómo el sistema llegó a tener `puede_participar()` en un adaptador
entrante y `consentimiento` en un `dict` de sesión respondiendo a la misma
pregunta con criterios distintos. Es el mismo argumento con el que
`dominio/modelo/acceso.py` salió de las guardas de FastAPI.

EL FALLO SEGURO APUNTA AL LADO CONTRARIO QUE EN EL FRONTEND, Y ES DELIBERADO
------------------------------------------------------------------------------
`nucleo/sesion/rol.js::esEstudiante()` trata como **estudiante** cualquier rol
que no reconozca, porque allí lo que se protege es no enseñar el panel
conductual a quien no debe verlo.

Aquí se protege otra cosa —**no fabricar evaluación sobre quien no es
estudiante**— y por eso la regla es la inversa: sólo un `estudiante` explícito
produce `APRENDIZAJE_ESTUDIANTE`. Cualquier otro valor, incluida una errata del
registro de docentes, cae en `CONSULTA_PROFESIONAL` y queda fuera de perfiles,
alertas y agregados.

Los dos errores no cuestan lo mismo. Excluir de más deja un turno sin contar en
un KPI que todavía no existe; incluir de menos escribe un perfil afectivo, una
alerta docente o una fila de investigación **sobre una persona que nunca
consintió participar como estudiante**, y eso ni se deshace ni se nota.

⚠️ ESTO NO DECIDE QUIÉN PUEDE ENTRAR, Y NO DEBE USARSE PARA ESO
-----------------------------------------------------------------
`contexto_de_uso_de()` responde *«¿este turno alimenta evaluación?»* y **nada
más**. Quién puede usar `POST /api/turno`, y por qué puerta, lo decide una
allowlist explícita en `rutas/turno.py`: un rol desconocido recibe 403, no la
puerta del profesional. Fundir las dos preguntas convertiría el fallo seguro de
arriba en un agujero: cualquier rol no reconocido se saltaría el consentimiento
de `EQ-016` por el mismo camino que lo excluye de la evaluación.

Este módulo no importa FastAPI, ni Psycopg, ni lee variables de entorno.
`pruebas/arquitectura/test_reglas_arquitectonicas.py` lo comprueba para todo
`dominio/`.


"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

#: El único rol cuyo uso del tutor es aprendizaje evaluable. Se nombra como
#: constante y no se escribe suelto: es el valor con el que `Sesiones.abrir()`
#: abre una sesión ordinaria y con el que compara este módulo, y dos literales
#: iguales en dos archivos se separan la primera vez que alguien renombra uno.
ROL_ESTUDIANTE = "estudiante"

#: Los roles a los que `EQ-031` concede el modo Tutor. Allowlist y no «todos
#: menos estudiante»: un rol nuevo no debe heredar el espacio profesional por
#: omisión. Lo consume la puerta de `rutas/turno.py`, no la clasificación.
ROLES_PROFESIONALES = frozenset({"docente", "investigador"})


class ContextoDeUso(StrEnum):
    """Para qué se usó el tutor. Dos valores, y no hay un tercero.

    Los nombres son los del dominio del proyecto y no una traducción de
    `rol`: describen **el uso**, no a la persona. La misma persona puede
    producir turnos de un solo tipo hoy, pero la columna dice qué era el turno,
    no quién lo escribió — que es lo que permite que una consulta posterior
    excluya sin volver a preguntar por el rol de nadie.
    """

    #: Un estudiante usando el tutor. Alimenta perfil, diagnóstico y agregados
    #: en la medida en que `EQ-016` y `RL-09` lo permitan.
    APRENDIZAJE_ESTUDIANTE = "aprendizaje_estudiante"

    #: `EQ-031` · un docente o investigador consultando. Historial personal sí;
    #: evaluación, señales, alertas, KPI y conjuntos de investigación, no.
    CONSULTA_PROFESIONAL = "consulta_profesional"

    #: Tutoría a una cuenta estudiante que no está incluida actualmente en
    #: investigación. Conserva continuidad académica, pero no produce perfil,
    #: diagnóstico, supervisión, KPI ni conjuntos de estudio.
    TUTORIA_ACADEMICA_SIN_INVESTIGACION = "tutoria_academica_sin_investigacion"


#: El valor con el que nacieron las filas anteriores a `EQ-031`.
#:
#: Todas son de estudiantes: antes de esta decisión `POST /api/turno` exigía
#: `acceso == habilitado`, y ese estado sólo lo alcanza quien completó el
#: recorrido de `EQ-020` —perfil, consentimiento, matrícula—. Un docente no
#: podía tener uno. Por eso la migración puede rellenar el histórico con este
#: valor sin reinterpretar nada: no se está adivinando, se está escribiendo lo
#: que la puerta de entrada garantizaba.
CONTEXTO_HISTORICO = ContextoDeUso.APRENDIZAJE_ESTUDIANTE


def contexto_de_uso_de(rol: str | None) -> ContextoDeUso:
    """El contexto de este turno, derivado del **rol real de la sesión**.

    ⚠️ **Nunca de un campo del cliente.** `RP-17` ya fija que la separación por
    rol se decide en el servidor; `EQ-031` lo repite para este caso concreto
    porque aquí el incentivo es nuevo: un estudiante que pudiera declararse
    profesional se saldría del diagnóstico, y un profesional que pudiera
    declararse estudiante metería sus consultas en los agregados de una clase.
    Ninguna de las dos cosas depende de la buena fe del navegador — el rol lo
    resuelve `Sesiones.leer()` desde la cookie y llega aquí ya resuelto.

    Ver la cabecera del módulo sobre por qué lo desconocido cae del lado que
    **no** evalúa.
    """
    return (
        ContextoDeUso.APRENDIZAJE_ESTUDIANTE
        if rol == ROL_ESTUDIANTE
        else ContextoDeUso.CONSULTA_PROFESIONAL
    )


def es_consulta_profesional(contexto: ContextoDeUso) -> bool:
    """Si este turno es una consulta profesional de `EQ-031`."""
    return contexto is ContextoDeUso.CONSULTA_PROFESIONAL


def alimenta_evaluacion(contexto: ContextoDeUso) -> bool:
    """Si este turno puede producir perfil, diagnóstico, alertas o agregados.

    **Es la pregunta que hay que hacer en cada productor de señales**, y por eso
    tiene nombre propio en vez de escribirse como `not es_consulta_profesional()`:
    `EQ-031` pide aplicar la exclusión *«en cada productor de señales y
    agregados»*, y una pregunta con nombre se encuentra buscándola.

    Hoy es exactamente la negación de la otra. Se declaran las dos porque
    describen decisiones distintas —una clasifica, la otra autoriza— y el día
    que aparezca un tercer contexto (un turno de demostración, un banco de
    pruebas) las dos dejarán de ser simétricas sin que haya que buscar dónde.
    """
    return contexto is ContextoDeUso.APRENDIZAJE_ESTUDIANTE


def puede_consultar_como_profesional(rol: str | None) -> bool:
    """Si `EQ-031` concede a este rol el modo Tutor.

    La allowlist de la puerta, separada de la clasificación a propósito: ver la
    advertencia de la cabecera. Un rol desconocido responde `False` y la ruta lo
    rechaza, en vez de dejarlo pasar por la puerta que no exige consentimiento.
    """
    return rol in ROLES_PROFESIONALES


@dataclass(frozen=True, slots=True)
class PoliticaDelTurno:
    """Qué puede producir este turno. Una política con nombres, no una ristra de `if`.

    `EQ-031` enumera nueve efectos de los que hay que excluir la consulta
    profesional. Escritos como condiciones sueltas dentro de `rutas/turno.py`,
    cada uno sería una oportunidad de olvidar el décimo: la lista no está en
    ningún sitio, así que nada avisa cuando falta uno.

    Aquí sí está, y cada efecto tiene un nombre que se puede probar por
    separado. Añadir un productor de señales nuevo obliga a preguntarse a cuál
    de estas propiedades pertenece, que es exactamente la pregunta que `EQ-031`
    quiere que alguien se haga.

    ⚠️ **Todas se derivan de `alimenta_evaluacion()` y ninguna se declara
    suelta.** Es deliberado: si una pudiera valer `True` mientras las demás
    valen `False`, existiría un camino por el que una consulta profesional
    dejaría rastro de evaluación, y ese camino no se vería leyendo el borde.
    Cuando el día de mañana una tenga que separarse —un contexto de
    demostración, por ejemplo— se separará aquí, a la vista, y su prueba lo
    dirá.

    Lo que la política **no** apaga, y `EQ-031` autoriza expresamente: la
    respuesta didáctica, el cómputo simbólico, la recuperación del corpus, las
    gráficas y el historial personal. Un profesional recibe el mismo tutor; lo
    que no recibe es un expediente.
    """

    contexto: ContextoDeUso

    @classmethod
    def de_la_sesion(cls, rol: str | None) -> PoliticaDelTurno:
        """La política de un turno de esta sesión, desde su **rol real**."""
        return cls(contexto_de_uso_de(rol))

    @classmethod
    def del_contexto(cls, contexto: ContextoDeUso | str) -> PoliticaDelTurno:
        """Construye la política desde el contexto sellado por el servidor."""
        return cls(ContextoDeUso(contexto))

    @property
    def es_consulta_profesional(self) -> bool:
        return es_consulta_profesional(self.contexto)

    @property
    def resuelve_matricula(self) -> bool:
        """`PM-B21` · buscar en qué clase está quien escribe.

        Para un profesional no se busca. `mias()` devuelve también las clases
        que **creó**, así que un docente con una sola clase habría quedado con
        todos sus turnos atribuidos a ella —y contando en sus agregados— por el
        mero hecho de haberla creado. `EQ-031` excluye la matrícula del modo
        Tutor, y ésta es la línea concreta donde eso ocurre.
        """
        return alimenta_evaluacion(self.contexto)

    @property
    def escribe_perfil_longitudinal(self) -> bool:
        """`PM-B11` · el perfil afectivo, conceptual y estratégico versionado."""
        return alimenta_evaluacion(self.contexto)

    @property
    def extrae_indicadores_conductuales(self) -> bool:
        """`PM-B10` · señales afectivas o conductuales inferidas del texto.

        Esta autorización es distinta de ``escribe_perfil_longitudinal``:
        impedir la escritura no impide que el filtro 3 calcule una inferencia,
        la use durante la conversación o la copie a la traza forense. `EQ-031`
        excluye también esos tres efectos para una consulta profesional, así
        que el productor se apaga antes de observar el texto.
        """
        return alimenta_evaluacion(self.contexto)

    @property
    def diagnostica(self) -> bool:
        """`PM-B08` · sondeos de dos niveles y su clasificación de concepciones.

        Un sondeo existe para evaluar. Ofrecérselo a un profesional sería
        diagnosticarle una concepción errónea sobre cálculo y guardarla.
        """
        return alimenta_evaluacion(self.contexto)

    @property
    def encola_supervision(self) -> bool:
        """`RU-12` · las alertas que llegan a la cola del docente.

        Una consulta profesional que disparara una alerta la pondría en la cola
        de supervisión de estudiantes — donde un docente la leería como el
        problema de alguien a quien tiene que atender.
        """
        return alimenta_evaluacion(self.contexto)

    @property
    def cuenta_en_agregados(self) -> bool:
        """KPI, estadísticas de curso y conjuntos de investigación.

        Hoy no hay ningún consumidor: los KPI son una decisión humana abierta.
        Se declara igual porque la exclusión tiene que existir **antes** que el
        primer agregado, no después: la columna `contexto_de_uso` de la
        migración 17 es lo que permitirá filtrar, y esta propiedad es el nombre
        con el que se preguntará.
        """
        return alimenta_evaluacion(self.contexto)
