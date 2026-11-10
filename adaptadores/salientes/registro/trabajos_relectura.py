import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from adaptadores.salientes.conexion import conectar
from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.relectura_factores import (
    _ejecutar,
    autorizar_operador,
    ejecutar,
)
from dominio.modelo.factores_conductuales import VERSION
from dominio.puertos.almacen import AlmacenNoConfigurado


class ConflictoRelectura(ValueError):
    pass

class TrabajosRelecturaPostgres:
    def __init__(self, cadena, *, interprete=None):
        self.cadena = cadena
        self.interprete = interprete

    def _conexion(self):
        if not self.cadena:
            raise AlmacenNoConfigurado("la relectura requiere PostgreSQL")
        return conectar(self.cadena)

    @staticmethod
    def _recuperar(cur):
        cur.execute(
            "SELECT 1 FROM relectura_conductual_trabajo "
            "WHERE estado IN ('en_cola','en_curso') "
            "AND actualizado_en < now() - interval '5 minutes' LIMIT 1"
        )
        if not cur.fetchone():
            return
        cur.execute(
            "SELECT pg_try_advisory_xact_lock(hashtext(%s))", ("didaxia.factores." + VERSION,)
        )
        if cur.fetchone()[0]:
            cur.execute(
                "UPDATE relectura_conductual_trabajo SET estado='interrumpido', "
                "motivo='ejecucion_interrumpida', actualizado_en=now() "
                "WHERE estado IN ('en_cola','en_curso') "
                "AND actualizado_en < now() - interval '5 minutes'"
            )

    @staticmethod
    def _leer(cur, actor, identificador=None):
        cur.execute(
            "SELECT id, version, clase, desde, hasta, maximo_llamadas, estado, "
            "resumen, motivo, actualizado_en FROM relectura_conductual_trabajo "
            "WHERE actor=%s AND "
            + ("id=%s" if identificador else "estado<>'vista_previa'")
            + " ORDER BY creado_en DESC LIMIT 1",
            (actor, identificador) if identificador else (actor,),
        )
        fila = cur.fetchone()
        if not fila:
            return None
        return dict(
            id=str(fila[0]),
            version=fila[1],
            clase=fila[2],
            desde=fila[3].isoformat(),
            hasta=fila[4].isoformat(),
            maximo_llamadas=fila[5],
            estado=fila[6],
            resumen=fila[7],
            motivo=fila[8],
            actualizado_en=fila[9].isoformat(),
        )

    def consultar(self, actor, identificador=None):
        with self._conexion() as cnx, cnx.cursor() as cur:
            autorizar_operador(cur, actor)
            self._recuperar(cur)
            return self._leer(cur, actor, identificador)

    def prever(self, actor, *, clase=None, desde=None, hasta=None):
        ahora = datetime.now(UTC)
        hasta = hasta or ahora
        desde = desde or datetime(1970, 1, 1, tzinfo=UTC)
        if desde.tzinfo is None or hasta.tzinfo is None or desde >= hasta:
            raise ValueError("el periodo requiere fechas ordenadas con zona horaria")
        hasta = min(hasta, ahora)
        if desde >= hasta:
            raise ValueError("el periodo no contiene historial pasado")
        with self._conexion() as cnx, cnx.cursor() as cur:
            autorizar_operador(cur, actor)
            if clase:
                cur.execute("SELECT id FROM clase WHERE id=%s AND archivada_en IS NULL", (clase,))
                if not cur.fetchone():
                    raise ValueError("el curso no está disponible")
        resumen = _ejecutar(self.cadena, actor=actor, desde=desde, hasta=hasta, clase=clase)
        identificador = str(uuid4())
        with self._conexion() as cnx, cnx.cursor() as cur:
            autorizar_operador(cur, actor)
            cur.execute(
                "INSERT INTO relectura_conductual_trabajo "
                "(id,actor,version,clase,desde,hasta,estado,resumen) "
                "VALUES (%s,%s,%s,%s,%s,%s,'vista_previa',%s::jsonb)",
                (identificador, actor, VERSION, clase, desde, hasta, json.dumps(resumen)),
            )
            return self._leer(cur, actor, identificador)

    def confirmar(self, actor, identificador, *, maximo_llamadas):
        if type(maximo_llamadas) is not int or not 1 <= maximo_llamadas <= 200:
            raise ValueError("elige un máximo entre 1 y 200 llamadas")
        with self._conexion() as cnx, cnx.cursor() as cur:
            autorizar_operador(cur, actor)

            cur.execute("SELECT pg_advisory_xact_lock(hashtext('didaxia.factores.confirmacion'))")
            self._recuperar(cur)
            cur.execute(
                "SELECT estado, creado_en, version FROM relectura_conductual_trabajo "
                "WHERE id=%s AND actor=%s FOR UPDATE",
                (identificador, actor),
            )
            fila = cur.fetchone()
            if not fila:
                raise ValueError("la vista previa no existe")
            if fila[0] != "vista_previa":
                return self._leer(cur, actor, identificador), False
            if fila[1] < datetime.now(UTC) - timedelta(minutes=15) or fila[2] != VERSION:
                raise ConflictoRelectura("consulta de nuevo los pendientes: la vista previa expiró")
            cur.execute(
                "SELECT 1 FROM relectura_conductual_trabajo WHERE estado IN ('en_cola','en_curso')"
            )
            if cur.fetchone():
                raise ConflictoRelectura("ya hay un lote en curso; espera a que termine")
            cur.execute(
                "UPDATE relectura_conductual_trabajo SET estado='en_cola', "
                "maximo_llamadas=%s, actualizado_en=now() WHERE id=%s",
                (maximo_llamadas, identificador),
            )
            anotar(
                cur,
                "factores.relectura_confirmada",
                actor=actor,
                detalle=dict(
                    trabajo=identificador, version=VERSION, maximo_llamadas=maximo_llamadas
                ),
            )
            return self._leer(cur, actor, identificador), True

    def procesar(self, actor, identificador):
        try:
            with self._conexion() as cnx, cnx.cursor() as cur:
                autorizar_operador(cur, actor)
                cur.execute(
                    "UPDATE relectura_conductual_trabajo SET estado='en_curso', actualizado_en=now() "
                    "WHERE id=%s AND actor=%s AND estado='en_cola' RETURNING id",
                    (identificador, actor),
                )
                if not cur.fetchone():
                    return
                trabajo = self._leer(cur, actor, identificador)

            def avance(resumen):
                with self._conexion() as cnx, cnx.cursor() as cur:
                    cur.execute(
                        "UPDATE relectura_conductual_trabajo SET resumen=%s::jsonb, actualizado_en=now() "
                        "WHERE id=%s AND estado='en_curso' RETURNING id",
                        (json.dumps(resumen), identificador),
                    )
                    if not cur.fetchone():
                        raise ConflictoRelectura("el trabajo fue interrumpido")

            resumen = ejecutar(
                self.cadena,
                actor=actor,
                desde=datetime.fromisoformat(trabajo["desde"]),
                hasta=datetime.fromisoformat(trabajo["hasta"]),
                clase=trabajo["clase"],
                aplicar=True,
                maximo_llamadas=trabajo["maximo_llamadas"],
                interprete=self.interprete,
                avance=avance,
            )
            self._terminar(
                actor,
                identificador,
                resumen=resumen,
                motivo=(resumen.get("motivo_fallo") or "proveedor_sin_lectura") if resumen.get('detenido', resumen.get('fase') == 'interrumpido') else None,
            )
        except Exception:
            self._terminar(actor, identificador, motivo="ejecucion_interrumpida")

    def _terminar(self, actor, identificador, *, resumen=None, motivo=None):
        try:
            with self._conexion() as cnx, cnx.cursor() as cur:
                cur.execute(
                    "UPDATE relectura_conductual_trabajo SET estado=%s, motivo=%s, "
                    "resumen=COALESCE(%s::jsonb,resumen), actualizado_en=now() "
                    "WHERE id=%s AND actor=%s AND estado IN ('en_curso','en_cola')",
                    (
                        "interrumpido" if motivo else "completado",
                        motivo,
                        json.dumps(resumen) if resumen is not None else None,
                        identificador,
                        actor,
                    ),
                )
        except Exception:
            return
