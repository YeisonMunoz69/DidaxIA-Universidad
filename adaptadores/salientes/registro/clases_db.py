"""
clases_db.py — Persistencia de clases y matrícula en PostgreSQL (`DD-12`)
============================================================================

Hasta el 2026-08-22 `Clases` (`clases_memoria.py`) era la única opción y vivía sólo en
memoria del proceso — declarado como correcto en su momento, pero sin ningún
motivo de producto para que un curso desaparezca en un reinicio del backend,
a diferencia de `Sesiones` (`RP-02` sí pide que esa sea efímera). Este
adaptador es la otra mitad: mismo `PuertoClases` que `Clases`,
re-expresado contra `08-clases.sql`.

Por qué devuelve `Clase`/`Matricula` de `dominio/puertos/clases.py`
------------------------------------------------------------------------
Reconstruirlas aquí en vez de duplicarlas es la misma disciplina que
`conexion.py` describe para el plazo de espera: «dos implementaciones de la
misma cuenta acaban discrepando siempre» — aquí sería
`como_fila()`/`como_resumen()` divergiendo entre el almacén en memoria y
este.

Hasta la Fase 2 · sesión 3 los dos modelos se importaban de
`adaptadores/entrantes/http/clases.py`, con el argumento de que «no hay un
`dominio/modelo/clase.py`». El diagnóstico era correcto y el remedio no: la
salida no era importar hacia atrás sino crear el sitio neutral que faltaba.
Ahora los dos almacenes —memoria y este— dependen del mismo puerto y ninguno
del otro.

`aplicacion.py` elige uno de los dos por `AGENTE_BD`, igual que
`composicion.py::_recuperacion()` ya elige entre el recuperador real y
`_SinIdentificador()`/`_CorpusVacio()` — ninguna ruta necesita saber cuál
recibió: las dos satisfacen `PuertoClases`.
"""

from __future__ import annotations

import secrets
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import exigir_investigador_administrador
from adaptadores.salientes.registro.base_postgres import (
    bloquear_y_exigir_sin_supresion,
    traducir_fallo,
)
from dominio.puertos.clases import (
    Clase,
    ConflictoDeMatricula,
    ContextoCurricular,
    Matricula,
    SolicitudDeMatricula,
)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator


def _codigo() -> str:
    # Mismo alfabeto que `clases_memoria.py::_codigo()` — sin
    # ambigüedad de mayúscula/minúscula ni de «cero» y «o».
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(6))


