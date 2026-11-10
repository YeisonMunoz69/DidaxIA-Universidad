/**
 * La información pública de privacidad · `D0` §10.2 y §10.6.
 *
 * ⚠️ **NO SUSTITUYE EL PROTOCOLO NI EL CONSENTIMIENTO VERSIONADO.**
 * `ESTADO-ACTUAL.md` §10.9 deja pendientes cuatro cosas que esos instrumentos
 * necesita y que aquí **no se inventan**: quién es el responsable del
 * tratamiento, qué dependencia lo asume, por qué canal se ejercen los derechos
 * y cuál es el plazo de retención aprobado. Donde falta el dato, el texto dice
 * que falta.
 *
 * ⚠️ **NI UNA CATEGORÍA DE DATO QUE EL SISTEMA NO TRATE.** Las siete que se
 * enumeran salen del inventario de persistencia (§2.3) y del recorrido ya
 * construido: identidad de Google, perfil con edad exacta, eventos de
 * consentimiento y asentimiento, conversaciones, métricas, evidencia del
 * representante y registros técnicos. Añadir una octava «por si acaso» sería
 * pedir autorización para algo que nadie decidió hacer.
 *
 * ES CONTENIDO Y NO MARCADO, A PROPÓSITO
 * ----------------------------------------
 * Los tres documentos tienen la misma estructura —secciones con título,
 * párrafos y listas— y un solo componente los pinta
 * (`piezas/DocumentoPublico.svelte`). Así el texto se revisa como texto: quien
 * lo corrija después de la respuesta institucional no tiene que leer Svelte, y
 * cambiar una frase no puede romper la maquetación de las otras dos páginas.
 *
 */
import { AUTORES, INSTITUCION, MARCA } from './proyecto.js';

