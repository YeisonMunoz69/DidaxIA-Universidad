
export const MENSAJES = Object.freeze({
  'sin-red': {
    titulo: 'No hay conexión',
    detalle: 'No consigo llegar al servidor del curso. Puede ser la red de aquí.',
    salida: 'Cuando vuelva la conexión, tu mensaje sigue escrito.'
  },

  'servidor-caido': {
    titulo: 'El sistema no está respondiendo',
    detalle: 'El servicio no está disponible en este momento.',
    salida: 'Vuelve a intentarlo en un rato.'
  },

  'tiempo-agotado': {
    titulo: 'La respuesta está tardando demasiado',
    detalle: 'Dejé de esperar para no tenerte en blanco sin saber qué pasa.',
    salida: 'Puedes intentarlo otra vez.'
  },

  'sin-sesion': {
    titulo: 'Necesitas entrar con tu cuenta institucional',
    detalle:
      'Esta parte del tutor sólo está disponible con la cuenta del dominio de la universidad.',
    salida: 'Entra con Google desde el botón de la aplicación.'
  },

  'sin-permiso': {
    titulo: 'Esta parte no es de tu cuenta',
    detalle: 'Tu cuenta no tiene acceso a lo que se pidió.',
    salida: ''
  },

  mantenimiento: {
    titulo: 'El servicio está en mantenimiento',
    detalle:
      'No puedo consultar ni guardar nada ahora mismo, así que prefiero no enseñarte un estado que no puedo comprobar.',
    salida: 'Lo que hayas escrito se conserva. Vuelve a intentarlo en un momento.'
  },

  'peticion-invalida': {
    titulo: 'Hay un dato que no puedo aceptar',
    detalle: 'Alguno de los valores enviados no es admisible.',
    salida: 'Revisa lo marcado y vuelve a enviarlo.'
  },

  conflicto: {
    titulo: 'No pude registrar esa decisión',
    detalle: 'El sistema no admite esa operación en el estado actual.',
    salida: 'Vuelve a cargar el estado para ver cómo quedó.'
  },

  retirada: {
    titulo: 'Esa opción ya no existe',
    detalle: 'Se retiró y fue sustituida por otro camino dentro de la aplicación.',
    salida: ''
  },

  'archivo-rechazado': {
    titulo: 'No pude aceptar ese archivo',
    detalle: 'El archivo no cumple lo que se pide para la autorización.',
    salida: 'Comprueba que sea un PDF válido y vuelve a intentarlo.'
  },

  'turno-interrumpido': {
    titulo: 'No pude completar la respuesta',
    detalle: 'Empecé a prepararla y me quedé a medias.',
    salida: 'Puedes intentarlo otra vez.'
  },

  desconocido: {
    titulo: 'Algo no salió bien',
    detalle: 'No pude preparar la respuesta y no sé decirte por qué.',
    salida: 'Puedes intentarlo otra vez.'
  }
});

export function mensajeDe(clase) {
  return MENSAJES[clase] ?? MENSAJES.desconocido;
}
