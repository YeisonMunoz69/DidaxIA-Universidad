"""
aviso_legal.py — El ciclo de vida de los datos y la edad (`PM-B19`, `DD-26`)
====================================================================================

`datos_personales.py` ya cubre `RP-19` —consultar, exportar, suprimir—. Lo que
faltaba, y es de este archivo, son dos cosas que **no son sobre datos ya
recogidos** sino sobre las condiciones bajo las que se recogen:

- **`DD-15`**, el ciclo de vida: qué pasa con cada cosa al sustentar. Hasta
  hoy solo vivía en `04-Decisiones-de-Detalle.md`; `frontend/src/estudiante/
  rutas/Consentimiento.svelte` (`PM-F05`) cubre el consentimiento del
  tratamiento conductual (`RP-19`) pero no dice qué pasa con los datos al
  terminar el proyecto. `bloque_legal()` es esa mitad, servida como dato del
  servidor y no solo como documento — la misma razón por la que
  `08-Contrato-del-Turno.md` existe en vez de bastar con la ERS.
- **`RL-09`**, la edad: *«el sistema deberá verificar la mayoría de edad… ante
  un usuario menor de edad, el módulo conductual permanece deshabilitado»*.

`DD-26` cambió el mecanismo de `RL-09`, y por qué
--------------------------------------------------------
Hasta el 2026-08-12 esto era `mayoria_de_edad: bool` con piso `False`: sin
confirmación activa, nada de módulo conductual. La cuarta sesión de ese día
enganchó el filtro 3 a la cadena real y ese piso pasó de teórico a caro —
`D-17` lo cuenta entero—: el único salón que la universidad presta este
semestre puede tener estudiantes de primer o segundo semestre, y exigir
confirmación activa habría dejado sin módulo conductual a un salón entero de
personas que **no son menores**, simplemente por no tocar un campo que nadie
les pidió tocar.

`DD-26` invierte la fricción: **`edad` con valor por defecto 18**. Quien es
menor y lo sabe tiene un campo para decirlo; no tiene que decirlo nadie más.

Dos predicados y no uno, porque `DD-26` §3 separa dos situaciones
------------------------------------------------------------------------
`puede_participar()` y `modulo_conductual_habilitado()` **no son la misma
pregunta**, y fundirlas borraría justo la distinción que `DD-26` §3 fija:

- **Quien declara ser menor queda fuera del experimento ENTERO** —no en un
  modo degradado—. `RL-03` exige consentimiento diferenciado y expreso, y el
  régimen reforzado que permitiría dárselo a un menor (`RL-10`) no está
  construido: no puede decir que sí de forma válida todavía. Es
  `puede_participar()`, y es **más estricto** que la regla anterior.
- **Quien no ha declarado edad y el modo piloto no está activo** sí puede
  seguir usando el tutor —`RL-04`: negar el tratamiento conductual no debe
  impedir la funcionalidad educativa básica— pero sin inferencia conductual.
  Es `modulo_conductual_habilitado()`, el piso `False` original de `RL-09`.

`MODO_PILOTO` · por qué el valor por defecto vive detrás de un interruptor
--------------------------------------------------------------------------------
`DD-26` §4: asumir 18 es una **conveniencia de piloto, no una posición
permanente**, y el riesgo real es que sobreviva por inercia cuando deje de
estar justificada. `AGENTE_PILOTO_TESIS` es ese interruptor.

**Sin la variable puesta, el sistema cae al `RL-09` original** y no a un
equivalente disfrazado: `edad_por_defecto()` devuelve `None` —«no declarada»—
y `modulo_conductual_habilitado()` da `False`, que es exactamente la
confirmación activa que `RL-09` describe tal cual. Se hizo así a propósito:
un interruptor que al apagarse no cambia nada es decoración, y `DD-26` §4
pide que retirar esto sea *«una línea de configuración, no una arqueología de
código»*. Apagarlo tiene consecuencia real y comprobable.

Qué NO hace esta pieza, y por qué se queda corta a propósito
--------------------------------------------------------------------
**No aplica el régimen reforzado de `RL-10`.** Si el piloto llegara a incluir
menores de edad, `RL-10` exige autorización del representante legal y
validación institucional previa — un protocolo que se aprueba con personas,
no que se programa. Mientras no exista esa aprobación, la única salida que
este módulo ofrece a quien declara ser menor es **quedarse fuera**, nunca una
vía alterna simulada.

**No verifica identidad ni edad de verdad.** `DD-26` es explícito en que esto
es un valor por defecto declarado, y así se escribe en la tesis: una
limitación conocida y deliberada del piloto, no `RL-09` resuelto de fondo.
`PM-X03` (aprobación ética institucional) sigue siendo quien debe revisarlo
formalmente antes de cualquier despliegue que no sea el de este semestre.
"""

