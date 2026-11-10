<!--
El recorrido retenido · `EQ-020` / `EQ-021` / `EQ-016`.

Una sola ruta y una composición por pasos dentro. Los pasos NO son rutas: no
hay navegación real entre ellos —no se puede «ir» a la pantalla de bloqueo— y
cuál se pinta lo decide el `acceso` que **calcula el servidor**.

⚠️ QUÉ HABÍA AQUÍ ANTES, Y POR QUÉ NO SE PODÍA CONSERVAR NADA
---------------------------------------------------------------
La pantalla anterior llamaba a `POST /api/consentimiento` —que hoy responde
**410**— mandando decisión y edad juntas, y anunciaba un tratamiento
«Opcional» de «acompañamiento personalizado» con tres garantías redactadas en
el propio componente. Cuatro problemas, y ninguno de redacción:

1. la ruta escribía en memoria de proceso y en una tabla que no es autoridad, y
   al declarar una edad menor de 18 ejecutaba una cascada de borrado;
2. el texto legal estaba **inventado en el frontend**. `EQ-021` exige un
   documento versionado con su huella, y hoy no hay ninguno publicado: la
   interfaz tiene que impedir aceptar, no redactar un sustituto;
3. decía «tu elección se recuerda mientras dure esta sesión» a quien no tuviera
   cuenta — un supuesto que `EQ-020` retiró junto con las sesiones anónimas;
4. rechazar se presentaba como algo que no cierra el tutor. Bajo `EQ-016`,
   rechazar o revocar **sí** bloquea.

CÓMO SE DECIDE QUÉ SE PINTA
----------------------------
`GET /api/onboarding/estado` en una sola llamada: las cuatro dimensiones tienen
que describir el mismo instante. De ahí sale `acceso`, y de `acceso` sale el
paso. El cliente no recalcula el estado ni deduce el paso de los datos sueltos.

NINGÚN ÉXITO OPTIMISTA
-----------------------
Cada escritura espera la respuesta de PostgreSQL y **pinta el estado que
devuelve el servidor**, no uno que este archivo adelante. `responder_con_estado()`
manda el estado ya recalculado junto a los recibos, así que no hace falta suponer
nada: si la escritura falló, el paso sigue donde estaba y el formulario conserva
lo escrito.

⚠️ UNA DECISIÓN VISIBLE, UNA PETICIÓN · `D1B`
----------------------------------------------
Aquí había **dos** pasos de decisión: `DecisionDeConsentimiento` montado para el
titular y, más abajo, otra vez para el asentimiento del menor. Eran dos
peticiones, y entre ellas cabía el estado que nadie decidió.

`D0` §10.10 lo cierra: una sola acción, «Acepto y continuar», y los actos que
correspondan guardados **atómicamente por el servidor**. Esta composición hace
exactamente **una** llamada a `decidirConjunta()` y pinta los `recibos` que
devuelva —uno para un adulto, dos para un menor—. No hay `Promise.all`, no hay
encadenamiento y no hay una segunda petición para el asentimiento.

QUÉ DECIDE SI HAY QUE DECIDIR · `D1B` bis
--------------------------------------------
`estado.decision`, que lo resuelve el servidor. Aquí se consume.

Hasta la corrección, esta composición deducía el paso comparando `al_dia` de las
dos dimensiones. Con el estado mixto —una revocada por su ruta independiente,
la otra otorgada— eso ya no basta: hay que saber si la **política** admite una
decisión nueva, y esa regla vive en `dominio/modelo/redecision.py`. Recalcularla
aquí habría puesto dos redacciones de la misma regla en dos sitios, y la del
navegador sería la que la persona ve.

`decision.requerida` se combina con `al_dia` en vez de sustituirlo: son dos
preguntas —«¿la política admite decidir?» y «¿está el acceso al día?»— y las dos
tienen que ser ciertas para que el paso siguiente tenga sentido.



