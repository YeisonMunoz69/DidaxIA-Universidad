
<script>
  import { onMount } from 'svelte';
  import DocumentoPublico from '../piezas/DocumentoPublico.svelte';
  import { PRIVACIDAD } from '../contenido/privacidad.js';
  onMount(() => document.querySelector('meta[name="description"]')?.setAttribute('content',
    'Consulta la información de privacidad y tratamiento de datos personales de DidaxIa conforme a la Ley 1581 de 2012.'));
</script>

<svelte:head><title>Política de privacidad y Ley 1581 · DidaxIa</title></svelte:head>
<DocumentoPublico documento={PRIVACIDAD} />
