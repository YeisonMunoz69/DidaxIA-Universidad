<!-- Lista desplazable y estados del historial; la acción de cada grupo es delegada. -->
<script>
  import CargadorCubo from '../base/CargadorCubo.svelte';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { historial } from '../../nucleo/historial/historial.svelte.js';
  import { agruparPorFecha } from '../../nucleo/historial/agrupar.js';
  import { navegar } from '../../enrutado/navegar.js';
  import { inicioDe } from '../../enrutado/caminos.js';
  import { espacio } from '../../nucleo/espacio/espacio.svelte.js';
  import GrupoDelHistorial from './GrupoDelHistorial.svelte';

  let { carrilAbierto = $bindable(false) } = $props();
  const grupos = $derived(
    sesion.autenticada ? agruparPorFecha(historial.conversaciones) : []
  );

  function verHistorial(sesionId) {
    historial.ver(sesionId);
    // `EQ-031` · con el espacio activo, por el mismo motivo que en
    // `BotonNuevaConversacion.svelte`: abrir una charla del historial no puede
    // sacar a un profesional del espacio Tutor donde la estaba leyendo.
    navegar(inicioDe(sesion.rol, espacio.activo));
    carrilAbierto = false;
  }
</script>

<nav aria-label="Conversaciones">
  {#if grupos.length > 0}
    {#each grupos as grupo (grupo.id)}
      <GrupoDelHistorial
        {grupo}
        sesionSeleccionada={historial.sesionVista || sesion.conversacion}
        alAbrir={verHistorial} />
    {/each}
  {:else if !sesion.autenticada && historial.conversaciones.length === 0}
    <p class="sin-historial">
      Inicia sesión con Google para guardar y ver tus conversaciones anteriores.
    </p>
  {:else if historial.cargandoLista && historial.conversaciones.length === 0}
    <CargadorCubo mensaje="Cargando tu historial…" compacto />
  {:else if historial.falloLista && historial.conversaciones.length === 0}
    <p class="sin-historial" role="alert">{historial.falloLista.titulo}</p>
  {:else}
    <p class="sin-historial">Todavía no tienes conversaciones guardadas.</p>
  {/if}
</nav>

<style>
  nav {
    flex: 1;
    min-block-size: 0;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: thin;
  }

  .sin-historial {
    margin: 0.5rem 0 0;
    font-size: var(--texto-xs);
    line-height: 1.4;
    color: var(--ink-tertiary);
  }
</style>
