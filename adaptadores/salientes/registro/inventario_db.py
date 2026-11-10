"""
inventario_db.py — Qué alcanzaría una supresión, contado y no ejecutado (B3)
=============================================================================

`PuertoInventarioDeDatos` contra PostgreSQL y contra las autoridades paralelas
que el inventario de la Fase 2 · sesión 1 dejó anotadas.

Qué cuenta, y por qué esa lista
-------------------------------------------
Sale del inventario que la auditoría de persistencia produjo, no de recordar qué
tablas existen: PostgreSQL, el registro forense en volumen, el navegador y los
archivos. Cada autoridad dice **cuántas filas** le corresponden al titular, si
contiene **texto libre** —lo que V-B tiene que mirar una por una— y si una
cascada de hoy la **alcanza**.

⚠️ Sólo lee, y no devuelve ni un dato personal
----------------------------------------------------------
Ni un `DELETE`, ni un `UPDATE`, ni una transacción de escritura. Y lo que sale
son nombres de tabla y conteos: un inventario que imprimiera lo que va a borrar
sería una exportación disfrazada, y se le enseña a quien depura.

Lo que no es alcanzable, declarado
----------------------------------------------
Tres autoridades salen marcadas `alcanzable=False`, y no es un fallo de este
adaptador: es la deuda que la Fase 2 dejó escrita y que el cierre V-B tiene que
resolver.

- **el registro forense en volumen** · `infraestructura/registro_turnos/` guarda
  un JSON por turno. `registro_turno` tiene la clave del sujeto; los archivos se
  nombran por turno, así que alcanzarlos exige leer la tabla primero. Se cuenta
  a través de ella y se marca como autoridad aparte porque **borrar la fila no
  borra el archivo**;
- **`cola_revision`** · no tiene clave de sujeto. Su `turno` es JSONB y el
  titular no está indexado; contarlo exigiría recorrer la cola entera y aun así
  no sería fiable. Se declara con `filas=0` y la nota que lo explica;
- **el navegador** · `sessionStorage` conserva el hilo completo. Ninguna
  supresión del servidor lo alcanza, y `EQ-007` ya lo tiene como contradicción
  pendiente.


"""

from __future__ import annotations

from typing import Any

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.base_postgres import RepositorioPostgres
from dominio.puertos.inventario_de_datos import Autoridad, InventarioPorTitular

#: Las tablas que se cuentan por `identificador_sujeto`, con si llevan texto
#: escrito por personas. Una tupla y no un descubrimiento automático: qué es
#: texto libre es una afirmación sobre el contenido, y eso no se deduce del
#: esquema.
_POR_SUJETO = (
    ("perfil_afectivo", False),
    ("perfil_conceptual", False),
    ("perfil_estrategico", False),
    ("registro_turno", False),
    ("historial_turno", True),
    # Fase 8 · los eventos que alimentan el catálogo KPI. Entra en el inventario
    # el mismo día que nace la tabla, y no después: una autoridad que aparece en
    # la base pero no en este inventario es exactamente la deuda que la Fase 2 ·
    # sesión 1 dejó anotada —«borrar una conversación elimina el historial, pero
    # no llama al borrado hermano del registro forense»—.
    #
    # `texto_libre=False` y es comprobable: la migración 23 acota `metadatos` a
    # 1000 caracteres con valores de vocabulario cerrado, y el dominio rechaza
    # cualquier clave no declarada. Aquí no hay frases escritas por personas.
    ("evento_telemetria", False),
)

#: Las de la migración 11, que se cuentan por `sujeto_google`.
_POR_SUJETO_GOOGLE = (
    ("recurso_respuesta", True),
    ("recurso_visita", False),
    ("preferencia_interfaz", False),
    ("persona", False),
    ("consentimiento_evento", False),
    ("asentimiento_evento", False),
    ("representante_evidencia", False),
    ("rol_asignacion", False),
    ("solicitud_supresion", False),
)


