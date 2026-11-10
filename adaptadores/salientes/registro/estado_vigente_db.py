"""
estado_vigente_db.py — La consulta determinista de las tres dimensiones
=========================================================================

`PuertoEstadoVigente` contra la migración 11. Es la lectura que sostiene el
cálculo de acceso de `EQ-016`: perfil, consentimiento, asentimiento y evidencia
del representante, resueltos **en una sola consulta** para que las cuatro cosas
describan el mismo instante.

Por qué una consulta y no cuatro
-----------------------------------------
Cuatro consultas sucesivas pueden ver cuatro estados distintos: entre la segunda
y la tercera alguien revoca, y el resultado combina un consentimiento vigente con
un asentimiento posterior a la revocación. Nadie escribió nunca ese estado y aun
así se presentaría como el actual. Con una sola sentencia y sus CTE, PostgreSQL
resuelve todo sobre el mismo instante.

Qué significa «determinista» aquí
------------------------------------------
Dos cosas, y la segunda la añadió la revisión:

1. **entre eventos** · dos actos del mismo sujeto con `momento` idéntico —cosa
   que ocurre cuando dos escrituras caen en la misma transacción o en el mismo
   microsegundo— producen siempre el mismo estado. `ORDER BY momento DESC` no
   basta: PostgreSQL puede devolverlos en cualquier orden, así que todas las
   subconsultas desempatan con la identidad monótona de la fila.
2. **entre versiones** · la versión REQUERIDA de cada alcance se elige con la
   regla de `SQL_VERSION_REQUERIDA` —vigente ahora, y `vigente_desde DESC,
   codigo DESC` como desempate—, que vive en `base_postgres.py` y la comparte con
   `AdaptadorVersionesDeConsentimientoPostgres`. Dos redacciones de esa regla
   acabarían eligiendo versiones distintas el día que se publiquen dos el mismo
   día.

Qué cambió tras la revisión
------------------------------------
La consulta devolvía el último acto y nada más, de modo que un consentimiento
otorgado sobre una versión ya retirada se presentaba como vigente. Ahora trae
además:

- **la versión requerida** de cada alcance, para que el dominio pueda distinguir
  «aceptó» de «aceptó lo que hoy se pide»;
- **la categoría de edad** con la que se emitió el último consentimiento, que es
  como se detecta que alguien cumplió 18 (`EQ-021`);
- **la versión del último asentimiento**;
- el último intento de evidencia **de la versión requerida del representante**, y
  no el último a secas: una autorización firmada sobre un texto anterior no
  autoriza el que rige hoy.

Lo que esta consulta NO decide
---------------------------------------
No calcula el acceso. Devuelve los hechos y `dominio/modelo/acceso.py` los
interpreta: el día que una regla cambie, cambia en el dominio y no en un `SELECT`.
Tampoco deriva el estado del representante con SQL propio — construye el último
intento y llama a `estado_representante()`, para que memoria y base no puedan
discrepar en la derivación.

`eliminacion_solicitada` ya tiene fuente (hito B3)
--------------------------------------------------------
Sale de `solicitud_supresion` (migración 12) y entra en **esta** consulta, no en
otra: `EQ-022` bloquea el acceso durante el trámite, y leerlo aparte permitiría
habilitar a quien acaba de solicitarlo. `to_regclass` la hace opcional para que
un despliegue sin la migración 12 siga pudiendo leer el estado; allí es `false`,
que es lo cierto — no hay trámite porque no hay dónde registrarlo.


"""

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

#: Una sentencia, un instante. Cada subconsulta que elige «el último» desempata
#: con el identificador monótono además de con la fecha.
#:
#: ⚠️ **Corregido en el hito A2.** Esta consulta llevaba tres CTE con la regla de
#: la versión requerida **copiada**, y `base_postgres.py` llevaba una cuarta
#: copia. Cuatro redacciones de la misma regla son cuatro reglas en cuanto
#: alguien corrige una, y eso es exactamente lo que la revisión encontró: el
#: adaptador y el cálculo de acceso podían hablar de versiones distintas. Ahora
#: las tres llaman a `didaxia_version_requerida()`, que vive en la migración 11 y
#: es la única definición.
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
    -- `EQ-022` · durante el tramite no se permite usar el tutor. Entra en ESTA
    -- consulta y no en otra para que el estado siga describiendo un solo
    -- instante: leerlo aparte permitiria habilitar a quien acaba de solicitar.
    --
    -- `to_regclass` la vuelve opcional: un despliegue sin la migracion 12 no
    -- tiene la tabla, y el estado tiene que seguir leyendose. Sin ella, `false`,
    -- que es lo cierto — no hay tramite porque no hay donde registrarlo.
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

#: Cuántas columnas describen el perfil al principio de la fila.
_COLUMNAS_DE_PERFIL = 8
#: Cuántas describen el bloque intermedio: límite, tres versiones requeridas,
#: estado/versión/categoría/id del consentimiento y estado/versión del
#: asentimiento.
_COLUMNAS_DE_ESTADO = 10


class AdaptadorEstadoVigentePostgres(RepositorioPostgres):
    """`PuertoEstadoVigente`. Devuelve hechos; el dominio los interpreta."""

    def estado_vigente(self, sujeto_google: str) -> EstadoVigente | None:
        """El estado de las tres dimensiones, o `None` si no hay persona.

        `None` significa **sólo** que no existe la fila de identidad. Un almacén
        caído levanta `AlmacenNoDisponible` y un esquema sin migrar levanta
        `AlmacenNoConfigurado`: la sesión 3 puede así mostrar mantenimiento en
        vez de mandar a alguien a repetir un onboarding que ya hizo.
        """
        with self._conexion() as cnx, cnx.cursor() as cur:
            return self.desde_cursor(cur, sujeto_google)

    def desde_cursor(self, cur, sujeto_google: str) -> EstadoVigente | None:
        """La misma política dentro de una lectura auditada ya abierta."""
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
        # Las dos últimas columnas son los estados de supresión y rectificación;
        # el resto del bloque final describe el intento de evidencia.
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
            # `EQ-022`, hito B3 · durante el trámite no se permite usar el tutor.
            eliminacion_solicitada=bool(eliminacion_solicitada),
            tutoria_academica_sin_investigacion=bool(tutoria_academica),
        )

    def _asentimiento(self, estado: str | None, *, requerido: bool) -> EstadoAsentimiento:
        """Sin eventos, `PENDIENTE` para un menor y `NO_REQUERIDO` para el resto.

        Y `NO_REQUERIDO` para un adulto **aunque tenga eventos**: quien dio su
        asentimiento a los 17 conserva la fila, pero a los 18 esa dimensión ya no
        le corresponde y no puede seguir bloqueándole. Es la misma precedencia que
        `HistorialDeAsentimiento.estado`, y una prueba de integración comprueba
        que las dos derivaciones coincidan.
        """
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


#: Se importa para que quede constancia de que los tres alcances de la consulta
#: son exactamente los del enumerado del dominio; una prueba lo comprueba contra
#: el SQL en vez de contra esta línea.
_ALCANCES_DE_LA_CONSULTA = tuple(a.value for a in Alcance)
