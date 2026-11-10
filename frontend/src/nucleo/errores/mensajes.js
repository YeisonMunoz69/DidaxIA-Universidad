/**
 * Los textos de error.
 *
 * En un solo archivo para poder revisarlos de una sentada. Ninguno culpa al
 * estudiante ni usa lenguaje técnico.
 *
 * LAS TRES REGLAS DE REDACCIÓN, y son comprobables leyendo:
 *
 *   1. El sujeto es el sistema, nunca el estudiante. «No pude» y no «enviaste
 *      mal». Un error de red no lo causó quien escribe.
 *   2. Sin jerga: nada de «500», «timeout», «token». Un código de estado no le
 *      dice nada a nadie y suena a que el problema es suyo por no entenderlo.
 *   3. Si hay algo que hacer, se dice; si no lo hay, no se finge que sí. Un
 *      «inténtalo más tarde» cuando el turno no es reintentable es peor que
 *      callar, porque invita a repetir lo que se acaba de interrumpir.
 *
 * NINGÚN TEXTO DE AQUÍ NOMBRA UN FILTRO, UN SUBSISTEMA NI UN COMPONENTE. El
 * contrato §9 lo prohíbe en la respuesta y sería absurdo que el cliente lo
 * filtrara ahí y lo escribiera aquí: «falló la verificación simbólica» deja
 * deducir la arquitectura de la detección igual de bien que un campo.
 *
 */

/**
 * Un texto por clase de fallo de `degradacion.js`.
 *
 * `titulo` encabeza; `detalle` explica qué pasó; `salida` dice qué puede hacer
 * el estudiante, o queda vacío cuando no hay nada honesto que ofrecerle.
 */
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

  /*
    ⚠️ ERA `sesion-vencida`, Y DECÍA UNA COSA FALSA LA MITAD DE LAS VECES.

    El backend responde 401 tanto a quien nunca entró como a quien se le
    acabaron los siete días de `EQ-020`, y este texto afirmaba lo segundo
    siempre. A quien acaba de abrir la aplicación por primera vez se le decía
    que su sesión había caducado — un error del sistema, aparentemente, cuando
    lo único que pasa es que todavía no ha entrado.

    El texto nuevo sirve a los dos casos sin mentir en ninguno, y la salida es
    la misma para ambos: entrar con la cuenta institucional.
  */
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

  /*
    `EQ-024` EN UN TEXTO. La regla que este mensaje sostiene es que un fallo de
    la base NUNCA se enseña como «no has autorizado», como una lista vacía ni
    como un formulario en blanco: eso sería afirmar algo que no se sabe.
  */
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

  // El estado seguro cuando no se sabe qué pasó. `RP-18`: no afirmar de más.
  desconocido: {
    titulo: 'Algo no salió bien',
    detalle: 'No pude preparar la respuesta y no sé decirte por qué.',
    salida: 'Puedes intentarlo otra vez.'
  }
});

/** El texto de una clase, con respaldo si la clase no estuviera. */
export function mensajeDe(clase) {
  return MENSAJES[clase] ?? MENSAJES.desconocido;
}
