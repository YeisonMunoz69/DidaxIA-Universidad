<script>
  import TarjetaKPI from './TarjetaKPI.svelte';
  import PerfilDeProporciones from './PerfilDeProporciones.svelte';
  import CalidadDeDatos from './CalidadDeDatos.svelte';
  import { visibleEnTablero, tieneValorPublicable, esEvidenciaDeDialogo, factorPrincipal, ordenarFactores } from './visibilidad.js';

  let { datos, alDescargarPDF = null, descargasHabilitadas = true } = $props();
  const ORDEN = Object.freeze([
    ['resumen', 'Resumen'], ['fenomenos', 'Fenómenos y diálogo'], ['adopcion', 'Adopción'], ['aprendizaje', 'Aprendizaje'],
    ['recuperacion', 'Recuperación documental'], ['supervision', 'Supervisión'],
    ['conductual', 'Conductuales'], ['institucion', 'Institución'],
    ['calidad', 'Calidad de datos']
  ]);
  let pestana = $state('resumen');
  const indicadores = $derived(datos?.indicadores ?? []);
  const publicados = $derived(indicadores.filter(visibleEnTablero));
  const dimensiones = $derived(ORDEN.filter(([clave]) =>
    clave === 'resumen' || clave === 'calidad' || (clave === 'fenomenos'
      ? publicados.some(esEvidenciaDeDialogo) : publicados.some((item) => item.dimension === clave))
  ));
  const visibles = $derived(pestana === 'calidad' ? [] : pestana === 'resumen'
    ? [...ordenarFactores(publicados.filter(esEvidenciaDeDialogo)), ...publicados.filter((item) => !esEvidenciaDeDialogo(item))].slice(0, 8)
    : pestana === 'fenomenos' ? publicados.filter(esEvidenciaDeDialogo)
    : publicados.filter((item) => item.dimension === pestana));
</script>

<div class="resumen-calidad" aria-label="Resumen de disponibilidad">
  <span><strong>Instrumento-Prototipo</strong></span>
  <span><strong>{publicados.filter(tieneValorPublicable).length}</strong> KPI con valor en este periodo</span>
  <span><strong>{publicados.filter((item) => !tieneValorPublicable(item)).length}</strong> indicadores con cobertura pendiente</span>
</div>

<nav class="pestanas" aria-label="Dimensiones de indicadores">
  {#each dimensiones as dimension (dimension[0])}
    <button type="button" class:activa={pestana === dimension[0]}
      aria-pressed={pestana === dimension[0]} onclick={() => pestana = dimension[0]}>{dimension[1]}</button>
  {/each}
</nav>

{#if pestana === 'calidad'}
  <CalidadDeDatos calidad={datos?.calidad} />
{:else if visibles.length}
  <section class="rejilla" aria-live="polite">
    <div class="grafica"><PerfilDeProporciones indicadores={visibles} /></div>
    {#if visibles.some(item => factorPrincipal(item, publicados))}
      <div class="principales" aria-label="Factores principales del estudio">
        {#each ordenarFactores(visibles).filter(item => factorPrincipal(item, publicados)) as indicador (indicador.codigo)}
          <TarjetaKPI {indicador} principal={factorPrincipal(indicador, publicados)} {alDescargarPDF} {descargasHabilitadas} />
        {/each}
      </div>
    {/if}
    {#each visibles.filter(item => !factorPrincipal(item, publicados)) as indicador (indicador.codigo)}
      <TarjetaKPI {indicador} {alDescargarPDF} {descargasHabilitadas} />
    {/each}
  </section>
{:else}
  <section class="vacio">
    <h2>No hay indicadores disponibles en este resumen</h2>
    <p>Prueba otro periodo o filtro para consultar valores observados.</p>
  </section>
{/if}

<style>
  .resumen-calidad { display: flex; flex-wrap: wrap; gap: .5rem; }
  .resumen-calidad span { padding: .5rem .7rem; border: 1px solid var(--trazo-suave); border-radius: 999px; background: var(--surface-paper); color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .resumen-calidad strong { color: var(--ink-primary); }
  .pestanas { display: flex; gap: .45rem; overflow-x: auto; padding-block-end: .25rem; scrollbar-width: thin; }
  .pestanas button { flex: 0 0 auto; min-block-size: 2.55rem; padding: .5rem .85rem; border: 1px solid var(--trazo-suave); border-radius: 999px; background: var(--surface-paper); color: var(--ink-secondary); font: inherit; font-size: var(--texto-xs); font-weight: 750; cursor: pointer; }
  .pestanas button.activa { border-color: transparent; background: var(--accent-main); color: var(--accent-on-main); }
  .rejilla { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(18rem, 100%), 1fr)); gap: .8rem; }
  .grafica { grid-column: 1 / -1; }
  .principales { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(auto-fit, minmax(min(18rem, 100%), 1fr)); gap: .8rem; }
  .vacio { padding: 1.5rem; border: 1px dashed var(--trazo); border-radius: var(--radius-md); text-align: center; }
  .vacio h2 { margin: 0; color: var(--ink-primary); font-size: var(--texto-base); }
  .vacio p { margin: .4rem auto 0; color: var(--ink-tertiary); font-size: var(--texto-sm); }
</style>