from __future__ import annotations

import os

from dominio.modelo.acceso import (
    AccesoCalculado,
    permite_escritura_longitudinal,
)

#: `RL-09`. No es configurable: es la mayoría de edad legal, no un umbral que
#: el proyecto pueda calibrar como los de `ADR-003`.
MAYORIA_DE_EDAD = 18

#: `DD-15` §Qué pasa con cada cosa, literal — no resumido ni reinterpretado.
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

#: `C-02` del acta del 2026-08-18 · `D-29` · **BORRADOR, sin firmar**
#: ============================================================================
#: `D-29` decide que los **agregados ya calculados no se deshacen** al ejercer
#: la supresión. Eso solo es defendible si el titular lo sabe **antes** de
#: participar, no después de la primera solicitud — y por eso el texto está
#: aquí y no en un documento aparte.
#:
#: ⚠️ **Transcrito literal del acta y NO reescrito.** Resumirlo o mejorarlo
#: aquí crearía una segunda redacción del mismo compromiso, que es la regla
#: madre de `COMO-TRABAJAMOS.md` §1 incumplida sobre un texto legal.
#:
#: ⚠️ **`revisado` es `False` y esto no se publica en silencio.** Falta la
#: firma de la dirección del proyecto y del comité (`PM-X03`). El cliente
#: recibe la marca para poder mostrarlo como borrador o no mostrarlo: lo que
#: no puede es enseñarlo como si estuviera aprobado. No es asesoría legal.
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
    # La contrapartida que hace honesta a la cláusula. Va junta con ella a
    # propósito: la primera sola es una excepción a favor del proyecto.
    "contrapartida": (
        "Le contaremos cuántas personas pidieron el borrado y en qué momento "
        "del estudio, porque eso forma parte de leer bien los resultados."
    ),
}

#: `D-29` · el plazo de conservación, para que la pantalla pueda decirlo.
#: `AGENTE_RETENCION_HASTA` (ISO) queda vacía mientras no haya fecha de
#: sustentación. ⚠️ **Vacía no es «sin límite»**: manda el techo de 24 meses
#: desde la recolección. Leerla como «para siempre» sería el modo mock
#: silencioso de `CONTEXTO-MAESTRO.md` §5.1 aplicado a un plazo legal.
TECHO_DE_RETENCION_MESES = 24


def retencion_declarada() -> dict:
    """Qué plazo de conservación rige hoy, dicho sin redondear.

    No calcula la fecha de purga —eso es de quien purgue, contra `momento`—:
    dice qué regla manda y si la primera mitad ya tiene fecha.
    """
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


#: El mensaje que ve quien declara ser menor. Explícito y con el motivo, que
#: es lo que `DD-26` §3 pide: no un 401 genérico que parezca una avería.
MOTIVO_DE_BLOQUEO = (
    "Para participar en este piloto hay que ser mayor de edad. El sistema no "
    "tiene todavía el régimen reforzado que la ley exige para tratar datos de "
    "menores (RL-10), así que no puede ofrecerte una versión reducida: no "
    "puedes participar. Si te equivocaste al escribir tu edad, abre una sesión "
    "nueva."
)


def modo_piloto() -> bool:
    """`DD-26` §4. Se lee en cada llamada y no al importar el módulo, para que
    una prueba pueda ejercitar los dos caminos sin recargar nada."""
    return bool(os.environ.get("AGENTE_PILOTO_TESIS", "").strip())


def edad_por_defecto() -> int | None:
    """La edad con la que se abre una sesión que no ha declarado nada.

    `MAYORIA_DE_EDAD` en modo piloto (`DD-26`); `None` —«no declarada»— sin
    él, que es el piso original de `RL-09`. Ver la cabecera del módulo sobre
    por qué el interruptor tiene consecuencia real y no es decoración.
    """
    return MAYORIA_DE_EDAD if modo_piloto() else None


