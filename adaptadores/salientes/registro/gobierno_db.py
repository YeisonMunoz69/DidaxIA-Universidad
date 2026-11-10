"""
gobierno_db.py — Supresión solicitada, retención y auditoría (migración 12)
============================================================================

Los tres repositorios PostgreSQL del gobierno de datos reversible de `EQ-022` y
`EQ-023`, contra `solicitud_supresion`, `politica_retencion` y
`auditoria_operacion`.

⚠️ Ninguno borra nada
------------------------------
`AdaptadorSolicitudesDeSupresionPostgres` abre, cancela y consulta. **No tiene un
método que elimine**, y no es un olvido: el cierre V-B decidirá qué textos se
borran, qué se conserva seudonimizado hasta el límite de retención y qué métricas
pueden anonimizarse de forma irreversible. Dejar aquí media ejecución sería peor
que no tenerla: alguien la completaría sin esa decisión.

⚠️ La auditoría va DENTRO de la transacción · hito R5
--------------------------------------------------------------------
Hasta el cierre V-B, `rutas/gobierno.py` llamaba a `_auditar()` **después** de la
operación, en otra conexión, capturando el fallo y siguiendo. `EQ-023` dice lo
contrario, y la auditoría V-B lo devolvió como quinto invariante:

    «Una operación auditable no puede informar éxito sin auditoría. Abrir o
    cancelar una supresión, consultar conversaciones ajenas y cambiar permisos
    deben persistir operación y auditoría en una misma transacción, o no
    ocurrir.»

Ahora `abrir()` y `cancelar()` reciben el actor y escriben su constancia con el
mismo cursor, dentro de la misma transacción: si el `INSERT` de auditoría falla,
el trámite no queda abierto ni cancelado. La redacción del `INSERT` vive una sola
vez en `auditoria_sql.py`.

La notificación por correo sigue **fuera** de la transacción y sigue sin
decidirla: `EQ-024` es explícito en que el canal no es una garantía. Lo que sí
cambió es que su resultado se representa —`aviso_enviado`— en vez de fingirse.

⚠️ La doble aprobación necesita dos peticiones · hito R5
--------------------------------------------------------------------
`AdaptadorPropuestasPostgres` es la pieza que faltaba. La primera petición crea
una propuesta pendiente con su payload canónico y su huella; la segunda, de otro
administrador autenticado, la aprueba. Aprobar comprueba el rol, recomputa la
huella, **aplica el efecto** y audita, todo en una transacción. Ver su docstring.

Cancelar sí es un UPDATE, y por qué
------------------------------------------------
`solicitud_supresion` no lleva el disparador de inmutabilidad de la migración 11
porque su estado **es** su ciclo de vida: se solicita, se cancela o se resuelve.
Lo que la protege es el índice único parcial —un solo trámite abierto por
titular— y el CHECK que exige coherencia entre estado y cierre. Lo inmutable son
los actos de consentimiento, que sí llevan el disparador.

La auditoría, en cambio, es inmutable
--------------------------------------------------
`auditoria_operacion` lleva el disparador: un registro que se puede editar no
audita nada.


"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from adaptadores.salientes.informes.pdf_auditoria import (
    VERSION_PLANTILLA_AUDITORIA,
    generar_informe_auditoria,
)
from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import (
    exigir_investigador_administrador,
)
from adaptadores.salientes.registro.base_postgres import RepositorioPostgres, exigir_persona
from adaptadores.salientes.registro.roles_db import PRESENTACION_PERSONAS_SQL
from dominio.auditoria.catalogo import (
    codigos_de_categoria,
    describir_operacion,
    diferencias,
    glosario,
)
from dominio.modelo.propuestas import (
    EstadoPropuesta,
    Propuesta,
    PropuestaInvalida,
    huella_de,
)
from dominio.modelo.supresion import (
    EstadoSupresion,
    SolicitudDeSupresion,
    frase_correcta,
    plazos_de,
    reautenticacion_reciente,
)
from dominio.puertos.almacen import EscrituraRechazada, ReferenciaDesconocida
from dominio.puertos.gobierno import OperacionAuditada, Retencion

#: Las columnas de una solicitud, en el orden en que `_desde_fila()` las espera.
_CAMPOS = """
    id, sujeto_google, estado, solicitada_en, solicitada_por,
    cancelable_hasta, resolver_antes_de, extension_hasta, extension_motivo, cerrada_en
