/**
 * La tabla de rutas.
 *
 * Camino, cómo se carga su componente, y el árbol que la puede ver.
 *
 * LAS RUTAS NO SE INVENTAN AQUÍ. Salen de la figura `D-20`, que ya declaró la
 * navegación de cada rol, y `07-Estructura-del-Frontend.md` §9 y §10 las
 * convirtió en archivos. Esta tabla es la tercera copia de la misma decisión y
 * por eso no añade ninguna: si falta una ruta, se añade en `D-20` primero.
 *
 * `arbol` ES EL CAMPO QUE PROTEGE ALGO, Y DESDE C2B `roles` ES EL SEGUNDO
 * -------------------------------------
 * `DD-04` decidió que docente e investigador comparten aplicación y que la
 * frontera que importa es **estudiante frente a no-estudiante**. Por eso la
 * tabla no lista roles uno a uno sino el árbol al que pertenece cada ruta: el
 * día que aparezca un cuarto rol, lo que no puede fallar es de qué lado del
 * vector conductual cae, y con una lista de roles ese fallo se comete por
 * omisión.
 *
 * Eso **sigue siendo cierto** y por eso `arbol` no desaparece. Lo que C2B añadió
 * es un caso que aquel diseño no cubría: una pantalla del árbol no-estudiante
 * que no es de las dos personas que lo comparten. `/evidencias` la reserva
 * `EQ-023` a un investigador con rol vigente, y una docente no tiene por qué
 * revisar autorizaciones de representantes legales.
 *
 * `roles` es una **allowlist opcional dentro del árbol**, no un sustituto suyo:
 * una ruta sin ella se comporta exactamente como antes. Y es allowlist y no
 * «todos menos docente» porque un rol nuevo no debe heredar esta pantalla por
 * omisión.
 *
 * Y ESTO NO ES SEGURIDAD, ES CORTESÍA
 * ------------------------------------
 * §11: la negativa efectiva la ejerce el servidor, siempre. Esta tabla evita
 * que alguien llegue a una pantalla que el servidor le va a negar; si fuera lo
 * único que separa los dos árboles, bastaría abrir las herramientas del
 * navegador para saltárselo.
 *
 */
import { CAMINOS, inicioDe } from './caminos.js';
import { ESPACIO_TUTOR, arbolDe, normalizarEspacio } from './espacios.js';
import { esEstudiante } from '../nucleo/sesion/rol.js';

export { inicioDe } from './caminos.js';
/**
 * Los componentes se cargan CUANDO SE ENTRA, no al arrancar.
 *
 * Dos motivos, y el segundo es del proyecto y no de rendimiento:
 *
 *   1. El navegador de un estudiante **no descarga siquiera** el árbol del
 *      docente. `VectorConductual.svelte` vive bajo `docente/` para que un
 *      import distraído se vea raro al leerlo; con carga diferida, además, su
 *      código no llega a la máquina de quien no debe verlo. La barrera deja de
 *      depender solo de la disciplina de quien escribe.
 *   2. Esta tabla queda siendo **datos**, así que se puede comprobar sin
 *      compilar un solo componente — que es lo que hace
 *      `pruebas/contrato/separacion-de-arboles.prueba.js`.
 */

/**
 * Los dos árboles. `estudiante` · `no-estudiante`.
 *
 * `abierta` marca **el recorrido retenido**: la pantalla que se alcanza en
 * cualquier estado de acceso que no sea `habilitado`, y que por eso no aparece
 * como un destino más de la navegación. Es una sola ruta y tiene que serlo: si
 * hubiera dos, habría un camino por el que llegar al recorrido sin pasar por su
 * composición de pasos.
 *
 * ⚠️ **`abierta` ya no significa «se ve con el consentimiento sin resolver».**
 * Qué se alcanza en cada estado no lo decide un campo de esta tabla sino la
 * allowlist explícita de `nucleo/sesion/acceso.js`, que sale de la tabla
 * aprobada de `EQ-016`. Escrito como una marca por ruta, un estado nuevo habría
 * heredado los permisos del anterior sin que nadie lo decidiera.
 */
