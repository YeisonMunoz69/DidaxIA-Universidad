/**
 * Estado reactivo de la sesión.
 *
 * Quién es, qué rol tiene, qué acceso le calculó el servidor y si la conexión
 * está degradada. Es el único estado compartido de la aplicación: no hay
 * almacén global, porque invitaría a acumular en el navegador cosas que no
 * deben salir del servidor.
 *
 * QUÉ CABE AQUÍ, Y LA REGLA ES CORTA
 * -----------------------------------
 * Lo que hace falta para decidir QUÉ PANTALLA SE PINTA. Nada más. En concreto
 * no cabe —y no es una lista de buenas intenciones, es `RP-18`— ningún campo
 * del modelo del estudiante: ni ansiedad, ni autoeficacia, ni concepción
 * candidata, ni dominio por nodo.
 *
 * ⚠️ Y EN C1 LA REGLA SE APLICÓ TAMBIÉN A LOS DATOS DEL RECORRIDO. Aquí no hay
 * edad, ni programa, ni semestre, ni recibos, ni el estado del representante,
 * ni la solicitud de supresión. El estado completo lo pide quien lo pinta
 * —`Consentimiento.svelte`, `MisDatos.svelte`— y lo suelta al desmontarse.
 * Copiarlo aquí habría construido en el navegador una réplica de la base de
 * datos que `EQ-020` no quiere, y habría dejado a la aplicación decidiendo con
 * un estado viejo mientras la base ya dice otra cosa.
 *
 * SE CONSERVAN CINCO COSAS Y CADA UNA PINTA ALGO
 * -----------------------------------------------
 *   `autenticada`      · hay sesión o no la hay → entrada institucional
 *   `rol`              · qué árbol se monta
 *   `acceso`           · qué puede alcanzar dentro del suyo
 *   `expiraEnSegundos` · para avisar antes de los siete días de `EQ-020`
 *   `degradada`        · si lo de arriba no se pudo comprobar
 *
 */
import * as api from '../api/sesion.js';
import { limpiarCachesDeLectura } from '../lectura/cache.js';
import * as onboarding from '../api/onboarding.js';
import { clasificar } from '../errores/degradacion.js';
import { conversacion } from '../conversacion/conversacion.svelte.js';
import { historial } from '../historial/historial.svelte.js';
import { esEstudiante } from './rol.js';
import { SIN_CONSULTAR, permiteTutor } from './acceso.js';
import { vincularCuenta, desvincularCuenta } from '../preferencias/cuenta.js';

