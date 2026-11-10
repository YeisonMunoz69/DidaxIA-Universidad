<!--
El nivel de divulgación alcanzado.

MUESTRA EL NIVEL; NO LO DECIDE NI LO ESCALA. La escala de divulgación es dominio
y vive en el servidor. Si el cliente decidiera cuándo escalar, dos clientes
distintos darían ayudas distintas ante el mismo estado, y la garantía dejaría de
serlo.

Los tres valores del contrato §6: sondeo · regla · desarrollo.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

-->
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
