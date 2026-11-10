"""Objetos cuya forma permite reconocer los SQL 01–10 ya aplicados."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Huella:
    dominios: tuple[str, ...] = ()
    columnas: tuple[tuple[str, tuple[str, ...]], ...] = ()
    indices: tuple[str, ...] = ()


HUELLAS: dict[int, Huella] = {
    1: Huella(
        dominios=("nivel_apos", "registro_duval", "modo_de_captura", "clave_de_obra"),
        columnas=(("fragmento", (
            "identificador", "texto", "nivel_apos", "registro_duval",
            "concepcion_asociada", "nodo_grafo", "obra", "pagina",
            "pagina_hasta", "captura", "representacion",
            "matematica_verificada", "cargado_en",
        )),),
        indices=("fragmento_por_nodo", "fragmento_por_similitud"),
    ),
    2: Huella(
        columnas=(
            ("perfil_afectivo", (
                "id", "identificador_sujeto", "subcomponente", "alcance", "turno",
                "señal", "regla_aplicada", "valor_previo", "valor_nuevo",
                "lambda_aplicado", "certeza", "vigencia", "creado_en",
            )),
            ("perfil_conceptual", (
                "id", "identificador_sujeto", "elemento", "turno", "estado_previo",
                "estado_nuevo", "evento_diagnostico", "creado_en",
            )),
            ("perfil_estrategico", (
                "id", "identificador_sujeto", "turno", "tipo_evento", "ventana",
                "contador", "ciclo_negativo", "creado_en",
            )),
        ),
        indices=(
            "perfil_afectivo_vigente", "perfil_conceptual_por_sujeto",
            "perfil_estrategico_por_sujeto",
        ),
    ),
    3: Huella(
        columnas=(("registro_turno", (
            "turno", "identificador_sesion", "ruta_archivo", "nivel_divulgacion",
            "latencia_total_ms", "creado_en",
        )),),
        indices=("registro_turno_por_sesion",),
    ),
    4: Huella(
        columnas=(("registro_turno", ("identificador_sujeto",)),),
        indices=("registro_turno_por_sujeto",),
    ),
    5: Huella(
        columnas=(("historial_turno", (
            "id", "turno", "identificador_sesion", "identificador_sujeto", "momento",
            "autor", "contenido", "degradado",
        )),),
        indices=("historial_turno_por_sujeto", "historial_turno_por_sesion"),
    ),
    6: Huella(
        columnas=(
            ("historial_bloque", (
                "id", "historial", "orden", "tipo", "contenido", "sello", "alternativo",
            )),
            ("historial_cita", ("id", "historial", "marca", "expresion")),
            ("historial_turno", (
                "nivel", "procedencia_origen", "procedencia_referencia",
            )),
        ),
        indices=("historial_bloque_por_mensaje", "historial_cita_por_mensaje"),
    ),
    7: Huella(
        columnas=(("consentimiento_usuario", (
            "identificador_sujeto", "correo", "decision", "edad", "momento",
        )),),
        indices=("consentimiento_usuario_correo",),
    ),
    8: Huella(
        columnas=(
            ("clase", ("id", "nombre", "creador", "codigo", "creada_en")),
            ("clase_matricula", ("clase", "identificador", "desde")),
        ),
        indices=("clase_creador", "clase_matricula_identificador"),
    ),
    9: Huella(
        columnas=(("cola_revision", (
            "id", "recibido", "urgencia", "clase", "tipo", "mensaje", "turno",
            "estado", "concepcion_candidata", "ansiedad_estimada",
        )),),
        indices=("cola_revision_pendientes",),
    ),
    10: Huella(
        columnas=(("solicitud_docente", (
            "id", "correo", "creada", "estado", "nota",
        )),),
        indices=("solicitud_docente_correo_estado",),
    ),
}
