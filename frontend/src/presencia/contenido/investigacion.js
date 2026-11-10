/**
 * Qué se investiga con DidaxIa, y qué se hará con lo que se observe.
 *
 * ⚠️ **NO PROMETE PUBLICAR NINGÚN PDF.** `ESTADO-ACTUAL.md` §10.7 es
 * explícito: que una obra sea descargable no demuestra autorización para
 * redistribuirla, y cada una necesita evidencia individual de licencia. Aquí
 * se describe el aporte de digitalización sin comprometer una biblioteca
 * pública que hoy no se puede sostener.
 *
 * ⚠️ **LA PARTICIPACIÓN ES VOLUNTARIA Y SE DICE DOS VECES**: al describir el
 * piloto y al describir los datos. Un texto de investigación que sólo lo
 * menciona en una nota final está escrito para el expediente, no para quien
 * decide.
 *
 * Mismo formato que `privacidad.js` y `condiciones.js`; lo pinta
 * `piezas/DocumentoPublico.svelte`.
 *
 */
import { AUTORES, INSTITUCION, MARCA, MATERIALES_ESTUDIO } from './proyecto.js';

export const INVESTIGACION = Object.freeze({
  clave: 'investigacion',
  titulo: 'La investigación',
  entradilla:
    `Qué pregunta responde ${MARCA}, qué se observó en su evaluación formativa y cuáles ` +
    'son los límites de lo que puede concluirse.',

  secciones: Object.freeze([
    Object.freeze({
      id: 'objetivo',
      titulo: 'El objetivo',
      parrafos: Object.freeze([
        `${MARCA} es un trabajo de grado de ${AUTORES[0]} y ${AUTORES[1]} en la ` +
        `${INSTITUCION}. Parte de una revisión sistemática de literatura sobre tutores ` +
        'inteligentes y de lo que esa revisión dejó como requisitos.',
        'El tutor ajusta la ayuda según la solicitud, la tarea activa y los intentos registrados. ' +
        'La evaluación formativa documentó su uso, la experiencia declarada y la valoración docente de contenido y funciones seleccionados.'
      ])
    }),

    Object.freeze({
      id: 'piloto',
      titulo: 'La evaluación formativa',
      parrafos: Object.freeze([
        'La evaluación formativa universitaria se realizó entre el 16 de septiembre y el 9 de ' +
        'octubre de 2026 con participación voluntaria; el corte acumulado de datos fue el 10 de octubre. ' +
        'La revisión de dos docentes fue posterior. El análisis reunió 251 conversaciones y 1.473 pares completos de 113 personas.',
        'La unión de personas con conversación o encuesta elegible fue de 117. De 1.602 registros brutos se seleccionaron ' +
        '1.474 elegibles y 1.473 pares completos, cada uno con un mensaje del estudiante y la respuesta registrada del tutor.',
        'En el ítem de satisfacción F03.5 hubo 62 respuestas numéricas favorables entre 82 ' +
        '(75,61%). Se excluyó una respuesta no numérica de los 83 formularios posteriores. ' +
        'En 57 pares cronológicos de autopercepción sobre explicar una derivada en un punto, ' +
        'las respuestas de 32 aumentaron, 20 quedaron iguales y cinco disminuyeron; son cambios en las respuestas al ítem, no una medición de aprendizaje.',
        'Participar es voluntario. Quien no acepte el tratamiento de sus datos conserva las ' +
        'páginas públicas, puede volver a leer y decidir más tarde, y no queda en desventaja ' +
        'académica por ello: el tutor no califica y no reporta la participación como nota.'
      ])
    }),

    Object.freeze({
      id: 'menores',
      titulo: 'Participantes menores de 18 años',
      parrafos: Object.freeze([
        'Un estudiante menor de edad participa sólo cuando se cumplen dos cosas independientes: ' +
        'su propio asentimiento —se le pregunta a él, no se decide por él— y la autorización ' +
        'firmada de su representante legal.',
        'La autorización se revisa manualmente y con el mínimo de información necesaria. ' +
        'Ningún modelo automático decide sobre su validez. El detalle está en la página de ' +
        'privacidad.'
      ])
    }),

    Object.freeze({
      id: 'datos',
      titulo: 'Qué se usa de lo que ocurre en el tutor',
      lista: Object.freeze([
        'Las interacciones con el tutor: qué se preguntó, qué se respondió y cómo avanzó el ' +
        'hilo de trabajo.',
        'Las métricas derivadas del uso: avance, patrones de interacción y las señales que el ' +
        'motor pedagógico calcula para ajustar la ayuda.',
        'Los datos del perfil que hacen falta para interpretar lo anterior: programa y edad.'
      ]),
      cierre:
        'Nada de esto se usa para evaluar a una persona. Se usa para evaluar el tutor.'
    }),

    Object.freeze({
      id: 'docentes',
      titulo: 'Qué ve el docente',
      parrafos: Object.freeze([
        'Un docente ve únicamente lo que corresponde a sus propias clases, y sólo si tiene el ' +
        'permiso vigente para hacerlo. No ve los cursos de otros docentes ni el conjunto del ' +
        'piloto.',
        'El seguimiento docente existe para acompañar al grupo, no para vigilar a un ' +
        'estudiante: la aplicación no le muestra al estudiante ningún perfil conductual, y esa ' +
        'ausencia es una decisión del diseño y no un pendiente.'
      ])
    }),

    Object.freeze({
      id: 'publicacion',
      titulo: 'Qué se publica',
      parrafos: Object.freeze([
        'Los resultados se publican únicamente de forma agregada o anonimizada de manera ' +
        'irreversible. No se publican conversaciones individuales, ni nombres, ni correos, ni ' +
        'nada que permita reidentificar a una persona.',
        'El paquete contiene tablas agregadas y un script de comprobación. Las conversaciones individuales, las encuestas vinculadas y los formularios docentes individuales permanecen restringidos.'
      ]),
      enlace: Object.freeze({ texto: 'Ver materiales del estudio', href: MATERIALES_ESTUDIO })
    }),

    Object.freeze({
      id: 'limitaciones',
      titulo: 'Limitaciones que conviene conocer',
      lista: Object.freeze([
        'Es un estudio de un solo contexto, con un grupo pequeño y durante un periodo corto. ' +
        'Lo que se observe no se generaliza a otras instituciones ni a otras asignaturas.',
        'El modelo generador puede equivocarse. El sistema comprueba determinadas expresiones y operaciones. El piloto no estimó la exactitud matemática global del tutor.',
        'Quienes desarrollan el sistema son los mismos que lo evalúan. Se declara porque es una ' +
        'limitación del diseño, no un detalle administrativo.',
        'La evaluación no utilizó una medida común de logro que permita atribuir un cambio al ' +
        'tutor. La satisfacción y la autopercepción describen respuestas de participantes; no ' +
        'demuestran un efecto causal ni aprendizaje.'
      ])
    }),

    Object.freeze({
      id: 'recursos',
      titulo: 'Digitalización y material de apoyo',
      parrafos: Object.freeze([
        'El tutor puede recuperar pasajes y mostrar su procedencia. Una referencia permite consultar el material de apoyo. Por sí sola no verifica toda la explicación.',
        'Que ese material esté digitalizado no autoriza a redistribuirlo. Cada obra necesita ' +
        'evidencia individual de licencia, dominio público o permiso expreso, y mientras esa ' +
        'evidencia no exista sólo se muestran sus datos de referencia y los fragmentos que el ' +
        'uso académico ampara. Aquí no se publica ningún documento completo por ahora.'
      ])
    })
  ])
});
