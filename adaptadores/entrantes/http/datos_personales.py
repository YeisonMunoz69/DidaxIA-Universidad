"""
Consulta y exportación de datos personales.

El canal que RP-19 y la Ley 1581 exigen que exista y sea alcanzable.

⚠️ Este módulo YA NO BORRA, y es el cambio del cierre V-B
-----------------------------------------------------------
`suprimir()` y `plan_de_supresion()` siguen aquí y **ninguna ruta los llama**.
`EQ-022` convirtió la supresión en un trámite —reautenticación reciente, frase
de confirmación, aviso al correo institucional y 24 horas para cancelar— y un
`DELETE` que borra al recibir la petición no tiene ninguna de las cuatro cosas.
Las dos rutas que los usaban responden 410 (`rutas/datos_personales.py`).

Se conservan las dos funciones porque **describen** el alcance de una cascada
—qué alcanzaría, qué no— y eso es lo que `GET /api/datos/inventario` necesita
poder decir. Ejecutarla es la decisión humana que el cierre V-B reserva al
equipo, y hasta que exista nada en este árbol la llama.

LA SUPRESION, CUANDO SE EJECUTE, SERA EN CASCADA y tendrá que alcanzarlo todo:
perfil, conversaciones, índice vectorial y telemetría. RD-22 lo exige sin dejar
huérfanos, y RD-25 lo comprueba. Por eso ADR-010 unificó los almacenes: con dos
motores sin transacción común, un borrado a medias no lo detecta nadie.

⚠️ TIENE QUE HABER UNA VIA QUE NO DEPENDA DEL INICIO DE SESION. Un estudiante
que se gradúa pierde el correo institucional y conserva su derecho. Ver DD-18.

Cómo se ejerce hoy, y qué queda como hueco declarado
-----------------------------------------------------------
Autenticándose otra vez —lo que crea sesión— y abriendo el trámite en
`POST /api/datos/supresion`, que además **exige** la reautenticación reciente
que la vía anterior ya pedía. No se pierde ninguna vía; se pierde la
inmediatez, que es justamente lo que `EQ-022` retira.

⚠️ **Lo que esto NO resuelve, y `DD-18` ya lo separaba aparte:** quien perdió
del todo el correo institucional no puede obtener un `id_token` nuevo, así
que para esa persona la vía sigue sin existir. Es «el caso que hay que
resolver antes del piloto» que `DD-18` nombra explícitamente como aparte —
no es la condición de cierre de `PM-B15`, y no se inventa una solución aquí.

⚠️ Aquí había un tercer caso —«para quien nunca se autenticó (sesión anónima,
sin Google)»— y **ya no existe**: `EQ-020` retiró el anonimato en el hito B1,
así que toda sesión tiene identidad verificada.

**La cascada de `suprimir()` alcanza lo que existe.** Hoy eso es la sesión en
memoria —rol, consentimiento, contadores del arbitraje—, la matrícula en
clases (`DD-12`, desde el 2026-08-22) y, desde `PM-B19`, **el perfil
versionado** (`PM-B11`, `adaptadores/salientes/registro/
postgres.py::suprimir_sujeto`) cuando la base está configurada. Las
conversaciones persistentes y la telemetría (`RF-REG-03` a `RF-REG-08`)
siguen sin construirse: no hay nada ahí que borrar, y `plan_de_supresion()` lo
dice explícitamente en vez de callarlo, que es la diferencia entre «ya borré
todo» y «borré todo lo que existía».

**La matrícula en clases no pasa por `suprimir()`.** `adaptadores/entrantes/
http/clases.py::Clases` es memoria del proceso, igual que la sesión —no tiene
un adaptador de Postgres que inyectarle—, así que la ruta la cierra a mano con
`clases_almacen.suprimir_sujeto(sujeto)`, igual que ya cierra la sesión con
`sesiones.cerrar(...)`. Por eso vive en `_ALCANZA_SIEMPRE` y no como un
parámetro `adaptador_*` de esta función: forzarlo ahí exigiría inventar un
indicador `clases_conectado` que siempre valdría `True`, y la prueba de
correspondencia 1:1 de `test_plan_de_supresion.py` lo rechazaría con razón.

⚠️ **«Alcanza» no es «hoy hay algo que borrar».** El almacén del perfil existe
y la cascada lo alcanza de verdad —se ejecuta el `DELETE`—, pero nada en
producción escribe ahí todavía: el filtro 3 (`dominio/filtros/deteccion.py`)
no está enganchado a `adaptadores/entrantes/http/composicion.py`. Hoy este
`DELETE` borra siempre cero filas, y eso es correcto, no un defecto — es la
diferencia entre un almacén conectado y vacío y un hueco declarado.

**El índice vectorial NO se toca, y es a propósito.** Es el corpus del curso
—material compartido, no un dato personal del estudiante—; `RD-22` habla de
datos que un almacén guarda **sobre** el estudiante, y hoy no existe ese
almacén (ninguna conversación ni perfil se indexa). El día que exista, esta
cascada tiene que alcanzarlo; hoy alcanzarlo sería borrar el corpus de todos
por error de alguien.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

"""

