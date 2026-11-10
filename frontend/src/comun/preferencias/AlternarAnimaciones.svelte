<script>
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import InterruptorDePreferencia from './InterruptorDePreferencia.svelte';
</script>

<InterruptorDePreferencia nombre="Animaciones y transiciones fluidas"
  pista="Movimiento suave entre vistas y al abrir menús."
  valor={preferencias.animaciones}
  alCambiar={(valor) => preferencias.alternarAnimaciones(valor)} />
