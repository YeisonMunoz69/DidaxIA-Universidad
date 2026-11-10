from __future__ import annotations

import re

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from adaptadores.entrantes.http.rutas.comun import requerir_sesion
from adaptadores.entrantes.http.sesiones import Sesiones
from adaptadores.salientes.biblioteca.catalogo import CatalogoDeFuentes, FichaDeFragmento
from adaptadores.salientes.biblioteca.markdown_seguro import convertir
from dominio.puertos.biblioteca import (
    Canal,
    Indisponible,
    Localizacion,
    MotivoIndisponible,
    Obra,
    Parte,
    Permiso,
)


CODIGO_POR_MOTIVO = {
    MotivoIndisponible.FRAGMENTO_INEXISTENTE: 404,
    MotivoIndisponible.RECURSO_NO_CATALOGADO: 404,
    MotivoIndisponible.OBRA_NO_AUTORIZADA: 403,
    MotivoIndisponible.RECURSO_RETIRADO: 403,
    MotivoIndisponible.ARCHIVO_AUSENTE: 404,
    MotivoIndisponible.PAGINA_SIN_MAPEO: 404,
    MotivoIndisponible.RECURSO_NO_SERVIBLE: 404,
}


EXPLICACION = {
    MotivoIndisponible.FRAGMENTO_INEXISTENTE: "no hay material con ese identificador",
    MotivoIndisponible.RECURSO_NO_CATALOGADO: "todavía no está en el catálogo de la biblioteca",
    MotivoIndisponible.OBRA_NO_AUTORIZADA: (
        "esta obra todavía no tiene registrada la autorización necesaria para "
        "publicar este material"
    ),
    MotivoIndisponible.RECURSO_RETIRADO: "este material se retiró de la biblioteca",
    MotivoIndisponible.ARCHIVO_AUSENTE: "el material no está disponible en este servidor",
    MotivoIndisponible.PAGINA_SIN_MAPEO: (
        "no se puede señalar la página exacta de esta obra sin comprobarla antes"
    ),
    MotivoIndisponible.RECURSO_NO_SERVIBLE: "este material no se puede abrir aquí",
}


def _negativa(motivo: MotivoIndisponible, detalle: str = "") -> JSONResponse:
    cuerpo = {"motivo": motivo.value, "detalle": EXPLICACION[motivo]}
    if detalle:
        cuerpo["diagnostico"] = detalle
    return JSONResponse(cuerpo, status_code=CODIGO_POR_MOTIVO[motivo])

def _localizacion_json(localizacion: Localizacion | None) -> dict | None:
    if localizacion is None:
        return None
    return {
        "obra": localizacion.obra,
        "parte": localizacion.parte,
        "pagina_impresa": localizacion.pagina_impresa,
        "pagina_impresa_hasta": localizacion.pagina_impresa_hasta,
        "pagina_interna_en_parte": localizacion.pagina_interna_en_parte,
        "pagina_interna_en_obra": localizacion.pagina_interna_en_obra,
        "exacta": localizacion.exacta,
    }

def _obra_json(catalogo: CatalogoDeFuentes, obra: Obra) -> dict:
    return {
        "clave": obra.clave,
        "titulo": obra.titulo,
        "autoria": obra.autoria,
        "paginas_del_archivo": obra.paginas_del_archivo,
        "referencia_externa": obra.referencia_externa,
        "referencia_verificada": obra.referencia_verificada,
        "desfase_medido": catalogo.desfase_medido(obra.clave),
        "disponibilidad": {
            canal.value: _disponibilidad_json(catalogo, obra.clave, canal) for canal in Canal
        },
    }

def _disponibilidad_json(catalogo: CatalogoDeFuentes, clave: str, canal: Canal) -> dict:
    vista = catalogo.disponibilidad(clave, canal)
    motivo = vista.motivo()
    return {
        "permiso": vista.permiso.value,
        "catalogado": vista.catalogado,
        "archivo_presente": vista.archivo_presente,
        "servible": vista.servible,
        "motivo": motivo.value if motivo else None,
    }

def _parte_json(parte: Parte) -> dict:
    return {
        "identificador": parte.identificador,
        "nombre": parte.identificador.split(":", 1)[1],
        "obra": parte.obra,
        "titulo": parte.titulo,
        "pagina_impresa_inicial": parte.pagina_impresa_inicial,
        "pagina_impresa_final": parte.pagina_impresa_final,
    }

