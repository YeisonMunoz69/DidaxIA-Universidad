from __future__ import annotations

from datetime import UTC, datetime

from adaptadores.salientes.registro.base_postgres import RepositorioPostgres
from adaptadores.salientes.registro.identidad_db import perfil_desde_fila
from dominio.modelo.acceso import EstadoVigente, VersionesRequeridas
from dominio.modelo.consentimiento import Alcance, EstadoConsentimiento
from dominio.modelo.identidad import CategoriaDeEdad
from dominio.modelo.menores import (
    EstadoAsentimiento,
    IntentoDeEvidencia,
    ResultadoDeRevision,
    RevisionDeEvidencia,
    estado_representante,
)


_CONSULTA = """
WITH p AS (
    SELECT * FROM persona WHERE sujeto_google = %(sujeto)s
),
requerida AS (
    SELECT didaxia_version_requerida('titular')       AS titular,
           didaxia_version_requerida('asentimiento')  AS asentimiento,
           didaxia_version_requerida('representante') AS representante
),
ultimo_consentimiento AS (
    SELECT id, estado, version, categoria_edad FROM consentimiento_evento
     WHERE sujeto_google = %(sujeto)s
     ORDER BY momento DESC, id DESC LIMIT 1
),
ultimo_asentimiento AS (
    SELECT estado, version FROM asentimiento_evento
     WHERE sujeto_google = %(sujeto)s
     ORDER BY momento DESC, id DESC LIMIT 1
),
ultimo_intento AS (
    SELECT id, intento, version, referencia, sha256, tamano_bytes, tipo_mime, recibido_en
      FROM representante_evidencia
     WHERE sujeto_google = %(sujeto)s
       AND version = (SELECT representante FROM requerida)
     ORDER BY intento DESC, id DESC LIMIT 1
),
ultima_revision AS (
    SELECT id, resultado, revisada_por, revisada_en, motivo
      FROM representante_revision
     WHERE evidencia = (SELECT id FROM ultimo_intento)
     ORDER BY revisada_en DESC, id DESC LIMIT 1
),
supresion_abierta AS (
    --
    SELECT EXISTS (
        SELECT 1 FROM solicitud_supresion
         WHERE sujeto_google = %(sujeto)s AND estado = 'solicitada'
    ) AS hay
     WHERE to_regclass('solicitud_supresion') IS NOT NULL
),
rectificacion_pendiente AS (
    SELECT EXISTS (
        SELECT 1
          FROM rectificacion_edad r
         WHERE r.sujeto_google = %(sujeto)s
           AND r.reconsentimiento_necesario
           AND EXISTS (
               SELECT 1 FROM rectificacion_edad_transicion t
                WHERE t.rectificacion = r.id
                  AND t.estado = 'reconsentimiento_pendiente'
           )
           AND NOT EXISTS (
               SELECT 1 FROM rectificacion_edad_transicion t
                WHERE t.rectificacion = r.id
                  AND t.estado IN ('reconsentida', 'sustituida')
           )
    ) AS hay
)
SELECT p.sujeto_google, p.correo, p.nombre, p.edad_declarada, p.facultad, p.programa, p.semestre,
       EXISTS (SELECT 1 FROM clase_matricula m WHERE m.identificador = p.sujeto_google),
       p.representante_limite,
       (SELECT titular       FROM requerida),
       (SELECT asentimiento  FROM requerida),
       (SELECT representante FROM requerida),
       (SELECT estado         FROM ultimo_consentimiento),
       (SELECT version        FROM ultimo_consentimiento),
       (SELECT categoria_edad FROM ultimo_consentimiento),
       (SELECT id             FROM ultimo_consentimiento),
       (SELECT estado  FROM ultimo_asentimiento),
       (SELECT version FROM ultimo_asentimiento),
       (SELECT id FROM ultimo_intento),
       (SELECT intento FROM ultimo_intento),
       (SELECT version FROM ultimo_intento),
       (SELECT referencia FROM ultimo_intento),
       (SELECT sha256 FROM ultimo_intento),
       (SELECT tamano_bytes FROM ultimo_intento),
       (SELECT tipo_mime FROM ultimo_intento),
       (SELECT recibido_en FROM ultimo_intento),
       (SELECT id FROM ultima_revision),
       (SELECT resultado FROM ultima_revision),
       (SELECT revisada_por FROM ultima_revision),
       (SELECT revisada_en FROM ultima_revision),
       (SELECT motivo FROM ultima_revision),
       coalesce((SELECT hay FROM supresion_abierta), false),
       coalesce((SELECT hay FROM rectificacion_pendiente), false)
  FROM p
"""


