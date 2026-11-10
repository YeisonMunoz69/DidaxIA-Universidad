"""Motor común de relectura para CLI y panel; una lectura por turno y versión."""

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime

from adaptadores.salientes.conexion import conectar
from adaptadores.salientes.generacion.interpretacion_deepseek import (
    FalloInterpretacion,
    InterpretacionDeepSeek,
)
from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import exigir_investigador_administrador
from adaptadores.salientes.registro.base_postgres import exigir_persona_activa
from adaptadores.salientes.registro.factores_db import guardar, habilitado
from adaptadores.salientes.registro.kpi_consultas import ConsultasKPI, alcance_sql
from adaptadores.salientes.registro.lectura_factores import completar_trazas
from dominio.modelo.factores_conductuales import RUBRICA, VERSION
from dominio.modelo.fenomenos_anteproyecto import _metadatos
from dominio.modelo.fusion_conductual import lectura_guardada


def autorizar_operador(cur, actor):
    exigir_investigador_administrador(cur, actor)
    exigir_persona_activa(cur, actor)


def entrada_historica(hilo, posicion):
    actual = hilo[posicion]
    return dict(
        mensaje=actual["mensaje"][:4000],
        regla={},
        ejercicio_activo=None,
        historial=[
            dict(estudiante=t["mensaje"][:1500], tutor=t.get("tutor", "")[:2500])
            for t in hilo[max(0, posicion - 3) : posicion]
        ],
        evidencia_matematica=[
            dict(
                turno=i + 1,
                intento=_metadatos(t["trazas"], "verificación del intento del estudiante"),
                correccion_entregada=_metadatos(t["trazas"], "verificación simbólica").get(
                    "correccion_del_resultado_entregada"
                )
                is True,
            )
            for i, t in enumerate(hilo[: posicion + 1])
            if _metadatos(t["trazas"], "verificación del intento del estudiante").get("veredicto")
            in ("valida", "invalida")
        ][-6:],
    )


def ejecutar(cadena, **opciones):
    """Una relectura a la vez; evita llamadas duplicadas de dos operadores."""
    with conectar(cadena) as cnx, cnx.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(hashtext(%s))", ("didaxia.factores." + VERSION,))
        if not cur.fetchone()[0]:
            raise RuntimeError("ya hay una relectura de esta versión en curso")
        cnx.commit()
        try:
            return _ejecutar(cadena, **opciones)
        finally:
            cur.execute("SELECT pg_advisory_unlock(hashtext(%s))", ("didaxia.factores." + VERSION,))


