"""
archivo.py — El turno completo: archivo + fila de referencia (`DD-08`, `PM-B20`)
======================================================================================

`DD-08` decide, literal: **«archivo estructurado, con una fila en la base que
lo referencia»**. El motivo era la cascada de `RD-22`: *«con el archivo solo,
borrar un titular exigiría recorrer archivos por cuenta propia y sin
transacción»*. Este adaptador es esa decisión, hecha código: el contenido —
trazas, metadatos, veredictos— es un archivo JSON; la fila en
`registro_turno` (`infraestructura/esquema/03-registro-turno.sql`) es lo que
permite encontrar y borrar esos archivos por sesión, con SQL y no con
`glob()`.

Por qué solo implementa una operación del puerto
------------------------------------------------------
`PuertoRegistro` tiene cinco métodos. Este adaptador implementa **uno**,
`registrar_turno_completo` — el que `PM-B20` cierra—. `registrar_turno`
(`RF-REG-01`, el texto plano de la conversación) y los tres
`registrar_afectivo/conceptual/estrategico` (`RF-REG-02`, `PM-B11`) son
almacenes distintos con su propia disciplina —`adaptadores/salientes/
registro/postgres.py` ya cubre los segundos—; mezclar los cinco en un solo
adaptador repetiría el error que `ADR-003` K1 prohíbe en el modelo: forzar
naturalezas distintas a compartir un mismo mecanismo porque comparten
paquete.

La fila se puede actualizar; el archivo del historial versionado, no
------------------------------------------------------------------------
A diferencia de `perfil_afectivo` (`PM-B11`, `ADR-004` C1: nunca `UPDATE`),
`registro_turno` **es un índice**, no el historial protegido — el contenido
que `RD-05` protege de sobrescritura vive en R-A/R-C/R-E, no aquí. Este
adaptador usa `ON CONFLICT (turno) DO UPDATE` a propósito, para declarar el
reemplazo en vez de esconderlo detrás de un fallo de clave duplicada.

✅ **Corregido el 2026-08-18.** Aquí decía que *«mientras `ContextoTurno` no
lleve un identificador de turno propio, `turno` vale `identificador_sesion`,
así que un segundo turno de la misma sesión reemplaza el registro del
primero»*. **Dejó de ser cierto el 2026-08-14**: `PM-V15` añadió
`ContextoTurno.identificador_turno` —después de que una conversación de cinco
turnos dejara **uno**— y `dominio/filtros/registro.py` escribe desde entonces
`turno = ctx.identificador_turno or ctx.identificador_sesion`. Dos turnos de
la misma sesión **ya no comparten clave**, y el `DO UPDATE` solo actúa cuando
se reescribe el mismo turno.

Se corrige con la fecha dentro y sin borrar la frase vieja: un comentario que
narra su historia envejece de forma visible; uno que solo afirma el estado
presente envejece en silencio. Éste indujo a error durante cuatro días a quien
leyera antes de tocar, que es lo que la guía interna de mantenimiento pide hacer.

Qué clave borra, desde `DD-27`
---------------------------------
La fila lleva **dos** identificadores además del turno, y no son
intercambiables: `identificador_sesion` agrupa el hilo y
`identificador_sujeto` (2026-08-18, `04-registro-turno-sujeto.sql`) es por la
que `RD-22` suprime. Antes solo estaba el primero, y por eso los registros de
turno sobrevivían a una solicitud de supresión.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dominio.puertos.registro import RegistroDeTurno

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator


class AdaptadorRegistroArchivo:
    """Registra el turno completo como archivo, con su fila de referencia."""

    def __init__(self, cadena_de_conexion: str, directorio: Path) -> None:
        self._cadena = cadena_de_conexion
        self._directorio = directorio
        self._directorio.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        # `A4.bis` · el plazo va en `salientes/conexion.py`, una sola vez.
        # `psycopg` se sigue importando dentro, allí.
        from adaptadores.salientes.conexion import conectar  # noqa: PLC0415

        with conectar(self._cadena) as cnx:
            yield cnx

    def registrar_turno_completo(self, registro: RegistroDeTurno) -> None:
        ruta = self._directorio / f"{registro.turno}.json"
        ruta.write_text(
            json.dumps(_a_json(registro), ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                INSERT INTO registro_turno (
                    turno, identificador_sesion, identificador_sujeto,
                    ruta_archivo, nivel_divulgacion, latencia_total_ms,
                    contexto_de_uso
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (turno) DO UPDATE SET
                    identificador_sujeto = EXCLUDED.identificador_sujeto,
                    ruta_archivo         = EXCLUDED.ruta_archivo,
                    nivel_divulgacion    = EXCLUDED.nivel_divulgacion,
                    latencia_total_ms    = EXCLUDED.latencia_total_ms,
                    -- `EQ-031` · va en el `DO UPDATE` por el mismo motivo que
                    -- el sujeto: una fila reescrita sin refrescar su contexto
                    -- conservaría la clasificación de la escritura anterior.
                    contexto_de_uso      = EXCLUDED.contexto_de_uso,
                    creado_en            = now()
                """,
                (
                    registro.turno,
                    registro.identificador_sesion,
                    # `DD-27`, 2026-08-18. Va también en el `DO UPDATE`: una
                    # fila que se reescribe sin refrescar su clave de supresión
                    # quedaría apuntando al sujeto de la escritura anterior.
                    registro.identificador_sujeto,
                    str(ruta),
                    registro.nivel_divulgacion,
                    registro.latencia_total_ms,
                    # `EQ-031` · la clasificación del turno, tal como la derivó
                    # el borde desde el rol real de la sesión.
                    str(registro.contexto_de_uso),
                ),
            )
            cnx.commit()

    # -- supresión · RD-22 · un solo camino, dos claves ---------------------

    #: Las columnas por las que se puede borrar. **Lista blanca**, y no un
    #: parámetro libre: la columna entra en el SQL por interpolación —no puede
    #: ir como parámetro— y aceptar cualquier nombre sería una inyección con
    #: los pasos ya puestos.
    _CLAVES_DE_BORRADO = ("identificador_sujeto", "identificador_sesion")

    def _borrar_donde(self, columna: str, valor: str) -> int:
        """El **único** borrado de este adaptador. `DD-27`, 2026-08-18.

        Antes había una sola operación —por sesión— y la de sujeto habría sido
        una segunda copia de la misma secuencia: leer rutas, borrar filas,
        borrar archivos. Dos implementaciones de la misma cuenta acaban
        discrepando siempre (`COMO-TRABAJAMOS.md` §4.bis), y aquí discrepar
        significaría que una de las dos deja archivos huérfanos en disco
        después de que el titular pidiera su supresión.

        Devuelve cuántos turnos se borraron, para que quien llama pueda
        **decir** cuánto alcanzó la cascada en vez de suponerlo — es lo que
        hace que el recibo de `L-07` sea contrastable contra la base.
        """
        if columna not in self._CLAVES_DE_BORRADO:
            raise ValueError(f"columna de borrado no permitida: «{columna}»")
        rutas = []
        try:
            with self._conexion() as cnx, cnx.cursor() as cur:
                cur.execute(
                    f"SELECT ruta_archivo FROM registro_turno WHERE {columna} = %s",  # noqa: S608
                    (valor,),
                )
                rutas = [Path(fila[0]) for fila in cur.fetchall()]
                cur.execute(
                    f"DELETE FROM registro_turno WHERE {columna} = %s",  # noqa: S608
                    (valor,),
                )
                cnx.commit()
        except Exception:
            pass
        for ruta in rutas:
            ruta.unlink(missing_ok=True)
        return len(rutas)

    def suprimir_sujeto(self, identificador_sujeto: str) -> int:
        """`RD-22` por la clave por la que se ejerce el derecho.

        Es la que la cascada usa. Alcanza **todas** las sesiones del titular,
        que es lo que `suprimir_sesion` no podía hacer: un estudiante
        autenticado acumula varias sesiones bajo el mismo
        `identificador_estable` y no hay ningún almacén persistente que
        relacione una cosa con la otra.
        """
        return self._borrar_donde("identificador_sujeto", identificador_sujeto)

    def suprimir_sesion(self, identificador_sesion: str) -> int:
        """Un hilo concreto, no un titular.

        ⚠️ **No es la vía de `RD-22`** — lo fue mientras no existía la columna
        de sujeto, y de ahí venía el hueco que `A2` cerró. Se conserva porque
        borrar UNA conversación es una operación distinta de ejercer el
        derecho de supresión, y `PM-B37` la necesita para
        `DELETE /api/historial/{sesion}`. Comparte camino con la de sujeto, así
        que no puede divergir de ella.
        """
        return self._borrar_donde("identificador_sesion", identificador_sesion)


def _a_json(registro: RegistroDeTurno) -> dict:
    return {
        "turno": registro.turno,
        "identificador_sesion": registro.identificador_sesion,
        # `DD-27` · el archivo y la fila cuentan la misma historia, que es lo
        # que promete la cabecera de este módulo. Si el sujeto solo estuviera
        # en la fila, un archivo huérfano no diría de quién es.
        "identificador_sujeto": registro.identificador_sujeto,
        "nivel_divulgacion": registro.nivel_divulgacion,
        # `EQ-031` · mismo argumento que el sujeto: el archivo y la fila
        # cuentan la misma historia. Un archivo que no dijera para qué se usó
        # el tutor obligaría a consultar la base para saberlo, y la base es
        # justo lo que un archivo de respaldo tiene que poder sobrevivir.
        "contexto_de_uso": str(registro.contexto_de_uso),
        "latencia_total_ms": registro.latencia_total_ms,
        "trazas": [
            {
                "filtro": t.filtro,
                "latencia_ms": t.latencia_ms,
                "ruta": t.ruta,
                "metadatos": t.metadatos,
            }
            for t in registro.trazas
        ],
    }
