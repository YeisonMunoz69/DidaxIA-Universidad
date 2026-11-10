"""
version.py — Qué versión del corpus respondió un turno
=======================================================

El encargo de la Fase 8 pide medir *«versión de corpus utilizada»* y *«cambios
en recuperación después de actualizar el corpus»*. Hasta hoy no había de dónde
sacarlo: el corpus no lleva número de versión en ninguna parte, y ninguna tabla
lo registraba.

De dónde sale la versión, y por qué ésta y no otra
-----------------------------------------------------------
De `fragmento`, que la migración 01 creó con una columna `cargado_en`. La huella
es **cuántos fragmentos hay indexados y cuándo entró el más reciente**:

    248@20260906T142211Z

Es verificable —cualquiera puede reproducirla con un `SELECT`—, cambia cuando y
sólo cuando el corpus se reingiere, y no inventa un número de versión que nadie
mantiene. Un identificador semántico como «corpus v3» habría exigido que alguien
lo subiera a mano, y el día que se olvidara la serie diría que no cambió nada.

⚠️ **No es una versión semántica y no se pretende que lo sea.** Dos ingestas que
carguen los mismos 248 fragmentos con contenido distinto darían huellas
distintas —cambia `cargado_en`—, lo cual es correcto; pero dos cortes con el
mismo recuento y la misma marca serían indistinguibles, lo cual sólo puede pasar
si no hubo reingesta. Se declara el límite en vez de descubrirlo.

Por qué no lleva caché
--------------------------------
Porque el corpus son ~250 filas y el agregado es inmediato, mientras que una
caché con tiempo de vida introduce un estado que puede mentir: durante su
ventana, los turnos posteriores a una reingesta quedarían atribuidos a la
versión anterior, y ese error es exactamente el que el indicador «cambios en
recuperación tras actualizar el corpus» no puede permitirse. Si algún día el
corpus creciera hasta que la consulta pese, se añade la caché **y** una
invalidación explícita en la ingesta; no antes.


"""

from __future__ import annotations

from adaptadores.salientes.registro.base_postgres import RepositorioPostgres

#: Cuando no hay ni un fragmento indexado. Cadena vacía y no «0@», porque el
#: catálogo trata la cadena vacía como «no consta» y un recuento de cero no
#: identifica ninguna versión: identifica la ausencia de corpus.
SIN_CORPUS = ""


class VersionDelCorpusPostgres(RepositorioPostgres):
    """La huella del corpus indexado ahora mismo."""

    def actual(self) -> str:
        """`<fragmentos>@<ISO básico UTC del más reciente>`, o cadena vacía.

        Devuelve UTC y con formato básico —sin guiones ni dos puntos— porque el
        valor viaja como metadato de telemetría, y `PATRON_REFERENCIA` no admite
        el `+` de un desplazamiento horario. El instante sigue siendo inequívoco:
        la `Z` lo dice.
        """
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute("SELECT count(*), max(cargado_en) FROM fragmento")
            fila = cur.fetchone()
        if fila is None:
            return SIN_CORPUS
        cantidad, mas_reciente = fila
        if not cantidad or mas_reciente is None:
            return SIN_CORPUS
        from datetime import UTC  # noqa: PLC0415 — sólo para formatear la salida

        marca = mas_reciente.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"{int(cantidad)}@{marca}"
