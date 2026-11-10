"""
clases.py — Las trece rutas del espacio de clase · `DD-12` / `EQ-033`
====================================================================

Crear, solicitar matrícula, listar y resolver solicitudes, listar las clases
propias, ver integrantes, abrir la ficha de uno, recuperar su foto privada y
regenerar el código. La frontera de `DD-12` sigue intacta: **sin tareas,
calificaciones, entregas, calendario ni mensajería**. `EQ-033` añade la
condición de una única clase activa por estudiante y aprobación humana antes
de toda alta o cambio.

La ficha (Fase 7) no cruza la frontera de `DD-12`: no añade progreso,
calificación ni entrega. Devuelve lo que la lista de matriculados ya muestra,
por una ruta que además dice desde qué clase se mira.

⚠️ No confundir con el almacén. Desde la Fase 2 · sesión 3, el contrato es
`dominio/puertos/clases.py::PuertoClases` y las dos implementaciones viven en
`adaptadores/salientes/registro/` —`clases_memoria.py` y `clases_db.py`—. Estas
rutas dependen del puerto y no saben cuál recibieron. Ver `rutas/__init__.py`.

Quién puede qué, y por qué no es simétrico
-------------------------------------------------
Crear una clase, listar integrantes, recuperar sus fotos privadas y regenerar
el código exigen rol docente (`RP-17`) **y** propiedad de la clase. Solicitar
matrícula exige rol estudiante; aprobar o rechazar corresponde al docente
propietario de la clase de destino o al investigador, y cancelar sólo al
estudiante titular. Listar las clases propias no exige rol profesional. La
propiedad se protege además en el ALMACÉN para cualquier borde que lo llame;
la ruta conserva la comprobación del rol vigente porque ser creador histórico
no mantiene permisos docentes después de que el rol se retire (`EQ-023`).


"""

from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import json_del_cuerpo, mantenimiento, requerir_rol
from adaptadores.entrantes.http.rutas.puerta_de_supresion import respuesta_de_supresion
from adaptadores.entrantes.http.sesiones import COOKIE, Sesiones, sujeto_de
from adaptadores.salientes.almacenamiento.fotos_perfil import AlmacenFotosPerfil
from adaptadores.salientes.notificacion.plantillas import solicitud_de_matricula
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible, EscrituraRechazada
from dominio.puertos.clases import ConflictoDeMatricula
from dominio.puertos.gobierno import SupresionEnCurso
from dominio.puertos.preferencias_notificacion import SOLICITUDES_MATRICULA

if TYPE_CHECKING:  # pragma: no cover
    from adaptadores.entrantes.http.rutas.puerta_de_supresion import PuertaDeSupresion
    from dominio.puertos.clases import PuertoClases
    from dominio.puertos.gobierno import PuertoNotificacion
    from dominio.puertos.preferencias_notificacion import PuertoPreferenciasDeNotificacion


_ASUNTO_SOLICITUD = "Nueva solicitud para tu clase en DidaxIa"
_URL_CLASES = "https://app.didaxia.pro/mis-clases"
_URL_SOLICITUDES = "https://app.didaxia.pro/solicitudes-matricula"


def _mensaje_de_solicitud(solicitud) -> str:
    estudiante = solicitud.nombre_estudiante.strip() or "Un estudiante"
    docente = solicitud.nombre_docente.strip()
    saludo = f"Hola, {docente}." if docente else "Hola."
    return (
        f"{saludo}\n\n{estudiante} solicitó ingresar a "
        f"«{solicitud.nombre_destino}».\n\n"
        "Revisa la solicitud desde tu panel de clases en DidaxIa. Allí podrás "
        "confirmar la identidad y ver su foto de perfil, cuando esté disponible, "
        "antes de aprobar o rechazar el ingreso.\n\n"
        "Este mensaje es informativo: la matrícula no cambia hasta que una persona autorizada la apruebe."
    )


def _destinos_de_investigacion(configuracion: str) -> tuple[str, ...]:
    """Buzones separados por coma o punto y coma, limpios y sin duplicados."""
    unicos: dict[str, str] = {}
    for fragmento in configuracion.replace(";", ",").split(","):
        correo = fragmento.strip()
        if correo and "@" in correo:
            unicos.setdefault(correo.casefold(), correo)
    return tuple(unicos.values())


