from __future__ import annotations

import os

from dominio.modelo.acceso import (
    AccesoCalculado,
    permite_escritura_longitudinal,
)


MAYORIA_DE_EDAD = 18


CICLO_DE_VIDA = (
    {
        "que": "Conversaciones e inferencias conductuales",
        "al_sustentar": "Se suprimen, o se anonimizan de forma irreversible.",
    },
    {
        "que": "Resultados agregados y anonimizados",
        "al_sustentar": "Se conservan. Son la evidencia del trabajo de grado.",
    },
    {
        "que": "Corpus, banco de conceptos, grafo, código",
        "al_sustentar": "No son datos personales. Se quedan.",
    },
    {
        "que": "Cualquier dato del piloto",
        "al_sustentar": (
            "Nunca pasa a una versión comercial. Si el producto crece, "
            "arranca con consentimiento nuevo."
        ),
    },
)


CLAUSULA_DE_AGREGADOS = {
    "revisado": False,
    "origen": "DECISIONES-PENDIENTES.md § D-29 (C-02) · pendiente de firma de la dirección",
    "titulo": "Sobre los resultados ya calculados",
    "texto": (
        "Usted puede pedir en cualquier momento que borremos sus datos, y lo "
        "haremos: sus conversaciones y su perfil dejarán de existir y nadie "
        "podrá volver a relacionarlos con usted. Hay una sola cosa que no "
        "podemos deshacer, y preferimos decírsela ahora: si para cuando usted "
        "lo pida ya calculamos un resultado de conjunto —un promedio, un "
        "conteo, una gráfica del grupo—, ese resultado se queda como está. No "
        "contiene su nombre, ni su correo, ni nada que permita señalarlo a "
        "usted dentro de él, y rehacerlo obligaría a rehacer el estudio "
        "entero. Sus datos se van; los promedios que ya existían, no."
    ),

    "contrapartida": (
        "Le contaremos cuántas personas pidieron el borrado y en qué momento "
        "del estudio, porque eso forma parte de leer bien los resultados."
    ),
}


TECHO_DE_RETENCION_MESES = 24


def retencion_declarada() -> dict:
    hasta = os.environ.get("AGENTE_RETENCION_HASTA", "").strip()
    return {
        "regla": (
            "min(sustentación + 6 meses, recolección + 24 meses); "
            "manda la que venza primero"
        ),
        "sustentacion_fijada": bool(hasta),
        "sustentacion_mas_seis_meses": hasta or None,
        "techo_meses_desde_la_recoleccion": TECHO_DE_RETENCION_MESES,
        "nota": (
            "Sin fecha de sustentación manda el techo de 24 meses. Vacío no "
            "significa sin límite."
        ),
    }

MOTIVO_DE_BLOQUEO = (
    "Para participar en este piloto hay que ser mayor de edad. El sistema no "
    "tiene todavía el régimen reforzado que la ley exige para tratar datos de "
    "menores (RL-10), así que no puede ofrecerte una versión reducida: no "
    "puedes participar. Si te equivocaste al escribir tu edad, abre una sesión "
    "nueva."
)


def modo_piloto() -> bool:
    return bool(os.environ.get("AGENTE_PILOTO_TESIS", "").strip())

def edad_por_defecto() -> int | None:
    return MAYORIA_DE_EDAD if modo_piloto() else None

def edad_declarada(datos_de_sesion: dict) -> int | None:
    edad = datos_de_sesion.get("edad")
    if isinstance(edad, bool) or not isinstance(edad, int):
        return None
    return edad

def puede_participar(datos_de_sesion: dict) -> bool:
    if datos_de_sesion.get("consentimiento") == "otorgado":
        return True
    edad = edad_declarada(datos_de_sesion)
    return edad is None or edad >= MAYORIA_DE_EDAD

def modulo_conductual_habilitado(datos_de_sesion: dict) -> bool:
    edad = edad_declarada(datos_de_sesion)
    return edad is not None and edad >= MAYORIA_DE_EDAD

def permite_escritura_conductual(
    datos_de_sesion: dict, acceso: AccesoCalculado | None
) -> bool:

    if acceso is None:

        return False
    return permite_escritura_longitudinal(acceso) and modulo_conductual_habilitado(
        datos_de_sesion
    )

def bloque_legal() -> dict:
    return {
        "ciclo_de_vida": list(CICLO_DE_VIDA),

        "retencion": retencion_declarada(),
        "clausula_de_agregados": dict(CLAUSULA_DE_AGREGADOS),
        "responsable_hasta_la_entrega": (
            "Los autores del proyecto son responsables del tratamiento hasta "
            "la entrega. Si la institución mantiene el despliegue después de "
            "eso, la responsabilidad pasa a ser suya."
        ),
        "mayoria_de_edad": {
            "requerida": True,
            "edad_minima": MAYORIA_DE_EDAD,

            "asumida_por_defecto": modo_piloto(),
            "motivo": (
                "RL-09: quien declara ser menor de edad no puede participar en "
                "el piloto. No hay régimen reforzado para menores implementado "
                "todavía (RL-10), así que no existe una versión reducida que "
                "ofrecerle. DD-26 asume la mayoría de edad por defecto durante "
                "el piloto: es un valor declarado, no una verificación."
            ),
        },
    }