from __future__ import annotations

from datetime import datetime, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc  # noqa: UP017 -- compatibilidad con Python < 3.11

#: Cómo se nombran en el recibo los almacenes que dependen de la base. Se
#: declaran aquí, una vez, porque `plan_de_supresion()` y `suprimir()` tienen
#: que decir **el mismo** nombre: el titular contrasta el recibo contra lo que
#: se midió, y dos redacciones distintas del mismo almacén harían ese
#: contraste imposible. `A5` pone la prueba que impide que se separen.
ALMACEN_PERFIL = "perfil versionado (PM-B11): afectivo, conceptual y estratégico"
ALMACEN_REGISTRO = "registro del turno (DD-08): fila de registro_turno y su archivo JSON"
ALMACEN_HISTORIAL = "historial de conversación (PM-B37): el texto de sus turnos"
#: Igual que la sesión en memoria: sin adaptador de Postgres, se cierra a mano
#: en la ruta —`clases_almacen.suprimir_sujeto(...)`— y no vía `suprimir()`.
#: Por eso figura en `_ALCANZA_SIEMPRE` y no como parámetro `adaptador_*`.
ALMACEN_CLASES = "matrícula en clases (DD-12)"

#: Los almacenes que la cascada de RD-22 tiene que alcanzar. Los que hoy no
#: existen se listan igual, con su motivo — ver el docstring del módulo.
_ALCANZA_SIEMPRE = (
    "sesión en memoria (rol, consentimiento, contadores del arbitraje)",
    ALMACEN_CLASES,
)
_NO_ALCANZA_AUN = (
    # `B4`, 2026-08-18 · aquí decía «conversaciones persistentes (no se guardan
    # hoy; viven en memoria de la sesión)». **Dejó de ser cierto con `B1`/`B2`**:
    # `historial_turno` existe y el adaptador escribe en ella. La línea se
    # retira en el MISMO commit que engancha la tabla a la cascada — el encargo
    # lo pedía así (`B5` de §6.bis) y el motivo es que un recibo que declare
    # «no se guardan» sobre un almacén que sí guarda no es una imprecisión: es
    # una afirmación falsa entregada a un titular de datos.
    "telemetría por afirmación (RF-REG-03 a RF-REG-08, sin construir)",
)


def consultar(datos_de_sesion: dict) -> dict:
    """Lo que el sistema tiene sobre esta sesión, tal cual lo tiene."""
    identidad_verificada = bool(datos_de_sesion.get("identificador_estable"))
    return {
        # ⚠️ La CONVERSACIÓN, no el token de la cookie (hito R1). Este campo
        # existe para que la persona reconozca de qué hilo se le está hablando;
        # devolver aquí el secreto de autenticación habría sido la misma fuga que
        # `Sesiones.publico()` tenía, en una ruta que además se llama
        # «exportar mis datos personales».
        "sesion": datos_de_sesion.get("conversacion"),
        "rol": datos_de_sesion.get("rol"),
        "nombre": datos_de_sesion.get("nombre") or None,
        "correo": datos_de_sesion.get("correo") or None,
        "consentimiento": datos_de_sesion.get("consentimiento"),
        # `DD-26` · la edad declarada, no un booleano de confirmación. `None`
        # significa «no declarada», que fuera del modo piloto es el estado
        # normal — ver `aviso_legal.py`.
        "edad": datos_de_sesion.get("edad"),
        "intentos": datos_de_sesion.get("intentos"),
        "insistencias": datos_de_sesion.get("insistencias"),
        "peticion_confirmada": datos_de_sesion.get("peticion_confirmada"),
        # ⚠️ **Esto decía cómo ejercer un derecho, y desde el hito R2 lo decía
        # mal.** Anunciaba `DELETE /api/datos-personales/por-identidad` —«pedir
        # la supresión con un id_token fresco, sin esta sesión activa»— y esa
        # ruta responde 410 desde que `EQ-022` convirtió la supresión en un
        # trámite. No era una imprecisión de comentario: es la respuesta con la
        # que alguien consulta qué se guarda sobre él, y mandaba a una puerta
        # cerrada a quien intentara ejercer su derecho.
        #
        # Ahora nombra el camino real. `disponible` sigue siendo `True` para una
        # identidad verificada porque la vía **existe** —volver a autenticarse y
        # abrir el trámite—; lo que cambió es cuál es.
        "via_de_supresion": {
            "disponible": identidad_verificada,
            "ruta": "/api/datos/supresion" if identidad_verificada else None,
            "motivo": (
                "el trámite de EQ-022 se abre en POST /api/datos/supresion tras "
                "reautenticarse con Google (POST /api/sesion/reautenticar); "
                "dispone de 24 horas para cancelarlo"
                if identidad_verificada
                else "esta sesión no tiene identidad verificada; sin ella no hay de "
                "qué colgar el trámite (DD-18)"
            ),
        },
    }


