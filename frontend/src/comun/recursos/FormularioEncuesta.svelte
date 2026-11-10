<script>
 import { tick } from 'svelte';
 import Accion from './AccionRecurso.svelte';
 import ImagenesEncuesta from './ImagenesEncuesta.svelte';
 import Icono from '../base/Icono.svelte';
 import Dialogo from '../base/Dialogo.svelte';
 import SelectorFecha from '../base/SelectorFecha.svelte';
 import { menuDesplegable } from '../base/menuDesplegable.js';
 import { fechaBogota } from '../../nucleo/formato/selectorFecha.js';
 import { confirmarAccion } from '../estado/confirmaciones.svelte.js';
 import { problemaPregunta, contestada, prepararRespuestas } from './validacionEncuesta.js';
 let { recurso, respuestas=$bindable({}), soloLectura=false, previa=false, ocupado=false, corroborar=false, correo='', contexto=null, alEnviar=async()=>{} }=$props();
 let pagina=$state(0), errores=$state([]), dialogoError=$state(false), revisadas=$state(new Set());
 const paginas=$derived(recurso.contenido.paginas);
 const preguntas=$derived(paginas.flatMap(p=>p.preguntas));
 const completadas=$derived(preguntas.filter(p=>contestada(p,respuestas[p.id])).length);
 let formulario, inicioPagina;
 function responder(id,valor){respuestas={...respuestas,[id]:valor};}
 $effect(()=>{if(correo&&!soloLectura&&!previa)for(const p of preguntas)if(p.tipo==='correo'&&respuestas[p.id]===undefined)respuestas[p.id]=correo;});
 function multiple(p,opcion,marcada){
  const actual=Array.isArray(respuestas[p.id])?respuestas[p.id]:[];
  respuestas[p.id]=!marcada?actual.filter(v=>v!==opcion):p.exclusivas?.includes(opcion)?[opcion]:[...actual.filter(v=>!p.exclusivas?.includes(v)),opcion];
 }
 async function revisar(lista){
  revisadas=new Set([...revisadas,...lista.map(p=>p.id)]);errores=lista.map(p=>({id:p.id,titulo:p.titulo,mensaje:problemaPregunta(p,respuestas[p.id])})).filter(e=>e.mensaje);
  if(!errores.length)return true;
  pagina=paginas.findIndex(p=>p.preguntas.some(q=>q.id===errores[0].id));await tick();dialogoError=true;return false;
 }
 async function enfocar(id){dialogoError=false;pagina=paginas.findIndex(p=>p.preguntas.some(q=>q.id===id));await tick();const campo=formulario?.querySelector(`[data-pregunta="${CSS.escape(id)}"]`);campo?.scrollIntoView({behavior:'smooth',block:'center'});campo?.querySelector('input,textarea,select,button')?.focus();}
 async function cambiarPagina(indice){pagina=Math.max(0,Math.min(indice,paginas.length-1));await tick();inicioPagina?.scrollIntoView({block:'start',behavior:'instant'});inicioPagina?.focus({preventScroll:true});}
 async function avanzar(){if(!soloLectura&&!previa&&!await revisar(paginas[pagina].preguntas))return;await cambiarPagina(pagina+1);}
 async function enviar(e){
  e.preventDefault();if(ocupado||soloLectura||previa||!await revisar(preguntas))return;
  if(!await confirmarAccion({titulo:corroborar?'¿Actualizar y confirmar tus datos?':'¿Enviar tu encuesta?',descripcion:corroborar?'Se registrarán los datos revisados en este envío. Tu respuesta anterior se conservará.':'Se registrarán todas tus respuestas. Después podrás revisarlas.',confirmar:corroborar?'Confirmar datos':'Enviar respuestas',cancelar:'Revisar encuesta'}))return;
  await alEnviar(prepararRespuestas(preguntas,respuestas));
 }
