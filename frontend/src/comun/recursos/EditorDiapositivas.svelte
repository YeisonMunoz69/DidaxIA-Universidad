<script>
  import PresentacionDidaxia from './PresentacionDidaxia.svelte';
  let { recurso = $bindable(), espacioTrabajo=false, alControles = () => {} } = $props();
</script>
{#if !espacioTrabajo}<p class="muted">Edita el contenido y los colores de cada diapositiva. Para conservar los cambios en tu cuenta, usa Guardar borrador al terminar.</p>{/if}
<PresentacionDidaxia contenido={recurso.contenido} titulo={recurso.titulo} editable {espacioTrabajo} {alControles} onchange={(contenido) => recurso.contenido = contenido} />
