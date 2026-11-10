"""
sesiones.py — El almacén de sesiones del borde HTTP (`RP-02`, `EQ-020`, `DD-26`)
=================================================================================

Vivía dentro de `aplicacion.py` como `_Sesiones` privada, porque cuando se
escribió era el único estado que ese archivo sostenía. Desde `PM-B24` tiene
tres hermanos —`clases.py`, `supervision.py`, `docentes.py`—, todos almacenes
en memoria del proceso con la misma disciplina, y `PM-B27` la trajo aquí para
que esté donde ellos: **un almacén por archivo**, y `aplicacion.py` solo los
compone.

⚠️ Tres identificadores, y confundirlos costó una revisión · hito R1
------------------------------------------------------------------------------
Hasta el cierre V-B había **uno solo** haciendo tres trabajos incompatibles: el
valor de la cookie `HttpOnly` se devolvía en el JSON como `sesion`, se usaba
como identificador de conversación y se reemplazaba al empezar una charla nueva.
Las tres consecuencias, tal como las encontró la auditoría:

1. **El secreto cruzaba al JavaScript.** Una cookie `HttpOnly` existe para que
   ningún guion de la página pueda leerla; devolver su valor en el cuerpo de la
   respuesta anula esa protección por completo. Da igual lo bien puesto que esté
   el atributo si el mismo valor viaja en el JSON de al lado.
2. **«Nueva conversación» renovaba los siete días.** Cerraba la sesión y abría
   otra, así que `creada_en` volvía a cero: quien empezara una charla cada seis
   días conservaba la sesión indefinidamente y el plazo de `EQ-020` no existía.
3. **Retomar un hilo tocaba la autenticación.** Dos cosas que no tienen por qué
   moverse juntas.

Ahora son tres, con tres vidas distintas:

- **`token`** · el secreto. Vive **sólo** en la cookie y en la clave de este
  almacén. No entra en `publico()`, no sale en ningún cuerpo y no se registra.
  Lo invalida `cerrar()`, y nada más.
- **`sesion_autenticada`** · un identificador **no secreto** de la sesión, para
  lo que necesita nombrarla sin poder suplantarla: el tope de peticiones y
  cualquier traza. Que exista es lo que permite que el token no salga de aquí.
- **`conversacion`** · el hilo en curso. Es lo que el historial y los turnos
  usan, lo que `nueva_conversacion()` cambia y lo único que `publico()` publica
  como `sesion`.

El campo público sigue llamándose `sesion` **por compatibilidad temporal** con
el frontend anterior a C1, y desde el hito R1 significa **la conversación**.
`publico()` lo acompaña de `conversacion` con el mismo valor para que C1 pueda
migrar al nombre correcto sin que el contrato se rompa a mitad.

Qué guarda una sesión, y por qué cada cosa
-------------------------------------------------
- `identificador_estable`, `correo`, `nombre` — `PM-B15`/`DD-18`. Los pone
  `/api/sesion/google` cuando verificó identidad; son los tres campos que
  `DD-18` autoriza guardar, ni uno más.
- `rol` — lo decide **el servidor** (`RP-17`), nunca el cuerpo de la petición.
- `consentimiento` — `RP-19`. Estado inicial `pendiente`. ⚠️ Desde el hito B2 el
  acceso real lo calcula `dominio/modelo/acceso.py` contra el estado persistido:
  este campo es informativo para el cliente y **no autoriza nada**.
- `intentos`, `insistencias`, `peticion_confirmada` — lo que el filtro 6
  necesita y el turno no puede deducir de su propio texto. Son de la
  CONVERSACIÓN, así que `nueva_conversacion()` los reinicia.
- `reautenticada_en` — hito R3. Cuándo acreditó el servidor una reautenticación
  con Google. **El momento, nunca el token**: el secreto no se guarda y su
  antigüedad es el único dato que `EQ-022` necesita.
- `edad` — `RL-09`/`DD-26`. Ver `aviso_legal.py`.

No persiste, y es correcto para lo que sostiene
------------------------------------------------------
Las sesiones viven en memoria del proceso: un reinicio las pierde. `RP-02` pide
conservar el identificador **durante la sesión**, no entre despliegues. Lo que sí
tiene que sobrevivir —la identidad y el perfil— vive en `persona` (migración 11)
desde el hito B1, y esto sólo guarda el vínculo con la petición.

⚠️ Sólo existen sesiones autenticadas
------------------------------------------------------
`EQ-020` es explícito en que *«sólo existen usuarios autenticados con cuenta
institucional»* y en que *«el backend no crea una sesión al consultar una ruta
pública»*. `abrir()` exige sujeto estable y correo, y levanta si faltan: no es
una validación defensiva sino la forma de que no exista un camino —ni por
descuido ni por una ruta futura— que produzca una sesión sin identidad. La única
puerta es `POST /api/sesion/google`.


"""

