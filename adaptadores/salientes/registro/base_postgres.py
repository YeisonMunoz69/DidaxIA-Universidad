"""
base_postgres.py — La conexión y la traducción de fallos de los repositorios de la Fase 3
===========================================================================================

Cuatro repositorios nuevos comparten dos cosas: cómo obtienen la conexión y cómo
convierten un fallo de Psycopg en uno de los desenlaces que
`dominio/puertos/almacen.py` declara. Escribirlas cuatro veces habría dejado
cuatro traducciones que acabarían discrepando — es el mismo argumento que
`adaptadores/salientes/conexion.py` da para el plazo de espera.

La cadena entra por el constructor y nunca por el proceso
------------------------------------------------------------------
Ningún repositorio de este árbol lee la variable de la base, ni al importarse ni
después. La composición decide a qué base se habla; el repositorio sólo guarda lo
que recibe. Es la lección de la Fase 2 · sesión 3, donde una constante de módulo
resuelta al importar hacía que la autoridad sobre la base dependiera del orden de
importación.

Los mensajes no llevan valores, y es una regla dura
-------------------------------------------------------------
PostgreSQL redacta mensajes útiles y peligrosos a la vez: una violación de clave
foránea dice literalmente qué clave faltaba, y esa clave puede ser el sujeto de
Google de una persona o la referencia de su documento. Un mensaje así acaba en
una consola, en un registro de CI y en una captura pegada en un chat.

Por eso la traducción conserva **el código SQLSTATE y nada más**, y encadena con
`from None` para que la excepción original —con su texto— no viaje dentro de la
nueva. Se pierde detalle de depuración a cambio de que ningún dato personal salga
por un mensaje de error; el código de cinco caracteres basta para saber qué
restricción falló y buscarla en la migración 11.

Por la misma razón aquí no hay ningún `logging`: el adaptador heredado de
consentimiento registra un aviso cuando falla, y esta frontera no puede hacerlo
sin arriesgarse a escribir lo que acaba de recibir.

Un fallo del almacén sí sube
-------------------------------------
Y es el cambio de fondo respecto del adaptador heredado, que captura cualquier
excepción y devuelve `None`. Aquí una base caída levanta `AlmacenNoDisponible`,
para que la sesión 3 pueda mostrar mantenimiento (`EQ-024`) en vez de un
onboarding que la persona ya completó.

Y las operaciones sobre cursor que los repositorios comparten · `D1B`
------------------------------------------------------------------------------
La mitad de abajo de este módulo son funciones que reciben un `cur` y no abren
nada: bloquear la persona, resolver la versión requerida, leer su huella, leer
el último acto de una tabla de eventos e insertar uno nuevo.

Están aquí porque **tienen que caber dentro de la transacción de quien llama**.
`AdaptadorDecisionConjuntaPostgres` escribe dos actos en dos tablas bajo un solo
`FOR UPDATE`, así que no puede componer dos adaptadores —serían dos
transacciones— y necesita las mismas operaciones que aquéllos usan por dentro.

Antes de `D1B` tres de ellas estaban escritas dos y tres veces entre
`consentimiento_versionado_db.py` y `menores_db.py`: «el último acto», «la
versión de la concesión otorgada» y el `INSERT ... RETURNING`. Repetidas, cada
copia podía cambiar de criterio por su cuenta — y «el último acto» con dos
desempates distintos es un estado vigente que depende de a quién se le pregunte.


"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.conexion import conectar
from dominio.modelo.identidad import CategoriaDeEdad, categoria_de_edad
from dominio.puertos.almacen import (
    AlcanceIncorrecto,
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    DatoNoAdmitido,
    ErrorDeAlmacen,
    EscrituraRechazada,
    PerfilSinEdad,
    ReferenciaDesconocida,
    VersionNoVigente,
)
from dominio.puertos.gobierno import SupresionEnCurso

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

#: SQLSTATE → qué desenlace del contrato es. La lista es corta a propósito: lo
#: que no está aquí es «la base no pudo servir esta operación», que es
#: indisponibilidad y no un rechazo con motivo.
_INTEGRIDAD_REFERENCIAL = "23503"          # foreign_key_violation
_RECHAZOS = {
    "23505": "ya existe un registro con esa clave",           # unique_violation
    "23514": "un valor no cumple una restricción del esquema",  # check_violation
    "23502": "falta un valor obligatorio",                    # not_null_violation
    "22001": "un valor excede la longitud admitida",          # string_data_right_truncation
}
#: El esquema no está migrado. No es indisponibilidad transitoria: nada se
#: recupera solo, y presentarlo como mantenimiento haría esperar en vano.
_SIN_ESQUEMA = {"42P01", "42703"}          # undefined_table, undefined_column


def _psycopg() -> Any:
    """Psycopg, importado tarde. Mismo criterio que `conexion.py`: quien no vaya
    a hablar con la base no debería tropezar con su dependencia."""
    import psycopg  # noqa: PLC0415

    return psycopg


def _traducir(error: Any) -> ErrorDeAlmacen:
    """El fallo de Psycopg como desenlace del contrato, sin su texto."""
    codigo = getattr(error, "sqlstate", None) or ""
    if not codigo and isinstance(error, _psycopg().DataError):
        # `M1` · un dato que el CONTROLADOR se niega a enviar. Hoy sólo lo
        # produce un `\x00` dentro de un `str`: psycopg levanta `DataError`
        # antes de hablar con el servidor, y por eso no trae SQLSTATE —no hubo
        # servidor que lo asignara—.
        #
        # Las dos mitades de la condición son necesarias:
        #
        # - **sin SQLSTATE** distingue el rechazo del controlador del rechazo
        #   del servidor. `22001` también es un `DataError`, pero llegó a la
        #   base y la base lo denegó: eso es `EscrituraRechazada` y se resuelve
        #   más abajo, sin cambios;
        # - **`DataError`** distingue el dato del transporte. `OperationalError`
        #   tampoco trae SQLSTATE y es una base que no responde; sin esta mitad,
        #   una base caída empezaría a contestar «no existe» y el aviso de
        #   `EQ-024` no llegaría nunca.
        #
        # Antes caía en el `AlmacenNoDisponible` del final y un código
        # malformado del cliente se vestía de avería del servidor.
        return DatoNoAdmitido("el valor no es representable en la base")
    if codigo == _INTEGRIDAD_REFERENCIAL:
        return ReferenciaDesconocida(
            f"la escritura nombra algo que no existe (SQLSTATE {codigo})"
        )
    if codigo in _RECHAZOS:
        return EscrituraRechazada(f"{_RECHAZOS[codigo]} (SQLSTATE {codigo})")
    if codigo in _SIN_ESQUEMA:
        return AlmacenNoConfigurado(
            f"la base no tiene el esquema de la migración 11 (SQLSTATE {codigo})"
        )
    detalle = f" (SQLSTATE {codigo})" if codigo else ""
    return AlmacenNoDisponible(f"la base no pudo atender la operación{detalle}")


@contextmanager
def traducir_fallo() -> Iterator[None]:
    """Convierte lo que levante Psycopg dentro del bloque en un desenlace del
    contrato, sin abrir ninguna conexión.

    `RepositorioPostgres._conexion()` hace lo mismo, pero atado a su propia
    cadena y a su propia conexión. Esto existe para los adaptadores que **no**
    heredan de él y aun así tienen que hablar el mismo idioma de errores —hoy
    `historial.py`, que es anterior a esta base y gestiona su conexión.

    Sin esto, `GET /api/historial` recibía una excepción cruda de Psycopg y no
    podía distinguir «la base no responde» de cualquier otro fallo: de ahí salía
    el `except Exception: []` que el hito R6 retira. La ruta necesita
    `AlmacenNoDisponible` para responder mantenimiento, y necesita que ese tipo
    llegue por el mismo camino desde todos los adaptadores.
    """
    psycopg = _psycopg()
    try:
        yield
    except ErrorDeAlmacen:
        # Ya es un desenlace del contrato. Volver a traducirlo lo convertiría en
        # indisponibilidad y perdería su motivo.
        raise
    except psycopg.Error as error:
        raise _traducir(error) from None


class RepositorioPostgres:
    """Base común de los repositorios de identidad, consentimiento y roles."""

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        """Una conexión, o el desenlace que corresponda.

        Sin cadena levanta `AlmacenNoConfigurado` **antes** de intentar nada: no
        hay nada que reintentar y no es mantenimiento. Todo lo que Psycopg
        levante dentro del bloque —conectando o ejecutando— sale traducido.
        """
        if not self._cadena:
            raise AlmacenNoConfigurado(
                "este repositorio no recibió cadena de conexión: la composición "
                "no lo cableó a ninguna base"
            )
        psycopg = _psycopg()
        try:
            with conectar(self._cadena) as cnx:
                yield cnx
        except ErrorDeAlmacen:
            # Ya es un desenlace del contrato —lo levantó el repositorio, no la
            # base—. Volver a traducirlo lo convertiría en indisponibilidad.
            raise
        except psycopg.Error as error:
            raise _traducir(error) from None

    @contextmanager
    def _escritura(self) -> Iterator[Any]:
        """Conexión y transacción explícita para una operación atómica.

        Las escrituras de esta frontera leen el estado vigente y escriben en
        función de él —la transición del consentimiento, el número del intento
        siguiente—, así que la lectura y la escritura tienen que caber en la
        misma transacción o dos peticiones simultáneas producirían dos actos
        incompatibles.
        """
        with self._conexion() as cnx, cnx.transaction():
            yield cnx


#: La versión que rige AHORA en un alcance. **La regla vive en la base**, en
#: `didaxia_version_requerida()` (migración 11), y aquí sólo se la llama.
#:
#: Antes del hito A2 esta constante llevaba la consulta escrita, y la lectura del
#: estado vigente llevaba otra copia como CTE. Dos redacciones de la misma regla
#: son dos reglas en cuanto alguien corrige una: eso es exactamente lo que la
#: revisión encontró. Ahora hay una sola definición y los tres consumidores
#: —este adaptador, la consulta de estado y el disparador que valida cada acto—
#: la comparten.
SQL_VERSION_REQUERIDA = "SELECT didaxia_version_requerida(%s)"

#: Las dos tablas de eventos cuyo nombre puede interpolarse en las consultas de
#: este módulo. Lista cerrada y de este árbol: el nombre de una tabla no admite
#: parámetro, así que la única defensa aceptable es que el valor no pueda venir
#: de fuera. `exigir_tabla_de_eventos()` es la única puerta.
_TABLAS_DE_EVENTOS = frozenset({"consentimiento_evento", "asentimiento_evento"})


def exigir_persona(cur: Any, sujeto_google: str) -> int | None:
    """Bloquea la fila de la persona, confirma que existe y devuelve su edad.

    `FOR UPDATE` no protege la fila de `persona` —aquí no se cambia—: sirve de
    cerrojo por titular para que dos escrituras del mismo sujeto se serialicen.
    Sin él, dos peticiones podrían leer el mismo estado vigente y escribir dos
    eventos que juntos no forman una transición válida.

    Devuelve `edad_declarada` —que puede ser `None`— porque las escrituras que
    dependen del régimen de edad tienen que decidirlo **con la fila ya
    bloqueada**: leerla en otra consulta abriría la ventana en la que alguien
    cumple 18 entre la comprobación y el INSERT.
    """
    cur.execute(
        "SELECT edad_declarada FROM persona WHERE sujeto_google = %s FOR UPDATE",
        (sujeto_google,),
    )
    fila = cur.fetchone()
    if fila is None:
        raise ReferenciaDesconocida("esa persona no está registrada")
    return fila[0]


# Filtro de visibilidad del directorio de personas (alias p). No autoriza una
# lectura por ID ni reemplaza exigir_sin_supresion dentro de la transacción.
FILTRO_PERSONA_SIN_SUPRESION_SQL = """NOT EXISTS (
    SELECT 1 FROM solicitud_supresion s
    WHERE s.sujeto_google = p.sujeto_google AND s.estado = 'solicitada')"""


def exigir_sin_supresion(cur: Any, sujeto_google: str) -> None:
    """Ninguna escritura de la persona mientras tenga un trámite abierto.

    `EQ-022` y `ESTADO-ACTUAL.md` §10.2: durante la supresión se puede consultar
    y cancelar, **no aportar ni registrar datos nuevos**. Se llama con la fila de
    `persona` ya bloqueada por `exigir_persona()`, de modo que quede **dentro de
    la misma transacción** que la escritura que protege.

    Por qué eso importa, y no es una preferencia
    ------------------------------------------------------
    `AdaptadorSolicitudesDeSupresionPostgres.abrir()` bloquea la **misma** fila
    con el mismo `FOR UPDATE`. Con las dos operaciones esperando en el mismo
    cerrojo sólo caben dos historias, y las dos son un orden serial:

    - la escritura toma el cerrojo primero → termina y confirma; el trámite se
      abre después, sobre datos que ya existían. Válido: ocurrió antes;
    - el trámite toma el cerrojo primero → la escritura espera, entra, vuelve a
      comprobar y se rechaza.

    Nunca queda una escritura **posterior** a una supresión ya establecida, que
    es la propiedad entera. Una lectura fuera de la transacción habría dejado la
    ventana entre comprobar y escribir.

    ⚠️ **Sin `to_regclass()`, y es deliberado.** `estado_vigente_db.py` la usa
    para que un despliegue sin la migración 12 pueda seguir *leyendo* el estado;
    allí una tabla ausente significa «no hay trámite porque no hay dónde
    registrarlo», que es cierto para una lectura.

    Aquí no vale. Después de la Fase 3 las migraciones 01–12 son parte del
    esquema requerido, así que una tabla ausente es un **despliegue incompleto**
    y no una licencia para escribir: si esta consulta no se puede hacer, no se
    sabe si hay trámite, y no saberlo no puede parecerse a que no lo haya.
    `_traducir()` convierte el `42P01` en `AlmacenNoConfigurado`, que el borde
    presenta como mantenimiento (`EQ-024`).

    No se lee ni una columna más que la existencia: quien necesite las fechas del
    trámite las pide por su ruta, con su sesión.

    ⚠️ **Una sola redacción.** Estaba dentro de
    `AdaptadorDecisionConjuntaPostgres` y ahora vive aquí, junto a
    `exigir_persona()`, porque la usan cinco escrituras. Una copia por adaptador
    habría sido cinco reglas en cuanto alguien corrigiera una — y la que se
    olvidara sería un hueco por el que se escribe durante un trámite.
    """
    cur.execute(
        "SELECT 1 FROM solicitud_supresion "
        "WHERE sujeto_google = %s AND estado = 'solicitada' "
        "LIMIT 1",
        (sujeto_google,),
    )
    if cur.fetchone() is not None:
        raise SupresionEnCurso(
            "hay un trámite de supresión en curso: mientras dure no se registra "
            "ningún tratamiento nuevo"
        )


def exigir_persona_activa(cur: Any, sujeto_google: str) -> int | None:
    """`exigir_persona()` + `exigir_sin_supresion()`, en ese orden y sin hueco.

    Las dos van juntas en toda escritura de datos del sujeto, y el orden es el
    contrato: primero el cerrojo, después la comprobación. Al revés, la
    comprobación se haría sin cerrojo y volvería la ventana que este diseño
    cierra.

    Existe para que ese orden no dependa de que cada adaptador se acuerde.
    Devuelve lo mismo que `exigir_persona()` —la edad declarada, que puede ser
    `None`— porque quien la llama suele necesitarla a continuación.

    ⚠️ **Exige que la persona esté registrada**, y por eso no vale para todas las
    escrituras: `clase.creador` es `text` sin clave foránea a `persona`, así que
    hay clases cuyo creador no tiene fila. Para ésas está
    `bloquear_y_exigir_sin_supresion()`, que no inventa un requisito que el
    esquema no tiene.
    """
    edad = exigir_persona(cur, sujeto_google)
    exigir_sin_supresion(cur, sujeto_google)
    return edad


def bloquear_y_exigir_sin_supresion(cur: Any, sujeto_google: str) -> None:
    """El cerrojo y el trámite **sin exigir que la persona exista**.

    Misma garantía que `exigir_persona_activa()` para quien sí tiene fila: se
    bloquea con `FOR UPDATE` y se comprueba dentro de la misma transacción, de
    modo que la carrera con `abrir()` siga resolviéndose en el mismo cerrojo.

    La diferencia es qué pasa con quien **no** está en `persona`. Se deja pasar,
    y no es una concesión: `solicitud_supresion.sujeto_google` referencia a
    `persona`, así que sin fila no puede existir una solicitud que comprobar. Lo
    que se evitaría exigiendo la fila no es un hueco de supresión — sería una
    regla nueva sobre quién puede crear una clase, y este encargo no la decide.

    `clase.creador` y `clase_matricula.identificador` son `text` libres en la
    migración 08: hoy hay clases cuyo creador no está en `persona`, y varias
    pruebas de integración las construyen así. Convertir eso en un error sería un
    cambio de producto disfrazado de corrección de seguridad.
    """
    cur.execute(
        "SELECT 1 FROM persona WHERE sujeto_google = %s FOR UPDATE",
        (sujeto_google,),
    )
    if cur.fetchone() is None:
        # Sin fila de identidad no puede haber solicitud —clave foránea— así que
        # no hay trámite que respetar. La consulta se hace igual, para que un
        # esquema sin la migración 12 falle aquí y no más adelante.
        exigir_sin_supresion(cur, sujeto_google)
        return
    exigir_sin_supresion(cur, sujeto_google)


def exigir_categoria_de_edad(edad: int | None) -> CategoriaDeEdad:
    """La categoría con la que se emite un acto, o el rechazo si no se puede.

    Sin edad declarada no hay régimen de `EQ-016` que aplicar, así que el acto no
    se registra. No se asume mayoría de edad: es la corrección deliberada de
    `DD-26`, y el disparador `didaxia_derivar_categoria_edad` la repite en la
    base para que no dependa de que la escritura pase por aquí.
    """
    categoria = categoria_de_edad(edad)
    if categoria is CategoriaDeEdad.NO_DECLARADA:
        # `PerfilSinEdad` y no `EscrituraRechazada` a secas desde `D1B`: sigue
        # siendo un rechazo con motivo —y quien atrape la clase madre lo sigue
        # atrapando— pero ahora se puede distinguir del resto para responder
        # «completa tu perfil» en vez de un conflicto sin explicación.
        raise PerfilSinEdad(
            "no se registra un acto de consentimiento sin edad declarada"
        )
    return categoria


def version_requerida_de(cur: Any, alcance: str) -> str | None:
    """La versión que rige ahora en ese alcance, o `None`.

    Llama a `didaxia_version_requerida()` —la única redacción de la regla— y
    normaliza el resultado: la función siempre devuelve **una fila**, con `NULL`
    dentro cuando no hay versión requerida, así que `fetchone()` nunca es `None`
    y comprobar sólo eso dejaría pasar un `(None,)` como si fuera un código.
    """
    cur.execute(SQL_VERSION_REQUERIDA, (alcance,))
    fila = cur.fetchone()
    return fila[0] if fila else None


def exigir_version_requerida(cur: Any, codigo: str, alcance: str) -> None:
    """Que el acto use **exactamente** la versión que rige ahora en su alcance.

    Es la regla del hito A2 aplicada a otorgar, rechazar y cargar evidencia. No
    basta con que la versión siga abierta: si una posterior la desplazó, aceptar
    el texto viejo no autoriza el tratamiento que hoy se hace.

    La garantía real está en el disparador `didaxia_version_del_acto`; esta
    comprobación no la sustituye. Existe para que el rechazo llegue con un motivo
    **preciso** —futura, vencida, desplazada o sin ninguna vigente— en vez de con
    un mensaje genérico o una violación de clave que no se puede mostrar.

    `FOR SHARE` retiene la fila de la versión mientras dura la transacción, de
    modo que nadie pueda publicar una posterior entre la comprobación y el INSERT.
    """
    cur.execute(
        """
        SELECT alcance,
               vigente_desde <= now() AS ya_empezo,
               (vigente_hasta IS NULL OR now() < vigente_hasta) AS no_vencio
          FROM consentimiento_version
         WHERE codigo = %s
         FOR SHARE
        """,
        (codigo,),
    )
    fila = cur.fetchone()
    if fila is None:
        raise ReferenciaDesconocida("esa versión de consentimiento no existe")
    alcance_real, ya_empezo, no_vencio = fila
    if alcance_real != alcance:
        raise AlcanceIncorrecto(
            f"esa versión es de alcance {alcance_real!r} y aquí hace falta {alcance!r}"
        )
    if not ya_empezo:
        raise VersionNoVigente("esa versión todavía no está vigente")
    if not no_vencio:
        raise VersionNoVigente("esa versión ya está vencida")

    requerida = version_requerida_de(cur, alcance)
    if requerida is None:
        raise VersionNoVigente(
            f"no hay ninguna versión requerida del alcance {alcance!r}: la última "
            "que comenzó ya venció"
        )
    if requerida != codigo:
        # Ni futura ni vencida: sigue abierta y aun así fue **desplazada**. Es el
        # caso que la revisión devolvió, y el motivo tiene que decirlo tal cual.
        raise VersionNoVigente(
            f"esa versión fue desplazada por una posterior del alcance {alcance!r}"
        )


def exigir_tabla_de_eventos(tabla: str) -> str:
    """`tabla` si está en la lista cerrada; si no, un rechazo.

    El nombre de una tabla no admite parámetro y hay que interpolarlo. La única
    defensa aceptable es que el valor **no pueda venir de fuera**, y por eso la
    lista es cerrada y de este árbol. Se comprueba en una función y no en cada
    consulta porque desde `D1B` son cuatro las que interpolan el nombre, y una
    que se olvidara de comprobarlo sería una inyección.
    """
    if tabla not in _TABLAS_DE_EVENTOS:
        raise EscrituraRechazada(f"{tabla!r} no es una tabla de eventos de esta frontera")
    return tabla


def ultimo_acto(cur: Any, tabla: str, sujeto: str, columnas: tuple[str, ...]) -> tuple | None:
    """El acto más reciente de esa persona en esa tabla, o `None`.

    ⚠️ **El desempate es el contrato, no una preferencia.** `ORDER BY momento
    DESC` no basta: dos actos escritos en la misma transacción —que es
    exactamente lo que la decisión conjunta hace— pueden compartir `now()` al
    microsegundo, y PostgreSQL podría devolverlos en cualquier orden. La
    identidad monótona desempata, y es el **mismo** desempate que usan
    `estado_vigente_db.py` y los índices de la migración 11.

    Existe aquí porque hasta `D1B` estaba escrito tres veces —`_vigente()` en el
    adaptador de eventos del titular, `_vigente()` en el del asentimiento y la
    consulta de la concesión— con la misma cláusula copiada. Tres redacciones de
    «el último» son tres criterios en cuanto alguien corrija una.
    """
    proyeccion = ", ".join(columnas)
    cur.execute(
        f"""
        SELECT {proyeccion} FROM {exigir_tabla_de_eventos(tabla)}
         WHERE sujeto_google = %s
         ORDER BY momento DESC, id DESC
         LIMIT 1
        """,  # noqa: S608 — tabla de la lista cerrada; `columnas` es de este árbol
        (sujeto,),
    )
    return cur.fetchone()


def version_de_la_concesion_de(cur: Any, tabla: str, sujeto: str) -> str | None:
    """La versión de la última concesión **otorgada**, o `None`.

    Una sola redacción para los tres consumidores: la lectura pública de cada
    puerto —`version_de_la_concesion()`— y la comprobación que la escritura de
    una revocación repite dentro de su transacción. Si aquí se eligiera «la
    última otorgada» con un criterio y allí con otro, la revocación fallaría
    siempre con un motivo incomprensible.
    """
    cur.execute(
        f"""
        SELECT version FROM {exigir_tabla_de_eventos(tabla)}
         WHERE sujeto_google = %s AND estado = 'otorgado'
         ORDER BY momento DESC, id DESC
         LIMIT 1
        """,  # noqa: S608 — `tabla` está en la lista cerrada de arriba
        (sujeto,),
    )
    fila = cur.fetchone()
    return fila[0] if fila else None


#: Qué columnas asignadas por la base devuelve el `INSERT` de cada tabla.
#:
#: `categoria_edad` sólo existe en la del titular, y allí **la deriva un
#: disparador**: lo que se envíe en el INSERT se descarta, así que la única
#: forma de saber con qué categoría quedó la fila es que la propia sentencia la
#: devuelva. Sale de aquí y no de un parámetro para que nadie pueda pedirle a
#: `asentimiento_evento` una columna que no tiene.
_DEVUELVE_DE = {
    "consentimiento_evento": ("id", "momento", "categoria_edad"),
    "asentimiento_evento": ("id", "momento"),
}


def insertar_acto(
    cur: Any,
    tabla: str,
    *,
    sujeto: str,
    version: str,
    estado: str,
    comprobante: str,
) -> tuple:
    """Añade un acto y devuelve lo que la base le asignó. Nunca modifica ninguno.

    **No hay `ON CONFLICT`, y es el punto entero.** Ninguna de las dos tablas
    tiene una clave única por sujeto que pudiera convertir este `INSERT` en un
    `UPDATE`, así que un rechazo anterior sigue ahí después de reaceptar. Era el
    defecto de `consentimiento_usuario`, y no puede volver por una consulta
    escrita a mano en un adaptador nuevo.

    Devuelve `(id, momento)` y, en la tabla del titular, la `categoria_edad` que
    derivó el disparador. Ver `_DEVUELVE_DE`.
    """
    columnas = ", ".join(_DEVUELVE_DE[exigir_tabla_de_eventos(tabla)])
    cur.execute(
        f"""
        INSERT INTO {tabla}
            (sujeto_google, version, estado, comprobante)
        VALUES (%s, %s, %s, %s)
        RETURNING {columnas}
        """,  # noqa: S608 — tabla de la lista cerrada; `columnas`, de `_DEVUELVE_DE`
        (sujeto, version, estado, comprobante),
    )
    return cur.fetchone()


def huella_de_version(cur: Any, codigo: str) -> str:
    """La `huella_contenido` de una versión publicada.

    Es la prueba de qué texto leyó quien aceptó, y entra en el comprobante. Se
    lee **dentro** de la transacción de escritura y no antes: entre una lectura
    externa y el INSERT cabría una publicación que la cambiara, y el comprobante
    quedaría calculado sobre un paquete distinto del que la fila referencia.

    Levanta `ReferenciaDesconocida` si ese código no existe. No devuelve `None`:
    quien llama ya resolvió el código llamando a `version_requerida_de()`, así
    que una ausencia aquí significa que la fila desapareció bajo la transacción,
    no que no haya versión.
    """
    cur.execute(
        "SELECT huella_contenido FROM consentimiento_version WHERE codigo = %s",
        (codigo,),
    )
    fila = cur.fetchone()
    if fila is None:
        raise ReferenciaDesconocida("esa versión de consentimiento no existe")
    return fila[0]


def exigir_version_de_la_concesion(cur: Any, tabla: str, sujeto: str, codigo: str) -> None:
    """Que la revocación retire la concesión que efectivamente se otorgó.

    Semántica distinta de `exigir_version_requerida()`, y `EQ-022` la exige así:
    quien otorgó conserva el derecho a retirar esa concesión **aunque su
    documento haya vencido o haya sido desplazado**. Lo que no puede es revocar
    una versión arbitraria que nunca se le concedió.
    """
    otorgada = version_de_la_concesion_de(cur, tabla, sujeto)
    if otorgada is None:
        raise EscrituraRechazada("no hay ninguna concesión otorgada que revocar")
    if otorgada != codigo:
        raise EscrituraRechazada(
            "una revocación sólo retira la concesión efectivamente otorgada"
        )
