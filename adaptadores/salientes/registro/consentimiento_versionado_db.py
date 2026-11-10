from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from adaptadores.salientes.registro.base_postgres import (
    RepositorioPostgres,
    exigir_categoria_de_edad,
    exigir_persona,
    exigir_sin_supresion,
    exigir_version_de_la_concesion,
    exigir_version_requerida,
    insertar_acto,
    ultimo_acto,
    version_de_la_concesion_de,
    version_requerida_de,
)
from dominio.modelo.consentimiento import (
    Alcance,
    EstadoConsentimiento,
    EventoConsentimiento,
    Finalidad,
    HistorialDeConsentimiento,
    VersionDeConsentimiento,
    exigir_transicion,
)
from dominio.modelo.identidad import CategoriaDeEdad
from dominio.modelo.instantanea_consentimiento import (
    InstantaneaDeVersion,
    PublicacionDeVersion,
)
from dominio.puertos.almacen import EscrituraRechazada
from dominio.puertos.instantaneas import ResultadoDePublicacion


class AdaptadorVersionesDeConsentimientoPostgres(RepositorioPostgres):

    def registrar_version(self, version: VersionDeConsentimiento) -> None:
        with self._escritura() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM consentimiento_version WHERE codigo = %s",
                (version.codigo,),
            )
            if cur.fetchone() is not None:
                raise EscrituraRechazada(
                    "esa versión ya está publicada; una corrección es una versión nueva"
                )
            cur.execute(
                """
                INSERT INTO consentimiento_version
                    (codigo, alcance, huella_contenido, vigente_desde, vigente_hasta)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    version.codigo,
                    version.alcance.value,
                    version.huella_contenido,
                    version.vigente_desde,
                    version.vigente_hasta,
                ),
            )
            cur.executemany(
                """
                INSERT INTO consentimiento_version_finalidad (version, finalidad)
                VALUES (%s, %s)
                """,
                [(version.codigo, f.value) for f in sorted(version.finalidades)],
            )

    def consultar_version(self, codigo: str) -> VersionDeConsentimiento | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT codigo, alcance, huella_contenido, vigente_desde, vigente_hasta
                  FROM consentimiento_version
                 WHERE codigo = %s
                """,
                (codigo,),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            return self._con_finalidades(cur, fila)

    def versiones(self, alcance: Alcance | None = None) -> tuple[VersionDeConsentimiento, ...]:
        condicion = "WHERE alcance = %s" if alcance is not None else ""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"""
                SELECT codigo, alcance, huella_contenido, vigente_desde, vigente_hasta
                  FROM consentimiento_version
                  {condicion}
                 ORDER BY vigente_desde DESC, codigo DESC
                """,
                (alcance.value,) if alcance is not None else (),
            )
            filas = list(cur.fetchall())
            return tuple(self._con_finalidades(cur, fila) for fila in filas)

    def version_requerida(self, alcance: Alcance) -> VersionDeConsentimiento | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            codigo = version_requerida_de(cur, Alcance(alcance).value)
            if codigo is None:
                return None
            cur.execute(
                """
                SELECT codigo, alcance, huella_contenido, vigente_desde, vigente_hasta
                  FROM consentimiento_version WHERE codigo = %s
                """,
                (codigo,),
            )
            return self._con_finalidades(cur, cur.fetchone())

    def publicar(self, publicacion: PublicacionDeVersion) -> ResultadoDePublicacion:
        (resultado,) = self.publicar_lote((publicacion,))
        return resultado

    def publicar_lote(
        self, publicaciones: Sequence[PublicacionDeVersion]
    ) -> tuple[ResultadoDePublicacion, ...]:

        if not publicaciones:
            return ()
        with self._escritura() as cnx, cnx.cursor() as cur:
            return tuple(self._publicar_en(cur, p) for p in publicaciones)

    def _publicar_en(
        self, cur: Any, publicacion: PublicacionDeVersion
    ) -> ResultadoDePublicacion:

        instantanea = publicacion.instantanea
        cur.execute(
            """
            SELECT alcance, huella_contenido
              FROM consentimiento_version
             WHERE codigo = %s
               FOR UPDATE
            """,
            (publicacion.codigo,),
        )
        fila = cur.fetchone()
        if fila is not None:
            return self._publicacion_repetida(cur, publicacion, fila)

        cur.execute(
            """
            INSERT INTO consentimiento_version
                (codigo, alcance, huella_contenido, vigente_desde, vigente_hasta)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                publicacion.codigo,
                publicacion.alcance.value,
                publicacion.huella,
                publicacion.vigente_desde,
                publicacion.vigente_hasta,
            ),
        )
        cur.executemany(
            """
            INSERT INTO consentimiento_version_finalidad (version, finalidad)
            VALUES (%s, %s)
            """,
            [(publicacion.codigo, f.value) for f in sorted(publicacion.finalidades)],
        )
        cur.execute(
            """
            INSERT INTO consentimiento_version_texto (version, cuerpo, medio)
            VALUES (%s, %s, %s)
            """,
            (publicacion.codigo, instantanea.cuerpo, instantanea.medio),
        )
        return ResultadoDePublicacion(
            codigo=publicacion.codigo,
            escrita=True,
            motivo="versión publicada con su documento",
        )

    def _publicacion_repetida(
        self, cur: Any, publicacion: PublicacionDeVersion, fila: tuple
    ) -> ResultadoDePublicacion:

        alcance_guardado, huella_guardada = fila
        if alcance_guardado != publicacion.alcance.value:
            raise EscrituraRechazada(
                f"«{publicacion.codigo}» ya está publicado con alcance "
                f"«{alcance_guardado}»: un código no cambia de alcance"
            )
        if huella_guardada != publicacion.huella:
            raise EscrituraRechazada(
                f"«{publicacion.codigo}» ya está publicado con OTRA huella; no se "
                "sobrescribe: su huella es la prueba de qué texto leyó quien lo "
                "aceptó. Una corrección es una versión nueva"
            )
        cur.execute(
            "SELECT cuerpo FROM consentimiento_version_texto WHERE version = %s",
            (publicacion.codigo,),
        )
        guardado = cur.fetchone()
        if guardado is None:

            raise EscrituraRechazada(
                f"«{publicacion.codigo}» existe sin instantánea: es anterior a "
                "esta tabla y no se le añade una a posteriori. Publique una "
                "versión nueva"
            )
        if guardado[0] != publicacion.instantanea.cuerpo:

            raise EscrituraRechazada(
                f"«{publicacion.codigo}» tiene la misma huella y un cuerpo "
                "distinto: no se continúa"
            )
        return ResultadoDePublicacion(
            codigo=publicacion.codigo,
            escrita=False,
            motivo="ya estaba publicada, idéntica: no se escribió nada",
        )

    def instantanea_de(self, codigo: str) -> InstantaneaDeVersion | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT v.codigo, v.alcance, t.cuerpo, t.medio
                  FROM consentimiento_version_texto t
                  JOIN consentimiento_version v ON v.codigo = t.version
                 WHERE t.version = %s
                """,
                (codigo,),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            return InstantaneaDeVersion(
                codigo=fila[0], alcance=Alcance(fila[1]), cuerpo=fila[2], medio=fila[3]
            )

    def _con_finalidades(self, cur: Any, fila: tuple) -> VersionDeConsentimiento:
        codigo, alcance, huella, desde, hasta = fila
        cur.execute(
            "SELECT finalidad FROM consentimiento_version_finalidad WHERE version = %s",
            (codigo,),
        )
        finalidades = frozenset(Finalidad(f[0]) for f in cur.fetchall())
        return VersionDeConsentimiento(
            codigo=codigo,
            alcance=Alcance(alcance),
            finalidades=finalidades,
            huella_contenido=huella,
            vigente_desde=desde,
            vigente_hasta=hasta,
        )

class AdaptadorEventosDeConsentimientoPostgres(RepositorioPostgres):

    def registrar(
        self,
        sujeto_google: str,
        version: str,
        estado: EstadoConsentimiento,
        comprobante: str,
    ) -> EventoConsentimiento:

        provisional = EventoConsentimiento(
            sujeto_google=sujeto_google,
            version=version,
            estado=estado,
            comprobante=comprobante,
            momento=datetime.now(UTC),
        )
        with self._escritura() as cnx, cnx.cursor() as cur:

            edad = exigir_persona(cur, provisional.sujeto_google)
            if provisional.estado is not EstadoConsentimiento.REVOCADO:
                exigir_sin_supresion(cur, provisional.sujeto_google)

            categoria = exigir_categoria_de_edad(edad)

            if provisional.estado is EstadoConsentimiento.REVOCADO:
                exigir_version_de_la_concesion(
                    cur, "consentimiento_evento", provisional.sujeto_google, provisional.version
                )
            else:
                exigir_version_requerida(cur, provisional.version, Alcance.TITULAR.value)
            actual, version_actual, categoria_actual = self._vigente(
                cur, provisional.sujeto_google
            )
            exigir_transicion(
                actual,
                provisional.estado,
                cambia_version=version_actual != provisional.version,

                cambia_categoria=(
                    categoria_actual is not None and categoria_actual is not categoria
                ),
            )
            identificador, momento, categoria_guardada = insertar_acto(
                cur,
                "consentimiento_evento",
                sujeto=provisional.sujeto_google,
                version=provisional.version,
                estado=provisional.estado.value,
                comprobante=provisional.comprobante,
            )
            return replace(
                provisional,
                momento=momento,
                secuencia=identificador,
                categoria_edad=CategoriaDeEdad(categoria_guardada),
            )

    def version_de_la_concesion(self, sujeto_google: str) -> str | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            return version_de_la_concesion_de(cur, "consentimiento_evento", sujeto_google)

    def historial(self, sujeto_google: str) -> HistorialDeConsentimiento:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT id, version, estado, comprobante, momento, categoria_edad
                  FROM consentimiento_evento
                 WHERE sujeto_google = %s
                 ORDER BY momento ASC, id ASC
                """,
                (sujeto_google,),
            )
            eventos = tuple(
                EventoConsentimiento(
                    sujeto_google=sujeto_google,
                    version=version,
                    estado=EstadoConsentimiento(estado),
                    comprobante=comprobante,
                    momento=momento,
                    secuencia=identificador,
                    categoria_edad=CategoriaDeEdad(categoria),
                )
                for identificador, version, estado, comprobante, momento, categoria
                in cur.fetchall()
            )
        return HistorialDeConsentimiento(sujeto_google=sujeto_google, eventos=eventos)

    def _vigente(
        self, cur: Any, sujeto_google: str
    ) -> tuple[EstadoConsentimiento, str | None, CategoriaDeEdad | None]:

        fila = ultimo_acto(
            cur,
            "consentimiento_evento",
            sujeto_google,
            ("estado", "version", "categoria_edad"),
        )
        if fila is None:
            return EstadoConsentimiento.PENDIENTE, None, None
        return EstadoConsentimiento(fila[0]), fila[1], CategoriaDeEdad(fila[2])
