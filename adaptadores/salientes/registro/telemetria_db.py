"""
telemetria_db.py — Escritura PostgreSQL de `evento_telemetria`
===============================================================

Un `INSERT ... ON CONFLICT (clave_idempotencia) DO NOTHING` con `RETURNING id`,
y una comprobación de referencias antes, dentro de la misma transacción.

Por qué el `ON CONFLICT` y no un `SELECT` previo
-------------------------------------------------------
Porque entre el `SELECT` y el `INSERT` cabe el segundo reintento. Dos peticiones
del mismo evento que se cruzan verían las dos «no existe» y las dos
insertarían: la restricción única las frenaría, pero una de las dos subiría como
error de integridad y el cliente lo leería como fallo. Con `ON CONFLICT` las dos
terminan bien y sólo una crea fila, que es lo que idempotente significa.

`RETURNING id` es lo que distingue los dos casos: la cláusula sólo devuelve fila
cuando el `INSERT` la creó, así que un `fetchone()` vacío **es** el duplicado.

Por qué las referencias se comprueban aquí y no en la ruta
------------------------------------------------------------------
El encargo pide rechazar «IDs fuera del alcance», y el alcance es una propiedad
de la base: qué clase existe y de quién es. Comprobarlo en la ruta, antes de
abrir la transacción, dejaría el mismo hueco que `autorizacion_sql.py` documenta
para los roles —entre la comprobación y el efecto cabe un cambio— y, sobre todo,
dejaría la regla fuera del repositorio: bastaría llamar al adaptador desde otro
sitio para saltársela.

Dos comprobaciones y no una:

1. **La clase existe.** Si no, el evento se rechaza; no se guarda con la clase
   en `NULL`, porque eso convertiría un identificador inventado en un evento
   «sin clase» perfectamente válido y contaminaría los agregados institucionales.
2. **El sujeto pertenece a esa clase, o la creó.** Un estudiante sólo puede
   declarar eventos de su propia clase; un docente, de las suyas. Sin esto,
   cualquier sesión autenticada podría inflar la telemetría de un curso ajeno.

⚠️ Lo que este adaptador NO hace
--------------------------------------
No audita. Registrar que alguien abrió el panel de fuentes no es una operación
administrativa de `EQ-023`, y anotar cada evento en `auditoria_operacion`
llenaría la tabla que más sobrevive con el uso ordinario del producto. Lo que sí
se audita es la **lectura institucional** de los indicadores, y eso ocurre en
`kpi_db.py`.


"""

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

if TYPE_CHECKING:  # pragma: no cover
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

#: La clase existe y este sujeto puede declararle eventos: o está matriculado en
#: ella, o es quien la creó. Una sola consulta y no dos, para que la respuesta
#: «no existe» y la respuesta «no es tuya» sean indistinguibles desde fuera: la
#: diferencia le diría a un cliente qué identificadores de clase son reales.
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
    """`PuertoTelemetria` sobre PostgreSQL. Append-only e idempotente."""

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
        """Adjunta clase y conversación que el navegador no conserva.

        El evento canónico `turno.respondido` se escribe antes de que la
        respuesta llegue a la interfaz. Correlacionarlo por sujeto y turno
        permite enriquecer el hecho sin confiar en una clase declarada por el
        cliente y sin llevar el perfil académico al estado global del navegador.
        """
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
        """Que la clase referida exista y admita a este sujeto.

        Un evento sin clase es legítimo —abrir un informe institucional no
        pertenece a ninguna—, así que la ausencia no se comprueba: lo que se
        comprueba es que una clase declarada sea real y propia.
        """
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
        """Una clave repetida sólo es éxito si identifica el mismo hecho.

        No se compara ``ocurrido_en``: un cliente que reintenta sin conservar
        su reloj recibe una nueva hora de servidor, pero el hecho sigue siendo
        el mismo por sujeto, tipo, referencias, versiones y metadatos.
        """
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
        """Conserva el descarte sin duplicar la clave opaca ni contenido."""
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
