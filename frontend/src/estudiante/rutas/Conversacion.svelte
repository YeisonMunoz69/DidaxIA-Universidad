<!--
La ruta principal.

Historial del diálogo, el redactor de entrada mixta español-notación de
RU-01, el progreso del turno mientras se espera y la respuesta con sus
sellos. Es donde vive el sistema.

LO QUE ESTA PANTALLA NO MUESTRA, Y NO ES UN OLVIDO
---------------------------------------------------
Ni ansiedad, ni autoeficacia, ni concepción candidata, ni dominio por nodo, ni
confianza del diagnóstico, ni el nombre del filtro que intervino. `D-20` lo
declaró ausente del árbol del estudiante, `RP-18` lo obliga y `DSC-03` deja
constancia de que el artefacto previo SÍ lo mostraba. Ni siquiera
indirectamente: no hay aquí ninguna señal —un color, un orden, un icono— que se
derive de esos campos.

`VectorConductual.svelte` vive bajo `docente/` justo para que importarlo desde
aquí se vea raro al leerlo.

La identidad y los límites del sistema siguen disponibles en las superficies
de acceso, condiciones y privacidad. No se repiten como dos bandas permanentes
en cada conversación: ocupaban la primera pantalla y apartaban del hilo el
contenido que la persona vino a consultar.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

