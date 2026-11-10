"""
menores_db.py — Asentimiento y evidencia del representante contra la migración 11
===================================================================================

Las dos implementaciones PostgreSQL de las dimensiones de `EQ-016` que no son el
consentimiento del titular: `asentimiento_evento` por un lado,
`representante_evidencia` y `representante_revision` por el otro.

Ningún archivo entra en PostgreSQL
-------------------------------------------
`registrar_intento()` recibe una referencia opaca, una huella, un tamaño y nada
más. No hay ningún parámetro que pueda contener el PDF, ninguna columna donde
cupiera y ninguna consulta que lo devuelva. El tipo del dominio rechaza además
una referencia `http(s)://` —`EQ-021` descarta un enlace mutable como evidencia
definitiva— y el CHECK de la tabla lo vuelve a rechazar.

Una carga nueva conserva la anterior
---------------------------------------------
El número de intento lo calcula el adaptador **dentro** de la transacción, con la
fila de la persona bloqueada, y lo protege además `UNIQUE (sujeto_google,
intento)`. No hay `ON CONFLICT`, así que la segunda carga no puede convertirse en
un `UPDATE` de la primera: son dos filas y las dos se consultan.

Quién puede revisar, y por qué se comprueba aquí dentro
------------------------------------------------------------------
`EQ-023` reserva la verificación a un investigador autorizado. El adaptador lee
las asignaciones vigentes **en la misma transacción** que la escritura y deja que
el dominio decida —`puede_revisar_evidencia()`—, en vez de comparar correos: un
permiso retirado un segundo antes no puede colarse por una comprobación hecha en
otra conexión.

⚠️ **Y desde el hito R7-B la retiene, además de leerla.** La misma transacción no
bastaba: entre el `SELECT` y el `INSERT` de la revisión cabía una revocación que
se confirmara, y la revisión quedaba autorizada por un permiso que ya no existía
al aplicarse. La comprobación vive ahora en `autorizacion_sql.py`, con el nivel
de lock explicado allí, y es **la misma** que usan `roles_db.py` y
`gobierno_db.py`: hasta esta corrección eran tres redacciones distintas de la
misma pregunta.

Leer también autoriza, y con el mismo lock · C2A
-----------------------------------------------------------------
`cola()`, `detalle()` y `referencia_del_documento()` llaman a la **misma**
`exigir_investigador_administrador()` que `revisar()`, dentro de una transacción
explícita para que el `FOR SHARE` dure lo que dure la consulta. Y la llaman
**antes** de tocar `representante_evidencia`: en una lectura, autorizar después
de consultar no protege nada —el dato ya se leyó— y además convierte el código de
respuesta en un oráculo de qué identificadores existen.

La proyección de esas tres consultas **no incluye `referencia`**. La única que la
trae es `_SQL_REFERENCIA`, que trae esa columna y ninguna más.

Y la de la **cola** tampoco incluye `motivo`. `EQ-021` lo exige al rechazar y el
detalle lo conserva para que una decisión histórica siga siendo comprensible;
una lista paginada no lo consume y arrastrarlo multiplicaría la circulación de un
texto libre escrito por una persona sobre otra. `_SQL_DETALLE` es la proyección
de la cola más esa columna, compuesta sobre ella para que la «última revisión»
la elija el mismo `LATERAL` con el mismo desempate en las dos.

Una revisión por intento, hoy
--------------------------------------
`TRANSICIONES_REPRESENTANTE` no admite pasar de `aprobado` o `rechazado` a otra
resolución del **mismo** intento: la vía prevista para corregir es una carga
nueva, que conserva la anterior. Revisar dos veces el mismo intento levanta
`TransicionInvalida`. La tabla no lo impide —admite varias filas por evidencia y
nunca actualiza una anterior— porque permitirlo el día que el equipo lo decida no
debería exigir una migración.


"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.registro.autorizacion_sql import (
    exigir_investigador_administrador,
)
from adaptadores.salientes.registro.base_postgres import (
    RepositorioPostgres,
    exigir_persona,
    exigir_persona_activa,
    exigir_sin_supresion,
    exigir_version_de_la_concesion,
    exigir_version_requerida,
    insertar_acto,
    ultimo_acto,
    version_de_la_concesion_de,
)
from dominio.modelo.consentimiento import Alcance
from dominio.modelo.evidencia_revisable import (
    EvidenciaRevisable,
    FiltroDeEvidencias,
    PaginaDeEvidencias,
    PosicionDeCursor,
)
from dominio.modelo.identidad import CategoriaDeEdad, categoria_de_edad
from dominio.modelo.menores import (
    EstadoAsentimiento,
    EstadoRepresentante,
    EventoAsentimiento,
    HistorialDeAsentimiento,
    IntentoDeEvidencia,
    ResultadoDeRevision,
    RevisionDeEvidencia,
    exigir_transicion_asentimiento,
    exigir_transicion_representante,
)
from dominio.puertos.almacen import EscrituraRechazada, ReferenciaDesconocida

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

#: Qué estado de la dimensión deja un intento ya resuelto. Una sola traducción
#: entre el resultado de una revisión y el enumerado de `EQ-016`.
_ESTADO_TRAS_REVISION = {
    ResultadoDeRevision.APROBADA: EstadoRepresentante.APROBADO,
    ResultadoDeRevision.RECHAZADA: EstadoRepresentante.RECHAZADO,
}

#: La proyección que sale hacia quien revisa · C2A.
#:
#: ⚠️ **`e.referencia` NO está en esta lista, y es el punto entero.** Las tres
#: consultas de lectura de C2A se construyen sobre este SELECT, así que ninguna
#: puede traer la referencia del archivo privado ni por descuido: no la pide.
#: La única consulta que la pide es `_SQL_REFERENCIA`, que devuelve esa columna y
#: nada más, de modo que leerla sea un acto deliberado y no un campo de sobra en
#: una fila ancha que alguien serialice entera.
#:
#: ⚠️ **Tampoco trae `r.motivo`, y por el mismo tipo de razón.** El motivo de un
#: rechazo es texto libre escrito por una persona sobre otra; el detalle lo
#: necesita para que una decisión histórica siga siendo comprensible y la cola no
#: lo consume. `_SQL_DETALLE` lo añade; ésta no puede traerlo aunque el
#: serializador se despistara, porque no lo pide.
#:
#: `LEFT JOIN LATERAL` con el mismo desempate que `intentos()` —fecha y después
#: identidad monótona—, para que la última revisión sea la misma en las dos.
_SQL_PROYECCION = """
SELECT e.id, e.sujeto_google, e.intento, e.version, e.sha256, e.tamano_bytes,
       e.tipo_mime, e.recibido_en, r.resultado, r.revisada_en,
       p.nombre,
       ARRAY(
           SELECT c.nombre
             FROM clase_matricula m
             JOIN clase c ON c.id = m.clase
            WHERE m.identificador = e.sujeto_google
            ORDER BY c.nombre, c.id
       ) AS clases
  FROM representante_evidencia e
  JOIN persona p ON p.sujeto_google = e.sujeto_google
  LEFT JOIN LATERAL (
       SELECT resultado, revisada_en
         FROM representante_revision
        WHERE evidencia = e.id
        ORDER BY revisada_en DESC, id DESC
        LIMIT 1
  ) r ON true
