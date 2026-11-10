"""Aplicación atómica, ordenada y bloqueada de las migraciones de DidaxIA."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycopg import sql

from infraestructura.migraciones.catalogo import Migracion, descubrir
from infraestructura.migraciones.linea_base import Estado, Inspeccion, inspeccionar

TABLA_LEDGER = "migracion_esquema"
ORIGEN_APLICADA = "aplicada"
ORIGEN_ADOPTADA = "adoptada"

# Durante el despliegue de `8d08548` estas dos migraciones llegaron en el
# orden contrario al que quedó canónico en `main`. Ambas estructuras se
# aplicaron correctamente; lo que difiere es exclusivamente la numeración del
# ledger. Las huellas hacen que esta reconciliación sólo reconozca ese estado
# histórico exacto y nunca convierta una divergencia desconocida en válida.
_LEDGER_TRANSITORIO_15_16 = (
    (15, "material-del-turno", "94a22c22a326ff43db4dd1b9f6c65002262397442099312157ae59fb534aced0"),
    (16, "foto-perfil", "2a8f9b12aaada5e4cd510ec968826c6419e7215b660b8350a75aa7bc70786235"),
)


class ErrorDeMigracion(RuntimeError):
    """La evolución no puede continuar sin cambiar el estado actual."""


class MigracionEnCurso(ErrorDeMigracion):
    """Otro proceso ya gobierna la evolución de este esquema."""


class HistorialIncompatible(ErrorDeMigracion):
    """El ledger no coincide con el catálogo versionado."""


class BaseExistenteSinLineaBase(ErrorDeMigracion):
    """Hay una línea histórica reconocible, pero nadie autorizó adoptarla."""


class EsquemaParcial(ErrorDeMigracion):
    """La base no representa una secuencia completa de migraciones."""


class MigracionRequiereDecision(ErrorDeMigracion):
    """La siguiente migración destruiría o reinterpretaría datos."""


@dataclass(frozen=True, slots=True)
class Resultado:
    adoptadas: tuple[int, ...]
    aplicadas: tuple[int, ...]


def _fijar_esquema(cur: Any, esquema: str) -> None:
    cur.execute(sql.SQL("SET LOCAL search_path TO {}, public").format(sql.Identifier(esquema)))


def _exigir_esquema(cur: Any, esquema: str) -> None:
    cur.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", (esquema,))
    if cur.fetchone() is None:
        raise ErrorDeMigracion(f"el esquema {esquema!r} no existe")


def _tomar_bloqueo(cur: Any, esquema: str) -> None:
    cur.execute(
        "SELECT pg_try_advisory_xact_lock(hashtext('didaxia:migraciones:v1'), hashtext(%s))",
        (esquema,),
    )
    if not cur.fetchone()[0]:
        raise MigracionEnCurso(f"ya hay una migración en curso para el esquema {esquema!r}")


def _crear_ledger(cur: Any, esquema: str) -> None:
    cur.execute(
        sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {}.{} (
                version     integer PRIMARY KEY CHECK (version > 0),
                nombre      text NOT NULL CHECK (btrim(nombre) <> ''),
                checksum    text NOT NULL CHECK (checksum ~ '^[0-9a-f]{{64}}$'),
                origen      text NOT NULL CHECK (origen IN ('aplicada', 'adoptada')),
                registrada_en timestamptz NOT NULL DEFAULT now()
            )
            """
        ).format(sql.Identifier(esquema), sql.Identifier(TABLA_LEDGER))
    )


def _leer_ledger(cur: Any, esquema: str) -> list[tuple[int, str, str, str]]:
    cur.execute(
        sql.SQL("SELECT version, nombre, checksum, origen FROM {}.{} ORDER BY version").format(
            sql.Identifier(esquema), sql.Identifier(TABLA_LEDGER)
        )
    )
    return list(cur.fetchall())