#: `EQ-023` · con qué nombre queda registrada la consulta de un inventario
#: ajeno. Constante por la misma razón que en `historial.py` y `roles_db.py`.
OPERACION_INVENTARIO = "inventario.consultado"


class AdaptadorInventarioPostgres(RepositorioPostgres):
    """`PuertoInventarioDeDatos`. Cuenta; nunca toca."""

    def inventariar(self, sujeto_google: str, *, actor: str = "") -> InventarioPorTitular:
        """Qué alcanzaría una supresión de ese titular.

        Devuelve **todas** las autoridades, incluidas las de cero filas: saber
        que una tabla no le corresponde es un dato, y omitirla haría imposible
        distinguir «no tiene» de «no se miró».

        ⚠️ **`actor` audita una consulta de datos AJENOS**, en la misma
        transacción y **antes** de contar nada (`EQ-023`, hito R5). Si la
        auditoría falla, la transacción se deshace y no se devuelve ningún
        conteo: no puede existir una lectura de lo de otra persona sin constancia
        de quién la hizo. Auditar después dejaría el inventario ya entregado y el
        registro faltando.

        Vacío cuando el titular mira **lo suyo**: `EQ-023` audita el acceso a
        datos ajenos, y registrar que alguien consultó su propio inventario
        enterraría los accesos que sí importan bajo filas sin valor.
        """
        with self._escritura() as cnx, cnx.cursor() as cur:
            if actor:
                anotar(
                    cur,
                    OPERACION_INVENTARIO,
                    actor=actor,
                    sujeto_afectado=sujeto_google,
                    # Ni un conteo: lo que `EQ-023` registra es que se consultó,
                    # y el resultado de la consulta es el dato ajeno.
                    detalle={},
                )
            autoridades = [
                *self._tablas_por_columna(cur, sujeto_google, _POR_SUJETO, "identificador_sujeto"),
                *self._tablas_por_columna(
                    cur, sujeto_google, _POR_SUJETO_GOOGLE, "sujeto_google"
                ),
                self._matriculas(cur, sujeto_google),
                self._clases_creadas(cur, sujeto_google),
                self._historial_cuerpo(cur, sujeto_google, "historial_bloque"),
                self._historial_cuerpo(cur, sujeto_google, "historial_cita"),
                self._historial_cuerpo(cur, sujeto_google, "analisis_conductual"),
                *self._tablas_por_columna(
                    cur, sujeto_google, (("relectura_conductual_trabajo", False),), "actor"
                ),
                self._revisiones(cur, sujeto_google),
                self._registro_forense(cur, sujeto_google),
                self._cola_de_revision(),
                self._navegador(),
            ]
        return InventarioPorTitular(sujeto_google=sujeto_google, autoridades=tuple(autoridades))

    def _contar(self, cur: Any, sql: str, parametros: tuple) -> int:
        cur.execute(sql, parametros)
        return cur.fetchone()[0]

    def _tablas_por_columna(
        self, cur: Any, sujeto: str, tablas: tuple, columna: str
    ) -> list[Autoridad]:
        salida = []
        for tabla, texto_libre in tablas:
            # `tabla` y `columna` salen de las constantes de arriba, nunca de
            # una entrada: un nombre de tabla no admite parámetro.
            filas = self._contar(
                cur,
                f"SELECT count(*) FROM {tabla} WHERE {columna} = %s",  # noqa: S608
                (sujeto,),
            )
            salida.append(Autoridad(nombre=tabla, filas=filas, texto_libre=texto_libre))
        return salida

    def _matriculas(self, cur: Any, sujeto: str) -> Autoridad:
        """`RD-22` ya la alcanza: `suprimir_sujeto()` quita las matrículas.

        `EQ-022` es explícito en que *«la pertenencia a una clase no se borra por
        una revocación»*; la supresión sí la alcanza, y son cosas distintas.
        """
        filas = self._contar(
            cur, "SELECT count(*) FROM clase_matricula WHERE identificador = %s", (sujeto,)
        )
        return Autoridad(nombre="clase_matricula", filas=filas)

    def _clases_creadas(self, cur: Any, sujeto: str) -> Autoridad:
        """Las clases que este titular creó. `DD-12` no ofrece borrar una clase.

        Se marcan como **no alcanzables** porque borrarlas afectaría a terceros
        —los demás matriculados— y eso no lo decide una supresión individual.
        """
        filas = self._contar(cur, "SELECT count(*) FROM clase WHERE creador = %s", (sujeto,))
        return Autoridad(
            nombre="clase (creadas)",
            filas=filas,
            alcanzable=False,
            nota="borrarlas afectaría a terceros matriculados; decisión de V-B",
        )

    def _historial_cuerpo(self, cur: Any, sujeto: str, tabla: str) -> Autoridad:
        """Bloques y citas cuelgan de `historial_turno`, no del sujeto.

        Se cuentan a través de él: la cascada los alcanza porque la clave foránea
        de `06-historial-cuerpo.sql` va en cascada, pero contarlos aparte hace
        visible cuánto texto hay debajo de cada mensaje.
        """
        filas = self._contar(
            cur,
            f"SELECT count(*) FROM {tabla} b "  # noqa: S608
            "JOIN historial_turno h ON h.id = b.historial "
            "WHERE h.identificador_sujeto = %s",
            (sujeto,),
        )
        return Autoridad(nombre=tabla, filas=filas, texto_libre=True)

    def _revisiones(self, cur: Any, sujeto: str) -> Autoridad:
        """Revisiones **hechas por** este titular, si es investigador.

        No alcanzables: son la prueba de que una autorización se aprobó, y
        `EQ-022` reconoce deberes de conservación. Borrarlas dejaría aprobaciones
        sin autor.
        """
        filas = self._contar(
            cur, "SELECT count(*) FROM representante_revision WHERE revisada_por = %s", (sujeto,)
        )
        return Autoridad(
            nombre="representante_revision (como revisor)",
            filas=filas,
            alcanzable=False,
            nota="evidencia de quién aprobó una autorización; deber de conservación",
        )

    def _registro_forense(self, cur: Any, sujeto: str) -> Autoridad:
        """Los JSON de `DD-08`, contados a través de `registro_turno`.

        **Borrar la fila no borra el archivo**, y por eso es una autoridad aparte
        y no alcanzable: la cascada de hoy llega a la tabla y deja el volumen.
        Es exactamente la brecha que la Fase 2 · sesión 1 midió —70 archivos
        frente a 67 filas— y que V-B tiene que resolver.
        """
        filas = self._contar(
            cur,
            "SELECT count(*) FROM registro_turno WHERE identificador_sujeto = %s AND "
            "coalesce(btrim(ruta_archivo), '') <> ''",
            (sujeto,),
        )
        return Autoridad(
            nombre="registro forense (archivos en volumen)",
            filas=filas,
            alcanzable=False,
            nota="la cascada llega a registro_turno y no al archivo; brecha de Fase 2",
        )

    def _cola_de_revision(self) -> Autoridad:
        """`cola_revision` no tiene clave de sujeto y no se puede contar.

        Se declara con cero y la nota: decir «no tiene» cuando lo que pasa es que
        no se puede mirar sería el silencio que este inventario existe para
        evitar.
        """
        return Autoridad(
            nombre="cola_revision",
            filas=0,
            texto_libre=True,
            alcanzable=False,
            nota="no tiene clave de sujeto: no se puede contar ni alcanzar por titular",
        )

    def _navegador(self) -> Autoridad:
        """`sessionStorage` conserva el hilo. Ninguna supresión del servidor lo
        alcanza, y `EQ-007` ya lo tiene como contradicción pendiente."""
        return Autoridad(
            nombre="navegador (sessionStorage)",
            filas=0,
            texto_libre=True,
            alcanzable=False,
            nota="fuera del alcance del servidor; contradice EQ-007 y sigue pendiente",
        )