"""


def _desde_fila(fila: tuple) -> SolicitudDeSupresion:
    (
        identificador,
        sujeto,
        estado,
        solicitada_en,
        solicitada_por,
        cancelable_hasta,
        resolver_antes_de,
        extension_hasta,
        extension_motivo,
        cerrada_en,
    ) = fila
    return SolicitudDeSupresion(
        sujeto_google=sujeto,
        estado=EstadoSupresion(estado),
        solicitada_en=solicitada_en,
        solicitada_por=solicitada_por,
        cancelable_hasta=cancelable_hasta,
        resolver_antes_de=resolver_antes_de,
        extension_hasta=extension_hasta,
        extension_motivo=extension_motivo or "",
        cerrada_en=cerrada_en,
        secuencia=identificador,
    )


class AdaptadorSolicitudesDeSupresionPostgres(RepositorioPostgres):
    """`PuertoSolicitudesDeSupresion` sobre `solicitud_supresion`."""

    def abrir(
        self, sujeto_google: str, *, reautenticada_en: datetime, frase: str, actor: str = ""
    ) -> SolicitudDeSupresion:
        """Abre el trámite si `EQ-022` lo permite, y lo deja auditado.

        Las tres condiciones se comprueban **antes** de escribir y con la fila de
        la persona bloqueada, de modo que dos peticiones simultáneas no puedan
        abrir dos trámites: el índice único parcial las atraparía igual, pero con
        un choque de clave en vez de un motivo utilizable.

        `actor` es quien pide la supresión —hoy siempre el propio titular— y sale
        de la sesión, nunca del cuerpo. Su constancia se escribe con el mismo
        cursor: si falla, el trámite no queda abierto (hito R5). `reautenticada_en`
        llega ya **acreditada por el servidor**; este repositorio comprueba que
        siga siendo reciente, no que exista.
        """
        ahora = datetime.now(UTC)
        if not reautenticacion_reciente(reautenticada_en, ahora):
            raise EscrituraRechazada(
                "hace falta una reautenticación reciente con Google para abrir el trámite"
            )
        if not frase_correcta(frase):
            raise EscrituraRechazada("la frase de confirmación no coincide")

        cancelable_hasta, resolver_antes_de = plazos_de(ahora)
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona(cur, sujeto_google)
            cur.execute(
                "SELECT 1 FROM solicitud_supresion "
                "WHERE sujeto_google = %s AND estado = 'solicitada'",
                (sujeto_google,),
            )
            if cur.fetchone() is not None:
                raise EscrituraRechazada("ya hay un trámite de supresión abierto")
            cur.execute(
                f"""
                INSERT INTO solicitud_supresion
                    (sujeto_google, solicitada_por, reautenticada_en, frase_confirmada,
                     solicitada_en, cancelable_hasta, resolver_antes_de)
                VALUES (%s, %s, %s, true, %s, %s, %s)
                RETURNING {_CAMPOS}
                """,  # noqa: S608 — `_CAMPOS` es una constante de este módulo
                (
                    sujeto_google,
                    sujeto_google,
                    reautenticada_en,
                    ahora,
                    cancelable_hasta,
                    resolver_antes_de,
                ),
            )
            solicitud = _desde_fila(cur.fetchone())
            # `EQ-023` · misma transacción. Conteos e identificadores, nunca la
            # frase que la persona escribió ni su correo.
            anotar(
                cur,
                "supresion.solicitada",
                actor=actor or sujeto_google,
                sujeto_afectado=sujeto_google,
                detalle={"solicitud": solicitud.secuencia},
            )
            return solicitud

    def cancelar(self, sujeto_google: str, *, ahora: datetime, actor: str = "") -> bool:
        """`EQ-022` · 24 horas. `False` si no había nada abierto.

        Igual que `abrir()`: la constancia va en la misma transacción, así que un
        fallo de auditoría deja el trámite **abierto**. Es lo correcto — decirle a
        alguien que canceló algo que sigue en curso es el peor de los dos errores.
        """
        with self._escritura() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"SELECT {_CAMPOS} FROM solicitud_supresion "  # noqa: S608
                "WHERE sujeto_google = %s AND estado = 'solicitada' FOR UPDATE",
                (sujeto_google,),
            )
            fila = cur.fetchone()
            if fila is None:
                return False
            solicitud = _desde_fila(fila)
            if not solicitud.cancelable_en(ahora):
                raise EscrituraRechazada(
                    "la ventana de cancelación de 24 horas ya pasó"
                )
            cur.execute(
                "UPDATE solicitud_supresion SET estado = 'cancelada', cerrada_en = %s "
                "WHERE id = %s",
                (ahora, solicitud.secuencia),
            )
            anotar(
                cur,
                "supresion.cancelada",
                actor=actor or sujeto_google,
                sujeto_afectado=sujeto_google,
                detalle={"solicitud": solicitud.secuencia},
            )
            return True

    def abierta_de(self, sujeto_google: str) -> SolicitudDeSupresion | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"SELECT {_CAMPOS} FROM solicitud_supresion "  # noqa: S608
                "WHERE sujeto_google = %s AND estado = 'solicitada' "
                "ORDER BY solicitada_en DESC, id DESC LIMIT 1",
                (sujeto_google,),
            )
            fila = cur.fetchone()
            return _desde_fila(fila) if fila else None

    def historial(self, sujeto_google: str) -> tuple[SolicitudDeSupresion, ...]:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"SELECT {_CAMPOS} FROM solicitud_supresion "  # noqa: S608
                "WHERE sujeto_google = %s ORDER BY solicitada_en ASC, id ASC",
                (sujeto_google,),
            )
            return tuple(_desde_fila(f) for f in cur.fetchall())


class AdaptadorRetencionPostgres(RepositorioPostgres):
    """`PuertoRetencion` sobre `politica_retencion`.

    ⚠️ La tabla nace vacía y `vigente()` devuelve una `Retencion` **sin fecha**:
    la sustentación no existe todavía y una inventada sería peor que ninguna.
    """

    def vigente(self) -> Retencion:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT sustentacion_en, meses_despues, nota FROM politica_retencion "
                "ORDER BY vigente_desde DESC, id DESC LIMIT 1"
            )
            fila = cur.fetchone()
        if fila is None:
            return Retencion(
                nota="la fecha de sustentación todavía no está fijada (EQ-022)"
            )
        return Retencion(sustentacion_en=fila[0], meses_despues=fila[1], nota=fila[2] or "")

    def fijar(
        self, sustentacion_en: datetime, *, registrada_por: str, meses_despues: int = 6
    ) -> Retencion:
        """Registra una política nueva; no edita la anterior.

        `EQ-023` reserva las políticas a la doble aprobación. Este adaptador
        **no** la comprueba —no puede: no conoce la auditoría— y por eso la ruta
        que lo llama exige el registro auditado con segundo aprobador antes de
        llegar aquí. La separación es deliberada: un repositorio que decidiera
        permisos sería un segundo sitio donde se decide quién puede qué.
        """
        if meses_despues <= 0:
            raise EscrituraRechazada("el plazo de retención tiene que ser positivo")
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona(cur, registrada_por)
            cur.execute(
                "INSERT INTO politica_retencion "
                "(sustentacion_en, meses_despues, registrada_por) VALUES (%s, %s, %s)",
                (sustentacion_en, meses_despues, registrada_por),
            )
        return Retencion(sustentacion_en=sustentacion_en, meses_despues=meses_despues)


_ZONA_AUDITORIA = ZoneInfo("America/Bogota")

def _identidad_presentada(  # noqa: PLR0913 -- fila estable del read model
    identificador, nombre, correo, facultad, programa, semestre, roles,
    *, rol_comprobado: str = "",
) -> dict | None:
    if not identificador:
        return None
    nombre = str(nombre or "").strip()
    roles_visibles = [rol_comprobado] if rol_comprobado else sorted(roles or [])
    return {
        "identificador": identificador,
        "nombre": nombre,
        "correo": correo or "",
        "roles": roles_visibles,
        "naturaleza_roles": (
            "comprobados al momento de la operación" if rol_comprobado else "actuales"
        ),
        "facultad": facultad or "",
        "programa": programa or "",
        "semestre": semestre,
        "perfil_incompleto": not bool(nombre and correo),
        "etiqueta": (
            nombre
            or f"Identidad conservada únicamente para trazabilidad · {identificador}"
        ),
    }


def _operacion_presentada(fila: tuple) -> dict:
    (
        identificador, codigo, actor, sujeto, momento, detalle, exige, aprobada,
        actor_nombre, actor_correo, actor_facultad, actor_programa, actor_semestre,
        actor_roles, sujeto_nombre, sujeto_correo, sujeto_facultad, sujeto_programa,
        sujeto_semestre, sujeto_roles, aprobador_nombre, aprobador_correo,
        aprobador_facultad, aprobador_programa, aprobador_semestre, aprobador_roles,
    ) = fila
    detalle = detalle or {}
    operacion = describir_operacion(codigo)
    actor_detalle = _identidad_presentada(
        actor, actor_nombre, actor_correo, actor_facultad, actor_programa,
        actor_semestre, actor_roles, rol_comprobado=str(detalle.get("rol_actor") or ""),
    )
    sujeto_detalle = _identidad_presentada(
        sujeto, sujeto_nombre, sujeto_correo, sujeto_facultad, sujeto_programa,
        sujeto_semestre, sujeto_roles,
    )
    aprobador_detalle = _identidad_presentada(
        aprobada, aprobador_nombre, aprobador_correo, aprobador_facultad,
        aprobador_programa, aprobador_semestre, aprobador_roles,
    )
    instante_local = momento.astimezone(_ZONA_AUDITORIA)
    return {
        "id": identificador,
        "secuencia": identificador,
        "operacion": codigo,
        "operacion_detalle": operacion,
        "actor": actor,
        "actor_detalle": actor_detalle,
        "sujeto": sujeto,
        "sujeto_detalle": sujeto_detalle,
        "momento": momento.astimezone(UTC).isoformat(),
        "momento_local": instante_local.strftime("%d/%m/%Y, %H:%M:%S"),
        "zona_horaria": "America/Bogota",
        "detalle": detalle,
        "motivo": detalle.get("motivo") or "No consta",
        "resultado": detalle.get("resultado") or detalle.get("estado") or "",
        "diferencias": diferencias(detalle),
        "exige_doble_aprobacion": bool(exige),
        "aprobada_por": aprobada,
        "aprobacion": {
            "requerida": bool(exige),
            "aportada": aprobador_detalle is not None,
            "aprobador": aprobador_detalle,
        },
    }


class AdaptadorAuditoriaPostgres(RepositorioPostgres):
    """`PuertoAuditoria` sobre `auditoria_operacion`. Sólo añade."""

    def registrar(
        self,
        operacion: str,
        *,
        actor: str,
        sujeto_afectado: str | None = None,
        detalle: dict | None = None,
        exige_doble_aprobacion: bool = False,
        aprobada_por: str | None = None,
    ) -> OperacionAuditada:
        """Deja constancia. La doble aprobación de `EQ-023` se exige aquí.

        No hay aprobación automática: si la operación la exige y no llega un
        segundo aprobador **distinto del actor**, se rechaza. El CHECK de la
        tabla lo vuelve a exigir, para que no dependa de pasar por aquí.
        """
        if exige_doble_aprobacion and not aprobada_por:
            raise EscrituraRechazada(
                "esta operación exige la aprobación de un segundo administrador (EQ-023)"
            )
        if aprobada_por and aprobada_por == actor:
            raise EscrituraRechazada("nadie puede aprobar su propia operación")
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona(cur, actor)
            cur.execute(
                """
                INSERT INTO auditoria_operacion
                    (operacion, actor, sujeto_afectado, detalle,
                     exige_doble_aprobacion, aprobada_por)
                VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                RETURNING id, momento
                """,
                (
                    operacion,
                    actor,
                    sujeto_afectado,
                    json.dumps(detalle or {}),
                    exige_doble_aprobacion,
                    aprobada_por,
                ),
            )
            identificador, momento = cur.fetchone()
        return OperacionAuditada(
            operacion=operacion,
            actor=actor,
            momento=momento,
            sujeto_afectado=sujeto_afectado,
            detalle=detalle or {},
            exige_doble_aprobacion=exige_doble_aprobacion,
            aprobada_por=aprobada_por,
            secuencia=identificador,
        )

    def de(self, sujeto_google: str) -> tuple[OperacionAuditada, ...]:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT id, operacion, actor, sujeto_afectado, momento, detalle,
                       exige_doble_aprobacion, aprobada_por
                  FROM auditoria_operacion
                 WHERE sujeto_afectado = %s
                 ORDER BY momento ASC, id ASC
                """,
                (sujeto_google,),
            )
            return tuple(
                OperacionAuditada(
                    operacion=operacion,
                    actor=actor,
                    momento=momento,
                    sujeto_afectado=afectado,
                    detalle=detalle,
                    exige_doble_aprobacion=exige,
                    aprobada_por=aprobada,
                    secuencia=identificador,
                )
                for identificador, operacion, actor, afectado, momento, detalle, exige, aprobada
                in cur.fetchall()
            )

    def consultar_institucional(  # noqa: PLR0913 -- filtros del puerto explícitos
        self, actor: str, pagina: int, tamano: int, *,
        operacion: str = "", actor_filtro: str = "", sujeto_filtro: str = "",
        desde: datetime | None = None, hasta: datetime | None = None,
        categoria: str = "", doble_aprobacion: str = "",
    ) -> dict:
        """Consulta sensible: permiso, auditoría y lectura comparten transacción."""
        if pagina < 1 or tamano < 1 or tamano > 100:
            raise ValueError("paginación no admitida")
        parametros = self._parametros(
            operacion=operacion, actor_filtro=actor_filtro,
            sujeto_filtro=sujeto_filtro, desde=desde, hasta=hasta,
            categoria=categoria, doble_aprobacion=doble_aprobacion,
        )
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            anotar(
                cur, "auditoria.consultada", actor=actor,
                detalle={
                    "pagina": pagina, "tamano": tamano,
                    "filtros_activos": sorted(
                        clave for clave in (
                            "operacion", "actor", "sujeto", "desde", "hasta",
                            "categoria", "doble_aprobacion",
                        ) if parametros.get(clave)
                    ),
                },
            )
            resultado = self._leer(cur, parametros, pagina=pagina, tamano=tamano)
        return resultado

    def informe_institucional(
        self, actor: str, *, filtros: dict, confirmado: bool,
        corte_instante: datetime,
    ) -> tuple[bytes, dict]:
        """Genera, audita y confirma el corte antes de devolver sus bytes."""
        parametros = self._parametros(**filtros)
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            cur.execute("SELECT COALESCE(max(id), 0) FROM auditoria_operacion")
            corte_secuencia = int(cur.fetchone()[0])
            parametros["corte_secuencia"] = corte_secuencia
            resultado = self._leer(
                cur, parametros, pagina=1, tamano=10_000,
                corte_secuencia=corte_secuencia,
            )
            if resultado["total"] > 500 and confirmado is not True:
                raise ValueError(
                    f"confirma expresamente la exportación de {resultado['total']} operaciones"
                )
            if resultado["total"] > 10_000:
                raise ValueError("el corte supera 10.000 operaciones; acota el periodo")
            solicitante = self._persona(cur, actor)
            datos_pdf = {
                **resultado,
                "institucion": "Unimayor",
                "corte_secuencia": corte_secuencia,
                "corte_instante": corte_instante.astimezone(_ZONA_AUDITORIA).isoformat(),
                "solicitante": solicitante,
                "filtros": {
                    clave: (
                        valor.isoformat() if isinstance(valor, datetime) else valor
                    )
                    for clave, valor in parametros.items()
                    if clave not in {"codigos_categoria", "corte_secuencia"} and valor
                },
            }
            documento = generar_informe_auditoria(datos_pdf)
            huella = hashlib.sha256(documento).hexdigest()
            anotar(
                cur,
                "auditoria.informe_descargado",
                actor=actor,
                detalle={
                    "corte_secuencia": corte_secuencia,
                    "corte_instante": datos_pdf["corte_instante"],
                    "filtros": datos_pdf["filtros"],
                    "operaciones": resultado["total"],
                    "version_plantilla": VERSION_PLANTILLA_AUDITORIA,
                    "sha256": huella,
                    "bytes": len(documento),
                    "resultado": "exitoso",
                },
            )
        return documento, {
            "sha256": huella, "bytes": len(documento),
            "corte_secuencia": corte_secuencia, "total": resultado["total"],
        }

    @staticmethod
    def _parametros(  # noqa: PLR0913 -- normaliza el contrato público de filtros
        *, operacion: str = "", actor_filtro: str = "", sujeto_filtro: str = "",
        desde: datetime | None = None, hasta: datetime | None = None,
        categoria: str = "", doble_aprobacion: str = "",
        **_ignorados,
    ) -> dict:
        categoria = str(categoria or "").strip()
        doble = str(doble_aprobacion or "").strip()
        if doble not in {"", "con", "sin"}:
            raise ValueError("filtro de doble aprobación no válido")
        codigos = codigos_de_categoria(categoria) if categoria else ()
        if categoria and not codigos:
            raise ValueError("categoría de auditoría no válida")
        return {
            "operacion": str(operacion or "").strip().lower()[:120],
            "actor": str(actor_filtro or "").strip().lower()[:160],
            "sujeto": str(sujeto_filtro or "").strip().lower()[:160],
            "desde": desde,
            "hasta": hasta,
            "categoria": categoria,
            "codigos_categoria": list(codigos),
            "doble_aprobacion": doble,
        }

    @staticmethod
    def _condicion() -> str:
        return """
            WHERE (%(operacion)s = '' OR lower(a.operacion) LIKE '%%' || %(operacion)s || '%%')
              AND (%(actor)s = '' OR lower(concat_ws(' ', pa.sujeto_google, pa.nombre, pa.correo)) LIKE '%%' || %(actor)s || '%%')
              AND (%(sujeto)s = '' OR lower(concat_ws(' ', ps.sujeto_google, ps.nombre, ps.correo)) LIKE '%%' || %(sujeto)s || '%%')
              AND (%(desde)s::timestamptz IS NULL OR a.momento >= %(desde)s::timestamptz)
              AND (%(hasta)s::timestamptz IS NULL OR a.momento < %(hasta)s::timestamptz)
              AND (%(categoria)s = '' OR a.operacion = ANY(%(codigos_categoria)s::text[]))
              AND (%(doble_aprobacion)s = ''
                   OR (%(doble_aprobacion)s = 'con' AND a.exige_doble_aprobacion)
                   OR (%(doble_aprobacion)s = 'sin' AND NOT a.exige_doble_aprobacion))
              AND (%(corte_secuencia)s::bigint IS NULL OR a.id <= %(corte_secuencia)s::bigint)
        """

    def _leer(
        self, cur, parametros: dict, *, pagina: int, tamano: int,
        corte_secuencia: int | None = None,
    ) -> dict:
        condicion = self._condicion()
        params = {**parametros, "corte_secuencia": corte_secuencia}
        cte = f"WITH {PRESENTACION_PERSONAS_SQL}"
        joins = """
            LEFT JOIN presentacion pa ON pa.sujeto_google = a.actor
            LEFT JOIN presentacion ps ON ps.sujeto_google = a.sujeto_afectado
            LEFT JOIN presentacion pp ON pp.sujeto_google = a.aprobada_por
        """
        cur.execute(
            f"""{cte}
            SELECT count(*), min(a.momento), max(a.momento), count(DISTINCT a.actor),
                   count(*) FILTER (WHERE a.exige_doble_aprobacion)
              FROM auditoria_operacion a {joins} {condicion}
            """,  # noqa: S608 -- fragmentos constantes
            params,
        )
        total, primero, ultimo, actores, dobles = cur.fetchone()
        cur.execute(
            f"""{cte}
            SELECT a.operacion, count(*)
              FROM auditoria_operacion a {joins} {condicion}
             GROUP BY a.operacion ORDER BY a.operacion
            """,  # noqa: S608 -- fragmentos constantes
            params,
        )
        conteos = [(codigo, int(cantidad)) for codigo, cantidad in cur.fetchall()]
        cur.execute(
            f"""{cte}
            SELECT a.id, a.operacion, a.actor, a.sujeto_afectado, a.momento,
                   a.detalle, a.exige_doble_aprobacion, a.aprobada_por,
                   pa.nombre, pa.correo, pa.facultad, pa.programa, pa.semestre, pa.roles,
                   ps.nombre, ps.correo, ps.facultad, ps.programa, ps.semestre, ps.roles,
                   pp.nombre, pp.correo, pp.facultad, pp.programa, pp.semestre, pp.roles
              FROM auditoria_operacion a {joins} {condicion}
             ORDER BY a.momento DESC, a.id DESC
             LIMIT %(tamano)s OFFSET %(desplazamiento)s
            """,  # noqa: S608 -- fragmentos constantes
            {**params, "tamano": tamano, "desplazamiento": (pagina - 1) * tamano},
        )
        operaciones = [_operacion_presentada(fila) for fila in cur.fetchall()]
        por_categoria = Counter()
        sensibles = 0
        por_operacion = []
        for codigo, cantidad in conteos:
            descripcion = describir_operacion(codigo)
            por_categoria[descripcion["categoria"]] += cantidad
            sensibles += cantidad if descripcion["sensible"] else 0
            por_operacion.append({**descripcion, "cantidad": cantidad})
        paginas = (int(total) + tamano - 1) // tamano
        return {
            "pagina": pagina, "tamano": tamano, "total": int(total),
            "paginas": paginas, "operaciones": operaciones,
            "resumen": {
                "total": int(total), "actores": int(actores),
                "sensibles": sensibles, "doble_aprobacion": int(dobles),
                "desde": primero.astimezone(_ZONA_AUDITORIA).isoformat() if primero else None,
                "hasta": ultimo.astimezone(_ZONA_AUDITORIA).isoformat() if ultimo else None,
                "por_categoria": dict(sorted(por_categoria.items())),
                "por_operacion": por_operacion,
            },
            "glosario": glosario([codigo for codigo, _ in conteos]),
        }

    @staticmethod
    def _persona(cur, identificador: str) -> dict:
        cur.execute(
            f"""WITH {PRESENTACION_PERSONAS_SQL}
            SELECT sujeto_google, nombre, correo, facultad, programa, semestre, roles
              FROM presentacion WHERE sujeto_google = %s
            """,  # noqa: S608 -- CTE constante
            (identificador,),
        )
        fila = cur.fetchone()
        return _identidad_presentada(*fila) if fila else {
            "identificador": identificador,
            "etiqueta": f"Identidad conservada únicamente para trazabilidad · {identificador}",
            "roles": [], "naturaleza_roles": "actuales",
        }


