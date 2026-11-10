"""
fuentes.py — La biblioteca de fuentes por HTTP · Fase 5
=========================================================

Siete rutas institucionales autenticadas. El material del curso no contiene
datos del estudiante, pero la decisión institucional del 2026-09-05 autoriza
su consulta **dentro del piloto**, no su exposición anónima en Internet. Por
eso incluso la ficha exige una sesión verificada de `@unimayor.edu.co`.

**El cliente nunca nombra un archivo.** Todas las rutas se direccionan por
identificador catalogado —`F-252`, `LOP`, `LOP/partes/seccion-2-1`— y el
backend resuelve el archivo por dentro. No hay ningún parámetro que acepte una
ruta, un nombre de archivo ni una URL, así que `../`, `C:\\`, una barra
invertida o un nombre con mayúsculas manipuladas no tienen dónde entrar: no se
rechazan, es que no se pueden expresar.

Las dos puertas, y en este orden
---------------------------------
1. **¿Existe?** El catálogo responde `Indisponible` con su motivo.
2. **¿Está autorizado?** `FUENTES.md` decide, canal por canal y obra por obra.

La segunda se comprueba **en el servidor y en cada ruta**, no escondiendo el
botón. Un cliente que invente la URL del PDF de una obra bloqueada recibe la
misma negativa que si la pidiera desde la pantalla.

Qué se puede ver
----------------
Dentro de una sesión institucional viajan la ficha, la procedencia y los
canales expresamente autorizados. Sin sesión no viaja siquiera el inventario;
si una autorización se retira, el contenido vuelve a quedar bloqueado.


"""

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

#: Qué código HTTP le corresponde a cada motivo. **La tabla es el contrato.**
#:
#: `403` sólo para lo que una decisión del equipo puede cambiar; `404` para lo
#: que no existe o no está aquí. Distinguirlos importa porque el cliente hace
#: cosas distintas: ante `403` explica la puerta de publicación, ante `404`
#: ofrece volver.
CODIGO_POR_MOTIVO = {
    MotivoIndisponible.FRAGMENTO_INEXISTENTE: 404,
    MotivoIndisponible.RECURSO_NO_CATALOGADO: 404,
    MotivoIndisponible.OBRA_NO_AUTORIZADA: 403,
    MotivoIndisponible.RECURSO_RETIRADO: 403,
    MotivoIndisponible.ARCHIVO_AUSENTE: 404,
    MotivoIndisponible.PAGINA_SIN_MAPEO: 404,
    MotivoIndisponible.RECURSO_NO_SERVIBLE: 404,
}

#: Lo que se le dice a una persona por cada motivo. Ninguno menciona una ruta,
#: un directorio ni un nombre de archivo: el detalle técnico se queda dentro.
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
    """La respuesta de un recurso que no se puede servir. **Siempre con motivo.**

    El cuerpo lleva el motivo en clave estable para que la interfaz elija su
    estado sin analizar el texto, y una explicación en español para quien lo
    lea. El `detalle` técnico —que sí nombra claves y páginas— sólo viaja
    cuando no revela nada del sistema de archivos.
    """
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
    """La parte, **sin sus nombres de archivo.**

    El cliente no los necesita —pide la parte por su nombre catalogado— y
    publicarlos filtraría cómo está organizado el material en el servidor, que
    es justo lo que la fase prohíbe exponer.
    """
    return {
        "identificador": parte.identificador,
        "nombre": parte.identificador.split(":", 1)[1],
        "obra": parte.obra,
        "titulo": parte.titulo,
        "pagina_impresa_inicial": parte.pagina_impresa_inicial,
        "pagina_impresa_final": parte.pagina_impresa_final,
    }


def _ficha_json(catalogo: CatalogoDeFuentes, ficha: FichaDeFragmento, con_texto: bool) -> dict:
    """El fragmento tal como se publica.

    ⚠️ **`texto` sólo viaja si `con_texto`.** El resto —identificador, obra,
    página, nivel APOS, registro de Duval y estado de verificación— viaja
    siempre, porque son metadatos y `FUENTES.md` los autoriza. Es la diferencia
    entre *«de aquí salió esto»* y *«aquí tienes el pasaje»*.
    """
    fragmento = ficha.fragmento.fragmento
    procedencia = fragmento.procedencia
    datos = {
        "identificador": fragmento.identificador,
        # El MISMO rótulo que el contrato del turno pone en «Material del
        # curso». Dos composiciones del mismo título acabarían discrepando, y
        # discrepar aquí significa que el enlace y su destino se llaman
        # distinto.
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
        # `DD-02` · qué se comprobó de su matemática. Cadena vacía es «sin
        # marca», y se dice así en vez de traducirse a «verificado».
        "verificacion": ficha.fragmento.verificacion_dd02 or "sin marca",
        "localizacion": _localizacion_json(ficha.localizacion),
        "motivo_sin_localizacion": (
            ficha.motivo_sin_localizacion.value if ficha.motivo_sin_localizacion else None
        ),
        # `RP-18` y el encargo de Fase 5: esto es material recuperado del
        # corpus, no una explicación generada, y la interfaz debe poder decirlo
        # sin deducirlo de la pantalla en la que está.
        "naturaleza": "material_del_curso",
    }
    if con_texto:
        documento = convertir(fragmento.texto)
        datos["contenido"] = documento.como_json()
    return datos


#: Cuánto se lee por vez al servir un PDF. 64 KiB es lo que cabe cómodamente
#: en memoria por petición sin convertir el servidor en un almacén de archivos.
_TROZO = 64 * 1024

