from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import DOCENTE_VIGENTE_SQL
from adaptadores.salientes.registro.base_postgres import FILTRO_PERSONA_SIN_SUPRESION_SQL
from dominio.modelo.recursos import RecursoInvalido


def validar_destinos(clases, audiencia):
    if (not isinstance(clases, list) or not clases or len(clases) > 100
            or any(not isinstance(c, str) or not c or len(c) > 250 for c in clases)):
        raise RecursoInvalido('Selecciona entre uno y 100 destinatarios vÃ¡lidos.')
    if audiencia not in ('estudiantes', 'docentes', 'individuales'):
        raise RecursoInvalido('Selecciona cursos, estudiantes concretos o docentes.')
    return sorted(set(clases))

def comprobar_destinos(cur, destinos, audiencia):
    if audiencia == 'estudiantes':
        cur.execute('SELECT id FROM clase WHERE id=ANY(%s) AND archivada_en IS NULL FOR SHARE', (destinos,))
    elif audiencia == 'individuales':
        cur.execute('SELECT p.sujeto_google FROM persona p WHERE p.sujeto_google=ANY(%s) AND EXISTS '
                    '(SELECT 1 FROM clase_matricula m JOIN clase c ON c.id=m.clase '
                    'WHERE m.identificador=p.sujeto_google AND c.archivada_en IS NULL) '
                    f'AND {FILTRO_PERSONA_SIN_SUPRESION_SQL} FOR SHARE', (destinos,))
    else:
        cur.execute("SELECT p.sujeto_google FROM persona p WHERE p.sujeto_google=ANY(%s) AND "
                    "(EXISTS (SELECT 1 FROM clase c WHERE c.creador=p.sujeto_google AND c.archivada_en IS NULL) OR "
                    f"{DOCENTE_VIGENTE_SQL} OR EXISTS (SELECT 1 FROM solicitud_docente s WHERE s.correo=p.correo AND s.estado='aprobada')) FOR SHARE", (destinos,))
    if {f[0] for f in cur.fetchall()} != set(destinos):
        raise RecursoInvalido('Hay destinatarios inexistentes, archivados o no disponibles. No se aplicÃ³ ningÃºn cambio.')

class DestinatariosRecursos:
    def estudiantes_destinatarios(self, actor):
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)
            cur.execute("SELECT p.sujeto_google,coalesce(nullif(p.nombre,''),'Estudiante'),p.correo,"
                        "string_agg(DISTINCT c.nombre,' Â· ' ORDER BY c.nombre) FROM persona p "
                        'JOIN clase_matricula m ON m.identificador=p.sujeto_google '
                        'JOIN clase c ON c.id=m.clase WHERE c.archivada_en IS NULL '
                        f'AND {FILTRO_PERSONA_SIN_SUPRESION_SQL} '
                        'GROUP BY p.sujeto_google,p.nombre,p.correo ORDER BY p.nombre,p.correo')
            return [dict(id=f[0], nombre=f[1], correo=f[2], curso=f[3]) for f in cur.fetchall()]

    def retirar_destinatarios(self, actor, identificador, publicaciones, revision, envio):
        from adaptadores.salientes.registro.recursos_db import RecursoConflicto

        publicaciones = validar_destinos(publicaciones, 'individuales')
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)
            r = self._recurso(cur, identificador)
            if r['tipo'] != 'encuesta' or r['estado'] != 'publicado' or r['revision'] != revision:
                raise RecursoConflicto('Recarga la encuesta: sÃ³lo se retiran destinatarios de la publicaciÃ³n activa.')
            cur.execute("SELECT coalesce(max(envio),0) FROM recurso_publicacion WHERE recurso=%s AND estado='publicado'", (identificador,))
            if type(envio) is not int or cur.fetchone()[0] != envio:
                raise RecursoConflicto('Recarga la encuesta: el envÃ­o activo cambiÃ³.')
            cur.execute('SELECT id,retirada_en FROM recurso_publicacion WHERE recurso=%s AND envio=%s '
                        'AND id=ANY(%s) FOR UPDATE', (identificador, envio, publicaciones))
            filas = cur.fetchall()
            if {f[0] for f in filas} != set(publicaciones):
                raise RecursoConflicto('AlgÃºn destinatario no pertenece a este envÃ­o.')
            cur.execute('SELECT 1 FROM recurso_respuesta WHERE publicacion=ANY(%s) LIMIT 1', (publicaciones,))
            if cur.fetchone():
                raise RecursoConflicto('No se puede retirar: el docente, estudiante o curso ya tiene respuestas. Se conservaron todos los destinatarios.')
            nuevos = [f[0] for f in filas if f[1] is None]
            if nuevos:
                cur.execute('UPDATE recurso_publicacion SET retirada_en=clock_timestamp() WHERE id=ANY(%s)', (nuevos,))
                anotar(cur, 'recurso.destinatarios_retirados', actor=actor,
                       detalle={'recurso': identificador, 'envio': envio, 'publicaciones': nuevos})
            return {'retirados': len(nuevos), 'envio': envio, 'revision': r['revision']}
