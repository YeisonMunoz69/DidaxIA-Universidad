<!--
De dónde salió el material, y cuándo el sistema declara NO TENER FUENTE.

Declarar la ausencia de fuente no es un fallo que haya que disimular: es lo que
`RP-18` obliga, porque el estado seguro ante lo que no se puede sostener es no
afirmar. Un sistema que improvisa algo plausible cuando no tiene material es
exactamente lo que el requisito prohíbe.

Por eso el caso `sin-fuente` se muestra con más peso visual que el normal, y no
menos: es información que el estudiante necesita para calibrar cuánto confiar.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

-->
<script>
  let {
    /** { origen: 'corpus' | 'sin-fuente', referencia? } — contrato §7 */
    procedencia
  } = $props();
</script>

{#if procedencia?.origen === 'sin-fuente'}
  <span class="procedencia sin-fuente">
    <span class="signo" aria-hidden="true">!</span>
    Sin material del curso que lo respalde
  </span>
{:else if procedencia?.origen === 'corpus'}
  <span class="procedencia corpus">
    <span class="signo" aria-hidden="true">§</span>
    <!-- Fase 5 · con `material`, la lista navegable de `MaterialDelCurso`
         viene justo debajo y repetir aquí los identificadores sería decir dos
         veces lo mismo, la primera sin poder pulsarla. Sin `material` —un
         contrato antiguo, o el hilo de un turno anterior a la migración 15—
         se conserva la cadena, que es lo único que esas filas tienen. -->
    Material del curso{!procedencia.material?.length && procedencia.referencia
      ? ' · ' + procedencia.referencia : ''}
  </span>
{/if}

<style>
  .procedencia {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    font-size: var(--texto-xs);
  }

  .signo { font-weight: 700; }

  .corpus { color: var(--ink-tertiary); }

  /* Más peso, no menos: es lo que el estudiante necesita para calibrar. */
  .sin-fuente {
    color: var(--semantic-warning);
    font-weight: 500;
    padding: 0.15em 0.45em;
    background: var(--semantic-warning-bg);
    border-radius: var(--radius-xs);
  }
</style>
