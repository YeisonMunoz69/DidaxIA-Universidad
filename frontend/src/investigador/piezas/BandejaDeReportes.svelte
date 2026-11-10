
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { onMount, tick } from 'svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import Boton from '../../comun/base/Boton.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import * as api from '../../nucleo/api/reportes.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  const ESTADOS = { nuevo:'Pendiente', en_revision:'En revisión', resuelto:'Resuelto', descartado:'Descartado' };
  const CATEGORIAS = { funcional:'Funcional', visual:'Visual', rendimiento:'Rendimiento', accesibilidad:'Accesibilidad', contenido:'Contenido', otro:'Otro' };
  const RESPUESTAS = [
    { id:'corregida', nombre:'Corrección verificada', texto:'Verificamos la corrección en la versión desplegada. Revisa si el comportamiento se resolvió y avísanos si continúa.' },
    { id:'datos', nombre:'Solicitar más detalles', texto:'Para continuar necesitamos conocer el dispositivo, el navegador y los pasos para repetir el problema. Puedes compartir esos detalles sin incluir información personal ajena.' },
    { id:'no-reproducible', nombre:'No reproducible', texto:'Con los pasos disponibles no pudimos reproducir el problema. Comparte qué observaste y los pasos exactos para que podamos revisarlo nuevamente.' }
  ];
  let reportes = $state([]), filtro = $state(''), buscando = $state(''), abierto = $state(null);
  let borradores = $state({}), cargando = $state(true), guardando = $state(0);
  let fallo = $state(''), ahora = $state(Date.now());
  let capturaUrl = $state(''), capturaDe = $state(0), ampliada = $state(false), cargandoCaptura = $state(false);
  let respuestaRapida = $state('');
  let controladorCaptura;
  const plazo = (r) => new Date(r.creado_en).getTime() + 15 * 86400000;
  const cerrado = (r) => ['resuelto','descartado'].includes(r.estado);
  const dias = (r) => Math.ceil((plazo(r) - ahora) / 86400000);
  const alerta = (r) => !cerrado(r) && Number.isFinite(plazo(r)) && dias(r) <= 2;
  function etiquetaPlazo(r) {
    if(cerrado(r)) return 'Cerrado';
    if(!Number.isFinite(plazo(r))) return 'Sin fecha';
    const n = dias(r);
    return plazo(r) < ahora ? `Vencido · ${Math.ceil((ahora-plazo(r))/86400000)} d` : n === 0 ? 'Vence hoy' : `${n} d restantes`;
  }
  let filtros = $derived([
    { id:'', nombre:'Todos', cantidad:reportes.length },
    { id:'nuevo', nombre:'Pendientes', cantidad:reportes.filter((r) => r.estado === 'nuevo').length },
    { id:'en_revision', nombre:'En revisión', cantidad:reportes.filter((r) => r.estado === 'en_revision').length },
    { id:'sla', nombre:'Alerta SLA', cantidad:reportes.filter(alerta).length },
    { id:'resuelto', nombre:'Resueltos', cantidad:reportes.filter((r) => r.estado === 'resuelto').length },
    { id:'descartado', nombre:'Descartados', cantidad:reportes.filter((r) => r.estado === 'descartado').length }
  ]);
  let visibles = $derived(reportes.filter((r) => {
    const texto = `${r.id} ${r.titulo} ${r.reportante?.nombre ?? ''} ${r.reportante?.correo ?? ''} ${r.ruta}`.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    const termino = buscando.replace(/^#/,'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    return (!filtro || (filtro === 'sla' ? alerta(r) : r.estado === filtro)) && texto.includes(termino);
  }));
  $effect(() => { if(abierto !== null && !visibles.some((r) => r.id === abierto)) abierto = null; });
  function detalleDe(e) { return e?.cuerpo?.detalle || describir(e).explicacion; }
  async function cargar() {
    cargando = true; fallo = '';
    try { reportes = (await api.institucionales()).reportes ?? []; }
    catch(e) { fallo = detalleDe(e); }
    finally { cargando = false; }
  }
  function abrir(r) {
    abierto = abierto === r.id ? null : r.id;
    if(abierto && !borradores[r.id]) borradores[r.id] = { estado:r.estado, respuesta:r.respuesta ?? '' };
    respuestaRapida = '';
  }
  async function navegar(r, paso) {
    const siguiente = visibles[visibles.findIndex((v) => v.id === r.id) + paso];
    if(!siguiente) return;
    abrir(siguiente); await tick();
    document.getElementById(`abrir-reporte-${siguiente.id}`)?.focus();
  }
  function limpiarCaptura() {
    controladorCaptura?.abort();
    if(capturaUrl) URL.revokeObjectURL(capturaUrl);
    capturaUrl = ''; capturaDe = 0; ampliada = false;
  }
  async function verCaptura(id) {
    limpiarCaptura(); cargandoCaptura = true; fallo = '';
    const control = new AbortController(); controladorCaptura = control;
    try {
      const archivo = await api.captura(id, { señal: control.signal });
      if(control.signal.aborted) return;
      capturaUrl = URL.createObjectURL(archivo); capturaDe = id;
    } catch(e) { if(!control.signal.aborted) fallo = detalleDe(e); }
    finally { if(!control.signal.aborted) cargandoCaptura = false; }
  }
  async function copiarPasos(r) {
    try { await navigator.clipboard.writeText(r.pasos); toast.exito(`Pasos del reporte #${r.id} copiados.`); }
    catch { fallo = 'No se pudo copiar. Selecciona el texto de los pasos y cópialo manualmente.'; }
  }
  async function guardar(r) {
    const borrador = { ...borradores[r.id] };
    if (borrador.estado === 'descartado' && r.estado !== 'descartado' && !await confirmarAccion({ tipo:'eliminar', titulo:`¿Descartar el reporte #${r.id}?`, descripcion:'Se archivará sin respuesta pública nueva. Su historial auditable se conservará.', confirmar:'Descartar' })) return;
    guardando = r.id; fallo = '';
    try {
      const respuesta = await api.actualizar(r.id, borrador);
      reportes = reportes.map((item) => item.id === r.id ? { ...item, ...respuesta.reporte, reportante:item.reportante } : item);
      borradores[r.id] = { estado:respuesta.reporte.estado, respuesta:respuesta.reporte.respuesta ?? '' };
      toast.exito(`Reporte #${r.id} actualizado.`);
    } catch(e) { fallo = detalleDe(e); }
    finally { guardando = 0; }
  }
  onMount(() => { cargar(); const reloj = setInterval(() => ahora = Date.now(), 60000); return () => { clearInterval(reloj); limpiarCaptura(); }; });
</script>

<section class="bandeja" aria-labelledby="titulo-bandeja">
  <header><div class="titulo"><Icono nombre="supervision" medida={22} /><h2 id="titulo-bandeja">Reportes recibidos</h2><BotonAyudaTooltip ariaLabel="Ayuda de la bandeja de incidencias" texto="Hasta cien incidencias recientes, sólo para soporte. Los contadores y la búsqueda se aplican a esta lista cargada. El plazo de atención es de 15 días calendario; Alerta SLA destaca casos abiertos con dos días o menos. Estos contadores no son KPI educativos." /></div><button type="button" class="actualizar" onclick={cargar} disabled={cargando || guardando !== 0}>Actualizar</button></header>
  <div class="barra-filtros" role="group" aria-label="Filtrar incidencias por estado">{#each filtros as f (f.id)}<button type="button" class:activo={filtro === f.id} class:alerta={f.id === 'sla' && f.cantidad > 0} aria-pressed={filtro === f.id} onclick={() => filtro = f.id}>{f.nombre}<span>{f.cantidad}</span></button>{/each}</div>
  <label class="buscar"><Icono nombre="buscar" medida={18} /><input type="search" aria-label="Buscar incidencias" bind:value={buscando} placeholder="ID, título, persona o ruta" /></label>
  {#if fallo}<p class="fallo" role="alert">{fallo}</p>{/if}
  {#if cargando}<CargadorCubo mensaje="Consultando los reportes…" />{/if}
  {#if !cargando && !visibles.length}<p class="vacio">No hay reportes que coincidan con esta búsqueda.</p>{/if}
  <div class="lista">
    {#each visibles as r (r.id)}
      <article class:abierto={abierto === r.id}>
        <button id={`abrir-reporte-${r.id}`} class="fila" type="button" aria-expanded={abierto === r.id} aria-controls={`detalle-reporte-${r.id}`} onclick={() => abrir(r)}>
          <span class="id">#{r.id}</span><span class={`categoria ${r.categoria}`}>{CATEGORIAS[r.categoria] || 'Otro'}</span><span class="ruta">{r.ruta}</span><strong class="titulo-reporte">{r.titulo}</strong><span class={`estado ${r.estado}`}>{ESTADOS[r.estado] || r.estado}</span><span class="plazo" class:urgente={alerta(r)}>{etiquetaPlazo(r)}</span><span class="flecha" aria-hidden="true">{abierto === r.id ? '⌃' : '⌄'}</span>
        </button>
        {#if abierto === r.id && borradores[r.id]}
          <div class="detalle" id={`detalle-reporte-${r.id}`}>
            <div class="emisor"><span class="avatar" aria-hidden="true">{r.reportante?.nombre?.[0] ?? '?'}</span><div><strong>{r.reportante?.nombre || 'Cuenta no disponible'}</strong><span>{r.reportante?.correo || 'Correo no disponible'} · {r.rol}</span><small>{new Date(r.creado_en).toLocaleString('es-CO',{timeZone:'America/Bogota'})} · Límite {new Date(plazo(r)).toLocaleDateString('es-CO',{timeZone:'America/Bogota'})}</small></div></div>
            <div class="problema"><h3>Descripción</h3><p>{r.descripcion}</p></div>
            {#if r.pasos}<div class="pasos"><div><h3>Pasos para reproducir</h3><button type="button" onclick={() => copiarPasos(r)}>Copiar pasos</button></div><pre>{r.pasos}</pre></div>{/if}
            {#if r.tiene_captura}<div class="captura"><button type="button" onclick={() => verCaptura(r.id)} disabled={cargandoCaptura}>Ver captura privada</button>{#if capturaDe === r.id && capturaUrl}<img src={capturaUrl} alt={`Captura adjunta al reporte ${r.id}`} /><button type="button" onclick={() => ampliada = true}>Ver ampliada</button>{/if}</div>{/if}
            <form class="resolver" onsubmit={(e) => { e.preventDefault(); guardar(r); }}>
              <div class="seguimiento"><label>Estado<select use:menuDesplegable={borradores[r.id].estado} bind:value={borradores[r.id].estado} disabled={guardando !== 0}>{#each Object.entries(ESTADOS) as [valor,nombre]}<option value={valor}>{nombre}</option>{/each}</select></label>
                <label>Respuesta rápida<select use:menuDesplegable={respuestaRapida} bind:value={respuestaRapida} disabled={guardando !== 0} onchange={() => { const opcion = RESPUESTAS.find((p) => p.id === respuestaRapida); if(opcion) borradores[r.id].respuesta = opcion.texto; }}><option value="">Elegir borrador…</option>{#each RESPUESTAS as p (p.id)}<option value={p.id}>{p.nombre}</option>{/each}</select></label>
              </div>
              <label>Respuesta visible para quien reportó<textarea bind:value={borradores[r.id].respuesta} maxlength="2000" rows="3" disabled={guardando !== 0} placeholder="Qué se revisó y cómo continuar."></textarea></label>
              <div class="acciones"><div class="navegar"><button type="button" onclick={() => navegar(r,-1)} disabled={guardando !== 0 || visibles[0]?.id === r.id}>← Anterior</button><button type="button" onclick={() => navegar(r,1)} disabled={guardando !== 0 || visibles.at(-1)?.id === r.id}>Siguiente →</button></div><Boton tipo="submit" deshabilitado={guardando !== 0}>{guardando === r.id ? 'Guardando…' : 'Guardar seguimiento'}</Boton></div>
            </form>
          </div>
        {/if}
      </article>
    {/each}
  </div>
</section>
{#if ampliada && capturaUrl}<Dialogo bind:abierto={ampliada} titulo={`Captura privada · reporte #${capturaDe}`} ancho="65rem"><img class="captura-ampliada" src={capturaUrl} alt={`Captura ampliada del reporte ${capturaDe}`} />{#snippet acciones()}<Boton variante="secundario" onclick={() => ampliada = false}>Cerrar captura</Boton>{/snippet}</Dialogo>{/if}

<style>
  .bandeja { display:grid; gap:.9rem; padding:1rem; min-inline-size:0; border:1px solid var(--trazo-suave); border-radius:var(--radius-lg); background:var(--surface-paper); box-shadow:var(--shadow-soft); }
  header,.titulo { display:flex; gap:.5rem; align-items:center; } header { justify-content:space-between; flex-wrap:wrap; } .titulo { color:var(--accent-main); } h2,h3,p { margin:0; } h2 { color:var(--ink-primary); font-size:var(--texto-md); } h3 { font-size:var(--texto-sm); }
  button { min-block-size:2.5rem; padding:.45rem .65rem; border:1px solid var(--trazo); border-radius:var(--radius-sm); background:var(--surface-paper); color:var(--ink-primary); cursor:pointer; font:inherit; font-size:var(--texto-sm); } button:focus-visible { outline:2px solid var(--accent-main); outline-offset:2px; } button:disabled { opacity:.5; cursor:default; }
  .barra-filtros { display:flex; gap:.4rem; overflow:auto; padding-block:.25rem; } .barra-filtros button { flex:none; display:flex; gap:.5rem; align-items:center; border-radius:var(--radius-pill); border-color:var(--trazo-suave); color:var(--ink-secondary); } .barra-filtros span { display:grid; place-items:center; min-inline-size:1.5rem; padding:.1rem .3rem; background:var(--surface-panel); border-radius:var(--radius-pill); font-size:var(--texto-xs); }
  .barra-filtros .activo { background:var(--accent-surface); border-color:var(--accent-main); color:var(--accent-main); } .barra-filtros .alerta span { background:var(--semantic-danger-bg); color:var(--semantic-danger); animation:aviso-sla 2s ease-in-out 2; }
  .buscar { display:flex; align-items:center; gap:.5rem; padding:.1rem .65rem; border:1px solid var(--trazo); border-radius:var(--radius-sm); background:var(--surface-panel); color:var(--ink-tertiary); } .buscar input { border:0; background:transparent; }
  input,select,textarea { inline-size:100%; min-inline-size:0; padding:.6rem; border:1px solid var(--trazo); border-radius:var(--radius-sm); background:var(--surface-panel); color:var(--ink-primary); font:inherit; } textarea { resize:vertical; }
  .lista { display:grid; gap:.5rem; } article { min-inline-size:0; border:1px solid var(--trazo-suave); border-radius:var(--radius-md); overflow:hidden; } article.abierto { border-color:var(--accent-main); }
  .fila { display:grid; grid-template-columns:3rem 6.5rem minmax(3rem,7rem) minmax(0,1fr) 6rem 7.5rem 1rem; gap:.55rem; align-items:center; inline-size:100%; text-align:start; border:0; border-radius:0; padding:.9rem .75rem; }
  .fila:hover { background:var(--surface-panel); } .fila[aria-expanded=true] { background:var(--accent-surface); } .id,.ruta { color:var(--ink-tertiary); font-size:var(--texto-xs); } .ruta,.titulo-reporte { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; } .titulo-reporte { font-size:var(--texto-sm); }
  .categoria,.estado { padding:.25rem .4rem; justify-self:start; font-size:var(--texto-xs); border-radius:var(--radius-pill); background:var(--surface-panel); color:var(--ink-secondary); white-space:nowrap; }
  .funcional { background:var(--color-rose-bg); color:var(--color-rose); } .visual { background:var(--color-sky-bg); color:var(--color-sky); } .rendimiento { background:var(--color-violet-bg); color:var(--color-violet); } .accesibilidad { background:var(--color-emerald-bg); color:var(--color-emerald); } .contenido { background:var(--semantic-warning-bg); color:var(--semantic-warning); }
  .nuevo { background:var(--semantic-warning-bg); color:var(--semantic-warning); } .en_revision { background:var(--semantic-info-bg); color:var(--semantic-info); } .resuelto { background:var(--semantic-success-bg); color:var(--semantic-success); } .plazo { font-size:var(--texto-xs); color:var(--ink-secondary); } .urgente { color:var(--semantic-danger); font-weight:700; }
  .detalle { display:grid; gap:1rem; padding:1rem; border-block-start:1px solid var(--trazo-suave); background:var(--surface-paper); } .emisor { display:flex; gap:.7rem; align-items:center; } .avatar { display:grid; place-items:center; inline-size:2.8rem; block-size:2.8rem; flex:none; border-radius:var(--radius-pill); background:var(--accent-surface); color:var(--accent-main); }
  .emisor>div { display:grid; gap:.2rem; min-inline-size:0; } .emisor span,.emisor small { font-size:var(--texto-xs); color:var(--ink-secondary); overflow-wrap:anywhere; } .emisor strong { font-size:var(--texto-sm); overflow-wrap:anywhere; }
  .problema { display:grid; gap:.5rem; } .problema p { white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.6; font-size:var(--texto-sm); color:var(--ink-secondary); }
  .pasos { padding:.85rem; background:var(--surface-panel); border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); min-inline-size:0; } .pasos>div { display:flex; gap:.6rem; justify-content:space-between; align-items:center; } pre { white-space:pre-wrap; overflow-wrap:anywhere; font:var(--texto-sm)/1.6 var(--fuente-mono); color:var(--ink-primary); margin:.6rem 0 0; }
  .captura { display:flex; flex-wrap:wrap; gap:.6rem; align-items:center; } .captura img { max-inline-size:12rem; max-block-size:8rem; object-fit:contain; } .captura-ampliada { display:block; max-inline-size:100%; max-block-size:70dvh; margin-inline:auto; object-fit:contain; }
  .resolver { display:grid; gap:.7rem; padding-block-start:.8rem; border-block-start:1px solid var(--trazo-suave); } label { display:grid; gap:.3rem; color:var(--ink-secondary); font-size:var(--texto-sm); min-inline-size:0; } .seguimiento { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; } .acciones { display:flex; flex-wrap:wrap; justify-content:space-between; gap:.7rem; align-items:center; } .navegar { display:flex; gap:.4rem; }
  .fallo { padding:.65rem; border-radius:var(--radius-sm); overflow-wrap:anywhere; font-size:var(--texto-sm); background:var(--semantic-danger-bg); color:var(--semantic-danger); } .vacio { padding:1rem; color:var(--ink-tertiary); }
  @keyframes aviso-sla { 50% { transform:scale(1.08); } }
  @media(max-width:60rem) { .fila { grid-template-columns:3rem auto minmax(0,1fr) 1rem; } .ruta { display:none; } .titulo-reporte { grid-row:2; grid-column:1/4; } .estado { grid-column:3; justify-self:end; } .plazo { grid-row:3; grid-column:1/4; } .flecha { grid-column:4; grid-row:1/4; } }
  @media(max-width:36rem) { .bandeja,.detalle { padding:.75rem; } .seguimiento { grid-template-columns:minmax(0,1fr); } .acciones { align-items:stretch; flex-direction:column; } .navegar button { flex:1; } }
  @media(prefers-reduced-motion:reduce) { .barra-filtros .alerta span { animation:none; } }
</style>
