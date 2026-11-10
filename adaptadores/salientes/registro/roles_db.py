from __future__ import annotations

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import (
    exigir_actor_distinto,
    exigir_investigador_administrador,
)
from adaptadores.salientes.registro.base_postgres import RepositorioPostgres, exigir_persona
from dominio.modelo.oferta_academica import FACULTADES
from dominio.modelo.roles import AsignacionDeRol, Rol
from dominio.puertos.almacen import EscrituraRechazada


OPERACION_ASIGNAR = "rol.asignado"
OPERACION_REVOCAR = "rol.revocado"


PRESENTACION_PERSONAS_SQL = """
presentacion AS MATERIALIZED (
    SELECT p.sujeto_google, p.nombre, p.correo, p.facultad, p.programa, p.semestre,
           ARRAY(
               SELECT DISTINCT rol FROM (
                   SELECT r.rol
                     FROM rol_asignacion r
                    WHERE r.sujeto_google = p.sujeto_google AND r.revocado_en IS NULL
                   UNION ALL
                   SELECT 'docente' WHERE EXISTS (
                       SELECT 1 FROM clase c WHERE c.creador = p.sujeto_google
                   )
                   UNION ALL
                   SELECT 'estudiante' WHERE EXISTS (
                       SELECT 1 FROM clase_matricula m
                        WHERE m.identificador = p.sujeto_google
                   )
               ) funciones
              ORDER BY rol
           ) AS roles
      FROM persona p
)
"""


SUJETOS_PROFESIONALES_VIGENTES_SQL = """
SELECT sujeto_google
  FROM rol_asignacion
 WHERE revocado_en IS NULL
   AND rol IN ('docente', 'investigador_administrador')
"""


