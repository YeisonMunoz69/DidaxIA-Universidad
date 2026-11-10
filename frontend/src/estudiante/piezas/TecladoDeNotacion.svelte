
<script>
  import PestanasDeNotacion from './PestanasDeNotacion.svelte';

  let { alInsertar, alComando } = $props();
</script>

<PestanasDeNotacion {alInsertar} {alComando} />
