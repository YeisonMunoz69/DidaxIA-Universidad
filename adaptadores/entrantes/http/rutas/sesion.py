"""
sesion.py — Abrir, reautenticar, leer y cerrar sesión · identidad y edad
=======================================================================================

Las rutas por las que alguien **empieza** a usar el sistema: la identidad
delegada de `DD-18`/`PM-B15`, la conversación nueva, la reautenticación
acreditada de `EQ-022` y la edad de `DD-26`. Van juntas porque comparten el mismo
estado —el almacén de sesiones— y porque las decisiones se toman en la misma
pantalla del cliente.

Una sola puerta, y ninguna anónima · `EQ-020`
-----------------------------------------------------------------
`POST /api/sesion/google` verifica el `id_token` y **el rol lo decide el
servidor** con `docentes.py`. Antes de `PM-B15` la vía anónima aceptaba `rol` del
cuerpo, así que `{"rol":"docente"}` bastaba para pasar `requerir_rol` — las
guardas del frontend son cortesía, no seguridad. Desde el hito B1 esa vía está
retirada: `GET /api/sesion` no crea nada y `POST /api/sesion` responde 401.

⚠️ Token de autenticación y conversación son cosas distintas · hito R1
------------------------------------------------------------------------------
El valor de la cookie `HttpOnly` **no vuelve nunca en un cuerpo**, y
`POST /api/sesion/reiniciar` cambia sólo el identificador de conversación: la
autenticación, su token y sus siete días siguen donde estaban. El porqué y las
tres consecuencias que tenía confundirlos están en `sesiones.py`.

⚠️ La reautenticación la acredita el servidor · hito R3 · corregido en R7-A
------------------------------------------------------------------------------
`POST /api/sesion/reautenticar` recibe un `id_token`, lo verifica con la misma
comprobación criptográfica de siempre, **exige que el `sub` sea el de esta
sesión**, **exige que Google lo haya firmado hace un momento** y anota el
instante con el reloj del servidor. El token no se guarda.
`POST /api/datos/supresion` consume esa prueba y no acepta ninguna fecha del
cuerpo.

⚠️ **La tercera condición faltaba, y aquí decía que estaba.** Hasta el hito R7-A
este archivo hablaba de «un `id_token` fresco» y no comprobaba ninguna frescura:
`IdentidadVerificada` descartaba `iat`, así que servía cualquier token todavía
vigente del mismo sujeto —hasta una hora de antigüedad— y el reloj del servidor
le ponía encima una marca reciente. Lo que se acreditaba era **cuándo llegó el
token**, no cuándo se emitió, y son cosas distintas: reautenticar existe para
exigir que la persona esté delante ahora. La regla vive en
`dominio/modelo/supresion.py` §`emision_recien_firmada()`, con su tolerancia de
reloj declarada.

⚠️ `POST /api/consentimiento` está retirada · hito R2
------------------------------------------------------------------------------
Escribía la decisión en el `dict` de sesión y en `consentimiento_usuario`, y al
declarar una edad menor de 18 ejecutaba una cascada de borrado. Ninguna de las
tres cosas es admisible bajo `EQ-016`/`EQ-021`: la autorización vigente vive en
`consentimiento_evento`, el acceso lo calcula `dominio/modelo/acceso.py` y borrar
sólo ocurre por el trámite reversible de `EQ-022`. Responde 410 y orienta a
`/api/consentimiento/decision-conjunta`; C1 ya actualizó al consumidor.

De dónde sale el repositorio de consentimiento
---------------------------------------------------------
**Entra por parámetro, como el resto.** `crear_router()` recibe un
`PuertoConsentimiento` y `aplicacion.py` decide cuál construir. Desde el hito R2
sólo lo consulta `POST /api/sesion/google`, para rellenar los campos informativos
de la sesión; ninguna ruta de este archivo escribe ya en aquel almacén.


"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http import aviso_legal, cookies, identidad
from adaptadores.entrantes.http.docentes import RegistroDeDocentes
from adaptadores.entrantes.http.investigadores import aprovisionar_rol_configurado
from adaptadores.entrantes.http.rol_de_presentacion import rol_de_presentacion
from adaptadores.entrantes.http.rutas.comun import (
    json_del_cuerpo,
    mantenimiento,
    requerir_sesion,
)
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones
from dominio.modelo.identidad import Identidad, IdentidadInvalida, PerfilOnboarding
from dominio.modelo.supresion import (
    SEGUNDOS_DE_REAUTENTICACION_RECIENTE,
    emision_recien_firmada,
)
from dominio.puertos.almacen import ErrorDeAlmacen

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.salientes.almacenamiento.fotos_perfil import AlmacenFotosPerfil
    from dominio.puertos.consentimiento import PuertoConsentimiento
    from dominio.puertos.identidad import PuertoIdentidad
    from dominio.puertos.roles import PuertoAsignacionDeRoles

#: El rango que se admite como edad declarada. No es una validación de
#: identidad —`DD-26` es explícito en que esto es un valor declarado— sino el
#: filtro mínimo para no guardar un número imposible: una edad negativa no es
#: «menor de edad», es un cuerpo mal formado, y tratarla como declaración de
#: minoría bloquearía a alguien por un error de tecleo del cliente.
_EDAD_MINIMA_ADMISIBLE = 0
_EDAD_MAXIMA_ADMISIBLE = 120


def edad_del_cuerpo(valor) -> int | None:
    """La edad que trae la petición, o `None` si no es utilizable.

    Acepta el entero y la cadena de dígitos —un formulario HTML manda texto—,
    y rechaza todo lo demás. `True` es `int` en Python y aquí no vale: es
    exactamente el booleano de antes de `DD-26` colándose por el campo nuevo.
    """
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        if not valor.isdigit():
            return None
        valor = int(valor)
    if not isinstance(valor, int):
        return None
    if not _EDAD_MINIMA_ADMISIBLE <= valor <= _EDAD_MAXIMA_ADMISIBLE:
        return None
    return valor


#: Cuánto vive la cookie en el navegador. Vive en `cookies.py` con el resto de
#: sus atributos; se reexporta aquí porque el nombre era público de este módulo.
#:
#: ⚠️ **Eran 30 días y ahora son 7.** `EQ-020` fija siete días de sesión, y
#: `sesiones.TTL_SESION_SEGUNDOS` ya los aplicaba en el servidor: la cookie los
#: contradecía durante veintitrés días, en los que el navegador la seguía
#: mandando y el servidor la rechazaba. No era un agujero —el servidor decide—
#: pero sí una pantalla que decía «sin sesión» sin que nada explicara por qué.
COOKIE_DURACION_SEGUNDOS = cookies.DURACION_SEGUNDOS


def _persistir_identidad(
    identidades: PuertoIdentidad | None, verificada: identidad.IdentidadVerificada
) -> PerfilOnboarding | JSONResponse:
    """Deja la identidad en `persona`, o la respuesta que impide la sesión.

    Devuelve el perfil persistido cuando todo fue bien y una respuesta cuando
    no se puede continuar. El perfil importa: contiene la edad declarada que
    debe sustituir al 18 provisional del modo piloto al abrir cada sesión.

    Los tres desenlaces posibles y por qué son tres:

    - **sin almacén cableado** · el despliegue está incompleto (falta `AGENTE_BD`
      o la migración 11). No es transitorio, pero al cliente le da igual: no
      puede entrar, y decirle *por qué* filtraría configuración. Mantenimiento.
    - **almacén caído** · mantenimiento de verdad, el de `EQ-024`.
    - **identidad inaceptable** · Google mandó algo que el dominio no admite.
      Es un 401, no un 503: reintentar no lo arregla.
    """
    if identidades is None:
        return mantenimiento("el registro de identidad no está disponible")
    try:
        return identidades.registrar(
            Identidad(
                sujeto_google=verificada.identificador,
                correo=verificada.correo,
                nombre=verificada.nombre,
            )
        )
    except IdentidadInvalida:
        return JSONResponse(
            {"detalle": "la identidad verificada no es utilizable"}, status_code=401
        )
    except ErrorDeAlmacen:
        # El motivo concreto no cruza: nombraría la base o su configuración.
        return mantenimiento("no se pudo registrar la identidad en este momento")


def _con_cookie(cuerpo: dict, identificador: str) -> JSONResponse:
    """La respuesta que instala la cookie de sesión, con sus atributos.

    Un solo sitio: hasta el hito B1 los cinco `set_cookie()` de este módulo
    repetían los atributos a mano, y el sexto habría olvidado uno.
    """
    respuesta = JSONResponse(cuerpo)
    respuesta.set_cookie(
        COOKIE, identificador, max_age=COOKIE_DURACION_SEGUNDOS, **cookies.atributos()
    )
    return respuesta


def crear_router(  # noqa: PLR0913
    sesiones: Sesiones,
    registro_docentes: RegistroDeDocentes,
    consentimiento_almacen: PuertoConsentimiento,
    identidades: PuertoIdentidad | None = None,
    *,
    roles: PuertoAsignacionDeRoles | None = None,
    fotos: AlmacenFotosPerfil | None = None,
    invitaciones=None,
) -> APIRouter:
    """`identidades` es opcional **para no romper a quien componga sin base**.

    Cuando falta, `POST /api/sesion/google` responde mantenimiento en vez de
    crear una sesión sin identidad persistida: `EQ-024` prohíbe el éxito
    simulado, y una sesión que no se puede volver a reconocer tras un reinicio es
    exactamente eso. `aplicacion.py` lo declara en `/api/salud`.

    ⚠️ **`roles` entra por nombre y su ausencia NO es permisiva.** Es el
    `PuertoAsignacionDeRoles` con el que `POST /api/sesion/google` resuelve si
    esta cuenta se presenta como investigadora (`EQ-023`). Sin él, esa ruta
    responde mantenimiento en vez de entregar `estudiante`: no saber si alguien
    tiene un rol no es lo mismo que saber que no lo tiene, y montar el árbol
    equivocado por un fallo de composición sería el éxito parcial que `EQ-024`
    prohíbe. `aplicacion.py` le pasa **el mismo adaptador** que compone para el
    gobierno de datos, para que no haya dos lecturas de `rol_asignacion` capaces
    de discrepar. El porqué entero está en `rol_de_presentacion.py`.

    Va como argumento por nombre y al final para no reordenar una firma que
    cuatro módulos de prueba ya construyen posicionalmente.

    ⚠️ **`clases_almacen` y `adaptador_perfil` ya no entran** (hito R2). Los
    recibía únicamente `POST /api/consentimiento` para ejecutar su cascada de
    borrado al declarar una edad menor de 18. Retirada esa ruta, ninguna de estas
    rutas tiene por qué poder borrar nada, y seguir recibiendo los dos adaptadores
    habría dejado la capacidad a mano del siguiente que añadiera un handler aquí.
    Quitarlos es parte de cerrar el bypass, no una limpieza cosmética.
    """
    router = APIRouter()

    @router.get("/api/sesion")
    def sesion_actual(peticion: Request) -> JSONResponse:
        """La sesión actual, o 401. **Ya no crea ninguna.**

        Hasta el hito B1 esta ruta abría una sesión anónima al consultarla, y
        `EQ-020` lo prohíbe con todas las letras: *«el backend no crea una sesión
        al consultar una ruta pública»*. Quien llegue sin sesión recibe el estado
        que le corresponde —`sin_sesion`— y el cliente lo lleva a Google.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        return JSONResponse(sesiones.publico(datos))

    @router.post("/api/sesion")
    def abrir_sesion() -> JSONResponse:
        """La vía anónima, retirada en el hito B1.

        Se conserva la ruta y se niega, en vez de borrarla: un 404 se lee como
        «el backend se rompió» y esto es una decisión, no una avería. `EQ-020`:
        *«sólo existen usuarios autenticados con cuenta institucional»*.
        """
        return JSONResponse(
            {
                "detalle": (
                    "esta aplicación exige una cuenta institucional: "
                    "inicie sesión con Google"
                ),
                "estado": "sin_sesion",
            },
            status_code=401,
        )

    @router.post("/api/sesion/google")
    async def abrir_sesion_google(peticion: Request) -> JSONResponse:  # noqa: PLR0912
        """`PM-B15` A + B. El `id_token` que el cliente obtuvo de Google, la
        identidad delegada de `DD-18` y el rol de `D-16` opción C, los tres en
        una sola ruta porque las tres decisiones dependen una de la otra: sin
        identidad verificada no hay correo del que preguntarle al registro.

        **Desde el hito B1 es la única puerta que crea sesión**, y la identidad
        se persiste antes de crearla. El orden importa: si `persona` no se puede
        escribir, no hay sesión. Una sesión cuya identidad sólo existe en memoria
        se pierde en el primer reinicio y deja huérfano todo lo que se cuelgue de
        ella —consentimiento, evidencia, historial—, que es el éxito simulado que
        `EQ-024` prohíbe.

        La seguridad de OAuth no cambia: `identidad.verificar_id_token()` sigue
        comprobando firma, audiencia y `hd` antes de mirar cualquier otro campo, y
        el rol lo sigue decidiendo el servidor con sus propios registros.
        """
        cuerpo = await json_del_cuerpo(peticion)
        identidad_verificada = identidad.verificar_id_token(str(cuerpo.get("id_token") or ""))
        if identidad_verificada is None:
            return JSONResponse(
                {"detalle": "token de Google no válido, expirado o fuera de dominio"},
                status_code=401,
            )

        persistida = _persistir_identidad(identidades, identidad_verificada)
        if isinstance(persistida, JSONResponse):
            return persistida

        # Una invitación previa sólo se acepta con el secreto recibido por el
        # enlace y el correo que Google acaba de verificar. La asignación y la
        # auditoría ocurren dentro de una única transacción del repositorio.
        invitacion_token = str(cuerpo.get("invitacion") or "").strip()
        roles_aceptados = ()
        if invitacion_token and invitaciones is not None:
            try:
                roles_aceptados = invitaciones.aceptar_del_primer_inicio(
                    identidad_verificada.correo,
                    identidad_verificada.identificador,
                    hashlib.sha256(invitacion_token.encode("utf-8")).hexdigest(),
                )
            except ErrorDeAlmacen:
                return mantenimiento("no se pudo aceptar la invitación institucional")
            except ValueError:
                return JSONResponse({"detalle": "la invitación no es válida"}, status_code=400)

        # La foto de Google es sólo el valor inicial. Una foto que ya existe
        # —incluida una subida manualmente— siempre tiene prioridad.
        if fotos is not None and fotos.configurado and identidad_verificada.foto_url:
            try:
                referencia_actual = identidades.referencia_foto(
                    identidad_verificada.identificador
                )
                if not referencia_actual:
                    from adaptadores.salientes.almacenamiento.foto_google import (  # noqa: PLC0415
                        descargar_foto_google,
                    )
                    cuerpo_foto = descargar_foto_google(identidad_verificada.foto_url)
                    if cuerpo_foto:
                        nueva = fotos.guardar(cuerpo_foto)
                        try:
                            identidades.cambiar_foto(
                                identidad_verificada.identificador, nueva
                            )
                        except Exception:
                            fotos.retirar(nueva)
            except Exception:
                # La identidad y la sesión no dependen de un recurso visual.
                pass

        # Una cuenta declarada en la configuración operativa recibe aquí su
        # asignación persistente. La variable aprovisiona el registro; no lo
        # sustituye, por lo que las rutas siguen exigiendo el rol dentro de la
        # misma transacción que protege cada operación.
        if not aprovisionar_rol_configurado(
            roles=roles,
            sujeto_google=identidad_verificada.identificador,
            correo=identidad_verificada.correo,
        ):
            return mantenimiento("no se pudo aprovisionar el rol de esta cuenta")

        # ⚠️ El rol se resuelve **antes** de `sesiones.abrir()`, y fallar aquí
        # significa no abrir ninguna. Al revés quedaría una sesión creada con el
        # árbol equivocado, o —peor— una sesión abierta y una respuesta de
        # error: dos estados que se contradicen entre el servidor y el cliente.
        #
        # `investigador` → `docente` → `estudiante`, y el porqué de ese orden
        # está en `rol_de_presentacion.py`. Aquí no hay ninguna comparación de
        # correos para el rol de `EQ-023`: la única que queda es la de docente,
        # que es la de `D-16` opción C y no cambia.
        try:
            rol = rol_de_presentacion(
                roles=roles,
                registro_docentes=registro_docentes,
                sujeto_google=identidad_verificada.identificador,
                correo=identidad_verificada.correo,
            )
        except ErrorDeAlmacen:
            # El motivo concreto no cruza: nombraría la base o su configuración.
            return mantenimiento("no se pudo determinar el rol de esta cuenta")

        datos = sesiones.abrir(
            rol=rol,
            identificador_estable=identidad_verificada.identificador,
            correo=identidad_verificada.correo,
            nombre=identidad_verificada.nombre,
        )
        # La edad de `persona` es la autoridad. El 18 de `Sesiones.abrir()` es
        # sólo el valor provisional de DD-26 para una persona que todavía no la
        # ha declarado; conservarlo después de leer un perfil existente hacía
        # que «Mis datos» y el módulo conductual vieran una edad distinta a la
        # que gobierna el onboarding.
        if persistida.edad is not None:
            datos["edad"] = persistida.edad
        previo = consentimiento_almacen.consultar(
            identidad_verificada.identificador, identidad_verificada.correo
        )
        if previo and previo.get("decision"):
            datos["consentimiento"] = previo["decision"]
            # El almacén heredado sólo rellena una ausencia. Nunca puede
            # sustituir la edad más reciente que `persona` acaba de devolver.
            if persistida.edad is None and previo.get("edad") is not None:
                datos["edad"] = previo["edad"]

        publico = sesiones.publico(datos)
        if roles_aceptados:
            publico["invitacion_aceptada"] = [rol.value for rol in roles_aceptados]
        return _con_cookie(publico, datos["token"])

    @router.post("/api/sesion/reautenticar")
    async def reautenticar(peticion: Request) -> JSONResponse:
        """`EQ-022` · la prueba de reautenticación, acreditada por el servidor.

        Es el hito R3 entero. La revisión encontró que `POST /api/datos/supresion`
        recibía `reautenticada_en` del cuerpo y lo contrastaba con su reloj, lo
        que no demuestra nada: cualquiera que llame al API escribe la fecha que
        quiera. Aquí se sustituye por una prueba que el servidor construye.

        Las cinco condiciones, y por qué cada una:

        1. **hay sesión** — se reautentica una sesión concreta, no el aire;
        2. **el `id_token` verifica** — misma firma, audiencia y dominio
           institucional que `POST /api/sesion/google`; se reutiliza la
           comprobación en vez de escribir una segunda;
        3. **el `sub` es el de esta sesión** — un token perfectamente firmado de
           **otra** cuenta institucional no reautentica a ésta. Es la mitad que
           la criptografía sola no cubre;
        4. **Google lo firmó hace un momento** (hito R7-A) — el `iat` del token,
           tomado del diccionario de claims ya verificado, tiene que caber en la
           ventana de `EQ-022` con la tolerancia de reloj declarada, y el
           `auth_time`, si viene, no puede contradecirlo. Ésta es la condición
           que faltaba: sin ella el punto 2 sólo garantiza que el token **aún no
           ha expirado**, y un token vigente puede tener cincuenta minutos;
        5. **la marca la pone el reloj del servidor** — superadas las cuatro
           anteriores. `iat` demuestra la frescura; la autoridad sobre «cuándo
           acreditamos esto» sigue siendo de quien lo acredita, porque es la
           marca que `POST /api/datos/supresion` va a consumir.

        Y lo que NO cambia: `POST /api/sesion/google` sigue aceptando cualquier
        token válido según su contrato normal. Iniciar sesión no es reautenticar,
        y exigirle frescura de segundos convertiría un login legítimo con un
        token de hace un minuto en un fallo sin explicación.

        El `id_token` **no se guarda**, y sus marcas de tiempo tampoco: `EQ-022`
        necesita saber cuándo se acreditó, y el secreto con el que se demostró
        —o los claims que lo acompañaban— serían datos más que custodiar. No
        entran en la sesión, no salen en la respuesta y no se registran.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        cuerpo = await json_del_cuerpo(peticion)
        verificada = identidad.verificar_id_token(str(cuerpo.get("id_token") or ""))
        if verificada is None:
            return JSONResponse(
                {"detalle": "token de Google no válido, expirado o fuera de dominio"},
                status_code=401,
            )
        if verificada.identificador != datos["identificador_estable"]:
            # No se dice de quién era: confirmaría la existencia de otra cuenta.
            return JSONResponse(
                {
                    "detalle": "ese token no corresponde a la cuenta de esta sesión",
                    "estado": "sujeto_distinto",
                },
                status_code=401,
            )
        if not emision_recien_firmada(
            verificada.emitido_en,
            datetime.now(UTC),
            autenticado_en=verificada.autenticado_en,
        ):
            # El motivo no distingue «viejo», «del futuro», «sin `iat`» ni
            # «`auth_time` que se contradice»: los cuatro se arreglan igual
            # —volver a pasar por Google— y separarlos le diría a quien pruebe
            # tokens cuál de las comprobaciones acaba de esquivar.
            return JSONResponse(
                {
                    "detalle": (
                        "ese token no es lo bastante reciente para reautenticar: "
                        "vuelva a iniciar sesión con Google"
                    ),
                    "estado": "token_no_fresco",
                },
                status_code=401,
            )

        acreditada = sesiones.marcar_reautenticacion(datos)
        return JSONResponse(
            {
                "reautenticada": True,
                # El instante no cruza: al cliente le sirve saber cuánto le queda
                # para completar el diálogo, y un plazo relativo no depende de la
                # hora del navegador — el mismo criterio que `expira_en_segundos`.
                "vigente_por_segundos": SEGUNDOS_DE_REAUTENTICACION_RECIENTE,
                "acreditada_en": acreditada.isoformat(),
            }
        )

    @router.delete("/api/sesion")
    def cerrar_sesion(peticion: Request) -> Response:
        """`EQ-024` · cerrar sesión la invalida en el servidor, no sólo en el
        navegador.

        Las dos mitades hacen falta: `sesiones.cerrar()` retira el estado —de
        modo que la misma cookie ya no vale aunque alguien la conserve— y
        `delete_cookie()` limpia el navegador. Con sólo la segunda, copiar la
        cookie antes de cerrar seguiría dando acceso.

        Los atributos de borrado tienen que coincidir con los de escritura o el
        navegador no borra nada; por eso salen del mismo módulo.
        """
        sesiones.cerrar(peticion.cookies.get(COOKIE))
        respuesta = Response(status_code=204)
        respuesta.delete_cookie(COOKIE, **cookies.atributos_de_borrado())
        return respuesta

    @router.post("/api/sesion/renovar")
    def renovar(peticion: Request) -> JSONResponse:
        """Lo que el cliente consulta para saber cuánto le queda (`EQ-020`).

        No prolonga la sesión y no debe: los siete días se cuentan desde que se
        abrió, y renovarlos al consultarlos convertiría el plazo en «siete días
        sin cerrar la pestaña». Devuelve `expira_en_segundos`, que es lo que C1
        necesita para avisar antes de tiempo.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        return JSONResponse(sesiones.publico(datos))

    @router.post("/api/sesion/reiniciar")
    def reiniciar_sesion(peticion: Request) -> JSONResponse:
        """«Nueva conversación»: otro hilo, **la misma sesión autenticada**.

        La conversación —contadores del arbitraje, `historial_reciente`,
        expresión previa— vive en `Sesiones`, en memoria del proceso. Limpiar
        solo el hilo del cliente y seguir con el MISMO identificador habría
        dejado el turno siguiente con el contexto de la conversación anterior por
        debajo: el estudiante vería una pantalla en blanco y el tutor le
        contestaría recordando lo de antes. Por eso se genera un identificador de
        conversación nuevo y se reinicia su estado.

        ⚠️ **Y por eso NO se abre una sesión nueva** (hito R1). Aquí decía que el
        plazo de siete días «se reinicia, y es correcto: `EQ-020` lo cuenta por
        sesión y ésta es una sesión nueva». No lo era: nadie había vuelto a
        autenticarse. La consecuencia medida por la auditoría es que quien
        empezara una conversación cada seis días conservaba la sesión para
        siempre, y el plazo de `EQ-020` dejaba de existir para el uso normal del
        producto — justo para quien más usa el tutor.

        Lo que cambia es el hilo; lo que se conserva es la autenticación: token,
        `creada_en`, identidad, rol y la prueba de reautenticación si la había.

        No es `DELETE /api/sesion` seguido de volver a entrar —el camino de
        «Cerrar sesión»—, que sí exige pasar otra vez por Google.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa

        sesiones.nueva_conversacion(datos)
        # La cookie no se reescribe: es la misma sesión y el mismo token.
        return JSONResponse(sesiones.publico(datos))

    @router.post("/api/consentimiento")
    def consentimiento_retirado() -> JSONResponse:
        """La ruta heredada de `RP-19`, retirada en el hito R2.

        Hacía tres cosas que `EQ-016`/`EQ-021` no admiten, y la auditoría V-B las
        enumeró como un solo hallazgo:

        1. **guardaba la decisión en el `dict` de sesión** —memoria del
           proceso— y respondía éxito. Un consentimiento que se pierde al
           reiniciar no es un consentimiento; es el éxito simulado de `EQ-024`
           sobre lo único que no admite simulación.
        2. **escribía en `consentimiento_usuario`** como si fuera el contrato
           vigente. El contrato vigente son los eventos inmutables y versionados
           de `consentimiento_evento`, con su alcance, sus finalidades y su
           comprobante; aquella tabla no tiene ninguna de las tres cosas.
        3. **ejecutaba una cascada de borrado al declarar una edad menor de 18.**
           Declarar la edad es completar un perfil, no ejercer el derecho de
           supresión. Borrar ahí saltaba el trámite de `EQ-022` entero —sin
           reautenticación, sin frase, sin las 24 horas para cancelar— por un
           campo de un formulario.

        Se conserva la ruta con **410** en vez de borrarla: un 404 se lee como
        «el backend se rompió» y esto es una decisión. `Gone` es exactamente lo
        que significa —existió, ya no— y el cuerpo dice adónde ir. C1 actualiza
        al consumidor; hasta entonces esta ruta no muta nada en ningún almacén.
        """
        return JSONResponse(
            {
                "detalle": (
                    "esta ruta fue retirada: el consentimiento versionado de EQ-021 "
                    "se decide en POST /api/consentimiento/decision-conjunta y la "
                    "edad se declara en POST /api/onboarding/perfil"
                ),
                "estado": "retirada",
                # ⚠️ Actualizado por `D1B`. Aquí decía `/titular` y
                # `/asentimiento`, que desde entonces también responden 410:
                # orientar a una puerta cerrada es peor que no orientar, porque
                # cuesta dos intentos descubrir cuál es la vigente.
                "usar": [
                    "/api/consentimiento/decision-conjunta",
                    "/api/onboarding/perfil",
                ],
            },
            status_code=410,
        )

    @router.get("/api/aviso-legal")
    def aviso_legal_ruta() -> JSONResponse:
        """`DD-15` y `RL-09`, servidos como dato. Sin sesión: es el mismo
        aviso para cualquiera, antes incluso de que exista una sesión."""
        return JSONResponse(aviso_legal.bloque_legal())

    return router
