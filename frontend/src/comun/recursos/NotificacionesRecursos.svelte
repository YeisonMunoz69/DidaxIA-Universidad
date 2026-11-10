<script>
  import { onMount } from 'svelte';
  import Icono from '../base/Icono.svelte';
  import Accion from './AccionRecurso.svelte';
  import { destinoDe } from '../../nucleo/sesion/acceso.js';
  import * as api from '../../nucleo/api/recursos.js';
  let { ir, rol='estudiante' } = $props();
  let lista = $state([]), error = $state(''), abierto = $state(false);
  let pasoPendiente = $state('');
  let panel, control;
  let centro = $state(0), anchoVentana = $state(1024), arriba=$state(70);
  let activo = true, consultando = false;
  const nuevas = $derived(lista.filter(r => r.nueva).length);
  const anchoPanel = $derived(Math.min(520, anchoVentana - 32));
  const izquierda = $derived(Math.max(anchoPanel / 2 + 16, Math.min(centro, anchoVentana - anchoPanel / 2 - 16)));
  function contar(tipo) { return lista.filter(r => r.tipo === tipo && r.nueva).length; }
  function avisos(cantidad) { return cantidad===1?'1 nueva':`${cantidad} nuevas`; }
  async function cargar() {
    if (consultando) return;
    consultando = true;
    try { const l = await api.bandeja(); if (activo) { lista = l; error = ''; pasoPendiente=''; } }
    catch (e) { if (activo) { error = api.mensaje(e); pasoPendiente=e.estado===403&&e.cuerpo?.estado ? destinoDe(e.cuerpo.estado) : ''; } } finally { consultando = false; }
  }
  function situar() { const rect = control.getBoundingClientRect(); centro = rect.left + rect.width / 2; anchoVentana = innerWidth; arriba=(control.closest('header')?.getBoundingClientRect().bottom??rect.bottom)+8; }
  function cerrar() { panel.hidePopover(); control.focus(); }
  function ver(destino) {
    cerrar();
    const camino=rol==='docente'?destino.replace('/notificaciones?','/recursos/publicacion?').replace('/notificaciones/','/recursos/docentes/'):destino;
    window.open(camino,'_blank','noopener,noreferrer');
  }
  onMount(() => {
    cargar(); situar();
    const observador = globalThis.ResizeObserver ? new ResizeObserver(situar) : null; observador?.observe(control.closest('header'));
    const reloj = setInterval(() => { if (document.visibilityState === 'visible') cargar(); }, 15000);
    globalThis.addEventListener('resize', situar);
    globalThis.addEventListener('recursos-actualizados', cargar);
    return () => { activo = false; observador?.disconnect(); clearInterval(reloj); globalThis.removeEventListener('resize', situar); globalThis.removeEventListener('recursos-actualizados', cargar); };
  });
</script>

