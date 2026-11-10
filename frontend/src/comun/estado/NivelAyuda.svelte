
<script>
  import BotonAyudaTooltip from '../base/BotonAyudaTooltip.svelte';
  let { nivel } = $props();

  const ROTULO = {
    sondeo:     'Nivel 1 · te pregunto para que lo veas tú',
    regla:      'Nivel 2 · te nombro la regla que aplica',
    desarrollo: 'Nivel 3 · te muestro el desarrollo'
  };

  const rotulo = $derived(ROTULO[nivel] ?? null);
  const EXPLICACION = {
    sondeo: 'Nivel 1: el tutor pregunta qué observas o intentarías antes de mostrar un procedimiento.',
    regla: 'Nivel 2: el tutor nombra una regla o idea útil para avanzar.',
    desarrollo: 'Nivel 3: el tutor muestra pasos de resolución para contrastarlos con tu intento.'
  };
</script>

{#if rotulo}
  <span class="nivel {nivel}">{rotulo}<BotonAyudaTooltip tamano="sm" posicion="arriba" texto={EXPLICACION[nivel]} ariaLabel={`Qué significa ${rotulo}`} /></span>
{/if}

<style>
  .nivel {
    display: inline-flex;
    align-items: center;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }
</style>
