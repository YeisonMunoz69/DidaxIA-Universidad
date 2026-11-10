<script>
  import BotonAyudaTooltip from '../base/BotonAyudaTooltip.svelte';
  let { indicadores = [] } = $props();
  const colores = [
    'var(--color-sky)', 'var(--color-emerald)', 'var(--color-violet)',
    'var(--color-amber-chart)', 'var(--color-rose)', 'var(--color-cyan)'
  ];
  const filas = $derived(indicadores.filter((item) =>
    item.estado === 'disponible' && item.unidad === 'proporcion' &&
    Number.isFinite(item.valor) && item.valor >= 0 && item.valor <= 1
  ));
  const formato = new Intl.NumberFormat('es-CO', { style: 'percent', maximumFractionDigits: 1 });
</script>

{#if filas.length}
  <figure class="perfil" aria-label="Proporciones observadas en una escala de cero a cien por ciento">
    <figcaption><strong>Proporciones observadas <BotonAyudaTooltip tamano="sm" ariaLabel="Cómo interpretar las proporciones observadas" texto="Cada barra representa una proporción de 0 a 100 %, con su propia población y muestra. Su longitud no ordena aprendizaje ni calidad entre KPI distintos. Abre la explicación de cada tarjeta para conocer su denominador e interpretación." /></strong><span>Escala 0–100 % · cada KPI conserva su propia población</span></figcaption>
    <div class="filas">
      {#each filas as item, indice (item.codigo)}
        <div class="fila" style:--color={colores[indice % colores.length]}>
          <span class="nombre">{item.nombre}</span>
          <div class="pista" role="img" aria-label={`${item.nombre}: ${formato.format(item.valor)}, muestra ${item.muestra ?? 'no declarada'}`}>
            <span class="relleno" style:width={`${item.valor * 100}%`}></span>
          </div>
          <strong class="cifra">{formato.format(item.valor)}</strong>
          <small>n={item.muestra ?? '—'}</small>
        </div>
      {/each}
    </div>
  </figure>
{/if}

<style>
  .perfil { display: grid; gap: .8rem; margin: 0; padding: 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); }
  figcaption { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: .25rem 1rem; color: var(--ink-primary); }
  figcaption span { color: var(--ink-secondary); font-size: var(--texto-xs); }
  .filas { display: grid; gap: .5rem; }
  .fila { display: grid; grid-template-columns: minmax(8rem, 1.4fr) minmax(5rem, 2fr) auto auto; align-items: center; gap: .5rem; color: var(--ink-primary); font-size: var(--texto-xs); }
  .nombre { overflow-wrap: anywhere; }
  .pista { height: .65rem; border-radius: 999px; background: var(--surface-panel); overflow: hidden; }
  .relleno { display: block; height: 100%; border-radius: inherit; background: var(--color); }
  .cifra { min-width: 3.6rem; text-align: end; font-variant-numeric: tabular-nums; }
  small { color: var(--ink-tertiary); font-variant-numeric: tabular-nums; }
  @media (max-width: 36rem) { .fila { grid-template-columns: 1fr auto auto; } .pista { grid-column: 1 / -1; grid-row: 2; } }
</style>
