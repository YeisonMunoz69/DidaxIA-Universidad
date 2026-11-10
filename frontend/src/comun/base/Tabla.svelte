
<script>
  let {
    titulo,
    tituloVisible = false,
    columnas = [],
    filas = [],
    ...resto
  } = $props();
</script>


<div class="marco" tabindex="0" role="region" aria-label={titulo}>
  <table {...resto}>
    <caption class={tituloVisible ? '' : 'solo-lectura-asistida'}>{titulo}</caption>
    <thead>
      <tr>
        {#each columnas as c}
          <th scope="col" class={c.numerica ? 'num' : ''}>{c.etiqueta}</th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each filas as fila}
        <tr>
          {#each columnas as c, i}
            {#if i === 0}
              <th scope="row">{fila[c.clave]}</th>
            {:else}
              <td class={c.numerica ? 'num' : ''}>{fila[c.clave]}</td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .marco { overflow-x: auto; }

  table { border-collapse: collapse; inline-size: 100%; }

  caption {
    text-align: start;
    font-weight: 500;
    margin-block-end: 0.5em;
  }

  th, td {
    padding: 0.7em 0.85em;
    text-align: start;
    border-block-end: 1px solid var(--ink-ghost);
  }

  thead th {
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
    border-block-end: 2px solid var(--trazo-suave);
  }

  tbody tr:last-child :where(th, td) { border-block-end: none; }

  .num { text-align: end; font-variant-numeric: tabular-nums; }
</style>
