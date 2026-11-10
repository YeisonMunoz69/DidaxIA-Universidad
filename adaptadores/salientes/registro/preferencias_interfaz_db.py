from psycopg.types.json import Jsonb

from adaptadores.salientes.registro.base_postgres import RepositorioPostgres, exigir_persona_activa
from dominio.modelo.preferencias_interfaz import RevisionDesactualizada, validar_cambios


class PreferenciasInterfazPostgres(RepositorioPostgres):
    def consultar(self, sujeto):
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute("SELECT preferencias, revision FROM preferencia_interfaz WHERE sujeto_google=%s", (sujeto,))
            fila = cur.fetchone()
        return {"preferencias": fila[0] if fila else None, "revision": fila[1] if fila else 0}

    def guardar(self, sujeto, cambios, revision):
        cambios = validar_cambios(cambios)
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona_activa(cur, sujeto)
            cur.execute("INSERT INTO preferencia_interfaz(sujeto_google, preferencias) VALUES (%s, '{}'::jsonb) ON CONFLICT DO NOTHING", (sujeto,))
            cur.execute("UPDATE preferencia_interfaz SET preferencias=preferencias || %s, revision=revision+1, actualizado_en=now() WHERE sujeto_google=%s AND revision=%s RETURNING preferencias,revision", (Jsonb(cambios), sujeto, revision))
            fila = cur.fetchone()
            if fila is None:
                raise RevisionDesactualizada("otra selección fue guardada antes")
        return {"preferencias": fila[0], "revision": fila[1]}
