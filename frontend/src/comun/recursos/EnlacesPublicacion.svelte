<script>
 import CargadorCubo from '../base/CargadorCubo.svelte';
 import { onMount } from 'svelte';
 import Dialogo from '../base/Dialogo.svelte';
 import Accion from './AccionRecurso.svelte';
 import { menuDesplegable } from '../base/menuDesplegable.js';
 import { toast } from '../estado/toasts.svelte.js';
 import * as api from '../../nucleo/api/recursos.js';
 import { urlPublicacion } from './enlacesPublicados.js';
 let { recurso, abierto=$bindable(false) }=$props();
 let datos=$state(null), envio=$state(''), error=$state(''), cargando=$state(false);
 let secuencia=0;
 async function cargar(){const turno=++secuencia;cargando=true;error='';try{const d=await api.metricas(recurso.id,'',envio);if(turno===secuencia){datos=d;if(!envio)envio=String(d.envio_actual);}}catch(e){if(turno===secuencia)error=api.mensaje(e);}finally{if(turno===secuencia)cargando=false;}}
 async function copiar(curso){try{await navigator.clipboard.writeText(urlPublicacion(curso.publicacion,datos.audiencia));toast.exito(`Enlace del envío ${envio} copiado para ${curso.nombre}.`);}catch{toast.alerta('No se pudo copiar. Selecciona el enlace y cópialo manualmente.');}}
 onMount(()=>{cargar();return()=>{secuencia++;};});
</script>
<Dialogo bind:abierto titulo="Enlaces de publicación" tipo="comunicar" ancho="44rem">
 <p><strong>{recurso.titulo}</strong></p>
 <p>Copia el enlace para usarlo en otra presentación o en sus recursos. Cada envío y destinatario tiene su propia URL. Quien lo abra debe tener acceso a la publicación.</p>
 {#if error}<p role="alert">{error}</p><Accion icono="reiniciar" onclick={cargar}>Reintentar</Accion>{/if}
 {#if datos}
  <label>Envío<select aria-label="Envío del enlace" use:menuDesplegable bind:value={envio} onchange={cargar}>{#each datos.envios as e}<option value={String(e.numero)}>Envío {e.numero} · {e.estado} · {new Date(e.publicada_en).toLocaleString()}</option>{/each}</select></label>
  {#if cargando}<CargadorCubo compacto mensaje="Cargando enlaces…" />{:else}
   {#each datos.cursos as c}<div class="enlace-destino"><label>{c.nombre}<input aria-label={`Enlace para ${c.nombre}`} value={urlPublicacion(c.publicacion,datos.audiencia)} readonly onclick={e=>e.currentTarget.select()} /></label><Accion icono="copiar" onclick={()=>copiar(c)}>Copiar enlace</Accion></div>{/each}
  {/if}
 {:else if cargando}<CargadorCubo compacto mensaje="Cargando enlaces…" />{/if}
</Dialogo>
<style>
 p{font-size:.9rem;line-height:1.6}label{display:grid;gap:6px;font-size:.85rem}input{width:100%;min-width:0;box-sizing:border-box;padding:10px;border:1px solid var(--trazo);border-radius:var(--radius-sm);background:var(--surface-paper);color:var(--ink-primary)}.enlace-destino{display:flex;gap:12px;align-items:end;margin-top:18px}.enlace-destino label{flex:1;min-width:0}.enlace-destino :global(button){flex-shrink:0}@media(max-width:600px){.enlace-destino{align-items:stretch;flex-direction:column}}
</style>
