"""
consentimiento.py — Onboarding, consentimiento versionado y evidencia (hito B2)
================================================================================

El recorrido completo de `EQ-020`/`EQ-021` por API, conectado por fin a la
frontera que el paquete A construyó: `persona`, versiones, eventos inmutables,
asentimiento y evidencia del representante.

Por qué es un módulo aparte de `rutas/sesion.py`
-----------------------------------------------------------
Porque son dos autoridades distintas. `rutas/sesion.py` decide **quién es** quien
llama; esto decide **qué ha autorizado**. Meterlas juntas habría dejado un
archivo donde una guarda de sesión y una regla de consentimiento se leen igual, y
la guía interna de mantenimiento pide separar por responsabilidad justamente para que no
pase.

✅ Las rutas heredadas están retiradas · hito R2 y `D1B`
------------------------------------------------------------
Tres, y por dos motivos distintos:

1. **`POST /api/consentimiento`** (en `rutas/sesion.py`) escribía en
   `consentimiento_usuario`, movía un `dict` de sesión y ejecutaba una cascada de
   borrado al declarar una edad menor de 18. El cierre V-B lo devolvió: conservar
   una ruta que responde éxito desde memoria y borra sin trámite no es
   compatibilidad, es una mentira funcional.
2. **`POST /api/consentimiento/titular`** y **`POST
   /api/consentimiento/asentimiento`**, desde `D1B`. Escribían de verdad, y ése
   era el problema: permitían **decisiones parciales**. Un menor podía acabar con
   el consentimiento del titular registrado y sin su asentimiento porque la
   segunda petición se perdió, y nadie decidió nunca ese estado. `D0` §10.10
   pide una acción y actos atómicos, así que las dos responden **410** y
   orientan a `POST /api/consentimiento/decision-conjunta`.

No se redirigen por dentro y no se conservan como puerta alternativa: una ruta
que sigue escribiendo «por compatibilidad» es la que reabre el hueco.

⚠️ Revocar tiene su propia ruta, y su propia regla de versión · hito R3
------------------------------------------------------------
`POST /api/consentimiento/titular/revocar` y `.../asentimiento/revocar`. **Siguen
separadas y siguen operativas**, y `D1B` no las toca: `EQ-022` separa dos
vigencias —otorgar y rechazar exigen la versión **requerida**, revocar retira la
concesión **efectivamente otorgada**, aunque su documento haya vencido o haya
sido desplazado— y `EQ-016` declara las dimensiones independientes, así que un
menor puede retirar su asentimiento sin tocar el consentimiento del titular. El
cliente no elige ninguna de las dos versiones: las resuelve el servidor.

Dónde vive la única acción visible
--------------------------------------------
En `rutas/decision_conjunta.py`, que este módulo **incluye**. Está aparte porque
es otra responsabilidad —una transacción que cruza dos dimensiones— y porque
este archivo ya rondaba las 800 líneas antes de `D1B`. Lo que comparten las dos
familias está en `rutas/consentimiento_comun.py`.

Qué NO decide este módulo
--------------------------------------
- **El texto legal, la huella y la versión inicial.** Siguen abiertos en
  `DECISIONES.md`. `GET /api/consentimiento/versiones` devuelve lo que haya en
  PostgreSQL —hoy, nada— y el acceso queda en onboarding. No se siembra ninguna.
- **Dónde vive el PDF.** `PuertoAlmacenamientoPrivado`, y en este árbol el
  adaptador que falla cerrado: sin carpeta ni custodia acordadas no se acepta
  evidencia. Desde el hito R4 el puerto tiene **tres** fases —reservar,
  confirmar, retirar— para que un fallo de PostgreSQL no deje un PDF firmado del
  que ninguna base tenga noticia.
- **Cuándo empieza el plazo del menor.** Lo fija `declarar_perfil()` en la misma
  sentencia que la edad (hito R4). Esta ruta ya no lo toca: hacerlo al recibir el
  primer PDF era lo que impedía que venciera quien no subía ninguno.
- **Quién puede revisar.** `EQ-023`, comprobado contra `rol_asignacion` y nunca
  contra un correo.


"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from adaptadores.entrantes.http import formato_representante, pdf
from adaptadores.entrantes.http.rutas import decision_conjunta as rutas_decision
from adaptadores.entrantes.http.rutas.comun import (
    json_del_cuerpo,
    mantenimiento,
    requerir_sesion,
)
from adaptadores.entrantes.http.rutas.consentimiento_comun import (
    Repositorios,
    estado_como_json,
    leer_estado,
    recibo_de,
    version_como_json,
)
from adaptadores.entrantes.http.rutas.puerta_de_supresion import (
    ESTADO as ESTADO_SUPRESION,
)
from adaptadores.entrantes.http.rutas.puerta_de_supresion import (
    RUTA_DEL_TRAMITE,
    PuertaDeSupresion,
    respuesta_de_supresion,
)
from adaptadores.entrantes.http.sesiones import Sesiones
from dominio.modelo.comprobante import comprobante_de
from dominio.modelo.consentimiento import Alcance, EstadoConsentimiento
from dominio.modelo.identidad import IdentidadInvalida
from dominio.modelo.menores import (
    TAMANO_MAXIMO_BYTES,
    TIPO_MIME_ESPERADO,
    EstadoAsentimiento,
    EvidenciaInvalida,
    ResultadoDeRevision,
)
from dominio.modelo.oferta_academica import OfertaAcademicaInvalida
from dominio.puertos.almacen import (
    AlmacenNoConfigurado,
    AlmacenNoDisponible,
    DatoNoAdmitido,
    EscrituraRechazada,
)
from dominio.puertos.almacenamiento_privado import (
    AlmacenamientoNoConfigurado,
    AlmacenamientoNoDisponible,
)
from dominio.puertos.gobierno import SupresionEnCurso

# Se reexportan para que la composición y las pruebas que ya los nombraban por
#: este módulo los sigan encontrando. **La autoridad no está aquí**: `D1B` movió
#: la agrupación de puertos a `consentimiento_comun.py` y el algoritmo del
#: comprobante a `dominio/modelo/comprobante.py`, porque la decisión conjunta lo
#: calcula dentro de la transacción y un adaptador saliente no puede importar de
#: uno entrante.
__all__ = ["Repositorios", "comprobante_de", "crear_router"]


def _entero(valor: object) -> int | None:
    """El entero que trae el cuerpo, o `None`. `True` es `int` y aquí no vale."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        if not valor.lstrip("-").isdigit():
            return None
        valor = int(valor)
    return valor if isinstance(valor, int) else None


