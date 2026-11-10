"""Biblioteca del investigador, lectura docente y bandeja del estudiante."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, mantenimiento, requerir_sesion
from adaptadores.entrantes.http.sesiones import sujeto_de
from adaptadores.salientes.registro.recursos_db import RecursoConflicto, RecursoNoEncontrado
from dominio.modelo.acceso import AccesoCalculado, calcular_acceso
from dominio.modelo.recursos import RecursoInvalido
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible, EscrituraRechazada


def crear_router(sesiones, recursos, puerta, estado_vigente):
    router = APIRouter()

    def autorizar(peticion, roles):
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return None, negativa
        if datos['rol'] not in roles:
            return None, JSONResponse({'detalle': 'No tienes permiso para esta operación.'}, status_code=403)
        negativa = puerta.negativa(sujeto_de(datos))
        if negativa is not None:
            return None, negativa
        if datos['rol'] == 'estudiante':
            try:
                vigente = estado_vigente.estado_vigente(sujeto_de(datos))
                acceso = calcular_acceso(vigente) if vigente else AccesoCalculado.ONBOARDING_PENDIENTE
            except (AlmacenNoConfigurado, AlmacenNoDisponible):
                return None, mantenimiento()
            if acceso != AccesoCalculado.HABILITADO:
                return None, JSONResponse({'detalle': 'Completa tu autorización para usar los recursos.',
                                           'estado': acceso.value}, status_code=403)
        return datos, None

    def ejecutar(accion):
        try:
            return JSONResponse(accion(), headers={'Cache-Control': 'no-store'})
        except RecursoNoEncontrado as exc:
            return JSONResponse({'detalle': str(exc)}, status_code=404)
        except RecursoConflicto as exc:
            return JSONResponse({'detalle': str(exc)}, status_code=409)
        except RecursoInvalido as exc:
            return JSONResponse({'detalle': str(exc)}, status_code=400)
        except EscrituraRechazada:
            return JSONResponse({'detalle': 'La cuenta no está autorizada para esta operación.'}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento('No se pueden consultar o guardar los recursos ahora.')

    @router.get('/api/recursos/plantillas')
    def plantillas(peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        ruta = Path(__file__).resolve().parents[4] / 'contenido' / 'recursos'
        return n if n is not None else ejecutar(lambda: json.loads((ruta / 'indice.json').read_text(encoding='utf8')) + recursos.plantillas_personales(sujeto_de(d)))

    @router.get('/api/recursos/plantillas/{codigo}')
    def plantilla(codigo: str, peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        if n is not None:
            return n
        if codigo.startswith('personal-'):
            return ejecutar(lambda: recursos.consultar(sujeto_de(d), codigo.removeprefix('personal-')))
        ruta = Path(__file__).resolve().parents[4] / 'contenido' / 'recursos'
        indice = json.loads((ruta / 'indice.json').read_text(encoding='utf8'))
        if codigo not in {p['id'] for p in indice}:
            return JSONResponse({'detalle': 'Plantilla no disponible.'}, status_code=404)
        return JSONResponse(json.loads((ruta / (codigo + '.json')).read_text(encoding='utf8')))

    @router.get('/api/recursos/clases')
    def clases(peticion: Request):
        d, n = autorizar(peticion, {'investigador', 'docente'})
        return n if n is not None else ejecutar(lambda: recursos.clases(sujeto_de(d), d['rol']))

    @router.get('/api/recursos/docentes')
    def docentes(peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        return n if n is not None else ejecutar(lambda: recursos.docentes(sujeto_de(d)))

    @router.get('/api/recursos/estudiantes')
    def estudiantes_destinatarios(peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        return n if n is not None else ejecutar(lambda: recursos.estudiantes_destinatarios(sujeto_de(d)))

    @router.get('/api/recursos')
    def listado(peticion: Request):
        d, n = autorizar(peticion, {'investigador', 'docente'})
        return n if n is not None else ejecutar(lambda: recursos.listar(sujeto_de(d), d['rol']))

    @router.post('/api/recursos')
    async def crear(peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        if n is not None:
            return n
        if len(await peticion.body()) > 15_000_000:
            return JSONResponse({'detalle': 'El recurso supera 15 MB.'}, status_code=413)
        cuerpo = await json_del_cuerpo(peticion)
        return ejecutar(lambda: recursos.guardar(sujeto_de(d), cuerpo))

    @router.get('/api/recursos/bandeja')
    def bandeja(peticion: Request):
        d, n = autorizar(peticion, {'estudiante','docente'})
        return n if n is not None else ejecutar(lambda: recursos.bandeja(sujeto_de(d), d['rol']))

    @router.get('/api/recursos/publicaciones/{publicacion}')
    def lectura(publicacion: str, peticion: Request):
        d, n = autorizar(peticion, {'estudiante', 'docente', 'investigador'})
        return n if n is not None else ejecutar(lambda: recursos.abrir(sujeto_de(d), d['rol'], publicacion))

    @router.post('/api/recursos/publicaciones/{publicacion}/visita')
    def visitar(publicacion: str, peticion: Request):
        d, n = autorizar(peticion, {'estudiante','docente'})
        return n if n is not None else ejecutar(lambda: recursos.abrir(sujeto_de(d), d['rol'], publicacion, visita=True))

    @router.post('/api/recursos/publicaciones/{publicacion}/actividad')
    def actividad(publicacion: str, peticion: Request, solo_estado: bool = False):
        d, n = autorizar(peticion, {'estudiante','docente'})
        opciones = {'incluir_contenido': False} if solo_estado else {}
        return n if n is not None else ejecutar(lambda: recursos.abrir(sujeto_de(d), d['rol'], publicacion, actividad=True, **opciones))

    @router.post('/api/recursos/publicaciones/{publicacion}/respuestas')
    async def responder(publicacion: str, peticion: Request):
        d, n = autorizar(peticion, {'estudiante','docente'})
        if n is not None:
            return n
        if len(await peticion.body()) > 4_000_000:
            return JSONResponse({'detalle': 'La respuesta es demasiado grande.'}, status_code=413)
        cuerpo = await json_del_cuerpo(peticion)
        return ejecutar(lambda: recursos.responder(sujeto_de(d), publicacion, cuerpo.get('respuestas'), d['rol']))

    @router.get('/api/recursos/{identificador}')
    def detalle(identificador: str, peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        return n if n is not None else ejecutar(lambda: recursos.consultar(sujeto_de(d), identificador))

    @router.put('/api/recursos/{identificador}')
    async def guardar(identificador: str, peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        if n is not None:
            return n
        if len(await peticion.body()) > 15_000_000:
            return JSONResponse({'detalle': 'El recurso supera 15 MB.'}, status_code=413)
        cuerpo = await json_del_cuerpo(peticion)
        return ejecutar(lambda: recursos.guardar(sujeto_de(d), cuerpo, identificador))

    @router.post('/api/recursos/{identificador}/duplicar')
    def duplicar(identificador: str, peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        return n if n is not None else ejecutar(lambda: recursos.duplicar(sujeto_de(d), identificador))

    @router.post('/api/recursos/{identificador}/plantilla')
    def guardar_plantilla(identificador: str, peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        return n if n is not None else ejecutar(lambda: recursos.guardar_plantilla(sujeto_de(d), identificador))

    @router.post('/api/recursos/{identificador}/publicar')
    async def publicar(identificador: str, peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        if n is not None:
            return n
        cuerpo = await json_del_cuerpo(peticion)
        return ejecutar(lambda: recursos.publicar(sujeto_de(d), identificador, cuerpo.get('clases'), cuerpo.get('revision'), cuerpo.get('audiencia','estudiantes')))

    @router.post('/api/recursos/{identificador}/cursos')
    async def ampliar_cursos(identificador: str, peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        if n is not None:
            return n
        cuerpo = await json_del_cuerpo(peticion)
        return ejecutar(lambda: recursos.ampliar_cursos(sujeto_de(d), identificador,
                       cuerpo.get('clases'), cuerpo.get('revision'), cuerpo.get('envio'), cuerpo.get('audiencia', 'estudiantes')))

    @router.post('/api/recursos/{identificador}/retirar-destinatarios')
    async def retirar_destinatarios(identificador: str, peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        if n is not None:
            return n
        cuerpo = await json_del_cuerpo(peticion)
        return ejecutar(lambda: recursos.retirar_destinatarios(sujeto_de(d), identificador,
                       cuerpo.get('publicaciones'), cuerpo.get('revision'), cuerpo.get('envio')))

    @router.patch('/api/recursos/{identificador}/estado')
    async def estado(identificador: str, peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        if n is not None:
            return n
        cuerpo = await json_del_cuerpo(peticion)
        return ejecutar(lambda: recursos.cambiar_estado(sujeto_de(d), identificador, cuerpo.get('estado')))

    @router.delete('/api/recursos/{identificador}')
    def eliminar(identificador: str, peticion: Request):
        d, n = autorizar(peticion, {'investigador'})
        if n is not None:
            return n
        def accion():
            recursos.eliminar(sujeto_de(d), identificador)
            return {'eliminado': True}
        return ejecutar(accion)

    @router.get('/api/recursos/{identificador}/metricas')
    def metricas(identificador: str, peticion: Request, clase: str = '', envio: int | None = None):
        d, n = autorizar(peticion, {'investigador', 'docente'})
        return n if n is not None else ejecutar(lambda: recursos.metricas(sujeto_de(d), d['rol'], identificador, clase, envio))

    @router.get('/api/recursos/{identificador}/informe.pdf')
    def informe(identificador: str, peticion: Request, clase: str = '', envio: int | None = None):
        from adaptadores.salientes.informes.pdf_recursos import generar_pdf

        d, n = autorizar(peticion, {'investigador', 'docente'})
        if n is not None:
            return n
        m = ejecutar(lambda: recursos.metricas(sujeto_de(d), d['rol'], identificador, clase, envio))
        if m.status_code != 200:
            return m
        return Response(generar_pdf(json.loads(m.body)), media_type='application/pdf',
                        headers={'Cache-Control': 'no-store', 'Content-Disposition': 'attachment; filename="informe-recursos.pdf"'})

    return router