"""

#: El filtro de estado, con una redacción por valor del enumerado.
#:
#: Es un diccionario **cerrado y de este árbol**, y se indexa con el enumerado
#: —nunca con la cadena que llegó del cliente—. Un `f"WHERE r.resultado = '{x}'"`
#: habría sido más corto y habría puesto texto de fuera dentro del SQL; aquí lo
#: único que viaja del cliente es la elección de una de cuatro constantes que ya
#: estaban escritas, y `filtro_desde()` rechaza cualquier otra antes de llegar.
_FILTRO_SQL = {
    FiltroDeEvidencias.PENDIENTE: "r.resultado IS NULL",
    FiltroDeEvidencias.APROBADA: "r.resultado = 'aprobada'",
    FiltroDeEvidencias.RECHAZADA: "r.resultado = 'rechazada'",
    FiltroDeEvidencias.TODOS: "true",
}

#: La paginación por clave de orden. El cursor entra como par y la comparación de
#: filas de PostgreSQL —`(a, b) > (c, d)`— lo resuelve en una expresión, que es
#: exactamente el orden del `ORDER BY`. Escrito como dos comparaciones sueltas se
#: habría podido desincronizar del orden y producir saltos.
#:
#: `IS NULL` cubre la primera página sin una segunda consulta: sin cursor, la
#: condición es cierta para todas las filas.
_SQL_COLA = (
    _SQL_PROYECCION
    + """
 WHERE {filtro}
   AND (%(desde_fecha)s::timestamptz IS NULL
        OR (e.recibido_en, e.id) > (%(desde_fecha)s::timestamptz, %(desde_id)s::bigint))
 ORDER BY e.recibido_en ASC, e.id ASC
 LIMIT %(limite)s