/*
 * `icono` ES PRESENTACIÓN Y NO AÑADE NINGUNA RUTA.
 *
 * La cabecera de arriba dice que las rutas salen de `D-20` y que aquí no se
 * inventa ninguna. Sigue siendo cierto: este campo no crea ni quita caminos,
 * solo nombra el trazo con el que se dibuja cada uno. Los trazos viven en
 * `comun/base/Icono.svelte`; un nombre que no exista allí simplemente no pinta
 * icono, y el rótulo de texto —que es el que lleva el significado— no depende
 * de él.
 */
export const RUTAS = Object.freeze([
  { camino:'/recursos/docentes/encuestas',arbol:'no-estudiante',roles:['docente'],profunda:true,titulo:'Encuestas para docentes',cargar:()=>import('../docente/rutas/EncuestasParaDocentes.svelte') },
  { camino:'/recursos/docentes/diapositivas',arbol:'no-estudiante',roles:['docente'],profunda:true,titulo:'Diapositivas para docentes',cargar:()=>import('../docente/rutas/DiapositivasParaDocentes.svelte') },
  { camino: CAMINOS.notificaciones, arbol: 'estudiante', titulo: 'Notificaciones y recursos',
    icono: 'encuesta', zona: 'pie', oculta: true, roles: ['estudiante'],
    cargar: () => import('../comun/rutas/RecursosPublicados.svelte') },
  { camino: '/recursos/publicacion', arbol: 'no-estudiante', roles: ['docente','investigador'],
    titulo: 'Recurso del curso', profunda: true,
    cargar: () => import('../comun/rutas/RecursosPublicados.svelte') },
  { camino: '/notificaciones/encuestas', arbol: 'estudiante', roles: ['estudiante'], profunda: true,
    titulo: 'Encuestas del curso', cargar: () => import('../estudiante/rutas/EncuestasDelCurso.svelte') },
  { camino: '/notificaciones/diapositivas', arbol: 'estudiante', roles: ['estudiante'], profunda: true,
    titulo: 'Diapositivas del curso', cargar: () => import('../estudiante/rutas/DiapositivasDelCurso.svelte') },
  { camino: CAMINOS.conversacionesInvestigacion, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Conversaciones de estudiantes', icono: 'conversacion', profunda: true,
    cargar: () => import('../investigador/rutas/ConversacionesDeEstudiantes.svelte') },
  // ── árbol del estudiante ────────────────────────────────────────────────
  { camino: CAMINOS.conversacion, arbol: 'estudiante', titulo: 'Conversación', icono: 'conversacion',
    tutorProfesional: true,
    cargar: () => import('../estudiante/rutas/Conversacion.svelte') },
  // Compatibilidad con enlaces antiguos. El historial real vive en el carril
  // de `/`; no existe una segunda pantalla que mantener. `resolver()` aplica
  // esta redirección después de las guardas de árbol y consentimiento.
  { camino: CAMINOS.historial, arbol: 'estudiante', titulo: 'Mi historial', icono: 'historial',
    tutorProfesional: true,
    redirigirA: CAMINOS.conversacion, compatibilidad: true },
  // `pendiente` marca lo que TODAVÍA NO SE CONSTRUYÓ. Está en la tabla porque
  // `D-20` la declara y quitarla haría que la navegación mintiera sobre el
  // alcance; y marcada porque una pantalla en blanco se lee como un fallo.
  { camino: CAMINOS.practica, arbol: 'estudiante', titulo: 'Práctica', icono: 'practica',
    zona: 'pie', oculta: true,
    cargar: () => import('../estudiante/rutas/Practica.svelte') },
  { camino: CAMINOS.graficadora, arbol: 'estudiante', titulo: 'Graficadora', icono: 'graficadora',
    zona: 'pie', tutorProfesional: true,
    cargar: () => import('../comun/rutas/Graficadora.svelte') },
  { camino: CAMINOS.conceptos, arbol: 'estudiante', titulo: 'Conceptos', icono: 'conceptos',
    zona: 'pie', tutorProfesional: true,
    cargar: () => import('../estudiante/rutas/Conceptos.svelte') },
  { camino: CAMINOS.biblioteca, arbol: 'estudiante', titulo: 'Biblioteca del curso', icono: 'biblioteca',
    zona: 'pie', tutorProfesional: true,
    cargar: () => import('../estudiante/rutas/Biblioteca.svelte') },
  { camino: CAMINOS.datos, arbol: 'estudiante', titulo: 'Mis datos', icono: 'datos',
    zona: 'perfil',
    cargar: () => import('../estudiante/rutas/MisDatos.svelte') },
  { camino: CAMINOS.unirse, arbol: 'estudiante', titulo: 'Unirme a una clase', icono: 'clase',
    zona: 'pie',
    cargar: () => import('../estudiante/rutas/UnirseAClase.svelte') },
  // El recorrido retenido de `EQ-020`: entrada institucional, perfil
  // obligatorio, consentimiento versionado, dimensiones del menor y los
  // estados de bloqueo. Una sola ruta y una composición por pasos dentro —no
  // una ruta por pantalla—: no hay navegación real entre esos pasos, los
  // decide el `acceso` que calcula el servidor.
  { camino: CAMINOS.consentimiento, arbol: 'estudiante', titulo: 'Autorización', icono: 'datos',
    abierta: true,
    cargar: () => import('../estudiante/rutas/Consentimiento.svelte') },

  // ── `EQ-013` · la biblioteca de fuentes · Fase 5 ────────────────────────
  //
  // `profunda` MARCA LO QUE SE ALCANZA POR ENLACE Y NO POR NAVEGACIÓN.
  //
  // A una fuente se llega desde «Material del curso» de una respuesta, no
  // desde el carril: ponerlas ahí ofrecería «abrir un fragmento» sin decir
  // cuál. Y no son `abierta`, que significa otra cosa —el recorrido retenido
  // de `EQ-020`— ni `compatibilidad`, que es un alias que redirige.
  //
  // `patron` ES LO QUE LES PERMITE LLEVAR UN IDENTIFICADOR EN EL CAMINO.
  // `camino` sigue siendo la forma canónica que `rutasDe()` y las pruebas
  // usan; `patron` es lo que `rutaDe()` prueba cuando la igualdad falla. Sin
  // él, `/fuentes/F-252` sería «esta dirección no existe» y el enlace profundo
  // —que es media Fase 5— no funcionaría al recargar.
  { camino: CAMINOS.fuentes, patron: /^\/fuentes\/[^/]+$/,
    arbol: 'estudiante', titulo: 'Material del curso', icono: 'conceptos',
    profunda: true, tutorProfesional: true, lecturaInvestigacion: true,
    cargar: () => import('../estudiante/rutas/Fuente.svelte') },
  { camino: CAMINOS.obras, patron: /^\/obras\/[^/]+$/,
    arbol: 'estudiante', titulo: 'Obra del curso', icono: 'conceptos',
    profunda: true, tutorProfesional: true, lecturaInvestigacion: true,
    cargar: () => import('../estudiante/rutas/Obra.svelte') },

  // ── árbol del docente y del investigador ────────────────────────────────
  //
  // ⚠️ **Las pantallas profesionales declaran su rol desde la Fase 7.**
  //
  // `DD-04` decidió que docente e investigador comparten aplicación, y eso
  // sigue siendo cierto: comparten árbol. Lo que la Fase 7 corrige es haber
  // leído «comparten árbol» como «comparten todo» — el encargo lo dice con
  // todas las letras: *«no conviertas el árbol no-estudiante en una
  // autorización universal»*.
  //
  // `/supervision`, `/mis-clases` y `/contexto` pertenecen al docente.
  // `/grupo` y `/estudiante` comparten PRESENTACIÓN, pero no borde de datos:
  // el docente consulta su clase y el investigador entra por las rutas
  // institucionales auditadas. Declarar ambos aquí no convierte una API
  // docente en universal; evita duplicar dos pantallas que explican las mismas
  // métricas. Es la misma razón por la que `roles` es allowlist positiva.
  // El orden de declaración es el orden del header después de filtrar por rol.
  // Así investigador conserva una secuencia exacta y docente comienza por la
  // gestión de clases sin mantener dos listas que puedan discrepar.
  { camino: CAMINOS.clases, arbol: 'no-estudiante', roles: ['docente'],
    titulo: 'Crear y gestionar clases', icono: 'clases',
    cargar: () => import('../docente/rutas/MisClases.svelte') },
  { camino: CAMINOS.graficadoraProfesional, arbol: 'no-estudiante', roles: ['docente', 'investigador'],
    titulo: 'Graficadora', icono: 'graficadora', profunda: true,
    cargar: () => import('../comun/rutas/Graficadora.svelte') },
  { camino: CAMINOS.equipoInstitucional, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Equipo institucional', icono: 'equipo-institucional',
    cargar: () => import('../investigador/rutas/EquipoInstitucional.svelte') },
  { camino: CAMINOS.analiticaInstitucional, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Analítica institucional', icono: 'analitica-institucional',
    cargar: () => import('../investigador/rutas/PanelInstitucional.svelte') },
  { camino: CAMINOS.grupo, arbol: 'no-estudiante', roles: ['docente', 'investigador'],
    titulo: 'Vista del grupo', icono: 'grupo',
    cargar: () => import('../docente/rutas/VistaDelGrupo.svelte') },
  { camino: CAMINOS.estudiante, arbol: 'no-estudiante', roles: ['docente', 'investigador'],
    titulo: 'Estudiantes', icono: 'estudiante',
    cargar: () => import('../docente/rutas/FichaDeEstudiante.svelte') },
  { camino: CAMINOS.evidencias, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Autorizaciones de representantes', icono: 'evidencias-institucionales',
    cargar: () => import('../investigador/rutas/Evidencias.svelte') },
  { camino: CAMINOS.solicitudesMatricula, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Solicitudes de matrícula', icono: 'solicitudes',
    cargar: () => import('../investigador/rutas/SolicitudesDeClase.svelte') },
  { camino: CAMINOS.auditoriaInstitucional, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Auditoría institucional', icono: 'auditoria-institucional',
    cargar: () => import('../investigador/rutas/AuditoriaInstitucional.svelte') },
  { camino: CAMINOS.consumoIA, arbol: 'no-estudiante', roles: ['investigador'],
    titulo: 'Consumo de IA', icono: 'consumo-ia',
    cargar: () => import('../investigador/rutas/ConsumoIA.svelte') },
  { camino: CAMINOS.supervision, arbol: 'no-estudiante', roles: ['docente'],
    titulo: 'Cola de supervisión', icono: 'supervision',
    cargar: () => import('../docente/rutas/ColaDeSupervision.svelte') },
  { camino: CAMINOS.contexto, arbol: 'no-estudiante', roles: ['docente'],
    titulo: 'Contexto curricular', icono: 'contexto',
    cargar: () => import('../docente/rutas/ContextoCurricular.svelte') },
  // Gestión autorizada por Yeison el 2026-10-06; el servidor aplica permisos.
  { camino: CAMINOS.recursos, arbol: 'no-estudiante', roles: ['docente','investigador'],
    titulo: 'Recursos y encuestas', icono: 'recursos',
    cargar: () => import('../investigador/rutas/Recursos.svelte') },
  { camino: CAMINOS.encuestas, arbol: 'no-estudiante', roles: ['docente','investigador'],
    titulo: 'Encuestas', profunda: true,
    cargar: () => import('../investigador/rutas/Encuestas.svelte') },
  { camino: CAMINOS.diapositivas, arbol: 'no-estudiante', roles: ['docente','investigador'],
    titulo: 'Diapositivas', profunda: true,
    cargar: () => import('../investigador/rutas/Diapositivas.svelte') },
  { camino: CAMINOS.perfilProfesional, arbol: 'no-estudiante', roles: ['docente', 'investigador'],
    titulo: 'Mi perfil', icono: 'perfil-institucional', zona: 'perfil',
    cargar: () => import('../comun/rutas/MiPerfilProfesional.svelte') }
]);

