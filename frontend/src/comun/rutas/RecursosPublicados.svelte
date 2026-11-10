<script>
 import { onMount } from 'svelte';
 import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
 import { destinoDe } from '../../nucleo/sesion/acceso.js';
 import * as api from '../../nucleo/api/recursos.js';
 import { navegar, protegerSalida } from '../../enrutado/navegar.js';
 import { confirmarAccion } from '../estado/confirmaciones.svelte.js';
 import { confirmaciones } from '../estado/confirmaciones.svelte.js';
 import Dialogo from '../base/Dialogo.svelte';
 import CargadorCubo from '../base/CargadorCubo.svelte';
 import PestanasSegmentadas from '../base/PestanasSegmentadas.svelte';
 import * as apiSesion from '../../nucleo/api/sesion.js';
 import Icono from '../base/Icono.svelte';
 import Accion from '../recursos/AccionRecurso.svelte';
 import FormularioEncuesta from '../../comun/recursos/FormularioEncuesta.svelte';
 import VisorDiapositivas from '../../comun/recursos/VisorDiapositivas.svelte';
 import '../../comun/recursos/recursos.css';
 let { consultaActual = '', tipoInicial = '' } = $props();
 let lista=$state([]), publicacion=$state(null), respuestas=$state({}), error=$state(''), cargando=$state(true), ocupado=$state(false), enviada=$state(false);
 let pasoPendiente=$state('');
 const codigo=$derived(new URLSearchParams(consultaActual).get('publicacion'));
 const tipoLista=$derived(tipoInicial || new URLSearchParams(consultaActual).get('tipo'));
 const listaTipo=$derived(lista.filter(r=>!tipoLista||r.tipo===tipoLista));
 let coleccion=$state('activas');
 const activas=$derived(listaTipo.filter(r=>r.estado==='publicado'));
 const archivadas=$derived(listaTipo.filter(r=>r.estado!=='publicado'));
 const listaVisible=$derived(coleccion==='activas'?activas:archivadas);
 $effect(()=>{const aviso=new URLSearchParams(consultaActual).get('aviso');if(['plazo','cerrado','retirado'].includes(aviso))coleccion='archivadas';});
 const estudiante=$derived(sesion.rol==='estudiante');
 let correo=$state(''), finalizado=$state(false), ahora=$state(Date.now()), desfase=$state(0), exito=$state(false), errorDialogo=$state(false), cierreAvisado=$state(false);
 const participante=$derived(!!publicacion?.participante);
 const segundos=$derived(publicacion?.gracia_hasta?Math.max(0,Math.ceil((Date.parse(publicacion.gracia_hasta)-(ahora+desfase))/1000)):0);
 const enGracia=$derived(publicacion?.recurso.estado==='cerrado'&&segundos>0);
 const relojVisible=$derived(`${String(Math.floor(segundos/60)).padStart(2,'0')}:${String(segundos%60).padStart(2,'0')}`);
 const sinEnviar=$derived(!finalizado&&participante && publicacion?.recurso.tipo==='encuesta' && !enviada && Object.keys(respuestas).length>0);
 let cierreBloqueado=$state(false), salidaAceptada=$state(false), esperaCierre;
 async function volverAlEspacio(){
  if(!await permitirSalida())return;
  salidaAceptada=true;
  try{window.opener?.focus();}catch{}
  try{window.close();}catch{}
  esperaCierre=setTimeout(()=>{salidaAceptada=false;cierreBloqueado=true;},250);
 }
 function continuarEnEstaPestana(){cierreBloqueado=false;navegar(estudiante?'/':'/supervision');}
 function volver(){if(publicacion)navegar(participante?destinoLista(publicacion.recurso.tipo):`/recursos/${publicacion.recurso.tipo==='encuesta'?'encuestas':'diapositivas'}`);else navegar(estudiante?'/':'/supervision');}
 function destinoLista(tipo){return `${estudiante?'/notificaciones':'/recursos/docentes'}/${tipo==='encuesta'?'encuestas':'diapositivas'}`;}
 function actualizarReloj(p){desfase=Date.parse(p.servidor_en)-Date.now();ahora=Date.now();}
 async function permitirSalida() {
  if(ocupado)return false;
  return !sinEnviar || await confirmarAccion({tipo:'eliminar',titulo:'Hay respuestas sin enviar',descripcion:'Si sales de esta encuesta, se perderán las respuestas que todavía no has enviado.',confirmar:'Salir sin enviar',cancelar:'Seguir respondiendo'});
 }
 let secuencia=0, consultandoLista=false;
 async function cargar(id, silencioso=false) {
  if(silencioso&&(cargando||consultandoLista))return;
  const turno=++secuencia;consultandoLista=true;
  if(!silencioso){cargando=true;error='';pasoPendiente='';publicacion=null;respuestas={};enviada=false;finalizado=false;cierreAvisado=false;}
  try {
   if(id){const p=['estudiante','docente'].includes(sesion.rol)?await api.visitar(id):await api.abrir(id);if(turno===secuencia){publicacion=p;actualizarReloj(p);respuestas=p.respuesta??p.respuesta_anterior?.respuestas??{};enviada=!!p.respuesta;if(p.participante)globalThis.dispatchEvent(new Event('recursos-actualizados'));}}
   else if(['estudiante','docente'].includes(sesion.rol)){const l=await api.bandeja();if(turno===secuencia){lista=l;error='';}}
  }catch(e){if(turno===secuencia){error=api.mensaje(e);pasoPendiente=e.estado===403&&e.cuerpo?.estado ? destinoDe(e.cuerpo.estado) : '';}}finally{if(turno===secuencia){cargando=false;consultandoLista=false;}}
 }
 $effect(()=>{cargar(codigo);});
 async function actualizarEstado(){
  if(!codigo||!publicacion||!participante||finalizado||ocupado)return;
  const turno=secuencia;
  try{const p=await api.actividad(codigo);if(turno!==secuencia)return;publicacion={...p,recurso:{...publicacion.recurso,...p.recurso}};actualizarReloj(p);if(p.respuesta&&!enviada){respuestas=p.respuesta;enviada=true;}if(p.recurso.estado==='cerrado'&&!cierreAvisado){cierreAvisado=true;if(!enGracia&&!enviada)terminar('cerrado');}}
  catch(e){if(turno===secuencia){error=api.mensaje(e);if(e.estado===404||e.estado===403)terminar('retirado');}}
 }
 function terminar(motivo){
  if(finalizado)return;finalizado=true;confirmaciones.responder(false);document.querySelectorAll('dialog[open]').forEach(d=>d.close());
  navegar(destinoLista(publicacion.recurso.tipo)+`?aviso=${motivo}`);
 }
 $effect(()=>{if(codigo&&participante&&cierreAvisado&&publicacion?.recurso.estado==='cerrado'&&publicacion.gracia_hasta&&segundos===0&&!finalizado&&!enviada)terminar('plazo');});
 onMount(()=>{
  apiSesion.consultar().then(d=>correo=d.correo??'').catch(()=>{});
  const liberar=protegerSalida(permitirSalida);
  const reabrir=async()=>{if(codigo&&await permitirSalida())cargar(codigo);};
  globalThis.addEventListener('reabrir-recurso',reabrir);
  const reloj=setInterval(()=>{if(codigo)actualizarEstado();else if(document.visibilityState==='visible')cargar(null,true);},10000);
  const contador=setInterval(()=>{ahora=Date.now();},1000);
  const alVolver=()=>{if(document.visibilityState==='visible')actualizarEstado();};document.addEventListener('visibilitychange',alVolver);
  return()=>{secuencia++;clearInterval(reloj);clearInterval(contador);liberar();globalThis.removeEventListener('reabrir-recurso',reabrir);document.removeEventListener('visibilitychange',alVolver);};
 });
 let salidaExito;
 async function enviar(r) {ocupado=true;error='';try{await api.responder(codigo,r);enviada=true;finalizado=true;exito=true;globalThis.dispatchEvent(new Event('recursos-actualizados'));salidaExito=setTimeout(()=>{exito=false;navegar(destinoLista('encuesta')+'?aviso=enviada');},1800);}catch(e){error=api.mensaje(e);errorDialogo=true;await actualizarEstado();}finally{ocupado=false;}}
 onMount(()=>()=>{clearTimeout(salidaExito);clearTimeout(esperaCierre);});
