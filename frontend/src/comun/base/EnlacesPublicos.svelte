
<script>
  import { DOCUMENTOS_PUBLICOS, enlacePublico } from '../../nucleo/configuracion/origenes.js';

  let {
    absolutos = false,
    rotulo = 'Documentos públicos del proyecto',
    variante = 'en-linea',
    conResumen = false
  } = $props();

  const enlaces = $derived(
    DOCUMENTOS_PUBLICOS.map((p) => ({
      ...p,
      href: absolutos ? enlacePublico(p.camino) : p.camino
    }))
  );
</script>

<nav class="enlaces {variante}" aria-label={rotulo}>
  <ul>
    {#each enlaces as enlace (enlace.camino)}
      <li>
        <a href={enlace.href}>{enlace.titulo}</a>
        {#if conResumen}
          <span class="resumen">{enlace.resumen}</span>
        {/if}
      </li>
    {/each}
  </ul>
</nav>

<style>
  .enlaces ul {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    gap: var(--espacio-md) var(--espacio-lg);
  }

  .en-linea ul { flex-wrap: wrap; align-items: baseline; }

  .apilada ul { flex-direction: column; }

  li {
    max-inline-size: none;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  a {
    display: inline-flex;
    align-items: center;
    min-block-size: 24px;
    font-size: var(--texto-sm);
    font-weight: 500;
  }

  .resumen {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    line-height: 1.4;
  }
</style>