#: `Range: bytes=inicio-fin`. **Un solo intervalo.** Los rangos múltiples exigen
#: una respuesta `multipart/byteranges` que ningún visor de PDF necesita, y cada
#: forma admitida es una forma más que hay que defender.
_RANGO = re.compile(r"^bytes=(\d*)-(\d*)$")

#: Cabeceras de seguridad de toda respuesta con archivo.
#:
#: - `nosniff` impide que el navegador decida por su cuenta que un PDF es otra
#:   cosa. Sin ella, un archivo mal formado puede acabar interpretado como HTML
#:   y ejecutarse en nuestro origen.
#: - La política de contenido corta el documento entero: un PDF no carga nada.
#:   `frame-ancestors` deja que lo incruste nuestra propia página y nadie más.
#: - `no-store` es deliberado y cuesta rendimiento. El permiso de una obra puede
#:   retirarse, y una copia cacheada seguiría sirviéndose después de la retirada
#:   — que es exactamente el caso que `DD-15` quiere poder ejecutar. Mientras la
#:   caché no sepa de permisos, no se cachea.
_CABECERAS_DE_ARCHIVO = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'self'",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "private, no-store, max-age=0",
    "Accept-Ranges": "bytes",
}


def _nombre_publicado(clave: str, parte: str = "") -> str:
    """Cómo se llama el archivo **para quien lo descarga**.

    ⚠️ **No es el nombre del archivo en el disco.** El de dentro puede ser
    `[Purcell,Varberg,Rigdon]Calculo.pdf`, y publicarlo enseñaría cómo está
    organizado el material del servidor. Se compone con datos que el cliente ya
    conoce —la clave y el nombre catalogado de la parte— así que no revela nada
    nuevo y sigue siendo un nombre útil en la carpeta de descargas.
    """
    return f"{clave}-{parte}.pdf" if parte else f"{clave}.pdf"


def _rango_pedido(cabecera: str, tamano: int) -> tuple[int, int] | None | bool:
    """Interpreta `Range`. `None` sin cabecera; `False` si es inadmisible.

    Se separan los tres desenlaces porque producen tres respuestas distintas:
    sin cabecera se manda el archivo entero (200), con un rango válido su trozo
    (206) y con uno imposible un 416 —no un 200 disimulado, que dejaría al visor
    creyendo que recibió lo que pidió.
    """
    if not cabecera:
        return None
    coincidencia = _RANGO.match(cabecera.strip())
    if not coincidencia:
        return False

    crudo_inicio, crudo_fin = coincidencia.groups()
    if crudo_inicio == "" and crudo_fin == "":
        return False
    if crudo_inicio == "":
        # `bytes=-500`: los últimos 500 octetos.
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
    """Genera el intervalo pedido sin cargar el archivo entero en memoria."""

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
    """El archivo, entero o por rango, con sus cabeceras de seguridad."""
    try:
        tamano = ruta.stat().st_size
    except OSError:
        return _negativa(MotivoIndisponible.ARCHIVO_AUSENTE)
    if tamano == 0:
        # Un PDF de cero octetos no es un PDF. Se dice, en vez de entregarlo y
        # dejar que el visor muestre un error suyo que el equipo no vería.
        return _negativa(MotivoIndisponible.RECURSO_NO_SERVIBLE)

    cabeceras = {
        **_CABECERAS_DE_ARCHIVO,
        # `inline`: se abre en el visor del navegador. La descarga sigue siendo
        # posible desde el propio visor, y forzarla con `attachment` habría
        # convertido «consultar la fuente» en «llevarse el libro».
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
        """Índice institucional de pasajes, sin enviar todavía su texto."""
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

        # La puerta del canal `fragmento`, aplicada **aquí** y no en el cliente.
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
        """La transcripción de una parte, ya en bloques tipados.

        El identificador se **compone** con la clave de la ruta, de modo que
        una parte de otra obra no se puede pedir desde ésta ni aunque su
        nombre coincida.
        """
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
        """El PDF dividido de una parte. **La autorización se vuelve a mirar.**

        No basta con que la pantalla no haya ofrecido el botón: quien escriba
        esta dirección a mano recibe exactamente la misma negativa.
        """
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
            # Sin nombre catalogado y con el archivo ausente son dos hechos: al
            # equipo le falta catalogar en el primer caso y desplegar en el
            # segundo. Un 404 genérico habría mandado a mirar donde no era.
            return _negativa(
                MotivoIndisponible.RECURSO_NO_CATALOGADO
                if not parte.archivo_pdf
                else MotivoIndisponible.ARCHIVO_AUSENTE
            )
        # El nombre se compone con el de la parte **catalogada** y no con el
        # que llegó por la dirección. Hoy son el mismo —la búsqueda sólo
        # acierta si coinciden— pero el que entra por la URL es del cliente, y
        # va a parar a una cabecera: derivarlo del catálogo quita de en medio
        # todo el razonamiento sobre qué podría colarse por ahí.
        return _servir_pdf(
            peticion, ruta, _nombre_publicado(clave, parte.identificador.split(":", 1)[1])
        )

    @router.get("/api/fuentes/obras/{clave}/pdf")
    def pdf_completo(clave: str, peticion: Request) -> Response:
        """El PDF completo de una obra, **sólo cuando exista y esté autorizado**.

        `PIS` no tiene PDF completo según el inventario conocido; las otras
        cuatro obras sí tienen una copia institucional catalogada. Inventarle
        un nombre a `PIS` «para que funcione» seguiría siendo incorrecto.
        """
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
