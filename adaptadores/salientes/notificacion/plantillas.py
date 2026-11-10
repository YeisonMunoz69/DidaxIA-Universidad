"""Plantillas transaccionales de DidaxIa, sin depender del proveedor de correo.

Todo aviso del sistema pasa por el mismo armazón visual, pero conserva título,
etiqueta, color y acción propios. Los valores dinámicos se escapan aquí; el
adaptador de Resend sólo transporta el HTML resultante.
"""

from __future__ import annotations

from html import escape

FUENTE_MANUSCRITA = (
    "Caveat, 'Patrick Hand', 'Ink Free', 'Bradley Hand', Noteworthy, "
    "'Segoe Script', cursive"
)
MASCOTA_PUBLICA = "https://didaxia.pro/favicon-192.png"


def _parrafos(texto: str) -> str:
    bloques = []
    for bloque in texto.strip().split("\n\n"):
        limpio = escape(bloque.strip()).replace("\n", "<br>")
        if limpio:
            bloques.append(
                f'<p style="margin:0 0 14px;font-size:16px;line-height:1.65">{limpio}</p>'
            )
    return "".join(bloques)


def correo_didaxia(  # noqa: PLR0913 -- contrato visual explícito
    *,
    destinatario: str,
    etiqueta: str,
    titulo: str,
    mensaje: str,
    accion: str = "",
    url_accion: str = "",
    color: str = "#b64d00",
    prueba: bool = False,
) -> str:
    """Armazón compatible con clientes restrictivos y sin HTML dinámico crudo."""
    saludo = escape(destinatario.strip() or "Hola")
    rotulo = escape(etiqueta.strip())
    encabezado = escape(titulo.strip())
    color_seguro = color if color in {
        "#b64d00", "#4D6BFE", "#16795b", "#8b3d75", "#A84D08", "#0369A1", "#047857"
    } else "#b64d00"
    boton = ""
    if accion and url_accion:
        enlace = escape(url_accion.strip(), quote=True)
        boton = (
            '<table role="presentation" cellspacing="0" cellpadding="0" style="margin-top:22px">'
            f'<tr><td style="border-radius:12px;background:{color_seguro}">'
            f'<a href="{enlace}" style="display:inline-block;padding:13px 20px;color:#fff;'
            f'text-decoration:none;font-weight:700;font-size:15px">{escape(accion.strip())}</a>'
            "</td></tr></table>"
            f'<p style="margin:18px 0 0;font-size:12px;line-height:1.55;color:#738096">'
            f'Si el botón no abre, copia este enlace:<br><a href="{enlace}" '
            f'style="color:{color_seguro};word-break:break-all">{enlace}</a></p>'
        )
    aviso_prueba = (
        '<tr><td style="padding:10px 24px;text-align:center;background:#fff1c2;'
        'color:#7a4300;font:700 13px Inter,Segoe UI,Arial,sans-serif">'
        'PRUEBA DE PLANTILLA · no corresponde a un evento real</td></tr>'
        if prueba else ""
    )
    return f"""<!doctype html>
<html lang="es"><body style="margin:0;background:#f5f3ee;color:#172033;font-family:Inter,Segoe UI,Arial,sans-serif">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f3ee"><tr><td align="center" style="padding:32px 14px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:620px;background:#fffdf8;border:1px solid #ccd4df;border-radius:22px;overflow:hidden">
<tr><td style="height:10px;background:{color_seguro}"></td></tr>{aviso_prueba}
<tr><td style="padding:28px 34px 10px;text-align:center;background:#fff9e8">
<div style="color:{color_seguro};font:700 13px ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.08em">{rotulo}</div>
<img src="{MASCOTA_PUBLICA}" width="68" height="68" alt="Mascota de DidaxIa" style="display:block;margin:16px auto 7px;border:0;border-radius:18px">
<div style="font-family:{FUENTE_MANUSCRITA};font-size:36px;font-weight:700;color:#111827">DidaxIa</div>
</td></tr>
<tr><td style="padding:24px 34px 34px">
<p style="margin:0 0 16px;font-size:16px;line-height:1.6">{saludo},</p>
<h1 style="margin:0 0 16px;font-size:25px;line-height:1.25;color:#111827">{encabezado}</h1>
{_parrafos(mensaje)}{boton}
<p style="margin:26px 0 0;padding-top:18px;border-top:1px solid #e3e7ed;font-size:12px;line-height:1.55;color:#738096">Mensaje enviado por DidaxIa, sistema de apoyo al estudio del cálculo diferencial.</p>
</td></tr></table></td></tr></table></body></html>"""


