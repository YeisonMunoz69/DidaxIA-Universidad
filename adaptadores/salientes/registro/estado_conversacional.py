"""Checkpoint de tarea con candado PostgreSQL hasta terminar el turno."""
import json

from adaptadores.salientes.conexion import conectar
from dominio.modelo.continuidad import nuevo


class CheckpointConversacion:
    def __init__(self, cadena, sujeto, conversacion):
        self.cnx = conectar(cadena)
        self.sujeto, self.conversacion = sujeto, conversacion
        self.guardado = False
        try:
            with self.cnx.cursor() as cur:
                cur.execute("SET LOCAL lock_timeout = '5s'")
                cur.execute("SET LOCAL statement_timeout = '8s'")
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (sujeto + ':' + conversacion,))
                cur.execute("SELECT revision, estado FROM tutor_estado_conversacion WHERE sujeto=%s AND conversacion=%s", (sujeto, conversacion))
                fila = cur.fetchone()
                self.revision, self.estado = fila if fila else (0, nuevo())
        except BaseException:
            self.cnx.close()
            raise

    def recordar_respuesta(self, estado, clave, huella, lineas):
        if clave:
            recordadas = estado.setdefault("reintentos", {})
            recordadas[clave] = {"huella": huella, "lineas": [linea.decode("utf-8") for linea in lineas]}
            while len(recordadas) > 8:
                recordadas.pop(next(iter(recordadas)))

    def respuesta_recordada(self, clave, huella):
        recordada = self.estado.get("reintentos", {}).get(clave) if clave else None
        if recordada is None:
            return None
        if recordada["huella"] != huella:
            raise ValueError("clave de reintento reutilizada con otro mensaje")
        return tuple(linea.encode("utf-8") for linea in recordada["lineas"])

    def guardar(self, estado):
        with self.cnx.cursor() as cur:
            cur.execute("""
                INSERT INTO tutor_estado_conversacion(sujeto,conversacion,revision,estado)
                VALUES (%s,%s,%s,%s::jsonb)
                ON CONFLICT (sujeto,conversacion) DO UPDATE
                SET revision=EXCLUDED.revision, estado=EXCLUDED.estado, actualizada_en=now()
                WHERE tutor_estado_conversacion.revision=%s
                RETURNING revision
            """, (self.sujeto, self.conversacion, self.revision + 1,
                  json.dumps(estado, ensure_ascii=False), self.revision))
            if cur.fetchone() is None:
                raise ValueError("la revisión de la conversación cambió")
        self.cnx.commit()
        self.guardado = True

    def cerrar(self):
        self.cnx.close()
