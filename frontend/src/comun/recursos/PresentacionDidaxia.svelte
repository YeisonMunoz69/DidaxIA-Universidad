<script>
  import { onMount } from 'svelte';
  import { confirmarAccion, confirmaciones } from '../estado/confirmaciones.svelte.js';
  import { toast } from '../estado/toasts.svelte.js';
  import Dialogo from '../base/Dialogo.svelte';
  import CargadorCubo from '../base/CargadorCubo.svelte';
  import { menuDesplegable } from '../base/menuDesplegable.js';
  import { descargarBlob } from '../../nucleo/descargas/archivo.js';
  let { contenido, pantallaCompleta=false, alCerrarPresentacion=()=>{}, editable = false, espacioTrabajo=false, titulo = 'Presentación DidaxIa', onchange = () => {}, alControles = () => {} } = $props();
  let marco;
  let listo = $state(false), alto = $state(740), error = $state('');
  let indice = $state(0);
  let errorAccion = $state(''), errorVisible = $state(false), confirmando = false;
  const canal = crypto.randomUUID();
  let enviado = '';
  let preparado=false;
  function ejecutar(accion) {
    if (listo && editable) marco.contentWindow.postMessage({type:'didaxia:command',channel:canal,action:accion},location.origin);
  }

  function ir() { marco.contentWindow.postMessage({type:'didaxia:go',channel:canal,index:indice}, location.origin); }

  function cargar() {
    if (!marco?.contentWindow) return;
    enviado = JSON.stringify(contenido);
    const copia = JSON.parse(enviado);
    marco.contentWindow.postMessage({ type:'didaxia:load', channel:canal, content:copia, readonly:!editable, fullscreen:!!pantallaCompleta, externalToolbar:espacioTrabajo&&innerWidth>=900 }, location.origin);
  }
  $effect(() => {
    const actual = JSON.stringify(contenido);
    if (listo && actual !== enviado) cargar();
  });
  onMount(() => {
    let activo = true;
    function redimensionar() { marco?.contentWindow?.postMessage({type:'didaxia:toolbar',channel:canal,externalToolbar:espacioTrabajo&&innerWidth>=900},location.origin); }
    async function recibir(evento) {
      if (evento.source !== marco?.contentWindow || evento.origin !== location.origin) return;
      const mensaje = evento.data;
      if (mensaje?.type === 'didaxia:ready') { if(!preparado){preparado=true;cargar();} return; }
      if (mensaje?.channel !== canal) return;
      if (mensaje.type === 'didaxia:exit' && pantallaCompleta) {alCerrarPresentacion();return;}
      if (mensaje.type === 'didaxia:controls' && editable && espacioTrabajo) alControles({...mensaje,ejecutar});
      if (mensaje.type === 'didaxia:loaded') { listo = true; error = ''; }
      if (mensaje.type === 'didaxia:slide' && Number.isInteger(mensaje.index)) indice = Math.max(0,Math.min(contenido.slides.length-1,mensaje.index));
      if (mensaje.type === 'didaxia:height' && Number.isFinite(mensaje.height)) alto = Math.max(400, Math.min(15000, mensaje.height + 2));
      if (mensaje.type === 'didaxia:error') error = mensaje.message;
      if (mensaje.type === 'didaxia:download' && mensaje.blob instanceof Blob && ['application/pdf','application/json','text/html'].includes(mensaje.blob.type)) {
        const nombre = String(mensaje.name || 'presentacion.pdf').replace(/[\\/]/g,'-').slice(0,150);
        try { const descarga=descargarBlob(mensaje.blob,nombre);await descarga.finalizada;if(activo)toast.descarga(`Archivo ${nombre} preparado. Revisa las descargas del navegador.`); }
        catch(e){if(activo){errorAccion=`No se pudo descargar el archivo: ${e.message}`;errorVisible=true;}}
      }
      if (mensaje.type === 'didaxia:confirm-request' && typeof mensaje.requestId === 'string') {
        const acciones = {
          pdf: {tipo:'descarga',titulo:'¿Exportar esta presentación?',descripcion:`${contenido.slides.length} diapositivas · ${titulo}. Se descargará un PDF con texto seleccionable y enlaces, usando el estilo actual.`,confirmar:'Exportar PDF',cancelar:'Cancelar'},
          eliminar: {tipo:'eliminar',titulo:'¿Eliminar esta diapositiva?',descripcion:'Puedes recuperar la diapositiva con Deshacer mientras continúes en el editor.',confirmar:'Eliminar diapositiva',cancelar:'Conservar diapositiva'},
          restaurar: {tipo:'eliminar',titulo:'¿Restaurar el contenido inicial?',descripcion:'Se reemplazarán los cambios del editor por la versión inicial. Guarda una copia para conservarlos.',confirmar:'Restaurar contenido',cancelar:'Seguir editando'}
        };
        const accion = acciones[mensaje.action];
        if (!accion || (!editable && mensaje.action !== 'pdf') || confirmando) {
          marco.contentWindow.postMessage({type:'didaxia:confirm-decision',channel:canal,requestId:mensaje.requestId,accepted:false},location.origin); return;
        }
        confirmando = true;
        const aceptada = await confirmarAccion(accion);
        confirmando = false;
        if (activo) marco.contentWindow.postMessage({type:'didaxia:confirm-decision',channel:canal,requestId:mensaje.requestId,accepted:aceptada},location.origin);
      }
      if (mensaje.type === 'didaxia:feedback' && typeof mensaje.message === 'string') {
        const texto = mensaje.message.slice(0,700);
        if (mensaje.kind === 'error') {errorAccion = texto;errorVisible=true;}
        else if (mensaje.kind === 'download') toast.descarga(texto);
        else toast.exito(texto);
      }
      if (mensaje.type === 'didaxia:change' && editable && Array.isArray(mensaje.content?.slides)) {
        enviado = JSON.stringify(mensaje.content);
        onchange(mensaje.content);
      }
    }
    window.addEventListener('message', recibir);
    window.addEventListener('resize', redimensionar);
    return () => { activo=false; alControles(null); if(confirmando)confirmaciones.responder(false); window.removeEventListener('message', recibir); window.removeEventListener('resize',redimensionar); };
  });
