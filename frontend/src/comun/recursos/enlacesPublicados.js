export function urlPublicacion(id, audiencia = 'estudiantes', origen = location.origin) {
  const ruta = audiencia === 'docentes' ? '/recursos/publicacion' : '/notificaciones';
  return `${origen}${ruta}?publicacion=${encodeURIComponent(id)}`;
}
