<script>
 import { onMount } from 'svelte';
 import { menuDesplegable } from '../base/menuDesplegable.js';
 import CargadorCubo from '../base/CargadorCubo.svelte';
 import Accion from './AccionRecurso.svelte';
 import * as api from '../../nucleo/api/recursos.js';
 let { audiencia=$bindable('estudiantes'), seleccion=$bindable([]), cursos=[], docentes=[], fija=false, excluidos=[] }=$props();
 let estudiantes=$state([]), buscar=$state(''), error=$state(''), cargando=$state(false);
 const destinos=$derived(audiencia==='docentes'?docentes:audiencia==='individuales'?estudiantes:cursos);
 const visibles=$derived(destinos.filter(d=>`${d.nombre} ${d.correo??''} ${d.curso??''}`.toLocaleLowerCase().includes(buscar.toLocaleLowerCase())));
 async function cargar(){cargando=true;error='';try{estudiantes=await api.estudiantes();}catch(e){error=api.mensaje(e);}finally{cargando=false;}}
 onMount(cargar);
</script>
<div class="selector-destinos">
 {#if !fija}<label>Destinatarios<select aria-label="Destinatarios" use:menuDesplegable bind:value={audiencia} onchange={()=>{seleccion=[];buscar='';}}><option value="estudiantes">Cursos completos</option><option value="individuales">Estudiantes específicos</option><option value="docentes">Únicamente docentes</option></select></label>{/if}
 <label>Buscar destinatarios<input type="search" bind:value={buscar} placeholder="Nombre, correo o curso" /></label>
 <p>{seleccion.length} seleccionados · Máximo 100 {audiencia==='estudiantes'?'cursos':'personas'} por envío.</p>
 {#if audiencia==='individuales'&&cargando}<CargadorCubo compacto mensaje="Cargando estudiantes…" />{/if}
 {#if audiencia==='individuales'&&error}<p role="alert">{error}</p><Accion icono="reiniciar" onclick={cargar}>Reintentar</Accion>{/if}
 <div class="destinos">{#each visibles as d}<label><input type="checkbox" value={d.id} bind:group={seleccion} disabled={excluidos.includes(d.id)||(!seleccion.includes(d.id)&&seleccion.length>=100)} /><span><strong>{d.nombre}</strong>{#if d.correo}<small>{d.correo}</small>{/if}{#if d.curso}<small>{d.curso}</small>{/if}{#if excluidos.includes(d.id)}<small>Ya recibe este envío</small>{/if}</span></label>{/each}</div>
 {#if !cargando&&!visibles.length}<p>No hay destinatarios que coincidan con esta búsqueda.</p>{/if}
</div>
<style>
 .selector-destinos{display:grid;gap:.7rem}label{display:grid;gap:.4rem}input[type=search],select{width:100%;box-sizing:border-box;min-width:0}.destinos{max-height:22rem;overflow:auto;display:grid;gap:.5rem}.destinos label{display:flex;align-items:start;gap:.7rem;padding:.7rem;border:1px solid var(--trazo-suave);border-radius:var(--radius-sm)}strong,small{display:block;overflow-wrap:anywhere}small,p{color:var(--ink-secondary);font-size:.8rem}p[role=alert]{color:var(--semantic-error)}
</style>
