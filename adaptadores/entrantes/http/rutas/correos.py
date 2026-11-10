from __future__ import annotations

import asyncio
import base64
import binascii
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, mantenimiento, requerir_rol
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from adaptadores.salientes.notificacion.plantillas import (
    alerta_operativa,
    decision_registrada,
    invitacion_institucional,
    mensaje_institucional,
    solicitud_de_matricula,
    supresion_recibida,
)
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible, EscrituraRechazada

if TYPE_CHECKING:
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.gobierno import PuertoAuditoria, PuertoNotificacion

MAX_DESTINATARIOS = 35
MAX_ADJUNTOS = 3
MAX_ADJUNTOS_BYTES = 5 * 1024 * 1024
MAX_ASUNTO = 160
MAX_MENSAJE = 8_000
ENFASIS = {"oxido": "#A84D08", "azul": "#0369A1", "esmeralda": "#047857", "purpura": "#8b3d75"}
_VARIABLES = frozenset({"cohorte", "nodo_didactico", "fecha_limite"})
_VARIABLE = re.compile(r"\{(nombre|cohorte|nodo_didactico|fecha_limite)\}")
_CORREO = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_TIPOS_ADMITIDOS = frozenset({
    "application/pdf", "image/png", "image/jpeg", "text/plain", "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
})
_EXTENSION_DE_TIPO = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": (".jpg", ".jpeg"),
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
}
_PIEZA_OFFICE = {
    ".docx": "word/document.xml",
    ".xlsx": "xl/workbook.xml",
    ".pptx": "ppt/presentation.xml",
}


@dataclass(frozen=True, slots=True)
class Destinatario:
    nombre: str
    correo: str

_PLANTILLAS = (
    ("mensaje-institucional", "Mensaje institucional", "Comunicación libre con identidad visual DidaxIa."),
    ("solicitud-matricula", "Solicitud de matrícula", "Aviso al docente o al equipo de investigación."),
    ("invitacion-rol", "Invitación institucional", "Invitación para asumir una función autorizada."),
    ("autorizacion-registrada", "Autorización registrada", "Confirmación al titular de su decisión."),
    ("supresion-recibida", "Solicitud de eliminación", "Confirmación de recepción de un trámite."),
    ("alerta-caida", "Alerta de disponibilidad", "Aviso operativo cuando PostgreSQL no responde."),
    ("alerta-recuperacion", "Servicio restablecido", "Aviso operativo de recuperación."),
)
_IDENTIFICADORES = frozenset(item[0] for item in _PLANTILLAS)


def _error(detalle: str, estado: int = 400) -> JSONResponse:
    return JSONResponse({"detalle": detalle}, status_code=estado)

def _destinatarios(valor: object) -> tuple[Destinatario, ...]:
    if not isinstance(valor, list) or not valor:
        raise ValueError("agrega al menos un destinatario")
    if len(valor) > MAX_DESTINATARIOS:
        raise ValueError(f"se admiten máximo {MAX_DESTINATARIOS} destinatarios por envío")
    unicos: dict[str, Destinatario] = {}
    for item in valor:
        if not isinstance(item, dict):
            raise ValueError("cada destinatario debe incluir nombre y correo")
        nombre = str(item.get("nombre") or "").strip()
        correo = str(item.get("correo") or "").strip()
        if any(c in correo for c in "\r\n") or len(correo) > 254 or not _CORREO.fullmatch(correo):
            raise ValueError("hay una dirección de correo no admisible")
        if len(nombre) > 100 or any(c in nombre for c in "\r\n"):
            raise ValueError("hay un nombre de destinatario no admisible")
        unicos.setdefault(correo.casefold(), Destinatario(nombre=nombre, correo=correo))
    return tuple(unicos.values())

