<!--
La página pública de `/condiciones`.

Tres líneas y ninguna decisión: el texto vive en `contenido/condiciones.js` y el
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
  import { CONDICIONES } from '../contenido/condiciones.js';
  onMount(() => document.querySelector('meta[name="description"]')?.setAttribute('content',
    'Revisa las condiciones de uso del tutor automatizado DidaxIa y sus límites antes de utilizar la plataforma.'));
</script>

<svelte:head><title>Términos y condiciones de uso · DidaxIa</title></svelte:head>
<DocumentoPublico documento={CONDICIONES} />