/**
 * Dónde aterriza CADA ROL cuando no se pidió nada, o cuando lo pedido no toca.
 *
 * ⚠️ **Estaba indexado por árbol y ahora lo está por rol**, y es la corrección
 * que C2B necesitaba. Con dos árboles y tres roles, `INICIO['no-estudiante']`
 * mandaba a una investigadora a `/supervision` — una cola que no es la suya— y
 * no había forma de distinguirla sin escribir la excepción en cada consumidor.
 * Seis archivos calculaban su inicio; la séptima copia habría discrepado.
 *
 * Se indexa por rol y se lee **sólo** con `inicioDe()`. Un mapa expuesto invita
 * a `INICIO[algo]`, y `algo` acaba siendo un árbol otra vez.
 */
/**
 * ¿Este rol puede abrir esta ruta?
 *
 * Sin `roles` declarados, cualquiera de su árbol. Con ellos, sólo los de la
 * lista — y `null` nunca, para que no pasarlo esconda la ruta en vez de
 * publicarla.
 */
export function rolPermitido(ruta, rol) {
  if (!ruta?.roles) return true;
  return typeof rol === 'string' && ruta.roles.includes(rol);
}

/**
 * ¿Este rol, en este espacio, puede abrir esta ruta? · `EQ-031`
 *
 * **Es la matriz central, y por eso hay una sola.** La guarda (`guardas.js`) y
 * la navegación (`rutasDe()`) preguntan las dos aquí; si cada una decidiera por
 * su cuenta, la aplicación acabaría ofreciendo un enlace que su propia guarda
 * rebota. `espacios-de-trabajo.prueba.js` comprueba que las dos coinciden para
 * toda combinación de ruta, rol y espacio.
 *
 * Tres preguntas, en este orden, y ninguna es sustituible por otra:
 *
 * 1. **¿Es del árbol del espacio activo?** La frontera de `DD-04` sigue siendo
 *    la que protege algo; lo que `EQ-031` cambió es que el árbol lo decide el
 *    espacio y no sólo el rol.
 * 2. **¿Es de su rol?** La allowlist de `EQ-023` —hoy sólo `/evidencias`—. Va
 *    aparte del espacio a propósito: **el espacio no reparte permisos**. Un
 *    docente no revisa autorizaciones de representantes en ningún espacio, y un
 *    investigador no hereda la cola docente por cambiar de modo.
 * 3. **¿Es una capacidad de consulta?** Sólo para un profesional en espacio
 *    Tutor. `EQ-031` le concede *«conversación, historial propio, conceptos,
 *    biblioteca, fuentes, obras, notación y gráficas»* — no el ciclo de vida
 *    académico del estudiante: matrícula, consentimiento y perfil no son suyos.
 *
 * Se declara con `tutorProfesional` en la ruta y no como «todas menos
 * `/unirse`, `/consentimiento`…»: una ruta nueva del árbol del estudiante no
 * debe quedar expuesta a un profesional por omisión, que es el fallo que una
 * lista negativa comete sin que nadie lo decida.
 */