def crear_router(  # noqa: PLR0913 -- dependencias explícitas de esta frontera HTTP
    sesiones: Sesiones,
    clases_almacen: PuertoClases,
    puerta: PuertaDeSupresion,
    fotos: AlmacenFotosPerfil | None = None,
    notificacion: PuertoNotificacion | None = None,
    preferencias_notificacion: PuertoPreferenciasDeNotificacion | None = None,
    *,
    correo_investigacion: str = "",
) -> APIRouter:
    """Las trece rutas de `DD-12`/`EQ-033`, todas tras la puerta de `EQ-022`.

    ⚠️ **`puerta` es obligatoria**, sin valor por defecto. La tenía —`| None =
    None`— para no romper composiciones de prueba antiguas, y eso convertía
    olvidarla en una forma silenciosa de desactivar la regla: un router
    construido sin ella pasaba todas las pruebas y dejaba el producto abierto.
    Ahora omitirla es un `TypeError` al componer, que es donde tiene que doler.

    Todas, y no sólo las que escriben: `ESTADO-ACTUAL.md` §10.2 suspende el
    **uso del producto**, y la lista de mis clases o los integrantes de una no
    son un derecho del titular sobre sus propios datos — son producto. Lo que sí
    es derecho propio vive en `/api/datos-personales` y en `/api/datos/supresion`.
    """
    router = APIRouter()

    def _congelada(datos) -> Response | None:
        """La negativa si esta cuenta tiene el trámite abierto, o `None`."""
        return puerta.negativa(sujeto_de(datos))

    def _correo_habilitado(*, sujeto: str = "", correo: str = "") -> bool:
        """Falla cerrado: sin preferencia afirmativa no sale ningún correo."""
        if preferencias_notificacion is None:
            return False
        try:
            if sujeto:
                return preferencias_notificacion.habilitada(
                    sujeto, SOLICITUDES_MATRICULA
                )
            if correo:
                return preferencias_notificacion.habilitada_para_correo(
                    correo, SOLICITUDES_MATRICULA
                )
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return False
        return False

    @router.get("/api/clases")
    def listar_clases(peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        # `EQ-022` · listar las clases propias es usar el producto, no un derecho
        # del titular sobre sus datos: eso se ejerce en `/api/datos-personales`.
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        return JSONResponse([c.como_resumen() for c in clases_almacen.mias(sujeto_de(datos))])

    @router.post("/api/clases")
    async def crear_clase(peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        # `EQ-022` · **antes de leer el cuerpo**. Se comprueba después de la
        # sesión y el rol —el trámite no exime de autenticarse— y antes de
        # consumir nada de lo que llegue: un cuerpo que no se lee no hay que
        # validarlo ni descartarlo.
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        nombre = str(cuerpo.get("nombre") or "").strip()
        if not nombre:
            return JSONResponse({"detalle": "falta el nombre de la clase"}, status_code=400)
        try:
            clase = clases_almacen.crear(nombre, sujeto_de(datos))
        except SupresionEnCurso:
            # La carrera: el trámite se abrió entre la puerta y la escritura, y
            # el adaptador lo detectó con la fila bloqueada. Mismo contrato.
            return respuesta_de_supresion()
        return JSONResponse(clase.como_resumen(), status_code=201)

    @router.post("/api/clases/unirse")
    async def unirse_a_clase(peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        error = requerir_rol(sesiones, peticion, "estudiante")
        if error is not None:
            return error
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        codigo = str(cuerpo.get("codigo") or "").strip()
        try:
            solicitud = clases_almacen.unirse(codigo, sujeto_de(datos)) if codigo else None
        except SupresionEnCurso:
            return respuesta_de_supresion()
        except ConflictoDeMatricula as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=409)
        if solicitud is None:
            return JSONResponse({"detalle": "código no reconocido"}, status_code=404)
        aviso_enviado = False
        if (
            notificacion is not None
            and solicitud.correo_docente
            and _correo_habilitado(
                sujeto=solicitud.docente,
                correo=solicitud.correo_docente,
            )
        ):
            aviso_enviado = notificacion.avisar(
                solicitud.correo_docente,
                _ASUNTO_SOLICITUD,
                _mensaje_de_solicitud(solicitud),
                clave_idempotencia=f"solicitud-matricula/{solicitud.identificador}",
                html=solicitud_de_matricula(
                    destinatario=solicitud.nombre_docente,
                    estudiante=solicitud.nombre_estudiante,
                    clase=solicitud.nombre_destino,
                    url_accion=_URL_CLASES,
                ),
            )
        avisos_investigacion = []
        destinos_investigacion = (
            _destinos_de_investigacion(correo_investigacion)
            if notificacion is not None
            else ()
        )
        for destino in destinos_investigacion:
            if destino.casefold() == solicitud.correo_docente.casefold():
                continue
            if not _correo_habilitado(correo=destino):
                continue
            huella_destino = sha256(destino.casefold().encode("utf-8")).hexdigest()[:12]
            avisos_investigacion.append(notificacion.avisar(
                destino,
                "Nueva solicitud institucional de matrícula en DidaxIa",
                _mensaje_de_solicitud(solicitud),
                clave_idempotencia=(
                    f"solicitud-matricula/{solicitud.identificador}/"
                    f"investigacion/{huella_destino}"
                ),
                html=solicitud_de_matricula(
                    destinatario="Equipo de investigación",
                    estudiante=solicitud.nombre_estudiante,
                    clase=solicitud.nombre_destino,
                    url_accion=_URL_SOLICITUDES,
                ),
            ))
        salida = solicitud.como_elemento()
        salida["aviso_docente_enviado"] = aviso_enviado
        salida["aviso_investigacion_enviado"] = bool(avisos_investigacion) and all(
            avisos_investigacion
        )
        salida["avisos_investigacion_enviados"] = sum(avisos_investigacion)
        return JSONResponse(salida, status_code=202)

    @router.get("/api/clases/solicitudes")
    def solicitudes_de_matricula(peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        if datos.get("rol") not in {"estudiante", "docente", "investigador"}:
            return JSONResponse({"detalle": "rol sin acceso a solicitudes"}, status_code=403)
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        try:
            solicitudes = clases_almacen.solicitudes(sujeto_de(datos), datos["rol"])
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento()
        return JSONResponse([s.como_elemento() for s in solicitudes])

    def _resolver_matricula(identificador: str, peticion: Request, decision: str) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        roles = {"estudiante"} if decision == "cancelada" else {"docente", "investigador"}
        if datos["rol"] not in roles:
            return JSONResponse({"detalle": "sin permiso para esta decisión"}, status_code=403)
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        try:
            solicitud = clases_almacen.resolver_solicitud(
                identificador, sujeto_de(datos), datos["rol"], decision,
            )
        except SupresionEnCurso:
            return respuesta_de_supresion()
        except ConflictoDeMatricula as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=409)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento()
        if solicitud is None:
            return JSONResponse({"detalle": "solicitud no encontrada o sin permiso"}, status_code=404)
        return JSONResponse(solicitud.como_elemento())

    @router.post("/api/clases/solicitudes/{identificador}/aprobar")
    def aprobar_matricula(identificador: str, peticion: Request) -> Response:
        return _resolver_matricula(identificador, peticion, "aprobada")

    @router.post("/api/clases/solicitudes/{identificador}/rechazar")
    def rechazar_matricula(identificador: str, peticion: Request) -> Response:
        return _resolver_matricula(identificador, peticion, "rechazada")

    @router.post("/api/clases/solicitudes/{identificador}/cancelar")
    def cancelar_matricula(identificador: str, peticion: Request) -> Response:
        return _resolver_matricula(identificador, peticion, "cancelada")

    @router.get("/api/clases/{identificador}/integrantes")
    def integrantes_de_clase(identificador: str, peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        integrantes = clases_almacen.integrantes(identificador, sujeto_de(datos))
        if integrantes is None:
            return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
        return JSONResponse([m.como_fila() for m in integrantes])

    @router.delete("/api/clases/{identificador}/integrantes/{sujeto}")
    async def retirar_integrante_de_clase(
        identificador: str, sujeto: str, peticion: Request
    ) -> Response:
        """Cierra una matrícula por decisión del docente propietario.

        La cuenta y su historia permanecen intactas. La confirmación visual se
        hace en el cliente, pero el servidor exige además un motivo explícito y
        vuelve a comprobar rol, propiedad y trámites de supresión.
        """
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if (congelada := _congelada(datos)) is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        motivo = str(cuerpo.get("motivo") or "").strip()
        if not 5 <= len(motivo) <= 240:
            return JSONResponse(
                {"detalle": "explica el retiro en entre 5 y 240 caracteres"},
                status_code=400,
            )
        try:
            retirada = clases_almacen.retirar_integrante(
                identificador, sujeto_de(datos), sujeto, motivo
            )
        except SupresionEnCurso:
            return respuesta_de_supresion()
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento("no se pudo retirar la matrícula")
        if retirada is None:
            return JSONResponse(
                {"detalle": "no encontrada, no es tuya o la persona ya no está matriculada"},
                status_code=404,
            )
        return JSONResponse({
            "clase": identificador,
            "retirado": retirada.como_fila(),
            "resultado": "matrícula cerrada; la cuenta y su historia se conservaron",
        })

    @router.get("/api/clases/{identificador}/integrantes/{sujeto}")
    def ficha_de_integrante(identificador: str, sujeto: str, peticion: Request) -> Response:
        """La ficha de UN matriculado, para el docente que creó su clase · Fase 7.

        POR QUÉ CUELGA DE LA CLASE Y NO ES `/api/estudiantes/{id}`
        -----------------------------------------------------------
        `panel_docente.py` propuso en su día una ruta por estudiante, y con ella
        la autorización habría tenido que reconstruirse: «¿existe alguna clase
        de este docente donde esta persona esté matriculada?». Colgándola de la
        clase, la pregunta ya está contestada por `integrantes()` —que devuelve
        `None` si la clase no existe **o no es suya**— y no hay una segunda
        comprobación de permisos que pueda discrepar de la primera.

        Además obliga a que la ficha diga siempre DESDE QUÉ CLASE se mira, que
        es lo que un docente con dos grupos necesita para no confundirlas.

        `404` PARA LOS TRES CASOS, Y ESA INDISTINCIÓN ES LA GARANTÍA
        -------------------------------------------------------------
        Clase que no existe, clase ajena y persona no matriculada responden lo
        mismo. Distinguirlas permitiría recorrer identificadores para averiguar
        qué clases existen y quién está en ellas — el mismo criterio que
        `GET /api/historial/{sesion}` ya aplica y que `integrantes()` respeta
        más arriba en este archivo.

        QUÉ DEVUELVE, Y QUÉ NO
        ------------------------
        Lo que la lista de matriculados ya muestra —nombre visible, fecha de
        matrícula y si tiene foto—, más el nombre de la clase. **Nada más.**

        Esta ruta base no lleva vector conductual, diagnóstico, indicadores ni
        conversaciones. `EQ-032` ya aprobó que 7E.3 los exponga mediante
        contratos trazables y autorizados; esos contratos todavía no se
        mezclan aquí antes de existir. No es una prohibición pendiente sino una
        separación entre la ficha de matrícula ya disponible y la analítica que
        sigue en construcción.

        La foto no viaja aquí: se pide a `…/foto`, que ya la sirve con
        `Cache-Control: private, no-store` y sin URL pública permanente.
        """
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        # `RP-17` · la ficha de un estudiante es del docente que creó su clase.
        # Se comprueba el rol ADEMÁS de la propiedad de la clase: un
        # investigador alcanzará las fichas institucionales mediante el borde
        # auditado de 7E.4; el modo Tutor de `EQ-031` no sustituye ese borde.
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        integrantes = clases_almacen.integrantes(identificador, sujeto_de(datos))
        if integrantes is None:
            return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
        matricula = next((m for m in integrantes if m.identificador == sujeto), None)
        if matricula is None:
            return JSONResponse(
                {"detalle": "esa persona no está matriculada en esta clase"},
                status_code=404,
            )
        clase = next(
            (c for c in clases_almacen.mias(sujeto_de(datos)) if c.identificador == identificador),
            None,
        )
        return JSONResponse(
            {
                "clase": {
                    "id": identificador,
                    "nombre": clase.nombre if clase is not None else "",
                },
                "estudiante": matricula.como_fila(),
            }
        )

    @router.get("/api/clases/{identificador}/integrantes/{sujeto}/foto")
    def foto_de_integrante(identificador: str, sujeto: str, peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        if datos.get("rol") not in {"docente", "investigador"}:
            return JSONResponse({"detalle": "rol sin acceso a esta foto"}, status_code=403)
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        if datos["rol"] == "investigador":
            try:
                matricula = clases_almacen.integrante_para_investigacion(
                    identificador, sujeto_de(datos), sujeto
                )
            except EscrituraRechazada:
                return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
            except (AlmacenNoConfigurado, AlmacenNoDisponible):
                return mantenimiento("la foto institucional no está disponible")
        else:
            integrantes = clases_almacen.integrantes(identificador, sujeto_de(datos))
            if integrantes is None:
                return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
            matricula = next((m for m in integrantes if m.identificador == sujeto), None)
        if matricula is None or not matricula.foto_referencia:
            return JSONResponse({"detalle": "este integrante no tiene foto"}, status_code=404)
        if fotos is None or not fotos.configurado:
            return JSONResponse({"detalle": "las fotos no están disponibles"}, status_code=503)
        try:
            cuerpo = fotos.recuperar(matricula.foto_referencia)
        except (OSError, ValueError):
            cuerpo = None
        if cuerpo is None:
            return JSONResponse({"detalle": "la foto no está disponible"}, status_code=503)
        return Response(
            content=cuerpo,
            media_type="image/webp",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    @router.post("/api/clases/{identificador}/codigo")
    def regenerar_codigo_de_clase(identificador: str, peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        try:
            nuevo = clases_almacen.regenerar_codigo(identificador, sujeto_de(datos))
        except SupresionEnCurso:
            return respuesta_de_supresion()
        if nuevo is None:
            return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
        return JSONResponse({"codigo": nuevo})

    @router.patch("/api/clases/{identificador}")
    async def renombrar_clase(identificador: str, peticion: Request) -> Response:
        error = requerir_rol(sesiones, peticion, "docente")
        if error is not None:
            return error
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        nombre = str(cuerpo.get("nombre") or "").strip()
        if not nombre:
            return JSONResponse({"detalle": "falta el nombre de la clase"}, status_code=400)
        if len(nombre) > 120:
            return JSONResponse(
                {"detalle": "el nombre de la clase no puede superar 120 caracteres"},
                status_code=400,
            )
        try:
            clase = clases_almacen.renombrar(identificador, sujeto_de(datos), nombre)
        except SupresionEnCurso:
            return respuesta_de_supresion()
        if clase is None:
            return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
        return JSONResponse(clase.como_resumen())

    @router.delete("/api/clases/{identificador}")
    async def archivar_clase(identificador: str, peticion: Request) -> Response:
        datos = sesiones.leer(peticion.cookies.get(COOKIE))
        if datos is None:
            return JSONResponse({"detalle": "sin sesión"}, status_code=401)
        if datos.get("rol") not in {"docente", "investigador"}:
            return JSONResponse({"detalle": "sin permiso para eliminar clases"}, status_code=403)
        congelada = _congelada(datos)
        if congelada is not None:
            return congelada
        cuerpo = await json_del_cuerpo(peticion)
        motivo = str(cuerpo.get("motivo") or "").strip()
        if len(motivo) < 5 or len(motivo) > 240:
            return JSONResponse(
                {"detalle": "explica el motivo en 5 a 240 caracteres"}, status_code=400,
            )
        try:
            archivada = clases_almacen.archivar(identificador, sujeto_de(datos), motivo, datos["rol"])
        except SupresionEnCurso:
            return respuesta_de_supresion()
        except ConflictoDeMatricula as exc:
            return JSONResponse({"detalle": str(exc)}, status_code=409)
        except EscrituraRechazada:
            return JSONResponse({"detalle": "sin permiso vigente"}, status_code=403)
        except (AlmacenNoConfigurado, AlmacenNoDisponible):
            return mantenimiento()
        if not archivada:
            return JSONResponse({"detalle": "no encontrada, o no es tuya"}, status_code=404)
        return JSONResponse({"estado": "archivada", "clase": identificador})

    return router