def solicitud_de_matricula(
    *, destinatario: str, estudiante: str, clase: str, url_accion: str, prueba: bool = False
) -> str:
    """Correo compatible con clientes restrictivos; todos los datos dinámicos se escapan."""
    return correo_didaxia(
        destinatario=destinatario,
        etiqueta="SOLICITUD DE MATRÍCULA",
        titulo="Hay una nueva solicitud de matrícula",
        mensaje=(
            f"{estudiante.strip() or 'Un estudiante'} solicitó ingresar a "
            f"«{clase.strip() or 'tu clase'}».\n\nLa matrícula no cambia hasta que una "
            "persona autorizada revise y resuelva la solicitud."
        ),
        accion="Revisar solicitud",
        url_accion=url_accion,
        prueba=prueba,
    )


def decision_registrada(*, destinatario: str, url_accion: str, prueba: bool = False) -> str:
    return correo_didaxia(
        destinatario=destinatario,
        etiqueta="AUTORIZACIÓN Y PRIVACIDAD",
        titulo="Tu autorización quedó registrada",
        mensaje=(
            "Registramos tu decisión sobre el tratamiento de tus datos en DidaxIa.\n\n"
            "Puedes consultar la versión y la fecha desde «Mis datos». Si no fuiste tú, "
            "entra y retira la autorización."
        ),
        accion="Ver mis autorizaciones",
        url_accion=url_accion,
        color="#16795b",
        prueba=prueba,
    )


def supresion_recibida(*, destinatario: str, url_accion: str, prueba: bool = False) -> str:
    return correo_didaxia(
        destinatario=destinatario,
        etiqueta="DERECHOS SOBRE TUS DATOS",
        titulo="Solicitud de eliminación recibida",
        mensaje=(
            "Tu solicitud quedó registrada. Consulta su estado y sus plazos desde «Mis datos».\n\n"
            "Si no fuiste tú, entra a DidaxIa y cancela la solicitud dentro del plazo disponible."
        ),
        accion="Consultar mi solicitud",
        url_accion=url_accion,
        color="#8b3d75",
        prueba=prueba,
    )


def invitacion_institucional(
    *, destinatario: str, rol: str, correo: str, vence: str, url_accion: str,
    prueba: bool = False,
) -> str:
    return correo_didaxia(
        destinatario=destinatario,
        etiqueta="EQUIPO INSTITUCIONAL",
        titulo="Te invitaron a colaborar en DidaxIa",
        mensaje=(
            f"La invitación concede la función de {rol}. Inicia sesión con {correo}.\n\n"
            f"La invitación vence el {vence} y sólo funciona para la cuenta indicada."
        ),
        accion="Aceptar invitación",
        url_accion=url_accion,
        color="#4D6BFE",
        prueba=prueba,
    )


def alerta_operativa(
    *, titulo: str, mensaje: str, recuperado: bool = False, prueba: bool = False
) -> str:
    return correo_didaxia(
        destinatario="Equipo de operación",
        etiqueta="SERVICIO RESTABLECIDO" if recuperado else "ALERTA OPERATIVA",
        titulo=titulo,
        mensaje=mensaje,
        accion="Consultar salud del sistema",
        url_accion="https://app.didaxia.pro/api/salud",
        color="#16795b" if recuperado else "#8b3d75",
        prueba=prueba,
    )


def mensaje_institucional(
    *, destinatario: str, titulo: str, mensaje: str, prueba: bool = False,
    color: str = "#4D6BFE", accion: bool = False,
) -> str:
    return correo_didaxia(
        destinatario=destinatario,
        etiqueta="COMUNICACIÓN DEL EQUIPO DE INVESTIGACIÓN",
        titulo=titulo,
        mensaje=mensaje,
        color=color,
        accion="Abrir DidaxIa" if accion else "",
        url_accion="https://app.didaxia.pro/mi-perfil" if accion else "",
        prueba=prueba,
    )