from __future__ import annotations

import secrets
import time
from datetime import UTC, datetime

from adaptadores.entrantes.http import aviso_legal
from dominio.modelo.supresion import reautenticacion_reciente

#: La cookie donde vive el **token** de autenticación. `HttpOnly` para que ningún
#: guion de la página pueda leerla — y desde el hito R1 su valor tampoco viaja en
#: ningún cuerpo, que era la otra mitad de la misma protección.
COOKIE = "agente_sesion"

#: Cuánto dura una sesión antes de que `leer()` la trate como si no
#: existiera. Una semana (`EQ-020`): ni tan corta que interrumpa a media
#: conversación a quien vuelve al día siguiente, ni tan larga que el conteo de
#: sesiones abiertas —`_por_token`, en memoria del proceso, nunca se poda—
#: crezca sin límite entre reinicios.
#:
#: Se mide desde que se **autenticó**, no desde el último uso ni desde la última
#: conversación. Es justamente lo que el hito R1 restauró: contarlo desde la
#: conversación convertía los siete días en «siete días sin abrir una charla
#: nueva», que no es un plazo.
TTL_SESION_SEGUNDOS = 7 * 24 * 60 * 60

#: Con qué valor arranca el contador de turnos desde el último ítem. Alto a
#: propósito: quien acaba de llegar no ha visto ninguno, así que el tope de
#: frecuencia no le debe estorbar. El tope en sí lo fija
#: `dominio/pedagogia/sondeo.py` — aquí solo hace falta un valor que no lo
#: active, y por eso es un número y no un `import` del dominio: el almacén de
#: sesiones no tiene por qué conocer la regla pedagógica.
_SONDEO_NUNCA_OFRECIDO = 99


class SesionSinIdentidad(RuntimeError):
    """Se intentó abrir una sesión sin identidad verificada (`EQ-020`).

    Es un error de programación, no una respuesta HTTP: significa que alguien
    encontró —o creó— un camino hacia una sesión sin cuenta institucional, y el
    hito B1 existe para que ese camino no exista. Quien lo reciba está llamando a
    `abrir()` desde donde no debe.
    """


def _estado_de_conversacion() -> dict:
    """Lo que se reinicia al empezar una charla nueva, en un solo sitio.

    Vive aparte de `abrir()` porque `nueva_conversacion()` necesita exactamente
    lo mismo: tenerlo escrito dos veces es cómo un campo nuevo acaba
    sobreviviendo a un reinicio que debía limpiarlo, y el contexto de la
    conversación anterior reaparece por debajo de una pantalla en blanco.
    """
    return {
        "conversacion": secrets.token_urlsafe(16),
        # Lo que el filtro 6 necesita y el turno no puede deducir de su propio
        # texto. Es de la CONVERSACIÓN, no de la autenticación.
        "intentos": 0,
        "insistencias": 0,
        "peticion_confirmada": False,
        # `PM-B28` · lo que la conversación recuerda de los ítems de dos niveles
        # ya planteados, para el tope de frecuencia de
        # `dominio/pedagogia/sondeo.py`. Empieza en el tope y no en cero:
        # **nunca haber ofrecido no puede parecer «acabo de ofrecer»**, o el
        # primer ítem no llegaría nunca.
        "turnos_desde_el_sondeo": _SONDEO_NUNCA_OFRECIDO,
        "nodos_sondeados": [],
        # `PM-B31` · la última expresión escrita en la conversación. Sin ella el
        # respaldo determinista de `D-21` no puede entrar en un turno como «sigo
        # sin verlo», que es justo donde hace falta.
        "expresion_previa": "",
        # Memoria conversacional (los últimos turnos del hilo).
        "historial_reciente": [],
        "contexto_factual": {"total": 0, "turnos": []},
        "sesion_contexto_factual": "",
        # `PM-B37` · qué conversación pasada se está retomando, si alguna.
        "retomando_activo": "",
    }