export function puedeAbrir(ruta, rol, espacio) {
  if (!ruta) return false;
  // El visor de conversaciones cita material del corpus. El investigador ya
  // puede leerlo en Tutor; estas dos lecturas profundas también se abren desde
  // su espacio profesional, conservando el retorno al historial auditado.
  // No concede el editor, el historial propio ni el ciclo académico.
  if (ruta.lecturaInvestigacion && rol === 'investigador' && ruta.profunda) return true;
  if (ruta.arbol !== arbolDe(rol, espacio)) return false;
  return rolPermitido(ruta, rol) && esCapacidadDelEspacio(ruta, rol, espacio);
}

/**
 * La tercera pregunta de `puedeAbrir()`, aparte porque `rutasDe()` la necesita
 * sin la primera.
 *
 * `rutasDe()` recibe el árbol ya resuelto por quien pinta la navegación, así
 * que volver a derivarlo dentro daría dos respuestas a «de qué árbol es esto» y
 * la de un argumento explícito perdería contra la calculada. La regla del
 * espacio, en cambio, es la misma para los dos y vive **aquí sola**.
 */
function esCapacidadDelEspacio(ruta, rol, espacio) {
  // Un estudiante en su árbol no tiene nada más que comprobar: es su ciclo.
  if (esEstudiante(rol)) return true;
  if (normalizarEspacio(espacio, rol) !== ESPACIO_TUTOR) return true;
  return Boolean(ruta.tutorProfesional);
}

