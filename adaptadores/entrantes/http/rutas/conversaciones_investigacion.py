from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento, requerir_rol
from adaptadores.entrantes.http.rutas.historial import (
    conversaciones_como_contrato,
    hilo_como_contrato,
)
from adaptadores.entrantes.http.sesiones import COOKIE, sujeto_de
from dominio.puertos.almacen import ErrorDeAlmacen, EscrituraRechazada


def filtros(parametros):
    pagina = int(parametros.get('pagina', '1'))
    if not 1 <= pagina <= 1_000_000:
        raise ValueError('página fuera de rango')
    def fecha(nombre):
        texto = parametros.get(nombre, '')
        if not texto:
            return None
        valor = datetime.fromisoformat(texto.replace('Z', '+00:00'))
        if valor.tzinfo is None:
            raise ValueError('se necesita zona horaria')
        return valor.astimezone(UTC)
    desde, hasta = fecha('desde'), fecha('hasta')
    if desde and hasta and desde >= hasta:
        raise ValueError('periodo no válido')
    if any(len(parametros.get(k, '')) > 200 or '\x00' in parametros.get(k, '')
           for k in ('buscar', 'clase')):
        raise ValueError('filtro demasiado largo')
    return dict(clase=parametros.get('clase', ''), desde=desde, hasta=hasta, pagina=pagina)

def crear_router(sesiones, almacen, puerta, catalogo=None):
    router = APIRouter()

    def autorizar(peticion):
        negativa = requerir_rol(sesiones, peticion, 'investigador')
        if negativa is not None:
            return None, None, negativa
        actor = sujeto_de(sesiones.leer(peticion.cookies.get(COOKIE)))
        negativa = puerta.negativa(actor)
        if negativa is not None:
            return None, None, negativa
        try:
            alcance = filtros(peticion.query_params)
        except (ValueError, OverflowError):
            return None, None, JSONResponse({'detalle': 'filtros no válidos'}, status_code=400)
        return actor, alcance, None

    def fallo(error):
        if isinstance(error, EscrituraRechazada):
            return JSONResponse({'detalle': 'consulta no autorizada en el estado vigente'}, status_code=403)
        return mantenimiento('no se pudieron consultar las conversaciones')

    def respuesta(cuerpo):
        return JSONResponse(cuerpo, headers={'Cache-Control': 'no-store, private'})

    @router.get('/api/investigacion/conversaciones/estudiantes')
    def directorio(peticion: Request):
        actor, alcance, negativa = autorizar(peticion)
        if negativa is not None:
            return negativa
        try:
            cuerpo = almacen.directorio(actor, buscar=peticion.query_params.get('buscar', ''),
                clase=alcance['clase'], pagina=alcance['pagina'],
                incluir_pruebas=peticion.query_params.get('pruebas') == '1')
        except ErrorDeAlmacen as error:
            return fallo(error)
        return respuesta(cuerpo)

    @router.get('/api/investigacion/conversaciones/{sujeto}')
    def listar(sujeto: str, peticion: Request):
        actor, alcance, negativa = autorizar(peticion)
        if negativa is not None:
            return negativa
        try:
            filas, total = almacen.conversaciones(actor, sujeto, **alcance)
        except ErrorDeAlmacen as error:
            return fallo(error)
        return respuesta({**conversaciones_como_contrato(filas), 'total': total,
                          'pagina': alcance['pagina'], 'paginas': (total + 49) // 50})

    @router.get('/api/investigacion/conversaciones/{sujeto}/{sesion}')
    def hilo(sujeto: str, sesion: str, peticion: Request):
        actor, alcance, negativa = autorizar(peticion)
        if negativa is not None:
            return negativa
        alcance.pop('pagina')
        try:
            mensajes = almacen.conversacion(actor, sujeto, sesion, **alcance)
        except ErrorDeAlmacen as error:
            return fallo(error)
        if not mensajes:
            return JSONResponse({'detalle': 'conversación sin mensajes en este alcance'}, status_code=404)
        return respuesta(hilo_como_contrato(sesion, mensajes, catalogo))

    return router
