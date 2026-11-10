
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import TarjetaDeRevision from '../piezas/TarjetaDeRevision.svelte';
  import FiltrosDeCola from '../piezas/FiltrosDeCola.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import CabeceraDeRuta from '../piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../piezas/PantallaDesplazable.svelte';
  import EstadoVacio from '../piezas/EstadoVacio.svelte';
  import { onMount, untrack } from 'svelte';
  import * as api from '../../nucleo/api/supervision.js';
  import * as apiClases from '../../nucleo/api/clases.js';
  import { describir } from '../../nucleo/errores/degradacion.js';

  let filtros = $state({ urgencia: '', clase: '', tipo: '' });
  let elementos = $state([]);
  let clases = $state([]);
  let total = $state(0);
  let cargando = $state(false);
  let fallo = $state(null);

  const TAMANO_PAGINA = 6;
  let pagina = $state(0);

  const totalPaginas = $derived(Math.max(1, Math.ceil(total / TAMANO_PAGINA)));

  async function cargar() {
    cargando = true;
    fallo = null;
    try {
      const r = await api.listar({ ...filtros, tope: TAMANO_PAGINA, desde: pagina * TAMANO_PAGINA });
      elementos = r?.elementos ?? [];
      total = r?.total ?? elementos.length;
    } catch (e) {
      fallo = describir(e);
    } finally {
      cargando = false;
    }
  }

  async function actualizarSilenciosamente() {
    if (cargando || globalThis.document?.visibilityState === 'hidden') return;
    try {
      const r = await api.listar({
        ...filtros, tope: TAMANO_PAGINA, desde: pagina * TAMANO_PAGINA
      });
      elementos = r?.elementos ?? [];
      total = r?.total ?? elementos.length;
      const ultima = Math.max(0, Math.ceil(total / TAMANO_PAGINA) - 1);
      if (pagina > ultima) {
        pagina = ultima;
        await cargar();
      }
    } catch {
    }
  }

  $effect(() => {
    void filtros.urgencia; void filtros.clase; void filtros.tipo;
    pagina = 0;
    untrack(cargar);
  });

  function irAPagina(nueva) {
    if (nueva < 0 || nueva >= totalPaginas || nueva === pagina) return;
    pagina = nueva;
    cargar();
  }

  $effect(() => {
    apiClases.mias().then((c) => (clases = c ?? [])).catch(() => (clases = []));
  });

  onMount(() => {
    const alVolver = () => {
      if (globalThis.document?.visibilityState !== 'hidden') actualizarSilenciosamente();
    };
    const intervalo = globalThis.setInterval?.(actualizarSilenciosamente, 3000);
    globalThis.addEventListener?.('focus', alVolver);
    globalThis.document?.addEventListener?.('visibilitychange', alVolver);
    return () => {
      if (intervalo !== undefined) globalThis.clearInterval?.(intervalo);
      globalThis.removeEventListener?.('focus', alVolver);
      globalThis.document?.removeEventListener?.('visibilitychange', alVolver);
    };
  });

  function quitar(id) {
    elementos = elementos.filter((e) => e.id !== id);
    total = Math.max(0, total - 1);
  }

  const actuar = (fn) => async (id, extra) => {
    try {
      await fn(id, extra);
      quitar(id);
    } catch (e) {
      fallo = describir(e);
    }
  };
</script>

<PantallaDesplazable>
  <CabeceraDeRuta titulo="Cola de supervisión" icono="supervision" insignia="Revisión pedagógica">
    {#snippet accion()}
      <span class="badge-cuenta">
        {#if cargando}Cargando…
        {:else}{total} pendiente{total === 1 ? '' : 's'}
        {/if}
      </span>
    {/snippet}
    {#snippet nota()}
      Está pensada para revisar <strong>por muestreo y por excepción</strong>.
      No hace falta pasar por todas: acota con los filtros y mira lo que más lo
      pida.
    {/snippet}
  </CabeceraDeRuta>

  <details class="ayuda-supervision">
    <summary><Icono nombre="chispa" medida={15} /> ¿Cómo funciona esta revisión?</summary>
    <p>La cola recibe excepciones pedagógicas de tus clases. Al corregir, la respuesta original se conserva y tu texto llega al estudiante como una aclaración posterior; no se publica en su nombre ni se reescribe el historial.</p>
  </details>

  <FiltrosDeCola bind:filtros {clases} />

  {#if fallo}
    <Degradacion respuesta={fallo} alReintentar={cargar} />
  {/if}

  {#if cargando && !elementos.length && !fallo}
    <CargadorCubo mensaje="Consultando casos de supervisión…" pantallaCompleta />
  {:else if !cargando && !elementos.length && !fallo}
    <EstadoVacio icono="check" texto="No queda nada pendiente con estos filtros." tono="exito" />
  {/if}

  <ul class="lista">
    {#each elementos as e (e.id)}
      <li>
        <TarjetaDeRevision
          elemento={e}
          alAprobar={actuar(api.aprobar)}
          alEditar={actuar(api.editar)}
          alRechazar={actuar(api.rechazar)} />
      </li>
    {/each}
  </ul>

  {#if totalPaginas > 1}
    <nav class="paginacion" aria-label="Páginas de la cola">
      <button type="button" onclick={() => irAPagina(pagina - 1)} disabled={cargando || pagina === 0}>
        Anterior
      </button>
      <span class="indicador-pagina">Página {pagina + 1} de {totalPaginas}</span>
      <button type="button" onclick={() => irAPagina(pagina + 1)} disabled={cargando || pagina >= totalPaginas - 1}>
        Siguiente
      </button>
    </nav>
  {/if}
</PantallaDesplazable>

<style>
  .badge-cuenta {
    padding: 4px 12px;
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-pill, 9999px);
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-secondary);
    white-space: nowrap;
  }
  .ayuda-supervision { align-self: flex-end; max-inline-size: 42rem; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .ayuda-supervision summary { display: inline-flex; align-items: center; gap: .4rem; cursor: pointer; color: var(--accent-main); font-weight: 700; }
  .ayuda-supervision p { margin: .6rem 0 0; padding: .75rem .9rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-panel); }


  .lista {
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .lista > li { max-inline-size: none; }

  .paginacion {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--espacio-md);
    align-self: center;
    padding-block-start: var(--espacio-sm);
  }

  .paginacion button {
    padding: 0.5em 1.1em;
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-pill, 9999px);
    color: var(--ink-secondary);
    font-size: var(--texto-sm);
    font-weight: 600;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .paginacion button:hover:not(:disabled) { border-color: var(--accent-main); color: var(--accent-main); }

  .paginacion button:disabled { opacity: 0.5; cursor: not-allowed; }

  .indicador-pagina {
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-secondary);
    font-variant-numeric: tabular-nums;
  }
</style>