</script>

<div class="presentacion-integrada" class:espacio-trabajo={espacioTrabajo} class:pantalla-completa={pantallaCompleta} style:--alto-movil={`${alto}px`}>
{#if !listo&&!error}<div class="carga-presentacion"><CargadorCubo mensaje={editable?'Cargando el editor…':'Cargando las diapositivas…'} /></div>{/if}
{#if error}<p role="alert">No se pudo abrir la presentación: {error}</p>{/if}
<iframe bind:this={marco} title={`${editable ? 'Editor' : 'Visor'} de diapositivas · ${titulo}`}
  src={`/presentaciones/editor-integrado.html?integrado=1&version=figuras-20261007${espacioTrabajo?'&escritorio=1&barra=externa':''}`}
  style:height={pantallaCompleta?'100%':espacioTrabajo?undefined:`${alto}px`} allow="fullscreen" allowfullscreen
  sandbox="allow-scripts allow-same-origin allow-downloads allow-modals allow-forms allow-popups allow-popups-to-escape-sandbox"></iframe>
{#if editable&&!espacioTrabajo}<label>Ir a diapositiva<select use:menuDesplegable aria-label="Ir a diapositiva" bind:value={indice} onchange={ir}>
  {#each contenido.slides as diapositiva,n}<option value={n}>{n+1}. {diapositiva.title}</option>{/each}
</select></label>
{/if}
</div>
<Dialogo bind:abierto={errorVisible} titulo="No se pudo completar la acción" tipo="comunicar"><p>{errorAccion}</p><p>Tu presentación sigue disponible. Revisa el mensaje y vuelve a intentarlo.</p></Dialogo>

<style>
  .pantalla-completa{flex:1;height:100%;min-height:0;width:100%}.pantalla-completa iframe{height:100%;border:0;border-radius:0}
  .presentacion-integrada { position:relative; }
  .carga-presentacion { position:absolute;inset:0;z-index:1;display:grid;place-items:center;background:var(--surface-paper);border-radius:var(--radius-sm); }
  iframe { display:block; width:100%; min-width:0; border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); background:var(--surface-paper); }
  .espacio-trabajo { display:flex; flex-direction:column; height:100%; min-height:0; flex:1; }
  .espacio-trabajo iframe { flex:1; min-height:0; height:100%; border-radius:0; border:0; }
  @media(max-width:650px) {
    .espacio-trabajo { height:auto; flex:none; }
    .espacio-trabajo iframe { flex:none; height:var(--alto-movil); }
  }
</style>
