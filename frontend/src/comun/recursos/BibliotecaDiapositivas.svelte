<script>
  import CargadorCubo from '../base/CargadorCubo.svelte';
  import Icono from '../base/Icono.svelte';
  import Accion from './AccionRecurso.svelte';
  import { menuDesplegable } from '../base/menuDesplegable.js';
  let { lista=[], plantillas=[], cargando=false, ocupado=false, investigador=false,
    buscar=$bindable(''), filtro=$bindable('todos'), alCrear, alAbrir,
    alPresentar, alDuplicar, alMetricas, alCambiar, alEliminar, alPlantilla, alPublicar, alGuardarPlantilla, alEnlaces }=$props();
  let coleccion=$state('biblioteca');
  const propios=$derived(lista.filter(r=>r.tipo==='diapositivas'));
  const disponibles=$derived(propios.filter(r=>r.estado!=='archivado'));
  const archivadas=$derived(propios.filter(r=>r.estado==='archivado'));
  const visibles=$derived((coleccion==='archivadas'?archivadas:disponibles).filter(r=>(coleccion==='archivadas'||filtro==='todos'||r.estado===filtro)&&r.titulo.toLowerCase().includes(buscar.toLowerCase())));
  const bases=$derived(plantillas.filter(p=>p.titulo.toLowerCase().includes(buscar.toLowerCase())));
  const estados=[['todos','Todas'],['borrador','Borradores'],['publicado','Publicadas'],['cerrado','Cerradas']];
  function fecha(valor){return new Date(valor).toLocaleDateString('es-CO',{day:'numeric',month:'short',year:'numeric'});}
</script>

