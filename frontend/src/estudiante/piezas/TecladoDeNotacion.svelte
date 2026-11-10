<!--
Inserción de símbolos matemáticos.

El mismo catálogo por pestañas se ofrece en todas las bandas. Así teléfono,
tableta y escritorio conservan las mismas herramientas y cada tecla puede
mostrar su fórmula con KaTeX sin duplicar controles ocultos en el DOM.

Los botones son controles nativos y la variante rápida está agrupada en un
`fieldset`: así conserva teclado, nombre accesible y contexto de lectura sin
reimplementar interacción. El orden vigente de las teclas rápidas proviene del
recuento del contenido del proyecto; su precisión se revisará junto con el
catálogo pedagógico cuando se amplíen los símbolos.
-->
<script>
  import PestanasDeNotacion from './PestanasDeNotacion.svelte';

  let { alInsertar, alComando } = $props();
</script>

<PestanasDeNotacion {alInsertar} {alComando} />