def _validar_contenido(nombre: str, tipo: str, contenido: bytes) -> None:
    extension = Path(nombre).suffix.lower()
    esperada = _EXTENSION_DE_TIPO[tipo]
    if extension not in ((esperada,) if isinstance(esperada, str) else esperada):
        raise ValueError(f"la extensión de «{nombre}» no corresponde a su tipo")
    if tipo == "application/pdf" and not contenido.startswith(b"%PDF-"):
        raise ValueError(f"«{nombre}» no contiene un PDF reconocible")
    if tipo == "image/png" and not contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"«{nombre}» no contiene una imagen PNG reconocible")
    if tipo == "image/jpeg" and not contenido.startswith(b"\xff\xd8\xff"):
        raise ValueError(f"«{nombre}» no contiene una imagen JPEG reconocible")
    if tipo in {"text/plain", "text/csv"}:
        try:
            texto = contenido.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError(f"«{nombre}» debe ser texto UTF-8") from None
        if "\x00" in texto:
            raise ValueError(f"«{nombre}» no contiene texto admisible")
    if extension in _PIEZA_OFFICE:
        try:
            with zipfile.ZipFile(io.BytesIO(contenido)) as paquete:
                nombres = frozenset(paquete.namelist())
        except (OSError, zipfile.BadZipFile):
            raise ValueError(f"«{nombre}» no contiene un documento Office reconocible") from None
        if "[Content_Types].xml" not in nombres or _PIEZA_OFFICE[extension] not in nombres:
            raise ValueError(f"«{nombre}» no contiene un documento Office reconocible")