def _ejecutar(  # noqa: C901, PLR0913, PLR0912, PLR0915 — flujo acotado con puertas de autorización
    cadena,
    *,
    actor,
    desde,
    hasta,
    clase=None,
    aplicar=False,
    maximo_llamadas=10,
    interprete=None,
    avance=None,
):
    if not 1 <= maximo_llamadas <= 200 or desde >= hasta:
        raise ValueError("presupuesto o intervalo no admisible")
    condicion, parametros = alcance_sql(clase, None, {})
    with conectar(cadena) as cnx, cnx.cursor() as cur:
        autorizar_operador(cur, actor)
        anotar(
            cur,
            "factores.relectura_consultada",
            actor=actor,
            detalle=dict(
                version=VERSION, aplicar=aplicar, desde=desde.isoformat(), hasta=hasta.isoformat()
            ),
        )
        consultas = ConsultasKPI(
            cur, condicion, parametros, (datetime(1970, 1, 1, tzinfo=UTC), hasta)
        )
        registros = consultas.factores_hibridos()
        sujetos = {r["estudiante"] for r in registros}
        permitidos = {s for s in sujetos if habilitado(cur, s)}
    registros = completar_trazas([r for r in registros if r["estudiante"] in permitidos])
    hilos = defaultdict(list)
    for r in registros:
        hilos[(r["estudiante"], r["sesion"])].append(r)
    elegibles = [r for r in registros if desde <= r["momento"] < hasta]
    reutilizados = sum(bool(lectura_guardada(r["analisis_semantico"], r["mensaje"])) for r in elegibles)
    pendientes = len(elegibles) - reutilizados
    llamadas_necesarias = sum(
        not lectura_guardada(r["analisis_semantico"], r["mensaje"])
        and not lectura_guardada(_metadatos(r["trazas"], "interpretación semántica experimental").get(
            "analisis_conductual", {}), r["mensaje"])
        for r in elegibles
    )
    resultado = dict(
        version=VERSION,
        candidatos=len(elegibles),
        pendientes=pendientes,
        pendientes_iniciales=pendientes,
        objetivo_llamadas=min(maximo_llamadas, llamadas_necesarias),
        llamadas=0,
        llamadas_finalizadas=0,
        guardados=0,
        reutilizados=reutilizados,
        lecturas_anteriores=sum(
            r.get("lectura_anterior", False)
            and not lectura_guardada(r["analisis_semantico"], r["mensaje"])
            for r in elegibles
        ),
        fallos=0,
        descartados=0,
        motivo_fallo=None,
        rechazos_por_motivo={},
        fase="revisando_historial",
        aplicar=aplicar,
        desde=desde.isoformat(),
        hasta=hasta.isoformat(),
    )
    if avance:
        avance(dict(resultado))
    detener = False
    invalidas_seguidas = 0
    for hilo in hilos.values():
        hilo.sort(key=lambda t: (t["momento"], t["historial"]))
        for i, r in enumerate(hilo):
            if not desde <= r["momento"] < hasta:
                continue
            if lectura_guardada(r["analisis_semantico"], r["mensaje"]):
                continue
            if not aplicar or detener:
                continue
            lectura = _metadatos(r["trazas"], "interpretación semántica experimental").get(
                "analisis_conductual", {}
            )
            if resultado["llamadas"] >= maximo_llamadas and not lectura_guardada(lectura, r["mensaje"]):
                continue
            with conectar(cadena) as cnx, cnx.cursor() as cur:
                autorizar_operador(cur, actor)
                if not habilitado(cur, r["estudiante"]):
                    continue
                cur.execute("SELECT id FROM historial_turno WHERE id=%s", (r["historial"],))
                if cur.fetchone() is None:
                    continue
            entrada = entrada_historica(hilo, i)
            if not lectura_guardada(lectura, r["mensaje"]):
                if resultado["llamadas"] >= maximo_llamadas:
                    continue
                # Una relectura fuera del chat puede esperar más que el tutor
                # interactivo. El plazo total sigue acotado y no hay reintentos.
                try:
                    interprete = interprete or InterpretacionDeepSeek(
                        factores_conductuales=True, solo_factores=True, tiempo_maximo_s=60
                    )
                except FalloInterpretacion as exc:
                    resultado["fallos"] += 1
                    resultado["motivo_fallo"] = exc.codigo
                    detener = True
                    continue
                resultado["llamadas"] += 1
                resultado["fase"] = "esperando_proveedor"
                if avance:
                    avance(dict(resultado))
                try:
                    respuesta = interprete.interpretar(entrada)
                    lectura = dict(
                        revision_prompt=RUBRICA['revision_prompt'],
                        version=VERSION,
                        modelo=respuesta.modelo,
                        observaciones=[o.como_dict() for o in respuesta.factores],
                        error=respuesta.error_factores,
                    )
                except Exception as exc:  # noqa: BLE001 — sólo códigos locales, sin texto del proveedor
                    resultado["fallos"] += 1
                    resultado["motivo_fallo"] = (
                        exc.codigo if isinstance(exc, FalloInterpretacion)
                        else "plazo_proveedor" if isinstance(exc, TimeoutError)
                        else "proveedor_sin_lectura"
                    )
                    motivo = getattr(exc, 'detalle_codigo', None) or resultado['motivo_fallo']
                    resultado['rechazos_por_motivo'][motivo] = resultado['rechazos_por_motivo'].get(motivo, 0) + 1
                    if resultado["motivo_fallo"] in {
                        "salida_conductual_invalida", "salida_semantica_invalida",
                        "salida_proveedor_invalida", "salida_truncada",
                    }:
                        resultado["descartados"] += 1
                        invalidas_seguidas += 1
                        detener = invalidas_seguidas >= 3
                    else:
                        detener = True
                    continue
                finally:
                    resultado["llamadas_finalizadas"] += 1
                    resultado["fase"] = "guardando_lectura"
                    if avance:
                        avance(dict(resultado))
            if not lectura_guardada(lectura, r["mensaje"]):
                resultado["fallos"] += 1
                resultado["motivo_fallo"] = "salida_conductual_invalida"
                resultado["descartados"] += 1
                invalidas_seguidas += 1
                detener = invalidas_seguidas >= 3
                continue
            invalidas_seguidas = 0
            huella = hashlib.sha256(
                json.dumps(
                    dict(version=VERSION, entrada=entrada), sort_keys=True, ensure_ascii=False
                ).encode()
            ).hexdigest()
            with conectar(cadena) as cnx, cnx.cursor() as cur:
                autorizar_operador(cur, actor)
                if not habilitado(cur, r["estudiante"]):
                    continue
                # La FK confirma existencia; bloquear historial evita carrera con supresión.
                cur.execute(
                    "SELECT id FROM historial_turno WHERE id=%s FOR KEY SHARE", (r["historial"],)
                )
                if cur.fetchone() is None:
                    continue
                if guardar(
                    cur,
                    r["historial"],
                    r["mensaje"],
                    lectura,
                    r["trazas"],
                    origen="relectura",
                    huella=huella,
                ):
                    anotar(
                        cur,
                        "factores.relectura_guardada",
                        actor=actor,
                        sujeto_afectado=r["estudiante"],
                        detalle=dict(version=VERSION, historial=r["historial"]),
                    )
                    resultado["guardados"] += 1
                    resultado["pendientes"] -= 1
            if avance:
                avance(dict(resultado))
    resultado['detenido'] = detener
    resultado["fase"] = "interrumpido" if detener else "terminado"
    if avance:
        avance(dict(resultado))
    return resultado