export const PRIVACIDAD = Object.freeze({
  clave: 'privacidad',
  titulo: 'Privacidad y tratamiento de datos',
  actualizacion: 'Texto actualizado el 3 de noviembre de 2026. La versión institucional del aviso está pendiente de confirmación.',
  entradilla:
    `Qué información prevé tratar ${MARCA}, para qué, quién puede verla y qué puede ` +
    'pedir quien la aporta. Escrito para leerse, no para cubrirse.',

  secciones: Object.freeze([
    Object.freeze({
      id: 'quien',
      titulo: 'Quién trata los datos',
      parrafos: Object.freeze([
        `${MARCA} es un trabajo de grado desarrollado por ${AUTORES[0]} y ${AUTORES[1]} ` +
          `en la ${INSTITUCION}. Ellos son hoy quienes operan el sistema y responden por él.`,
        'Qué dependencia de la Institución actuará como responsable del tratamiento es una ' +
          'consulta institucional todavía abierta. Mientras no se resuelva, este documento no ' +
          'nombra a ningún responsable: hacerlo sería atribuirle una obligación a alguien que ' +
          'no la ha aceptado.'
      ])
    }),

    Object.freeze({
      id: 'datos',
      titulo: 'Qué datos se prevén',
      parrafos: Object.freeze([
        'Estas son las categorías previstas por el diseño actual del sistema. No todas ' +
          'aplican a todo el mundo: la evidencia del representante sólo existe para menores ' +
          'de edad, y las métricas sólo se generan al usar el tutor.'
      ]),
      lista: Object.freeze([
        'Identidad aportada por la cuenta institucional de Google: nombre, correo y el ' +
          'identificador estable que Google asigna. No se pide ni se guarda ninguna contraseña.',
        'Datos del perfil: la edad exacta declarada al primer ingreso, el programa académico ' +
          'y el resto de campos que el recorrido de entrada solicita.',
        'Eventos de consentimiento y de asentimiento: qué se decidió, sobre qué versión de qué ' +
          'documento y cuándo. Se guardan como hechos y no se sobrescriben.',
        'Conversaciones con el tutor e historial de sesiones: lo escrito, lo respondido y el ' +
          'hilo al que pertenece.',
        'Métricas académicas y conductuales derivadas del uso: avance, patrones de interacción ' +
          'y las señales que el motor pedagógico necesita para adaptar la ayuda.',
        'Para menores de 18 años, la autorización firmada del representante legal, en PDF, ' +
          'junto con la huella del archivo y el registro de su revisión.',
        'Registros técnicos de funcionamiento: marcas de tiempo, resultados de las peticiones ' +
          'y errores, necesarios para operar el servicio y para poder auditar lo que pasó.'
      ])
    }),

    Object.freeze({
      id: 'finalidades',
      titulo: 'Para qué',
      lista: Object.freeze([
        'Prestar la tutoría de cálculo diferencial y conservar el hilo de trabajo.',
        'Construir el perfil académico dentro del tutor y adaptar el nivel de ayuda.',
        'Permitir el seguimiento del docente sobre sus propias clases.',
        'Sostener la investigación del trabajo de grado: medir si el tutor ayuda y en qué.',
        'Cumplir las obligaciones de trazabilidad de las autorizaciones otorgadas.'
      ]),
      cierre:
        'Cada finalidad se declara en la versión del documento que se acepta. El tutor no ' +
        'trata datos para publicidad, no los vende y no los cede a terceros con fines comerciales.'
    }),

    Object.freeze({
      id: 'quien-ve',
      titulo: 'Quién puede verlos',
      parrafos: Object.freeze([
        'Hay que distinguir dos cosas que suelen confundirse: las personas que reciben los ' +
          'datos y las empresas que técnicamente pueden acceder a ellos.'
      ]),
      lista: Object.freeze([
        `Personas autorizadas: ${AUTORES[0]}, ${AUTORES[1]} y otras personas habilitadas según su función. ` +
          'El acceso depende de los permisos y del alcance de cada rol: un docente consulta sus clases y el investigador autorizado accede a las funciones que le corresponden. ' +
          'La relación completa de personas habilitadas y sus accesos efectivos requiere verificación operativa.',
        'Proveedores técnicos: el sistema se apoya en servicios externos —identidad, generación ' +
          'de texto, envío de correo, infraestructura— que pueden procesar datos aunque ninguna ' +
          'persona ajena sea destinataria de la investigación.'
      ]),
      cierre:
        'El inventario de esos proveedores está sin terminar. Qué empresa recibe cada clase de ' +
        'dato, en qué país, durante cuánto tiempo y con qué mecanismo de eliminación es una ' +
        'matriz que sigue pendiente de completar y verificar. La evaluación formativa descrita ' +
        'en la página de investigación no permite inferir por sí sola el destino, la retención ' +
        'o la eliminación de los datos. No se afirma que permanezcan en Colombia ni que ningún ' +
        'proveedor «no conserve» nada.'
    }),

    Object.freeze({
      id: 'menores',
      titulo: 'Si tienes menos de 18 años',
      lista: Object.freeze([
        'La edad exacta se pide en el primer ingreso, antes de decidir nada.',
        'Además de la autorización del titular hacen falta dos cosas independientes: tu propio ' +
          'asentimiento y la autorización firmada de tu representante legal.',
        'Hay siete días para aportar esa autorización. Durante ese plazo sólo quedan habilitados ' +
          'el perfil, las instrucciones y la carga del documento; el tutor sigue bloqueado.',
        'La revisa manualmente una persona autorizada, no un modelo automático, y sólo mira lo ' +
          'mínimo: identidad, relación, voluntad, firma, fecha e integridad del documento.',
        'Si se rechaza, el intento queda registrado. El plazo previsto para retirar los archivos es de 35 días; ' +
          'su ejecución requiere gestión operativa y no existe una tarea automática que garantice ese borrado. La familia conserva su propia copia.'
      ])
    }),

    Object.freeze({
      id: 'derechos',
      titulo: 'Qué puedes pedir',
      lista: Object.freeze([
        'Consultar y descargar lo que el sistema guarda sobre ti, desde la propia aplicación.',
        'Revocar tu autorización. Revocar bloquea el uso futuro del tutor y no borra hacia ' +
          'atrás: es una decisión distinta de la supresión.',
        'Solicitar la supresión de tus datos. Es un trámite aparte, con reautenticación, ' +
          'confirmación por correo, una ventana para cancelarlo y un plazo de resolución.',
        'Pedir que lo que se conserve para la investigación quede anonimizado de forma ' +
          'irreversible. Sólo se publican resultados agregados o anonimizados.'
      ])
    }),

    Object.freeze({
      id: 'retencion',
      titulo: 'Cuánto tiempo se conservan',
      parrafos: Object.freeze([
        'La aplicación declara como regla la fecha anterior entre seis meses después de la sustentación y 24 meses desde la recolección. ' +
          'La fecha de sustentación y la aplicación efectiva de la política requieren confirmación institucional y operativa.',
        'Para una autorización rechazada se prevé el retiro de los archivos a los 35 días mediante gestión operativa; ' +
          'no existe un borrado automático programado. Una solicitud de supresión tiene su propio trámite y plazo de resolución.'
      ])
    })
  ])
});