class AdaptadorRolesPostgres(RepositorioPostgres):

    def asignar(
        self, sujeto_google: str, rol: Rol, otorgado_por: str | None = None
    ) -> AsignacionDeRol:

        rol = Rol(rol)
        with self._escritura() as cnx, cnx.cursor() as cur:
            if otorgado_por is not None:
                exigir_actor_distinto(otorgado_por, sujeto_google)
            exigir_persona(cur, sujeto_google)
            if otorgado_por is not None:
                exigir_investigador_administrador(cur, otorgado_por)
            cur.execute(
                """
                SELECT 1 FROM rol_asignacion
                 WHERE sujeto_google = %s AND rol = %s AND revocado_en IS NULL
                """,
                (sujeto_google, rol.value),
            )
            if cur.fetchone() is not None:
                raise EscrituraRechazada("esa persona ya tiene ese rol vigente")
            cur.execute(
                """
                INSERT INTO rol_asignacion (sujeto_google, rol, otorgado_por)
                VALUES (%s, %s, %s)
                RETURNING id, otorgado_en
                """,
                (sujeto_google, rol.value, otorgado_por),
            )
            identificador, otorgado_en = cur.fetchone()
            if otorgado_por is not None:
                anotar(
                    cur,
                    OPERACION_ASIGNAR,
                    actor=otorgado_por,
                    sujeto_afectado=sujeto_google,

                    detalle={"rol": rol.value},
                )
        return AsignacionDeRol(
            sujeto_google=sujeto_google,
            rol=rol,
            otorgado_en=otorgado_en,
            otorgado_por=otorgado_por,
            secuencia=identificador,
        )

    def revocar(self, sujeto_google: str, rol: Rol, revocado_por: str) -> bool:
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_actor_distinto(revocado_por, sujeto_google)

            exigir_persona(cur, revocado_por)
            exigir_investigador_administrador(cur, revocado_por)
            cur.execute(
                """
                UPDATE rol_asignacion
                   SET revocado_en = now(), revocado_por = %s
                 WHERE sujeto_google = %s AND rol = %s AND revocado_en IS NULL
                """,
                (revocado_por, sujeto_google, Rol(rol).value),
            )
            if cur.rowcount == 0:
                return False
            anotar(
                cur,
                OPERACION_REVOCAR,
                actor=revocado_por,
                sujeto_afectado=sujeto_google,
                detalle={"rol": Rol(rol).value},
            )
            return True

    def roles_de(self, sujeto_google: str) -> frozenset[Rol]:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT rol FROM rol_asignacion
                 WHERE sujeto_google = %s AND revocado_en IS NULL
                """,
                (sujeto_google,),
            )
            return frozenset(Rol(fila[0]) for fila in cur.fetchall())

    def asignaciones(self, sujeto_google: str) -> tuple[AsignacionDeRol, ...]:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT id, rol, otorgado_por, otorgado_en, revocado_por, revocado_en
                  FROM rol_asignacion
                 WHERE sujeto_google = %s
                 ORDER BY otorgado_en ASC, id ASC
                """,
                (sujeto_google,),
            )
            return tuple(
                AsignacionDeRol(
                    sujeto_google=sujeto_google,
                    rol=Rol(rol),
                    otorgado_en=otorgado_en,
                    otorgado_por=otorgado_por,
                    revocado_por=revocado_por,
                    revocado_en=revocado_en,
                    secuencia=identificador,
                )
                for identificador, rol, otorgado_por, otorgado_en, revocado_por, revocado_en
                in cur.fetchall()
            )

    def directorio_institucional(
        self, investigador: str, filtro: str = "", pertenencia: str = "todas",
        clase: str = "",
    ) -> list[dict]:

        filtro = str(filtro or "").strip().lower()
        if pertenencia not in {"todas", "con_clase", "sin_clase", "solicitud_pendiente"}:
            raise ValueError("filtro de pertenencia no admitido")
        clase = str(clase or "").strip()
        with self._conexion() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, investigador)
            anotar(
                cur,
                "consultar_equipo_institucional",
                actor=investigador,
                detalle={"filtro": bool(filtro), "pertenencia": pertenencia,
                         "clase": bool(clase), "limite": 100},
            )
            cur.execute(
                """
                SELECT p.sujeto_google, p.correo, p.nombre, p.facultad,
                       BOOL_OR(p.foto_perfil_referencia IS NOT NULL),
                       COALESCE(array_agg(DISTINCT r.rol)
                           FILTER (WHERE r.rol IS NOT NULL AND r.revocado_en IS NULL),
                           ARRAY[]::text[]),
                       COUNT(DISTINCT c.id),
                       COALESCE(jsonb_agg(DISTINCT jsonb_build_object(
                           'id', cm.id, 'nombre', cm.nombre
                       )) FILTER (WHERE cm.id IS NOT NULL), '[]'::jsonb),
                       COUNT(DISTINCT s.id) FILTER (WHERE s.estado = 'pendiente'),
                       p.es_cuenta_prueba
                  FROM persona p
                  LEFT JOIN rol_asignacion r ON r.sujeto_google = p.sujeto_google
                  LEFT JOIN clase c ON c.creador = p.sujeto_google
                    AND c.archivada_en IS NULL
                  LEFT JOIN clase_matricula m ON m.identificador = p.sujeto_google
                  LEFT JOIN clase cm ON cm.id = m.clase AND cm.archivada_en IS NULL
                  LEFT JOIN clase_solicitud s ON s.estudiante = p.sujeto_google
                 WHERE (%(filtro)s = ''
                    OR lower(p.correo) LIKE '%%' || %(filtro)s || '%%'
                    OR lower(p.nombre) LIKE '%%' || %(filtro)s || '%%')
                   AND (%(pertenencia)s = 'todas'
                    OR (%(pertenencia)s = 'con_clase' AND EXISTS (
                        SELECT 1 FROM clase_matricula mx JOIN clase cx ON cx.id = mx.clase
                         WHERE mx.identificador = p.sujeto_google
                           AND cx.archivada_en IS NULL))
                    OR (%(pertenencia)s = 'sin_clase' AND NOT EXISTS (
                        SELECT 1 FROM clase_matricula mx JOIN clase cx ON cx.id = mx.clase
                         WHERE mx.identificador = p.sujeto_google
                           AND cx.archivada_en IS NULL))
                    OR (%(pertenencia)s = 'solicitud_pendiente' AND EXISTS (
                        SELECT 1 FROM clase_solicitud sx
                         WHERE sx.estudiante = p.sujeto_google AND sx.estado = 'pendiente')))
                   AND (%(clase)s = '' OR EXISTS (
                       SELECT 1 FROM clase_matricula mx JOIN clase cx ON cx.id = mx.clase
                        WHERE mx.identificador = p.sujeto_google AND mx.clase = %(clase)s
                          AND cx.archivada_en IS NULL))
                 GROUP BY p.sujeto_google, p.correo, p.nombre, p.facultad,
                          p.es_cuenta_prueba
                 ORDER BY p.nombre, p.correo
                 LIMIT 100
                """,
                {"filtro": filtro, "pertenencia": pertenencia, "clase": clase},
            )
            filas = cur.fetchall()
        return [
            {
                "identificador": sujeto,
                "correo": correo,
                "nombre": nombre or "Cuenta institucional",
                "facultad": facultad or "",
                "tiene_foto": bool(tiene_foto),
                "roles": sorted(roles),
                "cursos": cursos,
                "es_docente": "docente" in roles or cursos > 0,
                "clases": clases or [],
                "solicitudes_pendientes": int(solicitudes_pendientes),
                "es_cuenta_prueba": bool(es_cuenta_prueba),
            }
            for sujeto, correo, nombre, facultad, tiene_foto, roles, cursos,
                clases, solicitudes_pendientes, es_cuenta_prueba in filas
        ]

    def asignar_facultad_profesional(
        self, investigador: str, sujeto: str, facultad: str
    ) -> dict | None:

        facultad = str(facultad or "").strip()
        if facultad not in FACULTADES:
            raise ValueError("facultad no admitida")
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, investigador)
            cur.execute(
                """
                SELECT 1
                  FROM persona p
                 WHERE p.sujeto_google = %s
                   AND (
                       EXISTS (SELECT 1 FROM clase c WHERE c.creador = p.sujeto_google)
                       OR EXISTS (
                           SELECT 1 FROM rol_asignacion r
                            WHERE r.sujeto_google = p.sujeto_google
                              AND r.rol = 'docente' AND r.revocado_en IS NULL
                       )
                   )
                 FOR UPDATE
                """,
                (sujeto,),
            )
            if cur.fetchone() is None:
                return None
            cur.execute(
                "UPDATE persona SET facultad = %s, actualizada_en = now() "
                "WHERE sujeto_google = %s RETURNING correo, nombre",
                (facultad, sujeto),
            )
            correo, nombre = cur.fetchone()
            anotar(
                cur,
                "asignar_facultad_profesional",
                actor=investigador,
                sujeto_afectado=sujeto,
                detalle={"facultad": facultad},
            )
        return {
            "identificador": sujeto,
            "correo": correo,
            "nombre": nombre or "Cuenta institucional",
            "facultad": facultad,
        }