<button type="button" class="campana-recursos" class:seleccionado={abierto} bind:this={control}
  popovertarget="bandeja-recursos" aria-label={`Notificaciones de recursos${nuevas ? `: ${avisos(nuevas)}` : ''}`}
  aria-expanded={abierto} aria-controls="bandeja-recursos" aria-haspopup="dialog" data-tooltip="Notificaciones" onclick={cargar}>
  <Icono nombre="notificaciones" medida={24} />
  {#if nuevas}<span class="contador">{nuevas>99?'99+':nuevas}</span>{/if}
</button>
<div id="bandeja-recursos" class="bandeja-recursos" style:left={`${izquierda}px`} style:top={`${arriba}px`} style:max-height={`min(650px, calc(100dvh - ${arriba+16}px))`} bind:this={panel} popover="auto" role="dialog" aria-label="Notificaciones y recursos"
  ontoggle={(e) => { abierto = e.newState === 'open'; if(abierto)situar(); }}>
  <div class="cabecera-bandeja"><div><p>RECURSOS DEL CURSO</p><h2>Notificaciones</h2></div>
    <button type="button" class="cerrar-bandeja" aria-label="Cerrar notificaciones" onclick={cerrar}><Icono nombre="cerrar" medida={20} /></button>
  </div>
  <p class="resumen-bandeja">{error ? 'No podemos consultar tus publicaciones todavía.' : nuevas ? (nuevas===1?'Tienes una publicación nueva o actualizada.':`Tienes ${nuevas} publicaciones nuevas o actualizadas.`) : 'Estás al día con tus recursos.'} Los recursos se abren en otra pestaña para conservar tu pantalla actual.</p>
  <div class="secciones-bandeja">
    {#each [{tipo:'encuesta',nombre:'Encuestas',destino:'/notificaciones/encuestas',detalle:'Formularios para responder'}, {tipo:'diapositivas',nombre:'Diapositivas',destino:'/notificaciones/diapositivas',detalle:'Materiales para recorrer'}] as seccion}
      <button type="button" class="seccion-bandeja" disabled={Boolean(pasoPendiente)} onclick={() => ver(seccion.destino)} aria-label={`Ver ${seccion.nombre.toLowerCase()}`}>
        <span class="icono-seccion"><Icono nombre={seccion.tipo} medida={29} /></span>
        <strong>{seccion.nombre}</strong><small>{seccion.detalle}</small>
        <span class="estado-seccion">{contar(seccion.tipo) ? avisos(contar(seccion.tipo)) : 'Ver recursos'}<Icono nombre="flecha-der" medida={17} /></span>
      </button>
    {/each}
  </div>
  {#if error}<div class="aviso-bandeja"><p role="alert">{error}</p>
    {#if pasoPendiente}<Accion icono="escudo" onclick={()=>{cerrar();ir(pasoPendiente);}}>{pasoPendiente==='/mis-datos'?'Revisar mi solicitud':'Continuar mi autorización'}</Accion>
    {:else}<Accion icono="reiniciar" onclick={cargar}>Reintentar</Accion>{/if}
  </div>{/if}
  {#if lista.length}<h3>Últimas publicaciones</h3>
    <div class="lista-bandeja">{#each lista.slice(0,4) as r (r.id)}
      <button type="button" class="recurso-bandeja" onclick={() => ver(`/notificaciones?publicacion=${encodeURIComponent(r.id)}`)}>
        <span class="datos-recurso"><strong>{r.titulo}</strong><span>{r.clase} · {r.tipo==='encuesta'?'Encuesta':'Diapositivas'} · Envío {r.envio}</span><small>{new Date(r.publicada_en).toLocaleDateString()} · {r.nueva?'Nueva o actualizada':r.tipo==='encuesta'?(r.respondida?'Respuesta enviada':r.estado==='cerrado'?'Encuesta cerrada':'Pendiente de responder'):'Ya abiertas'}</small></span>
        {#if r.nueva}<span class="punto-nuevo" aria-label="Nueva publicación"></span>{/if}<Icono nombre="flecha-der" medida={19} />
      </button>
    {/each}</div>
  {:else if !error}<p class="vacio-bandeja">Las publicaciones de tus cursos aparecerán aquí.</p>{/if}
</div>
<style>
  button { font:inherit; color:var(--ink-primary); cursor:pointer; }
  .campana-recursos { display:grid; place-items:center; position:relative; min-width:44px; min-height:44px; padding:.5rem; border:1px solid var(--trazo-suave); background:var(--surface-paper); border-radius:var(--radius-trazado); }
  .campana-recursos:hover,.campana-recursos.seleccionado { background:var(--accent-surface); color:var(--accent-main); }
  .contador { position:absolute; top:-4px; right:-5px; min-width:20px; height:20px; padding:0 .2rem; background:var(--accent-main); color:var(--accent-on-main); border-radius:50%; font-size:.7rem; display:grid; place-items:center; border:2px solid var(--surface-paper); }
  .bandeja-recursos { position:fixed; inset:70px auto auto 50%; transform:translateX(-50%); margin:0; width:min(520px,calc(100vw - 2rem)); max-height:min(650px,calc(100dvh - 90px)); overflow:auto; box-sizing:border-box; padding:1.3rem; border:1px solid var(--trazo); border-radius:var(--radius-lg); box-shadow:var(--shadow-float); color:var(--ink-primary); background:var(--surface-paper); }
  .bandeja-recursos::backdrop { background:transparent; }
  .cabecera-bandeja { display:flex; align-items:center; justify-content:space-between; gap:1rem; }
  .cabecera-bandeja p { margin:0; color:var(--accent-main); letter-spacing:.1em; font-size:.7rem; }
  .cabecera-bandeja h2 { margin:.3rem 0; font-size:1.3rem; }
  .cerrar-bandeja { display:grid; place-items:center; width:44px; height:44px; border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); background:var(--surface-panel); }
  .resumen-bandeja { color:var(--ink-secondary); font-size:.85rem; line-height:1.5; margin:1rem 0; }
  .secciones-bandeja { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.75rem; }
  .seccion-bandeja { display:flex; flex-direction:column; align-items:flex-start; gap:.45rem; padding:1rem; border:1px solid var(--trazo-suave); border-radius:var(--radius-trazado); background:var(--surface-panel); text-align:left; }
  .seccion-bandeja:hover { background:var(--accent-surface); border-color:var(--accent-main); }
  .icono-seccion { color:var(--accent-main); margin-bottom:.3rem; }
  .seccion-bandeja strong { font-size:1rem; }
  .seccion-bandeja small { font-size:.78rem; color:var(--ink-secondary); }
  .estado-seccion { display:flex; align-items:center; justify-content:space-between; gap:.5rem; width:100%; color:var(--accent-main); font-size:.8rem; margin-top:.5rem; }
  h3 { font-size:.95rem; margin:1.5rem 0 .25rem; }
  .recurso-bandeja { display:flex; align-items:center; gap:.8rem; width:100%; padding:1rem .25rem; border:0; border-bottom:1px solid var(--trazo-suave); background:transparent; text-align:left; }
  .recurso-bandeja:hover { background:var(--surface-panel); }
  .datos-recurso { flex:1; min-width:0; display:grid; gap:.3rem; }
  .datos-recurso strong { font-size:.95rem; overflow-wrap:anywhere; }
  .datos-recurso span,.datos-recurso small { color:var(--ink-secondary); font-size:.8rem; }
  .punto-nuevo { width:8px; height:8px; border-radius:50%; background:var(--accent-main); }
  .vacio-bandeja { text-align:center; color:var(--ink-secondary); padding:1rem; }
  .aviso-bandeja { margin-block-start: 1rem; padding: .8rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-panel); }
  .aviso-bandeja p { margin-block: 0 .7rem; }
  .seccion-bandeja:disabled { cursor: not-allowed; opacity: .6; }
  button:focus-visible { outline:2px solid var(--accent-main); outline-offset:2px; }
  @media(max-width:480px) { .bandeja-recursos { padding:1rem; inset-block-start:68px; } .seccion-bandeja { padding:.8rem; } }
  @media(hover:none) { .campana-recursos::after { display:none; } }
</style>