#: Las columnas de una propuesta, en el orden en que `_propuesta_desde_fila()`
#: las espera. Una sola definición para las consultas que la leen.
_CAMPOS_PROPUESTA = """
    id, operacion, payload, propuesta_por, propuesta_en, estado, aprobada_por, aprobada_en
"""


def _propuesta_desde_fila(fila: tuple) -> Propuesta:
    identificador, operacion, payload, por, en, estado, aprobada_por, aprobada_en = fila
    return Propuesta(
        operacion=operacion,
        payload=payload or {},
        propuesta_por=por,
        propuesta_en=en,
        estado=EstadoPropuesta(estado),
        aprobada_por=aprobada_por,
        aprobada_en=aprobada_en,
        secuencia=identificador,
    )


class AdaptadorPropuestasPostgres(RepositorioPostgres):
    """La doble aprobación de `EQ-023` sobre `propuesta_administrativa`.

    ⚠️ **Este adaptador aplica el efecto de lo que aprueba**, y conviene decir
    por qué, porque rompe la costumbre del árbol de que un repositorio sólo
    escriba en su propia tabla.

    `EQ-023` exige que *«aprobación, cambio de política y auditoría se confirmen
    atómicamente»*. Atómicamente significa **una transacción**, y una transacción
    significa **una conexión**. Repartir los tres pasos entre tres repositorios
    —cada uno con la suya— es exactamente lo que producía el defecto que este
    hito corrige: piezas que se confirman por separado y un éxito informado
    aunque una fallara.

    Así que el efecto se aplica aquí, con el mismo cursor, y la lista de qué se
    puede aplicar es **cerrada** (`_EFECTOS`). No es un despachador genérico: una
    propuesta con una operación que este módulo no sabe ejecutar se rechaza al
    crearse, en el dominio, y nunca llega a quedar pendiente para siempre.
    """

    def crear(self, operacion: str, payload: dict, *, propuesta_por: str) -> Propuesta:
        """La **primera** petición autenticada. Deja la propuesta pendiente.

        No aplica nada y no acepta ningún aprobador: quien propone no puede
        afirmar que otro aprobó, y el modo de garantizarlo es que esta operación
        no tenga dónde escribirlo.
        """
        # El tipo del dominio valida la operación antes de tocar la base: una
        # propuesta que nadie sabría aplicar no llega a existir.
        propuesta = Propuesta(operacion=operacion, payload=payload, propuesta_por=propuesta_por)
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona(cur, propuesta_por)
            exigir_investigador_administrador(cur, propuesta_por)
            cur.execute(
                f"""
                INSERT INTO propuesta_administrativa
                    (operacion, payload, huella, propuesta_por)
                VALUES (%s, %s::jsonb, %s, %s)
                RETURNING {_CAMPOS_PROPUESTA}
                """,  # noqa: S608 — `_CAMPOS_PROPUESTA` es constante de este módulo
                (
                    propuesta.operacion,
                    json.dumps(propuesta.payload),
                    propuesta.huella,
                    propuesta_por,
                ),
            )
            return _propuesta_desde_fila(cur.fetchone())

    def aprobar(self, identificador: int, *, aprobador: str) -> Propuesta:
        """La **segunda** petición autenticada, de otra persona. Aplica y audita.

        Todo en una transacción, y el orden es el contrato:

        1. **comprobar el rol del aprobador ahora**, no cuando se propuso: un rol
           retirado entre las dos peticiones no puede seguir aprobando;
        2. **bloquear la fila** con `FOR UPDATE`, para que dos aprobaciones
           simultáneas no apliquen el efecto dos veces;
        3. **comprobar que puede aprobarla** —que no es suya y que sigue
           pendiente—, con la regla del dominio;
        4. **recomputar la huella** del contenido almacenado y compararla con la
           guardada. Es lo que convierte «lo aprobado es lo propuesto» en algo
           comprobable: si la fila se hubiera alterado entre las dos peticiones,
           aquí no cuadraría;
        5. **aplicar el efecto**;
        6. **auditar** con los dos actores;
        7. **cerrar la propuesta**.

        Si cualquiera falla, no se confirma ninguno.
        """
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona(cur, aprobador)
            exigir_investigador_administrador(cur, aprobador)
            cur.execute(
                f"SELECT {_CAMPOS_PROPUESTA}, huella FROM propuesta_administrativa "  # noqa: S608
                "WHERE id = %s FOR UPDATE",
                (identificador,),
            )
            fila = cur.fetchone()
            if fila is None:
                raise ReferenciaDesconocida("esa propuesta no existe")
            propuesta = _propuesta_desde_fila(fila[:-1])
            guardada = fila[-1]

            try:
                propuesta.exigir_aprobable_por(aprobador)
            except PropuestaInvalida as error:
                raise EscrituraRechazada(str(error)) from None

            if huella_de(propuesta.operacion, propuesta.payload) != guardada:
                # No puede pasar por el camino normal —nada edita esta tabla—, y
                # por eso se comprueba: si pasara, alguien cambió el contenido
                # entre proponer y aprobar, y lo aprobado no sería lo propuesto.
                raise EscrituraRechazada(
                    "el contenido de la propuesta no coincide con su huella"
                )

            _EFECTOS[propuesta.operacion](cur, propuesta)
            anotar(
                cur,
                _OPERACION_AUDITADA[propuesta.operacion],
                actor=propuesta.propuesta_por,
                detalle={"propuesta": propuesta.secuencia, "huella": guardada},
                # `exige_doble_aprobacion` lo deriva `anotar()` de este aprobador.
                aprobada_por=aprobador,
            )
            cur.execute(
                f"""
                UPDATE propuesta_administrativa
                   SET estado = 'aprobada', aprobada_por = %s, aprobada_en = now()
                 WHERE id = %s
                RETURNING {_CAMPOS_PROPUESTA}
                """,  # noqa: S608 — `_CAMPOS_PROPUESTA` es constante de este módulo
                (aprobador, identificador),
            )
            return _propuesta_desde_fila(cur.fetchone())

    def consultar(self, identificador: int) -> Propuesta | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"SELECT {_CAMPOS_PROPUESTA} FROM propuesta_administrativa "  # noqa: S608
                "WHERE id = %s",
                (identificador,),
            )
            fila = cur.fetchone()
            return _propuesta_desde_fila(fila) if fila else None

    def pendientes(self) -> tuple[Propuesta, ...]:
        """Las que esperan un segundo administrador, de la más reciente atrás."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"SELECT {_CAMPOS_PROPUESTA} FROM propuesta_administrativa "  # noqa: S608
                "WHERE estado = 'pendiente' ORDER BY propuesta_en DESC, id DESC"
            )
            return tuple(_propuesta_desde_fila(f) for f in cur.fetchall())


def _fijar_retencion(cur: Any, propuesta: Propuesta) -> None:
    """El efecto de `retencion.fijar`, con el mismo cursor de la aprobación.

    `registrada_por` es **quien propuso**, no quien aprueba: la política la
    propone alguien y el segundo la autoriza. Guardar al aprobador aquí haría
    perder de vista de quién fue la iniciativa, que es la mitad de lo que una
    auditoría de doble aprobación tiene que poder reconstruir — la otra mitad la
    guarda `auditoria_operacion.aprobada_por`.
    """
    sustentacion = datetime.fromisoformat(str(propuesta.payload["sustentacion_en"]))
    if sustentacion.tzinfo is None:
        sustentacion = sustentacion.replace(tzinfo=UTC)
    meses = int(propuesta.payload.get("meses_despues", 6))
    if meses <= 0:
        raise EscrituraRechazada("el plazo de retención tiene que ser positivo")
    cur.execute(
        "INSERT INTO politica_retencion (sustentacion_en, meses_despues, registrada_por) "
        "VALUES (%s, %s, %s)",
        (sustentacion, meses, propuesta.propuesta_por),
    )


#: Qué hace cada operación al aprobarse. **Lista cerrada**, y del mismo módulo:
#: un despachador que aceptara nombres de fuera convertiría la aprobación en una
#: forma de ejecutar lo que sea.
#:
#: Sus claves tienen que ser exactamente las de
#: `OPERACIONES_CON_DOBLE_APROBACION`; una prueba lo comprueba, porque una
#: operación proponible que nadie sabe aplicar quedaría pendiente para siempre.
_EFECTOS = {"retencion.fijar": _fijar_retencion}

#: Con qué nombre queda cada operación en `auditoria_operacion`. Aparte de
#: `_EFECTOS` porque son dos cosas distintas —qué se hace y cómo se llama lo
#: hecho— y derivarlo del nombre de la operación con un `split()` habría atado el
#: registro de auditoría a la forma de una cadena.
_OPERACION_AUDITADA = {"retencion.fijar": "retencion.fijada"}
