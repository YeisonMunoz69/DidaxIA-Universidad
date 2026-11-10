"""
historial.py — El historial de conversación, en PostgreSQL (`PM-B37`)
=========================================================================

El adaptador que implementa **`PuertoRegistro.registrar_turno()`**, el método
que el puerto declaraba desde el principio y que **ningún adaptador
implementaba**. `archivo.py` lo dejó escrito: *«`PuertoRegistro` tiene cinco
métodos. Este adaptador implementa uno»*.

Archivo propio, y no dentro de `archivo.py`
-----------------------------------------------
Por el mismo argumento que aquel da para no juntar los cinco métodos: son
almacenes distintos con disciplinas distintas. `registro_turno` es un **índice**
—se reescribe con `ON CONFLICT DO UPDATE`— y esto es **historial**: lo que el
estudiante escribió es lo que ocurrió, y no se reescribe nunca (`ADR-004` C1).
Mezclarlos repetiría el error que `ADR-003` K1 prohíbe en el modelo: forzar
naturalezas distintas a compartir mecanismo porque comparten paquete.

Una fila por voz
--------------------
`EntradaDeTurno` lo dice: *«el mismo turno produce (al menos) dos entradas, una
por lado de la conversación»*. Este adaptador escribe **una fila por llamada** y
no agrupa: quien tenga dos voces llama dos veces. Sin `ON CONFLICT`, porque
`turno` no es único aquí a propósito — dos filas lo comparten.

⚠️ Este adaptador LEE, y el puerto dice que no
-------------------------------------------------
`PuertoRegistro` declara *«ninguna [operación] devuelve nada: es la ruta fría,
escribe y no decide»*, y `historial_de()` y `hilo_de()` **sí devuelven**. Se
escriben aquí igual, y conviene que la decisión quede razonada y no como
descuido:

- **Tiene precedente en el árbol.** `AdaptadorPerfilPostgres.reconstruir_perfil()`
  hace exactamente lo mismo —lee y devuelve— sin que exista un puerto de
  lectura, y por el mismo motivo: quien consulta no es el dominio, es el borde
  HTTP, y `ADR-001` §7.2 no le exige pasar por un puerto del dominio para
  hablar con su propio almacén.
- **La frase del puerto describe la ESCRITURA**, que es lo que el filtro 12
  hace en ruta fría. `GET /api/historial` no es ruta fría ni pasa por la
  cadena: es una consulta del borde.
- **Y meterlas en `PuertoRegistro` sería peor**: obligaría al dominio a
  declarar formas de lectura que ningún filtro usa.

Lo que este adaptador NO decide
-----------------------------------
**No sella la marca temporal.** Transporta el `momento` que trae la entrada, y
`EntradaDeTurno.validar()` ya lo exige con zona horaria; si falta o no se lee,
esto no escribe. El `DEFAULT now()` del esquema es para inserciones manuales
por SQL, **no un respaldo de este camino**: una entrada mal construida que se
guardara con una marca que nadie decidió sería el modo mock silencioso de
`CONTEXTO-MAESTRO.md` §5.1 aplicado a un dato del que cuelga un plazo legal.

**No deriva el título de la conversación.** `T-06` lo sitúa en la respuesta del
API: aquí se devuelve el primer mensaje y un candidato matemático del hilo;
la ruta deriva su título y preserva las fórmulas completas.
Una columna de título obligaría a decidir quién la edita y a suprimirla también.


"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.conexion import conectar
from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.base_postgres import traducir_fallo

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

    from dominio.puertos.registro import EntradaDeTurno


# Candidato derivado para el título: primer planteamiento matemático, o primera
# intervención que no sea únicamente saludo/agradecimiento. Sólo presentación;
# el primer mensaje y el hilo literal se conservan, sin una columna editable.
MENSAJE_TITULABLE_SQL = """(array_agg(contenido ORDER BY
    CASE WHEN lower(contenido) ~ 'deriv|l[ií]mit|integral|[=^$]' THEN 0 ELSE 1 END, id)
    FILTER (WHERE autor = 'estudiante' AND btrim(contenido) <> ''
      AND lower(btrim(contenido)) !~ '^(hola|buenos días|buenas tardes|buenas noches|gracias|muchas gracias|ok|vale|sí|si|no)[[:space:]!¿¡?.,;]*$'))[1]"""


class AdaptadorHistorialPostgres:
    """`historial_turno` (`05-historial.sql`), una fila por voz."""

    def __init__(self, cadena_de_conexion: str) -> None:
        self._cadena = cadena_de_conexion

    @contextmanager
    def _transaccion(self) -> Iterator[Any]:
        """Conexión y transacción explícita, con los fallos ya traducidos.

        Dos cosas, y las dos las pide el hito R6:

        - **una transacción**, para que la auditoría de `hilo_de()` y su lectura
          se confirmen juntas o no se confirme ninguna;
        - **`traducir_fallo()`**, para que un almacén caído llegue a la ruta como
          `AlmacenNoDisponible` y no como una excepción cruda de Psycopg. Sin
          esto la ruta no podría distinguir «no responde» de «no hay filas», que
          es exactamente la confusión que producía el `except Exception: []`.

        La traducción conserva sólo el SQLSTATE: ver `base_postgres.py` sobre por
        qué el texto de PostgreSQL no puede viajar en un mensaje de error.
        """
        with traducir_fallo(), conectar(self._cadena) as cnx, cnx.transaction():
            yield cnx

    # -- escritura · RF-REG-01 ---------------------------------------------

    def abrir_estado_operativo(self, sujeto, conversacion):
        from adaptadores.salientes.registro.estado_conversacional import CheckpointConversacion

        return CheckpointConversacion(self._cadena, sujeto, conversacion)

    def registrar_turno(self, entrada: EntradaDeTurno) -> None:
        """`RF-REG-01`. Persiste UNA voz del turno, tal como ocurrió.

        Valida antes de tocar la base, igual que el filtro 12 hace con
        `RegistroDeTurno`: los `CHECK` del esquema atraparían lo mismo, pero
        como `violates check constraint`, que dice dónde reventó y no qué
        falta. Y la ruta fría se traga las excepciones, así que un mensaje
        ilegible sería un mensaje perdido.
        """
        fallos = entrada.validar()
        if fallos:
            raise ValueError("entrada de turno no admisible: " + "; ".join(fallos))

        with conectar(self._cadena) as cnx, cnx.cursor() as cur:
            # Sin `ON CONFLICT`: es historial, no índice (`ADR-004` C1). Y
            # `turno` no es único aquí — dos filas lo comparten, una por voz.
            #
            # `PM-B25`: las tres tablas van en UNA transacción. Un mensaje sin
            # sus citas mostraría `{{c1}}` crudo, y un mensaje sin sus bloques
            # no diría qué se verificó — guardar la mitad sería peor que no
            # guardar, porque parecería completo.
            cur.execute(
                """
                INSERT INTO historial_turno (
                    turno, identificador_sesion, identificador_sujeto,
                    momento, autor, contenido, degradado,
                    nivel, procedencia_origen, procedencia_referencia,
                    consentimiento_evento, contexto_de_uso
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    entrada.turno,
                    entrada.identificador_sesion,
                    entrada.identificador_sujeto,
                    entrada.momento,
                    entrada.autor,
                    entrada.contenido,
                    entrada.degradado,
                    entrada.nivel,
                    entrada.procedencia_origen,
                    entrada.procedencia_referencia,
                    # `EQ-016`, hito B3 · bajo qué autorización se recogió esto.
                    # `None` en un despliegue sin migración 12 es «no consta»,
                    # que es la verdad; no se inventa un vínculo.
                    entrada.consentimiento_evento,
                    # `EQ-031` · para qué se usó el tutor. Se escribe como
                    # llegó del borde; esta fila no vuelve a preguntar por el
                    # rol de nadie, y por eso un rol revocado no reclasifica
                    # conversaciones de hace un semestre.
                    str(entrada.contexto_de_uso),
                ),
            )
            (mensaje,) = cur.fetchone()

            if entrada.bloques:
                cur.executemany(
                    """
                    INSERT INTO historial_bloque (
                        historial, orden, tipo, contenido, sello, alternativo
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (mensaje, orden, b.tipo, b.contenido, b.sello, b.alternativo or None)
                        for orden, b in enumerate(entrada.bloques)
                    ],
                )
            if entrada.citas:
                cur.executemany(
                    """
                    INSERT INTO historial_cita (historial, marca, expresion)
                    VALUES (%s, %s, %s)
                    """,
                    [(mensaje, c.marca, c.expresion) for c in entrada.citas],
                )
            if entrada.material:
                # Fase 5 · en la MISMA transacción que las otras tres tablas, y
                # por el mismo motivo que `PM-B25` dio para bloques y citas: un
                # mensaje que dice «Material del curso» y no tiene su material
                # parecería completo y no lo estaría.
                cur.executemany(
                    """
                    INSERT INTO historial_material (
                        historial, orden, fragmento, obra, relacion, similitud
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (mensaje, m.orden, m.fragmento, m.obra, m.relacion, m.similitud)
                        for m in entrada.material
                    ],
                )
            if entrada.conceptos:
                cur.executemany(
                    """
                    INSERT INTO historial_concepto (historial, orden, concepto)
                    VALUES (%s, %s, %s)
                    """,
                    [
                        (mensaje, orden, concepto)
                        for orden, concepto in enumerate(entrada.conceptos)
                    ],
                )
            cnx.commit()

    # -- supresión · RD-22 · nace junto con la escritura --------------------

    #: Las columnas por las que se puede borrar, además del sujeto. **Lista
    #: blanca**, igual que en `archivo.py`: la columna entra en el SQL por
    #: interpolación —no puede ir como parámetro— y aceptar cualquier nombre
    #: sería una inyección con los pasos ya puestos.
    _CLAVES_DE_BORRADO = ("identificador_sesion",)

    def _borrar_del_sujeto(self, identificador_sujeto: str, columna: str = "", valor: str = "") -> int:
        """El **único** borrado de este adaptador · `A2`, aplicado aquí.

        El sujeto va **siempre** en el `WHERE`, y las demás claves solo
        restringen dentro de lo suyo. No es un detalle de estilo: sin eso,
        `DELETE /api/historial/{sesion}` con una sesión ajena borraría la
        conversación de otra persona, y eso no es un fallo de privacidad, es
        una pérdida de datos de un tercero.

        Dos claves, un camino, por el mismo motivo que `archivo.py`: dos copias
        de la misma secuencia acaban discrepando, y aquí discrepar significa
        que una de las dos deja historial de un titular que pidió su supresión.
        """
        condiciones = ["identificador_sujeto = %s"]
        parametros = [identificador_sujeto]
        if columna:
            if columna not in self._CLAVES_DE_BORRADO:
                raise ValueError(f"columna de borrado no permitida: «{columna}»")
            condiciones.append(f"{columna} = %s")
            parametros.append(valor)

        with conectar(self._cadena) as cnx, cnx.cursor() as cur:
            cur.execute(
                "DELETE FROM historial_turno WHERE " + " AND ".join(condiciones),  # noqa: S608
                tuple(parametros),
            )
            borradas = cur.rowcount
            cur.execute(
                "DELETE FROM tutor_estado_conversacion WHERE sujeto=%s" +
                (" AND conversacion=%s" if columna == "identificador_sesion" else ""),
                (identificador_sujeto, valor) if columna == "identificador_sesion" else (identificador_sujeto,),
            )
            cnx.commit()
        return borradas

    def suprimir_sesion(self, identificador_sesion: str, identificador_sujeto: str) -> int:
        """Una conversación concreta, **solo si es de este titular**.

        ⚠️ **No es la vía de `RD-22`**, que se ejerce por sujeto: esto es
        «borra esta conversación», que es una operación distinta y la que
        `DELETE /api/historial/{sesion}` sirve. Comparte camino con la de
        sujeto, así que no puede divergir de ella.

        El sujeto no es opcional. Una firma que lo dejara fuera invitaría a
        llamarla sin él desde una ruta, y ese es exactamente el descuido que
        convierte un borrado en una pérdida de datos ajena.
        """
        return self._borrar_del_sujeto(
            identificador_sujeto, "identificador_sesion", identificador_sesion
        )

    def suprimir_sujeto(self, identificador_sujeto: str) -> int:
        """`RD-22`. Borra **todo** el historial de un titular.

        Va en el mismo archivo y el mismo commit que `registrar_turno()` a
        propósito: `registro_turno` pudo escribir durante meses sin que nada
        supiera borrarlo, y de ahí salió `A2`. Una superficie nueva de dato
        personal nace cubierta o no nace.

        Devuelve cuántas **filas** —no turnos— se borraron: son dos por turno,
        y decir «turnos» aquí haría que el recibo de `L-07` no cuadrara con lo
        que se cuenta en la base.
        """
        return self._borrar_del_sujeto(identificador_sujeto)

    # -- lectura · del borde, no del dominio · ver la cabecera --------------

    def historial_de(self, identificador_sujeto: str) -> list[dict]:
        """Las conversaciones de un titular, de la más reciente hacia atrás.

        Agrupa por sesión y **cuenta turnos, no filas**: `count(DISTINCT turno)`
        y no `count(*)`, que daría el doble por las dos voces. Es la clase de
        cifra que se publica en una pantalla, así que equivocarla se ve.

        Devuelve `primer_mensaje` en crudo; recortarlo para el título es de la
        ruta (`T-06`).
        """
        with self._transaccion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"""
                SELECT identificador_sesion,
                       min(momento)          AS inicio,
                       max(momento)          AS ultimo,
                       count(DISTINCT turno) AS turnos,
                       (array_agg(contenido ORDER BY id)
                          FILTER (WHERE autor = 'estudiante'))[1] AS primer_mensaje,
                       {MENSAJE_TITULABLE_SQL} AS mensaje_para_titulo
                  FROM historial_turno
                 WHERE identificador_sujeto = %s
              GROUP BY identificador_sesion
              ORDER BY max(momento) DESC
                """,
                (identificador_sujeto,),
            )
            filas = cur.fetchall()
        return [
            {
                "sesion": fila[0],
                "inicio": fila[1],
                "ultimo": fila[2],
                "turnos": fila[3],
                "primer_mensaje": fila[4] or "",
                "mensaje_para_titulo": fila[5] or fila[4] or "",
            }
            for fila in filas
        ]

    def hilo_de(
        self,
        identificador_sesion: str,
        identificador_sujeto: str,
        *,
        actor: str = "",
        operacion: str = "conversacion.consultada",
    ) -> list[dict]:
        """Un hilo completo, en orden, **solo si es de este sujeto**.

        El sujeto va en el `WHERE` y no se comprueba después: así una sesión
        ajena devuelve lista vacía y la ruta responde `404` **sin haber leído
        nada de otro titular**. Comprobarlo en Python exigiría traérselo
        primero, que es justo lo que `B3` del encargo evita.

        Orden por `id` y no por `momento`: las dos voces de un turno pueden
        compartir marca temporal al milisegundo, y `id` es lo que desempata.

        ⚠️ **`actor` audita la consulta dentro de la misma transacción**
        (`EQ-023`, hito R5). Se anota **antes** del `SELECT`: si la auditoría
        falla, la transacción se deshace y no se devuelve nada, de modo que no
        puede existir una lectura de conversación sin constancia de quién la
        hizo. Al revés, el hilo ya habría salido y el registro faltaría.

        Sólo se registra **qué** conversación, nunca su contenido: la auditoría
        vive más que lo que audita.

        `actor` vacío no audita, y es para el único consumidor que no es una
        consulta de nadie: `contexto_retomado()` en `rutas/turno.py` lo pasa
        lleno igual, así que hoy no hay ninguno. Se conserva el valor por
        defecto para que un despliegue sin la migración 12 —donde
        `auditoria_operacion` no existe— pueda seguir leyendo su historial en
        vez de quedarse sin ninguna vía.
        """
        with self._transaccion() as cnx, cnx.cursor() as cur:
            if actor:
                anotar(
                    cur,
                    operacion,
                    actor=actor,
                    sujeto_afectado=identificador_sujeto,
                    # Identificador y nada más. Ver la cabecera de `auditoria_sql`.
                    detalle={"conversacion": identificador_sesion},
                )
            return self._hilo_de_cursor(
                cur, "h.identificador_sesion = %s AND h.identificador_sujeto = %s",
                (identificador_sesion, identificador_sujeto),
            )

    def _hilo_de_cursor(self, cur, condicion, valores):
        """Hidrata sólo las filas autorizadas por el llamador, en su transacción."""
        cur.execute(
            f"""
            SELECT id, turno, momento, autor, contenido, degradado,
                   nivel, procedencia_origen, procedencia_referencia
              FROM historial_turno h
             WHERE {condicion}
          ORDER BY id
            """,
            valores,
        )
        filas = cur.fetchall()
        if not filas:
            return []

        # `PM-B25` · los bloques y las citas, en DOS consultas y no en dos
        # por mensaje: un hilo de veinte turnos haría cuarenta viajes a la
        # base para pintar una pantalla. Se traen de una y se reparten aquí.
        mensajes = [f[0] for f in filas]
        cur.execute(
            """
            SELECT historial, tipo, contenido, sello, alternativo
              FROM historial_bloque
             WHERE historial = ANY(%s)
          ORDER BY historial, orden
            """,
            (mensajes,),
        )
        bloques: dict[int, list[dict]] = {}
        for h, tipo, contenido, sello, alternativo in cur.fetchall():
            bloques.setdefault(h, []).append(
                {
                    "tipo": tipo,
                    "contenido": contenido,
                    "sello": sello,
                    "alternativo": alternativo or "",
                }
            )
        cur.execute(
            """
            SELECT historial, marca, expresion
              FROM historial_cita
             WHERE historial = ANY(%s)
          ORDER BY historial, marca
            """,
            (mensajes,),
        )
        citas: dict[int, list[dict]] = {}
        for h, marca, expresion in cur.fetchall():
            citas.setdefault(h, []).append({"marca": marca, "expresion": expresion})

        # Fase 5 · el material, en una sola consulta como las dos de arriba.
        #
        # ⚠️ Un despliegue sin la migración 15 no tiene esta tabla, y el
        # historial tiene que seguir leyéndose: es el mismo criterio con el
        # que `consentimiento_evento` admite `None` en un despliegue sin la
        # 12. Sin la tabla, `material` sale vacío y el lector cae a
        # `procedencia_referencia`, que es lo que esas filas sí tienen.
        material = _material_de(cur, mensajes)

        return [
            {
                "turno": fila[1],
                "momento": fila[2],
                "autor": fila[3],
                "contenido": fila[4],
                "degradado": fila[5],
                "nivel": fila[6],
                "procedencia": {"origen": fila[7], "referencia": fila[8]},
                "bloques": bloques.get(fila[0], []),
                "citas": citas.get(fila[0], []),
                # Fase 5 · el material con su orden y su relación. Lista vacía
                # en las filas anteriores a la migración 15: a ésas no se les
                # inventa un orden, y quien lee cae a `procedencia.referencia`.
                "material": material.get(fila[0], []),
            }
            for fila in filas
        ]


