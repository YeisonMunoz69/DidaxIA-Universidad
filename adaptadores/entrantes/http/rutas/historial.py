"""
historial.py — `GET /api/historial` y el hilo · `PM-B37` · `RF-ORQ-02`
==========================================================================

Las rutas del historial de conversación. **El contrato es el de
`OE3-Implementacion/08-Contrato-del-Turno.md` §13 y no se improvisa**: es la
frontera contra la que Fabián construye el carril de conversaciones de
`PM-F20`, y los dos carriles tienen que estar construyendo contra la misma
forma. Cualquier cambio se acuerda con él antes, no después.

Autorización, no solo autenticación · `B3` del encargo
----------------------------------------------------------
La clave sale de `sujeto_de(datos)`, **jamás de un parámetro del cliente**. Y
el hilo se pide con su identificador en la URL, así que hay que comprobar que
esa conversación es suya:

> **`404` y no `403`.** Un `403` dice «existe pero no es tuya», que es
> justamente lo que no se puede confirmar sobre la conversación de otra
> persona. El `404` no distingue entre «no existe» y «no es suya», y esa
> indistinción es la garantía.

No se comprueba en Python después de leer: el sujeto va en el `WHERE` del
adaptador, así que una conversación ajena devuelve vacío **sin haber leído nada
de otro titular**.

⚠️ Una caída no es una lista vacía · hito R6
--------------------------------------------------------------------
Aquí había un `except` de captura total en el listado, que devolvía la lista
vacía del contrato, y otro en el hilo, que acababa en `404`.
Las dos convertían «no se puede saber» en una afirmación sobre los datos de
alguien:

- la lista vacía le dice al estudiante **«no tienes conversaciones»** cuando el
  historial es obligatorio durante el piloto, y le invita a empezar de cero lo
  que sigue guardado;
- el `404` mezcla una respuesta de **autorización** con una de
  **disponibilidad**, y deja al cliente sin poder distinguirlas.

`EQ-024` pide lo contrario: *«separa salud de proceso y disponibilidad, muestra
mantenimiento»*. Ahora un fallo del almacén sube y sale como **503**. `404`
vuelve a significar una sola cosa: la consulta se hizo bien y no hay nada de
este titular con ese identificador.

⚠️ Cada lectura de una conversación se audita · `EQ-023`
--------------------------------------------------------------------
*«Cada consulta de una conversación y cada cambio de permisos quedan
registrados.»* La constancia la escribe el adaptador **dentro de la misma
transacción** que la lectura, y **antes** del `SELECT`: si la auditoría falla, la
transacción no confirma y no se devuelve nada, así que no existe una consulta sin
registro. Al revés —auditar después— un fallo dejaría la conversación ya leída y
sin rastro de quién la leyó.

Lo que se registra es **qué conversación**, nunca su contenido: la auditoría se
conserva más tiempo que lo que audita, y copiar el texto ahí duplicaría en una
tabla de retención larga justo lo que una supresión tendría que borrar.

El listado no se audita, y la diferencia es del contrato: `EQ-023` habla de
*«cada consulta de una conversación»*. El carril lateral pide la lista en cada
carga de pantalla, y un registro por refresco enterraría los accesos reales a
contenido bajo miles de filas de metadatos propios.

⚠️ No se borra por conversación · hito R2
--------------------------------------------------------------------
`DELETE /api/historial/{sesion}` borraba un hilo entero de `historial_turno`.
`EQ-016` punto 6 dice que *«el historial es obligatorio para usar el tutor»*, y
`EQ-022` reserva toda eliminación al trámite reversible. Responde 410.

El título se deriva, no se guarda · `T-06`
-----------------------------------------------
De un planteamiento del estudiante, **en la respuesta del API**. Se prioriza el
primero con contenido matemático frente a un saludo inicial y se conserva una
fórmula marcada completa para su presentación con KaTeX. Una
columna de título obligaría a decidir quién la edita, a suprimirla también, y a
mantenerla en paso con un texto que no cambia. Derivarla no cuesta nada y se
puede promover a columna el día que alguien quiera renombrar conversaciones.


"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento, requerir_sesion
from adaptadores.entrantes.http.sesiones import Sesiones, sujeto_de
from dominio.puertos.almacen import ErrorDeAlmacen

if TYPE_CHECKING:  # pragma: no cover
    from datetime import datetime

#: `T-06` · cuántos caracteres del primer mensaje titulan la conversación.
#: Corto porque titula una fila de un carril lateral, no un documento.
LARGO_DEL_TITULO = 60
LARGO_FORMULA_TITULO = 512
FORMULA_TITULO = re.compile(r"\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$([^$\n]+?)\$|`([^`\n]+)`")

#: `EQ-023` · con qué nombre queda registrada la lectura de un hilo. Constante y
#: no una cadena suelta: es lo que una consulta de auditoría busca, y dos
#: redacciones distintas del mismo hecho harían que la mitad no apareciera.
OPERACION_CONSULTA = "conversacion.consultada"


def titulo_de(primer_mensaje: str) -> str:
    """Título derivado del planteamiento seleccionado, sin reescribir el hilo.

    Recorta por caracteres y no por palabras a propósito: un mensaje puede no
    tener espacios —una fórmula pegada— y partir por palabras devolvería el
    mensaje entero o nada. El puntuado final avisa de que hay más.

    Cadena vacía si no hay primer mensaje: es preferible a inventar un «Sin
    título» que el cliente no puede distinguir de un título de verdad.
    """
    limpio = " ".join((primer_mensaje or '').split())
    if re.fullmatch(r'(?:hola|buenos días|buenas tardes|buenas noches|gracias|muchas gracias|ok|vale)[!,.:;\s]*', limpio, flags=re.I):
        return 'Conversación de cálculo'
    limpio = re.sub(r'^(?:hola|buenos días|buenas tardes|buenas noches)[!,.:;\s]+', '', limpio, flags=re.I)
    formula = FORMULA_TITULO.search(limpio)
    if formula:
        expresion = next(g for g in formula.groups() if g is not None)
        # Un código entre backticks sólo se vuelve matemática si hay notación
        # explícita. No se convierte código o prosa ordinaria en una ecuación.
        es_codigo = formula.group(5) is not None
        if not es_codigo or re.search(r'[=^_]|\\(?:frac|lim|sqrt|int|sum)\b', expresion):
            asunto = 'Consulta'
            if re.search(r'deriv', limpio, re.I):
                asunto = 'Derivada'
            elif re.search(r'l[ií]mit|\\lim\b', limpio, re.I):
                asunto = 'Límite'
            elif re.search(r'integral|\\int\b', limpio, re.I):
                asunto = 'Integral'
            if len(expresion) <= LARGO_FORMULA_TITULO:
                return f'{asunto} · ${expresion}$'
            return f'{asunto} · expresión matemática extensa'
    # No cortar una marca abierta de una fórmula histórica: el texto completo
    # sigue en el hilo; el título usa la prosa anterior o una etiqueta neutral.
    if len(limpio) > LARGO_DEL_TITULO and ('$' in limpio or '\\(' in limpio or '\\[' in limpio):
        prosa = re.split(r'\$|\\\(|\\\[', limpio, maxsplit=1)[0].strip()
        limpio = prosa or 'Consulta de cálculo'
    if len(limpio) <= LARGO_DEL_TITULO:
        return limpio
    return limpio[: LARGO_DEL_TITULO - 1].rstrip() + "…"


def _momento(valor: datetime | str | None) -> str | None:
    """La marca temporal como la espera el contrato: ISO-8601, o `None`.

    `psycopg` devuelve `datetime` con zona; el contrato de §13 del contrato muestra
    cadenas. Se convierte aquí y no en el adaptador porque es una decisión de
    presentación del borde, no del almacén.
    """
    if valor is None:
        return None
    return valor if isinstance(valor, str) else valor.isoformat()


def _material_como_contrato(piezas: list[dict], catalogo) -> list[dict]:
    """El material persistido, con la MISMA forma que el del turno en vivo.

    `08-Contrato-del-Turno.md` §7 y el hilo tienen que decir lo mismo: si el
    turno en vivo entrega `{id, obra, titulo, relacion}` y el historial
    entregara `{fragmento, obra, relacion, similitud}`, la pantalla necesitaría
    dos lectores para la misma sección y acabarían discrepando.

    ⚠️ **`similitud` NO viaja.** Se persiste porque `ADR-006` U5 la necesita
    para calibrar el umbral, y ésa es una pregunta del OE4, no del estudiante.
    Un número junto a una fuente se lee como «cuánto la respalda», y no es eso:
    es cuánto se parecía el texto a la consulta. Enseñarlo afirmaría algo que
    el sistema no sostiene.
    """
    return [
        {
            "id": pieza["fragmento"],
            "obra": pieza["obra"],
            "titulo": (
                catalogo.titulo_de_fragmento(pieza["fragmento"])
                if catalogo is not None
                else pieza["fragmento"]
            ),
            "relacion": pieza["relacion"],
        }
        for pieza in piezas
    ]


def conversaciones_como_contrato(filas: list[dict]) -> dict:
    """`GET /api/historial`, con la forma exacta del contrato §13.1."""
    return {
        "conversaciones": [
            {
                "sesion": fila["sesion"],
                "titulo": titulo_de(fila.get("mensaje_para_titulo") or fila["primer_mensaje"]),
                "inicio": _momento(fila["inicio"]),
                "ultimo": _momento(fila["ultimo"]),
                "turnos": fila["turnos"],
            }
            for fila in filas
        ]
    }


def hilo_como_contrato(
    identificador_sesion: str, mensajes: list[dict], catalogo=None
) -> dict:
    """`GET /api/historial/{sesion}`, con la forma exacta del contrato §13.2.

    ⚠️ **`degradado` solo aparece cuando lo es** —así lo dibuja el contrato,
    «solo cuando lo es»—. Un `false` en cada mensaje normal sería ruido en el
    99% de las filas y obligaría al cliente a leerlo para nada.

    El orden es el que trae el adaptador, que ordena por `id` y **no por
    `momento`**: las dos voces de un turno comparten marca —un solo `_reloj()`
    por turno— así que ordenar por tiempo las devolvería en orden arbitrario.
    """
    return {
        "sesion": identificador_sesion,
        "mensajes": [
            {
                "turno": m["turno"],
                "momento": _momento(m["momento"]),
                "autor": m["autor"],
                "contenido": m["contenido"],
                # `PM-B25` · lo que el estudiante VIO. Sin `bloques` el hilo no
                # dice qué se verificó, y sin `citas` no se puede sustituir la
                # marca `{{c1}}` — el sidebar la mostraría cruda, que es el
                # fallo que este proyecto ya cometió en pantalla el 2026-08-11.
                **({"bloques": m["bloques"]} if m.get("bloques") else {}),
                **({"citas": m["citas"]} if m.get("citas") else {}),
                **({"nivel": m["nivel"]} if m.get("nivel") else {}),
                **(
                    {
                        "procedencia": {
                            **m["procedencia"],
                            # Fase 5 · las piezas navegables. Las filas
                            # anteriores a la migración 15 no tienen ninguna y
                            # el cliente cae a `referencia`, que sí tienen.
                            "material": _material_como_contrato(
                                m.get("material", []), catalogo
                            ),
                        }
                    }
                    if m.get("procedencia", {}).get("origen")
                    else {}
                ),
                **({"degradado": True} if m["degradado"] else {}),
            }
            for m in mensajes
        ],
    }


def crear_router(sesiones: Sesiones, adaptador_historial, catalogo=None) -> APIRouter:
    router = APIRouter()

    def _sin_almacen() -> Response:
        """Sin `AGENTE_BD`. No se finge una lista vacía: eso diría «no tiene
        conversaciones» cuando lo cierto es «no se puede saber».
        `GET /api/salud` ya publica el motivo (`A4`)."""
        return mantenimiento("el historial no está disponible en este despliegue")

    @router.get("/api/historial")
    def listar_historial(peticion: Request) -> Response:
        """Las conversaciones del titular, de la más reciente hacia atrás.

        `200` con lista vacía cuando no hay nada: no tener historial es un
        estado normal y no un error, y un `404` obligaría al cliente a tratar
        el primer día como una avería. Un fallo del almacén, en cambio, es
        `503`: ver la cabecera sobre por qué no son lo mismo.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if adaptador_historial is None:
            return _sin_almacen()
        try:
            filas = adaptador_historial.historial_de(sujeto_de(datos))
        except ErrorDeAlmacen:
            return mantenimiento("no se pudo leer el historial en este momento")
        return JSONResponse(conversaciones_como_contrato(filas))

    @router.get("/api/historial/{identificador_sesion}")
    def leer_hilo(identificador_sesion: str, peticion: Request) -> Response:
        """El hilo completo, en orden. `404` si no es de este titular.

        La lectura queda auditada (`EQ-023`) dentro de la misma transacción; ver
        la cabecera. `actor` sale de la sesión y nunca del cuerpo o la URL.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if adaptador_historial is None:
            return _sin_almacen()

        sujeto = sujeto_de(datos)
        try:
            mensajes = adaptador_historial.hilo_de(
                identificador_sesion, sujeto, actor=sujeto, operacion=OPERACION_CONSULTA
            )
        except ErrorDeAlmacen:
            return mantenimiento("no se pudo leer la conversación en este momento")

        if not mensajes:
            # `404` y no `403`: no se distingue «no existe» de «no es suya», y
            # esa indistinción es lo que impide confirmar la existencia de
            # conversaciones de terceros. Aquí ya significa una sola cosa: la
            # consulta se hizo bien y no había nada.
            return JSONResponse({"detalle": "no se encontró esa conversación"}, status_code=404)
        return JSONResponse(hilo_como_contrato(identificador_sesion, mensajes, catalogo))

    @router.delete("/api/historial/{identificador_sesion}")
    def borrar_hilo(identificador_sesion: str) -> Response:
        """Retirada en el hito R2. Ver la cabecera del módulo.

        Borraba las filas de un hilo por el mismo camino que la cascada
        —`_borrar_del_sujeto`, con el sujeto en el `WHERE`—, así que no podía
        alcanzar lo de otra persona. El problema no era ése: era que borraba, y
        el historial del piloto es obligatorio (`EQ-016` punto 6) y toda
        eliminación pasa por el trámite de `EQ-022`.
        """
        return JSONResponse(
            {
                "detalle": (
                    "esta ruta fue retirada: durante el piloto el historial es "
                    "obligatorio (EQ-016) y ninguna conversación se borra por "
                    "separado. Toda eliminación pasa por el trámite reversible"
                ),
                "estado": "retirada",
                "usar": "/api/datos/supresion",
            },
            status_code=410,
        )

    return router
