<script>
  import Notacion from '../turno/Notacion.svelte';
  let { metodologia } = $props();
</script>

{#if metodologia}
  <div class="metodologia">
    <section><h4>Qué pregunta responde</h4><p>{metodologia.pregunta}</p></section>
    <section><h4>Cómo se calcula</h4>
      <Notacion expresion={metodologia.formula_latex} alternativo={metodologia.formula} bloque compacto />
      <dl>{#each Object.entries(metodologia.simbolos ?? {}) as [simbolo, significado]}
        <div><dt><Notacion expresion={simbolo} alternativo={simbolo} compacto /></dt><dd>{significado}</dd></div>
      {/each}</dl>
      <p>{metodologia.regla_agregacion}</p>
    </section>
    <section><h4>Ejemplo ilustrativo</h4><p>{metodologia.ejemplo}</p></section>
    <section><h4>Cómo leer los valores</h4><p><strong>Alto:</strong> {metodologia.alto}</p><p><strong>Bajo:</strong> {metodologia.bajo}</p><p><strong>Ausente:</strong> {metodologia.ausente}</p></section>
    <section><h4>Datos e incertidumbre</h4><p>{metodologia.fuentes?.join(' · ') || 'Recolección pendiente'}</p><p>{metodologia.recoleccion}</p><p>{metodologia.incertidumbre}</p></section>
    {#if metodologia.items?.length}<section><h4>Ítems preliminares</h4><ol>{#each metodologia.items as item}<li>{item}</li>{/each}</ol><p>{metodologia.escala_respuesta}</p></section>{/if}
    {#if metodologia.prototipo}<p class="fundamento">{metodologia.fundamento}</p>{/if}
  </div>
{/if}

<style>
  .metodologia { display: grid; gap: .8rem; min-inline-size: 0; }
  section { min-inline-size: 0; padding: .8rem; border-radius: var(--radius-sm); background: var(--surface-panel); }
  h4 { margin: 0; color: var(--ink-primary); font-size: var(--texto-sm); }
  p, li, dd { margin: .3rem 0 0; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.55; overflow-wrap: anywhere; }
  dl { display: grid; gap: .4rem; margin: .7rem 0; }
  dl div { display: grid; grid-template-columns: 6.5rem minmax(0, 1fr); gap: .65rem; }
  dt { color: var(--accent-main); } dd { margin: 0; }
  ol { padding-inline-start: 1.3rem; }
  .fundamento { padding: .7rem; border-inline-start: 3px solid var(--accent-main); }
  @media (max-width: 34rem) {
    dl div { grid-template-columns: minmax(0, 1fr); gap: .15rem; }
  }
</style>
