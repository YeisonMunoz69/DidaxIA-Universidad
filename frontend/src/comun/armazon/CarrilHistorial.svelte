<!-- Historial activo del estudiante: compone acción y lista, sin decidir su lógica. -->
<script>
  import BotonNuevaConversacion from './BotonNuevaConversacion.svelte';
  import ListaDelHistorial from './ListaDelHistorial.svelte';

  let { carrilAbierto = $bindable(false) } = $props();
</script>

<BotonNuevaConversacion bind:carrilAbierto />
<ListaDelHistorial bind:carrilAbierto />