class Sesiones:
    """Sesiones en memoria. Ver la nota del módulo sobre por qué basta hoy."""

    def __init__(self) -> None:
        #: token secreto → datos. La clave **no** sale de aquí.
        self._por_token: dict[str, dict] = {}

    def abrir(
        self, rol: str = "estudiante", *,
        identificador_estable: str, correo: str, nombre: str = "",
    ) -> dict:
        """Abre una sesión autenticada para una identidad **ya verificada**.

        `identificador_estable` y `correo` son obligatorios y sin valor por
        defecto: el retiro del anonimato de `EQ-020` tiene que ser imposible de
        deshacer por descuido, y un parámetro con defecto vacío es justo el
        descuido que lo desharía.
        """
        if not (identificador_estable or "").strip() or not (correo or "").strip():
            raise SesionSinIdentidad(
                "una sesión exige sujeto estable y correo verificados por Google (EQ-020)"
            )
        token = secrets.token_urlsafe(32)
        datos = {
            # El secreto. Nunca sale en `publico()` ni en ningún cuerpo.
            "token": token,
            # El nombre no secreto de esta sesión: sirve para el tope de
            # peticiones y para cualquier traza, sin poder suplantarla.
            "sesion_autenticada": secrets.token_urlsafe(12),
            "rol": rol,
            # `PM-B15`. `identificador_estable` es el que sobrevive a cerrar el
            # navegador; el de sesión no.
            "identificador_estable": identificador_estable,
            "correo": correo,
            "nombre": nombre,
            # `RP-19`. Informativo: el acceso real lo calcula
            # `dominio/modelo/acceso.py` contra el estado persistido (hito B2).
            "consentimiento": "pendiente",
            # `RL-09` · `DD-26`. Ya no es un booleano con piso `False`: es la
            # edad, con el valor por defecto que decide `aviso_legal.py` según
            # el modo piloto — 18 con él, `None` («no declarada») sin él. El
            # valor por defecto vive allí y no aquí a propósito: es la decisión
            # legal, no un detalle del almacén de sesiones.
            "edad": aviso_legal.edad_por_defecto(),
            # `EQ-022`, hito R3 · cuándo acreditó el servidor una reautenticación
            # con Google. `None` hasta que ocurra; el token nunca se guarda.
            "reautenticada_en": None,
            # No es del contrato -`publico()` no la incluye-, es de este
            # almacén: cuándo expira, ver `TTL_SESION_SEGUNDOS` y `leer()`.
            # **No se mueve al empezar otra conversación** (hito R1).
            "creada_en": time.time(),
            **_estado_de_conversacion(),
        }
        self._por_token[token] = datos
        return datos

    def nueva_conversacion(self, datos: dict) -> dict:
        """Empieza otra charla **sin tocar la autenticación** (hito R1).

        Cambia el identificador de conversación y reinicia memoria, contadores y
        contexto. Conserva el token, `creada_en`, la identidad y el rol: quien
        abre una conversación nueva no se ha vuelto a autenticar, así que los
        siete días de `EQ-020` siguen contando desde donde contaban.

        Antes del cierre V-B esto cerraba la sesión y abría otra, que es como el
        plazo dejó de existir para quien conversaba a menudo.
        """
        # El estado operativo pertenece al hilo, nunca a la autenticación.
        for campo in (
            "ejercicio_activo", "ejercicio_en_pausa", "funciones_declaradas",
            "funcion_vigente", "estado_pedagogico", "estrategia_previa",
            "estado_operativo", "sondeos_ofrecidos", "sondeos_contestados",
            "item_pendiente", "sin_adaptacion",
        ):
            datos.pop(campo, None)
        datos.update(_estado_de_conversacion())
        return datos

    def publico(self, datos: dict) -> dict:
        """Lo que se le devuelve al cliente.

        ⚠️ **El token NO está aquí, y es el punto entero del hito R1.** `sesion`
        es el identificador de **conversación**; se conserva ese nombre por
        compatibilidad temporal con el frontend anterior a C1 y va acompañado de
        `conversacion`, con el mismo valor, para que C1 migre al nombre correcto
        sin romper el contrato a mitad.

        Los contadores del arbitraje **no cruzan**. No están en §9 del contrato
        porque no son del modelo del estudiante, pero enseñarle cuántos intentos
        le quedan para que el sistema le resuelva el ejercicio convertiría la
        escala en un marcador — y `RF-GEN-04` existe precisamente para que
        insistir no sea una estrategia.

        `correo`/`nombre` sí cruzan cuando existen: los trajo el propio cliente
        en el `id_token` que mandó, así que devolvérselos no es una fuga — es lo
        mínimo para que sepa con qué cuenta quedó identificado.

        `edad` cruza y `puede_participar` también (`DD-26`): el cliente necesita
        el valor que el servidor asumió para poder mostrarlo relleno y dejar
        corregirlo, y necesita saber si quedó bloqueado sin tener que deducirlo
        de un error en el siguiente turno.
        """
        publico = {
            k: datos[k] for k in ("rol", "consentimiento", "edad", "correo", "nombre")
        }
        publico["sesion"] = datos["conversacion"]
        publico["conversacion"] = datos["conversacion"]
        publico["puede_participar"] = aviso_legal.puede_participar(datos)
        # `EQ-020` · «la sesión autenticada dura siete días y avisa antes de
        # expirar». El aviso lo muestra C1, pero el plazo lo sabe el servidor: si
        # el cliente lo calculara desde su propio reloj, un reloj adelantado
        # avisaría tarde y uno atrasado no avisaría nunca.
        #
        # Se publican los segundos que faltan y no el instante de expiración
        # porque un plazo relativo no depende de la hora del navegador.
        publico["expira_en_segundos"] = self.expira_en(datos)
        return publico

    def expira_en(self, datos: dict) -> int:
        """Segundos que le quedan a esta **autenticación**. Nunca negativo.

        Cero significa vencida: `leer()` ya la habrá retirado la próxima vez que
        alguien la use, así que este valor y aquella decisión no pueden discrepar
        —los dos salen de `creada_en` y `TTL_SESION_SEGUNDOS`—.
        """
        restante = TTL_SESION_SEGUNDOS - (time.time() - datos["creada_en"])
        return max(0, int(restante))

    def leer(self, token: str | None) -> dict | None:
        """La sesión de ese token, o `None`. La autorización sale sólo de aquí.

        `token` es siempre el valor de la cookie: ninguna ruta resuelve una
        sesión por un identificador que el cliente pueda nombrar en el cuerpo, la
        URL o una cabecera propia.
        """
        datos = self._por_token.get(token or "")
        if datos is None:
            return None
        if time.time() - datos["creada_en"] > TTL_SESION_SEGUNDOS:
            # Vencida: se retira igual que `cerrar()` y se devuelve `None`,
            # exactamente lo que ya pasa cuando el proceso se reinició y la
            # cookie no está en `_por_token`. Cada ruta que llama a `leer()` ya
            # sabe tratar ese `None` -responde 401 si exige sesión-, así que una
            # sesión vencida no necesita un camino aparte.
            self._por_token.pop(token, None)
            return None
        return datos

    def cerrar(self, token: str | None) -> None:
        """Invalida la autenticación. Es lo único que lo hace (`EQ-024`)."""
        self._por_token.pop(token or "", None)

    # ── reautenticación acreditada por el servidor · hito R3 ─────────────────

    def marcar_reautenticacion(self, datos: dict, *, momento: datetime | None = None) -> datetime:
        """Deja constancia de que el servidor acreditó una reautenticación.

        El `momento` por defecto es el **reloj del servidor**, y el parámetro
        existe sólo para que las pruebas puedan envejecer una prueba sin tocar el
        reloj del proceso. Ninguna ruta lo pasa: si lo hiciera, la fecha volvería
        a poder venir de fuera, que es el defecto que este hito corrige.

        No recibe ni guarda el `id_token`: `EQ-022` necesita saber **cuándo**, y
        el secreto con el que se demostró no es un dato que custodiar.
        """
        acreditada = momento or datetime.now(UTC)
        datos["reautenticada_en"] = acreditada
        return acreditada

    def prueba_de_reautenticacion(self, datos: dict) -> datetime | None:
        """Cuándo se acreditó la última reautenticación, o `None`.

        Devuelve el momento **aunque ya haya caducado**: si algo caducó lo decide
        `reautenticacion_vigente()`, y quien quiera explicarle a alguien que su
        prueba venció necesita saber que existió.
        """
        return datos.get("reautenticada_en")

    def reautenticacion_vigente(self, datos: dict) -> bool:
        """Si esa prueba todavía sirve para una operación de `EQ-022`.

        La ventana la fija el dominio (`SEGUNDOS_DE_REAUTENTICACION_RECIENTE`) y
        se comprueba con la misma función que usa el repositorio, para que el
        borde y la base no puedan discrepar sobre qué es «reciente».
        """
        acreditada = self.prueba_de_reautenticacion(datos)
        if acreditada is None:
            return False
        return reautenticacion_reciente(acreditada, datetime.now(UTC))


def sujeto_de(datos: dict) -> str:
    """La clave del perfil versionado (`PM-B11`) de esta sesión.

    Siempre `identificador_estable`: desde el hito B1 **no existe sesión sin
    identidad verificada**, y desde R1 tampoco existe un identificador de sesión
    que pudiera hacer de sujeto.

    ⚠️ Aquí había un respaldo —`or datos["sesion"]`— que devolvía el
    identificador de sesión para un anónimo. Era el último rastro del anonimato y
    se retira: con él, un descuido que dejara la identidad vacía habría producido
    un sujeto distinto en cada sesión, un perfil longitudinal que no se acumula y
    una cascada de supresión que no alcanza nada. Sin él, ese descuido levanta.
    """
    sujeto = (datos.get("identificador_estable") or "").strip()
    if not sujeto:
        raise SesionSinIdentidad(
            "esta sesión no tiene identidad verificada: no hay sujeto del que colgar datos"
        )
    return sujeto