def _adjuntos(valor: object) -> tuple[tuple[dict[str, str], ...], int]:
    if valor in (None, []):
        return (), 0
    if not isinstance(valor, list) or len(valor) > MAX_ADJUNTOS:
        raise ValueError(f"se admiten máximo {MAX_ADJUNTOS} archivos")
    salida = []
    total = 0
    for item in valor:
        if not isinstance(item, dict):
            raise ValueError("cada archivo adjunto debe ser un objeto")
        nombre = str(item.get("nombre") or "").strip()
        tipo = str(item.get("tipo") or "").strip().lower()
        contenido = str(item.get("contenido") or "").strip()
        if not nombre or len(nombre) > 120 or any(c in nombre for c in "/\\\r\n\0"):
            raise ValueError("hay un nombre de archivo no admisible")
        if tipo not in _TIPOS_ADMITIDOS:
            raise ValueError(f"el tipo de «{nombre}» no está admitido")
        try:
            bytes_archivo = base64.b64decode(contenido, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError(f"el contenido de «{nombre}» no es Base64 válido") from None
        if not bytes_archivo:
            raise ValueError(f"«{nombre}» está vacío")
        _validar_contenido(nombre, tipo, bytes_archivo)
        total += len(bytes_archivo)
        if total > MAX_ADJUNTOS_BYTES:
            raise ValueError("los adjuntos superan 5 MB en total")
        salida.append({
            "filename": nombre,
            "content": base64.b64encode(bytes_archivo).decode("ascii"),
        })
    return tuple(salida), total

def _contenido(
    plantilla: str, destinatario: Destinatario, asunto: str, mensaje: str,
    *, enfasis: str = "",
) -> tuple[str, str]:
    nombre = destinatario.nombre or "Hola"
    if plantilla == "mensaje-institucional":
        return asunto, mensaje_institucional(
            destinatario=nombre, titulo=asunto, mensaje=mensaje,
            color=ENFASIS[enfasis] if enfasis else "#4D6BFE", accion=bool(enfasis),
        )
    if plantilla == "solicitud-matricula":
        return "[Prueba] Nueva solicitud para tu clase en DidaxIa", solicitud_de_matricula(
            destinatario=nombre, estudiante="Estudiante de ejemplo",
            clase="Cálculo Diferencial · grupo de prueba",
            url_accion="https://app.didaxia.pro/mis-clases", prueba=True,
        )
    if plantilla == "invitacion-rol":
        return "[Prueba] Invitación institucional a DidaxIa", invitacion_institucional(
            destinatario=nombre, rol="investigador delegado", correo=destinatario.correo,
            vence="fecha de ejemplo", url_accion="https://app.didaxia.pro/", prueba=True,
        )
    if plantilla == "autorizacion-registrada":
        return "[Prueba] Tu autorización quedó registrada", decision_registrada(
            destinatario=nombre, url_accion="https://app.didaxia.pro/mis-datos", prueba=True,
        )
    if plantilla == "supresion-recibida":
        return "[Prueba] Solicitud de eliminación recibida", supresion_recibida(
            destinatario=nombre, url_accion="https://app.didaxia.pro/mis-datos", prueba=True,
        )
    recuperado = plantilla == "alerta-recuperacion"
    titulo = "DidaxIa · la base de datos volvió a responder" if recuperado else "DidaxIa · la base de datos no responde"
    texto = (
        "La base de datos volvió a responder. Incidente de ejemplo."
        if recuperado else
        "La base de datos lleva más de dos minutos sin responder. Incidente de ejemplo."
    )
    return f"[Prueba] {titulo}", alerta_operativa(
        titulo=titulo, mensaje=texto, recuperado=recuperado, prueba=True
    )

def _catalogo() -> list[dict]:
    muestra = Destinatario(nombre="Persona destinataria", correo="persona@example.com")
    salida = []
    for identificador, nombre, descripcion in _PLANTILLAS:
        asunto = "Comunicación del equipo de investigación" if identificador == "mensaje-institucional" else ""
        mensaje = "Este es un mensaje de ejemplo redactado por el equipo de investigación."
        asunto_final, html = _contenido(identificador, muestra, asunto, mensaje)
        salida.append({
            "id": identificador, "nombre": nombre, "descripcion": descripcion,
            "asunto_ejemplo": asunto_final, "html": html,
            "solo_prueba": identificador != "mensaje-institucional",
        })
    return salida

def crear_router(
    sesiones: Sesiones,
    notificacion: PuertoNotificacion,
    auditoria: PuertoAuditoria,
    puerta: PuertaDeSupresion,
    *,
    canal_configurado: bool,
    pausa_entre_envios_s: float = 0.2,
) -> APIRouter:
    router = APIRouter()

    def _acceso(peticion: Request):
        negativa = requerir_rol(sesiones, peticion, "investigador")
        if negativa is not None:
            return None, negativa
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        congelada = puerta.negativa(sujeto_de(datos))
        return datos, congelada

    @router.get("/api/investigacion/correos/plantillas")
    def listar_plantillas(peticion: Request):
        _datos, negativa = _acceso(peticion)
        if negativa is not None:
            return negativa
        return {"plantillas": _catalogo(), "canal_configurado": canal_configurado,
                "limites": {"destinatarios": MAX_DESTINATARIOS, "adjuntos": MAX_ADJUNTOS,
                            "adjuntos_bytes": MAX_ADJUNTOS_BYTES}}

    def preparar(cuerpo):
        plantilla = str(cuerpo.get("plantilla") or "").strip()
        if plantilla not in _IDENTIFICADORES:
            raise ValueError("elige una plantilla disponible")
        asunto = str(cuerpo.get("asunto") or "").strip()
        mensaje = str(cuerpo.get("mensaje") or "").strip()
        enfasis = str(cuerpo.get("enfasis") or "")
        variables = cuerpo.get("variables") or {}
        if not isinstance(variables, dict) or any(clave not in _VARIABLES for clave in variables):
            raise ValueError("hay variables de mensaje no admitidas")
        if any(not isinstance(valor, str) or len(valor) > 200 for valor in variables.values()):
            raise ValueError("cada variable admite hasta 200 caracteres")
        if enfasis and enfasis not in ENFASIS:
            raise ValueError("elige un énfasis disponible")
        destinos = _destinatarios(cuerpo.get("destinatarios"))
        copias = []
        for destino in destinos:
            if plantilla == "mensaje-institucional":
                def reemplazar(coincidencia, nombre=destino.nombre):
                    clave = coincidencia[1]
                    valor = (nombre or "Hola") if clave == "nombre" else variables.get(clave, "")
                    if not valor.strip():
                        raise ValueError(f"completa la variable {{{clave}}} antes de continuar")
                    return valor.strip()
                titulo = _VARIABLE.sub(reemplazar, asunto)
                texto = _VARIABLE.sub(reemplazar, mensaje)

                etiquetas = {"cohorte": "Clase o grupo", "nodo_didactico": "Nodo didáctico",
                             "fecha_limite": "Fecha u horario acordado"}
                adicionales = [f"{etiqueta}: {valor.strip()}" for clave, etiqueta in etiquetas.items()
                               if (valor := variables.get(clave, "")) and valor.strip()
                               and f"{{{clave}}}" not in f"{asunto}\n{mensaje}"]
                if adicionales:
                    texto += "\n\n" + "\n".join(adicionales)
                if not titulo or len(titulo) > MAX_ASUNTO:
                    raise ValueError(f"el asunto debe tener entre 1 y {MAX_ASUNTO} caracteres")
                if not texto or len(texto) > MAX_MENSAJE:
                    raise ValueError(f"el mensaje debe tener entre 1 y {MAX_MENSAJE} caracteres")
            else:
                titulo, texto = asunto, mensaje
            asunto_final, html = _contenido(plantilla, destino, titulo, texto, enfasis=enfasis)
            copias.append((destino, asunto_final, texto, html))
        return plantilla, copias

    @router.post("/api/investigacion/correos/vista-previa")
    async def vista_previa(peticion: Request):
        _datos, negativa = _acceso(peticion)
        if negativa is not None:
            return negativa
        try:
            _, copias = preparar(await json_del_cuerpo(peticion))
        except ValueError as error:
            return _error(str(error))
        _, asunto, _, html = copias[0]

        return {"asunto": asunto, "html": html}

    @router.post("/api/investigacion/correos/enviar")
    async def enviar(peticion: Request):
        datos, negativa = _acceso(peticion)
        if negativa is not None:
            return negativa
        cuerpo = await json_del_cuerpo(peticion)
        if cuerpo.get("confirmado") is not True:
            return _error("confirma expresamente el envío")
        try:
            plantilla, copias = preparar(cuerpo)
            adjuntos, bytes_adjuntos = _adjuntos(cuerpo.get("adjuntos"))
        except ValueError as error:
            return _error(str(error))

        actor = sujeto_de(datos)
        try:
            registro = auditoria.registrar(
                "correo.institucional_intentado",
                actor=actor,
                detalle={
                    "plantilla": plantilla,
                    "destinatarios": len(copias),
                    "adjuntos": len(adjuntos),
                    "bytes_adjuntos": bytes_adjuntos,
                    "canal_configurado": canal_configurado,
                },
            )
        except EscrituraRechazada as error:
            return _error(str(error), 409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo auditar el envío; no se envió ningún correo")

        resultados = []
        for indice, (destino, asunto_final, mensaje, html) in enumerate(copias, start=1):

            if indice > 1 and pausa_entre_envios_s > 0:
                await asyncio.sleep(pausa_entre_envios_s)
            texto = mensaje if plantilla == "mensaje-institucional" else (
                "Este es un ensayo visual de una plantilla de DidaxIa. No corresponde a un evento real."
            )

            salio = await asyncio.to_thread(
                notificacion.avisar,
                destino.correo,
                asunto_final,
                texto,
                clave_idempotencia=f"correo-institucional/{registro.secuencia}/{indice}",
                html=html,
                adjuntos=adjuntos,
            )
            resultados.append({"indice": indice, "enviado": salio})

        enviados = sum(resultado["enviado"] for resultado in resultados)
        return {
            "auditoria": registro.secuencia,
            "canal_configurado": canal_configurado,
            "destinatarios": len(copias),
            "enviados": enviados,
            "fallidos": len(copias) - enviados,
            "resultados": resultados,
        }

    return router
