<script module>
  import { registrarLimpiezaDeLectura } from '../../nucleo/lectura/cache.js';
  // Sólo criterios de consulta en RAM para volver de una fuente; nunca mensajes ni almacenamiento del navegador.
  let vistaAnterior = null;
  registrarLimpiezaDeLectura(() => { vistaAnterior = null; });
</script>

<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import Turno from '../../comun/turno/Turno.svelte';
  import TituloDeConversacion from '../../comun/armazon/TituloDeConversacion.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import PanelDeContexto from '../../estudiante/piezas/PanelDeContexto.svelte';
  import FondoInicioMatematico from '../../estudiante/piezas/FondoInicioMatematico.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import * as api from '../../nucleo/api/conversacionesInvestigacion.js';
  import { navegar } from '../../enrutado/navegar.js';
  import { CAMINOS } from '../../enrutado/caminos.js';

  let buscar = $state(''), clase = $state(''), desde = $state(''), hasta = $state('');
  let pruebas = $state(false), capturar = $state(false);
  let directorio = $state({ estudiantes: [], clases: [], pagina: 1, paginas: 0, total: 0 });
  let lista = $state({ conversaciones: [], pagina: 1, paginas: 0, total: 0 });
  let estudiante = $state(null), sesionVista = $state(''), mensajes = $state([]);
  let ocupado = $state(false), error = $state('');
  let contingencia = $state(null), ultimaConsulta = null;
  let graficaSolicitada = $state(null);
  let selectorAbierto = $state(false), historialAbierto = $state(false), areaDelHilo = $state(null);
  let controlador, revision = 0;
  // Las fechas del formulario son días de Colombia; hasta incluye todo ese día.
  function filtros() {
    let fin = '';
    if (hasta) {
      const fecha = new Date(`${hasta}T00:00:00-05:00`);
      fecha.setUTCDate(fecha.getUTCDate() + 1);
      fin = fecha.toISOString();
    }
    return { clase, desde: desde ? `${desde}T00:00:00-05:00` : '', hasta: fin };
  }
  async function cargar(accion) {
    controlador?.abort();
    controlador = new AbortController();
    const señal = controlador.signal, actual = ++revision;
    ocupado = true; error = ''; contingencia = null; ultimaConsulta = accion;
    try { await accion(señal, actual); }
    catch (fallo) {
      if (actual === revision && !señal.aborted) {
        contingencia = describir(fallo);
        if (fallo?.name === 'Error' && fallo.message) contingencia.explicacion = fallo.message;
      }
    } finally { if (actual === revision) ocupado = false; }
  }
  function aplicar(pagina = 1) {
    if (desde && hasta && desde > hasta) { error = 'La fecha inicial debe ser anterior o igual a la final.'; return; }
    const persona = estudiante;
    sesionVista = ''; mensajes = []; graficaSolicitada = null; lista = { conversaciones: [], pagina: 1, paginas: 0, total: 0 };
    return cargar(async (señal, actual) => {
      const resultado = await api.estudiantes({ buscar, clase, pagina, pruebas: pruebas ? 1 : 0 }, señal);
      if (actual === revision) directorio = resultado;
      if (persona && actual === revision) {
        const charlas = await api.conversaciones(persona.id, { ...filtros(), pagina:1 }, señal);
        if (actual === revision) lista = charlas;
      }
    });
  }
  function cargarDirectorio(pagina = 1) {
    return cargar(async (señal, actual) => {
      const resultado = await api.estudiantes({ buscar, clase, pagina, pruebas:pruebas ? 1 : 0 }, señal);
      if (actual === revision) directorio = resultado;
    });
  }
  function elegir(persona, pagina = 1) {
    estudiante = persona; selectorAbierto = false; sesionVista = ''; mensajes = []; graficaSolicitada = null;
    lista = { conversaciones: [], pagina: 1, paginas: 0, total: 0 };
    return cargar(async (señal, actual) => {
      const resultado = await api.conversaciones(persona.id, { ...filtros(), pagina }, señal);
      if (actual === revision) lista = resultado;
    });
  }
  function abrir(id) {
    sesionVista = id; mensajes = []; historialAbierto = false; graficaSolicitada = null;
    return cargar(async (señal, actual) => {
      const resultado = await api.hilo(estudiante.id, id, filtros(), señal);
      if (actual === revision) {
        mensajes = resultado.mensajes ?? [];
        await tick();
        if (areaDelHilo) areaDelHilo.scrollTop = 0;
      }
    });
  }
  function ocultar(texto) {
    let salida = String(texto ?? '');
    if (!capturar) return salida;
    for (const valor of [estudiante?.correo, estudiante?.nombre].filter(Boolean)) salida = salida.split(valor).join('[dato oculto]');
    return salida.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '[correo oculto]');
  }
  function turnoDe(mensaje) {
    return { turno: capturar ? '' : mensaje.turno,
      bloques: (mensaje.bloques?.length ? mensaje.bloques : [{tipo:'prosa',contenido:mensaje.contenido}])
        .map(b => ({ ...b, contenido: ocultar(b.contenido) })),
      citas: mensaje.citas, nivel: mensaje.nivel, procedencia: mensaje.procedencia };
  }
  const hiloVisible = $derived(mensajes.map(m => ({autor:m.autor === 'estudiante' ? 'estudiante':'tutor',turno:turnoDe(m)})));
  const charlaActual = $derived(lista.conversaciones.find(c => c.sesion === sesionVista));
  const fecha = valor => new Date(valor).toLocaleString('es-CO', { timeZone: 'America/Bogota' });
  async function restaurarVista() {
    const anterior = vistaAnterior; vistaAnterior = null;
    if (!anterior || !sesion.conversacion || anterior.actor !== sesion.conversacion) { await aplicar(); return; }
    ({buscar,clase,desde,hasta,pruebas,capturar} = anterior);
    await aplicar(anterior.paginaDirectorio);
    const persona = directorio.estudiantes.find(p => p.id === anterior.sujeto);
    if (!persona || error || contingencia) return;
    await elegir(persona, anterior.paginaCharlas);
    if (lista.conversaciones.some(c => c.sesion === anterior.charla) && !error && !contingencia) await abrir(anterior.charla);
  }
  onMount(() => { void restaurarVista(); });
  onDestroy(() => {
    vistaAnterior = sesion.conversacion && estudiante ? {actor:sesion.conversacion,buscar,clase,desde,hasta,pruebas,capturar,
      sujeto:estudiante.id,charla:sesionVista,paginaDirectorio:directorio.pagina,paginaCharlas:lista.pagina} : null;
    revision++; controlador?.abort(); mensajes = [];
  });
