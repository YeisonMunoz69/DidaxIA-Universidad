<script>
  import Icono from '../base/Icono.svelte';
  import Prosa from './Prosa.svelte';
  let { aclaracion } = $props();
</script>

<article class="aclaracion" aria-label="Aclaración del docente">
  <span class="sello"><Icono nombre="estudiante" medida={15} /> Aclaración del docente</span>
  <div class="texto"><Prosa contenido={aclaracion.texto} /></div>
  <small>Se conserva junto a la respuesta original · {new Date(aclaracion.creada_en).toLocaleString('es-CO')}</small>
</article>

<style>
  .aclaracion {
    align-self: flex-start;
    inline-size: min(100%, 42rem);
    margin: .35rem 0 1rem;
    padding: .9rem 1rem;
    border: 1px solid color-mix(in srgb, var(--accent-main) 45%, var(--trazo-suave));
    border-inline-start: 4px solid var(--accent-main);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--accent-surface) 68%, var(--surface-paper));
    box-shadow: var(--shadow-soft);
  }
  .sello { display: inline-flex; align-items: center; gap: .4rem; color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }
  .texto { margin: .55rem 0 .45rem; max-inline-size: none; color: var(--ink-primary); white-space: pre-wrap; line-height: 1.6; }
  small { color: var(--ink-tertiary); }
</style>