/**
 * La ruta de un camino, o `null`.
 *
 * Primero por igualdad y sólo después por `patron`. El orden importa: si el
 * patrón se probara antes, una ruta fija que cayera dentro de él dejaría de
 * encontrarse a sí misma.
 *
 * El camino llega **sin consulta y sin ancla**: quien enruta pasa
 * `location.pathname`. Se recorta igual por si alguien llama con la dirección
 * entera, porque un `?volver=…` colado aquí haría fallar la igualdad de todas
 * las rutas fijas.
 */
export function rutaDe(camino) {
  const limpio = String(camino ?? '').split('?')[0].split('#')[0];
  return (
    RUTAS.find((r) => r.camino === limpio) ??
    RUTAS.find((r) => r.patron instanceof RegExp && r.patron.test(limpio)) ??
    null
  );
}

/**
 * Las que este árbol —y este rol— pueden ver, para pintar la navegación.
 *
 * `rol` es opcional y su ausencia **restringe**: sin él, lo que declara `roles`
 * queda fuera. Es lo que hace que olvidar pasarlo esconda `/evidencias` a todo
 * el mundo en vez de ofrecérsela a una docente.
 */
export function rutasDe(arbol, rol = null, espacio = null) {
  return RUTAS.filter(
    (r) =>
      r.arbol === arbol &&
      !r.abierta &&
      !r.compatibilidad &&
      // `profunda`: se alcanza por enlace desde una respuesta, no desde el
      // carril. Ofrecer «Material del curso» sin decir de qué turno no
      // significaría nada.
      !r.profunda && !r.oculta &&
      rolPermitido(r, rol) &&
      esCapacidadDelEspacio(r, rol, espacio)
  );
}