-->
<script>
  import { conservarFocoAlLeer } from '../../nucleo/presentacion/ventanaVisible.js';
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { tick, onMount } from "svelte";
  import Turno from "../../comun/turno/Turno.svelte";
  import AclaracionDocente from "../../comun/turno/AclaracionDocente.svelte";

  import ProgresoDelTurno from "../../comun/estado/ProgresoDelTurno.svelte";
  import Degradacion from "../../comun/estado/Degradacion.svelte";
  import BloqueoAutenticacion from "../../comun/estado/BloqueoAutenticacion.svelte";
  import { CORREO_INSTITUCIONAL } from "../../nucleo/configuracion/institucion.js";
  import PanelDeContexto from "../piezas/PanelDeContexto.svelte";
  import { preferencias } from "../../nucleo/preferencias/preferencias.svelte.js";
  import Redactor from "../piezas/Redactor.svelte";
  import EntrarConGoogle from "../../comun/sesion/EntrarConGoogle.svelte";
  import FondoInicioMatematico from "../piezas/FondoInicioMatematico.svelte";

  import { crearEnvioDeConversacion } from "../../nucleo/conversacion/envio.svelte.js";
  import { conversacion } from "../../nucleo/conversacion/conversacion.svelte.js";
  import { sesion } from "../../nucleo/sesion/sesion.svelte.js";
  import { historial } from "../../nucleo/historial/historial.svelte.js";
  import { animarDesplazamientoAbajo } from "../../nucleo/animaciones/gsap.js";
  import * as apiSupervision from "../../nucleo/api/supervision.js";

  /**
   * Fase 5 · a dónde vuelve quien sale a leer una fuente desde un turno.
   *
   * Es la ruta canónica de la conversación y **no** `location.pathname`: se
   * puede salir estando en el historial —que es esta misma pantalla vista de
   * otra manera, `EQ-018`— y el retorno tiene que seguir siendo válido.
   */
  const RETORNO_A_LA_CONVERSACION = "/";

  /** Lo que de verdad se pinta: el hilo persistente en vivo, o el de una sesión pasada.
      El segundo se puede retomar: cada envío conserva `retomarSesion` para
      que el backend lo archive bajo la charla que se está viendo. */
  const hiloAMostrar = $derived(
    historial.viendoHistorial ? (historial.hiloVisto ?? []) : conversacion.hilo,
  );
  /** @type {HTMLElement | undefined} El área que se desplaza. */
  let areaDelHilo;

  let tecladoAbierto = $state(false);
  let editando = $state(false);
  let graficaSolicitada = $state(null);
  let aclaraciones = $state([]);
  let consultaAclaraciones = 0;

  let sesionPrevia = null;
  const claveLectura = () => `${sesion.conversacion}:${historial.viendoHistorial ? historial.sesionVista : 'actual'}`;
  const lecturaInicial = () => conversacion.recuperarLectura(claveLectura(), hiloAMostrar.length);
  const posicionDeRetorno = lecturaInicial();
  let posicionActual = posicionDeRetorno ?? 0;
  let restauracionPendiente = posicionDeRetorno !== null;
  let temporizadoresDeEntrada = [];

  async function cargarAclaraciones() {
    if (!sesion.autenticada || sesion.rol !== 'estudiante') {
      aclaraciones = [];
      return;
    }
    const hilo = historial.viendoHistorial ? historial.sesionVista : sesion.conversacion;
    if (!hilo) return;
    const actual = ++consultaAclaraciones;
    try {
      const respuesta = await apiSupervision.misAclaraciones(hilo);
      if (actual === consultaAclaraciones) aclaraciones = respuesta?.elementos ?? [];
    } catch {
      /* La conversación sigue siendo utilizable si esta lectura auxiliar cae. */
    }
  }

  function aclaracionesDelTurno(entrada) {
    if (entrada?.autor === 'estudiante') return [];
    const turno = entrada?.turno?.turno;
    if (!turno) return [];
    return aclaraciones.filter((aclaracion) => aclaracion.turno === turno);
  }

  const aclaracionesSinAncla = $derived.by(() => {
    const turnosVisibles = new Set(
      hiloAMostrar
        .filter((entrada) => entrada?.autor !== 'estudiante')
        .map((entrada) => entrada?.turno?.turno)
        .filter(Boolean),
    );
    return aclaraciones.filter(
      (aclaracion) => !aclaracion.turno || !turnosVisibles.has(aclaracion.turno),
    );
  });

  async function desplazarAbajo(forzar = false, duracion = 0.38) {
    await tick();
    if (!areaDelHilo) return;
    if (!forzar) {
      const distanciaAlFinal =
        areaDelHilo.scrollHeight -
        areaDelHilo.scrollTop -
        areaDelHilo.clientHeight;
      if (distanciaAlFinal > 450) return;
    }
    animarDesplazamientoAbajo(areaDelHilo, duracion);
  }

  const envio = crearEnvioDeConversacion({ alDesplazar: desplazarAbajo });
  const conversacionVacia = $derived(
    sesion.autenticada &&
      !historial.viendoHistorial &&
      /* La fuente de verdad del estado nuevo es el hilo activo. Usar aquí la
         proyección condicional `hiloAMostrar` podía conservar el arreglo de
         una charla histórica durante el mismo ciclo reactivo en que
         `historial.volver()` abría una conversación nueva. */
      conversacion.vacia &&
      !envio.ocupado &&
      !envio.fallo,
  );

  /**
   * Contestar el ítem de dos niveles es **un turno normal** con un campo más.
   *
   * El mensaje que acompaña dice lo que el estudiante hizo, para que el hilo
   * se lea entero después: sin él, en el historial aparecería una respuesta
   * del tutor sin nada delante. Lo que diagnostica es `dos_niveles`, no ese
   * texto — el servidor no lo interpreta como una propuesta.
   *
   * @param {{nodo: string, resultado: string, razon: string}} respuesta
   */
  async function responderSondeo(respuesta) {
    // 🔴 Paquete H · se **espera** el envío y se rechaza si no llegó. El
    // componente usa esa promesa para decidir si cierra el ítem o lo deja
    // abierto con lo escrito dentro; antes se cerraba en la línea siguiente a
    // la llamada, sin mirar si el servidor había confirmado nada.
    //
    // Una respuesta **degradada** cuenta como llegada: el turno se registró y
    // volver a contestarlo lo contaría dos veces. Lo que deja el ítem abierto
    // es que la petición no llegara.
    //
    // La clave de idempotencia **sale de la propia respuesta**, no de un
    // contador: así el reintento del componente —que vuelve a llamar aquí con
    // el mismo payload— lleva la misma clave y el servidor lo reconoce en vez
    // de contar un turno más. Sin esto, un reintento tras un error que el
    // servidor sí había procesado contaría dos veces la misma respuesta.
    const clave = `sondeo:${respuesta.nodo}:${respuesta.resultado}:${respuesta.razon}`;
    await envio.enviar(
      `Respondo a la pregunta corta: ${respuesta.resultado}`,
      respuesta,
      { idempotencia: clave },
    );
    if (!envio.entregado) {
      throw new Error("el turno no llegó al servidor");
    }
  }

  $effect(() => {
    const sesionActual = historial.sesionVista || "nueva";
    hiloAMostrar.length;
    envio.progreso.fases.length;
    envio.ocupado;
    if (restauracionPendiente) { sesionPrevia = sesionActual; return; }

    if (sesionActual !== sesionPrevia) {
      sesionPrevia = sesionActual;
      desplazarAbajo(true, 0.25);
      temporizadoresDeEntrada.push(setTimeout(() => desplazarAbajo(true, 0.15), 80), setTimeout(() => desplazarAbajo(true, 0.15), 250));
    } else {
      desplazarAbajo(true);
    }
  });

  $effect(() => {
    if (tecladoAbierto) {
      desplazarAbajo(true, 0.42);
    }
  });

  onMount(() => {
    if (restauracionPendiente) {
      tick().then(() => {
        if (areaDelHilo) areaDelHilo.scrollTop = posicionDeRetorno;
        restauracionPendiente = false;
      });
    } else {
      desplazarAbajo(true, 0.2);
      temporizadoresDeEntrada.push(setTimeout(() => desplazarAbajo(true, 0.15), 80), setTimeout(() => desplazarAbajo(true, 0.15), 250));
    }
    cargarAclaraciones();
    // La aclaración la escribe otra sesión. Tres segundos mantiene la lectura
    // prácticamente en vivo sin tocar el hilo, el borrador ni la posición.
    const intervalo = setInterval(() => {
      if (!document.hidden) cargarAclaraciones();
    }, 3000);
    const alVolver = () => { if (!document.hidden) cargarAclaraciones(); };
    document.addEventListener('visibilitychange', alVolver);
    window.addEventListener('focus', alVolver);
    return () => {
      // bind:this puede estar vacío al destruir el DOM. Conservar el último
      // scroll observado mientras el elemento estaba conectado.
      conversacion.recordarLectura(claveLectura(), posicionActual, hiloAMostrar.length);
      temporizadoresDeEntrada.forEach(clearTimeout);
      clearInterval(intervalo);
      document.removeEventListener('visibilitychange', alVolver);
      window.removeEventListener('focus', alVolver);
    };
  });

  $effect(() => {
    void historial.sesionVista;
    void sesion.conversacion;
    cargarAclaraciones();
  });
