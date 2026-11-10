<!--
La página pública de `/investigacion`.

Tres líneas y ninguna decisión: el texto vive en `contenido/investigacion.js` y el
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
  import { INVESTIGACION } from '../contenido/investigacion.js';
  onMount(() => document.querySelector('meta[name="description"]')?.setAttribute('content',
    'Conoce el marco de investigación y el modelo didáctico de DidaxIa para el estudio del cálculo diferencial.'));
</script>

<svelte:head><title>Investigación y modelo didáctico · DidaxIa</title></svelte:head>
<DocumentoPublico documento={INVESTIGACION} />
