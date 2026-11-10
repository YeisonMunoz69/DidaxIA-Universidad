<script>
 import CargadorCubo from '../base/CargadorCubo.svelte';
 import { menuDesplegable } from '../base/menuDesplegable.js';
 import Accion from './AccionRecurso.svelte';
 import MetricasDiapositivas from './MetricasDiapositivas.svelte';
 import { toast } from '../estado/toasts.svelte.js';
 import { descargarBlob } from '../../nucleo/descargas/archivo.js';
 import { confirmarAccion } from '../estado/confirmaciones.svelte.js';
 import { onMount } from 'svelte';
 import { navegar } from '../../enrutado/navegar.js';
 import * as api from '../../nucleo/api/recursos.js';
 let { recurso } = $props();
 let datos = $state(null);
 let clase = $state('');
 let envio = $state('');
 let error = $state('');
 let descarga = $state(false);
 let actualizando = $state(false);
 let actualizado = $state('');
 let grafica = $state('barras');
 let categoria = $state({});
 let activo=true;
 let secuencia=0;
 const colores=['var(--recurso-cereza)','var(--recurso-azul)','var(--recurso-jade)','var(--recurso-ambar)','var(--recurso-violeta)','var(--recurso-coral)','var(--recurso-cian)'];
 const cursos = $derived(datos?.cursos.filter(c=>!clase||c.id===clase) ?? []);
 const matriculados = $derived(cursos.reduce((n,c)=>n+c.matriculados,0));
 const respondieron = $derived(cursos.reduce((n,c)=>n+c.respondieron,0));
 const vieron = $derived(cursos.reduce((n,c)=>n+c.vieron,0));
 async function cargar() {
  const turno=++secuencia; actualizando=true;
  try { const nuevos=await api.metricas(recurso.id,clase,envio); if(activo&&turno===secuencia){datos=nuevos;if(!envio&&nuevos.envio_actual)envio=String(nuevos.envio_actual);error='';actualizado=new Date().toLocaleTimeString();} }
  catch(e){if(activo&&turno===secuencia)error=api.mensaje(e);}
  finally{if(activo&&turno===secuencia)actualizando=false;}
 }
 function cambiarEnvio(){clase='';cargar();}
 onMount(()=>{cargar();const reloj=setInterval(()=>{if(document.visibilityState==='visible')cargar();},10000);return()=>{activo=false;clearInterval(reloj);};});
 function degradado(frecuencias) {
  const total=frecuencias.reduce((s,f)=>s+f.cantidad,0);let inicio=0;
  if(!total)return 'var(--trazo-suave)';
  return `conic-gradient(${frecuencias.map((f,i)=>{let desde=inicio;inicio+=f.cantidad/total*100;return `${colores[i%colores.length]} ${desde}% ${inicio}%`;}).join(',')})`;
 }
 async function descargar() {
  if(!await confirmarAccion({tipo:'descarga',titulo:'¿Descargar informe de recursos?',descripcion:'El PDF incluirá la participación y los resultados de los cursos seleccionados.',confirmar:'Descargar PDF'})) return;
  descarga=true;try {const blob=await api.informe(recurso.id,clase,envio);await descargarBlob(blob,`informe-recursos${envio?`-envio-${envio}`:''}.pdf`).finalizada;toast.descarga('Informe PDF preparado. Revisa las descargas del navegador.');}
  catch(e){error=api.mensaje(e);toast.error(error);}finally{descarga=false;}
 }
