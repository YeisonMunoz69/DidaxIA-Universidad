"""
roles_db.py — `PuertoAsignacionDeRoles` sobre `rol_asignacion` (migración 11)
==============================================================================

⚠️ **Relación con el rol docente, primero.** Este adaptador no lee ni escribe
`solicitud_docente` ni `DOCENTES_AUTORIZADOS`: ambos sostienen las cuentas
heredadas. La migración 22 amplía esta autoridad persistente para que las altas
nuevas de `docente`, igual que las de investigación, sean reversibles y
auditadas. `estudiante` no se almacena: es la experiencia base.

El permiso `investigador_administrador` sigue siendo el único que autoriza la
revisión de evidencia; tener `docente` nunca concede esa capacidad.

Revocar no borra
------------------------
`revocar()` pone `revocado_en`. La fila se conserva porque una aprobación de hace
un mes tiene que seguir explicándose: si la asignación desapareciera, esa
aprobación quedaría hecha por alguien que —según la base— nunca pudo hacerla.

⚠️ Cada cambio de permisos se audita, y en la misma transacción · hito R5
---------------------------------------------------------------------------
`EQ-023`: *«Cada consulta de una conversación y cada cambio de permisos quedan
registrados.»* La constancia la escribe `anotar()` con el mismo cursor, así que
un fallo de auditoría deja el rol **como estaba**. No hay una asignación
silenciosa: o consta quién la hizo, o no ocurrió.

⚠️ Y cada cambio de permisos se AUTORIZA en esa misma transacción · hito R7-B
------------------------------------------------------------------------------
Faltaba la otra mitad, y la revisión la demostró: `asignar()` y `revocar()` no
volvían a mirar el rol del actor: se fiaban de la comprobación que hacía la ruta
antes de abrir la transacción. Un sujeto registrado **con el conjunto de roles
vacío** llamó a `asignar()` directamente y el tercero terminó con
`investigador_administrador`.

Ahora la autorización la exige `autorizacion_sql.py` con el mismo cursor, y
además **retiene** la asignación del actor mientras dura la operación, de modo
que una revocación concurrente no pueda confirmarse entre la comprobación y el
efecto. Los tres consumidores de esa regla —este módulo, `gobierno_db.py` y
`menores_db.py`— comparten una sola redacción; antes había tres.

**El bootstrap es la única excepción, y se ve.** `otorgado_por = None` no audita
ni exige autorización porque no hay actor que registrar ni a quién exigirle nada:
la primera asignación del sistema no la puede otorgar un investigador —no existe
todavía— y por eso **ninguna ruta la ofrece**. `POST /api/gobierno/roles` pasa
siempre el actor de la sesión, así que ningún camino HTTP alcanza esta rama: es
una operación deliberada del equipo contra la base. Inventar un actor para poder
auditarla sería fabricar una autoría, que es peor que declarar el hueco.

⚠️ **Nadie se otorga ni se retira el rol a sí mismo**, y la regla vive también
aquí y no sólo en la ruta (`exigir_actor_distinto()`), por el mismo motivo que la
anterior: lo que sólo comprueba el borde se salta llamando al repositorio.

El índice único parcial `rol_asignacion_vigente` es quien impide dos asignaciones
vigentes del mismo rol para la misma persona; `asignar()` lo comprueba además
antes de escribir para poder dar un motivo en vez de un choque de clave.


"""

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

#: Con qué nombre quedan los dos cambios de permisos en `auditoria_operacion`.
#: Constantes y no cadenas sueltas: es lo que busca una consulta de auditoría, y
#: dos redacciones del mismo hecho dejarían la mitad sin aparecer.
OPERACION_ASIGNAR = "rol.asignado"
OPERACION_REVOCAR = "rol.revocado"

#: Proyección única de identidad y funciones vigentes para lecturas
#: institucionales. Vive junto a la autoridad de roles para que ningún otro
#: adaptador vuelva a redactar por su cuenta cómo se interpreta
#: ``rol_asignacion``; los consumidores la insertan como CTE dentro de su misma
#: consulta y conservan así un solo corte transaccional, sin N+1.
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

