<script>
  import Accion from './AccionRecurso.svelte';
  let { controles } = $props();
</script>

<div class="herramientas-presentacion" aria-label="Herramientas del lienzo">
  <Accion icono="deshacer" aria-label="Deshacer" title="Deshacer (Ctrl+Z)" disabled={!controles?.undo} onclick={()=>controles.ejecutar('undo')} />
  <Accion icono="rehacer" aria-label="Rehacer" title="Rehacer (Ctrl+Mayús+Z)" disabled={!controles?.redo} onclick={()=>controles.ejecutar('redo')} />
  <Accion icono="panel-izq" aria-label="Diapositivas" aria-expanded={controles?.indice} disabled={!controles} onclick={()=>controles.ejecutar('indice')}>Diapositivas</Accion>
  <Accion icono="panel-der" aria-label="Propiedades" aria-expanded={controles?.propiedades} disabled={!controles} onclick={()=>controles.ejecutar('propiedades')}>Propiedades</Accion>
  <Accion icono="exportar" disabled={!controles} onclick={()=>controles.ejecutar('savehtml')}>HTML</Accion>
  <Accion icono="descargar" disabled={!controles||controles.pdfBusy} onclick={()=>controles.ejecutar('pdf')}>PDF</Accion>
  <Accion icono="enlace" disabled={!controles} onclick={()=>controles.ejecutar('resources')}>Recursos</Accion>
</div>

<style>
  .herramientas-presentacion { display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin-left:auto; }
  @media(max-width:899px) { .herramientas-presentacion { display:none; } }
</style>