</script>
{#if recurso.tipo==='diapositivas'}
 {#if error}<p class="error" role="alert">{error} {datos?'Se conservan los últimos datos recibidos.':''}</p>{/if}
 {#if datos}<MetricasDiapositivas {datos} {cursos} {matriculados} {vieron} bind:clase bind:envio {actualizado} {actualizando} {descarga} alActualizar={cargar} alDescargar={descargar} alCurso={cargar} alEnvio={cambiarEnvio} />
 {:else}<CargadorCubo mensaje="Cargando métricas de la presentación…" />{/if}
{:else}
<h2>Participación y resultados</h2>
<p>Actualización automática cada 10 segundos mientras esta pantalla está visible.</p>
<div class="acciones"><Accion icono="reiniciar" onclick={cargar} disabled={actualizando}>Actualizar ahora</Accion>
 <Accion icono="descargar" onclick={descargar} disabled={!datos||descarga}>{descarga?'Preparando informe…':'Descargar informe PDF'}</Accion>
 <span class="muted">{actualizado?`Última actualización: ${actualizado}`:'Cargando métricas…'}</span></div>
{#if error}<p class="error" role="alert">{error} {datos?'Se conservan los últimos datos recibidos.':''}</p>{/if}
{#if datos}
 {#if datos.envios?.length}<label>Envío de la encuesta<select use:menuDesplegable aria-label="Envío de la encuesta" bind:value={envio} onchange={cambiarEnvio}>{#each datos.envios as e}<option value={String(e.numero)}>Envío {e.numero} · {new Date(e.publicada_en).toLocaleString()} · {e.estado}</option>{/each}</select></label><p class="muted">Las respuestas y gráficas corresponden únicamente al envío seleccionado.</p>{/if}
 <div class="fila"><label>{datos.audiencia==='docentes'?'Docente':datos.audiencia==='individuales'?'Estudiante':'Curso'}<select use:menuDesplegable aria-label={datos.audiencia==='docentes'?'Docente':datos.audiencia==='individuales'?'Estudiante':'Curso'} bind:value={clase} onchange={cargar}><option value="">Todos los destinatarios publicados</option>{#each datos.cursos as c}<option value={c.id}>{c.nombre}</option>{/each}</select></label>
 <label>Gráfica<select use:menuDesplegable aria-label="Gráfica" bind:value={grafica}><option value="barras">Barras</option><option value="circulo">Circular</option><option value="rosquilla">Rosquilla</option></select></label></div>
 {#if datos.destinatarios_retirados}<p>{datos.destinatarios_retirados} destinos retirados sin respuestas. No se incluyen en los totales actuales.</p>{/if}
 <div class="fila">
  <div class="bloque"><span class="metrica">{matriculados}</span>{datos.audiencia==='docentes'?'Docentes destinatarios':datos.audiencia==='individuales'?'Estudiantes destinatarios':'Matrícula actual'}</div>
  <div class="bloque"><span class="metrica">{recurso.tipo==='encuesta'?respondieron:vieron}</span>{recurso.tipo==='encuesta'?'Respondieron':'Abrieron las diapositivas'}</div>
  <div class="bloque"><span class="metrica">{matriculados-(recurso.tipo==='encuesta'?respondieron:vieron)}</span>Pendientes</div>
 </div>
 {#each cursos as curso}
  <div class="bloque"><h3>{curso.nombre}</h3>
   <Accion icono="visible" onclick={()=>navegar(`/recursos/publicacion?publicacion=${encodeURIComponent(curso.publicacion)}`)}>Abrir recurso de este curso</Accion>
   <p>{curso.respuestas_totales} respuestas históricas · {curso.vieron} aperturas en matrícula actual</p>
   <div class="tabla-scroll"><table><thead><tr><th>{datos.audiencia==='docentes'?'Docente':'Estudiante'}</th><th>{recurso.tipo==='encuesta'?'Encuesta':'Diapositivas'}</th><th>Fecha de respuesta</th></tr></thead>
    <tbody>{#each curso.integrantes as i}<tr><td>{i.nombre}</td><td>{recurso.tipo==='encuesta'?(i.respondida?'Respondida':'Pendiente'):(i.vista?'Abiertas':'Pendiente')}</td><td>{i.enviada_en?new Date(i.enviada_en).toLocaleString():'—'}</td></tr>{/each}</tbody>
   </table></div>
  </div>
 {/each}
 <p class="muted">Las listas usan la matrícula actual. Los resultados conservan las respuestas enviadas antes de un retiro. Abrir una presentación no acredita haberla leído completa.</p>
 {#each datos.preguntas as p}
  <div class="bloque"><h3>{p.titulo}</h3><p>{p.respondidas} respuestas{p.promedio!==null?` · Promedio ${p.promedio.toFixed(2)}`:''}</p>
   {#if p.frecuencias.length}
    {#if grafica!=='barras' && p.tipo!=='multiple'}<div class="circular" class:rosquilla={grafica==='rosquilla'} style:background={degradado(p.frecuencias)} role="img" aria-label={`Distribución de ${p.titulo}; valores en la tabla siguiente`}></div>{/if}
    {#if p.tipo==='multiple'}<p class="muted">Selección múltiple: cada respuesta puede elegir varias opciones. Los porcentajes pueden sumar más de 100 %.</p>{/if}
    {#each p.frecuencias as f,n}
     <button class="barra" class:elegida={categoria[p.id]===f.etiqueta} aria-pressed={categoria[p.id]===f.etiqueta}
      onclick={()=>categoria[p.id]=categoria[p.id]===f.etiqueta?null:f.etiqueta}>
      <span>{f.etiqueta}</span><span class="pista"><i style:width={`${Math.min(100,p.respondidas?f.cantidad/p.respondidas*100:0)}%`} style:background={colores[n%colores.length]}></i></span>
      <strong>{f.cantidad} · {p.respondidas?(f.cantidad/p.respondidas*100).toFixed(1):'0'} %</strong>
     </button>
    {/each}
    {#if categoria[p.id]}<p role="status">Opción seleccionada: {categoria[p.id]}. Puedes cambiar de curso para comparar su frecuencia.</p>{/if}
   {:else if p.textos.length}<details><summary>Ver respuestas de texto ({p.textos.length})</summary>{#each p.textos as t}<p class="texto-respuesta">{t}</p>{/each}</details>
   {/if}
  </div>
 {/each}
{:else}<CargadorCubo mensaje="Cargando métricas de la encuesta…" />{/if}
{/if}
<style>
 .barra { display:grid; grid-template-columns:minmax(100px,1fr) minmax(60px,2fr) 95px; align-items:center; gap:1rem; width:100%; margin:.4rem 0; text-align:left; }
 .barra.elegida { outline:2px solid var(--accent-main); } .pista { background:var(--recurso-pista); height:15px; border-radius:5px; overflow:hidden; } .pista i { display:block; height:100%; }
 .barra strong { font-size:.85rem; text-align:right; } .circular { width:180px; height:180px; border-radius:50%; margin:1rem auto; position:relative; }
 .circular.rosquilla::after { content:''; position:absolute; inset:25%; border-radius:50%; background:var(--surface-panel); }
 .texto-respuesta { white-space:pre-wrap; border-bottom:1px solid var(--trazo-suave); padding:.5rem; overflow-wrap:anywhere; }
 @media(max-width:500px){.barra{grid-template-columns:1fr 90px;}.pista{grid-column:1;grid-row:2;}.barra strong{grid-column:2;grid-row:1 / 3;}}
</style>