"""
)

#: El detalle: la proyección de la cola **más el motivo**, una fila.
#:
#: Se compone con `replace()` sobre la lista de columnas en vez de reescribir el
#: SELECT entero, para que la última revisión la elija el mismo `LATERAL` con el
#: mismo desempate —`revisada_en DESC, id DESC`— en las dos consultas. Dos
#: redacciones habrían podido discrepar sobre cuál es «la última», y entonces la
#: cola diría «rechazada» y el detalle enseñaría el motivo de otra revisión.
_SQL_DETALLE = _SQL_PROYECCION.replace(
    "SELECT resultado, revisada_en\n", "SELECT resultado, revisada_en, motivo\n"
).replace(
    "r.resultado, r.revisada_en,\n", "r.resultado, r.revisada_en, r.motivo,\n"
) + """
 WHERE e.id = %s
"""

#: La referencia opaca, sola. Ver el aviso de `_SQL_PROYECCION`.
_SQL_REFERENCIA = "SELECT referencia FROM representante_evidencia WHERE id = %s"


class AdaptadorAsentimientoPostgres(RepositorioPostgres):
    """`PuertoAsentimiento` sobre `asentimiento_evento`.

    Mismo contrato que los eventos del titular: `INSERT` sin `ON CONFLICT`,
    transición comprobada dentro de la transacción y ninguna fila anterior
    modificada.
    """

    def registrar(
        self,
        sujeto_google: str,
        version: str,
        estado: EstadoAsentimiento,
        comprobante: str,
    ) -> EventoAsentimiento:
        provisional = EventoAsentimiento(
            sujeto_google=sujeto_google,
            version=version,
            estado=estado,
            comprobante=comprobante,
            momento=datetime.now(UTC),
        )
        with self._escritura() as cnx, cnx.cursor() as cur:
            # El asentimiento suelto ya sólo se escribe al REVOCAR —la decisión
            # inicial la registra la conjunta— y revocar es un derecho que el
            # trámite no suspende. Aun así el cerrojo se toma igual: la
            # comprobación va en `_revocando()`, que distingue los dos casos.
            edad = self._persona_para(cur, provisional)
            # `EQ-016`: el asentimiento es del MENOR. Un adulto no lo da, da
            # consentimiento. Se comprueba con la fila de `persona` ya bloqueada,
            # y el disparador `asentimiento_evento_solo_menores` lo repite en la
            # base para que no dependa de que la escritura pase por aquí.
            if categoria_de_edad(edad) is not CategoriaDeEdad.MENOR:
                raise EscrituraRechazada(
                    "el asentimiento sólo corresponde a una persona menor de edad"
                )
            # Misma separación que el consentimiento del titular (hito A2): el
            # menor conserva el derecho a retirar su asentimiento aunque el texto
            # que firmó ya no sea el que hoy se pide.
            if provisional.estado is EstadoAsentimiento.REVOCADO:
                exigir_version_de_la_concesion(
                    cur, "asentimiento_evento", provisional.sujeto_google, provisional.version
                )
            else:
                exigir_version_requerida(cur, provisional.version, Alcance.ASENTIMIENTO.value)
            exigir_transicion_asentimiento(
                self._vigente(cur, provisional.sujeto_google), provisional.estado
            )
            identificador, momento = insertar_acto(
                cur,
                "asentimiento_evento",
                sujeto=provisional.sujeto_google,
                version=provisional.version,
                estado=provisional.estado.value,
                comprobante=provisional.comprobante,
            )
            return replace(provisional, momento=momento, secuencia=identificador)


    def version_de_la_concesion(self, sujeto_google: str) -> str | None:
        """La versión de la última concesión otorgada. Ver el puerto.

        Misma consulta que `exigir_version_de_la_concesion()` usa dentro de la
        transacción de escritura, y a propósito: si aquí se eligiera «la última
        otorgada» con un criterio y allí con otro, la revocación fallaría siempre
        con un motivo incomprensible. El desempate por `id` es el mismo.
        """
        with self._conexion() as cnx, cnx.cursor() as cur:
            return version_de_la_concesion_de(cur, "asentimiento_evento", sujeto_google)

    def historial(self, sujeto_google: str, *, requerido: bool) -> HistorialDeAsentimiento:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT id, version, estado, comprobante, momento
                  FROM asentimiento_evento
                 WHERE sujeto_google = %s
                 ORDER BY momento ASC, id ASC
                """,
                (sujeto_google,),
            )
            eventos = tuple(
                EventoAsentimiento(
                    sujeto_google=sujeto_google,
                    version=version,
                    estado=EstadoAsentimiento(estado),
                    comprobante=comprobante,
                    momento=momento,
                    secuencia=identificador,
                )
                for identificador, version, estado, comprobante, momento in cur.fetchall()
            )
        return HistorialDeAsentimiento(
            sujeto_google=sujeto_google, requerido=requerido, eventos=eventos
        )

    def _persona_para(self, cur: Any, provisional: EventoAsentimiento) -> int | None:
        """Bloquea la persona y aplica el trámite **según lo que se escriba**.

        `EQ-022` suspende el tratamiento nuevo, no los derechos. Revocar es un
        derecho —reduce el tratamiento, no lo amplía— y `ESTADO-ACTUAL.md` §10.2
        lo enumera entre lo que sigue disponible durante el trámite. Otorgar o
        rechazar sí es una decisión nueva, y por eso se distinguen aquí.

        Hoy la ruta que llega aquí con `otorgado` o `rechazado` está retirada
        —`410`, `D1B`— y la decisión la registra la conjunta, que ya comprueba lo
        suyo. La distinción se escribe igual porque el puerto sigue admitiendo
        los tres estados y una vía futura no debería estrenarse abierta.
        """
        edad = exigir_persona(cur, provisional.sujeto_google)
        if provisional.estado is not EstadoAsentimiento.REVOCADO:
            exigir_sin_supresion(cur, provisional.sujeto_google)
        return edad

    def _vigente(self, cur: Any, sujeto_google: str) -> EstadoAsentimiento:
        """El último acto. `PENDIENTE` si no hay ninguno.

        Se asume `PENDIENTE` y no `NO_REQUERIDO` a propósito: quien está
        registrando un asentimiento ya decidió que hacía falta, y `NO_REQUERIDO`
        no admite ninguna transición —bloquearía el primer acto de todo menor—.
        """
        fila = ultimo_acto(cur, "asentimiento_evento", sujeto_google, ("estado",))
        return EstadoAsentimiento(fila[0]) if fila else EstadoAsentimiento.PENDIENTE