-->
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import Icono from '../../comun/base/Icono.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import EntradaInstitucional from '../piezas/recorrido/EntradaInstitucional.svelte';
  import PanelDeEstado from '../piezas/recorrido/PanelDeEstado.svelte';
  import FormularioDePerfil from '../piezas/recorrido/FormularioDePerfil.svelte';
  import DecisionConjunta from '../piezas/recorrido/DecisionConjunta.svelte';
  import DocumentoDeLaVersion from '../piezas/recorrido/DocumentoDeLaVersion.svelte';
  import PanelDelRepresentante from '../piezas/recorrido/PanelDelRepresentante.svelte';
  import ReciboDelActo from '../piezas/recorrido/ReciboDelActo.svelte';
  import EnlacesPublicos from '../../comun/base/EnlacesPublicos.svelte';
  import EntrarConGoogle from '../../comun/sesion/EntrarConGoogle.svelte';
  import ReportarProblema from '../../comun/rutas/ReportarProblema.svelte';
  import * as onboarding from '../../nucleo/api/onboarding.js';
  import * as consentimiento from '../../nucleo/api/consentimiento.js';
  import * as sesionApi from '../../nucleo/api/sesion.js';
  import { describir, clasificar } from '../../nucleo/errores/degradacion.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { navegar } from '../../enrutado/navegar.js';
  import { esBloqueo } from '../../nucleo/sesion/acceso.js';

  const codigoDocumento = new URLSearchParams(globalThis.location?.search ?? '').get('documento') ?? '';

  /**
   * El estado vigente completo, tal como lo devolvió el servidor.
   *
   * Vive AQUÍ y no en `sesion.svelte.js` a propósito: es el detalle del
   * recorrido —perfil, versiones, dimensiones del menor— y el estado
   * compartido sólo conserva lo que decide qué pantalla se pinta. Copiarlo
   * arriba habría construido una réplica de la fila en el navegador.
   */
  let estado = $state(null);
  /** Las versiones publicadas de los tres alcances; pueden ser `null`. */
  let versiones = $state(null);
  let versionesNoDisponibles = $state(false);
  /** Nombre y correo de Google, sólo para enseñarlos. No se persisten aquí. */
  let identidad = $state(null);
  /**
   * Los recibos de la última decisión. Los devolvió el servidor.
   *
   * ⚠️ **Plural desde `D1B`.** Una decisión de un menor produce dos actos
   * —titular y asentimiento—, cada uno con su versión, su huella y su secuencia.
   * Un `recibo` singular habría obligado a elegir cuál enseñar, y la persona se
   * quedaría sin constancia de la mitad de lo que acaba de decidir.
   */
  let recibos = $state([]);
  /**
   * Si el aviso por correo de la última decisión **otorgada** salió · `D2`.
   *
   * `null` significa «no aplica»: no se ha decidido todavía, o lo que se decidió
   * fue un rechazo, que por decisión de `EQ-024` no manda correo. `true`/`false`
   * son lo que el servidor respondió en `aviso_enviado`, y sólo se conocen
   * **después** de intentarlo: la pantalla no promete el envío por adelantado.
   */
  let avisoEnviado = $state(null);
  /**
   * Si la decisión ya habilitó el tutor y se espera a que la persona continúe.
   *
   * ⚠️ **Hallazgo B de la revisión de `bd2b66f`.** Hasta entonces, un adulto que
   * aceptaba quedaba `habilitado` y `aplicarRespuesta()` navegaba a `/` en el
   * acto: el mensaje del correo y el recibo se pintaban y desaparecían en el
   * mismo fotograma. Las pruebas de `D2` usaban un menor —que no navega— y por
   * eso el recorrido adulto quedaba fuera de lo comprobado.
   *
   * La navegación ahora la acciona la persona. No hay `setTimeout` ni navegación
   * demorada: un plazo fijo o adivina cuánto tarda alguien en leer, o se lo
   * quita a quien lee despacio.
   */

  let cargando = $state(true);
  let fallo = $state(null);
  /** Motivo redactado por el servidor cuando rechazó la última escritura. */
  let errorDelPerfil = $state('');
  let errorDeDecision = $state('');
  let sinVersionAlDecidir = $state(false);
  /** Motivo cuando el servidor negó la decisión por política, no por versión. */
  let motivoDeLaPolitica = $state('');
  /** Qué alcances dijo el servidor que faltan. Lista cerrada, suya. */
  let alcancesFaltantes = $state([]);
  let errorDeEvidencia = $state('');
  let reservaPendiente = $state(false);
  let refrescandoRepresentante = $state(false);
  let dialogoDeRechazoAbierto = $state(false);
  let rechazoAnunciado = $state(false);
  let motivoDelRechazo = $state('');

  /** El acceso del que se pinta: el del estado recién leído, o el compartido. */
  const acceso = $derived(estado?.acceso ?? sesion.acceso);

  const enBloqueo = $derived(
    acceso === 'mantenimiento' || acceso === 'eliminacion_solicitada' || esBloqueo(acceso)
  );

  /**
   * Si un bloqueo tiene salida desde aquí · `D1B` bis.
   *
   * ⚠️ **Sin esto, el recorrido no tenía salida y la corrección del servidor no
   * llegaba a la persona.** Tras revocar una sola dimensión, el acceso calculado
   * es `bloqueado_por_revocacion`: la composición pintaba `PanelDeEstado` y
   * nunca la decisión, así que el servidor admitía volver a decidir y la
   * pantalla no lo ofrecía. Es el requisito 12 del encargo.
   *
   * Se ofrece **junto al panel**, no en su lugar: el panel explica qué pasó
   * —«retiraste tu autorización»— y eso sigue haciendo falta. Quitarlo dejaría a
   * la persona ante una decisión sin saber por qué se la vuelven a pedir.
   *
   * Los otros dos estados de `enBloqueo` quedan fuera a propósito:
   *
   * - **`mantenimiento`** · no se sabe nada del estado real, así que ofrecer una
   *   decisión sería inventarla (`EQ-024`);
   * - **`eliminacion_solicitada`** · `EQ-022` reserva ese trámite y su cancelación
   *   a «Mis datos». Ofrecer aquí una aceptación insinuaría que decidir de nuevo
   *   cancela la supresión, y no la cancela.
   */
  const bloqueoConSalida = $derived(
    esBloqueo(acceso) && estado?.decision?.requerida === true
  );

  /**
   * El `<h1>` de la vista. UNO, y siempre presente.
   *
   * `T-09`–`T-11` fijan que cada vista pone exactamente un `<h1>` y el armazón
   * ninguno. Aquí eso obliga a que el título viva en la composición y no en
   * cada paso: con un `<h1>` por panel, el paso de carga no tendría ninguno y
   * un paso que montara dos piezas tendría dos. Los pasos usan `<h2>`.
   */
  const titulo = $derived(
    codigoDocumento
      ? 'Documento vigente de consentimiento'
      : !sesion.autenticada && sesion.sincronizada
      ? 'Entra con tu cuenta de la universidad'
      : representanteEsPasoActual
      ? ({
          pendiente_documento: 'Autorización de tu representante',
          documento_recibido: 'Autorización en revisión',
          rechazado: 'Corrige la autorización de tu representante',
          aprobado: 'Autorización aprobada'
        }[estado?.representante?.estado] ?? 'Autorización de tu representante')
      : {
          mantenimiento: 'El servicio está en mantenimiento',
          eliminacion_solicitada: 'Tu solicitud de eliminación está en curso',
          bloqueado_por_rechazo: 'El tutor está bloqueado',
          bloqueado_por_revocacion: 'El tutor está bloqueado',
          esperando_representante: 'Falta la autorización de tu representante'
        }[acceso] ?? 'Antes de empezar tu tutoría'
  );

  /**
   * Si toca pedir el perfil.
   *
   * Sale de `perfil.completo`, que lo calcula el servidor con las cuatro cosas
   * que `EQ-020` exige. No se deduce mirando los campos uno a uno: la regla de
   * «completo» es del dominio y duplicarla aquí la haría divergir.
   */
  const faltaPerfil = $derived(estado?.perfil?.completo === false);

  /**
   * Si toca la decisión conjunta.
   *
   * Sólo cuando el perfil ya está completo: pedir las dos cosas a la vez haría
   * decidir sobre un documento antes de saber si la persona es menor, que es
   * justo lo que cambia el régimen —y cuántos actos escribe el servidor—.
   *
   * ⚠️ **Mira las dos dimensiones, no sólo el titular** (`D1B`). Un menor con el
   * consentimiento al día y el asentimiento sin otorgar sigue teniendo la
   * decisión pendiente, y presentarle el paso siguiente lo dejaría esperando
   * algo que nunca le van a pedir. Los dos `al_dia` los calcula el servidor:
   * `dominio/modelo/acceso.py` compara con la versión que rige, y recalcularlo
   * aquí habría duplicado la regla.
   */
  const faltaDecision = $derived(
    Boolean(estado) &&
      !faltaPerfil &&
      (estado.decision?.requerida === true ||
        estado.consentimiento?.al_dia !== true ||
        (esMenor && estado.asentimiento?.al_dia !== true))
  );

  /**
   * Qué acciones admite la política del servidor. Se consumen, no se calculan.
   *
   * `?? true` cubre una respuesta sin el campo —un backend anterior a `D1B`
   * bis—: se ofrecen las dos y el servidor responde 409 si no procede. Es más
   * honesto que deshabilitarlas por un campo ausente, que dejaría a la persona
   * mirando una pantalla muerta sin motivo.
   */
  const puedeAceptar = $derived(estado?.decision?.puede_aceptar ?? true);
  const puedeRechazar = $derived(estado?.decision?.puede_rechazar ?? true);

  /**
   * Si esta persona es menor de edad.
   *
   * ⚠️ **Sale de la edad PERSISTIDA, no del campo del formulario.** `perfil.edad`
   * es lo que `persona` guarda y lo que el servidor usó para derivar la
   * categoría de edad y fijar el plazo del representante. Mirar el `<input>`
   * habría hecho que el recorrido del menor apareciera y desapareciera mientras
   * alguien teclea, y que un guardado fallido dejara la pantalla del régimen
   * equivocado.
   *
   * Se compara con 18 igual que `categoria_de_edad()`: el límite exacto es
   * adulto. No se deriva de `representante.estado`, que podría venir
   * `no_requerido` en una fila vieja — `acceso.py` toma la misma precaución.
   */
  const esMenor = $derived(
    typeof estado?.perfil?.edad === 'number' && estado.perfil.edad < 18
  );

  /**
   * El rechazo del PDF es un bloqueo global, pero no una pantalla sin salida.
   * Si las decisiones del menor siguen vigentes, el trámite del representante
   * tiene prioridad sobre el panel genérico y permite enviar un nuevo intento.
   */
  const representanteEsPasoActual = $derived(
    Boolean(estado) &&
      esMenor &&
      !faltaPerfil &&
      estado.consentimiento?.al_dia === true &&
      estado.asentimiento?.al_dia === true &&
      ['pendiente_documento', 'documento_recibido', 'rechazado', 'aprobado', 'vencido'].includes(
        estado.representante?.estado
      )
  );

  /** Guarda lo que el servidor devolvió tras una escritura, sin adelantar nada. */
  function aplicarRespuesta(respuesta) {
    estado = respuesta;
    sesion.aplicarAcceso(
      respuesta.acceso,
      respuesta.tutoria_academica_sin_investigacion
    );
    // `recibos` de la decisión conjunta —uno o dos— y `recibo` de una
    // revocación o de la carga de evidencia, que siguen siendo de una sola
    // dimensión. Se normaliza a lista para que la plantilla tenga un solo caso.
    if (Array.isArray(respuesta.recibos) && respuesta.recibos.length) {
      recibos = respuesta.recibos;
    } else if (respuesta.recibo) {
      recibos = [respuesta.recibo];
    }
    if (respuesta.acceso !== 'habilitado') return;
    navegar('/');
  }

  /** Traduce un rechazo del servidor a lo que hay que enseñar. Nunca a un éxito. */
  function motivoDe(error) {
    const clase = clasificar(error);
    if (clase === 'mantenimiento') {
      sesion.aplicarAcceso('mantenimiento');
      estado = null;
      return '';
    }
    if (clase === 'sin-sesion') {
      sesion.sincronizar();
      return '';
    }
    // El `detalle` lo redacta el servidor y no contiene datos de nadie; es más
    // útil que un texto genérico porque nombra la regla concreta que falló.
    return error?.detalle || describir(error).titulo;
  }

  async function cargar() {
    if (!sesion.autenticada) {
      cargando = false;
      estado = null;
      return;
    }
    cargando = true;
    fallo = null;
    try {
      if (codigoDocumento) {
        estado = null;
        return;
      }
      estado = await onboarding.estado();
      sesion.aplicarAcceso(
        estado.acceso,
        estado.tutoria_academica_sin_investigacion
      );
      if (estado.acceso === 'habilitado') {
        navegar('/');
        return;
      }
      // Las versiones y la identidad hacen falta cuando hay algo que decidir o
      // que enseñar.
      //
      // ⚠️ **También en un bloqueo con salida** (`D1B` bis): sin las versiones,
      // la decisión que se ofrece debajo del panel saldría deshabilitada por
      // «falta el documento» aunque el documento exista, y la salida volvería a
      // estar cerrada — esta vez sin decir por qué.
      if (!enBloqueo || estado.decision?.requerida === true || representanteEsPasoActual) {
        // `Promise.allSettled` y no `all`: que falle la identidad —cosmética—
        // no puede impedir que se pinte el documento que hay que aceptar.
        const [v, s] = await Promise.allSettled([
          consentimiento.versiones(),
          sesionApi.consultar()
        ]);
        if (v.status === 'fulfilled') {
          versiones = v.value;
          versionesNoDisponibles = false;
        } else {
          versiones = null;
          versionesNoDisponibles = true;
        }
        if (s.status === 'fulfilled') {
          identidad = { nombre: s.value?.nombre ?? '', correo: s.value?.correo ?? '' };
        }
      }
    } catch (e) {
      const clase = clasificar(e);
      if (clase === 'sin-sesion') {
        // No es un fallo: es la entrada institucional. `sincronizar()` deja el
        // estado compartido coherente y la plantilla pinta la puerta.
        await sesion.sincronizar();
        estado = null;
      } else if (clase === 'mantenimiento') {
        // `EQ-024` · se representa como estado, no como error de red ni como
        // formulario vacío. `PanelDeEstado` lo pinta y ofrece reintentar.
        estado = null;
        sesion.aplicarAcceso('mantenimiento');
      } else {
        fallo = describir(e);
      }
    } finally {
      cargando = false;
    }
  }

  async function guardarPerfil(valores) {
    errorDelPerfil = '';
    try {
      aplicarRespuesta(await onboarding.guardarPerfil(valores));
    } catch (e) {
      errorDelPerfil = motivoDe(e);
      // Se relanza para que el formulario sepa que no salió y cierre su
      // diálogo conservando lo escrito.
      throw e;
    }
  }

  async function subirEvidencia(archivo) {
    errorDeEvidencia = '';
    reservaPendiente = false;
    try {
      const respuesta = await consentimiento.cargarEvidencia(archivo);
      aplicarRespuesta(respuesta);
    } catch (e) {
      // El 503 con `reserva_pendiente` del hito R4 no es un fallo limpio: el
      // archivo llegó y su custodia quedó a medias. Se dice tal cual.
      if (e?.cuerpo?.reserva_pendiente) reservaPendiente = true;
      else if (clasificar(e) === 'tiempo-agotado') {
        // Un timeout no demuestra que el servidor no guardó el archivo.
        // Consultar su estado antes de ofrecer un segundo intento evita
        // duplicarlo si terminó de llegar después de cortar la conexión.
        await actualizarRepresentante();
        if (estado?.representante?.estado === 'documento_recibido') return;
        errorDeEvidencia = 'La carga tardó demasiado y no pudimos confirmar si llegó. Comprueba su estado antes de enviarla otra vez.';
      } else errorDeEvidencia = motivoDe(e);
      throw e;
    }
  }

  async function descargarFormato() {
    if (!await confirmarAccion({ tipo:'descarga', titulo:'¿Descargar formato para acudiente?',
      descripcion:'Se preparará el PDF de autorización para que tu representante pueda revisarlo y firmarlo.', confirmar:'Descargar PDF' })) return false;
    await consentimiento.descargarFormatoRepresentante();
    toast.descarga('Descargando formato de autorización en PDF.');
    return true;
  }

  async function actualizarVersiones() {
    try {
      versiones = await consentimiento.versiones();
      versionesNoDisponibles = false;
    } catch {
      versiones = null;
      versionesNoDisponibles = true;
    }
  }

  /**
   * Actualiza únicamente el estado sensible a la revisión. No sustituye la
   * pantalla por un cargador ni enseña fallos transitorios de red: la persona
   * conserva la constancia de que su documento está en revisión.
   */
  async function actualizarRepresentante() {
    if (refrescandoRepresentante || !sesion.autenticada) return;
    refrescandoRepresentante = true;
    try {
      const respuesta = await onboarding.estado();
      estado = respuesta;
      sesion.aplicarAcceso(
        respuesta.acceso,
        respuesta.tutoria_academica_sin_investigacion
      );
      if (respuesta.acceso === 'habilitado') navegar('/');
    } catch (e) {
      if (clasificar(e) === 'sin-sesion') await sesion.sincronizar();
    } finally {
      refrescandoRepresentante = false;
    }
  }

  /**
   * La única acción visible · `D0` §10.10.
   *
   * **Una petición.** El servidor decide cuántos actos escribe y los guarda en
   * una transacción; aquí no se encadena nada ni se compone ningún
   * `Promise.all`, que es la solución falsa que la decisión descarta.
   */
  async function decidir(decision) {
    errorDeDecision = '';
    sinVersionAlDecidir = false;
    motivoDeLaPolitica = '';
    alcancesFaltantes = [];
    avisoEnviado = null;
    try {
      const respuesta = await consentimiento.decidirConjunta(decision);
      // `D2` · se lee ANTES de aplicar la respuesta, porque `aplicarRespuesta()`
      // puede navegar al tutor. Sólo aplica al otorgamiento: en un rechazo el
      // servidor devuelve `false` porque no había aviso que enviar, y
      // enseñárselo a alguien como «el correo no pudo enviarse» sería
      // contarle un fallo que no existió.
      avisoEnviado = decision === 'otorgado' ? (respuesta?.aviso_enviado ?? null) : null;
      // Si la decisión abre el tutor se entra directamente. La constancia y el
      // estado del aviso siguen disponibles en «Mis datos»; interponer una
      // segunda pantalla de confirmación repetía una decisión ya terminada.
      aplicarRespuesta(respuesta);
    } catch (e) {
      // Tres desenlaces que se arreglan de formas distintas, y por eso se
      // distinguen por el cuerpo y no por el 409 que comparten.
      const cual = e?.estadoDelServidor;
      if (cual === 'sin_version') {
        // Falta publicar algún documento. No se guardó nada.
        sinVersionAlDecidir = true;
        alcancesFaltantes = e?.cuerpo?.alcances_faltantes ?? [];
      } else if (cual === 'decision_ya_vigente' || cual === 'usar_revocacion') {
        // La política del servidor dice que no hay decisión pendiente. Se
        // recarga el estado para que la pantalla refleje lo que de verdad hay:
        // este caso llega, sobre todo, cuando otra pestaña ya decidió.
        motivoDeLaPolitica = e?.detalle || '';
        cargar();
      } else {
        errorDeDecision = motivoDe(e);
      }
      throw e;
    }
  }

  $effect(() => {
    // Se vuelve a cargar cuando cambia si hay sesión: entrar con Google desde
    // esta misma pantalla tiene que traer el recorrido sin recargar la página.
    sesion.autenticada;
    cargar();
  });

  $effect(() => {
    // El operador puede publicar el formato mientras el menor espera aquí.
    // Al volver a la pestaña o mientras se espera un documento se reconsulta
    // sin exigir cerrar sesión. No se sondea una versión que ya está presente.
    if (!sesion.autenticada || !representanteEsPasoActual) return;
    const alVolver = () => {
      if (globalThis.document?.visibilityState !== 'hidden') void actualizarVersiones();
    };
    globalThis.addEventListener?.('focus', alVolver);
    globalThis.document?.addEventListener?.('visibilitychange', alVolver);
    const intervalo = !versiones?.representante || versiones.representante.formato_disponible === false
      ? globalThis.setInterval(alVolver, 20_000)
      : null;
    return () => {
      if (intervalo !== null) globalThis.clearInterval(intervalo);
      globalThis.removeEventListener?.('focus', alVolver);
      globalThis.document?.removeEventListener?.('visibilitychange', alVolver);
    };
  });

  $effect(() => {
    const esperandoRevision =
      sesion.autenticada && estado?.representante?.estado === 'documento_recibido';
    if (!esperandoRevision) return;

    const alVolver = () => {
      if (globalThis.document?.visibilityState !== 'hidden') void actualizarRepresentante();
    };
    const intervalo = globalThis.setInterval(alVolver, 4_000);
    globalThis.addEventListener?.('focus', alVolver);
    globalThis.document?.addEventListener?.('visibilitychange', alVolver);
    return () => {
      globalThis.clearInterval(intervalo);
      globalThis.removeEventListener?.('focus', alVolver);
      globalThis.document?.removeEventListener?.('visibilitychange', alVolver);
    };
  });

  $effect(() => {
    const rechazado = estado?.representante?.estado === 'rechazado';
    if (rechazado && !rechazoAnunciado) {
      motivoDelRechazo = String(estado?.representante?.motivo ?? '').trim();
      dialogoDeRechazoAbierto = true;
      rechazoAnunciado = true;
    } else if (!rechazado) {
      rechazoAnunciado = false;
    }
  });
