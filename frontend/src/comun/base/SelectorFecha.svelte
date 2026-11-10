<script>
  import SelectorTamborFechaHora from './SelectorTamborFechaHora.svelte';
  let { value = $bindable(''), ...resto } = $props();
</script>
<SelectorTamborFechaHora bind:value {...resto}/>