def _ficha_json(catalogo: CatalogoDeFuentes, ficha: FichaDeFragmento, con_texto: bool) -> dict:
    fragmento = ficha.fragmento.fragmento
    procedencia = fragmento.procedencia
    datos = {
        "identificador": fragmento.identificador,

        "titulo": catalogo.titulo_de_fragmento(fragmento.identificador),
        "obra": _obra_json(catalogo, ficha.obra),
        "procedencia": {
            "obra": procedencia.obra,
            "pagina": procedencia.pagina,
            "pagina_hasta": procedencia.pagina_hasta,
            "exacta": procedencia.exacta,
            "captura": procedencia.captura,
        },
        "nivel_apos": fragmento.nivel_apos,
        "registro_duval": fragmento.registro_duval,
        "nodo_grafo": fragmento.nodo_grafo,
        "concepcion_asociada": fragmento.concepcion_asociada,

        "verificacion": ficha.fragmento.verificacion_dd02 or "sin marca",
        "localizacion": _localizacion_json(ficha.localizacion),
        "motivo_sin_localizacion": (
            ficha.motivo_sin_localizacion.value if ficha.motivo_sin_localizacion else None
        ),

        "naturaleza": "material_del_curso",
    }
    if con_texto:
        documento = convertir(fragmento.texto)
        datos["contenido"] = documento.como_json()
    return datos

_TROZO = 64 * 1024


_RANGO = re.compile(r"^bytes=(\d*)-(\d*)$")


_CABECERAS_DE_ARCHIVO = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'self'",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "private, no-store, max-age=0",
    "Accept-Ranges": "bytes",
}


def _nombre_publicado(clave: str, parte: str = "") -> str:
    return f"{clave}-{parte}.pdf" if parte else f"{clave}.pdf"

def _rango_pedido(cabecera: str, tamano: int) -> tuple[int, int] | None | bool:
    if not cabecera:
        return None
    coincidencia = _RANGO.match(cabecera.strip())
    if not coincidencia:
        return False

    crudo_inicio, crudo_fin = coincidencia.groups()
    if crudo_inicio == "" and crudo_fin == "":
        return False
    if crudo_inicio == "":

        longitud = min(int(crudo_fin), tamano)
        if longitud <= 0:
            return False
        return tamano - longitud, tamano - 1

    inicio = int(crudo_inicio)
    fin = int(crudo_fin) if crudo_fin else tamano - 1
    if inicio >= tamano or fin < inicio:
        return False
    return inicio, min(fin, tamano - 1)

def _leer_por_trozos(ruta, inicio: int, fin: int):
    def flujo():
        restante = fin - inicio + 1
        with ruta.open("rb") as archivo:
            archivo.seek(inicio)
            while restante > 0:
                trozo = archivo.read(min(_TROZO, restante))
                if not trozo:
                    break
                restante -= len(trozo)
                yield trozo

    return flujo

def _servir_pdf(peticion: Request, ruta, nombre: str) -> Response:
    try:
        tamano = ruta.stat().st_size
    except OSError:
        return _negativa(MotivoIndisponible.ARCHIVO_AUSENTE)
    if tamano == 0:

        return _negativa(MotivoIndisponible.RECURSO_NO_SERVIBLE)

    cabeceras = {
        **_CABECERAS_DE_ARCHIVO,

        "Content-Disposition": f'inline; filename="{nombre}"',
    }

    rango = _rango_pedido(peticion.headers.get("range", ""), tamano)
    if rango is False:
        return Response(
            status_code=416,
            headers={**cabeceras, "Content-Range": f"bytes */{tamano}"},
        )
    if rango is None:
        return StreamingResponse(
            _leer_por_trozos(ruta, 0, tamano - 1)(),
            media_type="application/pdf",
            headers={**cabeceras, "Content-Length": str(tamano)},
        )

    inicio, fin = rango
    return StreamingResponse(
        _leer_por_trozos(ruta, inicio, fin)(),
        status_code=206,
        media_type="application/pdf",
        headers={
            **cabeceras,
            "Content-Range": f"bytes {inicio}-{fin}/{tamano}",
            "Content-Length": str(fin - inicio + 1),
        },
    )

