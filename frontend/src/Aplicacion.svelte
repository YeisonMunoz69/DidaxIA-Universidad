<!--
Componente raíz.

Resuelve el enrutado, aplica las guardas y monta la ruta que corresponda al
rol vigente. No pinta contenido propio: pinta el MARCO, y desde el
2026-08-22 el marco mismo vive repartido en piezas —`comun/armazon/
Carril.svelte` y `comun/armazon/CabeceraGlobal.svelte`—, no todo aquí. Este
archivo compone esas piezas y decide QUÉ pantalla se monta; ellas deciden
CÓMO se ve el carril y la cabecera. Antes de esa fecha las tres cosas vivían
juntas en un solo archivo que crecía con cada pantalla nueva de docente o
estudiante que necesitara tocar el marco — el mismo síntoma que llevó a
partirlo.

EL CARRIL SUSTITUYE A LAS PESTAÑAS, Y ESO ES UNA DECISIÓN DE DISTRIBUCIÓN
--------------------------------------------------------------------------
Hasta el 2026-08-16 la navegación eran seis enlaces en una barra superior y una
página entera por enlace: para ver una conversación anterior había que SALIR de
la conversación, y para revisar qué datos tiene el sistema sobre uno, también.

El mockup que vieron las docentes ya lo resolvía de otra manera —`pc.html`— y es
la que se adopta: **historial y perfil son el marco permanente desde el que se
trabaja, no sitios a los que ir y volver.** El reparto exacto vive en
`rutasDeZona()`.

⚠️ **`D-20` declara la navegación de cada rol y todavía dice «pestañas».** Este
carril no añade ni quita ningún camino —los doce siguen siendo los mismos— pero
sí cambia dónde se alcanzan, así que la figura debería reflejarlo. Está anotado
en `rutas.js` junto al reparto.

⚠️ LO QUE CAMBIÓ EN C1, Y ERA MEDIA PÁGINA DE ESTA CABECERA
-------------------------------------------------------------
Aquí decía que identificarse era una vía más y nunca un peaje, que `RP-02`
abría sesión a quien llegara y que el tutor se usaba sin cuenta. `EQ-020` lo
sustituyó entero: **sólo se entra con cuenta institucional**, el backend no crea
sesión al consultar una ruta pública y `POST /api/sesion` responde 401. Sin
sesión no hay tutor y lo que se pinta es la entrada institucional.

`EntrarConGoogle` sigue estando en el pie del carril y **«Mis datos» sigue sin
quedar detrás de más trámite del necesario**: los derechos del titular se
alcanzan en todos los estados de bloqueo —así lo declara la allowlist de
`nucleo/sesion/acceso.js`—, porque quien rechazó, revocó o pidió la supresión es
justo quien más necesita llegar a ellos.

EL ENRUTADO USA LA HISTORIA DEL NAVEGADOR, NO EL FRAGMENTO
------------------------------------------------------------
Direcciones de verdad —`/supervision`, no `/#/supervision`—, que es lo que
permite compartir un enlace a una pantalla. Pide que el servidor devuelva el
documento para cualquier camino; en desarrollo lo hace `vite.config.js` y en
producción es una línea de configuración del servidor estático.

LA GUARDA SE APLICA EN CADA CAMBIO, NO SOLO AL ENTRAR
-------------------------------------------------------
Porque el acceso calculado y el rol pueden cambiar sin recargar: quien completa
el perfil y otorga el consentimiento pasa de retenido a habilitado en la misma
sesión, y quien revoca pasa de habilitado a bloqueado. Con la guarda solo en el
arranque, el primero seguiría atrapado y el segundo seguiría dentro.

Y SIGUE SIN SER SEGURIDAD. §11: la negativa efectiva la ejerce el servidor.
Esto evita llegar a una pantalla que va a rechazarnos, nada más.


Lenguaje declarado en OE3-Implementacion/13-Lenguaje-de-Diseno.md

