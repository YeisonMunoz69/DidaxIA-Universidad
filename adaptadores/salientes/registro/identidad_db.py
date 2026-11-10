from __future__ import annotations

from typing import TYPE_CHECKING, Any

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.base_postgres import (
    RepositorioPostgres,
    exigir_persona_activa,
    exigir_sin_supresion,
)
from dominio.modelo.identidad import (
    MAYORIA_DE_EDAD,
    Identidad,
    IdentidadInvalida,
    PerfilOnboarding,
    exigir_edad_admisible,
    exigir_semestre_admisible,
)
from dominio.modelo.menores import PLAZO_REPRESENTANTE_DIAS
from dominio.puertos.almacen import ReferenciaDesconocida
from dominio.puertos.gobierno import SupresionEnCurso

if TYPE_CHECKING:
    from datetime import datetime

_CAMPOS = """
    p.sujeto_google, p.correo, p.nombre, p.edad_declarada, p.facultad, p.programa, p.semestre,
    EXISTS (SELECT 1 FROM clase_matricula m WHERE m.identificador = p.sujeto_google)
"""


def perfil_desde_fila(fila: tuple) -> PerfilOnboarding:
    sujeto, correo, nombre, edad, facultad, programa, semestre, en_clase = fila
    return PerfilOnboarding(
        identidad=Identidad(sujeto_google=sujeto, correo=correo, nombre=nombre or ""),
        edad=edad,
        facultad=facultad or "",
        programa=programa or "",
        semestre=semestre,
        clase_vinculada=bool(en_clase),
    )

