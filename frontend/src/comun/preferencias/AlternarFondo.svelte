<script>
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import InterruptorDePreferencia from './InterruptorDePreferencia.svelte';
</script>

<div class="fondo">
  <InterruptorDePreferencia nombre="Mantener el ambiente matemático durante la charla"
    pista="Conserva el fondo matemático después del primer mensaje."
    valor={preferencias.fondoDuranteConversacion}
    alCambiar={(valor) => preferencias.alternarFondoConversacion(valor)} />
  {#if preferencias.fondoDuranteConversacion}
    <label class="intensidad" for="intensidad-ambiente">
      <span>Intensidad del ambiente <output>{preferencias.intensidadFondoConversacion}%</output></span>
      <input id="intensidad-ambiente" aria-label="Intensidad durante la charla" type="range"
        min="0" max="100" step="5" value={preferencias.intensidadFondoConversacion}
        oninput={(evento) => preferencias.elegirIntensidadFondoConversacion(evento.currentTarget.value)} />
    </label>
  {/if}
</div>

<style>
  .fondo { display:grid; gap:.75rem; }
  .intensidad { display:grid; gap:.55rem; padding:.65rem 1rem; color:var(--ink-secondary); font-size:var(--texto-sm); }
  .intensidad span { display:flex; justify-content:space-between; gap:1rem; }
  output { color:var(--accent-main); font-variant-numeric:tabular-nums; }
  input { inline-size:100%; accent-color:var(--accent-main); cursor:pointer; }
</style>
