
<script>
  import { onMount } from 'svelte';
  import DocumentoPublico from '../piezas/DocumentoPublico.svelte';
  import { INVESTIGACION } from '../contenido/investigacion.js';
  onMount(() => document.querySelector('meta[name="description"]')?.setAttribute('content',
    'Conoce el marco de investigación y el modelo didáctico de DidaxIa para el estudio del cálculo diferencial.'));
</script>

<svelte:head><title>Investigación y modelo didáctico · DidaxIa</title></svelte:head>
<DocumentoPublico documento={INVESTIGACION} />