class AdaptadorClasesPostgres:
    """Ver el docstring del módulo. Las reglas de `DD-12` que en memoria eran
    código Python —«no duplica matrícula», «regenerar no expulsa»— aquí son
    propiedades de la base: `ON CONFLICT DO NOTHING` y una columna que
    `regenerar_codigo()` nunca toca fuera de `codigo`.

    ⚠️ **Y desde la corrección transversal, el trámite de `EQ-022`.** Crear una
    clase, unirse a una y regenerar un código son **escrituras del sujeto**: las
    tres dejan filas que lo nombran. Durante una supresión abierta no se
    registran, y la comprobación va dentro de la misma transacción con la fila de
    `persona` bloqueada.

    Se usa `bloquear_y_exigir_sin_supresion()` y no `exigir_persona_activa()`
    porque `clase.creador` y `clase_matricula.identificador` son `text` libres en
    la migración 08: hay clases cuyo creador no tiene fila en `persona`, y exigir
    que la tenga sería una regla nueva de producto, no una corrección de
    seguridad. Sin fila tampoco puede haber solicitud —clave foránea—, así que no
    queda ningún hueco.

    `mias()`, `integrantes()` y las demás lecturas **no** la llevan: consultar es
    un derecho que el trámite no suspende.
    """

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        """Una conexión, con los fallos de Psycopg ya traducidos.

        ⚠️ **`traducir_fallo()` se añadió con la corrección transversal**, y no es
        cosmética. Este adaptador es anterior a `base_postgres.py` y gestionaba su
        conexión sin traducir nada, así que un `psycopg.errors.UndefinedTable`
        —el esquema sin la migración 12— salía crudo hacia la ruta, que no sabía
        reconocerlo y lo dejaba subir como un error 500.

        Con la comprobación del trámite dentro, eso importa: «no puedo saber si
        hay una supresión abierta» tiene que llegar al borde como
        `AlmacenNoConfigurado` para que responda mantenimiento (`EQ-024`), y no
        como una excepción anónima. Es el mismo argumento que
        `registro/historial.py` dejó escrito cuando hizo lo propio.
        """
        from adaptadores.salientes.conexion import conectar  # noqa: PLC0415

        with traducir_fallo(), conectar(self._cadena) as cnx:
            yield cnx

    def _clase_desde_fila(
        self, cur, id_clase: str, nombre: str, creador: str, codigo: str
    ) -> Clase:
        cur.execute(
            """
            SELECT m.identificador, m.desde, COALESCE(p.nombre, ''),
                   COALESCE(p.foto_perfil_referencia, '')
              FROM clase_matricula m
              LEFT JOIN persona p ON p.sujeto_google = m.identificador
             WHERE m.clase = %s
             ORDER BY COALESCE(NULLIF(btrim(p.nombre), ''), m.identificador)
            """,
            (id_clase,),
        )
        matriculados = {
            identificador: Matricula(
                identificador=identificador,
                desde=desde.isoformat(timespec="seconds"),
                nombre=nombre,
                foto_referencia=foto,
            )
            for identificador, desde, nombre, foto in cur.fetchall()
        }
        return Clase(
            identificador=id_clase,
            nombre=nombre,
            creador=creador,
            codigo=codigo,
            matriculados=matriculados,
        )

    # -- crear, unirse, regenerar · las tres que pueden chocar con el UNIQUE de codigo --

    def crear(self, nombre: str, creador: str) -> Clase:
        import psycopg  # noqa: PLC0415

        identificador = secrets.token_urlsafe(8)
        codigo = _codigo()
        with self._conexion() as cnx, cnx.cursor() as cur:
            while True:
                try:
                    with cnx.transaction():
                        # El cerrojo y el trámite van DENTRO del reintento: la
                        # colisión de código reabre la transacción, y una
                        # comprobación hecha fuera se habría quedado con el
                        # estado de la primera vuelta.
                        bloquear_y_exigir_sin_supresion(cur, creador)
                        cur.execute(
                            "INSERT INTO clase (id, nombre, creador, codigo) VALUES (%s, %s, %s, %s)",
                            (identificador, nombre, creador, codigo),
                        )
                    break
                except psycopg.errors.UniqueViolation:  # colisión de código, improbable
                    codigo = _codigo()
        return Clase(identificador=identificador, nombre=nombre, creador=creador, codigo=codigo)

    def unirse(self, codigo: str, identificador: str) -> SolicitudDeMatricula | None:
        """El código abre una solicitud, nunca una matrícula."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._bloquear_estudiante(cur, identificador)
            bloquear_y_exigir_sin_supresion(cur, identificador)
            cur.execute(
                "SELECT id FROM clase WHERE codigo = %s AND archivada_en IS NULL FOR SHARE",
                (codigo.strip().upper(),),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            id_clase = fila[0]
            actual = self._matricula_actual(cur, identificador)
            if actual == id_clase:
                raise ConflictoDeMatricula("ya tienes matrícula vigente en esta clase")
            cur.execute(
                "SELECT id, clase_destino FROM clase_solicitud "
                "WHERE estudiante = %s AND estado = 'pendiente'", (identificador,),
            )
            pendiente = cur.fetchone()
            if pendiente:
                if pendiente[1] == id_clase:
                    return self._solicitud(cur, pendiente[0])
                raise ConflictoDeMatricula("cancela tu solicitud pendiente antes de pedir otra clase")
            solicitud = secrets.token_urlsafe(12)
            cur.execute(
                "INSERT INTO clase_solicitud (id, estudiante, clase_destino, clase_origen) "
                "VALUES (%s, %s, %s, %s)", (solicitud, identificador, id_clase, actual),
            )
            self._anotar_solicitud(cur, solicitud, identificador, "estudiante", "pendiente")
            return self._solicitud(cur, solicitud)

    def _bloquear_estudiante(self, cur, estudiante: str) -> None:
        # La fila de persona puede no existir para matrículas históricas.
        # El cerrojo transaccional cubre también la primera solicitud y evita
        # carreras entre peticiones antes de que exista ninguna fila propia.
        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 1800))", (estudiante,))

    def _matricula_actual(self, cur, estudiante: str) -> str | None:
        cur.execute(
            "SELECT m.clase FROM clase_matricula m JOIN clase c ON c.id = m.clase "
            "WHERE m.identificador = %s AND c.archivada_en IS NULL", (estudiante,),
        )
        fila = cur.fetchone()
        return fila[0] if fila else None

    def _solicitud(self, cur, identificador: str) -> SolicitudDeMatricula:
        cur.execute(
            """SELECT s.id, s.estudiante, s.clase_destino, d.nombre,
                      s.clase_origen, o.nombre, m.clase, a.nombre,
                      s.estado, s.creada_en, s.resuelta_en, s.resuelta_por,
                      COALESCE(p.nombre, ''), COALESCE(docente.correo, ''),
                      COALESCE(docente.nombre, ''), COALESCE(p.facultad, ''),
                      COALESCE(p.programa, ''), p.semestre, d.creador
                 FROM clase_solicitud s JOIN clase d ON d.id = s.clase_destino
                 LEFT JOIN clase o ON o.id = s.clase_origen
                 LEFT JOIN clase_matricula m ON m.identificador = s.estudiante
                 LEFT JOIN clase a ON a.id = m.clase
                 LEFT JOIN persona p ON p.sujeto_google = s.estudiante
                 LEFT JOIN persona docente ON docente.sujeto_google = d.creador
                WHERE s.id = %s""", (identificador,),
        )
        fila = list(cur.fetchone())
        fila[9] = fila[9].isoformat()
        fila[10] = fila[10].isoformat() if fila[10] else None
        return SolicitudDeMatricula(*fila)

    def solicitudes(self, quien: str, rol: str) -> list[SolicitudDeMatricula]:
        with self._conexion() as cnx, cnx.cursor() as cur:
            if rol == "investigador":
                exigir_investigador_administrador(cur, quien)
            cur.execute(
                """SELECT s.id FROM clase_solicitud s JOIN clase c ON c.id = s.clase_destino
                    WHERE %s = 'investigador' OR (%s = 'docente' AND c.creador = %s)
                       OR (%s = 'estudiante' AND s.estudiante = %s)
                    ORDER BY s.creada_en, s.id""", (rol, rol, quien, rol, quien),
            )
            return [self._solicitud(cur, fila[0]) for fila in cur.fetchall()]

    def _anotar_solicitud(self, cur, solicitud: str, quien: str, rol: str, estado: str) -> None:
        cur.execute(
            "INSERT INTO clase_solicitud_evento (solicitud, actor, rol_actor, estado) "
            "VALUES (%s, %s, %s, %s)", (solicitud, quien, rol, estado),
        )

    def _puede_resolver(self, cur, fila, quien: str, rol: str, decision: str) -> bool:
        estudiante, _, _, _, creador = fila
        if decision == "cancelada":
            return rol == "estudiante" and estudiante == quien
        if decision not in {"aprobada", "rechazada"}:
            return False
        if rol == "investigador":
            exigir_investigador_administrador(cur, quien)
            return True
        return rol == "docente" and creador == quien

    def resolver_solicitud(
        self, identificador: str, quien: str, rol: str, decision: str
    ) -> SolicitudDeMatricula | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute("SELECT estudiante FROM clase_solicitud WHERE id = %s", (identificador,))
            fila = cur.fetchone()
            if fila is None:
                return None
            estudiante = fila[0]
            self._bloquear_estudiante(cur, estudiante)
            for sujeto in sorted({quien, estudiante}):
                bloquear_y_exigir_sin_supresion(cur, sujeto)
            cur.execute(
                """SELECT s.estudiante, s.clase_destino, s.clase_origen, s.estado, c.creador
                     FROM clase_solicitud s JOIN clase c ON c.id = s.clase_destino
                    WHERE s.id = %s AND c.archivada_en IS NULL
                    FOR UPDATE OF s FOR SHARE OF c""", (identificador,),
            )
            fila = cur.fetchone()
            if fila is None or not self._puede_resolver(cur, fila, quien, rol, decision):
                return None
            if fila[3] != "pendiente":
                raise ConflictoDeMatricula("esta solicitud ya fue resuelta")
            cur.execute("SELECT clock_timestamp()")
            momento = cur.fetchone()[0]
            if decision == "aprobada":
                self._aprobar_matricula(cur, identificador, fila, momento)
            cur.execute(
                "UPDATE clase_solicitud SET estado = %s, resuelta_en = %s, resuelta_por = %s "
                "WHERE id = %s", (decision, momento, quien, identificador),
            )
            self._anotar_solicitud(cur, identificador, quien, rol, decision)
            return self._solicitud(cur, identificador)

    def _aprobar_matricula(self, cur, solicitud: str, fila, momento) -> None:
        estudiante, destino, origen, _, _ = fila
        if self._matricula_actual(cur, estudiante) != origen:
            raise ConflictoDeMatricula("la matrícula cambió; cancela y crea una nueva solicitud")
        # Registra también una matrícula preexistente escrita por una importación
        # posterior a la migración. Es procedencia explícita, no una aprobación.
        cur.execute(
            """INSERT INTO clase_matricula_historial (estudiante, clase, desde, procedencia)
               SELECT m.identificador, m.clase, m.desde, 'preexistente'
                 FROM clase_matricula m WHERE m.identificador = %s
                  AND NOT EXISTS (SELECT 1 FROM clase_matricula_historial h
                                  WHERE h.estudiante = %s AND h.hasta IS NULL)""",
            (estudiante, estudiante),
        )
        cur.execute(
            "UPDATE clase_matricula_historial SET hasta = %s "
            "WHERE estudiante = %s AND hasta IS NULL", (momento, estudiante),
        )
        cur.execute("DELETE FROM clase_matricula WHERE identificador = %s", (estudiante,))
        cur.execute(
            "INSERT INTO clase_matricula (clase, identificador, desde) VALUES (%s, %s, %s)",
            (destino, estudiante, momento),
        )
        cur.execute(
            "INSERT INTO clase_matricula_historial "
            "(estudiante, clase, desde, solicitud, procedencia) VALUES (%s, %s, %s, %s, 'aprobacion')",
            (estudiante, destino, momento, solicitud),
        )

    def regenerar_codigo(self, identificador: str, quien: str) -> str | None:
        """`None` si no existe o no es de `quien` — misma ambigüedad
        deliberada que la versión en memoria: no distingue los dos casos
        hacia quien pregunta."""
        import psycopg  # noqa: PLC0415

        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute("SELECT creador FROM clase WHERE id = %s AND archivada_en IS NULL", (identificador,))
            fila = cur.fetchone()
            if fila is None or fila[0] != quien:
                return None
            nuevo = _codigo()
            while True:
                try:
                    with cnx.transaction():
                        # Regenerar es una acción de producto del creador sobre
                        # su clase. No aporta un dato personal nuevo, pero sí es
                        # uso del producto, y `ESTADO-ACTUAL.md` §10.2 lo
                        # suspende durante el trámite.
                        bloquear_y_exigir_sin_supresion(cur, quien)
                        # Solo `codigo` — nunca `clase_matricula`: invalida el
                        # código, no expulsa a quien ya entró.
                        cur.execute(
                            "UPDATE clase SET codigo = %s WHERE id = %s AND archivada_en IS NULL",
                            (nuevo, identificador),
                        )
                    break
                except psycopg.errors.UniqueViolation:
                    nuevo = _codigo()
        return nuevo

    def renombrar(self, identificador: str, quien: str, nombre: str) -> Clase | None:
        """Renombra sólo si la clase pertenece al actor, dentro de la escritura."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            bloquear_y_exigir_sin_supresion(cur, quien)
            cur.execute(
                "UPDATE clase SET nombre = %s WHERE id = %s AND creador = %s "
                "AND archivada_en IS NULL "
                "RETURNING id, nombre, creador, codigo",
                (nombre, identificador, quien),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            return self._clase_desde_fila(cur, *fila)

    def archivar(self, identificador: str, quien: str, motivo: str, rol: str = "docente") -> bool:
        """Cierra la clase y sus matrículas en una transacción; conserva evidencia."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            if rol not in {"docente", "investigador"}:
                return False
            if rol == "investigador":
                exigir_investigador_administrador(cur, quien)
            cur.execute(
                "SELECT creador FROM clase WHERE id = %s AND archivada_en IS NULL",
                (identificador,),
            )
            fila = cur.fetchone()
            if fila is None or (rol == "docente" and fila[0] != quien):
                return False
            # Las aprobaciones bloquean primero al estudiante y luego la clase.
            # Mantener ese orden evita un ciclo con una transferencia concurrente.
            participantes_sql = """
                SELECT identificador FROM clase_matricula WHERE clase = %s
                UNION SELECT estudiante FROM clase_solicitud
                       WHERE (clase_destino = %s OR clase_origen = %s) AND estado = 'pendiente'
                UNION SELECT estudiante FROM clase_matricula_historial
                       WHERE clase = %s AND hasta IS NULL
            """
            cur.execute(participantes_sql, (identificador,) * 4)
            sujetos = {fila[0] for fila in cur.fetchall()}
            for estudiante in sorted(sujetos):
                self._bloquear_estudiante(cur, estudiante)
            bloquear_y_exigir_sin_supresion(cur, quien)
            cur.execute(
                "UPDATE clase SET archivada_en = clock_timestamp(), "
                "archivada_por = %s, motivo_archivo = %s "
                "WHERE id = %s AND (creador = %s OR %s = 'investigador') "
                "AND archivada_en IS NULL RETURNING archivada_en",
                (quien, motivo, identificador, quien, rol),
            )
            fila = cur.fetchone()
            if fila is None:
                return False
            momento = fila[0]
            cur.execute(participantes_sql, (identificador,) * 4)
            if {fila[0] for fila in cur.fetchall()} - sujetos:
                raise ConflictoDeMatricula("La matrícula cambió durante el cierre; vuelve a intentarlo.")
            # Importaciones antiguas pueden tener matrícula sin periodo: conservar
            # su procedencia antes de retirar sólo la relación vigente.
            cur.execute(
                """INSERT INTO clase_matricula_historial (estudiante, clase, desde, procedencia)
                   SELECT m.identificador, m.clase, m.desde, 'preexistente'
                     FROM clase_matricula m WHERE m.clase = %s
                      AND NOT EXISTS (SELECT 1 FROM clase_matricula_historial h
                          WHERE h.estudiante = m.identificador AND h.clase = m.clase
                            AND h.hasta IS NULL)""",
                (identificador,),
            )
            cur.execute(
                "UPDATE clase_matricula_historial SET hasta = %s WHERE clase = %s AND hasta IS NULL",
                (momento, identificador),
            )
            cur.execute("DELETE FROM clase_matricula WHERE clase = %s", (identificador,))
            retirados = cur.rowcount
            cur.execute(
                """UPDATE clase_solicitud
                      SET estado = 'cancelada', resuelta_en = %s,
                          resuelta_por = %s
                    WHERE (clase_destino = %s OR clase_origen = %s) AND estado = 'pendiente'
                    RETURNING id""",
                (momento, quien, identificador, identificador),
            )
            canceladas = [fila[0] for fila in cur.fetchall()]
            for solicitud in canceladas:
                self._anotar_solicitud(cur, solicitud, quien, rol, "cancelada")
            anotar(
                cur, "clase.archivada", actor=quien,
                detalle={"clase": identificador, "motivo": motivo,
                         "solicitudes_canceladas": len(canceladas),
                         "matriculas_cerradas": retirados, "rol_actor": rol},
            )
            return True

    # -- lectura ------------------------------------------------------------

    def mias(self, identificador: str) -> list[Clase]:
        """Las que creó, más las que se unió — una fila por clase, sin el
        `OR` duplicando nada porque es la misma fila la que puede cumplir
        las dos condiciones."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre, creador, codigo FROM clase
                 WHERE archivada_en IS NULL AND (
                    creador = %s OR id IN (
                        SELECT clase FROM clase_matricula WHERE identificador = %s))
                """,
                (identificador, identificador),
            )
            filas = cur.fetchall()
            return [
                self._clase_desde_fila(cur, id_clase, nombre, creador, codigo)
                for id_clase, nombre, creador, codigo in filas
            ]

    def obtener(self, identificador: str) -> Clase | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT id, nombre, creador, codigo FROM clase "
                "WHERE id = %s AND archivada_en IS NULL",
                (identificador,),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            return self._clase_desde_fila(cur, *fila)

    def integrantes(self, identificador: str, quien: str) -> list[Matricula] | None:
        """`None` si no existe o `quien` no es su creador."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute("SELECT creador FROM clase WHERE id = %s AND archivada_en IS NULL", (identificador,))
            fila = cur.fetchone()
            if fila is None or fila[0] != quien:
                return None
            cur.execute(
                """
                SELECT m.identificador, m.desde, COALESCE(p.nombre, ''),
                       COALESCE(p.foto_perfil_referencia, ''),
                       COALESCE(p.facultad, ''), COALESCE(p.programa, ''), p.semestre
                  FROM clase_matricula m
                  LEFT JOIN persona p ON p.sujeto_google = m.identificador
                 WHERE m.clase = %s
                 ORDER BY COALESCE(NULLIF(btrim(p.nombre), ''), m.identificador)
                """,
                (identificador,),
            )
            return [
                Matricula(
                    identificador=ident,
                    desde=desde.isoformat(timespec="seconds"),
                    nombre=nombre,
                    foto_referencia=foto,
                    facultad=facultad,
                    programa=programa,
                    semestre=semestre,
                )
                for ident, desde, nombre, foto, facultad, programa, semestre in cur.fetchall()
            ]

    def retirar_integrante(
        self, identificador: str, quien: str, estudiante: str, motivo: str
    ) -> Matricula | None:
        """Retira de una clase propia sin borrar identidad ni historia académica."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute("SELECT creador FROM clase WHERE id = %s FOR UPDATE", (identificador,))
            propietaria = cur.fetchone()
            if propietaria is None or propietaria[0] != quien:
                return None
            for sujeto in sorted({quien, estudiante}):
                bloquear_y_exigir_sin_supresion(cur, sujeto)
            cur.execute(
                """
                SELECT m.identificador, m.desde, COALESCE(p.nombre, ''),
                       COALESCE(p.foto_perfil_referencia, ''),
                       COALESCE(p.facultad, ''), COALESCE(p.programa, ''), p.semestre
                  FROM clase_matricula m
                  LEFT JOIN persona p ON p.sujeto_google = m.identificador
                 WHERE m.clase = %s AND m.identificador = %s
                   FOR UPDATE OF m
                """,
                (identificador, estudiante),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            cur.execute("SELECT clock_timestamp()")
            momento = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO clase_matricula_historial
                           (estudiante, clase, desde, procedencia)
                   SELECT m.identificador, m.clase, m.desde, 'preexistente'
                     FROM clase_matricula m
                    WHERE m.clase = %s AND m.identificador = %s
                      AND NOT EXISTS (
                          SELECT 1 FROM clase_matricula_historial h
                           WHERE h.estudiante = m.identificador AND h.hasta IS NULL
                      )""",
                (identificador, estudiante),
            )
            cur.execute(
                "UPDATE clase_matricula_historial SET hasta = %s "
                "WHERE estudiante = %s AND clase = %s AND hasta IS NULL",
                (momento, estudiante, identificador),
            )
            cur.execute(
                "DELETE FROM clase_matricula WHERE clase = %s AND identificador = %s",
                (identificador, estudiante),
            )
            anotar(
                cur,
                "matricula.retirada_por_docente",
                actor=quien,
                sujeto_afectado=estudiante,
                detalle={
                    "clase": identificador,
                    "motivo": motivo,
                    "resultado": "matrícula cerrada",
                },
            )
            cnx.commit()
            ident, desde, nombre, foto, facultad, programa, semestre = fila
            return Matricula(
                identificador=ident,
                desde=desde.isoformat(timespec="seconds"),
                nombre=nombre,
                foto_referencia=foto,
                facultad=facultad,
                programa=programa,
                semestre=semestre,
            )

    def contexto_curricular(self, identificador: str, quien: str) -> ContextoCurricular | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT unidad_curricular, notacion_curricular,
                       observaciones_curriculares, contexto_actualizado_en
                  FROM clase
                 WHERE id = %s AND creador = %s
                """,
                (identificador, quien),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            unidad, notacion, observaciones, actualizado = fila
            return ContextoCurricular(
                clase=identificador,
                unidad=unidad,
                notacion=notacion,
                observaciones=observaciones,
                actualizado_en=(actualizado.isoformat(timespec="seconds") if actualizado else None),
            )

    def guardar_contexto_curricular(
        self, identificador: str, quien: str, unidad: str, notacion: str, observaciones: str
    ) -> ContextoCurricular | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            with cnx.transaction():
                bloquear_y_exigir_sin_supresion(cur, quien)
                cur.execute(
                    """
                    UPDATE clase
                       SET unidad_curricular = %s,
                           notacion_curricular = %s,
                           observaciones_curriculares = %s,
                           contexto_actualizado_en = now()
                     WHERE id = %s AND creador = %s
                 RETURNING contexto_actualizado_en
                    """,
                    (unidad, notacion, observaciones, identificador, quien),
                )
                fila = cur.fetchone()
            if fila is None:
                return None
            return ContextoCurricular(
                clase=identificador,
                unidad=unidad,
                notacion=notacion,
                observaciones=observaciones,
                actualizado_en=fila[0].isoformat(timespec="seconds"),
            )

    def integrante_para_investigacion(
        self, identificador: str, investigador: str, estudiante: str
    ) -> Matricula | None:
        """Un integrante concreto tras volver a comprobar el rol institucional."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, investigador)
            cur.execute(
                """
                SELECT m.identificador, m.desde, COALESCE(p.nombre, ''),
                       COALESCE(p.foto_perfil_referencia, '')
                  FROM clase_matricula m
                  LEFT JOIN persona p ON p.sujeto_google = m.identificador
                 WHERE m.clase = %s AND m.identificador = %s
                """,
                (identificador, estudiante),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            anotar(
                cur,
                "consultar_foto_estudiante_institucional",
                actor=investigador,
                sujeto_afectado=estudiante,
                detalle={"clase": identificador},
            )
            cnx.commit()
            ident, desde, nombre, foto = fila
            return Matricula(
                identificador=ident,
                desde=desde.isoformat(timespec="seconds"),
                nombre=nombre,
                foto_referencia=foto,
            )

    # -- supresión · RD-22 ---------------------------------------------------

    def suprimir_sujeto(self, identificador: str) -> int:
        """Quita a `identificador` de toda matrícula donde esté — no borra
        las clases que haya creado, `DD-12` no ofrece borrar una clase. Ver
        `Clases.suprimir_sujeto()` (memoria) para el mismo contrato."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._bloquear_estudiante(cur, identificador)
            cur.execute(
                "DELETE FROM clase_matricula WHERE identificador = %s",
                (identificador,),
            )
            quitadas = cur.rowcount
            cur.execute("DELETE FROM clase_matricula_historial WHERE estudiante = %s", (identificador,))
            cur.execute("DELETE FROM clase_solicitud WHERE estudiante = %s", (identificador,))
            cnx.commit()
        return quitadas
