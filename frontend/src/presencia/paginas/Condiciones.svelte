
<script>
  import { onMount } from 'svelte';
  import DocumentoPublico from '../piezas/DocumentoPublico.svelte';
  import { CONDICIONES } from '../contenido/condiciones.js';
  onMount(() => document.querySelector('meta[name="description"]')?.setAttribute('content',
    'Revisa las condiciones de uso del tutor automatizado DidaxIa y sus límites antes de utilizar la plataforma.'));
</script>

<svelte:head><title>Términos y condiciones de uso · DidaxIa</title></svelte:head>
<DocumentoPublico documento={CONDICIONES} />
