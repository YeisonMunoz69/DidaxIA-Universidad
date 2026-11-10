/**
 * Las condiciones públicas del servicio · `D0` §10.1 y §10.2.
 *
 * ⚠️ **NO ES ASESORÍA JURÍDICA NI UN CONTRATO.** Describe cómo funciona el
 * tutor y qué se espera de quien lo usa, en el idioma en que se le habla a un
 * estudiante. No fija cláusulas de responsabilidad, no limita acciones legales
 * y no sustituye el reglamento de la Institución.
 *
 * ⚠️ **NO PROMETE DISPONIBILIDAD.** El sistema falla cerrado cuando la base o
 * el almacenamiento crítico no responden (`ESTADO-ACTUAL.md` §10.4), y decirlo
 * es más honesto que un porcentaje de servicio que nadie mide.
 *
 * Mismo formato que `privacidad.js` y `investigacion.js`; lo pinta
 * `piezas/DocumentoPublico.svelte`. Ver la cabecera de `privacidad.js` para el
 * porqué de tener el texto como datos.
 *
 */
import { MARCA } from './proyecto.js';

export const CONDICIONES = Object.freeze({
  clave: 'condiciones',
  titulo: 'Condiciones del servicio',
  entradilla:
    `Cómo se entra a ${MARCA}, hasta dónde llega lo que hace y qué se espera de quien ` +
    'lo usa. Sin letra pequeña.',

  secciones: Object.freeze([
    Object.freeze({
      id: 'acceso',
      titulo: 'Acceso con cuenta institucional',
      lista: Object.freeze([
        'Se entra únicamente con la cuenta institucional de correo. No hay acceso anónimo ni ' +
        'registro con una cuenta personal.',
        'La identidad la verifica el proveedor de identidad de la Institución; el tutor sólo ' +
        'comprueba que el acceso venga de una cuenta del dominio institucional.',
        'La cuenta es personal. Quien la usa es responsable de lo que se haga desde ella.'
      ])
    }),

    Object.freeze({
      id: 'uso',
      titulo: 'Uso académico',
      parrafos: Object.freeze([
        `${MARCA} existe para acompañar el estudio del cálculo diferencial dentro de la ` +
        'actividad académica de la Institución. No es un servicio comercial y no se ofrece ' +
        'para otros fines.'
      ])
    }),

    Object.freeze({
      id: 'alcance',
      titulo: 'Qué alcance tiene el tutor, y qué no',
      lista: Object.freeze([
        'Es un sistema. Conversa, explica y propone caminos; no piensa por nadie ' +
        'y no reemplaza el trabajo de estudiar.',
        'No sustituye al docente. Lo acordado en clase manda sobre lo que diga el tutor.',
        'Puede equivocarse, incluso cuando se explica con seguridad. No hay garantía de que ' +
        'toda respuesta sea correcta.',
        'No califica, no evalúa y no toma decisiones sobre la situación académica de nadie.'
      ])
    }),

    Object.freeze({
      id: 'verificar',
      titulo: 'Verificar lo que importa',
      parrafos: Object.freeze([
        'Antes de usar un resultado del tutor en una entrega, un parcial o cualquier decisión ' +
        'académica, hay que comprobarlo. El tutor marca qué partes de una respuesta fueron ' +
        'verificadas por su motor y cuáles son narración: esa marca está para leerse.',
        'La comprobación simbólica se aplica a expresiones y operaciones admitidas por el sistema. ' +
        'No certifica toda la explicación, sus fuentes ni la corrección de cualquier resultado.'
      ])
    }),

    Object.freeze({
      id: 'materiales',
      titulo: 'Materiales y derechos de autor',
      parrafos: Object.freeze([
        'Los recursos del curso se ofrecen para apoyar el estudio en el contexto autorizado. ' +
        'Sus autores y titulares conservan los derechos que correspondan; acceder a un recurso ' +
        'no autoriza por sí solo a redistribuirlo o publicarlo.',
        'Las capturas públicas del recorrido usan ejemplos y datos ilustrativos. Las respuestas ' +
        'individuales y los materiales privados de la investigación tienen un tratamiento distinto.'
      ])
    }),

    Object.freeze({
      id: 'conducta',
      titulo: 'Lo que no se puede hacer',
      lista: Object.freeze([
        'Suplantar a otra persona, usar su cuenta o presentar como propia la identidad de un ' +
        'tercero.',
        'Intentar acceder a conversaciones, datos o pantallas de otras personas.',
        'Usar el tutor para producir trabajo que se presente como propio cuando la asignatura ' +
        'no lo permita. Esa regla la fija cada docente, no este documento.',
        'Someter el sistema a un uso abusivo o automatizado que degrade el servicio para los ' +
        'demás.'
      ])
    }),

    Object.freeze({
      id: 'sesion',
      titulo: 'Cuidado de la sesión',
      parrafos: Object.freeze([
        'La sesión queda abierta en el navegador desde el que se entra. Conviene cerrarla al ' +
        'terminar, sobre todo en un equipo compartido: el tutor guarda el historial de las ' +
        'conversaciones y quien tenga la sesión abierta puede leerlo.',
        'La sesión caduca sola tras un tiempo de inactividad y algunas acciones sensibles piden ' +
        'volver a identificarse aunque la sesión siga viva.'
      ])
    }),

    Object.freeze({
      id: 'disponibilidad',
      titulo: 'Disponibilidad y mantenimiento',
      parrafos: Object.freeze([
        'El servicio puede detenerse para mantenimiento, actualización o por un fallo. Cuando ' +
        'la base de datos o el almacenamiento no responden, el sistema se bloquea y lo dice: ' +
        'prefiere no funcionar antes que funcionar a medias sobre datos que no puede guardar.',
        'El acceso requiere una cuenta institucional habilitada y puede cambiar con la continuidad ' +
        'del proyecto. La página pública permite conocer sus funciones sin iniciar sesión. ' +
        'Para consultas o incidencias, utiliza los canales de contacto que aparecen al final de esta página.'
      ])
    }),

    Object.freeze({
      id: 'historial',
      titulo: 'El historial persiste',
      parrafos: Object.freeze([
        'Las conversaciones se guardan y siguen ahí en la siguiente sesión: es lo que permite ' +
        'retomar un ejercicio y lo que hace posible el seguimiento del docente sobre su clase.',
        'Cerrar sesión no borra el historial. Borrarlo es parte de la solicitud de supresión, ' +
        'que es un trámite distinto y está descrito en la página de privacidad.'
      ])
    }),

    Object.freeze({
      id: 'revocacion',
      titulo: 'Revocar y pedir la eliminación',
      lista: Object.freeze([
        'La autorización se puede revocar en cualquier momento desde la aplicación. Revocar ' +
        'bloquea el uso futuro del tutor y no borra hacia atrás.',
        'La eliminación de los datos es una solicitud aparte, con reautenticación, confirmación ' +
        'por correo, una ventana para cancelarla y un plazo de resolución.',
        'Quien revoca conserva el acceso a las páginas públicas y a la pantalla de sus propios ' +
        'datos, que es justo donde hace falta llegar después de revocar.'
      ])
    }),

    Object.freeze({
      id: 'versiones',
      titulo: 'Versiones de estas condiciones',
      parrafos: Object.freeze([
        'Cada cambio relevante produce una versión nueva, con su fecha. Cuando el sistema pida ' +
        'una autorización, registrará exactamente sobre qué versión se decidió, y esa versión ' +
        'la resuelve el servidor: no la elige el navegador ni quien acepta.',
        'La versión que registra una autorización la publica y resuelve el servidor; el navegador ' +
        'no puede elegirla ni sustituirla por el texto de esta página.'
      ])
    })
  ])
});