def edad_declarada(datos_de_sesion: dict) -> int | None:
    """La edad de esta sesión, o `None` si no hay ninguna utilizable.

    Un valor que no sea un entero —una cadena, un booleano, `None`— se trata
    como no declarado y **no** como cero: son cosas distintas, la misma
    distinción que `dominio/arbitraje/divulgacion.py` hace con sus señales.
    `True` es `int` en Python, así que se descarta explícitamente.
    """
    edad = datos_de_sesion.get("edad")
    if isinstance(edad, bool) or not isinstance(edad, int):
        return None
    return edad


def puede_participar(datos_de_sesion: dict) -> bool:
    """`DD-26` §3 · `False` solo cuando la sesión DECLARÓ ser menor y no ha otorgado consentimiento.

    Con autorización del acudiente/tutor declarada en el consentimiento informado,
    el estudiante puede interactuar normalmente con el tutor.
    """
    if datos_de_sesion.get("consentimiento") == "otorgado":
        return True
    edad = edad_declarada(datos_de_sesion)
    return edad is None or edad >= MAYORIA_DE_EDAD


def modulo_conductual_habilitado(datos_de_sesion: dict) -> bool:
    """`RL-09`, verificado por el servidor y no confiado al cliente.

    Exige una edad declarada **y** que alcance la mayoría de edad. En modo
    piloto la trae por defecto (`DD-26`), así que da `True` para cualquiera
    que no se haya declarado menor y no hace falta ningún gate por turno
    nuevo; sin modo piloto da `False` mientras nadie declare su edad, que es
    el piso conservador de `RL-09` tal como está escrito.
    """
    edad = edad_declarada(datos_de_sesion)
    return edad is not None and edad >= MAYORIA_DE_EDAD


def permite_escritura_conductual(
    datos_de_sesion: dict, acceso: AccesoCalculado | None
) -> bool:
    """Si esta sesión puede dejar rastro en el **perfil longitudinal**.

    Política F.11 de la fase 4: *«usa explícitamente
    `permite_escritura_longitudinal()` o un contrato equivalente ya aprobado en
    el borde de escritura. No dependas únicamente de que otra guarda haya
    impedido llegar allí»*.

    Hasta aquí la propiedad se sostenía **de rebote**: `claves_del_titular()`
    devolvía el sujeto conductual vacío cuando `RL-09` no habilitaba el módulo,
    y `AdaptadorTurno` no escribía sin sujeto. Era cierto, y era frágil: la
    protección vivía en el valor de una variable, no en una comprobación, así
    que cualquier futuro que rellenara ese sujeto por otra vía abría la
    escritura sin que ninguna prueba lo notara.

    **Son dos puertas y hacen falta las dos**, porque protegen cosas distintas:

    | Puerta | De dónde | Qué gobierna |
    |---|---|---|
    | `dominio/modelo/acceso.py::permite_escritura_longitudinal` | `EQ-016` | el consentimiento: qué perfil se actualiza |
    | `modulo_conductual_habilitado()` | `RL-09` · `DD-26` | la edad: si se puede inferir conducta |

    La primera ya existía y es la aprobada; ésta no la sustituye, la compone con
    la segunda en el punto donde ocurre la escritura. Se llama
    `permite_escritura_conductual` para no tener dos funciones con el mismo
    nombre diciendo cosas distintas — que es exactamente lo que se estaba a
    punto de hacer.
    """
    if acceso is None:
        # No se pudo calcular el acceso. `EQ-024` prohíbe afirmar lo que no se
        # sabe, y «no sé si puedo escribir» se resuelve no escribiendo.
        return False
    return permite_escritura_longitudinal(acceso) and modulo_conductual_habilitado(
        datos_de_sesion
    )


def bloque_legal() -> dict:
    """`DD-15` y `RL-09`, como datos que el servidor entrega.

    No exige sesión: es el mismo aviso para cualquiera, antes incluso de que
    exista una sesión que consultar — es lo que hay que saber para decidir si
    empezar, no algo que dependa de haber empezado ya.
    """
    return {
        "ciclo_de_vida": list(CICLO_DE_VIDA),
        # `D-29` / `C-02`, 2026-08-18. Van juntas: el plazo sin la cláusula no
        # explica qué sobrevive a una supresión, y la cláusula sin el plazo no
        # dice hasta cuándo. Las dos salen marcadas con lo que les falta.
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
            # `DD-26`: el cliente necesita saber si el campo viene relleno por
            # defecto o si tiene que pedirlo, para no prometer en pantalla algo
            # distinto de lo que el servidor hará.
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