-->
<script>
  import ArchivoPreparado from './comun/estado/ArchivoPreparado.svelte';
  import { lectura } from './nucleo/lectura/lectura.svelte.js';
  import { onMount } from 'svelte';
  import { seguirVentanaVisible } from './nucleo/presentacion/ventanaVisible.js';
  import SaltarAlContenido from './comun/base/SaltarAlContenido.svelte';
  import Ajustes from './comun/preferencias/Ajustes.svelte';
  import Carril from './comun/armazon/Carril.svelte';
  import CabeceraGlobal from './comun/armazon/CabeceraGlobal.svelte';
  import ContenidoDeRuta from './comun/armazon/ContenidoDeRuta.svelte';
  import AvisoDeConsultaProfesional from './comun/estado/AvisoDeConsultaProfesional.svelte';
  import ContenedorDeToasts from './comun/estado/ContenedorDeToasts.svelte';
  import ContenedorDeConfirmaciones from './comun/estado/ContenedorDeConfirmaciones.svelte';
  import { esEstudiante } from './nucleo/sesion/rol.js';
  import { rutaDe, rutasDeZona, inicioDe } from './enrutado/rutas.js';
  import { resolver, arbolDe, navegar } from './enrutado/guardas.js';
  import { sesion } from './nucleo/sesion/sesion.svelte.js';
  import { espacio } from './nucleo/espacio/espacio.svelte.js';
  import { historial } from './nucleo/historial/historial.svelte.js';
  import { preferencias } from './nucleo/preferencias/preferencias.svelte.js';
  import { aplicarColores } from './nucleo/preferencias/colores.js';
  import { untrack } from 'svelte';

  let camino = $state(globalThis.location?.pathname ?? '/');
  let consulta = $state(globalThis.location?.search ?? '');
  let carrilAbierto = $state(false);
  let masAbierto = $state(false);
  let ajustesAbiertos = $state(false);
  onMount(() => {
    const raiz = document.getElementById('aplicacion');
    return raiz ? seguirVentanaVisible(raiz).destroy : undefined;
  });

  sesion.sincronizar();

  /** El historial exige sesión AUTENTICADA (§13.4) — anónima no basta, y
      `cargarLista()` es idempotente, así que reintentar aquí en cada cambio
      de `autenticada` no repite la petición una vez que ya cargó.

      `recuperarSiHaceFalta()` cubre F5 dentro de una conversación retomada:
      `sesionVista` sobrevive la recarga por `sessionStorage`
      (`historial.svelte.js`), pero `hiloVisto` solo vive en memoria y se
      pierde, así que sin esto el carril marcaba la conversación como
      activa mientras el panel de chat se quedaba vacío hasta un clic más
      en la lista.

      `untrack()` NO ES OPCIONAL AQUÍ · 2026-08-22.
      `cargarLista()`/`recuperarSiHaceFalta()` leen y escriben SU PROPIO
      estado de control —`cargandoLista`, `listaCargada`, `cargandoHilo`—
      de forma síncrona antes del primer `await`. Llamadas directamente
      desde este efecto, esas lecturas lo vuelven dependiente de ese
      estado, y la escritura que sigue («ya estoy cargando») lo vuelve a
      disparar — sin `sesion.autenticada` haber cambiado. Si la petición
      FALLA, `listaCargada`/`hiloVisto` nunca llegan al valor que corta el
      ciclo (`cargarLista`/`ver` solo los fijan en el `try`, no en el
      `catch`), así que el efecto se reprograma indefinidamente: se midió
      con `/api/historial` fallando en bucle, más de 200 peticiones por
      segundo, sin que nada en pantalla lo delatara. `untrack()` saca esas
      lecturas del rastreo: el efecto vuelve a depender solo de
      `sesion.autenticada`, que es la única razón por la que debería
      volver a llamar a esto.

      `arbol === 'estudiante'` SE SUMÓ EL 2026-08-22, JUNTO CON EL RESTO DEL
      CARRIL DE ABAJO. El historial es un concepto de conversación —no
      existe para un docente ni para un investigador—, y antes de esta
      fecha el único filtro era `sesion.autenticada`, que no distingue rol:
      un docente autenticado disparaba esta llamada igual, contra una ruta
      que no tiene nada que decirle, y el 401/503 que a veces devolvía se
      leía en el carril como «Tu sesión caducó» sin que la sesión del
      docente tuviera nada malo. */
  $effect(() => {
    if (sesion.autenticada && arbol === 'estudiante') {
      untrack(() => {
        historial.cargarLista();
        historial.recuperarSiHaceFalta();
      });
    }
  });

  // Atrás y adelante del navegador, y también lo que `navegar()` emite: una
  // sola vía para los dos casos.
  $effect(() => {
    const alVolver = () => { camino = globalThis.location.pathname; consulta = globalThis.location.search; };
    globalThis.addEventListener('popstate', alVolver);
    return () => globalThis.removeEventListener('popstate', alVolver);
  });

  /*
    EL TEMA SE APLICA AL `<body>` Y NO A UN NODO DE AQUÍ.

    `tokens.css` declara el tema oscuro sobre `body.dark-theme`, y el velo de
    `<dialog>` lo pinta el navegador FUERA del árbol de la aplicación: puesto
    en un nodo interior, un diálogo abierto en tema oscuro se recortaría sobre
    un velo del tema claro.

    `sistema` no escribe nada: deja que mande `prefers-color-scheme`, y por eso
    se escucha el cambio — quien tiene el equipo en automático cambia de tema al
    anochecer y la aplicación tiene que seguirlo sin recargar.
  */
  /** Si el sistema pide oscuro. Se sigue en vivo: quien lo tiene en automático
      cambia al anochecer y la aplicación tiene que seguirlo sin recargar. */
  let sistemaOscuro = $state(
    globalThis.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  );

  const temaOscuro = $derived(
    preferencias.tema === 'oscuro' ||
    (preferencias.tema === 'sistema' && sistemaOscuro)
  );

  $effect(() => {
    const consulta = globalThis.matchMedia?.('(prefers-color-scheme: dark)');
    const alCambiar = () => { sistemaOscuro = Boolean(consulta?.matches); };
    consulta?.addEventListener('change', alCambiar);
    return () => consulta?.removeEventListener('change', alCambiar);
  });

  $effect(() => {
    globalThis.document?.body?.classList.toggle('dark-theme', temaOscuro);
    aplicarColores(preferencias.colores, temaOscuro);
  });

  $effect(() => {
    globalThis.document?.documentElement?.setAttribute('data-escala', preferencias.escalaTexto);
    globalThis.document?.documentElement?.setAttribute('data-animaciones', preferencias.animaciones ? 'si' : 'no');
  });

  /**
   * El árbol lo deciden AHORA el rol y el espacio activo · `EQ-031`.
   *
   * Un docente en espacio Tutor monta el árbol del estudiante —conversación,
   * conceptos, biblioteca— sin dejar de ser docente. La frontera de `DD-04`
   * no se movió: lo que cambió es quién la cruza, y con qué permisos, que los
   * decide `rutas.js::puedeAbrir()` y no este archivo.
   */
  const arbol = $derived(arbolDe(sesion.rol, espacio.activo));
  /**
   * El inicio de ESTE ROL, resuelto una sola vez y repartido · C2B.
   *
   * Antes cada consumidor escribía `INICIO[arbol]`, y con tres roles en dos
   * árboles eso mandaba a una investigadora a `/supervision`. Siete archivos
   * calculaban el inicio; la octava copia habría discrepado. Ahora hay una
   * función —`rutas.js::inicioDe()`— y esta línea es el único sitio de la
   * aplicación que la llama para el armazón: lo demás lo recibe resuelto.
   */
  const inicio = $derived(inicioDe(sesion.rol, espacio.activo));
  const destino = $derived(resolver(camino, {
    rol: sesion.rol,
    // Preferencia de interfaz, NO autorización: `resolver()` la valida contra
    // el rol del servidor antes de usarla (`espacios.js::normalizarEspacio`).
    espacio: espacio.activo,
    // El estado que CALCULA el servidor (`GET /api/onboarding/estado`), no un
    // campo de consentimiento que el cliente interprete. Ver `guardas.js`.
    acceso: sesion.acceso,
    tutoriaAcademicaSinInvestigacion: sesion.tutoriaAcademicaSinInvestigacion,
    autenticada: sesion.autenticada
  }));

  // La guarda redirige DE VERDAD: cambia la dirección además de lo que se
  // pinta. Pintar una pantalla distinta de la que dice la barra de direcciones
  // deja al usuario sin saber dónde está, y el botón de atrás deja de tener
  // sentido.
  $effect(() => {
    // NO SE DECIDE ANTES DE SABER QUIÉN ES. Sin esta condición, al abrir
    // cualquier dirección el rol vale «estudiante» y el consentimiento
    // «pendiente» durante un instante, la guarda redirige a la autorización y
    // **la dirección pedida se pierde**. Pasaba al abrir `/supervision` con
    // sesión de docente, y el síntoma —acabar en el consentimiento— apuntaba a
    // la guarda cuando el problema era cuándo se le preguntaba.
    if (sesion.sincronizada && destino !== camino) {
      globalThis.history?.replaceState({}, '', destino);
      camino = destino;
    }
  });

  /*
   * `T-13`: SIN RESPALDO A `INICIO[arbol]`, A PROPÓSITO.
   *
   * Hasta el 2026-08-20 decía `rutaDe(destino) ?? rutaDe(INICIO[arbol])`, así
   * que un camino que no existe pintaba en silencio la pantalla de inicio
   * como si fuera la que se pidió — la misma degradación silenciosa que
   * `07-Estructura-del-Frontend.md` prohíbe para un estático que falta.
   * `null` aquí es la señal que `<main>` usa para pintar la vista de «esta
   * dirección no existe», en vez de fingir que se pidió otra cosa.
   */
  const ruta = $derived(rutaDe(destino));
  // `sesion.rol` entra en las tres: una ruta con allowlist —hoy sólo
  // `/evidencias`— no se ofrece a quien no está en ella, y sin el rol
  // `rutasDeZona()` la esconde a todo el mundo en vez de publicarla.
  const principales = $derived(rutasDeZona(arbol, 'principal', sesion.rol, espacio.activo));
  const secundarias = $derived(rutasDeZona(arbol, 'pie', sesion.rol, espacio.activo));
  const perfilables = $derived(rutasDeZona(arbol, 'perfil', sesion.rol, espacio.activo));
  const perfilesDelCarril = $derived(espacio.puedeElegir
    ? rutasDeZona('no-estudiante', 'perfil', sesion.rol, 'profesional') : perfilables);
  const retenido = $derived(destino === '/consentimiento');

  /**
   * 2026-08-22 · el carril deja de montarse para `no-estudiante`.
   *
   * Antes de añadir `/mi-perfil`, `perfilables` estaba vacío para ese árbol,
   * así que el carril solo pintaba logo, «Cerrar sesión» y Ajustes: 16rem de
   * columna fija para tres controles. Ninguna ruta `no-estudiante` es
   * `abierta: true` (solo `/consentimiento`, de estudiante), así que
   * `conCarril` restringido a estudiante hace que `Carril.svelte` no se
   * monte NUNCA para docente/investigador, sin tocar ese componente por
   * dentro.
   */
  // Los recursos se consultan en una pestaña aparte: deja todo el ancho para
  // el material. La barra de charlas reaparece al volver al espacio del tutor.
  const recursoPublicado = $derived(destino === '/notificaciones' || destino.startsWith('/notificaciones/'));
  const conCarril = $derived(arbol === 'estudiante' && !retenido && !recursoPublicado);

  /**
   * `puedeNavegar` SE SEPARA DE `conCarril` A PROPÓSITO.
   *
   * Hasta hoy `CabeceraGlobal.svelte` gateaba la navegación
   * (`navGlobal`/«Más») con el mismo `conCarril` que gatea los botones de
   * abrir/plegar el carril, porque las dos condiciones siempre coincidían
   * —`retenido` solo existe para estudiante—. Al volver `conCarril`
   * exclusivo de estudiante, esa coincidencia se rompe: si la navegación
   * se siguiera gateando con `conCarril`, la cabecera del docente se
   * quedaría sin NINGÚN enlace, `/consentimiento` aparte. `puedeNavegar`
   * es la condición real que la navegación necesita —«no estamos en la
   * pantalla retenida»—, la misma para los dos árboles.
   */
  const puedeNavegar = $derived(!retenido);

  /**
   * `identidadEnCabecera`: docente/investigador no tiene carril donde
   * poner el logo, «Cerrar sesión» ni Ajustes — suben a la cabecera. Es
   * un booleano plano, igual que `conCarril`: `CabeceraGlobal.svelte`
   * sigue sin ninguna rama que compare `arbol` con un rol.
   */
  const identidadEnCabecera = $derived(arbol !== 'estudiante');

  /**
   * `.donde` —el título de la cabecera, en `CabeceraGlobal.svelte`— decía
   * lo mismo que el `<h1>` de la propia pantalla, los dos a la vez desde
   * el primer instante. Reportado como redundante, y lo era: el mismo
   * patrón existía también en el árbol de estudiante (`/conceptos`,
   * `/mis-datos`…), no era nuevo de esta tanda.
   *
   * `tituloDeH1Visible` se sigue con `IntersectionObserver` en vez de con
   * la posición de scroll a mano: el elemento que hace scroll cambia de
   * una pantalla a otra —`.cola-desplazable` en unas, `.hilo` en
   * Conversación, ninguno en las que no llegan a desbordar—, y
   * `IntersectionObserver` con `root: null` resuelve la intersección
   * contra el viewport real atravesando cualquier contenedor con
   * `overflow` intermedio, sin que este componente necesite saber CUÁL es
   * el contenedor de cada ruta.
   *
   * ⚠️ **El `<h1>` no está en el DOM en el instante en que este efecto se
   * dispara.** `rutas.js` carga cada pantalla con `cargar: () => import(…)`
   * —código partido, `07-Estructura-del-Frontend.md` lo pide así para que
   * el navegador de un estudiante ni siquiera descargue el árbol del
   * docente—, así que el componente de la ruta se monta de forma
   * asíncrona. Un `querySelector` directo aquí encontraba `null` casi
   * siempre —comprobado en el navegador el 2026-08-22: cero avisos del
   * observador, nunca llegaba a crearse— porque el efecto solo vuelve a
   * correr cuando cambia `destino`, y para entonces ya era tarde para
   * reintentar. Por eso se usa un `MutationObserver` sobre `<main>` como
   * «avísame cuando aparezca el `<h1>`», y no un `querySelector` a secas.
   *
   * Empieza en `true` —el `<h1>` recién montado está arriba del todo,
   * visible— para que el título de la cabecera no destelle un instante en
   * cada navegación antes de que el observador dispare su primer aviso.
   */
  let tituloDeH1Visible = $state(true);

  $effect(() => {
    void destino; // Vuelve a observar el <h1> de CADA pantalla nueva.
    const main = globalThis.document?.getElementById('contenido');
    if (!main || typeof IntersectionObserver === 'undefined' || typeof MutationObserver === 'undefined') {
      tituloDeH1Visible = true;
      return;
    }

    let observadorInterseccion = null;

    function intentarObservarH1() {
      if (observadorInterseccion) return; // Ya enganchado al <h1> de esta ruta.
      const h1 = main.querySelector('h1');
      if (!h1) return; // Todavía no montó — el `MutationObserver` volverá a llamar.
      observadorInterseccion = new IntersectionObserver(
        ([entrada]) => { tituloDeH1Visible = entrada.isIntersecting; },
        { threshold: 0 }
      );
      observadorInterseccion.observe(h1);
      observadorMutacion.disconnect(); // El <h1> de esta ruta no va a cambiar de nuevo.
    }

    const observadorMutacion = new MutationObserver(intentarObservarH1);
    observadorMutacion.observe(main, { childList: true, subtree: true });
    intentarObservarH1(); // Por si el `<h1>` ya estaba, sin esperar la primera mutación.

    return () => {
      observadorMutacion.disconnect();
      observadorInterseccion?.disconnect();
    };
  });

  /** Booleano plano para `CabeceraGlobal.svelte`, igual que `conCarril` o
      `identidadEnCabecera`: ese componente no decide CUÁNDO mostrar el
      título, solo lee si debe hacerlo. */
  const mostrarTituloCabecera = $derived(!tituloDeH1Visible);

  /**
   * «Modo zen», del mockup: las dos columnas plegadas a la vez despejan la
   * pantalla entera para la conversación. Solo tiene sentido ahí —es la
   * única ruta con un panel derecho que plegar—, así que fuera de ella
   * `modoZen` cae solo a `false` en cuanto `destino` cambia, sin que haga
   * falta un `else` que lo apague a mano.
   */
  const modoZen = $derived(
    destino === inicio && !preferencias.carrilVisible && !preferencias.panelVisible
  );

  $effect(() => {
    globalThis.document?.body?.classList.toggle('zen-mode', modoZen);
  });

  /**
   * `PM-F20`: lo que hasta hoy eran dos `<nav>` del carril —«Secciones» y
   * «Más secciones»— sube a la cabecera (`CabeceraGlobal.svelte`). El carril
   * se queda solo con las conversaciones, que es lo único que su rótulo dice.
   *
   * `/historial` ya no necesita una exclusión manual: `rutasDe()` omite las
   * entradas de compatibilidad. La dirección continúa siendo resoluble, pero
   * redirige a `/`, donde el carril pinta el historial real.
   *
   * ✅ **2026-08-22 · `INICIO[arbol]` deja de excluirse para `no-estudiante`.**
   * La exclusión nació pensada en estudiante, donde «Nueva conversación» ya
   * lleva a `/` un clic más abajo y el logo del carril hace de atajo. Para
   * docente/investigador esa misma exclusión dejaba «Cola de supervisión»
   * —`INICIO['no-estudiante']`— sin NINGÚN enlace rotulado: solo se llegaba
   * haciendo clic en el logo, sin que nada dijera adónde llevaba. Reportado
   * como «no queda nada claro». Con el carril fuera de ese árbol (ver
   * `conCarril` más arriba) tampoco queda un logo de carril que la
   * sustituya, así que ahora es un enlace normal, con su rótulo, igual que
   * las otras cuatro. Estudiante no cambia: sigue sin `/` en esta lista.
   */
  const navGlobal = $derived([
    ...principales.filter((r) =>
      arbol !== 'estudiante' || r.camino !== inicio
    ),
    ...secundarias
  ]);

  /** Navega y cierra cualquier capa transitoria abierta sobre la pantalla:
      el cajón de `Carril.svelte` y el menú «Más» de `CabeceraGlobal.svelte`.
      Vive aquí, y no en cualquiera de los dos, porque es la única pieza que
      conoce las dos capas a la vez. */
  /**
   * `EQ-031` · dónde estaba en su panel, para poder volver ahí.
   *
   * Se recuerda el destino YA RESUELTO por las guardas —nunca el pedido—, así
   * que jamás se guarda una dirección que la política rechace y a la que volver
   * sería rebotar. Con su consulta, porque `/estudiante?clase=…&id=…` sin
   * parámetros no es la misma pantalla.
   */
  $effect(() => {
    if (!sesion.sincronizada || !espacio.esProfesional) return;
    espacio.recordarProfesional(destino + (globalThis.location?.search ?? ''));
  });

  /**
   * Cambia de espacio y va a donde corresponda · `EQ-031`.
   *
   * **No cierra la sesión, no reautentica y no reinicia la conversación.** Lo
   * único que cambia es una preferencia de interfaz; el hilo del Tutor sigue en
   * `conversacion.svelte.js` y el historial en su carril, así que volver del
   * panel profesional encuentra la charla donde se dejó.
   *
   * El destino se calcula para el espacio solicitado. La preferencia cambia
   * después de aceptar la salida, para conservar el editor si se cancela.
   */
  function cambiarDeEspacio(nuevo) {
    if (nuevo === espacio.activo) return;
    // Cambiar de espacio no equivale a abandonar la conversación. `ir()` es
    // la navegación ordinaria y llama `historial.volver()`; usarla aquí
    // borraba el hilo pasado que la persona estaba retomando y contradecía la
    // promesa de este mismo bloque. Se cambia sólo la superficie visible y se
    // conservan `sesionVista`, `hiloVisto` y `necesitaRetomar` para que el
    // regreso al Tutor ocurra exactamente donde se dejó.
    navegar(espacio.destinoDe(nuevo), { alAceptar: () => {
      espacio.elegir(nuevo);
      carrilAbierto = false;
      masAbierto = false;
    } });
  }

  function abrirPerfilDelCarril(camino) {
    navegar(camino, { alAceptar: () => {
      if (espacio.puedeElegir) espacio.elegir('profesional');
      carrilAbierto = false;
      masAbierto = false;
    } });
  }

  function ir(destinoPedido) {
    navegar(destinoPedido, { alAceptar: () => {
      carrilAbierto = false;
      masAbierto = false;
      historial.volver();
    } });
  }
