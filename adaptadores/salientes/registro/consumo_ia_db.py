"""Persistencia, autorización y agregado del consumo institucional de IA."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import exigir_investigador_administrador
from adaptadores.salientes.registro.base_postgres import traducir_fallo
from adaptadores.salientes.tasas.banrep import FUENTE, ClienteTRMBanrep, ObservacionTRM
from dominio.modelo.consumo_ia import (
    RegistroConsumoIA,
    TarifaIA,
    costo_estimado_usd,
)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator

ZONA_LOCAL = ZoneInfo("America/Bogota")
UMBRAL_DESGLOSE = 5
VIGENCIA_CACHE_ULTIMA_TRM = timedelta(hours=6)
_ALIAS_TARIFA = {
    "deepseek-flash": "DeepSeek-V4.1-Flash",
    "deepseek-v4-flash": "DeepSeek-V4.1-Flash",
    "deepseek-v4-flash-vision-exp": "DeepSeek-V4.1-Flash",
    "deepseek-v4-pro": "DeepSeek-V4-Pro-0813",
}


class AdaptadorConsumoIAPostgres:
    def __init__(
        self, cadena_de_conexion: str, *, cliente_trm: ClienteTRMBanrep | None = None
    ) -> None:
        self._cadena = cadena_de_conexion
        self._cliente_trm = cliente_trm or ClienteTRMBanrep()

    @contextmanager
    def _conexion(self) -> Iterator[Any]:
        from adaptadores.salientes.conexion import conectar  # noqa: PLC0415

        with traducir_fallo(), conectar(self._cadena) as cnx:
            yield cnx

    def registrar(self, registro: RegistroConsumoIA) -> bool:
        """INSERT idempotente: una respuesta del proveedor tampoco se duplica."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                INSERT INTO consumo_ia_llamada (
                    llamada, instante_utc, proveedor, modelo_solicitado,
                    modelo_respondido, respuesta_proveedor, es_local, estado,
                    reintento, entrada_cache_hit, entrada_cache_miss,
                    entrada_total, salida, total
                ) VALUES (%s, %s, %s, %s, NULLIF(%s, ''), NULLIF(%s, ''),
                          %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING llamada
                """,
                (
                    registro.llamada,
                    registro.instante_utc,
                    registro.proveedor,
                    registro.modelo_solicitado,
                    registro.modelo_respondido,
                    registro.respuesta_proveedor,
                    registro.local,
                    registro.estado,
                    registro.reintento,
                    registro.entrada_cache_hit,
                    registro.entrada_cache_miss,
                    registro.entrada_total,
                    registro.salida,
                    registro.total,
                ),
            )
            insertado = cur.fetchone() is not None
            cnx.commit()
        return insertado

    def resumen(self, actor: str, desde: datetime, hasta: datetime) -> dict:
        """Lee bajo rol bloqueado y audita antes del SELECT en la transacción."""
        hechos, tarifas, cache, ultima_cache = self._leer_auditado(actor, desde, hasta)
        fechas = {hecho.instante_utc.astimezone(ZONA_LOCAL).date() for hecho in hechos}
        cache, fallo_trm, ultima_trm = self._completar_trm(
            fechas, cache, ultima_cache
        )
        return _agregar(hechos, tarifas, cache, desde, hasta, fallo_trm, ultima_trm)

    def resumen_deepseek(self, actor: str, desde: datetime, hasta: datetime) -> dict:
        """Referencia institucional del intervalo, nunca atribuida a una clase.

        Conserva la misma autorización y auditoría que el informe de consumo.
        Se filtra antes de calcular costos: los proveedores locales u otros
        modelos no deben inflar el subtotal presentado como DeepSeek.
        """
        hechos, tarifas, cache, ultima_cache = self._leer_auditado(actor, desde, hasta)
        hechos = [h for h in hechos if h.proveedor.casefold() == "deepseek"]
        if not hechos:
            return _agregar([], tarifas, {}, desde, hasta, None)
        fechas = {h.instante_utc.astimezone(ZONA_LOCAL).date() for h in hechos}
        cache, fallo_trm, ultima_trm = self._completar_trm(fechas, cache, ultima_cache)
        return _agregar(hechos, tarifas, cache, desde, hasta, fallo_trm, ultima_trm)

    def auditar_exportacion(
        self,
        actor: str,
        desde: datetime,
        hasta: datetime,
        formato: str,
        documento: bytes,
    ) -> None:
        """La constancia se confirma antes de que el borde entregue los bytes."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            anotar(
                cur,
                "exportar_consumo_ia_institucional",
                actor=actor,
                detalle={
                    "desde": desde.isoformat(),
                    "hasta": hasta.isoformat(),
                    "zona": "America/Bogota",
                    "formato": formato,
                    "bytes": len(documento),
                    "sha256": hashlib.sha256(documento).hexdigest(),
                    "incluye_personas": False,
                },
            )
            cnx.commit()

    def _leer_auditado(
        self, actor: str, desde: datetime, hasta: datetime
    ) -> tuple[
        list[RegistroConsumoIA],
        list[TarifaIA],
        dict[date, Decimal],
        tuple[ObservacionTRM, datetime] | None,
    ]:
        with self._conexion() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            anotar(
                cur,
                "consultar_consumo_ia_institucional",
                actor=actor,
                detalle={
                    "desde": desde.isoformat(),
                    "hasta": hasta.isoformat(),
                    "zona": "America/Bogota",
                    "incluye_personas": False,
                },
            )
            cur.execute(
                """
                SELECT llamada, instante_utc, proveedor, modelo_solicitado,
                       COALESCE(modelo_respondido, ''), COALESCE(respuesta_proveedor, ''),
                       es_local, estado, reintento, entrada_cache_hit,
                       entrada_cache_miss, entrada_total, salida, total
                  FROM consumo_ia_llamada
                 WHERE instante_utc >= %s AND instante_utc < %s
                 ORDER BY instante_utc, llamada
                """,
                (desde, hasta),
            )
            hechos = [RegistroConsumoIA(*fila) for fila in cur.fetchall()]
            cur.execute(
                """
                SELECT proveedor, modelo, franja, vigente_desde, vigente_hasta,
                       entrada_cache_hit_usd_millon,
                       entrada_cache_miss_usd_millon, salida_usd_millon, fuente
                  FROM tarifa_ia
                 WHERE vigente_desde < %s
                 ORDER BY vigente_desde DESC, id DESC
                """,
                (hasta,),
            )
            tarifas = [TarifaIA(*fila) for fila in cur.fetchall()]
            cur.execute(
                "SELECT fecha, pesos_por_usd FROM trm_oficial_cache "
                "WHERE fecha BETWEEN %s AND %s",
                (desde.astimezone(ZONA_LOCAL).date(), hasta.astimezone(ZONA_LOCAL).date()),
            )
            cache = {fila[0]: Decimal(fila[1]) for fila in cur.fetchall()}
            cur.execute(
                "SELECT fecha, pesos_por_usd, consultada_en "
                "FROM trm_oficial_cache WHERE es_ultima_disponible "
                "ORDER BY consultada_en DESC LIMIT 1"
            )
            fila_ultima = cur.fetchone()
            ultima_cache = (
                (ObservacionTRM(fila_ultima[0], Decimal(fila_ultima[1])), fila_ultima[2])
                if fila_ultima is not None
                else None
            )
            cnx.commit()
        return hechos, tarifas, cache, ultima_cache

    def _completar_trm(
        self,
        fechas: set[date],
        cache: dict[date, Decimal],
        ultima_cache: tuple[ObservacionTRM, datetime] | None,
    ) -> tuple[dict[date, Decimal], str | None, ObservacionTRM | None]:
        faltantes = sorted(fechas - cache.keys())
        ahora = datetime.now(UTC)
        fallos: list[str] = []
        nuevas: tuple[ObservacionTRM, ...] = ()
        if faltantes:
            try:
                nuevas = self._cliente_trm.historica(faltantes[0], faltantes[-1])
            except Exception:  # noqa: BLE001 — red/XML oficial; se declara ausencia
                fallos.append("no fue posible actualizar la TRM histórica oficial")
        ultima = ultima_cache[0] if ultima_cache is not None else None
        cache_reciente = bool(
            ultima_cache and ahora - ultima_cache[1].astimezone(UTC) < VIGENCIA_CACHE_ULTIMA_TRM
        )
        ultima_nueva = None
        if not cache_reciente:
            try:
                ultima_nueva = self._cliente_trm.ultima()
                ultima = ultima_nueva or ultima
            except Exception:  # noqa: BLE001 — una caché previa sigue siendo visible
                fallos.append("no fue posible actualizar la última TRM oficial")
        if not nuevas and ultima_nueva is None:
            return cache, "; ".join(fallos) or None, ultima
        with self._conexion() as cnx, cnx.cursor() as cur:
            for observacion in nuevas:
                cur.execute(
                    """
                    INSERT INTO trm_oficial_cache
                        (fecha, pesos_por_usd, fuente, consultada_en, es_ultima_disponible)
                    VALUES (%s, %s, %s, %s, false)
                    ON CONFLICT (fecha) DO UPDATE
                       SET pesos_por_usd = EXCLUDED.pesos_por_usd,
                           fuente = EXCLUDED.fuente,
                           consultada_en = EXCLUDED.consultada_en
                    """,
                    (observacion.fecha, observacion.pesos_por_usd, FUENTE, ahora),
                )
                cache[observacion.fecha] = observacion.pesos_por_usd
            if ultima_nueva is not None:
                cur.execute("UPDATE trm_oficial_cache SET es_ultima_disponible = false")
                cur.execute(
                    """
                    INSERT INTO trm_oficial_cache
                        (fecha, pesos_por_usd, fuente, consultada_en, es_ultima_disponible)
                    VALUES (%s, %s, %s, %s, true)
                    ON CONFLICT (fecha) DO UPDATE
                       SET pesos_por_usd = EXCLUDED.pesos_por_usd,
                           fuente = EXCLUDED.fuente,
                           consultada_en = EXCLUDED.consultada_en,
                           es_ultima_disponible = true
                    """,
                    (ultima_nueva.fecha, ultima_nueva.pesos_por_usd, FUENTE, ahora),
                )
                cache[ultima_nueva.fecha] = ultima_nueva.pesos_por_usd
            cnx.commit()
        return cache, "; ".join(fallos) or None, ultima


