export const PLANTILLAS_COMUNICACION = [
  { id: 'libre', categoria: 'Institucional', nombre: 'Mensaje institucional', asunto: '', mensaje: '' },
  { id: 'sesion', categoria: 'Investigación pedagógica', nombre: 'Convocatoria a sesión experimental',
    asunto: 'Invitación a una actividad de DidaxIa',
    mensaje: 'Te invitamos a una actividad de apoyo al estudio de límites con {cohorte}.\n\nLa docente y el equipo confirmarán el contenido, horario y condiciones antes de realizarla. Tu participación en la investigación es voluntaria.\n\nConfirma tu disponibilidad antes de {fecha_limite}.' },
  { id: 'refuerzo', categoria: 'Seguimiento pedagógico', nombre: 'Orientación y refuerzo de nodos',
    asunto: 'Una oportunidad de práctica: {nodo_didactico}',
    mensaje: 'Te proponemos revisar {nodo_didactico} y compartir con tu docente qué pasos te resultan difíciles.\n\nPuedes practicar con el tutor a tu ritmo y pedir una explicación cuando la necesites. Equivocarse forma parte del aprendizaje.' },
  { id: 'consentimiento', categoria: 'Ética y custodia de datos', nombre: 'Consentimiento informado PRISMA',
    asunto: 'Consulta tus autorizaciones en DidaxIa',
    mensaje: 'Puedes consultar tus autorizaciones y las condiciones de tratamiento de datos en «Mis datos».\n\nEste recordatorio no registra ni sustituye tu consentimiento. Si necesitas aclarar el alcance del estudio o retirar una autorización, consulta las opciones de esa pantalla y al equipo investigador.' },
  { id: 'retos', categoria: 'Novedades curriculares', nombre: 'Nuevos retos curriculares',
    asunto: 'Material de práctica para {cohorte}',
    mensaje: 'Te compartimos material de práctica sobre {nodo_didactico}, de acuerdo con el contenido trabajado en clase.\n\nRevisa el material adjunto y las indicaciones de la docente. Puedes comentar tus preguntas antes de {fecha_limite}.' },
  { id: 'entrevista', categoria: 'Experiencia de uso', nombre: 'Entrevista cualitativa de usabilidad',
    asunto: 'Queremos conocer tu experiencia con DidaxIa',
    mensaje: 'Te invitamos a una conversación breve y voluntaria sobre tu experiencia con DidaxIa.\n\nNos interesa conocer qué te ayudó, qué dificultó el uso y qué mejorarías. Contacta al equipo antes de {fecha_limite} para acordar un horario.' },
  { id: 'resuelta', categoria: 'Soporte', nombre: 'Incidencia técnica resuelta',
    asunto: 'Seguimiento de tu incidencia en DidaxIa',
    mensaje: 'Te compartimos el seguimiento de la incidencia que reportaste.\n\n[Describe la corrección que realmente se verificó y la versión en la que está disponible.]\n\nRevisa el resultado y avísanos si el problema continúa. Gracias por ayudarnos a mejorar.' },
  { id: 'mantenimiento', categoria: 'Operación del sistema', nombre: 'Aviso de mantenimiento programado',
    asunto: 'Mantenimiento programado de DidaxIa',
    mensaje: 'Tenemos previsto realizar un mantenimiento de DidaxIa en {fecha_limite}.\n\n[Indica el horario, duración estimada y servicios afectados, después de confirmarlos.]\n\nRecomendamos finalizar tu trabajo antes del horario anunciado. El equipo informará cuando el servicio esté disponible.' }
];

export const TONOS_CORREO = [
  { id: 'oxido', nombre: 'Óxido institucional', token: '--accent-main' },
  { id: 'azul', nombre: 'Azul DidaxIa', token: '--color-sky' },
  { id: 'esmeralda', nombre: 'Esmeralda', token: '--color-emerald' },
  { id: 'purpura', nombre: 'Púrpura investigación', token: '--email-purple' }
];

export function parsearDestinatarios(texto) {
  const unicos = new Map();
  for (const original of texto.split(/[\n;,]+/)) {
    const linea = original.trim();
    if (!linea) continue;
    const partes = linea.match(/^(.+?)\s*<([^<>]+)>$/);
    const correo = (partes?.[2] ?? linea).trim();
    unicos.set(correo.toLowerCase(), { nombre: (partes?.[1] ?? '').trim(), correo });
  }
  return [...unicos.values()];
}

export function faltantesDeVariables(asunto, mensaje, variables) {
  return [...new Set([...`${asunto}\n${mensaje}`.matchAll(/\{(cohorte|nodo_didactico|fecha_limite)\}/g)]
    .map((m) => m[1]))].filter((clave) => !variables[clave]?.trim());
}
