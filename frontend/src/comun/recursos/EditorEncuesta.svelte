<script>
 import { onMount } from 'svelte';
 import Accion from './AccionRecurso.svelte';
 import EditorImagenesEncuesta from './EditorImagenesEncuesta.svelte';
 import { confirmarAccion } from '../estado/confirmaciones.svelte.js';
 import { preguntaNueva } from '../../nucleo/api/recursos.js';
 import { menuDesplegable } from '../base/menuDesplegable.js';
 import { resumenImagenesEncuesta, MAX_BYTES_IMAGENES_ENCUESTA } from '../../nucleo/recursos/presupuestoImagenesEncuesta.js';
 let { recurso = $bindable() } = $props();
 let movil=$state(false), paginaActiva=$state(0), textosOpciones=$state({});
 const evidencia=$derived(resumenImagenesEncuesta(recurso.contenido));
 onMount(()=>{const banda=matchMedia('(max-width: 650px)');const ajustar=()=>movil=banda.matches;ajustar();banda.addEventListener('change',ajustar);return()=>banda.removeEventListener('change',ajustar);});
 const tipos = { texto:'Respuesta corta', parrafo:'Párrafo', unica:'Selección única', multiple:'Casillas múltiples', desplegable:'Lista desplegable', escala:'Escala lineal', numero:'Número', fecha:'Fecha', correo:'Correo electrónico' };
 function mover(lista, n, direccion) { const v=lista.splice(n,1)[0]; lista.splice(n+direccion,0,v); }
 function moverPagina(n,direccion) { mover(recurso.contenido.paginas,n,direccion);paginaActiva=n+direccion; }
 function nuevaPagina() { recurso.contenido.paginas.push({ titulo:'Nueva página', descripcion:'', preguntas:[preguntaNueva()] }); paginaActiva=recurso.contenido.paginas.length-1; }
 function copiarPregunta(pagina,p) { pagina.preguntas.push({...JSON.parse(JSON.stringify(p)), id:crypto.randomUUID()}); }
 function cambiarTipo(p,valor){p.tipo=valor;if(p.tipo!=='multiple')delete p.exclusivas;if(['unica','multiple','desplegable'].includes(valor))p.opciones??=[];if(valor==='escala'){p.minimo??=1;p.maximo??=5;}}
 function cambiarOpciones(n,j,texto){
  const p=recurso.contenido.paginas[n].preguntas[j];textosOpciones[p.id]=texto;
  const opciones=texto.split('\n').map(v=>v.trim()).filter(Boolean);
  const nueva={...p,opciones,...(p.exclusivas?{exclusivas:p.exclusivas.filter(o=>opciones.includes(o))}:{})};
  recurso={...recurso,contenido:{...recurso.contenido,paginas:recurso.contenido.paginas.map((pagina,i)=>i===n?{...pagina,preguntas:pagina.preguntas.map((pregunta,k)=>k===j?nueva:pregunta)}:pagina)}};
 }
 function exclusiva(p,opcion,marcada){p.exclusivas=marcada?[...(p.exclusivas??[]),opcion]:(p.exclusivas??[]).filter(o=>o!==opcion);}
 async function eliminarPagina(n) {
  if (await confirmarAccion({tipo:'eliminar',titulo:'¿Eliminar esta página?',descripcion:`Se quitará la página y sus ${recurso.contenido.paginas[n].preguntas.length} pregunta(s) del borrador.`,confirmar:'Eliminar página',cancelar:'Conservar página'})) {recurso.contenido.paginas.splice(n,1);paginaActiva=Math.min(paginaActiva,recurso.contenido.paginas.length-1);}
 }
 async function eliminarPregunta(pagina,j) {
  if (await confirmarAccion({tipo:'eliminar',titulo:'¿Eliminar esta pregunta?',descripcion:`Se quitará «${pagina.preguntas[j].titulo || 'Pregunta sin título'}» del borrador.`,confirmar:'Eliminar pregunta',cancelar:'Conservar pregunta'})) pagina.preguntas.splice(j,1);
 }
