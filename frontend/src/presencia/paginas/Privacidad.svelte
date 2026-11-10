<!--
La página pública de `/privacidad`.

Tres líneas y ninguna decisión: el texto vive en `contenido/privacidad.js` y el
marcado en `piezas/DocumentoPublico.svelte`. Este archivo sólo une los dos, y
existe para que `presencia/rutas.js` tenga un componente por camino.

Separar el texto del marcado no es ceremonia: quien corrija este documento
después de la respuesta institucional edita un archivo de datos, no un
componente, y no puede romper la maquetación de las otras dos páginas al
hacerlo.



-->
<script>
  import { onMount } from 'svelte';
  import DocumentoPublico from '../piezas/DocumentoPublico.svelte';
  import { PRIVACIDAD } from '../contenido/privacidad.js';
  onMount(() => document.querySelector('meta[name="description"]')?.setAttribute('content',
    'Consulta la información de privacidad y tratamiento de datos personales de DidaxIa conforme a la Ley 1581 de 2012.'));
</script>

<svelte:head><title>Política de privacidad y Ley 1581 · DidaxIa</title></svelte:head>
<DocumentoPublico documento={PRIVACIDAD} />
