<script>
 import Icono from '../base/Icono.svelte';
 import { menuDesplegable } from '../base/menuDesplegable.js';
 import Accion from './AccionRecurso.svelte';
 import { navegar } from '../../enrutado/navegar.js';
 let { datos, cursos, matriculados, vieron, clase=$bindable(''), actualizado,
  actualizando, descarga, envio=$bindable(''), alActualizar, alDescargar, alCurso, alEnvio }=$props();
 let buscar=$state(''), estado=$state('todos');
 const pendientes=$derived(Math.max(0,matriculados-vieron));
 const porcentaje=$derived(matriculados?Math.round(vieron/matriculados*100):0);
 const aperturas=$derived(cursos.reduce((n,c)=>n+(c.aperturas??0),0));
 const historicas=$derived(cursos.reduce((n,c)=>n+(c.aperturas_historicas??0),0));
 const envioActual=$derived(datos.envios?.find(e=>e.numero===datos.envio_actual));
 const filas=$derived(cursos.flatMap(c=>c.integrantes.map(i=>({...i,curso:c.nombre,clase:c.id}))));
 const visibles=$derived(filas.filter(i=>(estado==='todos'||(estado==='abiertas'?i.vista:!i.vista))&&i.nombre.toLocaleLowerCase().includes(buscar.trim().toLocaleLowerCase())));
 const indicadores=$derived([
  {icono:'grupo',valor:matriculados,titulo:datos.audiencia==='docentes'?'Docentes destinatarios':'Matrículas actuales',detalle:'En los destinos seleccionados'},
  {icono:'visible',valor:vieron,titulo:'Abrieron la presentación',detalle:'Destinatarios con apertura registrada'},
  {icono:'reloj',valor:pendientes,titulo:'Pendientes de abrir',detalle:'Aún sin una apertura registrada'},
  {icono:'historial',valor:aperturas,titulo:'Aperturas del envío',detalle:`Incluye reaperturas · ${cursos.length} destinos`}
 ]);
</script>