class AdaptadorIdentidadPostgres(RepositorioPostgres):

    def registrar(self, identidad: Identidad) -> PerfilOnboarding:
        with self._escritura() as cnx, cnx.cursor() as cur:
            existente = self._sin_actualizar_si_hay_supresion(cur, identidad)
            if existente is not None:
                return existente
            cur.execute(
                """
                INSERT INTO persona (sujeto_google, correo, nombre)
                VALUES (%s, %s, %s)
                ON CONFLICT (sujeto_google) DO UPDATE
                SET correo = EXCLUDED.correo,
                    nombre = CASE
                                 WHEN EXCLUDED.nombre <> '' THEN EXCLUDED.nombre
                                 ELSE persona.nombre
                             END,
                    actualizada_en = now()
                """,
                (identidad.sujeto_google, identidad.correo, identidad.nombre),
            )
            return self._leer(cur, identidad.sujeto_google)

    def _sin_actualizar_si_hay_supresion(
        self, cur, identidad: Identidad
    ) -> PerfilOnboarding | None:

        cur.execute(
            "SELECT 1 FROM persona WHERE sujeto_google = %s FOR UPDATE",
            (identidad.sujeto_google,),
        )
        if cur.fetchone() is None:
            return None
        try:
            exigir_sin_supresion(cur, identidad.sujeto_google)
        except SupresionEnCurso:

            return self._leer(cur, identidad.sujeto_google)
        return None

    def declarar_perfil(
        self,
        sujeto_google: str,
        *,
        edad: int | None = None,
        facultad: str = "",
        programa: str = "",
        semestre: int | None = None,
        motivo: str = "",
        origen: str = "onboarding_estudiante",
    ) -> PerfilOnboarding:

        exigir_edad_admisible(edad)
        exigir_semestre_admisible(semestre)

        if facultad:
            from dominio.modelo.oferta_academica import (
                exigir_oferta_valida,
            )

            facultad, programa = exigir_oferta_valida(facultad, programa)
        if origen not in {"onboarding_estudiante", "integracion_interna"}:
            raise IdentidadInvalida("origen de la corrección no admitido")
        with self._escritura() as cnx, cnx.cursor() as cur:

            exigir_persona_activa(cur, sujeto_google)
            cur.execute(
                """
                SELECT edad_declarada, facultad, programa, semestre,
                       EXISTS (SELECT 1 FROM clase_matricula m
                                WHERE m.identificador = persona.sujeto_google)
                  FROM persona
                 WHERE sujeto_google = %s
                 FOR UPDATE
                """,
                (sujeto_google,),
            )
            anterior = cur.fetchone()
            if anterior is None:
                raise ReferenciaDesconocida("esa persona no está registrada")

            (
                edad_anterior,
                facultad_anterior,
                programa_anterior,
                semestre_anterior,
                vinculada,
            ) = anterior
            edad_nueva = edad if edad is not None else edad_anterior
            facultad_nueva = facultad or facultad_anterior or ""
            programa_nuevo = programa or programa_anterior or ""
            semestre_nuevo = semestre if semestre is not None else semestre_anterior
            cambios = {
                "edad": edad_anterior is not None and edad_nueva != edad_anterior,
                "facultad": bool(facultad_anterior) and facultad_nueva != facultad_anterior,
                "programa": bool(programa_anterior) and programa_nuevo != programa_anterior,
                "semestre": semestre_anterior is not None and semestre_nuevo != semestre_anterior,
            }
            corrige = any(cambios.values())
            motivo = str(motivo or "").strip()
            if corrige and vinculada:
                raise IdentidadInvalida(
                    "la vinculación ya fue aprobada; la corrección debe seguir la vía gobernada"
                )
            if corrige and not 8 <= len(motivo) <= 500:
                raise IdentidadInvalida(
                    "el motivo de la corrección debe tener entre 8 y 500 caracteres"
                )

            rectificacion = None
            cambia_categoria = False
            if cambios["edad"]:
                era_menor = edad_anterior < MAYORIA_DE_EDAD
                sera_menor = edad_nueva < MAYORIA_DE_EDAD
                cambia_categoria = era_menor != sera_menor
                efecto_consentimiento = (
                    "reconsentimiento_por_cambio_de_categoria"
                    if cambia_categoria else "sin_cambio_de_categoria"
                )
                efecto_asentimiento = (
                    "pasa_a_requerir" if sera_menor and not era_menor
                    else "deja_de_requerir" if era_menor and not sera_menor
                    else "sin_cambio"
                )
                if cambia_categoria:
                    cur.execute(
                        """
                        INSERT INTO rectificacion_edad_transicion
                            (rectificacion, estado, actor, motivo)
                        SELECT r.id, 'sustituida', %s,
                               'sustituida por una rectificación posterior con cambio de categoría'
                          FROM rectificacion_edad r
                         WHERE r.sujeto_google = %s
                           AND r.reconsentimiento_necesario
                           AND EXISTS (SELECT 1 FROM rectificacion_edad_transicion t
                                        WHERE t.rectificacion = r.id
                                          AND t.estado = 'reconsentimiento_pendiente')
                           AND NOT EXISTS (SELECT 1 FROM rectificacion_edad_transicion t
                                            WHERE t.rectificacion = r.id
                                              AND t.estado IN ('reconsentida', 'sustituida'))
                        ON CONFLICT (rectificacion, estado) DO NOTHING
                        """,
                        (sujeto_google, sujeto_google),
                    )
                cur.execute(
                    """
                    INSERT INTO rectificacion_edad
                        (sujeto_google, valor_anterior, valor_nuevo, actor, motivo,
                         efecto_consentimiento, efecto_asentimiento,
                         reconsentimiento_necesario, origen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        sujeto_google, edad_anterior, edad_nueva, sujeto_google, motivo,
                        efecto_consentimiento, efecto_asentimiento, cambia_categoria, origen,
                    ),
                )
                rectificacion = int(cur.fetchone()[0])
                for estado in (
                    "registrada",
                    "reconsentimiento_pendiente" if cambia_categoria else "aplicada",
                ):
                    cur.execute(
                        "INSERT INTO rectificacion_edad_transicion "
                        "(rectificacion, estado, actor, motivo) VALUES (%s, %s, %s, %s)",
                        (
                            rectificacion,
                            estado,
                            sujeto_google,
                            motivo if estado == "registrada" else "",
                        ),
                    )
            cur.execute(
                """
                UPDATE persona
                   SET edad_declarada = COALESCE(%(edad)s, edad_declarada),
                       facultad = CASE
                                      WHEN btrim(%(facultad)s) <> '' THEN btrim(%(facultad)s)
                                      ELSE facultad
                                  END,
                       programa = CASE
                                      WHEN btrim(%(programa)s) <> '' THEN btrim(%(programa)s)
                                      ELSE programa
                                  END,
                       semestre = COALESCE(%(semestre)s, semestre),
                       representante_limite = CASE
                           WHEN edad_declarada IS NOT NULL
                            AND edad_declarada < %(mayoria)s
                            AND COALESCE(%(edad)s, edad_declarada) >= %(mayoria)s
                               THEN NULL
                           WHEN edad_declarada IS NOT NULL
                            AND edad_declarada >= %(mayoria)s
                            AND COALESCE(%(edad)s, edad_declarada) < %(mayoria)s
                               THEN now() + make_interval(days => %(plazo)s)
                           WHEN representante_limite IS NOT NULL THEN representante_limite
                           WHEN COALESCE(%(edad)s, edad_declarada) < %(mayoria)s
                               THEN now() + make_interval(days => %(plazo)s)
                           ELSE representante_limite
                       END,
                       actualizada_en = now()
                 WHERE sujeto_google = %(sujeto)s
                """,
                {
                    "edad": edad,
                    "facultad": facultad,
                    "programa": programa,
                    "semestre": semestre,

                    "mayoria": MAYORIA_DE_EDAD,
                    "plazo": PLAZO_REPRESENTANTE_DIAS,
                    "sujeto": sujeto_google,
                },
            )
            if cur.rowcount == 0:
                raise ReferenciaDesconocida("esa persona no está registrada")
            if corrige:
                if cambios["edad"]:
                    anotar(
                        cur,
                        "rectificacion_edad.aplicada",
                        actor=sujeto_google,
                        sujeto_afectado=sujeto_google,
                        detalle={
                            "rectificacion": rectificacion,
                            "cambio_categoria": cambia_categoria,
                            "reconsentimiento_necesario": cambia_categoria,
                            "origen": origen,
                            "motivo": motivo,
                            "antes": {"edad": edad_anterior},
                            "despues": {"edad": edad_nueva},
                        },
                    )
                if any(cambios[campo] for campo in ("facultad", "programa", "semestre")):
                    anotar(
                        cur,
                        "corregir_perfil_academico",
                        actor=sujeto_google,
                        sujeto_afectado=sujeto_google,
                        detalle={
                            "campos": [campo for campo in ("facultad", "programa", "semestre") if cambios[campo]],
                            "alcance": "antes_de_vinculacion",
                            "origen": origen,
                            "motivo": motivo,
                            "antes": {
                                "facultad": facultad_anterior,
                                "programa": programa_anterior,
                                "semestre": semestre_anterior,
                            },
                            "despues": {
                                "facultad": facultad_nueva,
                                "programa": programa_nuevo,
                                "semestre": semestre_nuevo,
                            },
                        },
                    )
            return self._leer(cur, sujeto_google)

    def consultar(self, sujeto_google: str) -> PerfilOnboarding | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"SELECT {_CAMPOS} FROM persona p WHERE p.sujeto_google = %s",
                (sujeto_google,),
            )
            fila = cur.fetchone()
            return perfil_desde_fila(fila) if fila else None

    def referencia_foto(self, sujeto_google: str) -> str | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT foto_perfil_referencia FROM persona WHERE sujeto_google = %s",
                (sujeto_google,),
            )
            fila = cur.fetchone()
            if fila is None:
                raise ReferenciaDesconocida("esa persona no está registrada")
            return fila[0]

    def cambiar_foto(self, sujeto_google: str, referencia: str | None) -> str | None:
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona_activa(cur, sujeto_google)
            cur.execute(
                "SELECT foto_perfil_referencia FROM persona WHERE sujeto_google = %s FOR UPDATE",
                (sujeto_google,),
            )
            anterior = cur.fetchone()[0]
            cur.execute(
                """
                UPDATE persona
                   SET foto_perfil_referencia = %s, actualizada_en = now()
                 WHERE sujeto_google = %s
                """,
                (referencia, sujeto_google),
            )
            return anterior

    def fijar_limite_representante(self, sujeto_google: str, limite: datetime) -> None:
        with self._escritura() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                UPDATE persona
                   SET representante_limite = %s, actualizada_en = now()
                 WHERE sujeto_google = %s
                """,
                (limite, sujeto_google),
            )
            if cur.rowcount == 0:
                raise ReferenciaDesconocida("esa persona no está registrada")

    def _leer(self, cur: Any, sujeto_google: str) -> PerfilOnboarding:
        cur.execute(
            f"SELECT {_CAMPOS} FROM persona p WHERE p.sujeto_google = %s",
            (sujeto_google,),
        )
        return perfil_desde_fila(cur.fetchone())