</script>
{#if evidencia.cantidad}
 <div class="resumen-imagenes" class:excedido={evidencia.bytes>MAX_BYTES_IMAGENES_ENCUESTA}>
  <p>{evidencia.cantidad} imágenes · {(evidencia.bytes/1_000_000).toFixed(2).replace('.',',')} de 8 MB, incluidas las repeticiones.</p>
  {#if evidencia.bytes>MAX_BYTES_IMAGENES_ENCUESTA}<p>Reduce el tamaño o quita alguna imagen para guardar.</p>{/if}
  {#if evidencia.sinDescripcion}<p>{evidencia.sinDescripcion} imágenes sin descripción accesible. Puedes guardar el borrador y completarlas antes de publicar.</p>{/if}
 </div>
{/if}
{#if movil}<nav class="paginas-editor" aria-label="Páginas del editor"><label>Página de la encuesta<select use:menuDesplegable={paginaActiva} bind:value={paginaActiva}>{#each recurso.contenido.paginas as pagina,n}<option value={n}>Página {n+1} · {pagina.titulo}</option>{/each}</select></label><p>{recurso.contenido.paginas[paginaActiva]?.preguntas.length??0} preguntas en esta página · {recurso.contenido.paginas.length} páginas en total</p></nav>{/if}
{#each recurso.contenido.paginas as pagina, n}
 <section class="bloque pagina-editor" hidden={movil&&n!==paginaActiva} aria-label={`Página ${n+1}`}>
  <div class="acciones acciones-pagina"><h2>Página {n+1}</h2>
   <Accion icono="subir" disabled={n===0} onclick={()=>moverPagina(n,-1)}>Subir página</Accion>
   <Accion icono="bajar" disabled={n===recurso.contenido.paginas.length-1} onclick={()=>moverPagina(n,1)}>Bajar página</Accion>
   <Accion icono="eliminar" disabled={recurso.contenido.paginas.length===1} onclick={()=>eliminarPagina(n)}>Eliminar página</Accion>
  </div>
  <label>Título de página<input maxlength="250" bind:value={pagina.titulo} /></label>
  <label>Descripción de página<textarea bind:value={pagina.descripcion}></textarea></label>
  <EditorImagenesEncuesta bind:imagenes={pagina.imagenes} titulo="Imágenes de esta página" />
  <details><summary>Transcripción opcional de las imágenes</summary><label>Texto accesible de la evidencia<textarea maxlength="10000" rows="6" bind:value={pagina.transcripcion}></textarea></label><p>Se mostrará al abrir «Leer transcripción de la evidencia». No incluya identidades de estudiantes.</p></details>
  {#each pagina.preguntas as p, j (p.id)}
   <fieldset>
    <legend>Pregunta {j+1}</legend>
    <label>Pregunta<input maxlength="500" bind:value={p.titulo} /></label>
    <div class="fila">
     <label>Tipo de pregunta<select use:menuDesplegable={p.tipo} bind:value={p.tipo} onchange={e=>cambiarTipo(p,e.currentTarget.value)}>{#each Object.entries(tipos) as [valor,rotulo]}<option value={valor}>{rotulo}</option>{/each}</select></label>
     <label class="check"><input type="checkbox" bind:checked={p.obligatoria} />Obligatoria</label>
    </div>
    <label>Ayuda para responder<input maxlength="2000" bind:value={p.ayuda} /></label>
    <EditorImagenesEncuesta bind:imagenes={p.imagenes} titulo="Imágenes de esta pregunta" />
    <details><summary>Transcripción opcional de esta pregunta</summary><label>Texto accesible de esta pregunta<textarea maxlength="10000" rows="4" bind:value={p.transcripcion}></textarea></label></details>
    {#if ['unica','multiple','desplegable'].includes(p.tipo)}
     <label>Opciones (una por línea)<textarea rows="3" value={textosOpciones[p.id]??(p.opciones??[]).join('\n')}
       oninput={e=>cambiarOpciones(n,j,e.currentTarget.value)}></textarea></label>
     {#if p.tipo==='multiple'}<details><summary>Opciones que deben marcarse solas</summary><p>Al elegir una de estas opciones se desmarcan las demás, por ejemplo «No pude usar la aplicación».</p>{#each p.opciones as opcion}<label class="check"><input type="checkbox" checked={p.exclusivas?.includes(opcion)??false} onchange={e=>exclusiva(p,opcion,e.currentTarget.checked)} />{opcion}</label>{/each}</details>{/if}
    {:else if p.tipo==='escala'}
     <div class="fila"><label>Mínimo<input type="number" min="0" max="9" bind:value={p.minimo} /></label>
      <label>Máximo<input type="number" min="1" max="10" bind:value={p.maximo} /></label></div>
    {/if}
    <div class="acciones acciones-pregunta">
     <Accion icono="subir" disabled={j===0} onclick={()=>mover(pagina.preguntas,j,-1)}>Subir pregunta</Accion>
     <Accion icono="bajar" disabled={j===pagina.preguntas.length-1} onclick={()=>mover(pagina.preguntas,j,1)}>Bajar pregunta</Accion>
     <Accion icono="duplicar" onclick={()=>copiarPregunta(pagina,p)}>Duplicar pregunta</Accion>
     <Accion icono="eliminar" disabled={pagina.preguntas.length===1} onclick={()=>eliminarPregunta(pagina,j)}>Eliminar pregunta</Accion>
    </div>
   </fieldset>
  {/each}
  <Accion icono="pregunta" onclick={()=>pagina.preguntas.push(preguntaNueva())}>Añadir pregunta</Accion>
 </section>
{/each}
<Accion icono="pagina" onclick={nuevaPagina}>Añadir página</Accion>
<style>
 .resumen-imagenes{padding:12px 16px;margin:16px 0;border:1px solid var(--trazo-suave);border-radius:var(--radius-sm);background:var(--accent-surface)}
 .resumen-imagenes p{margin:4px 0}.resumen-imagenes.excedido{border-color:var(--semantic-error)}
 .pagina-editor[hidden] { display:none; }
 .paginas-editor { padding:12px; background:var(--accent-surface); border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); }
 .paginas-editor p { font-size:.8rem; color:var(--ink-secondary); margin:8px 0 0; }
 @media(max-width:650px) {
   .pagina-editor .acciones-pagina,.pagina-editor .acciones-pregunta { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
   .acciones-pagina h2 { grid-column:1 / -1; margin:0 0 4px; }
   .acciones-pagina :global(button),.acciones-pregunta :global(button) { padding:8px 6px; font-size:.75rem; min-width:0; }
   .pagina-editor :global(fieldset) { margin:20px 0; padding:12px; }
   .pagina-editor :global(legend) { padding:0 6px; color:var(--accent-main); font-weight:650; }
 }
</style>