/**
 * Las de una zona del carril · `zona` es presentación, como `icono`.
 *
 * El carril reparte lo que se alcanza desde él en tres sitios, y el reparto
 * sale del mockup que las docentes vieron:
 *
 *   `principal`  el cuerpo del carril — la conversación y su historial
 *   `pie`        el bloque de abajo   — práctica, conceptos, unirme a clase
 *   `perfil`     junto a la identidad — mis datos
 *
 * Sin `zona` declarada, `principal`. Es el defecto seguro: una ruta nueva
 * aparece en el carril en vez de desaparecer, que es el fallo barato de los
 * dos.
 *
 * ⚠️ ESTE REPARTO NO ESTÁ EN `D-20`, Y `D-20` MANDA. La figura declaró la
 * navegación de cada rol cuando la navegación eran pestañas; el carril la
 * reorganiza sin añadir ni quitar ningún camino. **`D-20` debería reflejarlo**
 * — mientras no lo haga, el diagrama y la aplicación cuentan la misma lista de
 * rutas repartida de dos maneras distintas. Decidido con Fabián el 2026-08-16.
 */
export function rutasDeZona(arbol, zona, rol = null, espacio = null) {
  return rutasDe(arbol, rol, espacio).filter((r) => (r.zona ?? 'principal') === zona);
}