</script>

<section class="recorrido" class:modo-documento={Boolean(codigoDocumento)} class:modo-entrada={!sesion.autenticada && sesion.sincronizada}>
  <div class="tarjeta" class:tarjeta-documento={Boolean(codigoDocumento)} class:tarjeta-entrada={!sesion.autenticada && sesion.sincronizada} class:tarjeta-representante={representanteEsPasoActual}>
    <header class="encabezado">
      <div class="encabezado-superior">
        <div class="marca">
          <Icono nombre="escudo" medida={13} />
          <span>DidaxIa · Acceso y privacidad</span>
        </div>
        {#if sesion.autenticada && !codigoDocumento}
          <div class="salir-del-registro"><EntrarConGoogle /></div>
        {/if}
      </div>
      <h1>{titulo}</h1>
    </header>

    {#if !sesion.autenticada && sesion.sincronizada}
      <EntradaInstitucional />

    {:else if cargando || !sesion.sincronizada}
      <CargadorCubo mensaje="Comprobando tu estado…" />

    {:else if fallo}
      <Degradacion respuesta={fallo} alReintentar={cargar} />

    {:else if codigoDocumento}
      <div class="documento-independiente">
        <p class="aviso-documento">
          Esta copia se sirve sólo dentro de tu sesión y el servidor comprueba
          su huella antes de mostrarla. Puedes cerrar esta pestaña al terminar.
        </p>
        <DocumentoDeLaVersion codigo={codigoDocumento} rotulo="documento vigente" pagina />
      </div>

    {:else if representanteEsPasoActual}
      <PanelDelRepresentante
        representante={estado.representante}
        version={versiones?.representante ?? null}
        alDescargar={descargarFormato}
        alSubir={subirEvidencia}
        errorDelServidor={errorDeEvidencia}
        {reservaPendiente}
        motivo={estado.representante?.motivo ?? ''}
        {versionesNoDisponibles}
        alReintentarVersiones={actualizarVersiones}
        alComprobarEstado={actualizarRepresentante}
      />

    {:else if enBloqueo}
      <!--
        `D1B` bis · el panel explica, y si hay salida se ofrece debajo.

        Un bloqueo por rechazo o por revocación de UNA dimensión puede
        deshacerse volviendo a decidir; el servidor lo dice en
        `estado.decision.requerida` y aquí se consume. Sin esto, quien revocaba
        su asentimiento quedaba mirando una pantalla que sólo sabía decirle que
        estaba bloqueado.
      -->
      <PanelDeEstado {acceso} alReintentar={cargar} />

      {#if bloqueoConSalida}
        <div class="salida-del-bloqueo">
          <p class="explica-salida">
            Puedes volver a decidir ahora. Se registrará como una decisión nueva
            y lo anterior se conserva: nada de lo que ya existe se borra.
          </p>
          <DecisionConjunta
            {esMenor}
            versionTitular={versiones?.titular ?? null}
            versionAsentimiento={versiones?.asentimiento ?? null}
            alDecidir={decidir}
            errorDelServidor={errorDeDecision}
            sinVersion={sinVersionAlDecidir}
            {alcancesFaltantes}
            {puedeAceptar}
            {puedeRechazar}
            {motivoDeLaPolitica}
          />
        </div>
      {/if}

    {:else if faltaPerfil}
      <FormularioDePerfil
        perfil={estado.perfil}
        {identidad}
        alGuardar={guardarPerfil}
        errorDelServidor={errorDelPerfil}
      />

    {:else if faltaDecision}
      <!--
        `D1B` · UNA SOLA ACCIÓN VISIBLE, PARA ADULTO Y PARA MENOR.

        La misma pieza en los dos casos: lo único que cambia es que a un menor
        se le exige además la versión del asentimiento, y que el servidor
        escribirá dos actos en vez de uno. Dos componentes habrían acabado
        validando distinto.
      -->
      <DecisionConjunta
        {esMenor}
        versionTitular={versiones?.titular ?? null}
        versionAsentimiento={versiones?.asentimiento ?? null}
        alDecidir={decidir}
        errorDelServidor={errorDeDecision}
        sinVersion={sinVersionAlDecidir}
        {alcancesFaltantes}
        {puedeAceptar}
        {puedeRechazar}
        {motivoDeLaPolitica}
      />

    {:else}
      <!--
        Adulto, perfil completo y consentimiento al día, y aun así no habilitado.
        No debería ocurrir: es justo el estado que `calcular_acceso()` habilita.
        Se dice que no se puede explicar, en vez de fingir un éxito o un trámite.
      -->
      <p class="paso-pendiente">
        Tu perfil y tu autorización están al día, pero el sistema todavía no
        habilita el tutor. Vuelve a comprobarlo en un momento; si sigue igual,
        avisa al equipo del proyecto.
      </p>
    {/if}

    <!--
      `D1B` · UN RECIBO POR ACTO, y no uno «de la decisión».

      Un menor recibe dos: cada uno con su versión, su huella, su secuencia y su
      momento, que es lo que permite localizar la fila y recomputar el
      comprobante. Fundirlos habría producido un comprobante que no corresponde
      a ninguna fila.
    -->
    <!--
      `D2` · QUÉ PASÓ CON EL CORREO, DESPUÉS DE SABERLO.

      Va junto a los recibos y no en el diálogo de confirmación: ahí todavía no
      se sabe si el envío saldrá, y anunciarlo antes dejaría a alguien esperando
      un correo que quizá no llega —o dudando de si su decisión se guardó—.

      Las dos redacciones dicen primero lo que de verdad importa —que la decisión
      quedó registrada— y sólo después qué pasó con el aviso, porque `EQ-024`
      dice que el canal informa y no decide.
    -->
    {#if !representanteEsPasoActual}
      {#if avisoEnviado === true}
        <p class="aviso-correo" role="status">
          Tu decisión quedó guardada y te enviamos la confirmación a tu correo
          institucional.
        </p>
      {:else if avisoEnviado === false}
        <p class="aviso-correo sin-correo" role="status">
          Tu decisión quedó guardada. El correo de confirmación no pudo enviarse;
          la constancia sigue disponible en «Mis datos».
        </p>
      {/if}

      {#each recibos as unRecibo (unRecibo.alcance + unRecibo.secuencia)}
        <ReciboDelActo recibo={unRecibo} />
      {/each}
    {/if}

    <!--
      `D1A` · LOS TEXTOS PÚBLICOS, ALCANZABLES DESDE AQUÍ Y EN TODOS LOS PASOS.

      Va fuera de la cadena de `{:else if}` a propósito: quien todavía no ha
      entrado, quien está rellenando el perfil y quien ya quedó bloqueado
      necesitan los mismos tres documentos, y colgados de un paso concreto
      habrían desaparecido justo en los estados donde más falta hacen.

      Los enlaces salen de `nucleo/configuracion/origenes.js` y llevan el
      origen público delante —`absolutos`—: relativos apuntarían a
      `app.didaxia.pro/privacidad`, que no existe.

      ⚠️ **`D1B` YA SUSTITUYÓ LA SECUENCIA.** Este bloque sigue igual y sigue
      fuera de la cadena de pasos, pero la decisión de arriba es ahora una sola
      —«Acepto y continuar»— con los actos guardados atómicamente por el
      servidor. `DecisionConjunta.svelte` repite los enlaces de privacidad,
      condiciones e investigación **dentro de cada sección**, para que quien lee
      un resumen tenga ahí mismo el texto que lo desarrolla; éste los conserva
      para los pasos que no son la decisión.
    -->
    {#if !representanteEsPasoActual}
      <div class="publicos">
        <p class="rotulo-publicos">Antes de decidir</p>
        <p class="nota-publicos">
          Estos textos explican qué información se prevé tratar, quién puede
          verla, para qué se utiliza y qué puedes pedir antes de decidir.
        </p>
        <EnlacesPublicos absolutos rotulo="Documentos públicos del proyecto" />
      </div>
    {/if}
    {#if sesion.autenticada && !codigoDocumento}
      <ReportarProblema compacto />
    {/if}
  </div>
</section>

{#if estado?.representante?.estado === 'rechazado'}
  <Dialogo bind:abierto={dialogoDeRechazoAbierto} titulo="Debes corregir la autorización">
    <div class="explicacion-rechazo">
      <p>El equipo investigador revisó el PDF y solicitó una corrección:</p>
      <blockquote>{motivoDelRechazo || 'Revisa el documento firmado antes de enviarlo de nuevo.'}</blockquote>
      <p>El intento anterior se conserva. Descarga el formato si lo necesitas y sube un PDF corregido para una nueva revisión.</p>
    </div>
    {#snippet acciones()}
      <Boton onclick={() => (dialogoDeRechazoAbierto = false)}>Entendido</Boton>
    {/snippet}
  </Dialogo>
{/if}

<style>
  .documento-independiente { display: flex; flex-direction: column; gap: 0.75rem; }
  .aviso-documento { margin: 0; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .recorrido {
    flex: 1;
    inline-size: 100%;
    min-block-size: 0;
    overflow-y: auto;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 16px 14px;
    background: var(--surface-canvas);
  }

  .tarjeta {
    display: flex;
    flex-direction: column;
    gap: 12px;
    inline-size: 100%;
    min-inline-size: 0;
    max-inline-size: 560px;
    background: var(--surface-panel);
    padding: 22px 24px;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-card);
    box-sizing: border-box;
  }

  .recorrido.modo-documento { padding: clamp(12px, 2vw, 28px); }

  .tarjeta.tarjeta-documento {
    max-inline-size: 1080px;
    padding: clamp(18px, 3vw, 40px);
  }

  .tarjeta.tarjeta-entrada { max-inline-size: 920px; }
  .tarjeta.tarjeta-representante { max-inline-size: 620px; }

  .tarjeta-documento .documento-independiente {
    inline-size: 100%;
    max-inline-size: 900px;
    margin-inline: auto;
  }

  .encabezado { display: flex; flex-direction: column; gap: 4px; }
  .encabezado-superior { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .salir-del-registro { flex: none; }
  .salir-del-registro :global(.salir) { inline-size: auto; min-block-size: 36px; }

  .marca {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 8px;
    background: var(--accent-surface);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 600;
    border-radius: var(--radius-pill);
    inline-size: fit-content;
  }

  h1 {
    margin: 4px 0 0;
    font-size: var(--texto-2xl);
    font-weight: 700;
    color: var(--ink-primary);
    letter-spacing: -0.02em;
    line-height: 1.2;
  }

  /* `D1B` bis · la salida de un bloqueo, separada del panel que lo explica. */
  .salida-del-bloqueo {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-block-start: 12px;
    border-block-start: 1px solid var(--ink-ghost);
  }

  .explica-salida {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.5;
    color: var(--ink-secondary);
  }

  .paso-pendiente {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  .explicacion-rechazo { display: grid; gap: 10px; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.5; }
  .explicacion-rechazo p { margin: 0; }
  .explicacion-rechazo blockquote {
    margin: 0;
    padding: 10px 12px;
    border-inline-start: 3px solid var(--semantic-warning);
    border-radius: var(--radius-xs);
    background: var(--surface-panel);
    color: var(--ink-primary);
  }

  /*
    `D2` · el resultado del aviso por correo. No es un error ni un éxito del
    trámite —el trámite ya está registrado en los dos casos—, así que usa el
    tono informativo de la tarjeta y no el rojo de `.error-servidor`.
  */
  .aviso-correo {
    margin: 0;
    padding: 8px 10px;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--ink-secondary);
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-inline-start: 3px solid var(--accent-main);
    border-radius: var(--radius-xs);
  }

  .aviso-correo.sin-correo { border-inline-start-color: var(--ink-tertiary); }

  /* `D1A` · el bloque de documentos públicos, al pie de la tarjeta. */
  .publicos {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-block-start: 12px;
    border-block-start: 1px solid var(--ink-ghost);
  }

  .rotulo-publicos {
    margin: 0;
    font-size: var(--texto-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-tertiary);
  }

  .nota-publicos {
    margin: 0;
    font-size: var(--texto-xs);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  @media (max-width: 75rem) {
    .recorrido { padding: 12px 10px; }
    .tarjeta { padding: 18px 16px; }
  }

  @media (max-width: 75rem) {
    .encabezado-superior { align-items: stretch; flex-direction: column; }
    .salir-del-registro :global(.salir) { inline-size: 100%; }
  }
</style>
