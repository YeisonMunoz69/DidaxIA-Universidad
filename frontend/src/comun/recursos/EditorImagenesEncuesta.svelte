<script>
 import Accion from './AccionRecurso.svelte';
 import CargadorCubo from '../base/CargadorCubo.svelte';
 import { prepararImagenEncuesta } from '../../nucleo/recursos/imagenEncuesta.js';
 let { imagenes=$bindable(), titulo='Imágenes del enunciado' }=$props();
 const lista=$derived(imagenes??[]);
 let ocupado=$state(false), error=$state('');
 async function agregar(evento){
  const control=evento.currentTarget, archivo=control.files?.[0];if(!archivo)return;
  ocupado=true;error='';
  try{if(lista.length>=4)throw new Error('Puedes añadir hasta cuatro imágenes.');imagenes=[...lista,await prepararImagenEncuesta(archivo)];}
  catch(e){error=e.message;}finally{ocupado=false;control.value='';}
 }
 function mover(n,d){const copia=[...lista];[copia[n],copia[n+d]]=[copia[n+d],copia[n]];imagenes=copia;}
</script>
<section class="editor-evidencia" aria-label={titulo}>
 <h4>{titulo}</h4><p>Añade capturas anonimizadas. Hasta cuatro imágenes por bloque. Puedes guardar el borrador sin completar las descripciones; serán obligatorias al publicar.</p>
 <label>Añadir imagen<input type="file" accept="image/png,image/jpeg,image/webp" disabled={ocupado||lista.length>=4} onchange={agregar} /></label>
 {#if ocupado}<CargadorCubo compacto mensaje="Preparando imagen…" />{/if}
 {#if error}<p role="alert">{error}</p>{/if}
 {#each lista as imagen,n}
  <div class="imagen-editor">
   <img src={imagen.src} alt={imagen.alt||'Imagen pendiente de describir'} />
   <label>Descripción accesible de la imagen<input maxlength="500" bind:value={imagen.alt} placeholder="Qué muestra la captura y qué debe revisar la docente" /></label>
   {#if !imagen.alt?.trim()}<p class="pendiente-descripcion">Pendiente antes de publicar: describe el contenido de esta imagen para quien no pueda verla.</p>{/if}
   <label>Pie de imagen<textarea maxlength="1000" bind:value={imagen.pie}></textarea></label>
   <div class="acciones"><Accion icono="subir" disabled={n===0} onclick={()=>mover(n,-1)}>Subir imagen</Accion><Accion icono="bajar" disabled={n===lista.length-1} onclick={()=>mover(n,1)}>Bajar imagen</Accion><Accion icono="eliminar" onclick={()=>imagenes=lista.filter((_,i)=>i!==n)}>Quitar imagen del borrador</Accion></div>
  </div>
 {/each}
</section>
<style>
 .pendiente-descripcion{font-weight:600}
 .editor-evidencia{border:1px dashed var(--trazo-suave);border-radius:var(--radius-sm);padding:1rem;margin:1rem 0}.editor-evidencia h4{margin:0}.editor-evidencia p{font-size:.85rem;color:var(--ink-secondary)}.imagen-editor{border-top:1px solid var(--trazo-suave);margin-top:1rem;padding-top:1rem}img{display:block;max-width:100%;max-height:14rem;height:auto;margin:auto}label{display:grid;gap:.4rem;margin:.8rem 0}input,textarea{box-sizing:border-box;max-width:100%;min-width:0}p[role=alert]{color:var(--semantic-error)}
</style>
