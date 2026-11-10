<script>
  import PresentacionDidaxia from './PresentacionDidaxia.svelte';
  let { contenido, titulo = 'Presentación', pantallaCompleta=false, alCerrarPresentacion=()=>{} } = $props();
</script>
<PresentacionDidaxia {contenido} {titulo} {pantallaCompleta} {alCerrarPresentacion} />