_COLUMNAS_DE_PERFIL = 8


_COLUMNAS_DE_ESTADO = 10


class AdaptadorEstadoVigentePostgres(RepositorioPostgres):

    def estado_vigente(self, sujeto_google: str) -> EstadoVigente | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            return self.desde_cursor(cur, sujeto_google)

    def desde_cursor(self, cur, sujeto_google: str) -> EstadoVigente | None:
        cur.execute(_CONSULTA, {"sujeto": sujeto_google})
        fila = cur.fetchone()
        if fila is None:
            return None
        return self._componer(fila)

    def _componer(self, fila: tuple) -> EstadoVigente:
        perfil = perfil_desde_fila(fila[:_COLUMNAS_DE_PERFIL])
        (
            limite,
            requerida_titular,
            requerida_asentimiento,
            requerida_representante,
            estado_consentimiento,
            version_consentimiento,
            categoria_consentimiento,
            evento_consentimiento,
            estado_asentimiento,
            version_asentimiento,
        ) = fila[_COLUMNAS_DE_PERFIL : _COLUMNAS_DE_PERFIL + _COLUMNAS_DE_ESTADO]

        *columnas_del_intento, eliminacion_solicitada, tutoria_academica = fila[
            _COLUMNAS_DE_PERFIL + _COLUMNAS_DE_ESTADO :
        ]
        intento = self._ultimo_intento(perfil.sujeto_google, tuple(columnas_del_intento))
        return EstadoVigente(
            sujeto_google=perfil.sujeto_google,
            perfil=perfil,
            consentimiento=(
                EstadoConsentimiento(estado_consentimiento)
                if estado_consentimiento
                else EstadoConsentimiento.PENDIENTE
            ),
            version_consentimiento=version_consentimiento,
            evento_consentimiento=evento_consentimiento,
            categoria_edad_consentimiento=(
                CategoriaDeEdad(categoria_consentimiento) if categoria_consentimiento else None
            ),
            asentimiento=self._asentimiento(estado_asentimiento, requerido=perfil.es_menor),
            version_asentimiento=version_asentimiento if perfil.es_menor else None,
            representante=estado_representante(
                () if intento is None else (intento,),
                requerido=perfil.es_menor,
                version_requerida=requerida_representante,
                limite=limite,
                ahora=datetime.now(UTC),
            ),
            motivo_representante=(
                intento.revision.motivo
                if intento is not None
                and intento.revision is not None
                and intento.revision.resultado is ResultadoDeRevision.RECHAZADA
                else ""
            ),
            requeridas=VersionesRequeridas(
                titular=requerida_titular,
                asentimiento=requerida_asentimiento,
                representante=requerida_representante,
            ),
            limite_representante=limite,

            eliminacion_solicitada=bool(eliminacion_solicitada),
            tutoria_academica_sin_investigacion=bool(tutoria_academica),
        )

    def _asentimiento(self, estado: str | None, *, requerido: bool) -> EstadoAsentimiento:
        if not requerido:
            return EstadoAsentimiento.NO_REQUERIDO
        if estado:
            return EstadoAsentimiento(estado)
        return EstadoAsentimiento.PENDIENTE

    def _ultimo_intento(self, sujeto_google: str, columnas: tuple) -> IntentoDeEvidencia | None:
        (
            evidencia_id,
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
        ) = columnas
        if evidencia_id is None:
            return None
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
            secuencia=evidencia_id,
        )

_ALCANCES_DE_LA_CONSULTA = tuple(a.value for a in Alcance)