def _validar_ledger(filas: list[tuple[int, str, str, str]], catalogo: tuple[Migracion, ...]) -> int:
    for posicion, fila in enumerate(filas, start=1):
        version, nombre, checksum, origen = fila
        if version != posicion or version > len(catalogo):
            raise HistorialIncompatible(
                f"el ledger no es un prefijo continuo: se encontró la versión {version:02d}"
            )
        esperada = catalogo[version - 1]
        if nombre != esperada.nombre or checksum != esperada.checksum:
            raise HistorialIncompatible(
                f"la migración {version:02d} cambió de nombre o contenido después de registrarse"
            )
        if origen not in (ORIGEN_APLICADA, ORIGEN_ADOPTADA):
            raise HistorialIncompatible(f"origen no válido en la migración {version:02d}")
    return len(filas)


def _reconciliar_intercambio_15_16(
    cur: Any,
    esquema: str,
    filas: list[tuple[int, str, str, str]],
    catalogo: tuple[Migracion, ...],
) -> list[tuple[int, str, str, str]]:
    """Normaliza el único ledger transitorio publicado por `8d08548`.

    No vuelve tolerante el ledger. Reconoce nombres y checksums exactos,
    valida primero el prefijo 01--14 y exige las estructuras completas de las
    dos migraciones antes de reescribir sus dos filas dentro de la misma
    transacción. Si algo no coincide, la validación inmutable normal conserva
    el bloqueo.
    """
    if len(filas) != 16 or len(catalogo) < 16:
        return filas
    firma = tuple((version, nombre, checksum) for version, nombre, checksum, _ in filas[14:16])
    if firma != _LEDGER_TRANSITORIO_15_16:
        return filas

    _validar_ledger(filas[:14], catalogo)
    if any(fila[3] not in (ORIGEN_APLICADA, ORIGEN_ADOPTADA) for fila in filas[14:16]):
        raise HistorialIncompatible("el origen del ledger transitorio 15/16 no es válido")

    cur.execute(
        """
        SELECT
          EXISTS (
            SELECT 1 FROM information_schema.columns
             WHERE table_schema = %s AND table_name = 'persona'
               AND column_name = 'foto_perfil_referencia'
          ),
          EXISTS (
            SELECT 1
              FROM pg_constraint c
              JOIN pg_class t ON t.oid = c.conrelid
              JOIN pg_namespace n ON n.oid = t.relnamespace
             WHERE n.nspname = %s AND t.relname = 'persona'
               AND c.conname = 'persona_foto_perfil_referencia_valida'
          ),
          (
            SELECT count(*)
              FROM information_schema.columns
             WHERE table_schema = %s AND table_name = 'historial_material'
               AND column_name = ANY(%s)
          ),
          EXISTS (
            SELECT 1 FROM pg_indexes
             WHERE schemaname = %s AND tablename = 'historial_material'
               AND indexname = 'historial_material_por_mensaje'
          ),
          EXISTS (
            SELECT 1 FROM pg_indexes
             WHERE schemaname = %s AND tablename = 'historial_material'
               AND indexname = 'historial_material_por_obra'
          )
        """,
        (
            esquema,
            esquema,
            esquema,
            ["id", "historial", "orden", "fragmento", "obra", "relacion", "similitud"],
            esquema,
            esquema,
        ),
    )
    foto, restriccion_foto, columnas_material, indice_mensaje, indice_obra = cur.fetchone()
    if not all((foto, restriccion_foto, columnas_material == 7, indice_mensaje, indice_obra)):
        raise HistorialIncompatible(
            "el ledger transitorio 15/16 coincide, pero sus estructuras no están completas"
        )

    canonicas = {m.version: m for m in catalogo if m.version in (15, 16)}
    for version in (15, 16):
        migracion = canonicas[version]
        cur.execute(
            sql.SQL("UPDATE {}.{} SET nombre = %s, checksum = %s WHERE version = %s").format(
                sql.Identifier(esquema), sql.Identifier(TABLA_LEDGER)
            ),
            (migracion.nombre, migracion.checksum, version),
        )
    return _leer_ledger(cur, esquema)