def _material_de(cur, mensajes: list[int]) -> dict[int, list[dict]]:
    """El material de cada mensaje · Fase 5 · paquete 5B.

    ⚠️ **Se pregunta si la tabla existe en vez de intentar leerla y capturar.**

    No es estilo. La lectura del hilo ocurre dentro de una transacción que ya
    ha anotado la auditoría de `EQ-023` —quién consultó qué conversación—, y en
    PostgreSQL una sentencia fallida aborta la transacción entera: recuperarse
    con `rollback()` habría **borrado esa anotación** y devuelto el hilo igual.
    Es decir, una lectura de conversación sin constancia de quién la hizo, que
    es exactamente lo que el docstring de `conversacion()` promete que no puede
    ocurrir.

    `to_regclass` devuelve `NULL` si la tabla no existe y no falla, así que un
    despliegue sin la migración 15 lee su historial completo y sin material,
    que es la verdad de esas filas.
    """
    cur.execute("SELECT to_regclass('public.historial_material')")
    (existe,) = cur.fetchone()
    if existe is None:
        return {}

    cur.execute(
        """
        SELECT historial, fragmento, obra, relacion, similitud
          FROM historial_material
         WHERE historial = ANY(%s)
      ORDER BY historial, orden
        """,
        (mensajes,),
    )
    material: dict[int, list[dict]] = {}
    for h, fragmento, obra, relacion, similitud in cur.fetchall():
        material.setdefault(h, []).append(
            {
                "fragmento": fragmento,
                "obra": obra,
                "relacion": relacion,
                "similitud": float(similitud) if similitud is not None else None,
            }
        )
    return material
