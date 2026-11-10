<script>
  import * as api from '../../nucleo/api/clases.js';
  import { descargarPDF } from '../../nucleo/descargas/pdf.js';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import SelectorFecha from '../../comun/base/SelectorFecha.svelte';

  let { clase = '', rol = 'docente' } = $props();

  const opciones = [
    ['matriculados', 'Matriculados'], ['activos', 'Con actividad'],
    ['adopcion', 'Porcentaje con actividad'], ['turnos', 'Turnos elegibles'],
    ['conversaciones', 'Conversaciones'], ['mediana_turnos', 'Mediana de turnos'],
    ['turnos_por_activo', 'Turnos por estudiante activo'],
    ['respuestas_con_fuente', 'Respuestas no degradadas con fuente'],
    ['proporcion_con_fuente', 'Porcentaje de respuestas no degradadas con fuente']
  ];
  const opcionesKPI = [
    ['adopcion.activacion', 'Activación'],
    ['adopcion.actividad_semanal', 'Actividad semanal'],
    ['adopcion.retorno_7d', 'Retorno a 7 días'],
    ['adopcion.dias_activos_por_estudiante', 'Días activos por estudiante'],
    ['adopcion.profundidad_conversacion', 'Profundidad de conversación'],
    ['recuperacion.cobertura', 'Cobertura de recuperación'],
    ['recuperacion.tasa_sin_fuente', 'Tasa sin fuente'],
    ['recuperacion.referencias_conceptuales', 'Respuestas con referencia conceptual'],
    ['conductual.continuacion_observable', 'Continuación conversacional en 24 h'],
    ['conductual.abandono_de_conversacion', 'Sin retorno al hilo en 7 días']
  ];

  function horaBogota(instante) {
    const partes = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
    }).formatToParts(instante);
    const valor = (tipo) => partes.find((parte) => parte.type === tipo)?.value;
    return `${valor('year')}-${valor('month')}-${valor('day')}T${valor('hour')}:${valor('minute')}:${valor('second')}`;
  }

  let desde = $state(horaBogota(new Date(Date.now() - 7 * 86400000)));
  let hasta = $state(horaBogota(new Date()));
  let seleccion = $state(['matriculados', 'activos', 'adopcion', 'turnos', 'conversaciones', 'respuestas_con_fuente']);
  let seleccionKPI = $state([]);
  let incluirIA = $state(false);
  let datos = $state(null);
  let error = $state('');
  let ocupada = $state('');

  $effect(() => { void clase; datos = null; error = ''; });

  function alternar(codigo) {
    seleccion = seleccion.includes(codigo)
      ? seleccion.filter((item) => item !== codigo)
      : [...seleccion, codigo];
    datos = null;
  }

  function alternarKPI(codigo) {
    seleccionKPI = seleccionKPI.includes(codigo)
      ? seleccionKPI.filter((item) => item !== codigo)
      : [...seleccionKPI, codigo];
    datos = null;
  }

  function filtros() {
    if (!desde || !hasta || hasta <= desde) throw new Error('La hora final debe ser posterior a la inicial.');
    if (!seleccion.length) throw new Error('Elige al menos una métrica.');
    return {
      desde: `${desde}-05:00`, hasta: `${hasta}-05:00`,
      metricas: opciones.map(([codigo]) => codigo).filter((codigo) => seleccion.includes(codigo)),
      kpis: opcionesKPI.map(([codigo]) => codigo).filter((codigo) => seleccionKPI.includes(codigo)),
      incluirIA: rol === 'investigador' && incluirIA
    };
  }

  function mensaje(errorRecibido, respaldo) {
    if (errorRecibido?.detalle) return errorRecibido.detalle;
    if (errorRecibido?.name === 'Error') return errorRecibido.message;
    return describir(errorRecibido)?.mensaje ?? respaldo;
  }

  async function consultar() {
    error = ''; datos = null; ocupada = 'consulta';
    try { datos = await api.reporteDeSesion(clase, rol, filtros()); }
    catch (e) { error = mensaje(e, 'No se pudo consultar el reporte.'); }
    finally { ocupada = ''; }
  }

  async function descargar() {
    if (!await confirmarAccion({ tipo:'descarga', titulo:'¿Descargar reporte de sesión?',
      descripcion:'Se generará un PDF con el periodo, las métricas y los KPI seleccionados de esta clase.', confirmar:'Descargar PDF' })) return;
    error = ''; ocupada = 'pdf';
    try {
      const documento = await api.pdfDeSesion(clase, rol, filtros());
      descargarPDF(documento, `didaxia-sesion-${clase}-${desde}-${hasta}.pdf`);
      toast.descarga('Descargando reporte de sesión en PDF.');
    } catch (e) { error = mensaje(e, 'No se pudo descargar el PDF.'); }
    finally { ocupada = ''; }
  }
