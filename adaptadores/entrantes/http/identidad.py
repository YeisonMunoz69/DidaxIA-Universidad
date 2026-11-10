"""
Verificación del id_token de Google · DD-18 · D-16 opción de proveedor · PM-B15 A
====================================================================================

La primera mitad de la autenticación con identidad delegada: comprobar que un
id_token vino de verdad de Google y que la cuenta es del dominio institucional,
ANTES de mirar cualquier otro campo.

**Alternativa descartada: comparar el sufijo del correo a mano**
(`correo.endswith("@unimayor.edu.co")`). `DD-18` lo prohíbe explícitamente: el
claim `hd` (*hosted domain*) es lo que Google garantiza para cuentas de
Workspace y no se puede falsificar cambiando el nombre de usuario del correo;
el sufijo del correo sí se puede, porque nada impide un alias o un reenvío.

Qué se guarda y qué no — `DD-18` §«Qué se recibe y qué se guarda»
----------------------------------------------------------------------
Identificador estable (`sub`), correo y nombre son los campos de identidad que
se persisten en `persona`. La URL firmada de `picture` se lee sólo para importar
la fotografía inicial al almacén privado; la URL no se guarda y nunca se expone
como dato público. Cualquier otro campo del perfil se descarta.

⚠️ **`iat` y `auth_time` sí se leen desde el hito R7-A, y no contradicen lo
anterior.** No son campos de perfil: son las dos marcas de tiempo con las que
Google firma *cuándo* emitió el token y *cuándo* se autenticó la persona. Viven
lo que dura la petición dentro de `IdentidadVerificada`, sirven para una sola
cosa —comprobar que una reautenticación es de ahora— y **no se persisten, no
salen en ninguna respuesta y no se registran**. Lo que `persona` recibe siguen
siendo los tres campos de siempre. El porqué está en `IdentidadVerificada`.

El dominio es configurable, no literal
------------------------------------------
`unimayor.edu.co` es el de prueba (`D-16`, `DECISIONES-PENDIENTES.md`).
`DOMINIO_INSTITUCIONAL` lo trae por variable de entorno con ese valor por
defecto documentado: otra institución cambia un valor, no el código.

Por qué se exige `GOOGLE_CLIENT_ID`
----------------------------------------
`verify_oauth2_token()` comprueba la firma y la vigencia, pero **sin
audiencia no hay forma de comprobar que el token se emitió para este
sistema** y no para otra aplicación que también use Google como proveedor —
un token robado de otra app sería igual de válido sin ese tercer argumento.
Pisó `False`: sin la variable puesta, ningún token verifica, la misma postura
de no-favor-por-defecto que `Veredicto` y `aviso_legal.py` ya aplican.



"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from google.auth.transport import requests as _google_transporte
from google.oauth2 import id_token as _google_id_token

_registro = logging.getLogger(__name__)

# Google firma `iat` con su reloj y `google-auth` usa cero segundos de margen
# por defecto. Una estación o VPS correctamente sincronizado puede oscilar unas
# decenas de segundos respecto de Google; sin una tolerancia pequeña, un token
# recién emitido se rechaza como "used too early". Sesenta segundos cubren esa
# deriva operativa sin alterar firma, audiencia, caducidad, emisor ni dominio.
_DESFASE_RELOJ_SEGUNDOS = 60


def _motivo_de_verificacion(error: Exception) -> str:
    """Clasificación operativa sin copiar el mensaje potencialmente sensible."""
    texto = str(error).casefold()
    if "audience" in texto:
        return "audiencia"
    if "expired" in texto:
        return "expirado"
    if "too early" in texto or "issued at" in texto:
        return "reloj_adelantado"
    if "signature" in texto or "certificate" in texto or "signing key" in texto:
        return "firma"
    if "issuer" in texto:
        return "emisor"
    return "otro"

#: `DD-18` fija Google; `D-16` fija el dominio de prueba. Configurable, no
#: literal — ver la cabecera del módulo.
DOMINIO_INSTITUCIONAL = os.environ.get("DOMINIO_INSTITUCIONAL", "unimayor.edu.co")

#: El client ID de la aplicación registrada en Google Cloud Console. Sin él,
#: `verificar_id_token()` rechaza cualquier token — ver la cabecera del módulo.
_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")


@dataclass(frozen=True)
class IdentidadVerificada:
    """La identidad verificada y los datos efímeros necesarios en esta petición.

    ⚠️ Los dos timestamps no son un cuarto y un quinto campo de perfil: son la
    prueba de frescura del hito R7-A y no se guardan en ninguna parte. `DD-18`
    sigue autorizando exactamente tres campos de identidad *a persistir*
    —identificador, correo, nombre—, y son los tres que
    `_persistir_identidad()` escribe en `persona`. Los tiempos y `foto_url`
    viven lo que dura la petición; la imagen descargada se guarda aparte en el
    almacén privado, nunca como URL de Google.

    Por qué se conservan, después de haberlos descartado
    ------------------------------------------------------------
    Hasta el hito R7-A esta clase tiraba `iat` y `auth_time`, y la consecuencia
    la encontró la revisión: `POST /api/sesion/reautenticar` aceptaba **cualquier
    id_token todavía vigente** del mismo sujeto y anotaba la hora del servidor.
    El reloj del servidor acredita cuándo *llegó* el token; no dice nada de
    cuándo se emitió. Un token de hace cuarenta minutos, guardado por quien lo
    interceptó, reautenticaba igual que uno recién obtenido — y reautenticar
    existe precisamente para exigir que la persona esté delante ahora.

    `emitido_en` (`iat`) y `autenticado_en` (`auth_time`)
    -------------------------------------------------------------
    Los dos son `datetime` **conscientes de zona, en UTC**, o `None` cuando el
    token no trae el claim o no es interpretable. `None` no se rellena con un
    valor supuesto: quien decide qué hacer sin frescura firmada es
    `emision_recien_firmada()`, y para eso tiene que poder distinguir «no vino»
    de «vino y era viejo».

    ⚠️ **Salen del diccionario de claims que devolvió la verificación
    criptográfica**, nunca de decodificar el JWT a mano. Un `iat` leído del
    cuerpo del token sin comprobar la firma es un número que escribe quien manda
    la petición, que es justo lo contrario de lo que aquí hace falta.
    """

    identificador: str
    correo: str
    nombre: str
    #: `iat` firmado por Google, en UTC. **Sin valor por defecto a propósito**:
    #: un defecto haría que cualquier doble de pruebas —y cualquier construcción
    #: futura— pareciera recién emitido sin que nadie lo hubiera declarado, y la
    #: comprobación de frescura pasaría a estar apagada por omisión.
    emitido_en: datetime | None
    #: `auth_time`, cuando el token lo trae. Ver `emision_recien_firmada()`: se
    #: comprueba si viene y no se inventa si falta.
    autenticado_en: datetime | None = None
    foto_url: str = ""


def esta_configurado() -> bool:
    """Si este despliegue puede verificar tokens de Google.

    `compose.produccion.yaml` pasa `GOOGLE_CLIENT_ID` con defecto **vacío** y
    no con `:?` —el motivo está allí—, así que el sistema arranca sin
    credencial y el login de Google simplemente no funciona. Eso es correcto
    mientras `PM-X08` (el cliente OAuth) no exista, pero **no puede quedar
    callado**: `/api/salud` lo publica en `faltantes` para que quien depure un
    401 sepa si le falta configuración o si el token es de verdad inválido.
    """
    return bool(_CLIENT_ID)


def verificar_id_token(id_token_recibido: str) -> IdentidadVerificada | None:
    """`None` si el token no es válido, no tiene audiencia configurada, o no
    es del dominio institucional — nunca lanza.

    Un token corrupto, expirado o de otro proveedor no es un error del
    servidor: es lo que pasa cuando algo manda un token que no sirve, y el
    borde lo trata como identidad rechazada, no como excepción que revienta
    la petición.
    """
    if not id_token_recibido:
        _registro.warning("identidad_google_rechazada motivo=token_ausente")
        return None
    if not _CLIENT_ID:
        _registro.warning("identidad_google_rechazada motivo=cliente_no_configurado")
        return None
    try:
        claims = _google_id_token.verify_oauth2_token(
            id_token_recibido,
            _google_transporte.Request(),
            _CLIENT_ID,
            clock_skew_in_seconds=_DESFASE_RELOJ_SEGUNDOS,
        )
    except Exception as error:  # noqa: BLE001 — cualquier fallo es rechazo, no excepción
        # No se registra el token, los claims ni el texto de la excepción:
        # los dos primeros son credenciales/datos personales y el tercero puede
        # repetirlos. La clase basta para distinguir una credencial inválida de
        # un fallo de transporte durante una operación local o en producción.
        _registro.warning(
            "identidad_google_rechazada motivo=verificacion categoria=%s clase=%s",
            _motivo_de_verificacion(error),
            type(error).__name__,
        )
        return None
    # RECHAZA ANTES DE MIRAR NADA MÁS, tal como el encargo lo pide: sin `hd`
    # o con `hd` distinto, no importa qué más diga el token.
    if claims.get("hd") != DOMINIO_INSTITUCIONAL:
        _registro.warning("identidad_google_rechazada motivo=dominio_institucional")
        return None
    identificador = claims.get("sub")
    correo = claims.get("email")
    if not identificador or not correo:
        _registro.warning("identidad_google_rechazada motivo=claims_incompletos")
        return None
    return IdentidadVerificada(
        identificador=str(identificador),
        correo=str(correo).strip().lower(),
        nombre=str(claims.get("name") or ""),
        # Del diccionario ya verificado, nunca del JWT sin verificar.
        emitido_en=_momento_del_claim(claims.get("iat")),
        autenticado_en=_momento_del_claim(claims.get("auth_time")),
        foto_url=str(claims.get("picture") or ""),
    )


def _momento_del_claim(valor: object) -> datetime | None:
    """Un claim de tiempo de OIDC como `datetime` UTC, o `None`.

    OIDC define `iat` y `auth_time` como **segundos desde el epoch**, y así los
    entrega `verify_oauth2_token()`. Se acepta el entero y el número escrito como
    cadena de dígitos —un proveedor podría serializarlo así— y **nada más**:
    convertir cualquier otra cosa sería adivinar.

    `True` es `int` en Python y aquí no vale: `bool` se descarta antes de mirar
    el tipo numérico, o `iat=True` se leería como el segundo 1 del epoch — un
    token de 1970, que la ventana rechazaría, pero por el motivo equivocado.

    Devuelve `None` en vez de levantar: un claim ilegible es un token que no
    sirve para reautenticar, y quien decide eso es la comprobación de frescura,
    no esta conversión.
    """
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto.isdigit():
            return None
        valor = int(texto)
    if not isinstance(valor, int | float):
        return None
    try:
        return datetime.fromtimestamp(float(valor), tz=UTC)
    except (OSError, OverflowError, ValueError):
        # Un epoch fuera del rango representable. No es identidad rechazada: es
        # un claim que no se puede leer, y se trata como si no viniera.
        return None
