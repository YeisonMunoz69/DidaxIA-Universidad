
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import { onDestroy, untrack } from 'svelte';
  import CabeceraDeRuta from '../../docente/piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../../docente/piezas/PantallaDesplazable.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import TableroKPI from '../../comun/kpi/TableroKPI.svelte';
  import RelecturaConductual from '../piezas/RelecturaConductual.svelte';
  import { visibleEnTablero } from '../../comun/kpi/visibilidad.js';
  import * as apiKpi from '../../nucleo/api/kpi.js';
  import * as apiConceptos from '../../nucleo/api/conceptos.js';
  import * as apiInformes from '../../nucleo/api/informes.js';
  import { descargarPDF } from '../../nucleo/descargas/pdf.js';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import { pedir } from '../../nucleo/api/cliente.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { navegar } from '../../enrutado/navegar.js';
  import SelectorFecha from '../../comun/base/SelectorFecha.svelte';
  import { CAMINOS } from '../../enrutado/caminos.js';

  let desde = $state(fechaLocal(-7));
  let hasta = $state(fechaLocal(1));
  let facultad = $state('');
  let programa = $state('');
  let docente = $state('');
  let clase = $state('');
  let semestre = $state('');
  let concepto = $state('');
  let versionCorpus = $state('');
  let versionModelo = $state('');
  let datos = $state(null);
  let cursos = $state([]);
  let jerarquia = $state({ facultades: [] });
  let conceptos = $state([]);
  let fallo = $state(null);
  let cargando = $state(true);
  let peticion = 0;
  let consultaAplicada = $state(null);
  let confirmarCompleto = $state(false);
  let modoInforme = $state('seleccion');
  let seleccionInforme = $state([]);
  let generandoInforme = $state(false);
  let resultadoInforme = $state('');
  let errorInforme = $state('');
  let vistaPrevia = $state('');
  const descargasActivas = new Set();
  const controlesActivos = new Set();

  function fechaLocal(desplazamiento) {
    const fecha = new Date(Date.now() + desplazamiento * 86400000);
    const partes = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(fecha);
    const de = (tipo) => partes.find((parte) => parte.type === tipo)?.value;
    return `${de('year')}-${de('month')}-${de('day')}`;
  }

  function parametros({ incluirFiltros = true } = {}) {
    const base = {
      desde: `${desde}T00:00:00-05:00`,
      hasta: `${hasta}T00:00:00-05:00`
    };
    return incluirFiltros ? {
      ...base, facultad, programa, docente, clase, semestre, concepto,
      version_corpus: versionCorpus, version_modelo: versionModelo
    } : base;
  }

  const filtrosPendientes = $derived(
    consultaAplicada !== null &&
    JSON.stringify(parametros()) !== JSON.stringify(consultaAplicada)
  );
  const resultadosPublicables = $derived((datos?.indicadores ?? []).filter(visibleEnTablero));
  const insigniaKpi = $derived(datos?.version_catalogo?.replace(/^kpi\./i, 'KPI ') ?? 'KPI');
  const cantidadInforme = $derived(modoInforme === 'completo'
    ? resultadosPublicables.length : seleccionInforme.length);
  const informeListo = $derived(modoInforme === 'completo'
    ? confirmarCompleto && resultadosPublicables.length > 0 : seleccionInforme.length > 0);

  function alternarIndicador(codigo) {
    seleccionInforme = seleccionInforme.includes(codigo)
      ? seleccionInforme.filter((item) => item !== codigo)
      : [...seleccionInforme, codigo];
  }

  async function cargarOpciones() {
    const consulta = new URLSearchParams(parametros({ incluirFiltros: false }));
    const [resumen, banco] = await Promise.all([
      pedir(`/investigacion/resumen?${consulta}`), apiConceptos.listar()
    ]);
    cursos = resumen?.cursos ?? [];
    jerarquia = resumen?.jerarquia ?? { facultades: [] };
    conceptos = Array.isArray(banco) ? banco : [];
  }

  const nodoFacultad = $derived(
    jerarquia.facultades?.find((item) => item.nombre === facultad) ?? null
  );
  const nodoPrograma = $derived(
    nodoFacultad?.programas?.find((item) => item.nombre === programa) ?? null
  );
  const nodoDocente = $derived(
    nodoPrograma?.docentes?.find((item) => item.identificador === docente) ?? null
  );
  const nodoClase = $derived(
    nodoDocente?.clases?.find((item) => item.identificador === clase) ?? null
  );

  function bajar(nivel, valor) {
    if (nivel === 'institucion') {
      facultad = ''; programa = ''; docente = ''; clase = '';
    } else if (nivel === 'facultad') {
      facultad = valor; programa = ''; docente = ''; clase = '';
    } else if (nivel === 'programa') {
      programa = valor; docente = ''; clase = '';
    } else if (nivel === 'docente') {
      docente = valor; clase = '';
    } else if (nivel === 'clase') {
      clase = valor;
    }
    void cargar();
  }

  function abrirEstudiante(estudiante) {
    navegar(
      `${CAMINOS.estudiante}?clase=${encodeURIComponent(clase)}` +
      `&id=${encodeURIComponent(estudiante.identificador)}`
    );
  }

  async function cargar() {
    const actual = ++peticion;
    const consultaConfirmada = parametros();
    cargando = true;
    fallo = null;
    try {
      if (!cursos.length) await cargarOpciones();
      const nuevo = await apiKpi.indicadoresInstitucional(consultaConfirmada);
      if (actual === peticion) {
        datos = nuevo;
        seleccionInforme = seleccionInforme.filter((codigo) =>
          nuevo.indicadores?.some((item) => item.codigo === codigo && visibleEnTablero(item)));
        consultaAplicada = Object.freeze({ ...consultaConfirmada });
        resultadoInforme = '';
        errorInforme = '';
      }
    } catch (error) {
      if (actual === peticion) {
        datos = null;
        fallo = describir(error);
      }
    } finally {
      if (actual === peticion) cargando = false;
    }
  }

  function limpiar() {
    facultad = ''; programa = ''; docente = ''; clase = ''; semestre = '';
    concepto = ''; versionCorpus = ''; versionModelo = '';
    cargar();
  }

  function cuerpoInforme(tipo, codigo = '') {
    if (!consultaAplicada || filtrosPendientes) {
      throw new Error('Aplica primero los filtros para que el PDF coincida con el tablero.');
    }
    const nombres = [
      'facultad', 'programa', 'docente', 'semestre', 'concepto',
      'version_corpus', 'version_modelo'
    ];
    const filtros = Object.fromEntries(nombres
      .filter((nombre) => String(consultaAplicada[nombre] ?? '').trim() !== '')
      .map((nombre) => [nombre, String(consultaAplicada[nombre]).trim()]));
    return {
      tipo,
      codigo: tipo === 'indicador' ? codigo : '',
      codigos: tipo === 'seleccion' ? seleccionInforme : undefined,
      confirmado: tipo === 'completo' ? confirmarCompleto : false,
      desde: consultaAplicada.desde,
      hasta: consultaAplicada.hasta,
      clase: consultaAplicada.clase,
      filtros
    };
  }

  function nombreInforme(tipo, codigo = '') {
    const desdeAplicado = consultaAplicada?.desde?.slice(0, 10) || 'sin-fecha';
    const hastaAplicado = consultaAplicada?.hasta?.slice(0, 10) || 'sin-fecha';
    return `didaxia-kpi-${tipo === 'indicador' ? codigo : tipo}-${desdeAplicado}-${hastaAplicado}.pdf`;
  }

  async function solicitarArchivo(tipo, codigo = '', { vista = false } = {}) {
    const control = new AbortController();
    controlesActivos.add(control);
    try {
      return vista
        ? await apiInformes.vistaPrevia(cuerpoInforme(tipo, codigo), { señal: control.signal })
        : await apiInformes.descargar(cuerpoInforme(tipo, codigo), { señal: control.signal });
    } finally {
      controlesActivos.delete(control);
    }
  }

  async function descargarIndicador(indicador) {
    const archivo = await solicitarArchivo('indicador', indicador.codigo);
    const descarga = descargarPDF(archivo, nombreInforme('indicador', indicador.codigo));
    descargasActivas.add(descarga);
    return `La ficha de ${indicador.codigo} está lista para guardar.`;
  }

  async function prepararInforme(vista = false) {
    if (!vista && !await confirmarAccion({ tipo:'descarga', titulo:'¿Descargar informe de analítica institucional?',
      descripcion:`Se generará un PDF con ${cantidadInforme} ${cantidadInforme === 1 ? 'métrica' : 'métricas'} del periodo y filtros aplicados.`, confirmar:'Descargar PDF' })) return;
    generandoInforme = true;
    resultadoInforme = '';
    errorInforme = '';
    try {
      const tipo = modoInforme;
      const archivo = await solicitarArchivo(tipo, '', { vista });
      if (vista) {
        if (vistaPrevia) URL.revokeObjectURL(vistaPrevia);
        vistaPrevia = URL.createObjectURL(archivo);
        resultadoInforme = 'La vista previa usa la consulta aplicada al tablero.';
      } else {
        const descarga = descargarPDF(archivo, nombreInforme(tipo));
        descargasActivas.add(descarga);
        toast.descarga(`Descargando informe con ${cantidadInforme} métricas.`);
      }
    } catch (error) {
      errorInforme = error?.message && error.name !== 'FalloDeRed'
        ? error.message
        : describir(error).explicacion;
    } finally {
      generandoInforme = false;
    }
  }

  $effect(() => { untrack(() => cargar()); });
  onDestroy(() => {
    for (const control of controlesActivos) control.abort();
    for (const descarga of descargasActivas) descarga.liberar();
    if (vistaPrevia) URL.revokeObjectURL(vistaPrevia);
  });
