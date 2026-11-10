"""
decision_conjunta.py — La única acción visible del recorrido (`D0` §10.10, `D1B`)
==================================================================================

Una ruta:

    POST /api/consentimiento/decision-conjunta

y un cuerpo que sólo puede decir una cosa:

    {"decision": "otorgado"}   ·   {"decision": "rechazado"}

Qué sustituye, y por qué no se podía dejar como estaba
-----------------------------------------------------------------
`POST /api/consentimiento/titular` y `POST /api/consentimiento/asentimiento`
existían por separado y las llamaba el navegador una detrás de otra. Eso permitía
—y en el caso del menor **producía**— un estado que nadie decidió: el
consentimiento del titular escrito y el asentimiento no, porque la segunda
petición se perdió, falló o nunca se hizo.

`D0` §10.10 lo cierra: una acción, y los actos guardados **atómicamente por el
servidor**. Las dos rutas parciales responden hoy `410`; ésta es la vigente.

Qué NO puede decir el cuerpo, y es la mitad del contrato
------------------------------------------------------------------
La lista de claves admitidas tiene **un** elemento. Cualquier otra propiedad es
un `400`, y en particular estas cinco, que el encargo nombra una a una:

| lo que alguien podría mandar | por qué se rechaza |
|---|---|
| `edad` | decide el régimen entero de `EQ-016`: cuántos actos se escriben |
| `version` | dejarla elegir permite aceptar un texto ya desplazado (hito A2) |
| `alcance` | decide en qué tabla cae el acto |
| `huella` | es la prueba de qué paquete se leyó |
| `comprobante` | uno que enviara el navegador probaría lo que el navegador quisiera |

No se ignoran en silencio: se rechaza la petición entera. Ignorar un campo deja
a quien lo mandó creyendo que se aplicó, y ésa es la forma más silenciosa de que
un cliente acabe dependiendo de algo que el servidor nunca miró.

Los tres desenlaces que no son éxito, y no se confunden
------------------------------------------------------------------
- **`409` + `estado: "sin_version"`** con `alcances_faltantes` · el equipo no ha
  publicado el texto de algún alcance necesario. Cero eventos escritos. Es el
  estado real de este árbol hoy.
- **`409` + `estado: "perfil_incompleto"`** · la persona no ha declarado edad.
  Sin edad no hay régimen que aplicar. Cero eventos escritos.
- **`409` + `estado: "decision_ya_vigente"`** · el par entero ya dice
  exactamente eso sobre las versiones que rigen. Cero eventos escritos.
- **`409` + `estado: "usar_revocacion"`** con `rutas_de_revocacion` · se pidió
  rechazar con una autorización vigente y al día. `EQ-022` separa rechazar de
  revocar y esta ruta no puede sustituir a aquélla.
- **`409` + `estado: "eliminacion_solicitada"`** con `usar` · hay un trámite de
  supresión abierto. Durante él se consulta y se cancela, no se trata nada
  nuevo. Cero eventos escritos y la solicitud **intacta**.
- **`503` + `estado: "mantenimiento"`** · PostgreSQL o su esquema no responden.
  **Nunca** se degrada a una aceptación aparente (`EQ-024`).

Y un `409` sin `estado` para el resto de rechazos con motivo —transición
inválida, versión desplazada entre la lectura y la escritura, decisión
concurrente que llegó antes—, que se distinguen por el `detalle` que redacta el
dominio.

El aviso por correo va DESPUÉS y no forma parte de la decisión · `D2`
------------------------------------------------------------------------
Cuando la decisión fue **otorgada** y sus actos ya están confirmados, se intenta
un aviso al correo verificado de la sesión. Cuatro reglas, y las cuatro son
contrato:

1. **sólo por otorgar.** Un rechazo no produce correo. `DECISIONES.md` §`EQ-024`
   cierra el alcance de `D2` en tres hechos y ése no está;
2. **uno solo, también para el menor.** Los dos actos son *una* decisión: la
   clave sale de la secuencia del acto del **titular**, así que aunque haya dos
   recibos hay un correo. Un aviso por acto habría mandado dos correos por una
   sola acción visible, que es justo lo que `D0` §10.10 quiso dejar de hacer;
3. **al correo de la sesión**, verificado por Google, nunca a uno del cuerpo —el
   cuerpo de esta ruta admite exactamente una clave y no es ésa—;
4. **su fallo no toca nada.** Los actos están confirmados antes de llamar al
   canal, fuera de la transacción; `aviso_enviado: false` significa «no salió el
   correo», nunca «no se registró la decisión» (`EQ-024`).

`aviso_enviado` acompaña siempre a la respuesta exitosa, y en un **rechazo** vale
`false` porque no había ningún aviso que enviar. Quien la lee sabe qué decidió y
sólo menciona el correo cuando otorgó; ver `Consentimiento.svelte`.


"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import (
    json_del_cuerpo,
    mantenimiento,
    requerir_sesion,
)
from adaptadores.entrantes.http.rutas.consentimiento_comun import (
    recibo_de,
    responder_con_estado,
)
from dominio.modelo.decision_conjunta import Decision, decision_desde
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    EscrituraRechazada,
    PerfilSinEdad,
)
from dominio.puertos.decision_conjunta import (
    DecisionYaVigente,
    RevocacionRequerida,
    SupresionEnCurso,
    VersionesFaltantes,
)

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

    from adaptadores.entrantes.http.rutas.consentimiento_comun import Repositorios
from adaptadores.entrantes.http.sesiones import Sesiones
from adaptadores.salientes.notificacion.plantillas import decision_registrada

#: El camino de la única acción visible. Constante para que el `410` de las
#: rutas parciales lo cite de aquí y no de un literal que pueda desincronizarse.
CAMINO = "/api/consentimiento/decision-conjunta"

#: Las dos rutas que retiran una concesión otorgada. Se nombran en el cuerpo
#: del rechazo cuando alguien intenta usar la negativa como sustituto: sin
#: decirlo, «no puedes rechazar» deja a quien lo lee sin saber qué sí puede.
RUTAS_DE_REVOCACION = (
    "/api/consentimiento/titular/revocar",
    "/api/consentimiento/asentimiento/revocar",
)

#: Dónde se consulta y se cancela el trámite de `EQ-022`. Se nombra en el
#: rechazo por la misma razón: un «no puedes» a secas deja a quien lo lee sin
#: saber qué sí puede, y aquí lo que puede es cancelar dentro del plazo.
RUTA_DEL_TRAMITE = "/api/datos/supresion"

#: Lo único que el cuerpo puede traer. Una lista cerrada y no una comprobación
#: campo a campo: así, el día que alguien invente una propiedad nueva, el
#: rechazo no depende de que se acuerde de añadirla a una lista de prohibidas.
#:
#: Pública porque **es** parte del contrato de la ruta, y
#: `pruebas/unidad/test_decision_conjunta_contratos.py` la comprueba por su
#: nombre en vez de asomarse a un privado del módulo.
CLAVES_ADMITIDAS = frozenset({"decision"})

#: `D2` · el asunto del aviso de una decisión otorgada.
#:
#: Sin nombre, sin versión y sin identificadores: un asunto se lee en la lista de
#: la bandeja, antes de que nadie decida abrir el correo, y a veces en la
#: pantalla de bloqueo de un teléfono ajeno.
_ASUNTO_DECISION = "Tu autorización quedó registrada"

#: El texto. Lo mínimo para entender el hecho y una remisión a la aplicación
#: autenticada, donde están los recibos con su versión, su huella y su secuencia.
#:
#: **No copia los comprobantes.** `EQ-021` los conserva como constancia del acto
#: y la aplicación los muestra; duplicarlos en un correo los sacaría del sistema
#: que los custodia hacia un buzón que el proyecto no controla, sin que eso
#: añada ninguna garantía —el correo no es autoritativo—.
_CUERPO_DECISION = (
    "Registramos tu decisión sobre el tratamiento de tus datos en DidaxIa.\n\n"
    "Puedes ver la constancia completa —qué versión aceptaste y cuándo— "
    "entrando con tu cuenta institucional.\n\n"
    "Si no fuiste tú, entra y retira la autorización desde «Mis datos»."
)

#: Cómo se deriva la clave de idempotencia (`D2`).
#:
#: De `actos.titular.secuencia`: el identificador que PostgreSQL asignó al acto
#: del titular **ya persistido**, que existe siempre —para el adulto y para el
#: menor— y es uno solo por decisión. Nunca del correo, que es un dato personal y
#: además no identifica el hecho: la misma persona decide más de una vez.
_CLAVE_DECISION = "decision-conjunta/{secuencia}"
_URL_MIS_DATOS = "https://app.didaxia.pro/mis-datos"


def registrar_en(router: APIRouter, sesiones: Sesiones, repos: Repositorios) -> None:
    """Cuelga la ruta del router que le pasen. **No crea uno propio.**

    Podría devolver un `APIRouter` para que `rutas/consentimiento.py` lo
    incluyera, y sería lo idiomático. No se hace porque `include_router()` deja
    en `router.routes` un `_IncludedRouter` **sin `.path` ni `.methods`** —lo
    documenta ya `pruebas/unidad/test_aplicacion_docente.py`—, y media docena de
    pruebas de este árbol localizan una ruta recorriendo esa lista. Un router
    plano las deja funcionando y no esconde esta ruta de ninguna enumeración.

    La separación que importa —el cuerpo de la ruta, su validación y su
    traducción de desenlaces— vive aquí igual.
    """

    # `Request` se importa en tiempo de ejecución y no bajo `TYPE_CHECKING`, aun
    # con `from __future__ import annotations`: FastAPI resuelve las anotaciones
    # de cada handler para construir su esquema, y una que no pueda resolver
    # rompe `app.openapi()` — no al importar, sino la primera vez que alguien
    # pide el esquema.
    @router.post(CAMINO)
    async def decidir(peticion: Request) -> JSONResponse:
        """Una decisión, todos sus actos, una transacción.

        La ruta no abre ninguna transacción y no sabe cuántos actos van a
        escribirse: se lo pregunta al puerto, que lo resuelve con la fila de la
        persona bloqueada. Aquí sólo se valida la forma del cuerpo, se traduce
        el desenlace y se devuelve el estado recalculado con los recibos reales.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        cuerpo = await json_del_cuerpo(peticion)

        sobrantes = sorted(set(cuerpo) - CLAVES_ADMITIDAS)
        if sobrantes:
            return JSONResponse(
                {
                    "detalle": (
                        "el cuerpo de esta decisión sólo admite «decision»; el "
                        "servidor resuelve edad, versión, alcance, huella y "
                        f"comprobante. Sobra: {sobrantes}"
                    ),
                    "estado": "cuerpo_no_admitido",
                },
                status_code=400,
            )
        decision = decision_desde(cuerpo.get("decision"))
        if decision is None:
            return JSONResponse({"detalle": "decisión no admitida"}, status_code=400)

        sujeto = datos["identificador_estable"]
        try:
            actos = repos.decision_conjunta.registrar_decision(sujeto, decision)
        except VersionesFaltantes as error:
            # `EQ-021` sin texto publicado. No es un error del cliente: no hay
            # nada que aceptar, y decirlo —nombrando cuáles faltan— es más
            # honesto que un 400. Cero eventos escritos.
            return JSONResponse(
                {
                    "detalle": str(error),
                    "estado": "sin_version",
                    "alcances_faltantes": [a.value for a in error.alcances],
                },
                status_code=409,
            )
        except PerfilSinEdad as error:
            # Se distingue de lo anterior porque se arregla de otra forma: no
            # falta un documento, falta que la persona diga su edad.
            return JSONResponse(
                {"detalle": str(error), "estado": "perfil_incompleto"},
                status_code=409,
            )
        except SupresionEnCurso as error:
            # `EQ-022` · durante el trámite se consulta y se cancela, no se trata
            # nada nuevo. Cero actos escritos y la solicitud intacta.
            #
            # El cuerpo no lleva el sujeto, el correo ni las fechas del trámite:
            # un 409 se le enseña a cualquiera que mire una consola, y quien
            # necesite esos datos los pide por la ruta del trámite con su sesión.
            return JSONResponse(
                {
                    "detalle": str(error),
                    "estado": "eliminacion_solicitada",
                    "usar": RUTA_DEL_TRAMITE,
                },
                status_code=409,
            )
        except DecisionYaVigente as error:
            # El doble clic, la petición duplicada y la segunda de dos
            # simultáneas. Cero actos: repetir una decisión no la hace más
            # cierta y crearía un evento que nadie tomó.
            return JSONResponse(
                {"detalle": str(error), "estado": "decision_ya_vigente"},
                status_code=409,
            )
        except RevocacionRequerida as error:
            # `EQ-022` · rechazar no es un atajo para revocar. Se dice cuál es
            # la puerta que corresponde, porque un «no puedes» a secas deja a
            # quien lo lee sin saber qué sí puede.
            return JSONResponse(
                {
                    "detalle": str(error),
                    "estado": "usar_revocacion",
                    "rutas_de_revocacion": list(RUTAS_DE_REVOCACION),
                },
                status_code=409,
            )
        except EscrituraRechazada as error:
            # Transición inválida —doble clic o decisión concurrente—, versión
            # desplazada entre la lectura y la escritura, persona sin registrar.
            # Todas son rechazos con motivo utilizable y sin datos de nadie.
            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo registrar la decisión")

        # `D2` · el aviso va aquí: **después** de que la transacción confirmara
        # los actos y fuera de ella. Un fallo del canal no puede revertir nada
        # porque ya no hay nada que revertir, y su resultado se representa en vez
        # de fingirse. Ver la cabecera de este módulo.
        aviso = False
        if actos.decision is Decision.OTORGADO:
            aviso = repos.notificacion.avisar(
                datos["correo"],
                _ASUNTO_DECISION,
                _CUERPO_DECISION,
                clave_idempotencia=_CLAVE_DECISION.format(
                    secuencia=actos.titular.secuencia
                ),
                html=decision_registrada(
                    destinatario=str(datos.get("nombre") or ""),
                    url_accion=_URL_MIS_DATOS,
                ),
            )

        return responder_con_estado(
            repos,
            sujeto,
            {
                "recibos": [recibo_de(acto, acto.alcance) for acto in actos.actos],
                "aviso_enviado": aviso,
            },
        )
