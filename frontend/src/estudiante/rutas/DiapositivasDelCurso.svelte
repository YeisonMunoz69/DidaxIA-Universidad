<script>
  import RecursosPublicados from '../../comun/rutas/RecursosPublicados.svelte';
  let { consultaActual = '' } = $props();
</script>

<RecursosPublicados {consultaActual} tipoInicial="diapositivas" />