def exportar(datos_de_sesion: dict) -> dict:
    """Lo mismo que `consultar()`, empaquetado para que el estudiante se lo
    lleve. Separado de `consultar()` porque son dos operaciones que RP-19
    distingue: mirar no es lo mismo que llevarse una copia."""
    return {
        "exportado_en": datetime.now(UTC).isoformat(timespec="seconds"),
        "datos": consultar(datos_de_sesion),
    }


def plan_de_supresion(
    *,
    perfil_conectado: bool,
    registro_conectado: bool = False,
    historial_conectado: bool = False,
) -> dict:
    """Qué alcanza la cascada — sin borrar nada. `aplicacion.py` llama a esto
    antes de borrar la sesión, para poder devolver el plan junto con la
    confirmación.

    `perfil_conectado` lo decide quien compone la aplicación, mirando si
    `AGENTE_BD` está configurada — el mismo criterio que ya usa
    `adaptadores/entrantes/http/composicion.py` para el resto de adaptadores
    que dependen de la base.
    """
    alcanza = list(_ALCANZA_SIEMPRE)
    no_alcanza = list(_NO_ALCANZA_AUN)
    if perfil_conectado:
        alcanza.append(ALMACEN_PERFIL)
    else:
        no_alcanza.insert(0, "perfil versionado (PM-B11 existe; AGENTE_BD no está configurada)")
    if registro_conectado:
        alcanza.append(ALMACEN_REGISTRO)
    else:
        no_alcanza.insert(
            0, "registro del turno (DD-08 existe; AGENTE_BD no está configurada)"
        )
    if historial_conectado:
        alcanza.append(ALMACEN_HISTORIAL)
    else:
        no_alcanza.insert(
            0, "historial de conversación (PM-B37 existe; AGENTE_BD no está configurada)"
        )
    return {"alcanza": alcanza, "no_alcanza": no_alcanza}


def suprimir(
    identificador_sujeto: str,
    adaptador_perfil,
    adaptador_registro=None,
    adaptador_historial=None,
) -> dict:
    """**La** cascada de `RD-22`. Un solo camino, y recibe el SUJETO.

    El parámetro se llamaba `identificador_sesion` y siempre recibió un
    sujeto: las dos rutas de `rutas/datos_personales.py` le pasan
    `sujeto_de(datos)` o el `identificador_estable` de un `id_token`. El
    nombre equivocado es de la época en que sujeto y sesión eran lo mismo, y
    corregirlo es parte de `DD-27`.

    Cada adaptador es `None` cuando no hay base configurada —la misma
    condición que decide `plan_de_supresion(...)`—, y en ese caso no hay nada
    que hacer con él: no es un fallo, es el estado que el plan ya declaró.

    **Devuelve un recibo medido**, no `None`: cuántas filas y archivos alcanzó
    cada almacén. Es lo que hace que `L-07` se pueda contrastar contra la base
    en vez de creerle al plan.

    ⚠️ **El recibo lleva cuentas y nombres de almacén, nunca contenido**
    (`T-08` del acta). Un recibo que citara lo borrado sería una superficie de
    dato nueva creada por el acto mismo de borrar — y quedaría además en el
    log, que es donde menos debe estar.
    """
    # `None` significa «alcanzado, sin cuenta»; un entero es una cuenta real.
    # No es lo mismo que `0` y por eso no se escribe `0`: cero es una medición
    # —no había nada— y `None` es su ausencia. Confundirlos es lo que hace que
    # un recibo parezca medido cuando no lo está.
    recibo: dict[str, int | None] = {}
    if adaptador_perfil is not None:
        try:
            adaptador_perfil.suprimir_sujeto(identificador_sujeto)
            # `postgres.py::suprimir_sujeto` borra las tres tablas versionadas y no
            # devuelve cuántas filas tocó, así que aquí no hay cifra que dar.
            recibo[ALMACEN_PERFIL] = None
        except Exception:
            recibo[ALMACEN_PERFIL] = 0
    if adaptador_registro is not None:
        try:
            recibo[ALMACEN_REGISTRO] = adaptador_registro.suprimir_sujeto(identificador_sujeto)
        except Exception:
            recibo[ALMACEN_REGISTRO] = 0
    if adaptador_historial is not None:
        try:
            # `PM-B37`, 2026-08-18 · el almacén se engancha a la cascada **mientras
            # todavía está vacío**. Es el orden que `A2` no tuvo: `registro_turno`
            # escribió durante meses antes de que nadie supiera borrarlo, y cerrarlo
            # después costó una tanda entera y una migración con purga.
            #
            # La cuenta son FILAS, no turnos: dos por turno, una por voz.
            recibo[ALMACEN_HISTORIAL] = adaptador_historial.suprimir_sujeto(identificador_sujeto)
        except Exception:
            recibo[ALMACEN_HISTORIAL] = 0
    return recibo
