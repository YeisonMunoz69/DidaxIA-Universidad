"""Catálogo único de nombres y significados para interfaz e informes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OperacionHumana:
    nombre: str
    categoria: str
    descripcion: str
    sensible: bool = False


_CATALOGO = {
    "recurso.publicado": OperacionHumana(
        "Publicación de recurso", "recursos",
        "Un investigador publicó una encuesta o presentación en cursos seleccionados.", True,
    ),
    "recurso.cursos_ampliados": OperacionHumana(
        "Ampliación de destinatarios de encuesta", "recursos",
        "Un investigador compartió el envío abierto con cursos o docentes adicionales conservando las preguntas y respuestas anteriores.", True,
    ),
    "recurso.estado_actualizado": OperacionHumana(
        "Cierre o archivo de recurso", "recursos",
        "Un investigador cerró o archivó un recurso sin eliminar las respuestas recibidas.", True,
    ),
    "recurso.destinatarios_retirados": OperacionHumana(
        "Retirada de destinatarios sin respuestas", "recursos",
        "Un investigador retiró invitaciones del envío activo sin borrar visitas, respuestas ni cambiar el contenido de la encuesta.", True,
    ),
    "recurso.metricas_consultadas": OperacionHumana(
        "Consulta de resultados de recursos", "recursos",
        "Un profesional autorizado consultó participación y resultados dentro del alcance de sus cursos.", True,
    ),
    "investigacion.directorio_consultado": OperacionHumana(
        "Consulta del directorio para reconstrucción", "acceso",
        "Un investigador autorizado buscó estudiantes para revisar conversaciones académicas.", True,
    ),
    "investigacion.conversaciones_listadas": OperacionHumana(
        "Consulta del historial para investigación", "acceso",
        "Un investigador autorizado filtró el historial académico de un estudiante por curso y periodo.", True,
    ),
    "investigacion.conversacion_consultada": OperacionHumana(
        "Lectura de conversación para investigación", "acceso",
        "Un investigador autorizado reconstruyó mensajes originales de una conversación académica.", True,
    ),
    "auditoria.consultada": OperacionHumana(
        "Consulta del historial de auditoría", "acceso",
        "Un investigador autorizado abrió o filtró el registro institucional.", True,
    ),
    "auditoria.informe_descargado": OperacionHumana(
        "Descarga del informe de auditoría", "informe",
        "Un investigador autorizado exportó un corte del historial institucional.", True,
    ),
    "correo.institucional_intentado": OperacionHumana(
        "Intento de correo institucional", "comunicación",
        "Un investigador autorizado confirmó un envío desde DidaxIa; el registro no conserva destinatarios ni contenido.", True,
    ),
    "generar_informe_kpi": OperacionHumana(
        "Vista previa de informe KPI", "informe",
        "Se generó una vista previa auditada de indicadores institucionales.", True,
    ),
    "descargar_informe_kpi": OperacionHumana(
        "Descarga de informe KPI", "informe",
        "Se descargó un informe institucional de indicadores.", True,
    ),
    "consultar_consumo_ia_institucional": OperacionHumana(
        "Consulta de consumo de IA", "KPI",
        "Un investigador autorizado consultó tokens, costos y horas de uso para un periodo, sin incluir identidades personales.", True,
    ),
    "exportar_consumo_ia_institucional": OperacionHumana(
        "Descarga de consumo de IA", "informe",
        "Un investigador autorizado exportó un corte de tokens y costos de IA, sin incluir identidades personales.", True,
    ),
    "rectificacion_edad.aplicada": OperacionHumana(
        "Rectificación de edad", "rectificación",
        "Se registró una corrección histórica de edad y su efecto de reconsentimiento.", True,
    ),
    "corregir_perfil_academico": OperacionHumana(
        "Corrección del perfil académico", "perfil",
        "Se corrigieron datos académicos sin reescribir el historial de actos.", True,
    ),
    "consultar_ficha_estudiante": OperacionHumana(
        "Consulta de ficha estudiantil", "acceso",
        "Un docente o investigador autorizado consultó una ficha académica.", True,
    ),
    "consultar_actividad_clase": OperacionHumana(
        "Consulta de actividad de clase", "acceso",
        "Un docente o investigador autorizado consultó métricas observables agregadas de una clase, sin texto de conversaciones.", True,
    ),
    "consultar_directorio_estudiantes": OperacionHumana(
        "Consulta del directorio estudiantil", "acceso",
        "Se consultó un directorio limitado por el alcance del rol.", True,
    ),
    "consultar_analitica_institucional": OperacionHumana(
        "Consulta de analítica institucional", "KPI",
        "Se consultaron señales institucionales para evaluación y supervisión.", True,
    ),
    "consultar_kpi_institucional": OperacionHumana(
        "Consulta de KPI institucionales", "KPI",
        "Se calcularon indicadores con un periodo y filtros declarados.", True,
    ),
    "consultar_equipo_institucional": OperacionHumana(
        "Consulta del equipo institucional", "acceso",
        "Se abrió el directorio de funciones institucionales.", True,
    ),
    "consultar_clase_institucional": OperacionHumana(
        "Consulta de clase institucional", "acceso",
        "Un investigador autorizado abrió el detalle de una clase sin incorporar textos de conversación.", True,
    ),
    "consultar_foto_estudiante_institucional": OperacionHumana(
        "Consulta de foto de perfil", "acceso",
        "Un investigador autorizado consultó una foto de perfil dentro de su alcance institucional.", True,
    ),
    "inventario.consultado": OperacionHumana(
        "Consulta del inventario personal", "acceso",
        "La persona consultó el inventario de datos asociado a su cuenta.", True,
    ),
    "asignar_facultad_profesional": OperacionHumana(
        "Asignación de facultad", "perfil",
        "Se vinculó una cuenta profesional con una facultad.", True,
    ),
    "invitacion.emitida": OperacionHumana(
        "Invitación emitida", "invitación",
        "Se creó una invitación institucional previa para un rol autorizado.", True,
    ),
    "invitacion.consultada": OperacionHumana(
        "Consulta de invitaciones", "invitación",
        "Se consultó el estado de las invitaciones institucionales.", True,
    ),
    "invitacion.revocada": OperacionHumana(
        "Invitación revocada", "invitación",
        "Se invalidó una invitación antes de su aceptación.", True,
    ),
    "invitacion.aceptada": OperacionHumana(
        "Invitación aceptada", "invitación",
        "Una cuenta institucional aceptó la invitación durante su primer inicio.", True,
    ),
    "rol.asignado": OperacionHumana(
        "Rol asignado", "rol", "Se concedió una función institucional auditable.", True,
    ),
    "rol.revocado": OperacionHumana(
        "Rol revocado", "rol", "Se retiró una función institucional sin borrar su historia.", True,
    ),
    "supresion.solicitada": OperacionHumana(
        "Solicitud de supresión", "supresión",
        "La persona abrió un trámite de supresión tras reautenticarse.", True,
    ),
    "supresion.cancelada": OperacionHumana(
        "Cancelación de supresión", "supresión",
        "La persona canceló su trámite dentro de la ventana permitida.", True,
    ),
    "retencion.fijada": OperacionHumana(
        "Política de retención fijada", "retención",
        "Dos propietarios autorizados aprobaron una política de conservación.", True,
    ),
    "evidencia.revisada": OperacionHumana(
        "Revisión de evidencia de representación", "evidencia",
        "Un investigador autorizado revisó la evidencia aportada por un representante.", True,
    ),
    "matricula.aprobada": OperacionHumana(
        "Matrícula aprobada", "matrícula",
        "Una solicitud de ingreso a clase fue aprobada y quedó registrada históricamente.", True,
    ),
    "matricula.rechazada": OperacionHumana(
        "Matrícula rechazada", "matrícula",
        "Una solicitud de ingreso a clase fue rechazada con su motivo.", True,
    ),
    "matricula.retirada_por_docente": OperacionHumana(
        "Retiro de una matrícula por el docente", "matrícula",
        "El docente responsable cerró la matrícula vigente de una persona en su clase; la cuenta y el historial se conservaron.", True,
    ),
    "clase.archivada": OperacionHumana(
        "Clase retirada de las vistas", "clase",
        "El responsable archivó una clase; sus matrículas y registros históricos se conservaron fuera de los KPI activos.", True,
    ),
    "reporte.usuario_creado": OperacionHumana(
        "Reporte técnico creado", "soporte",
        "Una persona registró una incidencia para soporte técnico. La auditoría no conserva el texto ni la captura.", True,
    ),
    "reporte.institucional_consultado": OperacionHumana(
        "Consulta de reportes técnicos", "soporte",
        "Un investigador autorizado abrió o filtró la bandeja privada de soporte.", True,
    ),
    "reporte.captura_consultada": OperacionHumana(
        "Consulta de captura de soporte", "soporte",
        "Un investigador autorizado abrió la captura privada de un reporte técnico.", True,
    ),
    "reporte.estado_actualizado": OperacionHumana(
        "Seguimiento de reporte técnico", "soporte",
        "Un investigador autorizado cambió el estado de una incidencia o dejó una respuesta para quien la reportó.", True,
    ),
    "notificacion.preferencia_actualizada": OperacionHumana(
        "Preferencia de correo actualizada", "comunicación",
        "Una persona cambió su propia suscripción a un aviso opcional por correo.", True,
    ),
    "pedagogia.sondeo_configurado": OperacionHumana(
        "Estado de sondeo configurado", "pedagogía",
        "Un investigador cambió la disponibilidad de un nodo didáctico; la auditoría conserva el nodo y el estado.", True,
    ),
    "pedagogia.umbral_sondeo_configurado": OperacionHumana(
        "Umbral de sondeos configurado", "pedagogía",
        "Un investigador cambió el número de intentos que activa un sondeo digital.", True,
    ),
    "consentimiento.decision_conjunta": OperacionHumana(
        "Decisión conjunta de consentimiento", "consentimiento",
        "Se registró atómicamente la decisión aplicable a la categoría vigente.", True,
    ),
    "consentimiento.revocado": OperacionHumana(
        "Consentimiento revocado", "consentimiento",
        "La persona retiró su autorización para participar en investigación.", True,
    ),
    "conversacion.consultada": OperacionHumana(
        "Consulta de conversación", "acceso",
        "Una persona autorizada abrió una conversación dentro de su alcance.", True,
    ),
    "factores.relectura_consultada": OperacionHumana(
        "Consulta del historial pendiente de análisis", "KPI",
        "Se consultaron los turnos elegibles para relectura conductual y las lecturas reutilizables.", True,
    ),
    "factores.relectura_confirmada": OperacionHumana(
        "Lote de análisis histórico confirmado", "KPI",
        "Un investigador confirmó el alcance y el máximo de llamadas a IA del lote.", True,
    ),
    "factores.relectura_guardada": OperacionHumana(
        "Lectura conductual histórica guardada", "KPI",
        "Se conservó una lectura complementaria versionada sin modificar el diálogo original.", True,
    ),
}

_CATEGORIAS = (
    ("consent", "consentimiento"), ("asent", "consentimiento"),
    ("informe", "informe"), ("kpi", "KPI"), ("perfil", "perfil"),
    ("matric", "matrícula"), ("invit", "invitación"), ("rol", "rol"),
    ("reten", "retención"), ("supres", "supresión"),
    ("evidencia", "evidencia"), ("rectificacion", "rectificación"),
    ("correo", "comunicación"), ("notificacion", "comunicación"),
    ("reporte", "soporte"), ("consumo", "KPI"),
    ("consult", "acceso"),
)

_ETIQUETAS = {
    "edad": "Edad declarada", "facultad": "Facultad", "programa": "Programa",
    "semestre": "Semestre", "rol": "Rol", "estado": "Estado",
    "version": "Versión", "clase": "Clase", "codigo": "Código KPI",
    "desde": "Desde", "hasta": "Hasta", "sha256": "SHA-256",
    "bytes": "Tamaño en bytes", "motivo": "Motivo",
    "destinatarios": "Cantidad de destinatarios", "adjuntos": "Cantidad de adjuntos",
    "bytes_adjuntos": "Tamaño total de adjuntos", "plantilla": "Plantilla de correo",
    "canal_configurado": "Canal de correo configurado",
    "correo_habilitado": "Correo habilitado",
    "reporte": "Número de reporte", "categoria": "Categoría",
    "ruta": "Pantalla", "con_captura": "Incluyó captura",
    "con_respuesta": "Incluyó respuesta", "pagina": "Página",
    "tamano": "Tamaño de página", "limite": "Límite de resultados",
    "zona": "Zona horaria", "formato": "Formato",
    "incluye_personas": "Incluye identidades personales",
    "incluye_texto": "Incluye texto de conversaciones",
    "filtros_activos": "Filtros activos", "campos": "Campos modificados",
    "alcance": "Alcance",
}


def describir_operacion(codigo: str) -> dict[str, Any]:
    codigo = str(codigo or "").strip()
    conocida = _CATALOGO.get(codigo)
    if conocida is not None:
        return {"codigo": codigo, **asdict(conocida), "catalogada": True}
    minuscula = codigo.lower()
    categoria = next((valor for fragmento, valor in _CATEGORIAS if fragmento in minuscula), "otra")
    return {
        "codigo": codigo,
        "nombre": f"Operación no catalogada: {codigo}",
        "categoria": categoria,
        "descripcion": "El hecho se conserva visible con su código original para trazabilidad.",
        "sensible": categoria not in {"otra", "KPI"},
        "catalogada": False,
    }


def diferencias(detalle: dict | None) -> list[dict[str, Any]]:
    detalle = detalle or {}
    antes = detalle.get("antes") if isinstance(detalle.get("antes"), dict) else {}
    despues = detalle.get("despues") if isinstance(detalle.get("despues"), dict) else {}
    return [
        {
            "campo": clave,
            "etiqueta": _ETIQUETAS.get(clave, clave.replace("_", " ").capitalize()),
            "antes": antes.get(clave),
            "despues": despues.get(clave),
        }
        for clave in sorted(set(antes) | set(despues))
        if antes.get(clave) != despues.get(clave)
    ]


def glosario(codigos: list[str] | tuple[str, ...] | set[str]) -> list[dict[str, Any]]:
    return [describir_operacion(codigo) for codigo in sorted(set(codigos))]


def codigos_de_categoria(categoria: str) -> tuple[str, ...]:
    categoria = str(categoria or "").strip()
    return tuple(sorted(
        codigo for codigo, descripcion in _CATALOGO.items()
        if descripcion.categoria == categoria
    ))
