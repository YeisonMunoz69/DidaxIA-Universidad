<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import PestanasSegmentadas from '../../comun/base/PestanasSegmentadas.svelte';
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import CabeceraDeRuta from '../../docente/piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../../docente/piezas/PantallaDesplazable.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import * as api from '../../nucleo/api/auditoria.js';
  import { descargarPDF } from '../../nucleo/descargas/pdf.js';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import SelectorFecha from '../../comun/base/SelectorFecha.svelte';
  import { fechaBogota } from '../../nucleo/formato/selectorFecha.js';

  let pestaña = $state('bitacora');
  const pestañas = [{id:'bitacora',titulo:'Bitácora',icono:'auditoria-institucional'},{id:'gobernanza',titulo:'Doble aprobación',icono:'candado'},{id:'exportacion',titulo:'Exportar',icono:'descargar'}];
  const CATEGORIAS = [
    '', 'acceso', 'KPI', 'informe', 'soporte', 'matrícula', 'perfil',
    'consentimiento', 'comunicación', 'evidencia', 'invitación', 'rol',
    'supresión', 'rectificación', 'retención'
  ];
  let pagina = $state(1), operacion = $state(''), actor = $state(''), sujeto = $state('');
  let desde = $state(fechaBogota(-7)), hasta = $state(fechaBogota()), categoria = $state(''), dobleAprobacion = $state('');
  let respuesta = $state({ operaciones: [], total: 0, paginas: 0, resumen: {} });
  let cargando = $state(true), fallo = $state(null), exportando = $state(false);
  let errorExportacion = $state('');
  let temporizador, controlConsulta, controlExportacion;
  const cantidadFiltros = $derived(
    [operacion, actor, sujeto, desde, hasta, categoria, dobleAprobacion]
      .filter((valor) => String(valor ?? '').trim()).length
  );
  const hayFiltros = $derived(cantidadFiltros > 0);

  function filtros() { return { operacion, actor, sujeto, desde, hasta, categoria, dobleAprobacion }; }

  async function cargar() {
    controlConsulta?.abort();
    controlConsulta = new AbortController();
    cargando = true; fallo = null;
    try { respuesta = await api.listar({ pagina, ...filtros(), señal: controlConsulta.signal }); }
    catch (error) { if (error?.name !== 'AbortError') fallo = describir(error); }
    finally { if (!controlConsulta.signal.aborted) cargando = false; }
  }

  $effect(() => {
    void pagina; void operacion; void actor; void sujeto; void desde; void hasta; void categoria; void dobleAprobacion;
    clearTimeout(temporizador);
    temporizador = setTimeout(cargar, 250);
    return () => { clearTimeout(temporizador); controlConsulta?.abort(); controlExportacion?.abort(); };
  });

  function cambiarFiltro() { pagina = 1; }
  function limpiar() {
    operacion = ''; actor = ''; sujeto = ''; desde = ''; hasta = ''; categoria = ''; dobleAprobacion = '';
    cambiarFiltro();
  }

  async function exportar() {
    if (!await confirmarAccion({ tipo:'descarga', titulo:'¿Descargar auditoría institucional?',
      descripcion:`El PDF incluirá ${respuesta.total ?? 0} operaciones ${hayFiltros ? 'filtradas' : 'del corte completo'}. Su consulta y exportación quedan auditadas.`, confirmar:'Descargar PDF' })) return;
    controlExportacion?.abort(); controlExportacion = new AbortController();
    exportando = true; errorExportacion = '';
    try {
      const documento = await api.descargarInforme(filtros(), { confirmado:(respuesta.total ?? 0) > 500, señal: controlExportacion.signal });
      const descarga = descargarPDF(documento, `didaxia-auditoria-${desde || 'inicio'}-${hasta || 'corte'}.pdf`);
      toast.descarga(`Descargando auditoría: ${descarga.nombre}`);
    } catch (error) {
      if (error?.name !== 'AbortError') errorExportacion = describir(error)?.explicacion || 'No fue posible descargar el informe.';
    } finally { if (!controlExportacion.signal.aborted) exportando = false; }
  }

  function fecha(valor, local = '') {
    if (local) return `${local} (America/Bogota)`;
    return new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Bogota' }).format(new Date(valor));
  }
  function visible(valor) {
    if (valor == null || valor === '') return 'No aplica';
    return typeof valor === 'object' ? JSON.stringify(valor, null, 2) : String(valor);
  }
  function identidad(persona, respaldo) { return persona?.etiqueta || persona?.nombre || persona?.correo || respaldo || 'No aplica'; }
  function periodoCubierto() {
    const inicio = respuesta.resumen?.desde;
    const fin = respuesta.resumen?.hasta;
    return inicio && fin ? `${fecha(inicio)} – ${fecha(fin)}` : 'Sin operaciones';
  }