<div class="dashboard-presentacion">
 <header class="cabecera-metricas">
  <div><span class="rotulo-metricas"><Icono nombre="analitica" />Métricas de la presentación</span><h2>Alcance y participación</h2><p>Revisa quién abrió el material y qué cursos tienen participación pendiente.</p></div>
  <div class="estado-actualizacion"><span class="punto-actualizacion"></span><div><strong>{actualizando?'Actualizando…':'Seguimiento activo'}</strong><small>{actualizado?`Actualizado a las ${actualizado}`:'Cargando métricas…'} · cada 10 s</small></div></div>
 </header>
 <div class="controles-metricas">
  {#if datos.envios?.length}<label>Envío de la presentación<select use:menuDesplegable aria-label="Envío de la presentación" bind:value={envio} onchange={alEnvio}>{#each datos.envios as e}<option value={String(e.numero)}>Envío {e.numero} · {new Date(e.publicada_en).toLocaleString()}</option>{/each}</select></label>{/if}
  <label>{datos.audiencia==='docentes'?'Docente':'Curso'}<select use:menuDesplegable aria-label={datos.audiencia==='docentes'?'Docente':'Curso'} bind:value={clase} onchange={alCurso}><option value="">Todos los destinatarios publicados</option>{#each datos.cursos as c}<option value={c.id}>{c.nombre}</option>{/each}</select></label>
  <span class="estado">{datos.estado}</span>
  <div class="acciones-metricas"><Accion icono="reiniciar" onclick={alActualizar} disabled={actualizando}>Actualizar ahora</Accion><Accion icono="descargar" class="primario" onclick={alDescargar} disabled={descarga}>{descarga?'Preparando informe…':'Descargar informe PDF'}</Accion></div>
 </div>
 {#if envioActual}<p class="contexto-envio"><Icono nombre="publicar" />Envío {envioActual.numero} · {new Date(envioActual.publicada_en).toLocaleString()} · aperturas y pendientes propios de esta publicación</p>{/if}
 {#if !datos.cursos.length}
  <div class="sin-publicaciones"><Icono nombre="publicar" medida={32} /><h3>Esta presentación aún no tiene publicaciones</h3><p>Publícala en tus cursos desde la biblioteca para empezar a registrar las aperturas.</p></div>
 {:else}
  <div class="indicadores-metricas">{#each indicadores as indicador}<article class="indicador-metricas"><span class="icono-indicador"><Icono nombre={indicador.icono} medida={22} /></span><div><p>{indicador.titulo}</p><strong>{indicador.valor}</strong><small>{indicador.detalle}</small></div></article>{/each}</div>
  <div class="graficas-participacion">
   <section class="tarjeta-metricas resumen-aperturas" aria-labelledby="titulo-aperturas">
    <div class="titulo-tarjeta"><Icono nombre="visible" /><h3 id="titulo-aperturas">Aperturas del material</h3></div>
    <div class="contenido-aperturas"><div class="anillo-aperturas" style:background={`conic-gradient(var(--recurso-jade) ${porcentaje}%,var(--trazo-suave) 0)`} role="img" aria-label={`${vieron} matrículas con apertura y ${pendientes} pendientes, de ${matriculados} matrículas`}><div><strong>{porcentaje} %</strong><span>con apertura</span></div></div>
     <div class="leyenda-aperturas"><p><span class="punto abierta"></span>Abrieron<strong>{vieron}</strong></p><p><span class="punto pendiente"></span>Pendientes<strong>{pendientes}</strong></p><small>{matriculados?'Participación según la matrícula actual.':'Los cursos seleccionados aún no tienen matrícula.'}</small></div></div>
    <p class="nota-metricas"><Icono nombre="evidencias" />Una apertura indica acceso al material; no acredita su lectura completa.</p>
   </section>
   <section class="tarjeta-metricas comparacion-cursos" aria-labelledby="titulo-cursos">
    <div class="titulo-tarjeta"><Icono nombre="clases" /><h3 id="titulo-cursos">Participación por curso</h3><small>{cursos.length} {cursos.length===1?'curso':'cursos'}</small></div>
    <div class="lista-participacion">{#each cursos as curso}<article class="participacion-curso">
     <div class="nombre-curso"><strong>{curso.nombre}</strong><span>{curso.matriculados?`${Math.round(curso.vieron/curso.matriculados*100)} %`:'Sin matrícula'}</span></div>
     <progress value={curso.vieron} max={curso.matriculados||1} aria-label={`Aperturas en ${curso.nombre}: ${curso.vieron} de ${curso.matriculados}`}></progress>
     <div class="detalle-curso"><span>{curso.vieron} de {curso.matriculados} abrieron · {Math.max(0,curso.matriculados-curso.vieron)} pendientes · {curso.aperturas} aperturas</span><Accion icono="diapositivas" onclick={()=>navegar(`/recursos/publicacion?publicacion=${encodeURIComponent(curso.publicacion)}`)}>Abrir recurso de este curso</Accion></div>
    </article>{/each}</div>
   </section>
  </div>
  <section class="tarjeta-metricas detalle-estudiantes" aria-labelledby="titulo-estudiantes">
   <div class="cabecera-estudiantes"><div><div class="titulo-tarjeta"><Icono nombre={datos.audiencia==='docentes'?'docente':'estudiante'} /><h3 id="titulo-estudiantes">Seguimiento de {datos.audiencia==='docentes'?'docentes':'estudiantes'}</h3></div><p>{visibles.length} de {filas.length} destinatarios · una fila por persona y destino</p></div>
    <div class="filtros-estudiantes"><label><span class="solo-lector">Buscar participante</span><input type="search" aria-label={datos.audiencia==='docentes'?'Buscar docente':'Buscar estudiante'} bind:value={buscar} placeholder="Buscar participante…" /></label><label><span class="solo-lector">Estado de apertura</span><select use:menuDesplegable aria-label="Estado de apertura" bind:value={estado}><option value="todos">Todos los destinatarios</option><option value="abiertas">Con apertura</option><option value="pendientes">Pendientes de abrir</option></select></label></div>
   </div>
   <div class="tabla-participacion"><table><thead><tr><th>{datos.audiencia==='docentes'?'Docente':'Estudiante'}</th><th>Curso</th><th>Estado de apertura</th><th>Aperturas</th><th>Última apertura</th></tr></thead><tbody>{#each visibles as i (`${i.clase}:${i.id}`)}<tr><td><span class="nombre-estudiante"><span class="avatar-estudiante" aria-hidden="true">{i.nombre.trim().slice(0,1).toLocaleUpperCase()}</span>{i.nombre}</span></td><td>{i.curso}</td><td><span class="estado-apertura" class:abierta={i.vista}><Icono nombre={i.vista?'check':'reloj'} medida={15} />{i.vista?'Abiertas':'Pendiente'}</span></td><td>{i.aperturas}</td><td>{i.ultima_en?new Date(i.ultima_en).toLocaleString():'—'}</td></tr>{/each}</tbody></table>
    {#if !visibles.length}<p class="sin-resultados">{filas.length?'No hay estudiantes que coincidan con estos filtros.':'No hay estudiantes matriculados en los cursos seleccionados.'}</p>{/if}
   </div>
  </section>
  <p class="aclaracion-matricula">Los totales suman matrículas por curso. Un estudiante inscrito en varios cursos puede aparecer en más de una fila.</p>
  <p class="aclaracion-matricula">{historicas} aperturas históricas en los cursos del filtro, incluidas matrículas retiradas. {cursos.some(c=>!c.conteo_completo)?'Los registros antiguos conservan al menos una apertura por estudiante.':''}</p>
 {/if}
</div>

<style>
 .dashboard-presentacion { padding:20px; background:var(--surface-canvas); min-height:100%; box-sizing:border-box; }
 .cabecera-metricas { display:flex; align-items:center; justify-content:space-between; gap:24px; margin-bottom:14px; }
 .rotulo-metricas { display:flex; gap:7px; align-items:center; font-size:.74rem; color:var(--accent-main); }
 .cabecera-metricas h2 { margin:6px 0; font-size:1.4rem; }
 .cabecera-metricas p { margin:0; color:var(--ink-secondary); font-size:.82rem; }
 .estado-actualizacion { display:flex; align-items:center; gap:10px; flex-shrink:0; }
 .estado-actualizacion strong,.estado-actualizacion small { display:block; font-size:.75rem; }
 .estado-actualizacion small { color:var(--ink-secondary); margin-top:4px; font-size:.68rem; }
 .punto-actualizacion,.punto { width:9px; height:9px; border-radius:50%; display:inline-block; flex-shrink:0; }
 .punto-actualizacion { background:var(--semantic-success); }
 .controles-metricas { display:flex; gap:16px; align-items:center; margin-bottom:16px; }
 .contexto-envio { display:flex; align-items:center; gap:8px; font-size:.72rem; color:var(--ink-secondary); margin:0 0 16px; }
 .contexto-envio :global(svg) { flex-shrink:0; }
 .controles-metricas label { display:grid; gap:5px; margin:0; font-size:.72rem; color:var(--ink-secondary); width:clamp(190px,20vw,300px); }
 .controles-metricas select { background:var(--surface-paper); color:var(--ink-primary); }
 .acciones-metricas { display:flex; gap:8px; margin-left:auto; }
 .acciones-metricas :global(button) { font-size:.78rem; }
 .indicadores-metricas { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:16px; }
 .indicador-metricas,.tarjeta-metricas { border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); background:var(--surface-paper); }
 .indicador-metricas { display:flex; gap:12px; padding:16px; align-items:flex-start; }
 .icono-indicador { display:grid; place-items:center; width:40px; height:40px; border-radius:var(--radius-sm); background:var(--accent-surface); color:var(--accent-main); flex-shrink:0; }
 .indicador-metricas p { margin:0; font-size:.76rem; color:var(--ink-secondary); }
 .indicador-metricas strong { display:block; font-size:1.9rem; line-height:1.2; margin:6px 0; font-variant-numeric:tabular-nums; }
 .indicador-metricas small { font-size:.65rem; color:var(--ink-secondary); }
 .graficas-participacion { display:grid; grid-template-columns:minmax(340px,.85fr) minmax(0,1.4fr); gap:18px; margin-bottom:16px; }
 .tarjeta-metricas { padding:16px; min-width:0; }
 .titulo-tarjeta { display:flex; gap:8px; align-items:center; }
 .titulo-tarjeta :global(svg) { color:var(--accent-main); }
 .titulo-tarjeta h3 { margin:0; font-size:.95rem; }
 .titulo-tarjeta>small { margin-left:auto; color:var(--ink-secondary); font-size:.72rem; }
 .contenido-aperturas { display:flex; align-items:center; gap:24px; justify-content:center; padding:16px 0; }
 .anillo-aperturas { width:128px; height:128px; border-radius:50%; padding:14px; box-sizing:border-box; flex-shrink:0; }
 .anillo-aperturas>div { display:flex; align-items:center; justify-content:center; flex-direction:column; height:100%; border-radius:50%; background:var(--surface-paper); }
 .anillo-aperturas strong { font-size:1.65rem; }
 .anillo-aperturas span { font-size:.67rem; color:var(--ink-secondary); }
 .leyenda-aperturas { flex:1; max-width:200px; font-size:.78rem; }
 .leyenda-aperturas p { display:flex; align-items:center; gap:8px; margin:12px 0; }
 .leyenda-aperturas strong { margin-left:auto; }
 .leyenda-aperturas small { display:block; color:var(--ink-secondary); font-size:.68rem; line-height:1.6; }
 .punto.abierta { background:var(--recurso-jade); } .punto.pendiente { background:var(--trazo-suave); }
 .nota-metricas { display:flex; align-items:flex-start; gap:8px; font-size:.7rem; color:var(--ink-secondary); margin:0; border-top:1px solid var(--trazo-suave); padding-top:12px; }
 .nota-metricas :global(svg) { flex-shrink:0; }
 .lista-participacion { max-height:270px; overflow:auto; }
 .participacion-curso { padding:16px 0; border-bottom:1px solid var(--trazo-suave); }
 .participacion-curso:last-child { border-bottom:0; }
 .nombre-curso,.detalle-curso { display:flex; align-items:center; gap:12px; justify-content:space-between; font-size:.8rem; }
 .nombre-curso span { font-weight:600; color:var(--accent-main); }
 progress { display:block; width:100%; height:9px; border:0; border-radius:6px; overflow:hidden; margin:12px 0; background:var(--trazo-suave); accent-color:var(--recurso-jade); }
 progress::-webkit-progress-bar { background:var(--trazo-suave); } progress::-webkit-progress-value { background:var(--recurso-jade); } progress::-moz-progress-bar { background:var(--recurso-jade); }
 .detalle-curso { font-size:.7rem; color:var(--ink-secondary); }
 .detalle-curso :global(button) { min-height:30px; font-size:.69rem; padding:4px 8px; background:transparent; }
 .detalle-estudiantes { padding:0; overflow:hidden; }
 .cabecera-estudiantes { display:flex; gap:20px; align-items:center; justify-content:space-between; padding:18px 20px; border-bottom:1px solid var(--trazo-suave); }
 .cabecera-estudiantes p { margin:5px 0 0; font-size:.72rem; color:var(--ink-secondary); }
 .filtros-estudiantes { display:flex; gap:10px; }
 .filtros-estudiantes label { margin:0; width:210px; }
 .filtros-estudiantes input,.filtros-estudiantes select { font-size:.76rem; }
 .tabla-participacion { max-height:420px; overflow:auto; }
 table { font-size:.78rem; }
 th { position:sticky; top:0; z-index:1; font-size:.72rem; font-weight:500; color:var(--ink-secondary); background:var(--surface-panel); }
 td,th { padding:12px 20px; }
 .nombre-estudiante { display:flex; gap:10px; align-items:center; font-weight:500; }
 .avatar-estudiante { display:grid; place-items:center; width:30px; height:30px; border-radius:50%; background:var(--accent-surface); color:var(--accent-main); font-size:.72rem; flex-shrink:0; }
 .estado-apertura { display:inline-flex; align-items:center; gap:6px; color:var(--ink-secondary); background:var(--surface-panel); border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); padding:4px 8px; font-size:.72rem; }
 .estado-apertura.abierta { color:var(--semantic-success); background:var(--semantic-success-bg); }
 .aclaracion-matricula { color:var(--ink-secondary); font-size:.7rem; margin:12px 0 0; }
 .sin-publicaciones { display:grid; justify-items:center; text-align:center; padding:70px 20px; border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); background:var(--surface-paper); }
 .sin-publicaciones h3 { margin:16px 0 4px; } .sin-publicaciones p { color:var(--ink-secondary); font-size:.85rem; }
 .sin-resultados { padding:30px; text-align:center; color:var(--ink-secondary); }
 .solo-lector { position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); }
 @media(max-width:1200px) { .indicadores-metricas { grid-template-columns:repeat(2,minmax(0,1fr)); } .graficas-participacion { grid-template-columns:minmax(310px,.9fr) minmax(0,1.2fr); } .contenido-aperturas { gap:14px; } .detalle-curso { flex-wrap:wrap; } .filtros-estudiantes label { width:180px; } }
 @media(max-width:900px) { .cabecera-metricas,.cabecera-estudiantes { flex-wrap:wrap; } .graficas-participacion { grid-template-columns:1fr; } .controles-metricas { flex-wrap:wrap; } .acciones-metricas { margin-left:0; } }
 @media(max-width:550px) { .dashboard-presentacion { padding:14px; } .indicadores-metricas { gap:8px; } .indicador-metricas { padding:12px; gap:8px; } .icono-indicador { display:none; } .filtros-estudiantes { flex-wrap:wrap; width:100%; } .filtros-estudiantes label { width:100%; } .tabla-participacion { overflow:auto; } table { min-width:450px; } }
</style>