def _campos_de_perfil(cuerpo: dict, vigente: object) -> tuple[dict, JSONResponse | None]:
    """Normaliza y protege el perfil; la ruta sólo coordina la escritura."""
    edad = _entero(cuerpo.get("edad")) if "edad" in cuerpo else None
    semestre = _entero(cuerpo.get("semestre")) if "semestre" in cuerpo else None
    if "edad" in cuerpo and edad is None:
        return {}, JSONResponse({"detalle": "edad no admitida"}, status_code=400)
    if "semestre" in cuerpo and semestre is None:
        return {}, JSONResponse({"detalle": "semestre no admitido"}, status_code=400)

    facultad = str(cuerpo.get("facultad") or "").strip()
    programa = str(cuerpo.get("programa") or "").strip()
    if not facultad and (
        vigente is None
        or not getattr(vigente, "programa", "")
        or getattr(vigente, "semestre", None) is None
    ):
        return {}, JSONResponse({"detalle": "facultad no admitida"}, status_code=400)

    campos = {"edad": edad, "programa": programa, "semestre": semestre}
    # La facultad se incorporó después del contrato inicial. Omitirla cuando un
    # cliente antiguo no la envía mantiene legibles los perfiles heredados; el
    # formulario vigente sí la exige y la manda siempre.
    if facultad:
        campos["facultad"] = facultad
    if "motivo" in cuerpo:
        campos["motivo"] = str(cuerpo.get("motivo") or "").strip()
    campos["origen"] = "onboarding_estudiante"
    return campos, None


def _ruta_retirada(alcance: str) -> JSONResponse:
    """`410` · esta ruta permitía decisiones parciales y ya no escribe.

    `Gone` y no `404`: un 404 se lee como «el backend se rompió» y esto es una
    decisión. El cuerpo dice adónde ir, y **no se redirige por dentro**: una
    redirección silenciosa dejaría al cliente creyendo que su llamada sigue
    valiendo y volvería a producir la decisión parcial por otro camino.
    """
    return JSONResponse(
        {
            "detalle": (
                f"esta ruta registraba el acto de alcance «{alcance}» por separado "
                "y permitía decisiones parciales. La decisión es una sola y sus "
                "actos se guardan atómicamente en el servidor"
            ),
            "estado": "ruta_retirada",
            "ruta_vigente": rutas_decision.CAMINO,
        },
        status_code=410,
    )