def _tarifa(hecho: RegistroConsumoIA, tarifas: list[TarifaIA]) -> TarifaIA | None:
    modelo = _ALIAS_TARIFA.get(hecho.modelo_respondido, hecho.modelo_respondido)
    normalizado = RegistroConsumoIA(
        **{**hecho.__dict__, "modelo_respondido": modelo}
    )
    return next((tarifa for tarifa in tarifas if tarifa.aplica(normalizado)), None)


def _suma_o_ausencia(hechos: list[RegistroConsumoIA], campo: str) -> int | None:
    valores = [getattr(hecho, campo) for hecho in hechos if getattr(hecho, campo) is not None]
    return sum(valores) if valores else None


def _decimal_legible(valor: Decimal | None) -> str | None:
    """Serializa igual un valor de red y su copia ``numeric`` de PostgreSQL."""
    if valor is None:
        return None
    texto = format(valor, "f")
    return texto.rstrip("0").rstrip(".") if "." in texto else texto


def _agregar(  # noqa: PLR0913 — contrato explícito entre lectura, TRM y periodo
    hechos: list[RegistroConsumoIA],
    tarifas: list[TarifaIA],
    trm: dict[date, Decimal],
    desde: datetime,
    hasta: datetime,
    fallo_trm: str | None,
    ultima_trm: ObservacionTRM | None = None,
) -> dict:
    grupos: dict[tuple[str, str], list[RegistroConsumoIA]] = defaultdict(list)
    dias: dict[str, int] = defaultdict(int)
    costos_dia: dict[str, list[Decimal]] = defaultdict(list)
    incompletos_dia: dict[str, int] = defaultdict(int)
    horas: dict[int, int] = defaultdict(int)
    costos_usd: list[Decimal] = []
    costos_cop: list[Decimal] = []
    costos_faltantes = 0
    trm_faltantes = 0
    locales = 0
    for hecho in hechos:
        grupos[(hecho.proveedor, hecho.modelo_respondido or hecho.modelo_solicitado)].append(hecho)
        local = hecho.instante_utc.astimezone(ZONA_LOCAL)
        clave_dia = local.date().isoformat()
        dias[clave_dia] += 1
        horas[local.hour] += 1
        if hecho.local:
            locales += 1
        costo = costo_estimado_usd(hecho, _tarifa(hecho, tarifas))
        if costo is None:
            costos_faltantes += 1
            incompletos_dia[clave_dia] += 1
            continue
        costos_usd.append(costo)
        costos_dia[clave_dia].append(costo)
        if hecho.local:
            costos_cop.append(Decimal("0"))
            continue
        tasa = trm.get(local.date())
        if tasa is None:
            trm_faltantes += 1
        else:
            costos_cop.append((costo * tasa).quantize(Decimal("0.000001")))
    desglose = []
    for (proveedor, modelo), filas in sorted(grupos.items()):
        desglose.append(
            {
                "proveedor": proveedor,
                "modelo": modelo,
                "llamadas": len(filas),
                "medidas": sum(hecho.medido for hecho in filas),
                "entrada_cache_hit": _suma_o_ausencia(filas, "entrada_cache_hit"),
                "entrada_cache_miss": _suma_o_ausencia(filas, "entrada_cache_miss"),
                "entrada_total": _suma_o_ausencia(filas, "entrada_total"),
                "salida": _suma_o_ausencia(filas, "salida"),
            }
        )
    ultima_fecha = ultima_trm.fecha if ultima_trm is not None else None
    ultima_valor = ultima_trm.pesos_por_usd if ultima_trm is not None else None
    return {
        "version": "consumo-ia.institucional.v1",
        "naturaleza": "modulo_financiero_separado_de_los_51_kpi",
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "zona": "America/Bogota"},
        "totales": {
            "llamadas": len(hechos),
            "medidas": sum(hecho.medido for hecho in hechos),
            "sin_medicion": sum(hecho.estado == "sin_medicion" for hecho in hechos),
            "fallidas": sum(hecho.estado == "fallida" for hecho in hechos),
            "entrada_total": _suma_o_ausencia(hechos, "entrada_total"),
            "salida": _suma_o_ausencia(hechos, "salida"),
            "tokens": _suma_o_ausencia(hechos, "total"),
        },
        "costos": {
            "estimado_usd": str(sum(costos_usd)) if costos_usd and not costos_faltantes else None,
            "subtotal_calculable_usd": str(sum(costos_usd)) if costos_usd else None,
            "estimado_cop": str(sum(costos_cop)) if costos_cop and not costos_faltantes and not trm_faltantes else None,
            "subtotal_calculable_cop": str(sum(costos_cop)) if costos_cop else None,
            "llamadas_sin_tarifa_o_medicion": costos_faltantes,
            "llamadas_sin_trm_historica": trm_faltantes,
            "llamadas_locales_api_usd_cero": locales,
            "infraestructura_local_calculada": False,
            "es_cargo_real": False,
        },
        "trm_actual": {
            "fecha": ultima_fecha.isoformat() if ultima_fecha else None,
            "pesos_por_usd": _decimal_legible(ultima_valor),
            "fuente": FUENTE,
            "desactualizada": bool(
                ultima_fecha
                and (datetime.now(ZONA_LOCAL).date() - ultima_fecha).days > 4
            ),
            "advertencia": fallo_trm,
        },
        "por_modelo": desglose,
        "serie_diaria": [
            {"fecha": clave, "llamadas": valor if valor >= UMBRAL_DESGLOSE else None,
             "costo_usd": (
                 _decimal_legible(sum(costos_dia[clave]))
                 if valor >= UMBRAL_DESGLOSE and not incompletos_dia[clave]
                 and costos_dia[clave] else None
             ),
             "estado": "disponible" if valor >= UMBRAL_DESGLOSE else "suprimido"}
            for clave, valor in sorted(dias.items())
        ],
        "distribucion_hora_local": [
            {"hora": hora, "llamadas": horas.get(hora) if horas.get(hora, 0) >= UMBRAL_DESGLOSE else None,
             "estado": "disponible" if horas.get(hora, 0) >= UMBRAL_DESGLOSE else "suprimido"}
            for hora in range(24)
        ],
        "regla_supresion": f"los desgloses diarios y horarios con menos de {UMBRAL_DESGLOSE} llamadas no se muestran",
        "advertencias": [
            "Las horas de mayor uso del sistema no son las franjas tarifarias pico del proveedor.",
            "Los costos son estimaciones reproducibles, no cargos reales de facturación.",
            "Los registros anteriores a esta migración no se reconstruyen ni se presentan como exactos.",
        ],
    }