</script>

<section class="reporte" aria-labelledby="reporte-titulo">
  <header>
    <h3 id="reporte-titulo">Reporte de sesión por clase</h3>
    <p>Elige un intervalo con hora de Bogotá y las métricas que quieres ver o exportar. El final del intervalo es exclusivo.</p>
  </header>
  <div class="fechas">
    <SelectorFecha etiqueta="Desde" conHora bind:value={desde} maximo={horaBogota(new Date())} alCambiar={() => (datos = null)} />
    <SelectorFecha etiqueta="Hasta exclusivo" conHora bind:value={hasta} minimo={desde} maximo={horaBogota(new Date())} exclusivo alCambiar={() => (datos = null)} />
  </div>
  <fieldset>
    <legend>Métricas del reporte</legend>
    <div class="opciones">
      {#each opciones as [codigo, nombre]}
        <label><input type="checkbox" checked={seleccion.includes(codigo)} onchange={() => alternar(codigo)} /> {nombre}</label>
      {/each}
    </div>
  </fieldset>
  {#if rol === 'investigador'}
    <fieldset>
      <legend>Referencia operativa opcional</legend>
      <label class="referencia-ia"><input type="checkbox" bind:checked={incluirIA} onchange={() => (datos = null)} />
        Incluir llamadas y costo API estimado de DeepSeek durante este intervalo
      </label>
      <p class="ayuda-kpi">Es el total institucional del mismo intervalo, no una cifra de esta clase o de sus estudiantes.</p>
    </fieldset>
  {/if}
  <fieldset>
    <legend>KPI oficiales opcionales</legend>
    <p class="ayuda-kpi">Conservan su definición y estado de calidad propios; una muestra insuficiente se muestra sin cifra.</p>
    <div class="opciones">
      {#each opcionesKPI as [codigo, nombre]}
        <label><input type="checkbox" checked={seleccionKPI.includes(codigo)} onchange={() => alternarKPI(codigo)} /> {nombre}</label>
      {/each}
    </div>
  </fieldset>
  <div class="acciones">
    <button type="button" onclick={consultar} disabled={!!ocupada}> {ocupada === 'consulta' ? 'Consultando…' : 'Ver métricas'} </button>
    <button type="button" class="secundario" onclick={descargar} disabled={!!ocupada}>{ocupada === 'pdf' ? 'Generando…' : 'Descargar PDF'}</button>
  </div>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
  {#if datos}
    <p class="sello">{datos.clase.nombre} · {datos.periodo.desde} a {datos.periodo.hasta_exclusivo} · Generado {datos.generado_en}</p>
    <div class="metricas">
      {#each datos.metricas as metrica}
        <article><span>{metrica.nombre}</span><strong>{metrica.valor ?? 'Sin dato'}{['adopcion', 'proporcion_con_fuente'].includes(metrica.codigo) && metrica.valor != null ? '%' : ''}</strong></article>
      {/each}
    </div>
    {#if datos.kpi_oficiales.length}
      <h4>KPI oficiales seleccionados</h4>
      <div class="metricas">
        {#each datos.kpi_oficiales as indicador}
          <article><span>{indicador.nombre} · {indicador.estado.replaceAll('_', ' ')}</span>
            <strong>{indicador.valor == null ? 'Sin cifra' : indicador.unidad === 'proporcion' ? `${(indicador.valor * 100).toFixed(1)}%` : indicador.valor}</strong>
          </article>
        {/each}
      </div>
    {/if}
    {#if datos.referencia_ia}
      <h4>DeepSeek · referencia institucional del intervalo</h4>
      <p class="metodo">No atribuible a esta clase. El costo es una estimación, no una factura.</p>
      <div class="metricas">
        <article><span>Llamadas</span><strong>{datos.referencia_ia.totales.llamadas}</strong></article>
        <article><span>Tokens de entrada medidos</span><strong>{datos.referencia_ia.totales.entrada_total ?? 'Sin dato'}</strong></article>
        <article><span>Tokens de salida medidos</span><strong>{datos.referencia_ia.totales.salida ?? 'Sin dato'}</strong></article>
        <article><span>Costo API estimado USD</span><strong>{datos.referencia_ia.costos.estimado_usd ?? 'No calculable íntegramente'}</strong></article>
      </div>
    {/if}
    <h4>Actividad seudonimizada</h4>
    <div class="tabla"><table>
      <thead><tr><th>Alias</th><th>Turnos</th><th>Conversaciones</th><th>Última actividad</th></tr></thead>
      <tbody>{#each datos.estudiantes as estudiante}
        <tr><td>{estudiante.alias}</td><td>{estudiante.turnos}</td><td>{estudiante.conversaciones}</td><td>{estudiante.ultima_actividad ?? 'Sin actividad'}</td></tr>
      {/each}</tbody>
    </table></div>
    <p class="metodo">{datos.metodo}</p>
    {#each datos.limitaciones as limitacion}<p class="limite">{limitacion}</p>{/each}
  {/if}
</section>

<style>
  .reporte { display: grid; gap: 1rem; padding: 1.2rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); }
  header h3, h4 { margin: 0; color: var(--ink-primary); }
  header p, .metodo, .limite { margin: .35rem 0 0; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .fechas, .opciones, .metricas { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; }
  label { display: grid; gap: .25rem; color: var(--ink-secondary); font-size: var(--texto-sm); font-weight: 650; }
  fieldset { border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); }
  legend { font-weight: 750; }
  .opciones label { display: flex; align-items: flex-start; gap: .4rem; font-weight: 500; }
  .referencia-ia { display: flex; align-items: flex-start; gap: .4rem; font-weight: 500; }
  .acciones { display: flex; flex-wrap: wrap; gap: .6rem; }
  button { min-block-size: 2.5rem; padding: .5rem .8rem; border: 1px solid transparent; border-radius: var(--radius-sm); background: var(--accent-main); color: var(--accent-on-main); font: inherit; font-weight: 750; cursor: pointer; }
  button.secundario { border-color: var(--accent-main); background: var(--surface-paper); color: var(--accent-main); }
  button:disabled { opacity: .6; cursor: wait; }
  .metricas article { display: grid; gap: .35rem; padding: .8rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); }
  .metricas strong { font-size: var(--texto-lg); color: var(--ink-primary); }
  .metricas span, .sello { font-size: var(--texto-sm); color: var(--ink-secondary); }
  .tabla { overflow-x: auto; }
  table { inline-size: 100%; border-collapse: collapse; font-size: var(--texto-sm); }
  th, td { padding: .5rem; border-block-end: 1px solid var(--trazo-suave); text-align: left; }
  .error { margin: 0; color: var(--semantic-error); }
  .ayuda-kpi { margin: .15rem 0 .7rem; color: var(--ink-tertiary); font-size: var(--texto-sm); }
  @media (max-width: 48rem) { .fechas, .opciones, .metricas { grid-template-columns: 1fr; } }
</style>
