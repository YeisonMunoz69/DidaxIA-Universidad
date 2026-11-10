from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from adaptadores.salientes.registro.autorizacion_sql import (
    exigir_investigador_administrador,
)
from adaptadores.salientes.registro.base_postgres import RepositorioPostgres
from dominio.modelo.telemetria import ConflictoDeIdempotencia, EventoInvalido

if TYPE_CHECKING:
    from dominio.modelo.telemetria import EventoTelemetria

_INSERTAR = """
INSERT INTO evento_telemetria (
    clave_idempotencia, tipo, origen, ocurrido_en, identificador_sujeto,
    contexto_de_uso, clase, conversacion, turno, concepto,
    version_corpus, version_modelo, metadatos
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
ON CONFLICT (clave_idempotencia) DO NOTHING
RETURNING id
"""


_ALCANCE_DE_LA_CLASE = """
SELECT 1
  FROM clase c
 WHERE c.id = %s
   AND (c.creador = %s
        OR EXISTS (SELECT 1 FROM clase_matricula m
                    WHERE m.clase = c.id AND m.identificador = %s))
"""

_CLASE_EXISTE = "SELECT 1 FROM clase WHERE id = %s"

_EVENTO_POR_CLAVE = """
SELECT tipo, identificador_sujeto, contexto_de_uso, clase, conversacion, turno,
       concepto, version_corpus, version_modelo, metadatos
  FROM evento_telemetria
 WHERE clave_idempotencia = %s
"""

_CONTEXTO_DEL_TURNO = """
SELECT clase, conversacion
  FROM evento_telemetria
 WHERE tipo = 'turno.respondido'
   AND identificador_sujeto = %s
   AND turno = %s
 ORDER BY registrado_en DESC
 LIMIT 1
"""

_ANOTAR_INCIDENCIA = """
INSERT INTO incidencia_telemetria (
    identificador_sujeto, clase, tipo, categoria, codigo, huella_clave
) VALUES (%s, %s, %s, %s, %s, %s)
"""


class AdaptadorTelemetriaPostgres(RepositorioPostgres):

    def registrar(
        self, evento: EventoTelemetria, *, alcance_institucional: bool = False
    ) -> bool:
        conflicto = False
        with self._conexion() as cnx, cnx.cursor() as cur:
            if alcance_institucional:
                exigir_investigador_administrador(cur, evento.identificador_sujeto)
            evento = self._completar_contexto_del_turno(cur, evento)
            self._exigir_clase_en_alcance(cur, evento, alcance_institucional)
            cur.execute(_INSERTAR, self._parametros(evento))
            creado = cur.fetchone() is not None
            if not creado:
                conflicto = not self._es_el_mismo_evento(cur, evento)
                self._anotar_incidencia(
                    cur,
                    evento,
                    "conflicto_idempotencia" if conflicto else "duplicado",
                    "clave_reutilizada" if conflicto else "reintento_identico",
                )
            cnx.commit()
        if conflicto:
            raise ConflictoDeIdempotencia(
                "la clave de idempotencia ya identifica un evento diferente"
            )
        return creado

    @staticmethod
    def _completar_contexto_del_turno(cur: Any, evento: EventoTelemetria) -> EventoTelemetria:
        if not evento.turno or (evento.clase is not None and evento.conversacion is not None):
            return evento
        cur.execute(
            _CONTEXTO_DEL_TURNO,
            (evento.identificador_sujeto, evento.turno),
        )
        fila = cur.fetchone()
        if fila is None:
            return evento
        return replace(
            evento,
            clase=evento.clase or fila[0],
            conversacion=evento.conversacion or fila[1],
        )

    def _exigir_clase_en_alcance(
        self, cur: Any, evento: EventoTelemetria, alcance_institucional: bool
    ) -> None:

        if evento.clase is None:
            return
        if alcance_institucional:
            cur.execute(_CLASE_EXISTE, (evento.clase,))
            if cur.fetchone() is not None:
                return
            raise EventoInvalido("la clase del evento no existe")
        cur.execute(
            _ALCANCE_DE_LA_CLASE,
            (evento.clase, evento.identificador_sujeto, evento.identificador_sujeto),
        )
        if cur.fetchone() is None:
            raise EventoInvalido(
                "la clase del evento no existe o no está en el alcance de quien lo declara"
            )

    def _es_el_mismo_evento(self, cur: Any, evento: EventoTelemetria) -> bool:
        cur.execute(_EVENTO_POR_CLAVE, (evento.clave_idempotencia,))
        fila = cur.fetchone()
        esperado = (
            evento.tipo.value,
            evento.identificador_sujeto,
            evento.contexto_de_uso.value,
            evento.clase,
            evento.conversacion,
            evento.turno,
            evento.concepto,
            evento.version_corpus,
            evento.version_modelo,
            evento.metadatos,
        )
        return fila is not None and tuple(fila) == esperado

    @staticmethod
    def _anotar_incidencia(
        cur: Any,
        evento: EventoTelemetria,
        categoria: str,
        codigo: str,
    ) -> None:

        huella = hashlib.sha256(evento.clave_idempotencia.encode("utf-8")).hexdigest()
        cur.execute(
            _ANOTAR_INCIDENCIA,
            (
                evento.identificador_sujeto,
                evento.clase,
                evento.tipo.value,
                categoria,
                codigo,
                huella,
            ),
        )

    @staticmethod
    def _parametros(evento: EventoTelemetria) -> tuple:
        return (
            evento.clave_idempotencia,
            evento.tipo.value,
            evento.origen.value,
            evento.ocurrido_en,
            evento.identificador_sujeto,
            evento.contexto_de_uso.value,
            evento.clase,
            evento.conversacion,
            evento.turno,
            evento.concepto,
            evento.version_corpus,
            evento.version_modelo,
            json.dumps(evento.metadatos, ensure_ascii=False),
        )