</script>
<section class="visor" class:captura={capturar} aria-label="Conversaciones de estudiantes">
  <h1 class="solo-lectores">Conversaciones de estudiantes</h1>
  <header class="cabecera-investigacion">
    <button class="volver" aria-label="Volver a estudiantes" title="Volver a estudiantes" onclick={() => navegar(CAMINOS.estudiante)}><Icono nombre="flecha-izq" medida={18} /></button>
    <button class="selector" onclick={() => { selectorAbierto = true; }} aria-haspopup="dialog">
      <Icono nombre="estudiante" medida={18} />
      <span><strong>{estudiante ? (capturar ? 'Estudiante' : estudiante.nombre) : 'Seleccionar estudiante'}</strong>
      <small>{estudiante && !capturar ? estudiante.correo : 'Conversaciones para investigación'}</small></span>
      <span aria-hidden="true">⌄</span>
    </button>
    <button class="boton-historial" aria-expanded={historialAbierto} aria-controls="historial-investigacion" onclick={() => { historialAbierto = !historialAbierto; }}>Conversaciones ({lista.total})</button>
    <label class="opcion captura-opcion"><input type="checkbox" bind:checked={capturar} />Preparar captura sin identificadores visibles</label>
  </header>

  <details class="controles">
    <summary>Filtros de curso y fechas <span>{clase ? directorio.clases.find(c=>c.id===clase)?.nombre : 'Todos los cursos'}{desde || hasta ? ' · Periodo seleccionado' : ''}</span></summary>
    <form class="filtros" onsubmit={e => { e.preventDefault(); void aplicar(); }}>
      <label>Curso<select bind:value={clase}><option value="">Todos los cursos / sin atribución</option>
        {#each directorio.clases as curso}<option value={curso.id}>{curso.nombre}{curso.archivada ? ' (archivado)' : ''}</option>{/each}</select></label>
      <label>Desde<input type="date" bind:value={desde} /></label>
      <label>Hasta (inclusive)<input type="date" bind:value={hasta} /></label>
      <label class="opcion"><input type="checkbox" bind:checked={pruebas} />Incluir cuentas de prueba</label>
      <button type="submit" disabled={ocupado}>Aplicar filtros</button>
    </form>
    <p class="aclaracion">Curso según matrícula histórica; fechas en Colombia. El día final se incluye completo. Sin fechas se consulta todo el historial académico.</p>
  </details>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
  {#if ocupado}<p class="estado" role="status">Consultando…</p>{/if}
  {#if capturar}<p class="estado" role="status">Nombre y correo ocultos. Revisa otros datos personales del texto antes de compartir.</p>{/if}
  <div class="cuerpo">
    {#if historialAbierto}<button class="velo" aria-label="Cerrar lista de conversaciones" onclick={() => { historialAbierto = false; }}></button>{/if}
    <aside id="historial-investigacion" class="historial" class:abierto={historialAbierto} aria-label="Conversaciones guardadas">
      <div class="titulo-historial"><h2>Conversaciones ({lista.total})</h2><button class="cerrar-historial" aria-label="Cerrar lista de conversaciones" onclick={() => { historialAbierto = false; }}><Icono nombre="cerrar" medida={16} /></button></div>
      <div class="lista-charlas">
        {#each lista.conversaciones as charla (charla.sesion)}<button class:seleccionado={sesionVista === charla.sesion} onclick={() => abrir(charla.sesion)} disabled={ocupado}>
          <strong><TituloDeConversacion titulo={capturar ? 'Conversación académica' : charla.titulo || 'Conversación'} /></strong><small>{fecha(charla.inicio)} · {charla.turnos} turnos</small></button>{/each}
        {#if estudiante && !ocupado && !lista.total}<p>Sin mensajes en el curso y periodo elegidos.</p>{:else if !estudiante}<p>Elige un estudiante desde la cabecera.</p>{/if}
      </div>
      {#if estudiante && lista.paginas > 1}<div class="paginas"><button disabled={ocupado || lista.pagina <= 1} onclick={() => elegir(estudiante, lista.pagina-1)}>Anterior</button>
        <span>{lista.pagina} / {lista.paginas}</span><button disabled={ocupado || lista.pagina >= lista.paginas} onclick={() => elegir(estudiante, lista.pagina+1)}>Siguiente</button></div>{/if}
    </aside>
    <div class="espacio-chat">
      {#if preferencias.fondoDuranteConversacion}<div class="ambiente-chat" style={`opacity:${preferencias.intensidadFondoConversacion / 100}`}><FondoInicioMatematico /></div>{/if}
      <!-- svelte-ignore a11y_no_noninteractive_tabindex (El hilo desplazable debe recibir foco para recorrerlo con teclado.) -->
      <div class="hilo superficie-cuaderno" role="region" aria-label="Reconstrucción de conversación" tabindex="0" bind:this={areaDelHilo}>
        <div class="contenido-hilo">
          {#if contingencia}<Degradacion respuesta={contingencia} alReintentar={() => cargar(ultimaConsulta)} amplio />{/if}
          {#if !sesionVista}<div class="vacio"><Icono nombre="didaxia" medida={42} /><h2>{estudiante ? 'Elige una conversación' : 'Reconstruye una conversación'}</h2><p>{estudiante ? 'Abre una charla del historial para revisar sus mensajes.' : 'Selecciona un estudiante en la cabecera. Sus consultas y respuestas aparecerán aquí, como en el tutor.'}</p></div>
          {:else if charlaActual}<p class="fecha-charla"><TituloDeConversacion titulo={capturar ? 'Conversación académica' : charlaActual.titulo} /> · {fecha(charlaActual.inicio)}</p>{/if}
          {#each mensajes as mensaje, indice (indice)}
            <small class="momento">{fecha(mensaje.momento)}</small>
            {#if mensaje.degradado}<Degradacion respuesta={{situacion:'degradado',explicacion:ocultar(mensaje.contenido),reintentable:false}} />
            {:else}<Turno turno={turnoDe(mensaje)} autor={mensaje.autor === 'estudiante' ? 'estudiante' : 'tutor'} soloLectura
              rotuloEstudiante={capturar ? 'Estudiante' : `Estudiante · ${estudiante?.nombre ?? ''}`} rotuloAsistente="Respuesta del asistente"
              volverA={CAMINOS.conversacionesInvestigacion}
              alAbrirGrafica={(definicion,disparador) => { graficaSolicitada = {definicion,disparador,momento:Date.now()}; }} />{/if}
          {/each}
        </div>
      </div>
      <footer class="pie-lectura"><Icono nombre="escudo" medida={14} /><span>Lectura para investigación · mensajes originales · sin envío al estudiante</span></footer>
    </div>
    {#if !capturar}<PanelDeContexto hilo={hiloVisible} solicitudGrafica={graficaSolicitada} alCerrarGraficaDelChat={() => { graficaSolicitada = null; }} visibleEnEscritorio={preferencias.panelVisible} soloLectura />{/if}
  </div>
</section>

<Dialogo bind:abierto={selectorAbierto} titulo="Seleccionar estudiante" ancho="44rem">
  <form class="buscador" onsubmit={e => { e.preventDefault(); void cargarDirectorio(); }}>
    <label>Nombre o correo<input bind:value={buscar} maxlength="200" placeholder="Buscar por nombre o correo institucional" /></label>
    <button type="submit" disabled={ocupado}>Buscar</button>
  </form>
  <p class="resumen-directorio">{directorio.total} estudiantes que coinciden con la búsqueda y el curso</p>
  <div class="personas" aria-label="Lista de estudiantes">
    {#each directorio.estudiantes as persona (persona.id)}<button class:seleccionado={estudiante?.id === persona.id} onclick={() => elegir(persona)} disabled={ocupado}>
      <span class="inicial" aria-hidden="true">{persona.nombre?.slice(0,1)}</span><span><strong>{persona.nombre}</strong><small>{persona.correo}{persona.prueba ? ' · prueba' : ''}</small></span></button>{/each}
    {#if !ocupado && !directorio.total}<p>No hay estudiantes que coincidan.</p>{/if}
  </div>
  <div class="paginas"><button disabled={ocupado || directorio.pagina <= 1} onclick={() => cargarDirectorio(directorio.pagina-1)}>Anterior</button>
    <span>{directorio.pagina} / {directorio.paginas || 1}</span><button disabled={ocupado || directorio.pagina >= directorio.paginas} onclick={() => cargarDirectorio(directorio.pagina+1)}>Siguiente</button></div>
</Dialogo>

<style>
  .visor { flex:1; block-size:100%; min-block-size:0; min-inline-size:0; display:flex; flex-direction:column; overflow:hidden; color:var(--ink-primary); }
  .solo-lectores { position:absolute; inline-size:1px; block-size:1px; overflow:hidden; clip-path:inset(50%); }
  .cabecera-investigacion { display:flex; gap:.65rem; align-items:center; padding:.65rem 1rem; border-block-end:1px solid var(--trazo-suave); background:var(--surface-paper); flex-shrink:0; }
  button,input,select { font:inherit; color:inherit; border:1px solid var(--trazo-suave); border-radius:.65rem; background:var(--surface-paper); padding:.65rem; }
  button { min-block-size:44px; cursor:pointer; } button:disabled { opacity:.5; cursor:default; }
  button:hover { border-color:var(--accent-main); } button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible,.hilo:focus-visible { outline:2px solid var(--accent-main); outline-offset:2px; }
  .selector { display:flex; align-items:center; gap:.65rem; text-align:start; min-inline-size:0; max-inline-size:32rem; margin-inline-end:auto; }
  .selector span:not([aria-hidden]) { display:grid; min-inline-size:0; gap:.2rem; }
  .selector strong,.selector small { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  small { color:var(--ink-secondary); font-size:.75rem; }
  .opcion { display:flex; align-items:center; gap:.4rem; font-size:.75rem; } input[type=checkbox] { accent-color:var(--accent-main); inline-size:18px; block-size:18px; flex-shrink:0; }
  .controles { flex-shrink:0; border-block-end:1px solid var(--trazo-suave); font-size:.8rem; max-block-size:45%; overflow:auto; }
  summary { cursor:pointer; padding:.6rem 1rem; } summary span { color:var(--ink-secondary); margin-inline-start:.5rem; }
  .filtros { display:flex; align-items:end; flex-wrap:wrap; gap:.65rem; padding:.6rem 1rem; }
  label { display:grid; gap:.3rem; font-size:.8rem; min-inline-size:0; } input,select { max-inline-size:100%; } .filtros select { max-inline-size:25rem; }
  .aclaracion { padding:0 1rem .5rem; font-size:.75rem; color:var(--ink-secondary); }
  .estado,.error { flex-shrink:0; padding:.4rem 1rem; margin:0; font-size:.8rem; background:var(--surface-paper); } .error { color:var(--semantic-error); }
  .cuerpo { position:relative; display:flex; flex:1; min-block-size:0; min-inline-size:0; overflow:hidden; }
  .historial { inline-size:16rem; flex-shrink:0; min-block-size:0; display:flex; flex-direction:column; border-inline-end:1px solid var(--trazo-suave); padding:.75rem; background:var(--surface-paper); }
  .titulo-historial { display:flex; align-items:center; justify-content:space-between; } h2 { font-size:1rem; }
  .lista-charlas { overflow-y:auto; flex:1; min-block-size:0; overscroll-behavior:contain; touch-action:pan-y; }
  .lista-charlas > button { display:grid; gap:.4rem; text-align:start; inline-size:100%; border-color:transparent; margin-block:.4rem; overflow-wrap:anywhere; }
  .lista-charlas strong { min-inline-size:0; overflow:hidden; text-overflow:ellipsis; }
  .seleccionado { border-color:var(--accent-main)!important; background:var(--accent-surface,var(--surface-paper)); }
  .espacio-chat { flex:1; min-inline-size:0; min-block-size:0; display:flex; flex-direction:column; position:relative; background:var(--surface-paper); overflow:hidden; }
  .ambiente-chat { position:absolute; inset:0; pointer-events:none; overflow:hidden; z-index:0; }
  .hilo { position:relative; z-index:1; flex:1; min-block-size:0; min-inline-size:0; overflow-y:auto; overflow-x:hidden; overscroll-behavior:contain; touch-action:pan-y; -webkit-overflow-scrolling:touch; padding:1.5rem clamp(.75rem,3vw,2rem) 2rem; background-color:transparent; }
  .contenido-hilo { max-inline-size:58rem; margin-inline:auto; overflow-wrap:anywhere; }
  .momento,.fecha-charla { display:block; font-size:.7rem; color:var(--ink-secondary); margin-block:.75rem; } .fecha-charla { text-align:center; }
  .pie-lectura { position:relative; z-index:1; display:flex; gap:.4rem; align-items:center; justify-content:center; padding:.7rem; color:var(--ink-secondary); font-size:.7rem; flex-shrink:0; border-block-start:1px solid var(--trazo-suave); }
  .vacio { min-block-size:16rem; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:2rem 1rem; color:var(--ink-secondary); }
  .vacio h2 { font-size:1.3rem; color:var(--ink-primary); } .vacio p { max-inline-size:30rem; }
  .buscador { display:flex; align-items:end; gap:.5rem; } .buscador label { flex:1; } .resumen-directorio { color:var(--ink-secondary); font-size:.8rem; }
  .personas { display:grid; gap:.4rem; } .personas > button { display:flex; align-items:center; gap:.75rem; text-align:start; inline-size:100%; min-inline-size:0; }
  .personas > button > span:last-child { display:grid; gap:.3rem; overflow-wrap:anywhere; min-inline-size:0; }
  .inicial { display:grid; place-items:center; inline-size:2rem; block-size:2rem; border-radius:50%; flex-shrink:0; background:var(--accent-surface); color:var(--accent-main); }
  .paginas { display:flex; gap:.4rem; justify-content:space-between; align-items:center; margin-block-start:.6rem; font-size:.8rem; }
  .velo,.cerrar-historial,.boton-historial { display:none; }
  .captura .controles,.captura .historial,.captura .volver,.captura .boton-historial,.captura .selector { display:none; }
  .captura .cabecera-investigacion { justify-content:end; }
  @media(max-width:1100px) { .captura-opcion { max-inline-size:11rem; } .historial { inline-size:14rem; } }
  @media(max-width:768px) {
    .cabecera-investigacion { flex-wrap:wrap; padding:.5rem; gap:.4rem; } .volver { padding:.5rem; }
    .selector { max-inline-size:calc(100% - 3.5rem); flex:1; } .selector strong { font-size:.85rem; } .selector small { font-size:.65rem; }
    .boton-historial { display:block; font-size:.75rem; min-block-size:36px; } .captura-opcion { max-inline-size:none; margin-inline-start:auto; font-size:.65rem; }
    .controles summary span { display:block; margin-inline-start:0; margin-block-start:.25rem; }
    .filtros { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); } .filtros label:first-child { grid-column:1/-1; }
    .historial { display:none; position:absolute; inset-block:0; inset-inline-start:0; z-index:5; inline-size:min(85%,18rem); box-shadow:var(--shadow-float); }
    .historial.abierto { display:flex; } .cerrar-historial { display:block; } .velo { display:block; position:absolute; inset:0; background:var(--velo-modal); z-index:4; border:0; border-radius:0; }
    .hilo { padding:1rem .65rem 2rem; } .pie-lectura { padding:.5rem; font-size:.65rem; }
    .visor:not(.captura) .contenido-hilo { padding-block-start:3.5rem; }
  }
</style>