<div class="biblioteca-diapositivas">
  <aside class="colecciones-diapositivas" aria-label="Organizar diapositivas">
    <p class="rotulo-panel">Biblioteca</p>
    <button class="seleccion-coleccion" class:activa={coleccion==='biblioteca'} aria-pressed={coleccion==='biblioteca'} onclick={()=>{coleccion='biblioteca';buscar='';filtro='todos';}}><Icono nombre="diapositivas" /><span>Mis presentaciones</span><small>{disponibles.length}</small></button>
    <button class="seleccion-coleccion" class:activa={coleccion==='archivadas'} aria-pressed={coleccion==='archivadas'} onclick={()=>{coleccion='archivadas';buscar='';}}><Icono nombre="archivar" /><span>Archivadas</span><small>{archivadas.length}</small></button>
    {#if investigador}<button class="seleccion-coleccion" class:activa={coleccion==='plantillas'} aria-pressed={coleccion==='plantillas'} onclick={()=>{coleccion='plantillas';buscar='';}}><Icono nombre="duplicar" /><span>Plantillas y materiales</span><small>{plantillas.length}</small></button>{/if}
    <p class="rotulo-panel">Estado de publicación</p>
    {#each estados as [valor,nombre]}<button class="filtro-coleccion" aria-pressed={coleccion==='biblioteca'&&filtro===valor} onclick={()=>{coleccion='biblioteca';filtro=valor;}}><span>{nombre}</span><small>{valor==='todos'?disponibles.length:disponibles.filter(r=>r.estado===valor).length}</small></button>{/each}
    <div class="nota-coleccion"><Icono nombre="guardar" /><p>Los borradores se guardan en tu cuenta. Publica cuando estén listos para tus cursos.</p></div>
  </aside>
  <div class="contenido-coleccion">
    <div class="herramientas-coleccion">
      <div><h2>{coleccion==='biblioteca'?'Mis presentaciones':coleccion==='archivadas'?'Presentaciones archivadas':'Plantillas y materiales'}</h2><p>{coleccion==='biblioteca'?`${visibles.length} ${visibles.length===1?'presentación':'presentaciones'} · ${estados.find(e=>e[0]===filtro)?.[1]??'Todas'}`:coleccion==='archivadas'?`${visibles.length} archivadas · Sus datos y métricas se conservan.`:'Crea una copia editable de la base o de un material del piloto.'}</p></div>
      <label class="buscador-coleccion"><Icono nombre="buscar" /><input type="search" aria-label="Buscar recurso" bind:value={buscar} placeholder={coleccion==='plantillas'?'Buscar plantilla…':'Buscar presentación…'} /></label>
      {#if coleccion==='biblioteca'}<label class="estado-movil">Estado de publicación<select use:menuDesplegable={filtro} bind:value={filtro}>{#each estados as [valor,nombre]}<option value={valor}>{nombre}</option>{/each}</select></label>{/if}
    </div>
    {#if cargando}<CargadorCubo pantallaCompleta mensaje="Cargando presentaciones…" />
    {:else if coleccion!=='plantillas'}
      {#if visibles.length}
        <div class="tabla-biblioteca"><table>
          <thead><tr><th>Presentación</th><th>Estado</th><th>Cursos</th><th>Actualización</th><th><span class="solo-lector">Acciones</span></th></tr></thead>
          <tbody>{#each visibles as r (r.id)}<tr>
            <td class="nombre-presentacion"><Icono nombre="diapositivas" medida={24} /><div><button class="abrir-presentacion" onclick={()=>investigador?alAbrir(r):alMetricas(r)} disabled={ocupado}>{r.titulo||'Borrador sin título'}</button><p>{r.descripcion||'Sin descripción'}</p></div></td>
            <td><span class="estado" class:publicado={r.estado==='publicado'}>{r.estado}</span></td>
            <td class="cursos-presentacion"><span class="rotulo-movil">Destinatarios</span>{r.cursos}</td><td class="fecha-presentacion"><span class="rotulo-movil">Actualizada</span>{fecha(r.actualizado_en)}</td>
            <td><div class="acciones-fila">
              {#if investigador}<Accion icono="diapositivas" disabled={ocupado} onclick={()=>alPresentar(r)}>Presentar</Accion>{/if}{#if investigador&&r.estado==='borrador'}<Accion icono="editar" disabled={ocupado} onclick={()=>alAbrir(r)}>Editar</Accion>{/if}
              {#if investigador&&['borrador','cerrado'].includes(r.estado)}<Accion icono="publicar" class="primario" disabled={ocupado} onclick={()=>alPublicar(r)}>{r.estado==='borrador'?'Publicar':'Volver a publicar'}</Accion>{/if}
              <Accion icono="analitica" disabled={ocupado} onclick={()=>alMetricas(r)}>Métricas</Accion>
              {#if r.envios>0}<Accion icono="copiar" disabled={ocupado} onclick={()=>alEnlaces(r)}>Enlaces</Accion>{/if}
              {#if investigador}<details class="menu-presentacion"><summary aria-label={`Más acciones para ${r.titulo}`}><Icono nombre="mas" /><span class="rotulo-movil">Más acciones</span></summary><div>
                <Accion icono="duplicar" disabled={ocupado} onclick={()=>alDuplicar(r)}>Duplicar</Accion>
                <Accion icono="guardar" disabled={ocupado} onclick={()=>alGuardarPlantilla(r)}>Guardar como plantilla</Accion>
                {#if r.estado==='publicado'}<Accion icono="candado" disabled={ocupado} onclick={()=>alCambiar(r,'cerrado')}>Cerrar publicación</Accion>{/if}
                {#if r.puede_eliminar}<Accion icono="eliminar" disabled={ocupado} onclick={()=>alEliminar(r)}>{r.estado==='borrador'?'Eliminar borrador':'Eliminar presentación'}</Accion>{/if}
                {#if r.estado!=='archivado'}<Accion icono="archivar" disabled={ocupado} onclick={()=>alCambiar(r,'archivado')}>Archivar</Accion>{/if}
                {#if !r.puede_eliminar}<small class="datos-conservados">Tiene participación registrada. Sus datos se conservan al archivar.</small>{/if}
              </div></details>{/if}
            </div></td>
          </tr>{/each}</tbody>
        </table></div>
      {:else}<div class="estado-coleccion"><Icono nombre={coleccion==='archivadas'?'archivar':'diapositivas'} medida={32} /><h3>{coleccion==='archivadas'?'No hay presentaciones archivadas':buscar||filtro!=='todos'?'Sin resultados para este filtro':'Todavía no tienes presentaciones'}</h3><p>{coleccion==='archivadas'?'Las presentaciones que archives aparecerán aquí.':buscar||filtro!=='todos'?'Prueba otra búsqueda o cambia el estado.':'Empieza con la plantilla base, un material existente o tu archivo HTML.'}</p>
        {#if investigador}<div class="acciones"><Accion icono="nueva" class="primario" onclick={alCrear} disabled={ocupado}>Usar plantilla base</Accion><Accion icono="duplicar" onclick={()=>coleccion='plantillas'}>Explorar plantillas</Accion></div>{/if}
      </div>{/if}
    {:else}
      <div class="lista-plantillas">{#each bases as p (p.id)}<article>
        <span class="miniatura-plantilla" aria-hidden="true"><Icono nombre="diapositivas" medida={26} /><span>{p.diapositivas?`${p.diapositivas} diapositivas`:'Plantilla personalizada'}</span></span>
        <div><h3>{p.titulo}</h3><p>{p.id==='base'?'Base editable para preparar una nueva sesión':'Material del piloto · copia independiente'}</p></div>
        <Accion icono="duplicar" onclick={()=>alPlantilla(p)} disabled={ocupado}>Añadir a mi biblioteca</Accion>
      </article>{/each}</div>
      {#if !bases.length}<p class="estado-coleccion">No hay plantillas que coincidan con esta búsqueda.</p>{/if}
    {/if}
  </div>
</div>

<style>
  .biblioteca-diapositivas { display:grid; grid-template-columns:210px minmax(0,1fr); flex:1; min-height:0; border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); overflow:hidden; background:var(--surface-paper); }
  .colecciones-diapositivas { padding:18px 12px; background:var(--surface-panel); border-right:1px solid var(--trazo-suave); overflow:auto; }
  .rotulo-panel { font-size:.7rem; text-transform:uppercase; letter-spacing:.08em; color:var(--ink-secondary); margin:4px 8px 12px; }
  .rotulo-panel:not(:first-child) { margin-top:30px; }
  .colecciones-diapositivas button { width:100%; border:0; background:transparent; padding:9px 10px; font-size:.82rem; justify-content:flex-start; text-align:left; margin-bottom:3px; }
  .colecciones-diapositivas button small { margin-left:auto; font-variant-numeric:tabular-nums; color:var(--ink-secondary); }
  .colecciones-diapositivas button span { flex:1; }
  .colecciones-diapositivas button.activa,.colecciones-diapositivas button[aria-pressed=true] { background:var(--accent-surface); color:var(--accent-main); }
  .nota-coleccion { display:flex; gap:8px; align-items:flex-start; border-top:1px solid var(--trazo-suave); margin:24px 8px 0; padding-top:16px; color:var(--ink-secondary); }
  .nota-coleccion p { margin:0; font-size:.75rem; }
  .contenido-coleccion { min-width:0; min-height:0; overflow:auto; display:flex; flex-direction:column; }
  .herramientas-coleccion { display:flex; justify-content:space-between; gap:20px; padding:20px 24px; border-bottom:1px solid var(--trazo-suave); align-items:center; }
  .herramientas-coleccion h2 { font-size:1rem; margin:0; }
  .herramientas-coleccion p { margin:5px 0 0; font-size:.8rem; color:var(--ink-secondary); }
  .buscador-coleccion { display:flex; align-items:center; width:clamp(200px,28vw,380px); gap:8px; margin:0; }
  .tabla-biblioteca { flex:1; padding:0 24px; overflow:auto; }
  table { font-size:.82rem; }
  th { color:var(--ink-secondary); font-size:.72rem; font-weight:500; white-space:nowrap; }
  td { vertical-align:middle; }
  .nombre-presentacion { display:flex; align-items:center; gap:12px; min-width:200px; padding:18px 6px; }
  .nombre-presentacion :global(svg) { color:var(--accent-main); }
  .nombre-presentacion div { min-width:0; }
  .nombre-presentacion p { margin:4px 0 0; color:var(--ink-secondary); font-size:.75rem; max-width:340px; white-space:nowrap; text-overflow:ellipsis; overflow:hidden; }
  button.abrir-presentacion { border:0; background:transparent; padding:0; min-height:30px; text-align:left; font-size:.9rem; font-weight:600; justify-content:flex-start; }
  .acciones-fila { display:flex; align-items:center; justify-content:flex-end; gap:6px; }
  .acciones-fila :global(button) { font-size:.78rem; padding:6px 9px; white-space:nowrap; }
  .estado { display:inline-block;white-space:nowrap;overflow-wrap:normal;word-break:normal;min-width:max-content; }
  td:nth-child(2) { min-width:7rem; }
  .fecha-presentacion { white-space:nowrap; color:var(--ink-secondary); }
  .menu-presentacion { position:relative; }
  .menu-presentacion summary { min-height:36px; min-width:32px; display:grid; place-items:center; cursor:pointer; border-radius:var(--radius-sm); }
  .menu-presentacion[open] summary { background:var(--accent-surface); }
  .menu-presentacion summary::-webkit-details-marker { display:none; }
  .menu-presentacion>div { position:absolute; right:0; top:100%; z-index:3; display:grid; gap:4px; padding:8px; background:var(--surface-paper); border:1px solid var(--trazo-suave); box-shadow:var(--shadow-float); border-radius:var(--radius-sm); min-width:180px; }
  .menu-presentacion>div :global(button) { justify-content:flex-start; border:0; }
  .datos-conservados { padding:8px; font-size:.72rem; line-height:1.5; color:var(--ink-secondary); }
  .estado-coleccion { display:flex; flex-direction:column; align-items:center; justify-content:center; flex:1; padding:40px 20px; text-align:center; }
  .estado-coleccion h3 { margin:14px 0 4px; }
  .estado-coleccion p { font-size:.85rem; color:var(--ink-secondary); margin:4px 0; }
  .estado-coleccion>.acciones { justify-content:center; }
  .lista-plantillas { padding:8px 24px; flex:1; }
  .lista-plantillas article { display:flex; align-items:center; gap:18px; padding:18px 0; border-bottom:1px solid var(--trazo-suave); }
  .lista-plantillas article>div { flex:1; }
  .lista-plantillas h3 { margin:0; font-size:.92rem; }
  .lista-plantillas p { margin:6px 0 0; color:var(--ink-secondary); font-size:.8rem; }
  .miniatura-plantilla { width:116px; aspect-ratio:16/9; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; color:var(--accent-main); background:var(--accent-surface); border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); flex-shrink:0; }
  .miniatura-plantilla span { font-size:.65rem; }
  .solo-lector { position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); }
  .estado-movil,.rotulo-movil { display:none; }
  @media(max-width:1050px) { .biblioteca-diapositivas { grid-template-columns:180px minmax(0,1fr); } .herramientas-coleccion { padding:16px; } .tabla-biblioteca,.lista-plantillas { padding-inline:16px; } }
  @media(max-width:760px) { .biblioteca-diapositivas { display:flex; flex-direction:column; overflow:auto; } .colecciones-diapositivas { border-right:0; border-bottom:1px solid var(--trazo-suave); } .colecciones-diapositivas .rotulo-panel:not(:first-child),.nota-coleccion,.filtro-coleccion { display:none; } .herramientas-coleccion { flex-wrap:wrap; } .contenido-coleccion { overflow:visible; } .tabla-biblioteca { flex:none; } .lista-plantillas article { flex-wrap:wrap; } }
  @media(max-width:760px) {
    .biblioteca-diapositivas { overflow:visible; flex:none; }
    .colecciones-diapositivas { display:grid; grid-template-columns:1fr 1fr; gap:6px; padding:10px; overflow:visible; }
    .colecciones-diapositivas .rotulo-panel,.colecciones-diapositivas .nota-coleccion,.colecciones-diapositivas .filtro-coleccion { display:none; }
    .colecciones-diapositivas .seleccion-coleccion { font-size:.78rem; margin:0; gap:6px; padding:8px; }
    .seleccion-coleccion:nth-of-type(3) { grid-column:1 / -1; }
    .herramientas-coleccion { gap:12px; padding:16px 12px; align-items:stretch; }
    .herramientas-coleccion>div,.buscador-coleccion,.estado-movil { width:100%; }
    .buscador-coleccion { margin:0; }
    .estado-movil { display:grid; gap:6px; margin:0; font-size:.8rem; color:var(--ink-secondary); }
    .tabla-biblioteca { padding:12px; overflow:visible; }
    table,tbody { display:block; }
    thead { position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); }
    tr { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px; border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); padding:14px 12px; background:var(--surface-panel); }
    td { border:0; padding:0; min-width:0; }
    .nombre-presentacion { grid-column:1 / -1; min-width:0; padding:0; align-items:flex-start; }
    .nombre-presentacion div { flex:1; }
    .nombre-presentacion p { white-space:normal; overflow-wrap:anywhere; }
    button.abrir-presentacion { min-height:44px; overflow-wrap:anywhere; line-height:1.45; }
    td:nth-child(2) { grid-column:1 / -1; }
    .fecha-presentacion { white-space:normal; font-size:.78rem; }
    .cursos-presentacion { font-size:.8rem; }
    .rotulo-movil { display:block; font-size:.72rem; color:var(--ink-secondary); margin-bottom:4px; }
    td:last-child { grid-column:1 / -1; border-top:1px solid var(--trazo-suave); padding-top:12px; }
    .acciones-fila { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    .acciones-fila :global(button) { min-height:44px; white-space:normal; font-size:.78rem; padding:8px; }
    .menu-presentacion { min-width:0; }
    .menu-presentacion summary { min-height:44px; display:flex; align-items:center; justify-content:center; gap:6px; border:1px solid var(--trazo-suave); }
    .menu-presentacion summary .rotulo-movil { margin:0; color:inherit; font-size:.78rem; }
    .menu-presentacion[open] { grid-column:1 / -1; }
    .menu-presentacion>div { position:static; min-width:0; margin-top:8px; box-shadow:none; }
    .lista-plantillas { padding:8px 12px; }
    .lista-plantillas article { display:grid; grid-template-columns:72px minmax(0,1fr); gap:12px; }
    .miniatura-plantilla { width:72px; height:64px; }
    .miniatura-plantilla span { display:none; }
    .lista-plantillas article :global(button) { grid-column:1 / -1; width:100%; }
    .lista-plantillas h3 { overflow-wrap:anywhere; }
  }
</style>