export function crearSesion() {
  /** El identificador de CONVERSACIÓN. Nunca el token de autenticación: ése
      vive en una cookie `HttpOnly` y no cruza al JavaScript (hito R1). */
  let conversacionActual = $state('');
  let rol = $state('estudiante');
  let acceso = $state(SIN_CONSULTAR);
  let tutoriaAcademicaSinInvestigacion = $state(false);
  let degradada = $state(false);
  let cargando = $state(false);
  /** Segundos que le quedan a la AUTENTICACIÓN, según el servidor. */
  let expiraEnSegundos = $state(0);

  /**
   * ¿Ya se preguntó al servidor quién es?
   *
   * Existe porque las guardas del enrutado no pueden decidir antes de saberlo.
   * Sin esto, al cargar cualquier dirección el rol vale «estudiante» y el
   * acceso no está consultado durante un instante, la guarda redirige y **la
   * dirección pedida se pierde** — que es lo que pasaba al abrir
   * `/supervision` con sesión de docente.
   */
  let sincronizada = $state(false);

  /**
   * ¿Hay una sesión autenticada?
   *
   * NO guarda el correo ni el nombre aunque el servidor los devuelva. Aquí solo
   * cabe lo que hace falta para decidir qué pantalla se pinta, y para eso basta
   * un sí o un no: quién es se pregunta cuando haga falta enseñarlo, y así este
   * objeto no se convierte en la copia de cliente de un dato personal.
   *
   * ⚠️ **Desde `EQ-020` esto ya no distingue «anónima» de «con cuenta»: sólo
   * existen sesiones autenticadas.** `GET /api/sesion` no crea ninguna y
   * responde 401 a quien llegue sin cookie válida, así que tener sesión y estar
   * autenticado pasaron a ser lo mismo.
   */
  let autenticada = $state(false);

  /** Aplica lo que dijo el servidor sobre la SESIÓN. Único sitio donde el rol cambia. */
  function aplicar(datos) {
    const eraAutenticada = autenticada;
    conversacionActual = datos?.conversacion ?? datos?.sesion ?? '';
    rol = datos?.rol ?? 'estudiante';
    autenticada = Boolean(datos);
    if (autenticada) void vincularCuenta(datos.correo ?? datos.identificador_estable ?? 'sesion-activa');
    else if (eraAutenticada) desvincularCuenta();
    expiraEnSegundos = Number(datos?.expira_en_segundos ?? 0);

    // La conversación cacheada puede ser de otra sesión: el servidor guarda su
    // estado en memoria del proceso y un reinicio la pierde, aunque la cookie
    // siga en el navegador. `verificarDueno` descarta el hilo cuando el
    // identificador ya no es el mismo con el que se guardó.
    conversacion?.verificarDueno?.(conversacionActual);

    if (!autenticada) {
      limpiarCachesDeLectura();
      acceso = SIN_CONSULTAR;
      tutoriaAcademicaSinInvestigacion = false;
      conversacion?.limpiar?.();
      historial?.limpiar?.();
    } else if (!eraAutenticada && esEstudiante(rol)) {
      // Entró ahora: el carril puede estar mostrando la lista de antes.
      // `recargarLista()` ya sabe no pisarse con una carga en vuelo.
      historial?.recargarLista?.();
    }
  }

  /**
   * Pregunta el acceso calculado. Se separa de `aplicar()` a propósito.
   *
   * Son dos autoridades distintas —`rutas/sesion.py` dice **quién es** y
   * `rutas/consentimiento.py` dice **qué ha autorizado**— y dos rutas
   * distintas. Fundirlas obligaría a que un fallo de una borrara lo que la otra
   * ya sabía; separadas, un 503 del estado deja `mantenimiento` sin tocar la
   * identidad, que es justo lo que `EQ-024` pide representar.
   */
  async function refrescarAcceso() {
    if (!autenticada || !esEstudiante(rol)) {
      // Un docente o investigador no tiene recorrido de onboarding: preguntarlo
      // gastaría una petición para recibir un estado que nada suyo consume.
      acceso = SIN_CONSULTAR;
      return;
    }
    try {
      const estado = await onboarding.estado();
      acceso = estado?.acceso ?? SIN_CONSULTAR;
      tutoriaAcademicaSinInvestigacion =
        estado?.tutoria_academica_sin_investigacion === true;
      degradada = false;
    } catch (e) {
      const clase = clasificar(e);
      if (clase === 'sin-sesion') {
        // La sesión se cayó entre las dos llamadas. No es degradación.
        aplicar(null);
      } else if (clase === 'mantenimiento') {
        // `EQ-024` · no se inventa el estado. `mantenimiento` ES un estado de
        // pleno derecho, no una lista vacía ni un consentimiento pendiente.
        acceso = 'mantenimiento';
      } else {
      acceso = SIN_CONSULTAR;
      tutoriaAcademicaSinInvestigacion = false;
        degradada = true;
      }
    }
  }

  return {
    get conversacion() { return conversacionActual; },
    get rol() { return rol; },
    get acceso() { return acceso; },
    get tutoriaAcademicaSinInvestigacion() { return tutoriaAcademicaSinInvestigacion; },
    get degradada() { return degradada; },
    get cargando() { return cargando; },
    get sincronizada() { return sincronizada; },
    get abierta() { return autenticada; },
    get autenticada() { return autenticada; },
    get expiraEnSegundos() { return expiraEnSegundos; },
    /** Si el tutor se puede usar AHORA. Lo decide el acceso, no el rol. */
    get puedeUsarTutor() {
      return permiteTutor(acceso, tutoriaAcademicaSinInvestigacion);
    },

    /**
     * Pregunta al servidor quién es y qué acceso tiene. Al arrancar.
     *
     * No propaga el fallo: que no haya sesión es el estado normal de quien
     * acaba de llegar —un 401 esperado, no una avería— y que no haya red se
     * refleja en `degradada` para que la interfaz lo diga en vez de quedarse
     * en blanco.
     */
    async sincronizar() {
      cargando = true;
      try {
        aplicar(await api.consultar());
        degradada = false;
        await refrescarAcceso();
      } catch (e) {
        const clase = clasificar(e);
        // ⚠️ Un 401 NO es degradación. Antes de C1 esta línea comparaba con
        // `sesion-vencida`, que era la misma clase para «no has entrado» y
        // «se te acabó el plazo»; ahora `sin-sesion` cubre las dos y ninguna
        // enciende el aviso de sistema caído.
        degradada = clase !== 'sin-sesion';
        if (!degradada) aplicar(null);
      } finally {
        cargando = false;
        // Se marca aunque haya fallado: si el servidor no contesta, seguir
        // esperando eternamente deja la pantalla en blanco. Sabemos lo que hay
        // que saber —que no se pudo—, y `degradada` lo dice.
        sincronizada = true;
      }
    },

    /** Vuelve a pedir sólo el acceso. Tras decidir, revocar o cargar evidencia. */
    async refrescarAcceso() {
      await refrescarAcceso();
    },

    /**
     * Lo que una pantalla del recorrido ya consultó, aplicado sin repetir la
     * petición.
     *
     * `Consentimiento.svelte` recibe el estado completo en cada escritura —el
     * servidor lo devuelve junto al recibo—, así que volver a preguntarlo aquí
     * sería una llamada de más contra la misma fila. El acceso sigue viniendo
     * del servidor: esto lo copia, no lo calcula.
     */
    aplicarAcceso(valor, tutoriaAcademica = false) {
      if (typeof valor === 'string' && valor) acceso = valor;
      tutoriaAcademicaSinInvestigacion = tutoriaAcademica === true;
    },
    /**
     * Entra con la identidad de Google · `DD-18` · `EQ-020`.
     *
     * **Es la única puerta.** No complementa a ninguna vía anónima porque no
     * existe ninguna: `POST /api/sesion` responde 401 desde el hito B1 y
     * `GET /api/sesion` ya no abre nada al consultarse. Quien no tenga cuenta
     * del dominio institucional no puede usar el tutor, y eso se le dice.
     *
     * El rol que venga en la respuesta manda sobre el que hubiera: lo decide el
     * servidor con su registro de docentes.
     */
    async entrarConGoogle(idToken) {
      aplicar(await api.iniciarConGoogle(idToken));
      degradada = false;
      await refrescarAcceso();
    },

    /**
     * «Nueva conversación»: otro hilo, la MISMA autenticación.
     *
     * ⚠️ **No renueva los siete días** (hito R1). El servidor cambia sólo el
     * identificador de conversación y conserva token, `creada_en` e identidad;
     * aquí se refleja igual — `expiraEnSegundos` sigue bajando con el tiempo
     * real en vez de volver a empezar. Cuando decía lo contrario, quien
     * empezaba una conversación cada seis días conservaba la sesión para
     * siempre y el plazo de `EQ-020` dejaba de existir.
     *
     * Tampoco vuelve a preguntar el acceso: crear un hilo no cambia lo que la
     * persona ha autorizado, y pedirlo daría a entender que sí.
     */
    async reiniciarConversacion() {
      aplicar(await api.reiniciar());
      // Rotar la conversación del servidor sin soltar el hilo cacheado dejaba
      // la pantalla nueva con mensajes de la anterior. Además impedía que
      // `Conversacion.svelte` reconociera el estado vacío y, por tanto,
      // ocultaba el ambiente matemático que siempre debe acompañar un inicio.
      conversacion.limpiar();
      degradada = false;
    },

    /**
     * Consulta cuánto le queda a la sesión. **No la prolonga.**
     *
     * `POST /api/sesion/renovar` informa el tiempo restante y nada más; los
     * siete días se cuentan desde que se abrió. Renovar en silencio aquí
     * convertiría el plazo de `EQ-020` en «siete días sin cerrar la pestaña».
     */
    async consultarVencimiento() {
      try {
        const datos = await api.tiempoRestante();
        expiraEnSegundos = Number(datos?.expira_en_segundos ?? 0);
      } catch (e) {
        if (clasificar(e) === 'sin-sesion') aplicar(null);
      }
    },

    async cerrar() {
      // El estado local se limpia PASE LO QUE PASE con la petición: si el
      // servidor no contesta, dejar la pantalla como si la sesión siguiera
      // abierta es lo peor de los dos mundos.
      try {
        await api.cerrar();
      } finally {
        aplicar(null);
        conversacion?.limpiar?.();
        historial?.limpiar?.();
        // ⚠️ Y NO SE VUELVE A CONSULTAR. Antes se llamaba a `api.consultar()`
        // aquí para recoger la sesión anónima que `GET /api/sesion` abría al
        // salir; esa ruta ya no abre ninguna, así que la llamada sólo servía
        // para recibir el 401 que ya sabemos.
        sincronizada = true;
      }
    },

    /** Lo marca la capa de red cuando un turno se degrada. */
    marcarDegradada(v = true) { degradada = v; }
  };
}

/**
 * La instancia que usa la aplicación. UNA sola, y por eso está aquí.
 *
 * `05` §5 descartó el almacén global, y esto no lo reintroduce por la puerta de
 * atrás: es un objeto con seis campos, todos necesarios para decidir qué
 * pantalla se pinta, y ninguno del modelo del estudiante ni del recorrido de
 * consentimiento. La alternativa —pasar la sesión por props desde la raíz hasta
 * la séptima ruta— la haría más fácil de perder de vista, no menos.
 */
export const sesion = crearSesion();