</script>
<svelte:window onbeforeunload={(e)=>{if(sinEnviar&&!salidaAceptada){e.preventDefault();e.returnValue='';}}} />
<section class="recursos-pantalla recursos-publicados" class:visor-amplio={publicacion?.recurso.tipo==='diapositivas'}>
 <header class="encabezado-publicado">
  <div class="identidad-publicada"><span class="emblema-recurso"><Icono nombre={publicacion?.recurso.tipo || tipoLista || 'notificaciones'} medida={24} /></span><div><h1>{publicacion?.recurso.titulo ?? (tipoLista==='encuesta'?'Encuestas del curso':tipoLista==='diapositivas'?'Diapositivas del curso':'Notificaciones y recursos')}</h1>
  {#if publicacion}<p class="metadatos-publicados">{publicacion.nombre_clase} · Envío {publicacion.envio} · {publicacion.recurso.estado==='publicado'?'Activo':'Cerrado'} · {new Date(publicacion.publicada_en).toLocaleString()}</p>{:else}<p class="metadatos-publicados">Recursos de tus cursos</p>{/if}</div></div>
  <nav class="navegacion-publicada" aria-label="Navegación del recurso">
   {#if publicacion}<Accion icono="volver" onclick={volver}>Volver a recursos</Accion>{/if}
   <Accion icono="conversacion" onclick={volverAlEspacio}>{estudiante?'Volver a mi charla':'Volver a mi espacio'}</Accion>
  </nav>
 </header>
 {#if error}<p class="aviso error" role="alert">{error}</p>
  {#if pasoPendiente}<Accion icono="escudo" onclick={()=>navegar(pasoPendiente)}>{pasoPendiente==='/mis-datos'?'Revisar mi solicitud':'Continuar mi autorización'}</Accion>
  {:else}<Accion icono="reiniciar" onclick={()=>cargar(codigo)}>Reintentar</Accion>{/if}
 {/if}
 {#if cargando}<CargadorCubo mensaje="Cargando recursos…" />
 {:else if pasoPendiente}<p class="aviso">Completa el paso pendiente para consultar las encuestas y diapositivas de tu curso. Tus datos ya registrados se conservan.</p>
 {:else if publicacion}
  {#if enGracia&&!enviada}<div class="aviso plazo-recurso" role="status"><Icono nombre="reloj" /><div><strong>La publicación se cerró. Tienes tiempo adicional.</strong><p>{publicacion.recurso.tipo==='encuesta'?'Puedes terminar y enviar tus respuestas antes de que finalice el contador.':'El material se cerrará automáticamente al terminar el contador.'}</p></div><output aria-label="Tiempo adicional restante">{relojVisible}</output></div>{/if}
  {#if publicacion.recurso.tipo==='encuesta'}
   {#if enviada}<p class="aviso" role="status">Tu respuesta quedó registrada. Puedes revisar todas las páginas de tu encuesta.</p>
   {:else if publicacion.recurso.estado!=='publicado'&&!enGracia}<p class="aviso">Esta encuesta está cerrada.</p>{/if}
   {#key codigo}<FormularioEncuesta recurso={publicacion.recurso} bind:respuestas {ocupado} {correo} contexto={publicacion.contexto} corroborar={!!publicacion.respuesta_anterior&&!enviada} soloLectura={enviada||!participante||(publicacion.recurso.estado!=='publicado'&&!enGracia)} alEnviar={enviar} />{/key}
  {:else}{#key codigo}<VisorDiapositivas contenido={publicacion.recurso.contenido} titulo={publicacion.recurso.titulo} />{/key}{/if}
 {:else}
  {#if new URLSearchParams(consultaActual).get('aviso')==='enviada'}<p class="aviso respuesta-guardada" role="status"><Icono nombre="check" />Tu respuesta quedó registrada. Puedes revisar todas las páginas de tu encuesta desde su tarjeta.</p>
  {:else if ['plazo','cerrado','retirado'].includes(new URLSearchParams(consultaActual).get('aviso'))}<p class="aviso" role="status">{new URLSearchParams(consultaActual).get('aviso')==='plazo'?'Terminó el tiempo adicional. La publicación se cerró y las respuestas sin enviar no se registraron.':new URLSearchParams(consultaActual).get('aviso')==='retirado'?'El recurso fue retirado y ya no está disponible. Los cambios sin enviar no se registraron. Las respuestas enviadas anteriormente se conservan.':'La publicación se cerró o ya no está disponible. Las respuestas que enviaste se conservan.'}</p>{/if}
  <p class="descripcion-lista">{tipoLista==='encuesta'?'Participa en las encuestas activas y revisa tus respuestas de publicaciones anteriores.':tipoLista==='diapositivas'?'Consulta el material activo de tus cursos y el historial de publicaciones cerradas.':'Consulta tus recursos activos y las publicaciones anteriores.'}</p>
  <PestanasSegmentadas etiqueta="Estado de los recursos" prefijo="recursos-publicados" activa={coleccion} alElegir={c=>coleccion=c} opciones={[{id:'activas',icono:'reloj',titulo:`Activas (${activas.length})`},{id:'archivadas',icono:'archivar',titulo:`Archivadas (${archivadas.length})`}]} />
  {#if !listaVisible.length}<p class="aviso">{coleccion==='activas'?'No tienes publicaciones activas en este momento.':'Todavía no tienes publicaciones cerradas en este apartado.'}</p>{/if}
  <div id={`recursos-publicados-panel-${coleccion}`} role="tabpanel" aria-labelledby={`recursos-publicados-pestana-${coleccion}`} class="tarjetas tarjetas-publicadas">{#each listaVisible as r (r.id)}<article class="tarjeta tarjeta-publicada" class:respondida={r.respondida}><div class="cabecera-tarjeta"><span class="icono-material"><Icono nombre={r.tipo} medida={28} /></span><span class="estado" class:en-vivo={r.estado==='publicado'}>{#if r.estado==='publicado'}<i class="punto-vivo" aria-hidden="true"></i>En vivo{:else}<Icono nombre="archivar" medida={15} />Archivada{/if}</span></div><h2>{r.titulo}</h2><p class="curso-material">{r.clase}</p><p class="descripcion-material">{r.descripcion}</p>
   <p class="muted">Envío {r.envio} · {new Date(r.publicada_en).toLocaleString()}</p>
   <div class="retroalimentacion-material"><Icono nombre={r.respondida?'check':r.estado==='cerrado'?'candado':'reloj'} /><p>{r.tipo==='encuesta'?(r.respondida?'Ya contestaste esta encuesta. Tu respuesta está guardada y puedes revisarla.':r.estado==='cerrado'?'Encuesta cerrada. El plazo de respuesta terminó.':'Tu respuesta está pendiente. Abre la encuesta para participar.'):(r.estado==='cerrado'?'Publicación finalizada. Se conserva el registro de este material.':r.vista?'Ya abriste este material. Puedes volver a consultarlo.':'Nuevo material para tu curso.')}</p></div>
   <Accion icono={r.respondida?'visible':r.tipo} class={`primario accion-material ${r.estado==='publicado'&&!r.respondida&&(r.tipo==='encuesta'||!r.vista)?'accion-pendiente':''}`} disabled={r.estado!=='publicado'&&!r.respondida} onclick={()=>navegar(`${estudiante?'/notificaciones':'/recursos/publicacion'}?publicacion=${encodeURIComponent(r.id)}`)}>{r.estado!=='publicado'&&!r.respondida?'Publicación cerrada':r.tipo==='encuesta'?(r.respondida?'Revisar mi respuesta':'Abrir encuesta'):'Ver diapositivas'}</Accion>
  </article>{/each}</div>
 {/if}
</section>
{#if ocupado}<div class="carga-operacion"><CargadorCubo mensaje="Enviando tu respuesta…" /></div>{/if}
<Dialogo bind:abierto={cierreBloqueado} titulo={estudiante?'Volver a tu charla':'Volver a tu espacio'} tipo="comunicar">
 <p>El navegador no permitió cerrar esta pestaña automáticamente.</p>
 <p>{estudiante?'Tu charla sigue disponible en la pestaña desde la que abriste este recurso. Puedes cerrar esta pestaña con los controles del navegador o continuar aquí.':'Puedes cerrar esta pestaña con los controles del navegador o volver a tu espacio aquí.'}</p>
 {#snippet acciones()}<Accion onclick={()=>cierreBloqueado=false}>Seguir en el recurso</Accion><Accion icono="conversacion" onclick={continuarEnEstaPestana}>{estudiante?'Abrir mi charla aquí':'Abrir mi espacio aquí'}</Accion>{/snippet}
</Dialogo>
<Dialogo bind:abierto={exito} titulo="Respuesta enviada" tipo="confirmar"><div class="exito-encuesta"><span><Icono nombre="check" medida={42} /></span><h3>¡Tu respuesta quedó guardada!</h3><p>Volverás a tus encuestas para revisar la respuesta cuando quieras.</p></div></Dialogo>
<Dialogo bind:abierto={errorDialogo} titulo="No se pudo enviar la encuesta" tipo="comunicar"><p>{error}</p><p>Tus respuestas siguen en esta pantalla mientras el plazo de publicación lo permita. Revisa el mensaje y vuelve a intentarlo.</p></Dialogo>
<style>
 .recursos-publicados{padding:20px 24px}.visor-amplio{width:100%;max-width:1800px;padding:16px 24px}.encabezado-publicado{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:20px;padding-bottom:14px;border-bottom:1px solid var(--trazo-suave)}.identidad-publicada{display:flex;gap:12px;align-items:center;min-width:0}.identidad-publicada>div{min-width:0}.identidad-publicada .emblema-recurso{width:44px;height:44px;flex-shrink:0}.identidad-publicada h1{font-size:clamp(1.25rem,2vw,1.85rem);margin:0;line-height:1.3;overflow-wrap:anywhere}.metadatos-publicados{font-size:.78rem;color:var(--ink-secondary);margin:5px 0 0}.navegacion-publicada{display:flex;align-items:center;gap:6px;flex-shrink:0}.navegacion-publicada :global(button){font-size:.8rem;min-height:40px;padding:8px 10px}.descripcion-lista{font-size:.9rem;margin:0 0 20px;color:var(--ink-secondary)}.estado{display:inline-flex;gap:7px;align-items:center;font-size:.78rem}.en-vivo{color:var(--semantic-success)}.punto-vivo{width:7px;height:7px;border-radius:50%;background:currentColor;animation:latido 2.4s ease-in-out infinite}@keyframes latido{0%,100%{box-shadow:0 0 0 0 color-mix(in srgb,currentColor 30%,transparent)}50%{box-shadow:0 0 0 5px transparent}}:global(.accion-pendiente){animation:invitacion 4s ease-in-out infinite}@keyframes invitacion{0%,75%,100%{transform:translateY(0)}85%{transform:translateY(-2px)}92%{transform:translateY(0)}}.tarjetas-publicadas{align-items:stretch}.tarjeta-publicada{display:flex;flex-direction:column;gap:8px;margin:0!important;background:var(--surface-paper)!important;box-shadow:var(--shadow-soft);overflow:hidden}.tarjeta-publicada h2{font-size:1.15rem;margin:12px 0 0;line-height:1.4}.curso-material{font-size:.8rem;color:var(--accent-main);margin:0}.descripcion-material{font-size:.87rem;color:var(--ink-secondary);line-height:1.5;flex:1}.icono-material{display:grid;place-items:center;background:var(--accent-surface);border-radius:12px;width:48px;height:48px;flex-shrink:0}.retroalimentacion-material{display:flex;gap:10px;align-items:flex-start;padding:12px;background:var(--surface-panel);border-radius:10px;font-size:.8rem;line-height:1.5}.retroalimentacion-material p{margin:0}.respondida .retroalimentacion-material{background:var(--encuesta-completa-bg);color:var(--semantic-success)}:global(.accion-material){width:100%;margin-top:6px}.plazo-recurso{background:var(--encuesta-pendiente-bg);border-color:var(--encuesta-pendiente)!important;position:sticky;top:0;z-index:4;flex-wrap:wrap}.plazo-recurso div{flex:1;min-width:180px}.plazo-recurso p{margin:4px 0;font-size:.8rem}.plazo-recurso output{font-size:1.75rem;font-weight:750;font-variant-numeric:tabular-nums;color:var(--encuesta-pendiente-ink)}.exito-encuesta{text-align:center}.exito-encuesta>span{display:grid;place-items:center;margin:12px auto;width:76px;height:76px;border-radius:50%;background:var(--encuesta-completa-bg);color:var(--semantic-success);animation:confirmada .5s ease-out}.exito-encuesta p{color:var(--ink-secondary)}@keyframes confirmada{from{transform:scale(.65);opacity:0}to{transform:scale(1);opacity:1}}@media(prefers-reduced-motion:reduce){.exito-encuesta>span,.punto-vivo{animation:none}:global(.accion-pendiente){animation:none}}@media(max-width:760px){.recursos-publicados{padding:16px}.encabezado-publicado{flex-wrap:wrap;gap:12px}.identidad-publicada{width:100%}.navegacion-publicada{margin-left:auto}.navegacion-publicada :global(button){font-size:.75rem}.tarjetas-publicadas{grid-template-columns:1fr!important}}
</style>