#: Sujetos con una función profesional vigente que no deben aparecer como
#: estudiantes en analíticas de actividad. La lectura de ``rol_asignacion``
#: vive junto a la autoridad de roles, igual que ``PRESENTACION_PERSONAS_SQL``;
#: los consumidores insertan este subquery constante en su propia consulta y
#: evitan tanto N+1 como una segunda definición de qué rol está vigente.
SUJETOS_PROFESIONALES_VIGENTES_SQL = """
SELECT sujeto_google
  FROM rol_asignacion
 WHERE revocado_en IS NULL
   AND rol IN ('docente', 'investigador_administrador')
"""


class AdaptadorRolesPostgres(RepositorioPostgres):
    """Las cuatro operaciones del puerto, contra `rol_asignacion`."""

    def asignar(
        self, sujeto_google: str, rol: Rol, otorgado_por: str | None = None
    ) -> AsignacionDeRol:
        """Otorga el rol. Repetirlo estando vigente es un rechazo, no un `UPDATE`.

        Con `otorgado_por` queda auditado en la misma transacción (`EQ-023`); sin
        él es el bootstrap del equipo — ver la cabecera del módulo.

        ⚠️ **Con actor, el actor se autoriza aquí dentro** (hito R7-B). Hasta esta
        corrección este método se fiaba de que la ruta hubiera mirado el rol, y la
        revisión lo aprovechó: un sujeto registrado con el conjunto de roles vacío
        llamó al adaptador directamente y el tercero terminó con el rol. Ahora la
        autorización, el efecto y la auditoría comparten cursor y transacción, y
        la asignación del actor queda **retenida** mientras dura la operación —el
        porqué del nivel de lock está en `autorizacion_sql.py`—.

        El orden es el contrato:

        1. **el actor no es el sujeto** — barato y no toca la base;
        2. **el sujeto existe** — `exigir_persona()`, que además serializa por
           titular. Va antes que la autorización para conservar el contrato del
           puerto: un sujeto desconocido levanta `ReferenciaDesconocida`, y ese
           desenlace es el que la ruta traduce a 404;
        3. **el actor tiene el rol, y se le retiene** hasta el commit;
        4. **no hay ya una asignación vigente**;
        5. **el efecto**;
        6. **la auditoría**, con el mismo cursor.

        Cualquiera que falle deshace las anteriores.
        """
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
                    # El rol, nada más. Ni correo ni nombre: la auditoría vive
                    # más que lo que audita.
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
        """Cierra la asignación vigente, con autor. `False` si no había ninguna.

        `revocado_por` tiene que ser una persona registrada —`exigir_persona()` lo
        comprueba antes de escribir— porque `EQ-023` audita cada cambio de
        permisos: una revocación anónima deja sin explicar por qué alguien pudo
        aprobar una autorización el mes pasado y hoy no. La base exige la pareja
        con `rol_asignacion_revocacion_auditada`.

        ⚠️ **Y tiene que ser un investigador administrador vigente** (hito R7-B).
        Estar registrado como persona no es un permiso: hasta esta corrección
        bastaba con existir para poder retirarle el rol a cualquiera. No hay aquí
        una excepción de bootstrap como en `asignar()`, y no la puede haber:
        revocar presupone que alguien ya tenía el rol, así que siempre hay a quién
        exigírselo.
        """
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_actor_distinto(revocado_por, sujeto_google)
            # `exigir_persona()` antes que la autorización, igual que en
            # `asignar()`: quien no existe sigue levantando `ReferenciaDesconocida`
            # y la ruta lo sigue traduciendo a 404. Quien existe pero no tiene el
            # rol cae en la línea siguiente.
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
        """Los vigentes. Conjunto vacío para quien no tiene ninguno."""
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
        """El historial completo, vigentes y revocadas, de la más antigua a la
        más reciente."""
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
        """Cuentas registradas y funciones vigentes, leídas por su autoridad.

        Esta consulta vive aquí —y no en analítica— porque este adaptador es la
        única autoridad que conoce ``rol_asignacion``. La autorización y la
        auditoría se resuelven con el mismo cursor que produce el directorio.
        """
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
        """Asigna una facultad a una cuenta docente, con auditoría atómica."""
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
