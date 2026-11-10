from __future__ import annotations

import secrets
from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import (
    DOCENTE_VIGENTE_SQL,
    exigir_investigador_administrador,
)
from adaptadores.salientes.registro.base_postgres import (
    RepositorioPostgres,
    bloquear_y_exigir_sin_supresion,
)
from adaptadores.salientes.registro.destinatarios_recursos import (
    DestinatariosRecursos,
    comprobar_destinos,
    validar_destinos,
)
from adaptadores.salientes.registro.estado_vigente_db import AdaptadorEstadoVigentePostgres
from dominio.modelo.acceso import AccesoCalculado, calcular_acceso
from dominio.modelo.recursos import RecursoInvalido, resultados, validar_recurso, validar_respuestas
from dominio.puertos.almacen import EscrituraRechazada


class RecursoNoEncontrado(LookupError):
    pass

class RecursoConflicto(ValueError):
    pass

def _id():
    return secrets.token_urlsafe(12)

class RecursosPostgres(DestinatariosRecursos, RepositorioPostgres):
    def _estudiante(self, cur, actor):
        bloquear_y_exigir_sin_supresion(cur, actor)
        estado = AdaptadorEstadoVigentePostgres(self._cadena).desde_cursor(cur, actor)
        if estado is None or calcular_acceso(estado) != AccesoCalculado.HABILITADO:
            raise EscrituraRechazada('La autorización del estudiante no está vigente.')

    def _investigador(self, cur, actor):
        bloquear_y_exigir_sin_supresion(cur, actor)
        exigir_investigador_administrador(cur, actor)

    def _recurso(self, cur, identificador, incluir_contenido=True):
        columna = 'contenido' if incluir_contenido else 'NULL AS contenido'
        cur.execute(f'SELECT id, autor, tipo, titulo, descripcion, {columna}, estado, revision, '
                    'creado_en, actualizado_en,es_plantilla FROM recurso_investigacion WHERE id=%s FOR UPDATE', (identificador,))
        fila = cur.fetchone()
        if not fila:
            raise RecursoNoEncontrado('Recurso no disponible.')
        r = dict(zip(('id', 'autor', 'tipo', 'titulo', 'descripcion', 'contenido', 'estado', 'revision',
                      'creado_en', 'actualizado_en','es_plantilla'), fila, strict=True))
        for k in ('creado_en', 'actualizado_en'):
            r[k] = r[k].isoformat()
        return r

    def clases(self, actor, rol):
        with self._conexion() as cnx, cnx.cursor() as cur:
            if rol == 'investigador':
                self._investigador(cur, actor)
            cur.execute('SELECT id,nombre FROM clase WHERE archivada_en IS NULL '
                        "AND (%s='investigador' OR creador=%s) ORDER BY nombre", (rol, actor))
            return [{'id': f[0], 'nombre': f[1]} for f in cur.fetchall()]

    def listar(self, actor, rol):
        with self._conexion() as cnx, cnx.cursor() as cur:
            if rol == 'investigador':
                self._investigador(cur, actor)
            cur.execute('SELECT r.id,r.tipo,r.titulo,r.descripcion,r.estado,r.revision,r.actualizado_en, '
                        "count(DISTINCT coalesce(p.clase,p.destinatario)) FILTER (WHERE p.retirada_en IS NULL),count(DISTINCT p.envio),coalesce(string_agg(DISTINCT p.audiencia,','),''), "
                        "(r.tipo='encuesta' OR NOT EXISTS (SELECT 1 FROM recurso_publicacion h JOIN recurso_visita v ON v.publicacion=h.id WHERE h.recurso=r.id)) "
                        'AND NOT EXISTS (SELECT 1 FROM recurso_publicacion h JOIN recurso_respuesta a ON a.publicacion=h.id WHERE h.recurso=r.id) '
                        'FROM recurso_investigacion r '
                        'LEFT JOIN recurso_publicacion p ON p.recurso=r.id '
                        'LEFT JOIN clase c ON c.id=p.clase '
                        "WHERE NOT r.es_plantilla AND (%s='investigador' OR ((c.creador=%s OR p.destinatario=%s) AND r.estado IN ('publicado','cerrado'))) "
                        'GROUP BY r.id ORDER BY r.actualizado_en DESC', (rol, actor, actor))
            return [dict(id=f[0], tipo=f[1], titulo=f[2], descripcion=f[3], estado=f[4], revision=f[5],
                         actualizado_en=f[6].isoformat(), cursos=f[7], envios=f[8], audiencia=f[9], puede_eliminar=f[10]) for f in cur.fetchall()]

    def consultar(self, actor, identificador):
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)
            return self._recurso(cur, identificador)

    def guardar(self, actor, cuerpo, identificador=None):
        limpio = validar_recurso(cuerpo)
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)
            if identificador:
                actual = self._recurso(cur, identificador)
                if actual['estado'] != 'borrador':
                    raise RecursoConflicto('El contenido publicado está congelado. Duplica el recurso para editarlo.')
                if cuerpo.get('revision') != actual['revision']:
                    raise RecursoConflicto('Otro investigador guardó cambios. Recarga el recurso antes de guardar.')
                cur.execute('UPDATE recurso_investigacion SET tipo=%s,titulo=%s,descripcion=%s,contenido=%s, '
                            'revision=revision+1,actualizado_en=now() WHERE id=%s',
                            (limpio['tipo'], limpio['titulo'], limpio['descripcion'], Jsonb(limpio['contenido']), identificador))
            else:
                identificador = _id()
                cur.execute('INSERT INTO recurso_investigacion(id,autor,tipo,titulo,descripcion,contenido) '
                            'VALUES (%s,%s,%s,%s,%s,%s)', (identificador, actor, limpio['tipo'], limpio['titulo'],
                                                        limpio['descripcion'], Jsonb(limpio['contenido'])))
            return self._recurso(cur, identificador)

    def duplicar(self, actor, identificador):
        r = self.consultar(actor, identificador)
        r['titulo'] = (r['titulo'][:240] + ' · copia')
        return self.guardar(actor, r)

    def docentes(self, actor):
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)
            cur.execute("SELECT p.sujeto_google,p.nombre FROM persona p WHERE "
                        "EXISTS (SELECT 1 FROM clase c WHERE c.creador=p.sujeto_google AND c.archivada_en IS NULL) OR "
                        f"{DOCENTE_VIGENTE_SQL} OR EXISTS (SELECT 1 FROM solicitud_docente s WHERE s.correo=p.correo AND s.estado='aprobada') ORDER BY p.nombre")
            return [dict(id=f[0], nombre=f[1] or 'Docente') for f in cur.fetchall()]

    def plantillas_personales(self, actor):
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)
            cur.execute('SELECT id,titulo,tipo,descripcion FROM recurso_investigacion WHERE es_plantilla ORDER BY actualizado_en DESC')
            return [dict(id='personal-' + f[0], titulo=f[1], tipo=f[2], descripcion=f[3], personalizada=True) for f in cur.fetchall()]

    def guardar_plantilla(self, actor, identificador):
        copia = self.duplicar(actor, identificador)
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)
            cur.execute('UPDATE recurso_investigacion SET es_plantilla=true WHERE id=%s', (copia['id'],))
            return self._recurso(cur, copia['id'])

    def publicar(self, actor, identificador, clases, revision, audiencia='estudiantes'):
        clases = validar_destinos(clases, audiencia)
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)
            r = self._recurso(cur, identificador)
            republicable = r['estado'] == 'cerrado'
            if (r['estado'] != 'borrador' and not republicable) or r['revision'] != revision:
                raise RecursoConflicto('Recarga el recurso: la publicación requiere la revisión vigente.')
            if r['es_plantilla']:
                raise RecursoConflicto('Crea una copia de la plantilla para publicarla.')
            validar_recurso(r, publicable=True)
            comprobar_destinos(cur, clases, audiencia)
            cur.execute('SELECT coalesce(max(envio),0)+1 FROM recurso_publicacion WHERE recurso=%s', (identificador,))
            envio = cur.fetchone()[0]
            for clase in clases:
                cur.execute('INSERT INTO recurso_publicacion(id,recurso,clase,destinatario,audiencia,envio,revision_aviso) '
                            'VALUES (%s,%s,%s,%s,%s,%s,%s)', (_id(), identificador,
                            clase if audiencia == 'estudiantes' else None, clase if audiencia in {'docentes', 'individuales'} else None,
                            audiencia, envio, r['revision'] + 1))
            cur.execute("UPDATE recurso_investigacion SET estado='publicado',revision=revision+1,actualizado_en=now() WHERE id=%s", (identificador,))
            anotar(cur, 'recurso.publicado', actor=actor, detalle={'recurso': identificador, 'clases': clases, 'envio': envio})
            return self._recurso(cur, identificador)

    def ampliar_cursos(self, actor, identificador, clases, revision, envio, audiencia='estudiantes'):
        clases = validar_destinos(clases, audiencia)
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)
            r = self._recurso(cur, identificador)
            if r['tipo'] != 'encuesta' or r['estado'] != 'publicado' or r['revision'] != revision:
                raise RecursoConflicto('Recarga la encuesta: sólo puedes ampliar una publicación vigente.')
            cur.execute("SELECT coalesce(clase,destinatario),envio,audiencia,revision_aviso,retirada_en FROM recurso_publicacion "
                        "WHERE recurso=%s AND estado='publicado' FOR UPDATE", (identificador,))
            actuales = cur.fetchall()
            if (not actuales or any(p[1] != envio or p[2] != audiencia for p in actuales)):
                raise RecursoConflicto('Recarga la encuesta: deben coincidir el envío abierto y sus destinatarios.')
            existentes = {p[0] for p in actuales if p[4] is None}
            nuevos = set(clases) - existentes
            if len(existentes | nuevos) > 100:
                raise RecursoInvalido('Un envío admite hasta 100 destinatarios.')
            comprobar_destinos(cur, sorted(nuevos), audiencia)
            for clase in sorted(nuevos):
                cur.execute('UPDATE recurso_publicacion SET retirada_en=NULL WHERE recurso=%s AND envio=%s '
                            'AND coalesce(clase,destinatario)=%s AND audiencia=%s AND retirada_en IS NOT NULL RETURNING id',
                            (identificador, envio, clase, audiencia))
                if cur.fetchone():
                    continue
                cur.execute('INSERT INTO recurso_publicacion(id,recurso,clase,destinatario,audiencia,envio,revision_aviso) '
                            'VALUES (%s,%s,%s,%s,%s,%s,%s)',
                            (_id(), identificador, clase if audiencia == 'estudiantes' else None,
                             clase if audiencia in {'docentes', 'individuales'} else None, audiencia, envio, actuales[0][3]))
            if nuevos:
                anotar(cur, 'recurso.cursos_ampliados', actor=actor,
                       detalle={'recurso': identificador, 'envio': envio, 'clases': sorted(nuevos), 'audiencia': audiencia})
            return {'recurso': identificador, 'envio': envio, 'revision': r['revision'],
                    'cursos_anadidos': len(nuevos) if audiencia == 'estudiantes' else 0,
                    'destinatarios_anadidos': len(nuevos), 'audiencia': audiencia}

    def cambiar_estado(self, actor, identificador, estado):
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)
            r = self._recurso(cur, identificador)
            if not isinstance(estado, str) or estado not in {'cerrado', 'archivado'} or (estado == 'cerrado' and r['estado'] != 'publicado'):
                raise RecursoConflicto('No se puede aplicar ese estado al recurso.')
            cur.execute('UPDATE recurso_investigacion SET estado=%s,revision=revision+1,actualizado_en=now() WHERE id=%s', (estado, identificador))
            cur.execute('UPDATE recurso_publicacion SET revision_aviso=%s,estado=%s WHERE recurso=%s '
                        "AND (estado='publicado' OR %s='archivado')",
                        (r['revision'] + 1, estado, identificador, estado))
            if estado == 'cerrado':
                cur.execute('UPDATE recurso_publicacion SET cerrada_en=now() WHERE recurso=%s AND cerrada_en IS NULL', (identificador,))
                cur.execute("UPDATE recurso_visita v SET gracia_hasta=now()+interval '8 minutes' "
                            'FROM recurso_publicacion p WHERE v.publicacion=p.id AND p.recurso=%s '
                            "AND p.cerrada_en=now() AND v.actividad_en>=now()-interval '2 minutes'", (identificador,))
            else:
                cur.execute('UPDATE recurso_visita v SET gracia_hasta=NULL FROM recurso_publicacion p '
                            'WHERE p.id=v.publicacion AND p.recurso=%s', (identificador,))
            anotar(cur, 'recurso.estado_actualizado', actor=actor, detalle={'recurso': identificador, 'estado': estado})
            return self._recurso(cur, identificador)

    def eliminar(self, actor, identificador):
        with self._conexion() as cnx, cnx.cursor() as cur:
            self._investigador(cur, actor)

            recurso = self._recurso(cur, identificador)
            cur.execute("SELECT (%s <> 'encuesta' AND EXISTS (SELECT 1 FROM recurso_publicacion p JOIN recurso_visita v ON v.publicacion=p.id WHERE p.recurso=%s)) "
                        'OR EXISTS (SELECT 1 FROM recurso_publicacion p JOIN recurso_respuesta a ON a.publicacion=p.id WHERE p.recurso=%s)',
                        (recurso['tipo'], identificador, identificador))
            if cur.fetchone()[0]:
                detalle = 'respuestas registradas' if recurso['tipo'] == 'encuesta' else 'visitas o respuestas registradas'
                raise RecursoConflicto(f'Este recurso tiene {detalle}. Sólo se puede archivar para conservar sus datos.')
            cur.execute('DELETE FROM recurso_investigacion WHERE id=%s', (identificador,))

    def bandeja(self, actor, rol='estudiante'):
        with self._conexion() as cnx, cnx.cursor() as cur:
            bloquear_y_exigir_sin_supresion(cur, actor)
            if rol == 'estudiante':
                self._estudiante(cur, actor)
            cur.execute("SELECT p.id,r.titulo,r.tipo,r.descripcion,p.estado,coalesce(c.nombre,CASE WHEN p.audiencia='individuales' THEN 'Selección individual' ELSE 'Para docentes' END),p.publicada_en, "
                        'v.primera_en IS NOT NULL,a.enviada_en IS NOT NULL, '
                        'coalesce(v.revision_vista,0)<p.revision_aviso,p.envio,p.audiencia FROM recurso_publicacion p '
                        'JOIN recurso_investigacion r ON r.id=p.recurso LEFT JOIN clase c ON c.id=p.clase '
                        'LEFT JOIN recurso_visita v ON v.publicacion=p.id AND v.sujeto_google=%s '
                        'LEFT JOIN recurso_respuesta a ON a.publicacion=p.id AND a.sujeto_google=%s '
                        "WHERE p.retirada_en IS NULL AND r.estado IN ('publicado','cerrado') AND ((%s='estudiante' AND p.audiencia='estudiantes' "
                        'AND c.archivada_en IS NULL AND EXISTS(SELECT 1 FROM clase_matricula m WHERE m.clase=c.id AND m.identificador=%s)) '
                        "OR (%s='estudiante' AND p.audiencia='individuales' AND p.destinatario=%s) OR (%s='docente' AND p.audiencia='docentes' AND p.destinatario=%s)) ORDER BY p.publicada_en DESC",
                        (actor, actor, rol, actor, rol, actor, rol, actor))
            return [dict(id=f[0], titulo=f[1], tipo=f[2], descripcion=f[3], estado=f[4], clase=f[5],
                         publicada_en=f[6].isoformat(), vista=f[7], respondida=f[8], nueva=f[9], envio=f[10], audiencia=f[11]) for f in cur.fetchall()]

    def _publicacion(self, cur, actor, rol, identificador, incluir_contenido=True):
        cur.execute('SELECT recurso FROM recurso_publicacion WHERE id=%s', (identificador,))
        fila = cur.fetchone()
        if not fila:
            raise RecursoNoEncontrado('Publicación no disponible.')
        r = self._recurso(cur, fila[0]) if incluir_contenido else self._recurso(cur, fila[0], incluir_contenido=False)

        cur.execute('SELECT recurso,clase,envio,revision_aviso,publicada_en,estado,audiencia,destinatario,cerrada_en,retirada_en FROM recurso_publicacion WHERE id=%s', (identificador,))
        fila = cur.fetchone()
        if not fila or fila[9] is not None:
            raise RecursoNoEncontrado('La invitación fue retirada de este envío.')
        if fila[6] == 'estudiantes':
            cur.execute('SELECT nombre,creador,archivada_en FROM clase WHERE id=%s FOR SHARE', (fila[1],))
            clase = cur.fetchone()
        else:
            clase = ('Selección individual' if fila[6] == 'individuales' else 'Para docentes', fila[7], None)
        if rol == 'investigador':
            self._investigador(cur, actor)
        elif rol == 'docente':
            if fila[6] == 'individuales' or clase[1] != actor or (fila[6] == 'docentes' and r['estado'] not in {'publicado','cerrado'}):
                raise RecursoNoEncontrado('Publicación no disponible.')
        elif rol == 'estudiante':
            if fila[6] == 'individuales':
                permitido = fila[7] == actor
            elif fila[6] == 'estudiantes':
                cur.execute('SELECT 1 FROM clase_matricula WHERE clase=%s AND identificador=%s FOR SHARE', (fila[1], actor))
                permitido = bool(cur.fetchone()) and not clase[2]
            else:
                permitido = False
            if not permitido or r['estado'] not in {'publicado', 'cerrado'}:
                raise RecursoNoEncontrado('Publicación no disponible.')
        else:
            raise RecursoNoEncontrado('Publicación no disponible.')
        if r['estado'] != 'archivado':
            r['estado'] = fila[5]
        return r, fila[1], clase[0], dict(envio=fila[2], revision_aviso=fila[3], publicada_en=fila[4].isoformat(),
                                        audiencia=fila[6], destinatario=fila[7], cerrada_en=fila[8].isoformat() if fila[8] else None,
                                        participante=(rol == 'estudiante' or (rol == 'docente' and fila[6] == 'docentes')))

    def abrir(self, actor, rol, identificador, visita=False, actividad=False, incluir_contenido=True):
        with self._conexion() as cnx, cnx.cursor() as cur:
            bloquear_y_exigir_sin_supresion(cur, actor)
            if rol == 'estudiante':
                self._estudiante(cur, actor)
            r, clase, nombre, publicacion = self._publicacion(cur, actor, rol, identificador, incluir_contenido)
            if visita and publicacion['participante']:
                cur.execute('INSERT INTO recurso_visita(publicacion,sujeto_google,revision_vista,actividad_en) VALUES (%s,%s,%s,now()) '
                            'ON CONFLICT (publicacion,sujeto_google) DO UPDATE SET ultima_en=now(), '
                            'revision_vista=EXCLUDED.revision_vista,aperturas=recurso_visita.aperturas+1,actividad_en=now()',
                            (identificador, actor, publicacion['revision_aviso']))
            if actividad and publicacion['participante'] and r['estado'] == 'publicado':
                cur.execute('UPDATE recurso_visita SET actividad_en=now() WHERE publicacion=%s AND sujeto_google=%s', (identificador, actor))
            cur.execute('SELECT gracia_hasta FROM recurso_visita WHERE publicacion=%s AND sujeto_google=%s', (identificador, actor))
            plazo = cur.fetchone()
            gracia = plazo[0] if plazo else None
            cur.execute('SELECT respuestas,enviada_en FROM recurso_respuesta WHERE publicacion=%s AND sujeto_google=%s', (identificador, actor))
            respuesta = cur.fetchone()
            anterior = None
            if not respuesta and publicacion['participante'] and r['tipo'] == 'encuesta':
                cur.execute('SELECT a.respuestas,p.envio FROM recurso_respuesta a JOIN recurso_publicacion p ON p.id=a.publicacion '
                            'WHERE p.recurso=%s AND p.envio<%s AND p.audiencia=%s AND a.sujeto_google=%s '
                            'ORDER BY p.envio DESC LIMIT 1', (r['id'], publicacion['envio'], publicacion['audiencia'], actor))
                previa = cur.fetchone()
                if previa:
                    anterior = dict(respuestas=previa[0], envio=previa[1])
            r.pop('autor')
            if not incluir_contenido:
                r.pop('contenido')
            elif rol != 'investigador' and r['tipo'] == 'diapositivas':
                for slide in r['contenido']['slides']:
                    slide.pop('note', None)
            contexto = None
            if publicacion['participante'] and r['tipo'] == 'encuesta':
                cur.execute('SELECT correo FROM persona WHERE sujeto_google=%s', (actor,))
                cuenta = cur.fetchone()
                contexto = dict(correo=cuenta[0], curso=nombre, audiencia=publicacion['audiencia'],
                                enviada_en=respuesta[1].isoformat() if respuesta else None)
            return dict(recurso=r, id=identificador, clase=clase, nombre_clase=nombre,
                        envio=publicacion['envio'], publicada_en=publicacion['publicada_en'],
                        audiencia=publicacion['audiencia'], participante=publicacion['participante'], cerrada_en=publicacion['cerrada_en'],
                        servidor_en=datetime.now(UTC).isoformat(), gracia_hasta=gracia.isoformat() if gracia else None,
                        respuesta_anterior=anterior, respuesta=respuesta[0] if respuesta else None, contexto=contexto)

    def responder(self, actor, identificador, respuestas, rol='estudiante'):
        with self._conexion() as cnx, cnx.cursor() as cur:
            bloquear_y_exigir_sin_supresion(cur, actor)
            if rol == 'estudiante':
                self._estudiante(cur, actor)
            r, _, _, publicacion = self._publicacion(cur, actor, rol, identificador)
            cur.execute('SELECT gracia_hasta>clock_timestamp() FROM recurso_visita WHERE publicacion=%s AND sujeto_google=%s', (identificador, actor))
            plazo = cur.fetchone()
            en_gracia = r['estado'] == 'cerrado' and plazo and plazo[0]
            if r['tipo'] != 'encuesta' or not publicacion['participante'] or (r['estado'] != 'publicado' and not en_gracia):
                raise RecursoConflicto('La encuesta está cerrada o no admite respuestas.')
            limpias = validar_respuestas(r['contenido'], respuestas)
            cur.execute('SELECT respuestas FROM recurso_respuesta WHERE publicacion=%s AND sujeto_google=%s', (identificador, actor))
            actual = cur.fetchone()
            if actual:
                if actual[0] != limpias:
                    raise RecursoConflicto('Ya enviaste una respuesta. No se puede sustituir.')
                return {'enviada': True, 'repetida': True}
            cur.execute('INSERT INTO recurso_respuesta(publicacion,sujeto_google,respuestas) VALUES (%s,%s,%s)', (identificador, actor, Jsonb(limpias)))
            return {'enviada': True, 'repetida': False}

    def metricas(self, actor, rol, identificador, clase_filtro='', envio=None):
        if envio is not None and (type(envio) is not int or envio <= 0):
            raise RecursoInvalido('Selecciona un envío válido.')
        with self._conexion() as cnx, cnx.cursor() as cur:
            if rol == 'investigador':
                self._investigador(cur, actor)
            r = self._recurso(cur, identificador)
            envios = self._envios(cur, actor, rol, identificador)
            if rol != 'investigador' and not envios:
                raise RecursoNoEncontrado('Recurso no disponible.')
            envio_actual = envio if envio is not None else (envios[0]['numero'] if envios else None)
            if envio is not None and envio not in {e['numero'] for e in envios}:
                raise RecursoNoEncontrado('Envío no disponible.')
            cur.execute('SELECT p.id,coalesce(c.id,p.destinatario),coalesce(c.nombre,d.nombre),p.publicada_en,p.audiencia '
                        'FROM recurso_publicacion p LEFT JOIN clase c ON c.id=p.clase LEFT JOIN persona d ON d.sujeto_google=p.destinatario '
                        "WHERE p.retirada_en IS NULL AND p.recurso=%s AND p.envio=%s AND (%s='investigador' OR c.creador=%s OR p.destinatario=%s) ORDER BY 3",
                        (identificador, envio_actual, rol, actor, actor))
            publicaciones = cur.fetchall()
            if clase_filtro and clase_filtro not in {p[1] for p in publicaciones}:
                raise RecursoNoEncontrado('Curso no disponible.')
            anotar(cur, 'recurso.metricas_consultadas', actor=actor, detalle={'recurso': identificador, 'clase': clase_filtro, 'envio': envio_actual})
            cursos, respuestas = [], []
            for pub, clase, nombre, publicada_en, audiencia in publicaciones:
                cur.execute('SELECT m.identificador,COALESCE(NULLIF(p.nombre,\'\'),\'Participante\'), '
                            'a.enviada_en,v.primera_en,v.ultima_en,coalesce(v.aperturas,0) FROM '
                            '(SELECT identificador FROM clase_matricula WHERE clase=%s AND %s=\'estudiantes\' '
                            'UNION ALL SELECT %s WHERE %s IN (\'docentes\',\'individuales\')) m '
                            'LEFT JOIN persona p ON p.sujeto_google=m.identificador '
                            'LEFT JOIN recurso_respuesta a ON a.publicacion=%s AND a.sujeto_google=m.identificador '
                            'LEFT JOIN recurso_visita v ON v.publicacion=%s AND v.sujeto_google=m.identificador '
                            'ORDER BY p.nombre,m.identificador', (clase, audiencia, clase, audiencia, pub, pub))
                integrantes = [dict(id=f[0], nombre=f[1], respondida=bool(f[2]), vista=bool(f[3]),
                                    enviada_en=f[2].isoformat() if f[2] else None,
                                    primera_en=f[3].isoformat() if f[3] else None,
                                    ultima_en=f[4].isoformat() if f[4] else None, aperturas=f[5]) for f in cur.fetchall()]
                cur.execute('SELECT respuestas FROM recurso_respuesta WHERE publicacion=%s ORDER BY enviada_en', (pub,))
                todas = [f[0] for f in cur.fetchall()]
                if not clase_filtro or clase == clase_filtro:
                    respuestas.extend(todas)
                cur.execute('SELECT coalesce(sum(aperturas),0),coalesce(bool_and(conteo_completo),true) '
                            'FROM recurso_visita WHERE publicacion=%s', (pub,))
                aperturas_historicas, conteo_completo = cur.fetchone()
                cursos.append(dict(id=clase, nombre=nombre, publicacion=pub, integrantes=integrantes,
                                   matriculados=len(integrantes), respondieron=sum(i['respondida'] for i in integrantes),
                                   vieron=sum(i['vista'] for i in integrantes), respuestas_totales=len(todas),
                                   envio=envio_actual, publicada_en=publicada_en.isoformat(),
                                   audiencia=audiencia, puede_retirar=not todas,
                                   aperturas=sum(i['aperturas'] for i in integrantes),
                                   aperturas_historicas=int(aperturas_historicas), conteo_completo=conteo_completo))
            cur.execute('SELECT count(*) FROM recurso_publicacion WHERE recurso=%s AND envio=%s AND retirada_en IS NOT NULL', (identificador, envio_actual))
            retirados = cur.fetchone()[0]
            estado_envio = next((e['estado'] for e in envios if e['numero'] == envio_actual), r['estado'])
            return dict(id=r['id'], titulo=r['titulo'], tipo=r['tipo'], estado=estado_envio, cursos=cursos,
                        clase_filtro=clase_filtro, total_respuestas=len(respuestas),
                        envio_actual=envio_actual, envios=envios, destinatarios_retirados=retirados,
                        audiencia=next((e['audiencia'] for e in envios if e['numero'] == envio_actual), 'estudiantes'),
                        preguntas=resultados(r['contenido'], respuestas) if r['tipo'] == 'encuesta' else [])

    def _envios(self, cur, actor, rol, identificador):
        cur.execute('SELECT p.envio,min(p.publicada_en),count(DISTINCT coalesce(p.clase,p.destinatario)) FILTER (WHERE p.retirada_en IS NULL),'
                    'coalesce(sum(v.aperturas),0),coalesce(bool_and(v.conteo_completo),true),min(p.estado),min(p.audiencia) '
                    'FROM recurso_publicacion p LEFT JOIN clase c ON c.id=p.clase '
                    'LEFT JOIN recurso_visita v ON v.publicacion=p.id '
                    "WHERE p.recurso=%s AND (%s='investigador' OR (p.retirada_en IS NULL AND (c.creador=%s OR p.destinatario=%s))) "
                    'GROUP BY p.envio ORDER BY p.envio DESC', (identificador, rol, actor, actor))
        return [dict(numero=f[0], publicada_en=f[1].isoformat(), cursos=f[2],
                     aperturas=int(f[3]), conteo_completo=f[4], estado=f[5], audiencia=f[6]) for f in cur.fetchall()]

    def exportar_titular(self, sujeto):
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute('SELECT p.recurso,p.clase,a.respuestas,a.enviada_en,p.envio,p.id FROM recurso_respuesta a '
                        'JOIN recurso_publicacion p ON p.id=a.publicacion WHERE a.sujeto_google=%s', (sujeto,))
            respuestas = [dict(recurso=f[0], clase=f[1], respuestas=f[2], enviada_en=f[3].isoformat(),
                               envio=f[4], publicacion=f[5]) for f in cur.fetchall()]
            cur.execute('SELECT p.recurso,p.clase,v.primera_en,v.ultima_en,p.envio,p.id,v.aperturas,v.conteo_completo FROM recurso_visita v '
                        'JOIN recurso_publicacion p ON p.id=v.publicacion WHERE v.sujeto_google=%s', (sujeto,))
            visitas = [dict(recurso=f[0], clase=f[1], primera_en=f[2].isoformat(), ultima_en=f[3].isoformat(),
                            envio=f[4], publicacion=f[5], aperturas=f[6], conteo_completo=f[7]) for f in cur.fetchall()]
            return dict(respuestas=respuestas, visitas=visitas)