def _registrar(cur: Any, esquema: str, migracion: Migracion, origen: str) -> None:
    cur.execute(
        sql.SQL(
            "INSERT INTO {}.{} (version, nombre, checksum, origen) VALUES (%s, %s, %s, %s)"
        ).format(sql.Identifier(esquema), sql.Identifier(TABLA_LEDGER)),
        (migracion.version, migracion.nombre, migracion.checksum, origen),
    )


def _adoptar(
    cur: Any,
    esquema: str,
    catalogo: tuple[Migracion, ...],
    estados: tuple[Inspeccion, ...],
) -> tuple[int, ...]:
    parciales = [estado for estado in estados if estado.estado == Estado.PARCIAL]
    if parciales:
        primero = parciales[0]
        raise EsquemaParcial(
            f"la migración {primero.version:02d} está aplicada parcialmente: {primero.detalle}"
        )

    adoptadas: list[int] = []
    ya_hubo_ausencia = False
    for estado in estados:
        if estado.estado == Estado.AUSENTE:
            ya_hubo_ausencia = True
            continue
        if ya_hubo_ausencia:
            raise EsquemaParcial(
                f"la migración {estado.version:02d} existe después de un hueco en la secuencia"
            )
        migracion = catalogo[estado.version - 1]
        _registrar(cur, esquema, migracion, ORIGEN_ADOPTADA)
        adoptadas.append(estado.version)
    return tuple(adoptadas)


def _proteger_migracion_04(cur: Any, esquema: str) -> None:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
             WHERE table_schema = %s AND table_name = 'registro_turno'
               AND column_name = 'identificador_sujeto'
        )
        """,
        (esquema,),
    )
    if cur.fetchone()[0]:
        return
    cur.execute(sql.SQL("SELECT count(*) FROM {}.registro_turno").format(sql.Identifier(esquema)))
    filas = cur.fetchone()[0]
    if filas:
        raise MigracionRequiereDecision(
            "la migración 04 purgaría "
            f"{filas} fila(s) de registro_turno; exige respaldo y decisión humana explícita"
        )


def ejecutar(
    conexion: Any,
    *,
    adoptar_existente: bool = False,
    directorio: Path | None = None,
    esquema: str = "public",
) -> Resultado:
    """Evoluciona el esquema y el ledger en una sola transacción.

    La conexión ya debe corresponder al entorno autorizado. El CLI de esta
    sesión sólo obtiene esa conexión mediante la barrera efímera de 2A.
    """
    catalogo = descubrir(directorio)
    adoptadas: tuple[int, ...] = ()
    aplicadas: list[int] = []

    with conexion.transaction(), conexion.cursor() as cur:
        _exigir_esquema(cur, esquema)
        _fijar_esquema(cur, esquema)
        _tomar_bloqueo(cur, esquema)
        _crear_ledger(cur, esquema)
        filas = _leer_ledger(cur, esquema)
        filas = _reconciliar_intercambio_15_16(cur, esquema, filas, catalogo)
        aplicadas_hasta = _validar_ledger(filas, catalogo)

        if not filas:
            estados = inspeccionar(cur, catalogo, esquema)
            existe_linea = any(estado.estado != Estado.AUSENTE for estado in estados)
            if existe_linea and not adoptar_existente:
                raise BaseExistenteSinLineaBase(
                    "la base contiene objetos de los SQL 01–10 pero no tiene ledger; "
                    "revise la inspección y repita con adopción explícita"
                )
            if existe_linea:
                adoptadas = _adoptar(cur, esquema, catalogo, estados)
                aplicadas_hasta = len(adoptadas)

        for migracion in catalogo[aplicadas_hasta:]:
            if migracion.version == 4:
                _proteger_migracion_04(cur, esquema)
            cur.execute(migracion.sql)
            _registrar(cur, esquema, migracion, ORIGEN_APLICADA)
            aplicadas.append(migracion.version)

    return Resultado(adoptadas=adoptadas, aplicadas=tuple(aplicadas))
