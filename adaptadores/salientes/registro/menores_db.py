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

if TYPE_CHECKING:
    from collections.abc import Iterator

_ESTADO_TRAS_REVISION = {
    ResultadoDeRevision.APROBADA: EstadoRepresentante.APROBADO,
    ResultadoDeRevision.RECHAZADA: EstadoRepresentante.RECHAZADO,
}


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


_FILTRO_SQL = {
    FiltroDeEvidencias.PENDIENTE: "r.resultado IS NULL",
    FiltroDeEvidencias.APROBADA: "r.resultado = 'aprobada'",
    FiltroDeEvidencias.RECHAZADA: "r.resultado = 'rechazada'",
    FiltroDeEvidencias.TODOS: "true",
}


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


_SQL_DETALLE = _SQL_PROYECCION.replace(
    "SELECT resultado, revisada_en\n", "SELECT resultado, revisada_en, motivo\n"
).replace(
    "r.resultado, r.revisada_en,\n", "r.resultado, r.revisada_en, r.motivo,\n"
) + """
 WHERE e.id = %s
"""


_SQL_REFERENCIA = "SELECT referencia FROM representante_evidencia WHERE id = %s"


class AdaptadorAsentimientoPostgres(RepositorioPostgres):

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

            edad = self._persona_para(cur, provisional)

            if categoria_de_edad(edad) is not CategoriaDeEdad.MENOR:
                raise EscrituraRechazada(
                    "el asentimiento sólo corresponde a una persona menor de edad"
                )

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
        edad = exigir_persona(cur, provisional.sujeto_google)
        if provisional.estado is not EstadoAsentimiento.REVOCADO:
            exigir_sin_supresion(cur, provisional.sujeto_google)
        return edad

    def _vigente(self, cur: Any, sujeto_google: str) -> EstadoAsentimiento:
        fila = ultimo_acto(cur, "asentimiento_evento", sujeto_google, ("estado",))
        return EstadoAsentimiento(fila[0]) if fila else EstadoAsentimiento.PENDIENTE

class AdaptadorEvidenciaDelRepresentantePostgres(RepositorioPostgres):

    def registrar_intento(
        self,
        sujeto_google: str,
        version: str,
        referencia: str,
        sha256: str,
        tamano_bytes: int,
    ) -> IntentoDeEvidencia:

        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona_activa(cur, sujeto_google)

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

    def cola(
        self,
        *,
        actor: str,
        filtro: FiltroDeEvidencias = FiltroDeEvidencias.PENDIENTE,
        limite: int = 20,
        cursor: PosicionDeCursor | None = None,
    ) -> PaginaDeEvidencias:

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
        with self._lectura_autorizada(actor) as cur:
            cur.execute(_SQL_DETALLE, (evidencia,))
            fila = cur.fetchone()
        if fila is None:
            raise ReferenciaDesconocida("esa evidencia no existe")

        motivo = fila[10]
        comunes = (*fila[:10], *fila[11:])
        return replace(
            self._revisable_desde_fila(tuple(comunes)), motivo=(motivo or "").strip()
        )

    def referencia_del_documento(self, evidencia: int, *, actor: str) -> str:
        with self._lectura_autorizada(actor) as cur:
            cur.execute(_SQL_REFERENCIA, (evidencia,))
            fila = cur.fetchone()
        if fila is None:
            raise ReferenciaDesconocida("esa evidencia no existe")
        return fila[0]

    @contextmanager
    def _lectura_autorizada(self, actor: str) -> Iterator[Any]:
        with self._conexion() as cnx, cnx.transaction(), cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            yield cur

    def _revisable_desde_fila(self, fila: tuple) -> EvidenciaRevisable:
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
