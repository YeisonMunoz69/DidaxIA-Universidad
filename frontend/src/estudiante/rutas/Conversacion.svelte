
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

  const RETORNO_A_LA_CONVERSACION = "/";

  const hiloAMostrar = $derived(
    historial.viendoHistorial ? (historial.hiloVisto ?? []) : conversacion.hilo,
  );
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
      conversacion.vacia &&
      !envio.ocupado &&
      !envio.fallo,
  );

  async function responderSondeo(respuesta) {
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
    const intervalo = setInterval(() => {
      if (!document.hidden) cargarAclaraciones();
    }, 3000);
    const alVolver = () => { if (!document.hidden) cargarAclaraciones(); };
    document.addEventListener('visibilitychange', alVolver);
    window.addEventListener('focus', alVolver);
    return () => {
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

  <h1 class="solo-lectura-asistida">Conversación</h1>


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


  <PanelDeContexto
    hilo={hiloAMostrar}
    solicitudGrafica={graficaSolicitada}
    alCerrarGraficaDelChat={() => { graficaSolicitada = null; }}
    visibleEnEscritorio={preferencias.panelVisible}
    {editando}
  />
</div>

<style>
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
    background-color: var(--surface-paper);
  }

  .inicio-conversacion {
    position: absolute;
    inset: 0;
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

  .espaciador-inferior.no-autenticado {
    height: 0;
    min-height: 0;
  }

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

  .espacio-chat.vacia .pie.con-teclado {
    inset-block-end: 0;
  }

  .pie > :global(*) {
    pointer-events: auto;
    inline-size: 100%;
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


  .boton-login-hero {
    margin-block-start: 0.5rem;
  }

  @media (max-width: 48rem), (pointer: coarse) and (max-width: 75rem) {
    .hilo {
      padding: 16px 16px 0;
    }

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