</script>

<PantallaDesplazable anchoMaximo="min(86rem, 100%)">
  <CabeceraDeRuta titulo="Auditoría institucional" icono="auditoria-institucional" insignia="Sólo lectura" ayuda="Historial inmutable de accesos y cambios sensibles. La consulta también queda auditada antes de devolver resultados. Los nombres explican el hecho y los identificadores conservan su trazabilidad.">
  </CabeceraDeRuta>

  <section class="resumen" aria-label="Resumen del corte visible">
    <div><strong>{respuesta.resumen?.total ?? respuesta.total ?? 0}</strong><span>operaciones</span></div>
    <div><strong>{respuesta.resumen?.actores ?? '—'}</strong><span>actores</span></div>
    <div><strong>{respuesta.resumen?.sensibles ?? '—'}</strong><span>sensibles</span></div>
    <div><strong>{respuesta.resumen?.doble_aprobacion ?? '—'}</strong><span>con doble aprobación</span></div>
    <div><strong>{periodoCubierto()}</strong><span>periodo cubierto</span></div>
    <div><strong>{cantidadFiltros}</strong><span>filtros activos</span></div>
  </section>

  <div class="navegacion-secciones"><PestanasSegmentadas opciones={pestañas} activa={pestaña} alElegir={(id)=>{pestaña=id;}} etiqueta="Secciones de auditoría" prefijo="auditoria" /></div>

  <details class="panel-filtros" open={pestaña==='bitacora'}><summary>Filtros del corte · {cantidadFiltros} activos</summary>
  <section class="filtros" aria-label="Filtros de auditoría">
    <SelectorFecha etiqueta="Desde" bind:value={desde} maximo={fechaBogota()} limpiable alCambiar={cambiarFiltro} />
    <SelectorFecha etiqueta="Hasta" bind:value={hasta} minimo={desde} maximo={fechaBogota()} limpiable alCambiar={cambiarFiltro} />
    <label><span>Categoría</span><select use:menuDesplegable={categoria} bind:value={categoria} onchange={cambiarFiltro}>{#each CATEGORIAS as opcion}<option value={opcion}>{opcion || 'Todas'}</option>{/each}</select></label>
    <label><span>Operación</span><input bind:value={operacion} oninput={cambiarFiltro} placeholder="informe, rol, rectificación…" /></label>
    <label><span>Actor</span><input bind:value={actor} oninput={cambiarFiltro} placeholder="Nombre, correo o identificador" /></label>
    <label><span>Sujeto afectado</span><input bind:value={sujeto} oninput={cambiarFiltro} placeholder="Nombre, correo o identificador" /></label>
    <label><span>Doble aprobación</span><select use:menuDesplegable={dobleAprobacion} bind:value={dobleAprobacion} onchange={cambiarFiltro}><option value="">Todas</option><option value="con">Con aprobación doble</option><option value="sin">Sin aprobación doble</option></select></label>
    <div class="acciones-filtro"><Boton variante="discreto" onclick={limpiar}>Limpiar filtros</Boton></div>
  </section>

  </details>
  {#if fallo}<Degradacion respuesta={fallo} alReintentar={cargar} />{/if}
  <div id="auditoria-panel-exportacion" role="tabpanel" tabindex="0" aria-labelledby="auditoria-pestana-exportacion" hidden={pestaña!=='exportacion'}>
  <section class="exportacion" aria-labelledby="titulo-exportacion">
    <div><span class="sobrelinea">CORTE REPRODUCIBLE</span><h2 id="titulo-exportacion">Exportar el historial {respuesta.total ? `(${respuesta.total})` : ''}</h2><p>El PDF incluye filtros, fecha de corte, glosario, personas, cambios, aprobaciones y detalle técnico. La descarga también queda auditada.</p></div>
    <Boton deshabilitado={exportando || cargando || !(respuesta.total ?? 0)} onclick={exportar}>{exportando ? 'Preparando…' : hayFiltros ? `Descargar resultados filtrados (${respuesta.total ?? 0})` : `Descargar auditoría completa (${respuesta.total ?? 0})`}</Boton>
  </section>

  {#if errorExportacion}<p class="error" role="alert">{errorExportacion}</p>{/if}
  {#if respuesta.glosario?.length}<details class="glosario"><summary>Glosario de operaciones presentes en el corte</summary><ul>{#each respuesta.glosario as entrada}<li><strong>{entrada.nombre}</strong> <code>{entrada.codigo}</code><br />{entrada.descripcion}</li>{/each}</ul></details>{/if}
  </div>

  <div id="auditoria-panel-gobernanza" role="tabpanel" tabindex="0" aria-labelledby="auditoria-pestana-gobernanza" hidden={pestaña!=='gobernanza'}>
    <h2>Doble aprobación y seguridad <BotonAyudaTooltip texto="Este registro muestra operaciones ya auditadas. Una aprobación requerida y no aportada no demuestra que exista una solicitud pendiente. El resultado y la persona aprobadora explican cada caso." /></h2>
    <p>{respuesta.resumen?.doble_aprobacion ?? '—'} operaciones con doble aprobación en el corte.</p>
    <Boton variante="secundario" onclick={()=>{dobleAprobacion='con';cambiarFiltro();}}>Consultar operaciones con doble aprobación</Boton>
    <p class="nota-seguridad">Las tarjetas de esta pestaña corresponden a la página consultada; el resumen y el PDF abarcan el corte filtrado.</p>
    <ul class="sellos">{#each (respuesta.operaciones ?? []).filter(item=>item.aprobacion?.requerida) as item (item.id)}<li><strong>{item.operacion_detalle?.nombre || item.operacion}</strong><span>{item.aprobacion.aportada ? `Aprobada por ${identidad(item.aprobacion.aprobador,item.aprobada_por)}` : 'Aprobación requerida y no aportada'}</span><small>{fecha(item.momento,item.momento_local)} · {item.resultado || 'Registrado'}</small></li>{:else}<li>Sin operaciones con aprobación requerida en esta página.</li>{/each}</ul>
    <nav class="paginacion" aria-label="Páginas de auditoría"><Boton variante="secundario" deshabilitado={pagina <= 1 || cargando} onclick={() => (pagina -= 1)}>Anterior</Boton><span>Página {pagina} de {Math.max(1, respuesta.paginas ?? 0)}</span><Boton variante="secundario" deshabilitado={pagina >= (respuesta.paginas ?? 0) || cargando} onclick={() => (pagina += 1)}>Siguiente</Boton></nav>
  </div>
  <div id="auditoria-panel-bitacora" role="tabpanel" tabindex="0" aria-labelledby="auditoria-pestana-bitacora" hidden={pestaña!=='bitacora'}>
  {#if cargando && !respuesta.operaciones?.length}<CargadorCubo mensaje="Consultando el historial…" pantallaCompleta />
  {:else}
    <ol class="historial">
      {#each respuesta.operaciones ?? [] as item (item.id)}
        <li><div class="eje" aria-hidden="true"><span></span></div><article>
          <header><div><span class="categoria">{item.operacion_detalle?.categoria || 'otra'}</span><h3>{item.operacion_detalle?.nombre || `Operación no catalogada: ${item.operacion}`}</h3><p>{item.operacion_detalle?.descripcion || 'El código original se conserva para trazabilidad.'}</p></div><span class="secuencia">#{item.secuencia ?? item.id}</span></header>
          <dl class="hechos">
            <div><dt>Quién actuó</dt><dd><strong>{identidad(item.actor_detalle, item.actor)}</strong><small>{item.actor_detalle?.correo || item.actor}</small><small>{(item.actor_detalle?.roles ?? []).join(', ') || 'Rol no disponible'}</small></dd></div>
            <div><dt>Sobre quién</dt><dd><strong>{identidad(item.sujeto_detalle, item.sujeto)}</strong><small>{item.sujeto_detalle?.correo || item.sujeto || 'No aplica'}</small></dd></div>
            <div><dt>Cuándo</dt><dd><time datetime={item.momento}>{fecha(item.momento, item.momento_local)}</time></dd></div>
            <div><dt>Resultado</dt><dd>{item.resultado || 'Registrado'}</dd></div>
            <div class="ancho"><dt>Por qué</dt><dd>{item.motivo || 'No consta'}</dd></div>
          </dl>
          {#if item.diferencias?.length}<section class="cambios" aria-label="Cambios de la operación"><h4>Qué cambió</h4>{#each item.diferencias as cambio}<div><span>{cambio.etiqueta}</span><del>{visible(cambio.antes)}</del><span aria-hidden="true">→</span><ins>{visible(cambio.despues)}</ins></div>{/each}</section>{/if}
          {#if item.aprobacion?.requerida}<p class="aprobacion"><strong>Doble aprobación:</strong> {item.aprobacion.aportada ? `aportada por ${identidad(item.aprobacion.aprobador, item.aprobada_por)}` : 'requerida y no aportada'}.</p>{/if}
          <details><summary>Detalle técnico y código original</summary><p><code>{item.operacion}</code> · identidad de roles: {item.actor_detalle?.naturaleza_roles || 'no disponible'}</p><p>Actor: <code>{item.actor_detalle?.identificador || item.actor || 'No aplica'}</code> · sujeto: <code>{item.sujeto_detalle?.identificador || item.sujeto || 'No aplica'}</code></p><pre>{visible(item.detalle)}</pre></details>
        </article></li>
      {:else}<li class="vacio">No hay operaciones que coincidan con los filtros.</li>{/each}
    </ol>
    <nav class="paginacion" aria-label="Páginas de auditoría"><Boton variante="secundario" deshabilitado={pagina <= 1 || cargando} onclick={() => (pagina -= 1)}>Anterior</Boton><span>Página {pagina} de {Math.max(1, respuesta.paginas ?? 0)}</span><Boton variante="secundario" deshabilitado={pagina >= (respuesta.paginas ?? 0) || cargando} onclick={() => (pagina += 1)}>Siguiente</Boton></nav>
  {/if}


  </div>
</PantallaDesplazable>

<style>
  .navegacion-secciones{min-width:0}.navegacion-secciones :global(.contenedor){margin-block:.25rem}

  .panel-filtros{margin:0;font-size:var(--texto-sm)}.panel-filtros>summary{min-height:44px;display:list-item;line-height:44px;list-style-position:inside;cursor:pointer;color:var(--ink-primary);font-weight:750}.resumen{display:flex!important;flex-wrap:wrap;gap:0!important;border:1px solid var(--trazo-suave);border-radius:var(--radius-md);background:var(--surface-paper);padding:.5rem}.resumen div{flex:1 1 7rem;padding:.5rem!important;border:0!important;border-radius:0!important}.resumen div:nth-child(5){flex-basis:18rem}.resumen strong{font-size:var(--texto-lg)!important;line-height:1.3}.resumen div:nth-child(5) strong{font-size:var(--texto-sm)!important}

  [hidden]{display:none!important}[role=tabpanel]{min-width:0}.sellos{display:grid;gap:.65rem;padding:0;list-style:none}.sellos li{display:grid;gap:.4rem;padding:1rem;border:1px solid var(--trazo-suave);border-radius:var(--radius-md);background:var(--surface-paper)}.sellos span{color:var(--color-emerald)}.sellos small,.nota-seguridad{color:var(--ink-secondary);font-size:var(--texto-xs)}

  .resumen { display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.65rem }.resumen div{display:grid;gap:.1rem;padding:.85rem;border:1px solid var(--trazo-suave);border-radius:var(--radius-md);background:var(--surface-paper)}.resumen strong{color:var(--ink-primary);font-size:var(--texto-xl);overflow-wrap:anywhere}.resumen span,.sobrelinea{color:var(--ink-tertiary);font-size:var(--texto-xs);font-weight:750;text-transform:uppercase;letter-spacing:.04em}
  .filtros{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7rem;padding:.9rem;border:1px solid var(--trazo-suave);border-radius:var(--radius-md);background:var(--surface-paper)}label{display:grid;gap:.3rem;color:var(--ink-tertiary);font-size:var(--texto-xs);font-weight:750}input,select{min-block-size:2.5rem;min-inline-size:0;padding:.45rem .65rem;border:1px solid var(--trazo);border-radius:var(--radius-sm);background:var(--surface-panel);color:var(--ink-primary);font:inherit}.acciones-filtro{display:flex;align-items:end}
  .exportacion{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:1rem;border:1px solid var(--accent-main);border-radius:var(--radius-md);background:var(--accent-surface)}.exportacion h2{margin:.15rem 0;font-size:var(--texto-lg)}.exportacion p{max-inline-size:75ch;margin:0;color:var(--ink-secondary)}
  .error{padding:.75rem .9rem;border-inline-start:3px solid var(--semantic-error);border-radius:var(--radius-sm);background:var(--accent-surface);color:var(--ink-secondary)}.vacio{padding:2rem;color:var(--ink-tertiary);text-align:center}
  .historial{display:grid;gap:0;margin:0;padding:0;list-style:none}.historial>li{display:grid;grid-template-columns:1.4rem minmax(0,1fr);gap:.6rem;max-inline-size:none}.eje{position:relative;display:flex;justify-content:center}.eje::after{content:'';position:absolute;inset-block:1.2rem -1.2rem;inline-size:1px;background:var(--trazo-suave)}.eje span{z-index:1;inline-size:.7rem;block-size:.7rem;margin-block-start:1.2rem;border:2px solid var(--accent-main);border-radius:50%;background:var(--surface-paper)}article{min-inline-size:0;margin-block-end:.7rem;padding:.9rem;border:1px solid var(--trazo-suave);border-radius:var(--radius-md);background:var(--surface-paper);box-shadow:var(--shadow-soft)}
  article header{display:flex;justify-content:space-between;gap:.8rem}article header div{min-inline-size:0}h3{margin:.15rem 0;color:var(--ink-primary);font-size:var(--texto-lg)}header p{margin:0;color:var(--ink-secondary)}.categoria{color:var(--accent-main);font-size:var(--texto-xs);font-weight:800;text-transform:uppercase}.secuencia{color:var(--ink-tertiary);font-size:var(--texto-xs)}
  .hechos{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.55rem;margin:.75rem 0 0}.hechos div{min-inline-size:0;padding:.6rem;border-radius:var(--radius-sm);background:var(--surface-panel)}.hechos .ancho{grid-column:1/-1}dt{color:var(--ink-tertiary);font-size:var(--texto-xs);font-weight:750}dd{display:grid;gap:.1rem;margin:.2rem 0 0;color:var(--ink-secondary);overflow-wrap:anywhere}dd small{color:var(--ink-tertiary)}
  .cambios{margin-block-start:.65rem;padding:.7rem;border:1px solid var(--trazo-suave);border-radius:var(--radius-sm)}.cambios h4{margin:0 0 .4rem}.cambios div{display:grid;grid-template-columns:minmax(7rem,1fr) minmax(0,1fr) auto minmax(0,1fr);gap:.5rem;padding:.3rem 0}.cambios del,.cambios ins{overflow-wrap:anywhere;text-decoration:none}.cambios del{color:var(--color-rose);background:var(--color-rose-bg)}.cambios ins{color:var(--color-emerald);background:var(--color-emerald-bg);font-weight:700}.aprobacion{padding:.55rem;background:var(--surface-panel)}details{margin-block-start:.6rem;color:var(--ink-tertiary);font-size:var(--texto-xs)}details pre{max-inline-size:100%;margin-block-start:.4rem;padding:.55rem;overflow:auto;white-space:pre-wrap;background:var(--surface-panel);font:inherit}.paginacion{display:flex;justify-content:center;align-items:center;gap:.8rem;color:var(--ink-secondary)}.glosario{padding:.9rem;border:1px solid var(--trazo-suave);border-radius:var(--radius-md)}.glosario li{margin-block:.5rem}
  @media(max-width:68rem){.filtros,.resumen,.hechos{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:42rem){.filtros,.resumen,.hechos{grid-template-columns:1fr}.historial>li{grid-template-columns:1rem minmax(0,1fr)}.exportacion{align-items:stretch;flex-direction:column}.cambios div{grid-template-columns:1fr}.cambios div>span[aria-hidden='true']{display:none}}
</style>