</script>

<SaltarAlContenido />

<div class="armazon">
  {#if conCarril && !lectura.inmersiva}
    <Carril {arbol} {inicio} {destino} perfilables={perfilesDelCarril} {navGlobal} {ir}
            irAlPerfil={abrirPerfilDelCarril}
            bind:carrilAbierto bind:ajustesAbiertos />
  {/if}

  <div class="trabajo">
    {#if !lectura.inmersiva}<CabeceraGlobal {arbol} rol={sesion.rol} {inicio} {destino} {ruta} {conCarril} {puedeNavegar} {identidadEnCabecera}
                    {mostrarTituloCabecera}
                    {navGlobal} {perfilables} {temaOscuro} {ir}
                    espacioActivo={espacio.activo}
                    puedeElegirEspacio={espacio.puedeElegir}
                    alElegirEspacio={cambiarDeEspacio}
                    bind:carrilAbierto bind:masAbierto bind:ajustesAbiertos />{/if}

    <!--
      `EQ-031` · el espacio Tutor de un profesional dice, una vez y en un
      renglón, que este uso no evalua a nadie.

      ⚠️ **Vive en el armazón y no dentro de `Conversacion.svelte`.** Dos
      motivos, y el segundo se vio en el navegador:

        1. la garantía es del ESPACIO, no de una pantalla. Un profesional que
           consulta conceptos o biblioteca en modo Tutor está igual de fuera de
           la evaluación, y el aviso lo acompaña;
        2. dentro de la conversación chocaba. `.conversacion` es una FILA —chat
           y panel de contexto— así que un hijo suyo se lleva ancho; y metido en
           la columna del chat, el botón flotante «Conceptos y gráficas» de
           teléfono —`position: absolute` contra `.conversacion`— se le encimaba.
           Aquí arriba no hay nada con lo que competir.

      La condición es el ROL y el ESPACIO: el rol lo dice el servidor y el
      espacio ya viene validado contra él. `esEstudiante()` trata lo desconocido
      como estudiante, así que un rol con errata no ve el aviso —el lado barato
      de equivocarse, porque el backend clasifica por su cuenta—.
    -->
    {#if sesion.autenticada && !esEstudiante(sesion.rol) && espacio.esTutor}
      <AvisoDeConsultaProfesional />
    {/if}

    <ContenidoDeRuta sincronizada={sesion.sincronizada} {ruta} {destino} {consulta} {arbol} {inicio} {ir} />
  </div>
</div>

<Ajustes bind:abierto={ajustesAbiertos} {arbol} {temaOscuro} />
<ContenedorDeToasts />
<ContenedorDeConfirmaciones />
<ArchivoPreparado />

<style>
  /* ── El armazón ──────────────────────────────────────────────────────
     Dos regiones a lo ancho. `base.css` le da a `#aplicacion` los 100dvh y la
     columna; aquí empieza la fila. El plegado del carril —`carrilVisible`—
     ya no se decide aquí: `Carril.svelte` lee esa preferencia directamente
     y se oculta a sí mismo, así esta regla no necesita alcanzar una clase
     puesta en un componente hijo. */

  .armazon {
    flex: 1;
    min-block-size: 0;
    display: flex;
    height: 100%;
    overflow: hidden;
  }

  /* ── La zona de trabajo ─────────────────────────────────────────────── */

  .trabajo {
    flex: 1;
    min-inline-size: 0;
    min-block-size: 0;
    display: flex;
    flex-direction: column;
    background: var(--surface-paper);
    position: relative;
    overflow: hidden;
    height: 100%;
  }

</style>