def crear_router(sesiones: Sesiones, repos: Repositorios) -> APIRouter:
    router = APIRouter()

    # La puerta de `EQ-022`, construida sobre el puerto de estado que este router
    # ya recibe. No abre una conexión propia ni copia la consulta: pregunta a
    # quien ya sabe responderlo.
    puerta = PuertaDeSupresion(repos.estado_vigente)

    # La única acción visible del recorrido vive en su propio módulo y se cuelga
    # aquí. `D1B` no la mete dentro de este archivo a propósito: es otra
    # responsabilidad —una transacción que cruza dos dimensiones— y este router
    # ya rondaba las 800 líneas antes de abrirla.
    rutas_decision.registrar_en(router, sesiones, repos)

    def _estado(sujeto: str):
        """`leer_estado()` con los repositorios de este router ya puestos."""
        return leer_estado(repos, sujeto)

    @router.get("/api/onboarding/estado")
    def estado_de_onboarding(peticion: Request) -> JSONResponse:
        """Todo lo que C1 necesita para pintar el recorrido, en una llamada.

        Una sola ruta y no cuatro porque las cuatro dimensiones tienen que
        describir el MISMO instante: pedirlas por separado dejaría al cliente
        combinando un perfil de hace un segundo con un consentimiento de ahora.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        estado, acceso, fallo = _estado(datos["identificador_estable"])
        if fallo is not None:
            return fallo
        return JSONResponse(estado_como_json(estado, acceso))

    @router.post("/api/onboarding/perfil")
    async def declarar_perfil(peticion: Request) -> JSONResponse:
        """Edad exacta, facultad, programa y semestre (`EQ-020`).

        Nombre y correo no se aceptan: vienen de Google y ya están en `persona`.
        Admitirlos aquí dejaría que el cliente reescribiera su propia identidad.

        La vinculación a curso tampoco: la resuelve el mecanismo de
        clase/matrícula que `08-clases.sql` ya tiene, y duplicarla habría creado
        dos respuestas para «¿está en una clase?».

        El orden es sesión → trámite → cuerpo → escritura. La puerta va **antes
        de leer el cuerpo**: declarar edad, facultad, programa o semestre es
        aportar datos nuevos, y durante una supresión abierta eso no se
        registra (`EQ-022`).
        Validar primero lo que igualmente se va a rechazar sólo sirve para
        devolver un `400` que confundiría — diría «tu edad no vale» cuando lo que
        pasa es que hay un trámite en curso.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        congelada = puerta.negativa(datos["identificador_estable"])
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)

        try:
            vigente = repos.identidades.consultar(datos["identificador_estable"])
            campos, negativa_del_perfil = _campos_de_perfil(cuerpo, vigente)
            if negativa_del_perfil is not None:
                return negativa_del_perfil
            perfil = repos.identidades.declarar_perfil(
                datos["identificador_estable"], **campos
            )
            # `persona` sigue siendo la autoridad; la sesión conserva una
            # proyección para el borde heredado de datos personales y para las
            # puertas que todavía reciben `datos`. Sin esta sincronización, la
            # base guardaba la corrección pero la pantalla seguía mostrando 18.
            if perfil is not None:
                datos["edad"] = perfil.edad
        except (IdentidadInvalida, OfertaAcademicaInvalida) as error:
            # El tipo del dominio ya rechazó el valor; su motivo es utilizable y
            # no contiene datos de nadie.
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except SupresionEnCurso:
            # ⚠️ **La carrera entre la puerta y la escritura.** Entre que la
            # puerta miró y el repositorio escribe cabe la apertura de un
            # trámite; el adaptador lo detecta con la fila bloqueada y levanta.
            #
            # Va **antes** que `EscrituraRechazada`, de la que hereda: al revés
            # este `except` no se alcanzaría nunca y la carrera saldría como un
            # conflicto anónimo o un 500, en vez del contrato uniforme.
            return respuesta_de_supresion()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo guardar el perfil")

        estado, acceso, fallo = _estado(datos["identificador_estable"])
        if fallo is not None:
            return fallo
        return JSONResponse(estado_como_json(estado, acceso))

    @router.get("/api/consentimiento/versiones")
    def versiones_requeridas(peticion: Request) -> JSONResponse:
        """Qué documentos rigen ahora, uno por alcance.

        Una base nueva puede devolver tres `null`; producción puede contener
        versiones publicadas. No se siembra ninguna por código. Para la del
        representante se añade si el PDF empaquetado es descargable, con la
        misma comprobación que aplica la ruta binaria.
        """
        _datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        try:
            requeridas = {
                alcance.value: repos.versiones.version_requerida(alcance)
                for alcance in Alcance
            }
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudieron leer las versiones vigentes")
        respuesta = {
            alcance: (version_como_json(v) if v is not None else None)
            for alcance, v in requeridas.items()
        }
        if respuesta["representante"] is not None:
            respuesta["representante"]["formato_disponible"] = (
                formato_representante.disponibilidad(requeridas["representante"])
                == "disponible"
            )
        return JSONResponse(respuesta)

    @router.get("/api/consentimiento/version/{codigo}/texto")
    def texto_de_la_version(codigo: str, peticion: Request) -> JSONResponse:
        """El documento EXACTO de una versión, por código. `§8.1`/`§8.4`/`§8.11`

        Lo que esta ruta hace cierta
        --------------------------------
        `DecisionConjunta.svelte` promete que *«la huella identifica el texto
        exacto que estás leyendo»*. Sin una forma de leer el documento
        publicado, lo único que la pantalla ofrecía eran enlaces a las páginas
        públicas del sitio —genéricas y editables—, que no son el artefacto
        hasheado. Esto sirve el artefacto.

        Se pide por CÓDIGO y nunca por ruta · `§8.1`
        ------------------------------------------------
        El parámetro es el código de la versión, y con él se consulta la base.
        El servidor no recibe ninguna ruta del navegador, así que no hay
        recorrido de directorios que impedir: no se abre ningún archivo. El
        código que no exista devuelve 404 y no dice nada más — enumerar códigos
        no revela nada útil, pero tampoco hace falta ayudar a hacerlo.

        Se comprueba que lo servido sea lo hasheado · `§8.4`
        -------------------------------------------------------
        Antes de responder se recalcula el SHA-256 del cuerpo y se compara con
        `huella_contenido` de la versión. Si no coinciden **no se sirve**:
        enseñar un documento cuya huella no es la que la versión declara sería
        volver al defecto de partida, con el agravante de que ahora la pantalla
        afirmaría haberlo comprobado. Es la comprobación que convierte la frase
        de la interfaz en una propiedad verificada en cada lectura.

        No se filtra ninguna ruta del servidor · `§8.11`
        ---------------------------------------------------
        La respuesta lleva el cuerpo y sus metadatos. Ni una ruta, ni un nombre
        de archivo, ni el nombre de la base.

        Por qué exige sesión
        ------------------------
        Porque el resto del recorrido la exige y porque no hay motivo para que
        este documento sea el único punto anónimo de la superficie autenticada.
        No es un secreto —quien acepta se lo lleva—, pero servirlo sin sesión
        habría añadido una superficie pública que nadie pidió.
        """
        _datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        if repos.instantaneas is None:
            # Composición sin instantáneas. Se declara en vez de fingir un 404,
            # que haría creer que el código no existe.
            return mantenimiento("esta instalación no puede servir el documento")
        try:
            version = repos.versiones.consultar_version(codigo)
            instantanea = repos.instantaneas.instantanea_de(codigo)
        except DatoNoAdmitido:
            # `M1` · el controlador no pudo enviar el código —un `\x00`, hoy—
            # así que la consulta nunca se hizo. Un valor que la base no puede
            # ni almacenar no identifica ninguna fila: **no existe**.
            #
            # Se cae a la rama de abajo en vez de responder aquí para que el
            # cuerpo sea el mismo por construcción y no por copia. Si fueran dos
            # respuestas distintas, la diferencia permitiría separar «este
            # código no existe» de «este código no puede existir», que es un
            # oráculo que esta ruta no quiere dar.
            version = instantanea = None
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer el documento de la versión")

        if version is None or instantanea is None:
            return JSONResponse(
                {"detalle": "no hay documento publicado con ese código"},
                status_code=404,
            )
        if not instantanea.coincide_con(version.huella_contenido):
            # Fallo cerrado. Que esto ocurra significa que alguien escribió el
            # cuerpo sin pasar por la publicación —la tabla es inmutable, así
            # que haría falta una operación de esquema— o que la
            # canonicalización cambió sin republicar. Las dos exigen mirar.
            return JSONResponse(
                {
                    "detalle": (
                        "el documento almacenado no corresponde a la huella "
                        "publicada; no se muestra"
                    )
                },
                status_code=409,
            )
        return JSONResponse(
            {
                "codigo": version.codigo,
                "alcance": version.alcance.value,
                "medio": instantanea.medio,
                "huella_contenido": version.huella_contenido,
                "cuerpo": instantanea.cuerpo,
            }
        )

    def _responder_con_estado(sujeto: str, evento, alcance: Alcance) -> JSONResponse:
        """El estado nuevo y el **recibo verificable** del acto que lo produjo.

        `EQ-021` pide que el evento conserve *«versión, alcance, finalidades,
        fecha y comprobante»* y el hito R3 concreta qué tiene que poder
        identificar el recibo: *«como mínimo secuencia, momento, versión, alcance,
        decisión y huella»*. Los seis van aquí.

        `comprobante` se conserva además en la raíz por compatibilidad con lo que
        B2 ya devolvía; es el mismo valor que `recibo["huella"]`.
        """
        estado, acceso, fallo = _estado(sujeto)
        if fallo is not None:
            return fallo
        salida = estado_como_json(estado, acceso)
        salida["recibo"] = recibo_de(evento, alcance)
        salida["comprobante"] = evento.comprobante
        return JSONResponse(salida)

    def _revocar(sujeto: str, alcance: Alcance, es_asentimiento: bool) -> JSONResponse:
        """`EQ-022` · retira la concesión otorgada. Bloquea de inmediato.

        No recibe **nada** del cliente: ni versión, ni comprobante, ni decisión.
        La versión la resuelve el servidor desde la última concesión otorgada
        —`version_de_la_concesion()`— y el repositorio la vuelve a exigir dentro
        de la transacción.

        El bloqueo es inmediato porque el acceso lo calcula
        `dominio/modelo/acceso.py` sobre el estado persistido, y el evento nuevo
        ya está ahí cuando se responde: no hace falta ningún paso adicional para
        «aplicar» la revocación, y por eso no lo hay.
        """
        repositorio = repos.asentimientos if es_asentimiento else repos.eventos
        try:
            codigo = repositorio.version_de_la_concesion(sujeto)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la concesión vigente")
        if codigo is None:
            return JSONResponse(
                {
                    "detalle": "no hay ninguna concesión otorgada que revocar",
                    "estado": "sin_concesion",
                },
                status_code=409,
            )
        try:
            version = repos.versiones.consultar_version(codigo)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la versión de la concesión")
        if version is None:
            # La versión de una concesión otorgada no puede faltar —las versiones
            # son inmutables y no se borran—, así que llegar aquí es que el
            # esquema cambió por debajo. Mantenimiento, no un 409: no es culpa de
            # quien revoca ni se arregla reintentando distinto.
            return mantenimiento("la versión de esa concesión no está disponible")

        estado_nuevo = (
            EstadoAsentimiento.REVOCADO if es_asentimiento else EstadoConsentimiento.REVOCADO
        )
        comprobante = comprobante_de(
            sujeto, version.codigo, version.huella_contenido, estado_nuevo.value
        )
        try:
            evento = repositorio.registrar(sujeto, version.codigo, estado_nuevo, comprobante)
        except EscrituraRechazada as error:
            # Cubre la carrera: otra petición revocó entre la lectura y aquí.
            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo registrar la revocación")
        return _responder_con_estado(sujeto, evento, alcance)

    @router.post("/api/consentimiento/titular")
    def decidir_consentimiento() -> JSONResponse:
        """⚠️ **Retirada por `D1B`.** Registraba sólo el acto del titular.

        Para un adulto bastaba; para un menor dejaba la mitad de su decisión
        escrita y la otra mitad en manos de una segunda petición que podía no
        llegar. `D0` §10.10 pide una acción y actos atómicos, así que ésta ya no
        escribe: responde `410` y nombra la ruta vigente.

        **No comprueba la sesión antes de responder.** Hacerlo sugeriría que con
        la cookie correcta pasaría otra cosa, y no pasa: está retirada para
        cualquiera. Es el mismo criterio del `410` de `rutas/sesion.py`.
        """
        return _ruta_retirada(Alcance.TITULAR.value)

    @router.post("/api/consentimiento/titular/revocar")
    def revocar_consentimiento(peticion: Request) -> JSONResponse:
        """`EQ-022` · revocar el consentimiento del titular.

        Ruta propia y no una decisión más en la de aceptar, porque son dos
        operaciones con reglas de versión distintas —la requerida al aceptar, la
        de la concesión otorgada al revocar— y compartir handler las habría hecho
        compartir validación.

        *«Revocar bloquea inmediatamente el tutor y todo tratamiento opcional
        futuro, sin eliminar automáticamente el historial.»* Aquí no se borra
        nada: sólo se registra el acto nuevo.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        return _revocar(datos["identificador_estable"], Alcance.TITULAR, es_asentimiento=False)

    @router.post("/api/consentimiento/asentimiento")
    def decidir_asentimiento() -> JSONResponse:
        """⚠️ **Retirada por `D1B`.** Registraba sólo el asentimiento del menor.

        La dimensión sigue siendo independiente —`EQ-016` no cambia— y su
        revocación sigue teniendo ruta propia. Lo que desaparece es poder
        **decidirla suelta**: el asentimiento y el consentimiento del titular se
        registran juntos o no se registra ninguno.
        """
        return _ruta_retirada(Alcance.ASENTIMIENTO.value)

    @router.post("/api/consentimiento/asentimiento/revocar")
    def revocar_asentimiento(peticion: Request) -> JSONResponse:
        """`EQ-016` · el menor retira su propio asentimiento.

        Dimensión independiente y ruta independiente: `EQ-016` declara las tres
        dimensiones separadas, y un menor puede querer retirar su asentimiento sin
        tocar el consentimiento del titular. Bloquea de inmediato mientras siga
        siendo menor; al cumplir 18 esa dimensión deja de aplicarse y la fila se
        conserva como historia (ver `HistorialDeAsentimiento.estado`).
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        return _revocar(
            datos["identificador_estable"], Alcance.ASENTIMIENTO, es_asentimiento=True
        )

    def _quien_puede_cargar(peticion: Request) -> tuple[str, JSONResponse | None]:
        """Las tres comprobaciones que van ANTES de leer el cuerpo binario.

        Sesión, trámite de supresión y minoría de edad, en ese orden. Devuelve
        `(sujeto, None)` o `("", respuesta)`.

        Se extrae de `cargar_evidencia()` porque aquella función ya tenía siete
        pasos y la puerta de `EQ-022` añadía el octavo: separarlas deja a la vista
        que **las tres se resuelven sin haber recibido un solo byte**, que es la
        propiedad que importa. Un PDF de diez megas transferido, validado y
        reservado para acabar rechazado deja una reserva que compensar; lo que no
        se recibe, no.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return "", negativa
        sujeto = datos["identificador_estable"]

        estado, _acceso, fallo = _estado(sujeto)
        if fallo is not None:
            return "", fallo
        if estado.eliminacion_solicitada:
            return "", respuesta_de_supresion(
                "tienes una solicitud de eliminación en curso: mientras dure no "
                "se acepta ninguna autorización nueva"
            )
        if not estado.es_menor:
            return "", JSONResponse(
                {"detalle": "la autorización del representante sólo aplica a un menor de edad"},
                status_code=409,
            )
        return sujeto, None

    @router.get("/api/representante/formato")
    def descargar_formato(peticion: Request) -> Response:
        """Plantilla aprobada, en PDF y fechada en el instante de descarga.

        El mismo borde que admite la evidencia controla la descarga: exige
        sesión, ausencia de supresión en curso y minoría de edad. Además exige
        una versión de representante vigente, porque entregar un formulario sin
        versión contra la cual registrar luego el PDF crearía evidencia huérfana.

        La fecha es la civil de Colombia y se genera en el servidor; cambiar el
        reloj o la zona del navegador no altera el documento descargado.
        """
        _sujeto, negativa = _quien_puede_cargar(peticion)
        if negativa is not None:
            return negativa

        try:
            version = repos.versiones.version_requerida(Alcance.REPRESENTANTE)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la versión vigente")
        disponibilidad = formato_representante.disponibilidad(version)
        if disponibilidad == "sin_version":
            return JSONResponse(
                {
                    "detalle": "no hay ninguna versión vigente del documento del representante",
                    "estado": "sin_version",
                },
                status_code=409,
            )
        if disponibilidad == "version_no_corresponde":
            return JSONResponse(
                {
                    "detalle": (
                        "la versión vigente del representante no corresponde al "
                        "formato aprobado disponible para descarga"
                    ),
                    "estado": "formato_no_corresponde",
                },
                status_code=409,
            )

        if disponibilidad == "plantilla_no_disponible":
            return mantenimiento("el formato de autorización no está disponible")

        fecha = formato_representante.fecha_del_piloto()
        try:
            contenido = formato_representante.generar_pdf(fecha)
        except formato_representante.FormatoNoDisponible:
            return mantenimiento("el formato de autorización no está disponible")

        nombre = f"autorizacion-representante-menor-{fecha.isoformat()}.pdf"
        return Response(
            content=contenido,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{nombre}"',
                "Cache-Control": "no-store, private",
                "X-Content-Type-Options": "nosniff",
                "X-DidaxIA-Version-Representante": version.codigo,
                "X-DidaxIA-Fecha-Descarga": fecha.isoformat(),
            },
        )

    def _rechazar_archivo(contenido: bytes, declarado: str) -> JSONResponse | None:
        """`EQ-021` · tipo, tamaño y **estructura**, antes de tocar nada.

        Se valida el contenido y no sólo la cabecera: el `Content-Type` lo pone
        quien sube.

        ✅ **La validación estructural ya no es deuda** (hito R4). Aquí decía que
        una validación completa «exigiría una dependencia nueva y es una decisión
        que este hito no tiene». La dependencia es `pypdf`, está declarada en
        `requirements.txt`, y lo que la comprobación de cinco bytes dejaba pasar
        —un PDF truncado, uno cifrado, uno sin páginas— no es evidencia de nada.
        Ver `adaptadores/entrantes/http/pdf.py`.

        El orden va de lo barato a lo caro: cabecera declarada, tamaño, y sólo
        entonces abrir el archivo. Y todo **antes** de reservar nada, para no
        tener que compensar una carga por algo que se veía al llegar.
        """
        if declarado != TIPO_MIME_ESPERADO:
            return JSONResponse(
                {"detalle": f"la evidencia se recibe como {TIPO_MIME_ESPERADO}"},
                status_code=415,
            )
        if not contenido:
            return JSONResponse({"detalle": "el archivo llegó vacío"}, status_code=400)
        if len(contenido) > TAMANO_MAXIMO_BYTES:
            return JSONResponse(
                {"detalle": f"el archivo excede {TAMANO_MAXIMO_BYTES} bytes"},
                status_code=413,
            )
        try:
            pdf.exigir_pdf_utilizable(contenido)
        except pdf.PdfInutilizable as error:
            # El motivo lo redacta `pdf.py` y no interpola nada del contenido.
            return JSONResponse({"detalle": str(error)}, status_code=415)
        return None

    @router.post("/api/representante/evidencia")
    async def cargar_evidencia(peticion: Request) -> JSONResponse:
        """La autorización firmada del representante (`EQ-021`).

        El archivo llega como cuerpo binario y **no se guarda en PostgreSQL**: va
        al almacenamiento privado por su puerto, y la base recibe la referencia
        opaca, el SHA-256, el tipo y el tamaño.

        El orden de las comprobaciones es el contrato:

        1. **sesión** — nadie sube nada sin identidad;
        2. **trámite de supresión** — `EQ-022`: durante él no se aporta nada;
        3. **menor** — la dimensión no le corresponde a un adulto;
        4. **tipo y tamaño** — `EQ-021`: PDF y 10 MB, antes de tocar nada;
        5. **versión requerida** — una carga sobre un documento desplazado no
           autoriza el que hoy se pide (hito A2);
        6. **almacenamiento** — si no hay dónde guardar, no se acepta;
        7. **fila** — sólo entonces, y con la referencia ya real.

        Guardar la fila antes que el archivo dejaría una evidencia que apunta a
        nada. Al revés deja, en el peor caso, un archivo huérfano en la carpeta:
        recuperable, y por eso va en ese orden.

        ⚠️ **El paso 2 va donde va, y no al final** · corrección transversal. El
        cuerpo binario se lee en el paso 4: comprobar el trámite después habría
        significado transferir diez megas, validarlos con `pypdf` y reservarlos
        en almacenamiento privado para acabar rechazándolos —y esa reserva hay
        que compensarla, con todo lo que puede fallar en la compensación—. Lo que
        no se recibe no hay que compensarlo.

        La misma comprobación la repite `registrar_intento()` dentro de su
        transacción, con la fila bloqueada: ésta ahorra el trabajo, aquélla cierra
        la carrera con un trámite que se abre a mitad.
        """
        sujeto, negativa = _quien_puede_cargar(peticion)
        if negativa is not None:
            return negativa

        contenido = await peticion.body()
        declarado = peticion.headers.get("content-type", "").split(";")[0].strip().lower()
        rechazo = _rechazar_archivo(contenido, declarado)
        if rechazo is not None:
            return rechazo

        try:
            version = repos.versiones.version_requerida(Alcance.REPRESENTANTE)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo leer la versión vigente")
        if version is None:
            return JSONResponse(
                {
                    "detalle": "no hay ninguna versión vigente del documento del representante",
                    "estado": "sin_version",
                },
                status_code=409,
            )

        # ── fase 1 · reserva provisional ────────────────────────────────
        try:
            referencia = repos.almacenamiento.reservar(
                contenido,
                sujeto_google=sujeto,
                intento=len(_intentos_o_vacio(repos, sujeto)) + 1,
            )
        except (AlmacenamientoNoConfigurado, AlmacenamientoNoDisponible):
            return mantenimiento("el almacenamiento privado no está disponible")

        # ── fase 2 · la fila, y la compensación si no entra ─────────────
        try:
            intento = repos.evidencias.registrar_intento(
                sujeto,
                version.codigo,
                referencia,
                hashlib.sha256(contenido).hexdigest(),
                len(contenido),
            )
        except EvidenciaInvalida as error:
            return _compensar(repos, referencia, {"detalle": str(error)}, 400)
        except SupresionEnCurso as error:
            # ⚠️ **La carrera, y la reserva se compensa igual.** La puerta miró
            # antes de leer el cuerpo; entre eso y esta escritura cabe la
            # apertura de un trámite, que el adaptador detecta con la fila
            # bloqueada. Para entonces el PDF **ya está reservado**, así que hay
            # que retirarlo: la denegación no puede dejar un archivo firmado por
            # un representante legal del que ninguna base tenga noticia.
            #
            # Va antes que `EscrituraRechazada`, de la que hereda: al revés este
            # `except` no se alcanzaría y la carrera saldría como un conflicto
            # anónimo, sin el `estado` que el cliente necesita para distinguirla.
            return _compensar(
                repos,
                referencia,
                {
                    "detalle": str(error),
                    "estado": ESTADO_SUPRESION,
                    "usar": RUTA_DEL_TRAMITE,
                },
                409,
            )
        except EscrituraRechazada as error:
            return _compensar(repos, referencia, {"detalle": str(error)}, 409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return _compensar(
                repos,
                referencia,
                {"detalle": "no se pudo registrar la evidencia", "estado": "mantenimiento"},
                503,
            )

        # ── fase 3 · promoción a evidencia definitiva ───────────────────
        try:
            repos.almacenamiento.confirmar(referencia)
        except (AlmacenamientoNoConfigurado, AlmacenamientoNoDisponible):
            # La fila está y el archivo también, pero sigue siendo provisional.
            # No se informa éxito: `EQ-024` prohíbe el éxito parcial, y la reserva
            # queda pendiente y enumerable para que alguien la complete.
            return JSONResponse(
                {
                    "detalle": (
                        "la evidencia quedó como reserva pendiente: se registró la "
                        "carga pero no se pudo completar su custodia"
                    ),
                    "estado": "mantenimiento",
                    "reserva_pendiente": True,
                },
                status_code=503,
                headers={"Retry-After": "30"},
            )

        estado, acceso, fallo = _estado(sujeto)
        if fallo is not None:
            return fallo
        salida = estado_como_json(estado, acceso)
        salida["intento"] = intento.intento
        salida["sha256"] = intento.sha256
        return JSONResponse(salida)

    @router.post("/api/representante/evidencia/{evidencia}/revisar")
    async def revisar_evidencia(evidencia: int, peticion: Request) -> JSONResponse:
        """`EQ-023` · sólo un investigador con rol vigente resuelve una evidencia.

        El permiso lo comprueba el repositorio contra `rol_asignacion` dentro de
        la misma transacción, no esta ruta contra una lista: un rol retirado un
        segundo antes no puede colarse por una comprobación hecha aquí arriba.

        ⚠️ **Y el trámite del propio revisor la suspende** · corrección
        transversal. Revisar es una acción de producto, y `ESTADO-ACTUAL.md`
        §10.2 la suspende mientras la cuenta que la ejecuta tenga su supresión
        abierta. Quien se comprueba es el ACTOR: sobre el titular de la evidencia
        no se decide nada aquí, y su trámite —si lo tuviera— ya le impide aportar
        una nueva.
        """
        datos, negativa = requerir_sesion(sesiones, peticion)
        if negativa is not None:
            return negativa
        congelada = puerta.negativa(datos["identificador_estable"])
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        resultado = {
            "aprobada": ResultadoDeRevision.APROBADA,
            "rechazada": ResultadoDeRevision.RECHAZADA,
        }.get(str(cuerpo.get("resultado") or ""))
        if resultado is None:
            return JSONResponse({"detalle": "resultado no admitido"}, status_code=400)

        try:
            revision = repos.evidencias.revisar(
                evidencia,
                datos["identificador_estable"],
                resultado,
                str(cuerpo.get("motivo") or ""),
            )
        except EvidenciaInvalida as error:
            return JSONResponse({"detalle": str(error)}, status_code=400)
        except EscrituraRechazada as error:
            # Cubre «no tiene el rol», «esa evidencia no existe» y «ese intento ya
            # se resolvió». Los tres son 409: la petición está bien formada, el
            # sistema se niega, y ninguno se arregla reintentando.
            return JSONResponse({"detalle": str(error)}, status_code=409)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo registrar la revisión")

        return JSONResponse(
            {
                "resultado": revision.resultado.value,
                "revisada_en": revision.revisada_en.isoformat(),
                "motivo": revision.motivo,
            }
        )

    return router


def _intentos_o_vacio(repos: Repositorios, sujeto: str) -> tuple:
    """Los intentos previos, o vacío si el almacén no responde.

    Sólo sirve para numerar el archivo en el almacenamiento privado; el número
    real lo asigna la base dentro de la transacción. Si aquí se equivocara, la
    referencia llevaría un número distinto del intento —feo, no incorrecto— y la
    escritura fallaría después con su propio motivo.
    """
    try:
        return repos.evidencias.intentos(sujeto)
    except (AlmacenNoConfigurado, AlmacenNoDisponible):
        return ()


def _compensar(
    repos: Repositorios, referencia: str, cuerpo: dict, codigo: int
) -> JSONResponse:
    """Retira la carga provisional cuando la fila no entró, y responde.

    Es el protocolo de compensación del hito R4. Antes, la ruta guardaba el
    archivo, fallaba al escribir la fila y respondía el error **dejando el PDF en
    almacenamiento privado sin que ninguna base supiera de él**. El comentario
    llamaba a eso «recuperable», pero recuperable exige que alguien sepa que está.

    Dos desenlaces, y los dos son honestos:

    - **se retiró** · no queda nada. La respuesta es el error que corresponda.
    - **no se pudo retirar** · la reserva sigue **pendiente y enumerable**
      (`pendientes()`), que es la reserva durable que el encargo exige antes de
      admitir un 503. Se dice en la respuesta —`reserva_pendiente`— para que no
      sea sólo un error genérico.

    El fallo al retirar no se propaga como excepción: ya estamos respondiendo a un
    fallo, y sustituirlo por otro perdería el motivo original, que es el que la
    persona necesita.
    """
    salida = dict(cuerpo)
    try:
        repos.almacenamiento.retirar(referencia)
    except (AlmacenamientoNoConfigurado, AlmacenamientoNoDisponible):
        salida["reserva_pendiente"] = True
    cabeceras = {"Retry-After": "30"} if codigo == 503 else None
    return JSONResponse(salida, status_code=codigo, headers=cabeceras)
