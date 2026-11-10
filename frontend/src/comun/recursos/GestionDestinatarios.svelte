<script>
 import { onMount } from 'svelte';
 import Dialogo from '../base/Dialogo.svelte';
 import CargadorCubo from '../base/CargadorCubo.svelte';
 import Accion from './AccionRecurso.svelte';
 import SelectorDestinatarios from './SelectorDestinatarios.svelte';
 import { confirmarAccion } from '../estado/confirmaciones.svelte.js';
 import * as api from '../../nucleo/api/recursos.js';
 let { recurso, abierto=$bindable(false), alCambiar=()=>{} }=$props();
 let actual=$state(null), datos=$state(null), cursos=$state([]), docentes=$state([]), seleccion=$state([]), audiencia=$state('estudiantes');
 let ocupado=$state(false), error=$state('');
 async function cargar(){ocupado=true;error='';try{[actual,datos,cursos,docentes]=await Promise.all([api.consultar(recurso.id),api.metricas(recurso.id),api.clases(),api.docentes()]);audiencia=datos.audiencia;seleccion=[];}catch(e){error=api.mensaje(e);}finally{ocupado=false;}}
 onMount(cargar);
 async function retirar(destino){
  if(!await confirmarAccion({tipo:'confirmar',titulo:'¿Retirar este destinatario?',descripcion:`${destino.nombre} dejará de recibir este envío. Sólo se permite si no tiene respuestas. El contenido, las respuestas de los demás y el envío se conservan; las métricas de destinatarios y pendientes se actualizarán.`,confirmar:'Retirar del envío',cancelar:'Conservar destinatario'}))return;
  ocupado=true;error='';try{await api.retirarDestinatarios(actual,[destino.publicacion],datos.envio_actual);await cargar();alCambiar();}catch(e){error=api.mensaje(e);ocupado=false;}
 }
 async function agregar(){
  ocupado=true;error='';try{await api.ampliarCursos(actual,seleccion,datos.envio_actual,audiencia);await cargar();alCambiar();}catch(e){error=api.mensaje(e);ocupado=false;}
 }
</script>
<Dialogo bind:abierto titulo="Gestionar destinatarios" tipo="comunicar" ancho="48rem">
 <p><strong>{recurso.titulo}</strong></p><p>Se conserva el contenido y el mismo envío. Puedes retirar un docente, estudiante o curso sólo mientras no tenga respuestas.</p>
 {#if error}<p role="alert">{error}</p>{/if}
 {#if ocupado}<CargadorCubo compacto mensaje="Actualizando destinatarios…" />{/if}
 {#if datos&&actual&&actual.estado==='publicado'}
  <h3>Destinatarios actuales · Envío {datos.envio_actual}</h3>
  <p>{datos.cursos.length} destinos activos · {datos.destinatarios_retirados??0} retirados sin borrar su historial.</p>
  {#each datos.cursos as c}<div class="destino"><div><strong>{c.nombre}</strong><small>{c.respuestas_totales} respuestas · {c.matriculados} participantes actuales</small></div><Accion icono="eliminar" disabled={ocupado||!c.puede_retirar} onclick={()=>retirar(c)}>Retirar</Accion></div>{/each}
  {#if datos.cursos.some(c=>!c.puede_retirar)}<p>Los destinos con respuestas se conservan y no pueden retirarse.</p>{/if}
  <h3>Añadir destinatarios</h3>
  <fieldset disabled={ocupado}><legend>Seleccionar nuevos destinos</legend><SelectorDestinatarios fija bind:audiencia bind:seleccion {cursos} {docentes} excluidos={datos.cursos.map(c=>c.id)} /></fieldset>
  <Accion icono="publicar" disabled={ocupado||!seleccion.length} onclick={agregar}>Añadir al mismo envío</Accion>
 {:else if datos}<p>La publicación ya no está activa. Cierra esta ventana y actualiza la biblioteca.</p>{/if}
</Dialogo>
<style>.destino{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.8rem;border-bottom:1px solid var(--trazo-suave)}.destino>div{min-width:0}strong,small{display:block;overflow-wrap:anywhere}small{font-size:.8rem;color:var(--ink-secondary)}fieldset{min-width:0}p[role=alert]{color:var(--semantic-error)}</style>
