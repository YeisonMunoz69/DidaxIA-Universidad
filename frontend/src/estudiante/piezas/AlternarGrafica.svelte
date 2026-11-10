<!-- DD-14: ocultar la gráfica conserva siempre su descripción textual. -->
<script>
  import InterruptorDePreferencia from '../../comun/preferencias/InterruptorDePreferencia.svelte';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
</script>

<InterruptorDePreferencia nombre="Mostrar las representaciones gráficas"
  pista="Planos cartesianos en el hilo de tutoría y la galería de trabajo."
  valor={preferencias.graficaVisible}
  alCambiar={(valor) => preferencias.alternarGrafica(valor)} />
