
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import FilaDeEvidencia from './FilaDeEvidencia.svelte';
  import EstadoVacio from '../../docente/piezas/EstadoVacio.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import { FILTROS } from '../../nucleo/api/evidencias.js';

  let {
    evidencias = [],
    filtro = $bindable('pendiente'),
    seleccionada = 0,
    cargando = false,
    hayMas = false,
    fallo = null,
    alSeleccionar,
    alCargarMas,
    alReintentar
  } = $props();

  const ROTULOS = {
    pendiente: 'Sin revisar',
    aprobada: 'Aprobadas',
    rechazada: 'Rechazadas',
    todos: 'Todas'
  };

  const porSujeto = $derived(
    evidencias.reduce((cuenta, e) => {
      cuenta[e.sujeto] = (cuenta[e.sujeto] ?? 0) + 1;
      return cuenta;
    }, {})
  );

  const vacia = $derived(!cargando && !fallo && evidencias.length === 0);
</script>

<section class="cola" aria-label="Cola de autorizaciones">
  <fieldset class="filtros">
    <legend class="solo-lectura-asistida">Filtrar por estado</legend>
    {#each FILTROS as valor (valor)}
      <label class="opcion" class:activa={filtro === valor}>
        <input type="radio" name="estado-de-evidencia" value={valor} bind:group={filtro} />
        <span>{ROTULOS[valor]}</span>
      </label>
    {/each}
  </fieldset>

  {#if fallo}

    <Degradacion respuesta={fallo} alReintentar={fallo.reintentable ? alReintentar : null} />
  {/if}

  {#if cargando && evidencias.length === 0}
    <CargadorCubo mensaje="Cargando la cola…" pantallaCompleta />
  {/if}

  {#if vacia}
    <EstadoVacio
      icono="check"
      tono="exito"
      texto={filtro === 'pendiente'
        ? 'No queda ninguna autorización por revisar.'
        : 'Ninguna autorización con este filtro.'} />
  {/if}

  {#if evidencias.length}
    <ul class="lista">
      {#each evidencias as e (e.evidencia)}
        <li>
          <FilaDeEvidencia
            evidencia={e}
            seleccionada={seleccionada === e.evidencia}
            hermanos={porSujeto[e.sujeto] ?? 1}
            {alSeleccionar} />
        </li>
      {/each}
    </ul>
  {/if}

  {#if hayMas}
    <div class="continuar">
      <Boton variante="secundario" deshabilitado={cargando} onclick={alCargarMas}>
        {cargando ? 'Cargando…' : 'Cargar más'}
      </Boton>
    </div>
  {/if}
</section>

<style>
  .cola {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    min-inline-size: 0;
  }

  .filtros {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0;
    padding: 0;
    border: 0;
  }

  .opcion {
    padding: 4px 12px;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-pill, 9999px);
    background: var(--surface-panel);
    color: var(--ink-secondary);
    font-size: var(--texto-sm);
    font-weight: 600;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .opcion:hover { border-color: var(--accent-main); color: var(--accent-main); }

  .opcion.activa {
    border-color: var(--accent-main);
    background: var(--accent-surface);
    color: var(--accent-main);
  }

  .opcion input {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }

  .opcion:has(input:focus-visible) {
    outline: 2px solid var(--accent-main);
    outline-offset: 2px;
  }

  .lista {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .lista > li { max-inline-size: none; }

  .continuar { display: flex; justify-content: center; }
</style>