</script>

<div class="conversacion">
  <!-- `T-10`: el `<h1>` permanece en el árbol accesible sin duplicar una
       cabecera visual dentro del hilo. -->
  <h1 class="solo-lectura-asistida">Conversación</h1>

  <!-- `tabindex` porque un área que se desplaza tiene que poder desplazarse
       con el teclado, y sin él solo responde a la rueda y al dedo: WCAG 2.1.1.
       El `role="log"` no se pone a propósito — anunciaría cada turno entero
       otra vez, y el turno ya llega anunciado por `ProgresoDelTurno`. -->
  <div class="espacio-chat" class:vacia={conversacionVacia}>
    {#if conversacionVacia || preferencias.fondoDuranteConversacion}
      <div
        class="ambiente-chat"
        class:durante-charla={!conversacionVacia}
        style={`--intensidad-ambiente: ${preferencias.intensidadFondoConversacion / 100}`}>
        <FondoInicioMatematico />
      </div>
    {/if}
    {#if conversacionVacia}
      <div class="inicio-conversacion" class:teclado-abierto={tecladoAbierto}>
        <div class="saludo-inicial">
          <span class="marca-inicial">DidaxIa</span>
          <h2>¿Qué quieres comprender hoy?</h2>
          <p>Escribe una duda, una función o el paso que te está costando.</p>
        </div>
      </div>
    {/if}
    <section
      class="hilo superficie-cuaderno"
      aria-label="Conversación"
      tabindex="-1"
      bind:this={areaDelHilo}
      use:conservarFocoAlLeer
      onscroll={(evento) => { posicionActual = evento.currentTarget.scrollTop; }}
    >
      {#if !sesion.autenticada}
        <BloqueoAutenticacion
          icono="conversacion"
          titulo="Acceso al Tutor Didáctico"
        >
          <p>
            Inicia sesión con tu cuenta institucional de <strong
              >{CORREO_INSTITUCIONAL}</strong
            > para acceder al tutor de cálculo diferencial, guardar tus conversaciones,
            ver gráficas interactivas y consultar tu historial.
          </p>
          <div class="boton-login-hero">
            <EntrarConGoogle />
          </div>
        </BloqueoAutenticacion>
      {/if}

      {#if historial.viendoHistorial && historial.cargandoHilo}
        <CargadorCubo mensaje="Cargando la conversación…" pantallaCompleta />
      {:else if historial.viendoHistorial && historial.falloHilo}
        <Degradacion respuesta={historial.falloHilo} alReintentar={null} amplio />
      {:else}
        {#each hiloAMostrar as entrada, i (i)}
          <!-- Fase 5 · `volverA` es la ruta de la conversación y no
               `location.pathname`: el retorno tiene que seguir siendo válido
               aunque se saliera estando en el historial, que es la misma
               pantalla vista de otra manera.

               `RC-PED-06` · el ítem sólo se puede contestar en el ÚLTIMO turno
               del tutor y sólo fuera del historial: contestar uno de hace tres
               turnos mandaría una respuesta a un ítem que la conversación ya
               dejó atrás, y en un hilo pasado no hay a quién mandarla. -->
          <Turno
            turno={entrada.turno}
            autor={entrada.autor}
            alAbrirGrafica={(definicion, disparador) => {
              graficaSolicitada = { definicion, disparador, turno: entrada.turno?.turno, momento: Date.now() };
            }}
            ocupado={envio.ocupado}
            volverA={RETORNO_A_LA_CONVERSACION}
            alResponderSondeo={!historial.viendoHistorial &&
            entrada.autor !== "estudiante" &&
            i === hiloAMostrar.length - 1
              ? responderSondeo
              : null}
          />
          {#each aclaracionesDelTurno(entrada) as aclaracion (aclaracion.id)}
            <AclaracionDocente {aclaracion} />
          {/each}
        {/each}
        <!-- Filas anteriores a la migración 21 no tienen un turno demostrable.
             Se conservan visibles al final sin inventar a qué respuesta iban. -->
        {#each aclaracionesSinAncla as aclaracion (aclaracion.id)}
          <AclaracionDocente {aclaracion} />
        {/each}
      {/if}

      {#if envio.ocupado}
        <ProgresoDelTurno progreso={envio.progreso} />
      {/if}

      {#if envio.fallo}
        <Degradacion
          respuesta={envio.fallo}
          amplio
          alReintentar={envio.fallo.reintentable === false
            ? null
            : async () => {
                await sesion.sincronizar();
                // 🔴 Paquete H · `reintentar()` y no `enviar(ultimoMensaje)`:
                // aquello perdía `dosNiveles` —la respuesta al ítem viajaba
                // como texto suelto y no diagnosticaba nada— y duplicaba el
                // mensaje del estudiante en el hilo.
                await envio.reintentar();
              }}
        />
      {/if}

      <div
        class="espaciador-inferior"
        class:con-teclado={tecladoAbierto}
        class:no-autenticado={!sesion.autenticada}
        class:con-aviso-retomar={historial.viendoHistorial &&
          historial.necesitaRetomar}
        aria-hidden="true"
      ></div>
    </section>

    <div class="pie" class:no-autenticado={!sesion.autenticada} class:con-teclado={tecladoAbierto}>
      <div class="pie-contenido">
        {#if historial.viendoHistorial && historial.necesitaRetomar}
          <!-- Solo antes del primer turno de la retoma: después, esto ya es
               la conversación en curso y no hace falta seguir avisándolo. -->
          <p class="aviso-retomar">
            Escribe aquí para retomar esta conversación.
          </p>
        {/if}
        <Redactor
          ocupado={envio.ocupado}
          alEnviar={envio.enviar}
          bind:tecladoAbierto
          bind:editando
        />
      </div>
    </div>
  </div>

  <!--
    EL PANEL DE CONTEXTO · lo que el turno nombró, al lado y no debajo.

    Vive en `../piezas/PanelDeContexto.svelte` desde el 2026-08-22 —galería,
    conceptos citados y la ficha al abrir uno, las tres cosas juntas—. Esta
    ruta decide si se ve como columna en escritorio. En teléfono la pieza
    permanece disponible como una hoja transitoria de pantalla completa.
  -->
  <PanelDeContexto
    hilo={hiloAMostrar}
    solicitudGrafica={graficaSolicitada}
    alCerrarGraficaDelChat={() => { graficaSolicitada = null; }}
    visibleEnEscritorio={preferencias.panelVisible}
    {editando}
  />
</div>

<style>
  /*
    ARMAZÓN, NO FLUJO DE DOCUMENTO. Lo que se desplaza es el hilo y solo el
    hilo; el redactor flota en la parte inferior como en el mockup.
  */
  .conversacion {
    flex: 1;
    min-block-size: 0;
    display: flex;
    position: relative;
    overflow: hidden;
    inline-size: 100%;
    block-size: 100%;
    height: 100%;
    align-items: stretch;
  }

  .espacio-chat {
    flex: 1;
    min-inline-size: 0;
    min-block-size: 0;
    display: flex;
    flex-direction: column;
    position: relative;
    height: 100%;
    overflow: hidden;
    /* El papel pertenece al espacio completo, no a la capa desplazable. Así
       el ambiente puede vivir entre la hoja y los turnos sin que un fondo
       opaco lo oculte. */
    background-color: var(--surface-paper);
  }

  .inicio-conversacion {
    position: absolute;
    inset: 0;
    /* Por encima del hilo vacío y por debajo del redactor flotante. */
    z-index: 2;
    display: grid;
    place-items: center;
    overflow: hidden;
    pointer-events: none;
    transition: opacity 0.25s ease;
  }

  .inicio-conversacion.teclado-abierto { opacity: 0; }

  .ambiente-chat {
    position: absolute;
    inset: 0;
    z-index: 0;
    overflow: hidden;
    pointer-events: none;
    transition: opacity .45s ease;
  }

  .ambiente-chat.durante-charla { opacity: var(--intensidad-ambiente, 1); }

  /*
    Tres planos deliberados:
      0 · ambiente matemático;
      1 · cuadrícula y turnos;
      2 · saludo del estado vacío.

    `superficie-cuaderno` aporta la cuadrícula, pero su color sólido tapaba
    por completo el plano 0. El papel base queda ahora en `.espacio-chat` y
    esta capa conserva únicamente las líneas transparentes de la cuadrícula.
  */
  .hilo {
    position: relative;
    z-index: 1;
    background-color: transparent;
  }

  .saludo-inicial {
    position: relative;
    z-index: 1;
    inline-size: min(92%, 42rem);
    margin-block-start: -12.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    pointer-events: none;
    animation: aparecer-saludo 0.48s cubic-bezier(0.22, 1, 0.36, 1) both;
  }

  .saludo-inicial h2 {
    width: 100%;
    margin: 0.35rem 0 0.65rem;
    color: var(--ink-primary);
    font-size: clamp(1.5rem, 2.6vw, 2.2rem);
    letter-spacing: -0.035em;
    text-align: center;
  }

  .saludo-inicial p {
    margin: 0;
    margin-inline: auto;
    width: 100%;
    max-inline-size: none;
    color: var(--ink-secondary);
    font-size: var(--texto-sm);
    text-align: center;
  }
  .marca-inicial {
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 750;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    text-align: center;
  }

  @keyframes aparecer-saludo {
    from {
      opacity: 0;
      transform: translateY(10px) scale(0.985);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }

  /* La hoja donde se trabaja: continua y sin marcos innecesarios */
  .hilo {
    flex: 1;
    min-block-size: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 24px 36px 0;
    border: none;
    display: flex;
    flex-direction: column;
  }

  .hilo:focus-visible {
    outline-offset: -2px;
  }

  .espaciador-inferior {
    height: 160px;
    min-height: 160px;
    flex-shrink: 0;
    transition:
      height 0.35s cubic-bezier(0.22, 1, 0.36, 1),
      min-height 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .espaciador-inferior.con-teclado {
    height: 330px;
    min-height: 330px;
  }

  /* Sin sesión, `.pie` está en `display: none` —ver esa regla más abajo—:
     no hay redactor flotando que le reserve hueco al hilo, así que este
     espaciador se quedaba como puro vacío al final de la tarjeta de
     acceso. Con la sesión resuelta y `.pie` visible, vuelve a hacer
     falta y `no-autenticado` deja de aplicar. */
  .espaciador-inferior.no-autenticado {
    height: 0;
    min-height: 0;
  }

  /* El aviso «Escribe aquí para retomar esta conversación» —ver
     `.pie-contenido`— se suma ARRIBA del redactor, así que `.pie` mide
     más alto que lo que este espaciador ya reservaba: sin este ajuste el
     último mensaje del hilo quedaba tapado detrás. */
  .espaciador-inferior.con-aviso-retomar {
    height: 190px;
    min-height: 190px;
  }

  .espaciador-inferior.con-aviso-retomar.con-teclado {
    height: 360px;
    min-height: 360px;
  }

  .pie {
    position: absolute;
    inset-block-end: 0;
    inset-inline: 0;
    padding: 12px 28px 24px;
    background: linear-gradient(
      180deg,
      transparent 0%,
      var(--surface-paper) 45%
    );
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    pointer-events: none;
    z-index: 15;
    display: flex;
    justify-content: center;
    transition:
      inset-block-end 0.5s cubic-bezier(0.22, 1, 0.36, 1),
      padding 0.3s ease;
  }

  .espacio-chat.vacia .pie {
    inset-block-end: calc(50% - 8.5rem);
    background: transparent;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  /* El redactor centrado del estado vacío sirve sin teclado. Al abrir el
     panel matemático, el conjunto baja al borde para no cortar sus teclas
     en teléfonos de poca altura. */
  .espacio-chat.vacia .pie.con-teclado {
    inset-block-end: 0;
  }

  .pie > :global(*) {
    pointer-events: auto;
    inline-size: 100%;
    /* 54rem se sentía angosto para el teclado de notación matemática desde
       que el carril lateral —`Aplicacion.svelte`— ganó ancho para el botón
       de Google: la misma pantalla le dejaba menos sitio a esto. */
    max-inline-size: min(100%, 58rem);
  }

  .pie.no-autenticado {
    display: none !important;
  }

  .pie-contenido {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    inline-size: 100%;
  }

  .aviso-retomar {
    margin: 0;
    padding: 4px 14px;
    background: var(--accent-surface);
    border-radius: var(--radius-pill, 9999px);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 600;
    text-align: center;
  }

  /* La tercera columna del marco —panel de herramientas— vive en
     `../piezas/PanelDeContexto.svelte` desde el 2026-08-22, con su propio
     CSS. Esta ruta solo la monta condicionalmente; ver el markup. */

  /* La tarjeta «inicia sesión para…» vive en `comun/estado/
     BloqueoAutenticacion.svelte` desde el 2026-08-22 — este archivo era
     una de las tres copias que la motivaron. `.boton-login-hero` sigue
     aquí: es contenido que ESTE archivo le pasa por `children`, así que su
     marcado lleva el scope de aquí y no el de `BloqueoAutenticacion`. */
  .boton-login-hero {
    margin-block-start: 0.5rem;
  }

  @media (max-width: 48rem), (pointer: coarse) and (max-width: 75rem) {
    .hilo {
      padding: 16px 16px 0;
    }

    /* El editor ocupa su propio espacio: el hilo visible termina sobre él y
       puede recorrerse sin que una capa flotante intercepte el dedo. */
    .espacio-chat:not(.vacia) .pie {
      position: relative;
      flex-shrink: 0;
      background: var(--surface-paper);
      backdrop-filter: none;
    }
    .espacio-chat:not(.vacia) .espaciador-inferior {
      height: 16px;
      min-height: 16px;
    }

    .pie {
      padding: 8px 12px 14px;
    }

    .espacio-chat.vacia .pie {
      inset-block-end: calc(50% - 7.5rem);
    }

    .espacio-chat.vacia .pie.con-teclado {
      inset-block-end: 0;
    }

    .saludo-inicial {
      margin-block-start: -15rem;
      padding-inline: 1.25rem;
    }

    .saludo-inicial h2 {
      font-size: clamp(1.3rem, 4.8vw, 1.75rem);
      margin: 0.2rem 0 0.35rem;
    }

    .saludo-inicial p {
      font-size: var(--texto-xs);
      line-height: 1.45;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .pie,
    .saludo-inicial {
      transition: none;
      animation: none;
    }
  }
</style>