class AdaptadorEvidenciaDelRepresentantePostgres(RepositorioPostgres):
    """`PuertoEvidenciaDelRepresentante` sobre las dos tablas de evidencia."""

    def registrar_intento(
        self,
        sujeto_google: str,
        version: str,
        referencia: str,
        sha256: str,
        tamano_bytes: int,
    ) -> IntentoDeEvidencia:
        """Crea el intento siguiente. El anterior sigue donde estaba.

        ⚠️ **Con un trámite de supresión abierto no se registra ninguno** ·
        corrección transversal. Una autorización firmada es el dato más sensible
        del sistema —lleva la identidad de un tercero, el representante legal— y
        aportarla es tratamiento nuevo del que `EQ-022` suspende.

        La ruta ya lo rechaza antes de leer el archivo; esto es la garantía que
        no depende del borde: aquí está el cerrojo, y sin él la reserva y la fila
        podrían cruzarse con una supresión que se abre en medio.
        """
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona_activa(cur, sujeto_google)
            # Cargar es un acto como otorgar: exige la versión requerida. Una
            # autorización firmada sobre un documento desplazado no cubre el que
            # hoy se pide, aunque aquel siga temporalmente abierto (hito A2).
            exigir_version_requerida(cur, version, Alcance.REPRESENTANTE.value)
            cur.execute(
                """
                SELECT coalesce(max(intento), 0) + 1
                  FROM representante_evidencia
                 WHERE sujeto_google = %s
                """,
                (sujeto_google,),
            )
            siguiente = cur.fetchone()[0]
            # El tipo valida antes del `INSERT`: referencia navegable, huella mal
            # formada o tamaño fuera del límite de `EQ-021` no llegan a la tabla.
            intento = IntentoDeEvidencia(
                sujeto_google=sujeto_google,
                intento=siguiente,
                version=version,
                referencia=referencia,
                sha256=sha256,
                tamano_bytes=tamano_bytes,
            )
            cur.execute(
                """
                INSERT INTO representante_evidencia
                    (sujeto_google, intento, version, referencia, sha256,
                     tipo_mime, tamano_bytes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, recibido_en
                """,
                (
                    intento.sujeto_google,
                    intento.intento,
                    intento.version,
                    intento.referencia,
                    intento.sha256,
                    intento.tipo_mime,
                    intento.tamano_bytes,
                ),
            )
            identificador, recibido = cur.fetchone()
            return replace(intento, recibido_en=recibido, secuencia=identificador)

    def revisar(
        self,
        evidencia: int,
        revisor: str,
        resultado: ResultadoDeRevision,
        motivo: str = "",
    ) -> RevisionDeEvidencia:
        """Aprueba o rechaza un intento, conservando quién y cuándo."""
        provisional = RevisionDeEvidencia(
            resultado=resultado,
            revisada_por=revisor,
            revisada_en=datetime.now(UTC),
            motivo=motivo,
        )
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, provisional.revisada_por)
            cur.execute(
                "SELECT 1 FROM representante_evidencia WHERE id = %s FOR UPDATE",
                (evidencia,),
            )
            if cur.fetchone() is None:
                raise ReferenciaDesconocida("esa evidencia no existe")
            exigir_transicion_representante(
                self._estado_del_intento(cur, evidencia),
                _ESTADO_TRAS_REVISION[provisional.resultado],
            )
            cur.execute(
                """
                INSERT INTO representante_revision
                    (evidencia, resultado, revisada_por, motivo)
                VALUES (%s, %s, %s, %s)
                RETURNING id, revisada_en
                """,
                (
                    evidencia,
                    provisional.resultado.value,
                    provisional.revisada_por,
                    provisional.motivo or None,
                ),
            )
            identificador, momento = cur.fetchone()
            return replace(provisional, revisada_en=momento, secuencia=identificador)

    def intentos(self, sujeto_google: str) -> tuple[IntentoDeEvidencia, ...]:
        """Todos, del primero al último, cada uno con su última revisión.

        `LATERAL` con el mismo desempate que el resto de la frontera —fecha y
        después identidad monótona— para que dos revisiones del mismo instante no
        cambien de orden entre dos consultas.
        """
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT e.id, e.intento, e.version, e.referencia, e.sha256, e.tamano_bytes,
                       e.tipo_mime, e.recibido_en,
                       r.id, r.resultado, r.revisada_por, r.revisada_en, r.motivo
                  FROM representante_evidencia e
                  LEFT JOIN LATERAL (
                       SELECT id, resultado, revisada_por, revisada_en, motivo
                         FROM representante_revision
                        WHERE evidencia = e.id
                        ORDER BY revisada_en DESC, id DESC
                        LIMIT 1
                  ) r ON true
                 WHERE e.sujeto_google = %s
                 ORDER BY e.intento ASC
                """,
                (sujeto_google,),
            )
            return tuple(self._intento_desde_fila(sujeto_google, fila) for fila in cur.fetchall())

    # ── C2A · las tres lecturas autorizadas ──────────────────────────────

    def cola(
        self,
        *,
        actor: str,
        filtro: FiltroDeEvidencias = FiltroDeEvidencias.PENDIENTE,
        limite: int = 20,
        cursor: PosicionDeCursor | None = None,
    ) -> PaginaDeEvidencias:
        """Un tramo de la cola de revisión. Rol primero, evidencias después.

        Se piden `limite + 1` filas y se devuelven `limite`. La de más no se
        enseña: sirve **sólo** para saber si hay continuación, y así el cursor
        siguiente es `None` exactamente cuando la página es la última. La
        alternativa —un `count(*)` aparte— cuenta una cola que puede haber
        cambiado entre las dos consultas y produce un «hay más» que miente.
        """
        with self._lectura_autorizada(actor) as cur:
            cur.execute(
                _SQL_COLA.format(filtro=_FILTRO_SQL[FiltroDeEvidencias(filtro)]),
                {
                    "desde_fecha": cursor.recibido_en if cursor else None,
                    "desde_id": cursor.evidencia if cursor else None,
                    "limite": limite + 1,
                },
            )
            filas = cur.fetchall()
        hay_mas = len(filas) > limite
        evidencias = tuple(self._revisable_desde_fila(fila) for fila in filas[:limite])
        siguiente = evidencias[-1].posicion.codificar() if hay_mas and evidencias else None
        return PaginaDeEvidencias(evidencias=evidencias, cursor_siguiente=siguiente)

    def detalle(self, evidencia: int, *, actor: str) -> EvidenciaRevisable:
        """Una evidencia por identificador, sin su referencia privada.

        ⚠️ **`exigir_investigador_administrador()` va antes del `SELECT`, y el
        orden importa más que en `revisar()`.** Allí lo protegido era la
        escritura; aquí lo protegido es **la existencia misma**: consultar
        primero y autorizar después habría dejado que un usuario sin rol
        distinguiera un identificador vivo de uno muerto por el código de
        respuesta, y recorrer enteros es barato.
        """
        with self._lectura_autorizada(actor) as cur:
            cur.execute(_SQL_DETALLE, (evidencia,))
            fila = cur.fetchone()
        if fila is None:
            raise ReferenciaDesconocida("esa evidencia no existe")
        # La columna de más va al final y se separa aquí: el constructor de la
        # proyección sigue recibiendo exactamente las doce de la cola, así que
        # las dos consultas no pueden desalinearse sin que el desempaquetado
        # falle en la primera petición.
        motivo = fila[10]
        comunes = (*fila[:10], *fila[11:])
        return replace(
            self._revisable_desde_fila(tuple(comunes)), motivo=(motivo or "").strip()
        )

    def referencia_del_documento(self, evidencia: int, *, actor: str) -> str:
        """La referencia opaca del archivo privado. Mismo orden, mismo lock.

        Devuelve una cadena y no un tipo con más campos porque quien la recibe
        sólo tiene una cosa que hacer con ella: dársela al almacenamiento
        privado. Cuanto menos viaje con ella, menos hay que acordarse de no
        publicar.
        """
        with self._lectura_autorizada(actor) as cur:
            cur.execute(_SQL_REFERENCIA, (evidencia,))
            fila = cur.fetchone()
        if fila is None:
            raise ReferenciaDesconocida("esa evidencia no existe")
        return fila[0]

    @contextmanager
    def _lectura_autorizada(self, actor: str) -> Iterator[Any]:
        """Un cursor dentro de una transacción con el rol ya exigido y retenido.

        **Por qué una lectura necesita transacción explícita.**
        `exigir_investigador_administrador()` lee `rol_asignacion` con `FOR
        SHARE`, y un lock sólo dura lo que dure la transacción que lo tomó. Sin
        transacción explícita, la comprobación y la consulta protegida podrían
        caer en dos, y entre ellas cabría una revocación confirmada: la respuesta
        saldría autorizada por un permiso que ya no existía al construirla.

        Con la transacción abierta, mientras esta consulta vive, ninguna
        revocación de **esa** asignación puede confirmarse — espera o cae por
        `lock_timeout`. Es la misma garantía que `revisar()` ya daba para
        escribir, y la que el encargo de C2A pide comprobar contra una revocación
        concurrente.

        No se reutiliza `_escritura()` aunque el cuerpo coincida: su nombre
        promete una escritura, y una lectura que se anuncie como escritura es una
        pista falsa para quien audite qué toca la base. La duplicación son dos
        líneas; la confusión duraría lo que dure el archivo.
        """
        with self._conexion() as cnx, cnx.transaction(), cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            yield cur

    def _revisable_desde_fila(self, fila: tuple) -> EvidenciaRevisable:
        """Una fila de `_SQL_PROYECCION` como tipo del dominio.

        Doce columnas y ninguna es la referencia. Si alguien añadiera una a la
        proyección, este desempaquetado fallaría en la primera consulta — que es
        mejor sitio para enterarse que una respuesta JSON en producción.
        """
        (
            identificador,
            sujeto,
            numero,
            version,
            sha256,
            tamano,
            tipo,
            recibido,
            resultado,
            revisada_en,
            estudiante_nombre,
            clases,
        ) = fila
        return EvidenciaRevisable(
            evidencia=identificador,
            sujeto_google=sujeto,
            intento=numero,
            version=version,
            sha256=sha256,
            tamano_bytes=tamano,
            recibido_en=recibido,
            tipo_mime=tipo,
            resultado=None if resultado is None else ResultadoDeRevision(resultado),
            revisada_en=revisada_en,
            estudiante_nombre=estudiante_nombre,
            clases=tuple(clases or ()),
        )

    def _intento_desde_fila(self, sujeto_google: str, fila: tuple) -> IntentoDeEvidencia:
        (
            identificador,
            numero,
            version,
            referencia,
            sha256,
            tamano,
            tipo,
            recibido,
            revision_id,
            resultado,
            revisada_por,
            revisada_en,
            motivo,
        ) = fila
        revision = (
            None
            if revision_id is None
            else RevisionDeEvidencia(
                resultado=ResultadoDeRevision(resultado),
                revisada_por=revisada_por,
                revisada_en=revisada_en,
                motivo=motivo or "",
                secuencia=revision_id,
            )
        )
        return IntentoDeEvidencia(
            sujeto_google=sujeto_google,
            intento=numero,
            version=version,
            referencia=referencia,
            sha256=sha256,
            tamano_bytes=tamano,
            tipo_mime=tipo,
            recibido_en=recibido,
            revision=revision,
            secuencia=identificador,
        )

    def _estado_del_intento(self, cur: Any, evidencia: int) -> EstadoRepresentante:
        cur.execute(
            """
            SELECT resultado FROM representante_revision
             WHERE evidencia = %s
             ORDER BY revisada_en DESC, id DESC
             LIMIT 1
            """,
            (evidencia,),
        )
        fila = cur.fetchone()
        if fila is None:
            return EstadoRepresentante.DOCUMENTO_RECIBIDO
        return _ESTADO_TRAS_REVISION[ResultadoDeRevision(fila[0])]