</script>
<div class="bloque formulario-encuesta">
 <h2>{recurso.titulo}</h2><p>{recurso.descripcion}</p>
 {#if contexto}<section class="contexto-encuesta" aria-label="Datos registrados por el sistema"><div><Icono nombre="candado" medida={18} /><strong>Datos de tu participación</strong></div><dl><div><dt>Cuenta institucional</dt><dd>{contexto.correo}</dd></div><div><dt>{contexto.audiencia==='docentes'?'Destinatario':'Curso'}</dt><dd>{contexto.curso}</dd></div><div><dt>Fecha de envío</dt><dd>{contexto.enviada_en?new Date(contexto.enviada_en).toLocaleString('es-CO'):'Se registrará automáticamente al enviar'}</dd></div></dl><p>El sistema registra estos datos. No necesitas escribirlos ni puedes modificarlos en la encuesta.</p></section>{/if}
 {#if previa}<p class="aviso">Vista previa. Las respuestas aquí no se registran.</p>{/if}
 {#if corroborar&&!soloLectura}<p class="aviso"><Icono nombre="check" />Recuperamos tus respuestas del envío anterior. Revísalas, actualiza lo necesario y confirma tus datos para este envío.</p>{/if}
 <div class="progreso-encuesta"><span>Página {pagina+1} de {paginas.length}</span><strong>{completadas} de {preguntas.length} preguntas contestadas</strong></div>
 <progress value={completadas} max={preguntas.length} aria-label="Preguntas contestadas"></progress>
 {#if !soloLectura}<p class="leyenda-preguntas"><span class="pendiente">Amarillo: por responder</span><span class="completa">Verde: contestada</span><span>* Obligatoria</span></p>{/if}
 <form bind:this={formulario} onsubmit={enviar} novalidate>
  <h3 bind:this={inicioPagina} tabindex="-1">{paginas[pagina].titulo}</h3><p>{paginas[pagina].descripcion}</p>
  <ImagenesEncuesta imagenes={paginas[pagina].imagenes??[]} />
  {#if paginas[pagina].transcripcion}<details class="transcripcion"><summary>Leer transcripción de la evidencia</summary><p>{paginas[pagina].transcripcion}</p></details>{/if}
  {#each paginas[pagina].preguntas as p (p.id)}
   {@const completa=contestada(p,respuestas[p.id])}{@const mensaje=revisadas.has(p.id)&&!previa?problemaPregunta(p,respuestas[p.id]):''}
   <fieldset data-pregunta={p.id} class:contestada={completa&&!mensaje} class:pendiente={!completa&&!mensaje&&!soloLectura} class:invalida={!!mensaje&&!soloLectura} aria-describedby={mensaje?`error-${p.id}`:undefined}>
    <legend class="nombre-pregunta">{p.titulo}{p.obligatoria?' *':''}</legend>
    <h4 class="titulo-pregunta" id={`titulo-${p.id}`}>{p.titulo}{p.obligatoria?' *':''}</h4>
    <span class="situacion-pregunta" aria-live="polite"><Icono nombre={mensaje?'alerta':completa?'check':'reloj'} medida={15} />{mensaje?'Revisa esta respuesta':completa?'Contestada':p.obligatoria?'Pendiente · obligatoria':'Opcional · por responder'}</span>
    {#if p.ayuda}<p class="muted">{p.ayuda}</p>{/if}
    <ImagenesEncuesta imagenes={p.imagenes??[]} />
    {#if p.transcripcion}<details class="transcripcion"><summary>Leer transcripción de esta pregunta</summary><p>{p.transcripcion}</p></details>{/if}
    <fieldset class="controles-respuesta" disabled={soloLectura||ocupado}><legend class="nombre-pregunta">Respuesta: {p.titulo}</legend>
    {#if p.tipo==='unica'}
     {#each p.opciones as opcion}<label class="check"><input type="radio" name={p.id} value={opcion} checked={respuestas[p.id]===opcion} onchange={()=>responder(p.id,opcion)} />{opcion}</label>{/each}
    {:else if p.tipo==='multiple'}
     {#each p.opciones as opcion}<label class="check"><input type="checkbox" checked={(respuestas[p.id]??[]).includes(opcion)} onchange={e=>multiple(p,opcion,e.currentTarget.checked)} />{opcion}</label>{/each}
    {:else if p.tipo==='desplegable'||p.tipo==='escala'}
     <label><span class="nombre-pregunta">{p.titulo}</span><select aria-label={p.titulo} disabled={soloLectura||ocupado} use:menuDesplegable bind:value={respuestas[p.id]}><option value="">Selecciona {p.tipo==='escala'?'un valor':'una opción'}</option>
      {#each p.tipo==='escala'?Array.from({length:p.maximo-p.minimo+1},(_,i)=>p.minimo+i):p.opciones as valor}<option value={valor}>{valor}</option>{/each}</select></label>
    {:else if p.tipo==='parrafo'}<label><span class="nombre-pregunta">{p.titulo}</span><textarea rows="4" maxlength="10000" bind:value={respuestas[p.id]}></textarea></label>
    {:else if p.tipo==='fecha'}
     <SelectorFecha etiqueta={p.titulo} minimo="1900-01-01" maximo="2100-12-31" limpiable value={respuestas[p.id]??''} alCambiar={valor=>respuestas[p.id]=valor} />
     <Accion icono="calendario" onclick={()=>respuestas[p.id]=fechaBogota()}>Usar hoy</Accion>
    {:else}<label><span class="nombre-pregunta">{p.titulo}</span><input type="text" inputmode={p.tipo==='numero'?'decimal':p.tipo==='correo'?'email':'text'} autocomplete={p.tipo==='correo'?'email':'off'} maxlength="1000" bind:value={respuestas[p.id]} aria-invalid={!!mensaje} /></label>{/if}
    </fieldset>
    {#if mensaje&&!soloLectura}<p id={`error-${p.id}`} class="error-campo"><Icono nombre="alerta" medida={18} />{mensaje}</p>{/if}
   </fieldset>
  {/each}
  <div class="acciones navegacion-paginas">
   <Accion icono="flecha-izq" disabled={pagina===0||ocupado} onclick={()=>cambiarPagina(pagina-1)}>Anterior</Accion>
   {#if pagina<paginas.length-1}<Accion icono="flecha-der" disabled={ocupado} onclick={avanzar}>Siguiente página</Accion>
   {:else if !soloLectura&&!previa}<Accion icono="enviar" class="primario" type="submit" disabled={ocupado}>{ocupado?'Enviando…':corroborar?'Actualizar y confirmar datos':'Enviar encuesta completa'}</Accion>{/if}
  </div>
 </form>
</div>
<Dialogo bind:abierto={dialogoError} titulo="Revisa tu respuesta" tipo="comunicar">
 <p>Hay campos que necesitan tu atención. Tus respuestas se conservan.</p>
 <div class="errores-encuesta">{#each errores as e}<button type="button" onclick={()=>enfocar(e.id)}><strong>{e.titulo}</strong><span>{e.mensaje}</span><small>Ir a esta pregunta →</small></button>{/each}</div>
</Dialogo>
<style>
 .formulario-encuesta p{max-inline-size:none;width:100%;box-sizing:border-box;overflow-wrap:anywhere}.formulario-encuesta form{min-width:0}.transcripcion p{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}
 .controles-respuesta{border:0!important;box-shadow:none!important;padding:0!important;margin:0!important;background:transparent!important} .contexto-encuesta{padding:14px 16px;background:var(--surface-paper);border:1px solid var(--trazo-suave);border-radius:var(--radius-sm);margin:16px 0}.contexto-encuesta>div{display:flex;gap:8px;align-items:center;font-size:.85rem}.contexto-encuesta dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,200px),1fr));gap:12px;margin:14px 0 0}.contexto-encuesta dt{font-size:.72rem;color:var(--ink-secondary)}.contexto-encuesta dd{margin:4px 0 0;font-size:.82rem;overflow-wrap:anywhere}.contexto-encuesta p{margin:12px 0 0;font-size:.75rem;color:var(--ink-secondary)}
 progress{width:100%;height:8px;accent-color:var(--semantic-success)}.progreso-encuesta{display:flex;justify-content:space-between;gap:12px;font-size:.85rem}.leyenda-preguntas{display:flex;flex-wrap:wrap;gap:16px;font-size:.78rem}.leyenda-preguntas .pendiente{color:var(--encuesta-pendiente-ink)}.leyenda-preguntas .completa{color:var(--semantic-success)}
 fieldset{min-inline-size:0;box-sizing:border-box;position:relative;transition:background .18s,border-color .18s;border-bottom-width:3px!important}fieldset.pendiente{border-color:var(--encuesta-pendiente)!important;background:var(--encuesta-pendiente-bg)!important}fieldset.contestada{border-color:var(--semantic-success)!important;background:var(--encuesta-completa-bg)!important}fieldset.invalida{border-color:var(--semantic-error)!important;background:var(--semantic-error-bg)!important;box-shadow:0 0 0 2px var(--semantic-error-bg)}.nombre-pregunta{position:absolute;inline-size:1px;block-size:1px;padding:0;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.titulo-pregunta{margin:0 0 .75rem;font-size:1rem;line-height:1.5;font-weight:650;overflow-wrap:anywhere}.situacion-pregunta{display:flex;gap:6px;align-items:center;font-size:.74rem;color:var(--ink-secondary);margin-bottom:10px}.error-campo{display:flex;gap:8px;color:var(--semantic-error);font-size:.85rem}.errores-encuesta{display:grid;gap:10px}.errores-encuesta button{display:grid;gap:6px;text-align:left;padding:14px;background:var(--semantic-error-bg);color:var(--ink-primary);border:1px solid var(--semantic-error);border-radius:var(--radius-sm);cursor:pointer}.errores-encuesta small{color:var(--accent-main)}.navegacion-paginas{justify-content:space-between;position:relative;padding:12px;background:var(--surface-paper);border:1px solid var(--trazo-suave);border-radius:var(--radius-sm)}@media(max-width:600px){.progreso-encuesta{flex-direction:column}.formulario-encuesta{padding:14px!important}fieldset{padding:12px!important}}@media(prefers-reduced-motion:reduce){fieldset{transition:none}}
</style>