</script>

<PantallaDesplazable anchoMaximo="min(90rem, 100%)">
  <CabeceraDeRuta titulo="Analítica institucional" icono="analitica-institucional" insignia={insigniaKpi} ayuda="Concepto, corpus y modelo filtran sólo turnos con instrumentación explícita. Los anteriores quedan fuera por falta de cobertura, no se interpretan como cero. Cohorte está pendiente de una definición institucional aprobada. Los agregados no son rankings: consulta muestra, cobertura y límites de cada KPI.">
    {#snippet nota()}
      Indicadores institucionales reproducibles. Cada consulta conserva periodo y filtros en el resultado y deja trazabilidad de acceso.
    {/snippet}
  </CabeceraDeRuta>

  <form class="filtros" aria-label="Filtros institucionales" onsubmit={(evento) => { evento.preventDefault(); cargar(); }}>
    <SelectorFecha etiqueta="Desde" bind:value={desde} maximo={fechaLocal(0)} />
    <SelectorFecha etiqueta="Hasta (exclusivo)" bind:value={hasta} minimo={desde} maximo={fechaLocal(1)} exclusivo />
    <label><span>Facultad</span><input bind:value={facultad} maxlength="160" placeholder="Todas" /></label>
    <label><span>Programa</span><input bind:value={programa} maxlength="160" placeholder="Todos" /></label>
    <label><span>Docente</span><select use:menuDesplegable={docente} bind:value={docente}><option value="">Todos</option>
      {#each cursos as curso (curso.id)}<option value={curso.docente?.identificador ?? curso.docente?.id}>{curso.docente?.nombre ?? 'Docente'}</option>{/each}
    </select></label>
    <label><span>Clase</span><select use:menuDesplegable={clase} bind:value={clase}><option value="">Todas</option>
      {#each cursos as curso (curso.id)}<option value={curso.id}>{curso.nombre}</option>{/each}
    </select></label>
    <label><span>Semestre</span><select use:menuDesplegable={semestre} bind:value={semestre}><option value="">Todos</option>
      {#each Array.from({ length: 20 }, (_, i) => i + 1) as numero}<option value={numero}>{numero}</option>{/each}
    </select></label>
    <label><span>Concepto</span><select use:menuDesplegable={concepto} bind:value={concepto}><option value="">Todos</option>
      {#each conceptos as item (item.id)}<option value={item.id}>{item.nombre}</option>{/each}
    </select></label>
    <label><span>Versión de corpus</span><input bind:value={versionCorpus} maxlength="160" list="versiones-corpus" placeholder="Todas" /></label>
    <datalist id="versiones-corpus">{#each datos?.versiones_observadas?.corpus ?? [] as version}<option value={version}></option>{/each}</datalist>
    <label><span>Versión de modelo</span><input bind:value={versionModelo} maxlength="160" list="versiones-modelo" placeholder="Todas" /></label>
    <datalist id="versiones-modelo">{#each datos?.versiones_observadas?.modelos ?? [] as version}<option value={version}></option>{/each}</datalist>
    <button class="aplicar" type="submit" disabled={cargando}>{cargando ? 'Calculando…' : 'Aplicar filtros'}</button>
    <button class="limpiar" type="button" onclick={limpiar} disabled={cargando}>Limpiar</button>
  </form>
  <RelecturaConductual {cursos} alActualizar={cargar} />


  {#if fallo}
    <Degradacion respuesta={fallo} alReintentar={cargar} />
  {:else if cargando && !datos}
    <CargadorCubo mensaje="Calculando indicadores y verificando sus reglas de calidad…" pantallaCompleta />
  {:else if datos}
    <section class="contexto">
      <div><span>Estudiantes elegibles</span><strong>{datos.poblacion?.estudiantes_elegibles ?? '—'}</strong></div>
      <div><span>Clases en alcance</span><strong>{datos.poblacion?.clases ?? '—'}</strong></div>
      <div><span>Indicadores recibidos</span><strong>{datos.indicadores?.length ?? 0}</strong></div>
      <div><span>Catálogo</span><strong>{datos.version_catalogo}</strong></div>

    </section>
    <section class="drill-down" aria-labelledby="titulo-drill-down">
      <div class="cabecera-drill">
        <div><span class="sobrelinea">DRILL-DOWN AUTORIZADO</span><h2 id="titulo-drill-down">Del conjunto institucional a una ficha</h2></div>
        <nav aria-label="Ruta de exploración">
          <button type="button" onclick={() => bajar('institucion')}>Institución</button>
          {#if nodoFacultad}<span aria-hidden="true">›</span><button type="button" onclick={() => bajar('facultad', facultad)}>{facultad}</button>{/if}
          {#if nodoPrograma}<span aria-hidden="true">›</span><button type="button" onclick={() => bajar('programa', programa)}>{programa}</button>{/if}
          {#if nodoDocente}<span aria-hidden="true">›</span><button type="button" onclick={() => bajar('docente', docente)}>{nodoDocente.nombre}</button>{/if}
          {#if nodoClase}<span aria-hidden="true">›</span><button type="button" onclick={() => bajar('clase', clase)}>{nodoClase.nombre}</button>{/if}
        </nav>
      </div>
      <div class="niveles">
        {#if !nodoFacultad}
          {#each jerarquia.facultades ?? [] as item (item.nombre)}
            <button type="button" onclick={() => bajar('facultad', item.nombre)}><span>Facultad</span><strong>{item.nombre}</strong><small>{item.programas.length} programas</small></button>
          {/each}
        {:else if !nodoPrograma}
          {#each nodoFacultad.programas as item (item.nombre)}
            <button type="button" onclick={() => bajar('programa', item.nombre)}><span>Programa</span><strong>{item.nombre}</strong><small>{item.docentes.length} docentes</small></button>
          {/each}
        {:else if !nodoDocente}
          {#each nodoPrograma.docentes as item (item.identificador)}
            <button type="button" onclick={() => bajar('docente', item.identificador)}><span>Docente</span><strong>{item.nombre}</strong><small>{item.clases.length} clases</small></button>
          {/each}
        {:else if !nodoClase}
          {#each nodoDocente.clases as item (item.identificador)}
            <button type="button" onclick={() => bajar('clase', item.identificador)}><span>Clase</span><strong>{item.nombre}</strong><small>{item.estudiantes.length} estudiantes</small></button>
          {/each}
        {:else}
          {#each nodoClase.estudiantes as item (item.identificador)}
            <button type="button" onclick={() => abrirEstudiante(item)}><span>Estudiante</span><strong>{item.nombre}</strong><small>{item.semestre ? `Semestre ${item.semestre}` : 'Semestre pendiente'} · abrir ficha auditada</small></button>
          {/each}
        {/if}
      </div>
      {#if !(jerarquia.facultades?.length)}<p class="sin-jerarquia">No hay perfiles completos para construir esta ruta. Las ausencias se informan en Calidad de datos y no se reemplazan por una categoría inventada.</p>{/if}
    </section>
    {#if filtrosPendientes}
      <p class="aviso-filtros" role="status">Hay filtros sin aplicar. Las descargas quedan pausadas para no mezclar una consulta nueva con los datos visibles.</p>
    {/if}
    <TableroKPI {datos} alDescargarPDF={descargarIndicador} descargasHabilitadas={!filtrosPendientes} />
    <section class="informes" aria-labelledby="titulo-informes">
      <div><span class="sobrelinea">INFORME DE KPI</span><h2 id="titulo-informes">Elige las métricas del PDF</h2>
        <p>Cada ficha conserva definición, muestra, interpretación y límites. Las figuras usan sólo los datos que admite cada indicador.</p></div>
      <div class="selector-informe" role="group" aria-label="Alcance del informe">
        <label><input type="radio" bind:group={modoInforme} value="seleccion" /> Métricas seleccionadas</label>
        <label><input type="radio" bind:group={modoInforme} value="completo" /> Todos los resultados con valor ({resultadosPublicables.length})</label>
        {#if modoInforme === 'seleccion'}
          <div class="lista-kpi" role="group" aria-label="KPI disponibles">
            {#each resultadosPublicables as indicador (indicador.codigo)}
              <label><input type="checkbox" checked={seleccionInforme.includes(indicador.codigo)} onchange={() => alternarIndicador(indicador.codigo)} /> <span>{indicador.nombre} <small>({indicador.codigo})</small></span></label>
            {/each}
          </div>
          <p>{seleccionInforme.length} seleccionadas con valor en este periodo.</p>
        {:else}
          <label class="confirmacion"><input type="checkbox" bind:checked={confirmarCompleto} /><span>Confirmo generar {resultadosPublicables.length === 1 ? 'la' : 'las'} {resultadosPublicables.length} {resultadosPublicables.length === 1 ? 'ficha' : 'fichas'}.</span></label>
        {/if}
      </div>
      <div class="acciones-informe">
        <button type="button" onclick={() => prepararInforme(true)} disabled={generandoInforme || !informeListo || filtrosPendientes}>Vista previa</button>
        <button type="button" class="aplicar" onclick={() => prepararInforme(false)} disabled={generandoInforme || !informeListo || filtrosPendientes}>{generandoInforme ? 'Preparando…' : `Descargar ${cantidadInforme} ${cantidadInforme === 1 ? 'métrica' : 'métricas'}`}</button>
      </div>
      {#if resultadoInforme && vistaPrevia}<p class="resultado-informe" role="status">{resultadoInforme}</p>{/if}
      {#if errorInforme}<p class="error-informe" role="alert">{errorInforme}</p>{/if}
      {#if vistaPrevia}<object class="visor-informe" data={vistaPrevia} type="application/pdf" aria-label="Vista previa del informe KPI"><p>Tu navegador no puede mostrar la vista previa.</p></object>{/if}
    </section>
  {/if}
</PantallaDesplazable>

<style>
  .filtros { display: grid; grid-template-columns: repeat(5, minmax(9rem, 1fr)); align-items: end; gap: .65rem; padding: .9rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-panel); }
  label { display: grid; gap: .25rem; min-inline-size: 0; color: var(--ink-tertiary); font-size: var(--texto-xs); font-weight: 750; }
  input, select { min-block-size: 2.55rem; min-inline-size: 0; inline-size: 100%; padding: .45rem .6rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); font: inherit; }
  input:disabled { opacity: .7; }
  button { min-block-size: 2.55rem; padding: .45rem .8rem; border-radius: var(--radius-sm); font: inherit; font-size: var(--texto-sm); font-weight: 750; cursor: pointer; }
  button:disabled { opacity: .6; cursor: wait; }
  .aplicar { border: 1px solid transparent; background: var(--accent-main); color: var(--accent-on-main); }
  .limpiar { border: 1px solid var(--trazo-suave); background: var(--surface-paper); color: var(--ink-secondary); }
  .contexto { display: grid; grid-template-columns: repeat(3, auto) 1fr; align-items: center; gap: .7rem; padding: .75rem .9rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); }
  .contexto div { display: grid; padding-inline-end: .7rem; border-inline-end: 1px solid var(--trazo-suave); }
  .contexto span { margin: 0; color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .contexto strong { color: var(--ink-primary); font-variant-numeric: tabular-nums; }

  .informes { display: grid; grid-template-columns: minmax(16rem, 1.5fr) minmax(16rem, 1fr) auto; gap: .8rem; align-items: end; padding: 1.1rem; border: 2px solid var(--accent-main); border-radius: var(--radius-md); background: var(--accent-surface); }
  .selector-informe { display: grid; gap: .5rem; }
  .selector-informe > label, .lista-kpi label { display: flex; align-items: start; gap: .45rem; color: var(--ink-primary); font-weight: 600; }
  .selector-informe input { inline-size: auto; min-block-size: auto; margin-block-start: .25rem; }
  .lista-kpi { display: grid; gap: .45rem; max-block-size: 15rem; overflow: auto; padding: .65rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); }
  .lista-kpi small { color: var(--ink-tertiary); font-weight: 400; }
  .selector-informe p { margin: 0; color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .drill-down { display: grid; gap: .75rem; padding: 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); }
  .cabecera-drill { display: flex; justify-content: space-between; align-items: flex-end; gap: 1rem; }
  .cabecera-drill h2 { margin: .15rem 0 0; color: var(--ink-primary); font-size: var(--texto-lg); }
  .cabecera-drill nav { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: .3rem; }
  .cabecera-drill nav button { min-block-size: 2rem; padding: .25rem .5rem; border: 0; background: transparent; color: var(--accent-main); }
  .niveles { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(14rem, 100%), 1fr)); gap: .6rem; }
  .niveles button { display: grid; gap: .18rem; min-block-size: 5.25rem; text-align: start; border: 1px solid var(--trazo-suave); background: var(--surface-panel); color: var(--ink-primary); }
  .niveles button:hover, .niveles button:focus-visible { border-color: var(--accent-main); }
  .niveles span { color: var(--accent-main); font-size: .67rem; text-transform: uppercase; letter-spacing: .07em; }
  .niveles small, .sin-jerarquia { color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .informes h2 { margin: .15rem 0 .3rem; color: var(--ink-primary); font-size: var(--texto-lg); }
  .informes p { margin: 0; color: var(--ink-secondary); font-size: var(--texto-xs); }
  .sobrelinea { color: var(--accent-main); font-size: .68rem; font-weight: 850; letter-spacing: .08em; }
  .confirmacion { display: flex; align-items: center; gap: .55rem; }
  .confirmacion input { inline-size: 1.15rem; min-block-size: 1.15rem; }
  .acciones-informe { display: flex; gap: .5rem; }
  .aviso-filtros { margin: 0; padding: .7rem .9rem; border-inline-start: 3px solid var(--semantic-warning); background: var(--semantic-warning-bg); color: var(--ink-secondary); font-size: var(--texto-sm); }
  .resultado-informe, .error-informe { grid-column: 1 / -1; margin: 0; padding: .6rem .75rem; border-radius: var(--radius-sm); font-size: var(--texto-sm); }
  .resultado-informe { background: var(--semantic-success-bg); color: var(--semantic-success); }
  .error-informe { background: var(--semantic-error-bg); color: var(--semantic-error); }
  .visor-informe { grid-column: 1 / -1; inline-size: 100%; block-size: min(70vh, 48rem); border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); }
  @media (max-width: 72rem) { .filtros { grid-template-columns: repeat(3, minmax(0, 1fr)); }  .contexto { grid-template-columns: repeat(3, 1fr); }  .informes { grid-template-columns: 1fr 1fr; } .informes > div:first-child { grid-column: 1 / -1; } }
  @media (max-width: 42rem) { .filtros, .informes { grid-template-columns: 1fr; } .contexto { grid-template-columns: 1fr 1fr; } .contexto div { border: 0; } .informes > * { grid-column: 1; } .acciones-informe { flex-wrap: wrap; } .cabecera-drill { align-items: flex-start; flex-direction: column; } .cabecera-drill nav { justify-content: flex-start; } }
</style>
