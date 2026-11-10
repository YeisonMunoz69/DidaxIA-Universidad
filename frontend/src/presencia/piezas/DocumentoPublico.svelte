
<script>
  import CanalDePrivacidad from './CanalDePrivacidad.svelte';

  let {
    documento
  } = $props();
</script>

<article class="documento">
  <header>
    <h1>{documento.titulo}</h1>
    <p class="entradilla">{documento.entradilla}</p>
    {#if documento.actualizacion}<p class="entradilla">{documento.actualizacion}</p>{/if}
  </header>

  <nav class="indice" aria-label="Secciones de esta página">
    <ul>
      {#each documento.secciones as seccion (seccion.id)}
        <li><a href="#{seccion.id}">{seccion.titulo}</a></li>
      {/each}
    </ul>
  </nav>

  {#each documento.secciones as seccion (seccion.id)}
    <section id={seccion.id} aria-labelledby="titulo-{seccion.id}">
      <h2 id="titulo-{seccion.id}">{seccion.titulo}</h2>

      {#each seccion.parrafos ?? [] as parrafo (parrafo)}
        <p>{parrafo}</p>
      {/each}

      {#if seccion.lista?.length}
        <ul class="puntos">
          {#each seccion.lista as punto (punto)}
            <li>{punto}</li>
          {/each}
        </ul>
      {/if}

      {#if seccion.cierre}
        <p class="cierre">{seccion.cierre}</p>
      {/if}
      {#if seccion.enlace}
        <a href={seccion.enlace.href} target="_blank" rel="noopener noreferrer">{seccion.enlace.texto} ↗</a>
      {/if}
    </section>
  {/each}

  <CanalDePrivacidad />
</article>

<style>
  .documento {
    display: flex;
    flex-direction: column;
    gap: clamp(var(--espacio-lg), 3vw, var(--espacio-2xl));
  }

  header {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-sm);
    padding: clamp(var(--espacio-lg), 4vw, var(--espacio-2xl));
    border: 0;
    border-inline-start: 4px solid var(--accent-main);
    border-radius: 0 var(--radius-xl) var(--radius-xl) 0;
    background:
      linear-gradient(115deg, color-mix(in srgb, var(--accent-surface) 65%, var(--surface-paper)), color-mix(in srgb, var(--surface-paper) 94%, transparent) 62%),
      var(--surface-paper);
  }

  h1 {
    max-inline-size: 22ch;
    margin: 0;
    font-size: clamp(var(--texto-2xl), 4vw, 3.15rem);
    font-weight: 740;
    line-height: 1.06;
    color: var(--ink-primary);
    letter-spacing: -0.04em;
    text-wrap: balance;
  }

  .entradilla {
    max-inline-size: 72ch;
    margin: 0;
    font-size: var(--texto-md);
    line-height: var(--interlinea-comoda);
    color: var(--ink-secondary);
  }

  .indice {
    position: sticky;
    top: var(--espacio-sm);
    z-index: 3;
    padding: var(--espacio-xs);
    background: color-mix(in srgb, var(--surface-canvas) 88%, transparent);
    border: 1px solid color-mix(in srgb, var(--trazo-suave) 52%, transparent);
    border-radius: var(--radius-xl);
    box-shadow: 0 12px 32px color-mix(in srgb, var(--ink-primary) 5%, transparent);
    backdrop-filter: blur(12px) saturate(1.15);
    -webkit-backdrop-filter: blur(12px) saturate(1.15);
  }

  .indice ul {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: var(--espacio-xs);
  }

  .indice li { max-inline-size: none; }

  .indice a {
    display: inline-flex;
    align-items: center;
    min-block-size: 42px;
    padding: 0.45rem 0.75rem;
    border: 1px solid transparent;
    border-radius: var(--radius-trazado);
    color: var(--ink-secondary);
    font-size: var(--texto-xs);
    font-weight: 600;
    line-height: var(--interlinea-normal);
    text-decoration: none;
    transition: color 160ms ease, background-color 160ms ease, border-color 160ms ease;
  }

  .indice a:hover,
  .indice a:focus-visible {
    color: var(--accent-main);
    background: color-mix(in srgb, var(--accent-surface) 58%, var(--surface-paper));
    border-color: color-mix(in srgb, var(--accent-main) 18%, transparent);
  }

  .indice a:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 2px; }

  section {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    padding: clamp(var(--espacio-lg), 3vw, var(--espacio-2xl));
    background: color-mix(in srgb, var(--surface-paper) 94%, transparent);
    border: 1px solid color-mix(in srgb, var(--trazo-suave) 58%, transparent);
    border-radius: var(--radius-lg);
    box-shadow: 0 10px 34px color-mix(in srgb, var(--ink-primary) 4%, transparent);
    scroll-margin-block-start: var(--espacio-lg);
  }

  h2 {
    margin: 0;
    font-size: clamp(var(--texto-lg), 2vw, var(--texto-xl));
    font-weight: 720;
    line-height: 1.18;
    letter-spacing: -0.025em;
    color: var(--ink-primary);
    text-wrap: balance;
  }

  p {
    margin: 0;
    font-size: var(--texto-base);
    line-height: var(--interlinea-normal);
    color: var(--ink-secondary);
  }

  section p, section .puntos li { max-inline-size: none; }

  .cierre { color: var(--ink-primary); }

  .puntos {
    margin: 0;
    padding-inline-start: 1.15rem;
    display: flex;
    flex-direction: column;
    gap: var(--espacio-sm);
  }

  .puntos li {
    font-size: var(--texto-base);
    line-height: var(--interlinea-normal);
    color: var(--ink-secondary);
  }

  @media (max-width: 48rem) {
    .documento { gap: var(--espacio-lg); }
    .indice { position: static; }
    .indice ul { gap: 0.25rem; }
    .indice a { min-block-size: 44px; padding-inline: 0.65rem; }
    section { scroll-margin-block-start: var(--espacio-md); }
  }

  @media (prefers-reduced-motion: reduce) {
    .indice a { transition: none; }
  }
</style>