def crear_router(catalogo: CatalogoDeFuentes, sesiones: Sesiones) -> APIRouter:
    router = APIRouter()

    @router.get("/api/fuentes/obras")
    def listar_obras(peticion: Request) -> Response:
        _, negativa = requerir_sesion(sesiones, peticion)
        if negativa:
            return negativa
        return JSONResponse([_obra_json(catalogo, o) for o in catalogo.obras()])

    @router.get("/api/fuentes/obras/{clave}")
    def ficha_de_obra(clave: str, peticion: Request) -> Response:
        _, negativa = requerir_sesion(sesiones, peticion)
        if negativa:
            return negativa
        try:
            obra = catalogo.obra(clave)
        except Indisponible as exc:
            return _negativa(exc.motivo, exc.detalle)
        datos = _obra_json(catalogo, obra)
        datos["partes"] = [_parte_json(p) for p in catalogo.partes_de(clave)]
        return JSONResponse(datos)

    @router.get("/api/fuentes/fragmentos")
    def listar_fragmentos(peticion: Request) -> Response:
        _, negativa = requerir_sesion(sesiones, peticion)
        if negativa:
            return negativa
        return JSONResponse([
            {
                "identificador": leido.fragmento.identificador,
                "titulo": catalogo.titulo_de_fragmento(leido.fragmento.identificador),
                "obra": leido.fragmento.procedencia.obra,
                "pagina": leido.fragmento.procedencia.pagina,
                "pagina_hasta": leido.fragmento.procedencia.pagina_hasta,
            }
            for leido in catalogo.fragmentos()
        ])

    @router.get("/api/fuentes/fragmentos/{identificador}")
    def ficha_de_fragmento(identificador: str, peticion: Request) -> Response:
        _, negativa = requerir_sesion(sesiones, peticion)
        if negativa:
            return negativa
        try:
            ficha = catalogo.ficha_de_fragmento(identificador)
        except Indisponible as exc:
            return _negativa(exc.motivo, exc.detalle)

        autorizado = catalogo.disponibilidad(ficha.obra.clave, Canal.FRAGMENTO).servible
        datos = _ficha_json(catalogo, ficha, con_texto=autorizado)
        if not autorizado:
            motivo = (
                catalogo.disponibilidad(ficha.obra.clave, Canal.FRAGMENTO).motivo()
                or MotivoIndisponible.RECURSO_NO_SERVIBLE
            )
            datos["contenido"] = None
            datos["motivo_sin_contenido"] = motivo.value
            datos["explicacion_sin_contenido"] = EXPLICACION[motivo]
        return JSONResponse(datos)

    @router.get("/api/fuentes/obras/{clave}/partes/{nombre}")
    def markdown_de_parte(clave: str, nombre: str, peticion: Request) -> Response:
        _, negativa = requerir_sesion(sesiones, peticion)
        if negativa:
            return negativa
        try:
            parte = catalogo.parte(f"{clave}:{nombre}")
        except Indisponible as exc:
            return _negativa(exc.motivo, exc.detalle)

        vista = catalogo.disponibilidad(clave, Canal.MARKDOWN_CONTINUO)
        if not vista.servible:
            return _negativa(vista.motivo() or MotivoIndisponible.RECURSO_NO_SERVIBLE)

        ruta = catalogo.ruta_de_parte(parte, Canal.MARKDOWN_CONTINUO)
        if ruta is None:
            return _negativa(MotivoIndisponible.ARCHIVO_AUSENTE)
        try:
            texto = ruta.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return _negativa(MotivoIndisponible.RECURSO_NO_SERVIBLE)

        documento = convertir(texto)
        return JSONResponse(
            {
                "parte": _parte_json(parte),
                "obra": _obra_json(catalogo, catalogo.obra(clave)),
                "contenido": documento.como_json(),
                "naturaleza": "material_del_curso",
            }
        )

    @router.get("/api/fuentes/obras/{clave}/partes/{nombre}/pdf")
    def pdf_de_parte(clave: str, nombre: str, peticion: Request) -> Response:
        _, negativa = requerir_sesion(sesiones, peticion)
        if negativa:
            return negativa
        try:
            parte = catalogo.parte(f"{clave}:{nombre}")
        except Indisponible as exc:
            return _negativa(exc.motivo, exc.detalle)

        vista = catalogo.disponibilidad(clave, Canal.PDF_DIVIDIDO)
        if not vista.permiso.habilita:
            return _negativa(
                MotivoIndisponible.RECURSO_RETIRADO
                if vista.permiso is Permiso.RETIRADO
                else MotivoIndisponible.OBRA_NO_AUTORIZADA
            )

        ruta = catalogo.ruta_de_parte(parte, Canal.PDF_DIVIDIDO)
        if ruta is None:

            return _negativa(
                MotivoIndisponible.RECURSO_NO_CATALOGADO
                if not parte.archivo_pdf
                else MotivoIndisponible.ARCHIVO_AUSENTE
            )

        return _servir_pdf(
            peticion, ruta, _nombre_publicado(clave, parte.identificador.split(":", 1)[1])
        )

    @router.get("/api/fuentes/obras/{clave}/pdf")
    def pdf_completo(clave: str, peticion: Request) -> Response:
        _, negativa = requerir_sesion(sesiones, peticion)
        if negativa:
            return negativa
        try:
            catalogo.obra(clave)
        except Indisponible as exc:
            return _negativa(exc.motivo, exc.detalle)

        vista = catalogo.disponibilidad(clave, Canal.PDF_COMPLETO)
        if not vista.servible:
            return _negativa(vista.motivo() or MotivoIndisponible.RECURSO_NO_SERVIBLE)

        ruta = catalogo.ruta_del_pdf_completo(clave)
        if ruta is None:
            return _negativa(MotivoIndisponible.ARCHIVO_AUSENTE)
        return _servir_pdf(peticion, ruta, _nombre_publicado(clave))

    return router
