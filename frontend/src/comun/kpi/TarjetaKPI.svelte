<script>
  import BotonExplicacion from '../base/BotonExplicacion.svelte';
  import BotonAyudaTooltip from '../base/BotonAyudaTooltip.svelte';
  import Dialogo from '../base/Dialogo.svelte';
  import MetodologiaKPI from './MetodologiaKPI.svelte';
  import { describirPeriodo } from './periodo.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { confirmarAccion } from '../estado/confirmaciones.svelte.js';
  import { toast } from '../estado/toasts.svelte.js';
  import { esFenomenoAnteproyecto } from './visibilidad.js';

  let { indicador, alDescargarPDF = null, descargasHabilitadas = true, principal = '' } = $props();
  let explicacionAbierta = $state(false);
  let descargando = $state(false);
  let resultadoDescarga = $state('');
  let errorDescarga = $state('');

  const ESTADOS = Object.freeze({
    disponible: ['Disponible', 'disponible'],
    sin_datos: ['Sin datos', 'neutro'],
    no_instrumentado: ['No instrumentado', 'pendiente'],
    muestra_insuficiente: ['Muestra insuficiente', 'advertencia'],
    datos_incompletos: ['Datos incompletos', 'advertencia'],
    calculo_no_aplicable: ['No aplicable', 'neutro'],
    error_de_calidad: ['Error de calidad', 'error']
  });

  const estado = $derived.by(() => {
    if (indicador?.estado === 'disponible' && indicador?.madurez_metodologica === 'experimental') {
      return ['Experimental', 'advertencia'];
    }
    if (indicador?.madurez_metodologica === 'en_calibracion') {
      return ['En calibración', 'advertencia'];
    }
    if (indicador?.madurez_metodologica === 'proximo') {
      return ['Próximamente', 'pendiente'];
    }
    if (indicador?.madurez_metodologica === 'excluido') {
      return ['Excluido', 'neutro'];
    }
    return ESTADOS[indicador?.estado] ?? ['Estado desconocido', 'error'];
  });
  const valor = $derived(formatearValor(indicador));

  function formatearValor(item) {
    if (item?.estado !== 'disponible' || !Number.isFinite(item?.valor)) return '—';
    if (item.unidad === 'proporcion') {
      return new Intl.NumberFormat('es-CO', {
        style: 'percent', maximumFractionDigits: 1
      }).format(item.valor);
    }
    const numero = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 }).format(item.valor);
    return item.codigo === 'conductual.observable_cambio_ayuda' ? `${numero} pp` : numero;
  }

  async function descargarFicha() {
    if (!alDescargarPDF || descargando || !descargasHabilitadas) return;
    if (!await confirmarAccion({ tipo:'descarga', titulo:`¿Descargar ficha de ${indicador.nombre}?`,
      descripcion:'Se generará un PDF del indicador con el periodo, la muestra y la explicación de su cálculo.', confirmar:'Descargar PDF' })) return;
    descargando = true;
    resultadoDescarga = '';
    errorDescarga = '';
    try {
      resultadoDescarga = await alDescargarPDF(indicador) || `Se descargó ${indicador.codigo}.`;
      toast.descarga(resultadoDescarga);
    } catch (error) {
      const descripcion = describir(error);
      errorDescarga = error?.message && error.name !== 'FalloDeRed'
        ? error.message
        : descripcion.explicacion;
    } finally {
      descargando = false;
    }
  }
</script>

<article class="tarjeta" class:principal={Boolean(principal)} data-factor={principal || undefined} data-estado={indicador.estado}>
  {#if principal}
    <svg class="trazo-factor" viewBox="0 0 300 100" fill="none" aria-hidden="true"><path d="M-10 80 C45 80 45 18 100 28 S150 94 210 48 S265 14 320 38" /></svg>
  {/if}
  <header>
    <span class="estado {estado[1]}">{estado[0]}</span>
    <BotonExplicacion etiqueta={`Explicar ${indicador.nombre}`} abierto={explicacionAbierta}
      texto={[indicador.interpretacion, indicador.detalle?.motivo_cobertura, 'Abre la explicación completa para consultar cálculo, fuentes y límites.'].filter(Boolean).join(' ')}
      alAbrir={() => explicacionAbierta = true} />
  </header>
  {#if principal}<span class="rotulo-factor">FACTOR DEL ESTUDIO · {indicador.codigo.includes('hibrido') || indicador.codigo === 'aprendizaje.preconcepciones_dialogo' ? 'LECTURA HÍBRIDA' : 'INSTRUMENTO ORIGINAL'}</span>{/if}
  <h3>{indicador.nombre}</h3>
  <strong class="valor">{valor}</strong>
  <p class="conteo">{#if indicador.unidad === 'proporcion' && indicador.numerador != null && indicador.denominador != null}{indicador.numerador} de {indicador.denominador} oportunidades{:else}Muestra: {indicador.muestra ?? 'sin registro'}{/if}</p>
  {#if indicador.estado !== 'disponible'}<span class="sin-valor">{indicador.estado === 'muestra_insuficiente' ? 'Aún no alcanza la muestra mínima' : 'Sin valor publicable en este periodo'}</span>{/if}
  {#if alDescargarPDF}
    <button class="descargar-ficha" type="button" onclick={descargarFicha}
      disabled={descargando || !descargasHabilitadas}
      aria-label={`Descargar ficha PDF de ${indicador.nombre}`}>
      {descargando ? 'Preparando ficha…' : 'Descargar ficha PDF'}
    </button>
    {#if errorDescarga}<p class="error-descarga" role="alert">{errorDescarga}</p>{/if}
  {/if}
</article>

<Dialogo bind:abierto={explicacionAbierta} titulo={indicador.nombre} ancho="48rem">
  <div class="ficha">
    <p><span class="estado {estado[1]}">{estado[0]}</span> <code>{indicador.codigo}</code></p>
    <section><h4>Resultado observado</h4><strong class="valor">{valor}</strong><dl class="muestra"><div><dt>Numerador</dt><dd>{indicador.numerador ?? 'Sin registro'}</dd></div><div><dt>Denominador</dt><dd>{indicador.denominador ?? 'Sin registro'}</dd></div><div><dt>Muestra</dt><dd>{indicador.muestra ?? 'Sin registro'}</dd></div></dl></section>
    <section><h4>Qué mide</h4><p>{indicador.definicion_operacional}</p></section>
    <MetodologiaKPI metodologia={indicador.metodologia} />
    <div class="formula">
      <section><h4>Numerador</h4><p>{indicador.definicion_numerador ?? indicador.numerador}</p></section>
      <section><h4>Denominador</h4><p>{indicador.definicion_denominador ?? indicador.denominador}</p></section>
    </div>
    <section><h4>Unidad, muestra y faltantes <BotonAyudaTooltip tamano="sm" texto="La muestra es el número de observaciones elegibles. Los faltantes no se interpretan como cero y pueden limitar las conclusiones." /></h4><p>{indicador.unidad} · Muestra: {indicador.muestra ?? 'sin observaciones'} · Mínimo de publicación: {indicador.muestra_minima ?? 'no declarado'} · Faltantes registrados: {indicador.faltantes ?? 'no declarados'}.</p>
      {#if indicador.detalle?.censuradas != null}<p>Conversaciones con seguimiento truncado: {indicador.detalle.censuradas}. No entran en el denominador.</p>{/if}
      {#if indicador.detalle?.trazas_faltantes}<p>Turnos con traza no legible, excluidos del cálculo: {indicador.detalle.trazas_faltantes}.</p>{/if}
      {#if indicador.detalle?.por_concepcion && Object.keys(indicador.detalle.por_concepcion).length}<p>Etiquetas observadas: {Object.entries(indicador.detalle.por_concepcion).map(([codigo, cantidad]) => `${codigo}: ${cantidad}`).join(' · ')}.</p>{/if}
    </section>
    <section><h4>Población elegible</h4><p>{indicador.poblacion_elegible}</p></section>
    <section><h4>Cómo interpretarlo</h4><p>{indicador.interpretacion}</p>
      {#if indicador.detalle?.motivo_cobertura}<p>{indicador.detalle.motivo_cobertura}</p>{/if}
      {#if indicador.detalle?.formatos && Object.keys(indicador.detalle.formatos).length}<p>Formatos pedidos: {Object.entries(indicador.detalle.formatos).map(([nombre, cantidad]) => `${nombre}: ${cantidad}`).join(' · ')}. Se permiten varias peticiones en un mensaje.</p>{/if}
      {#if indicador.detalle?.por_concepto && Object.keys(indicador.detalle.por_concepto).length}<ul>{#each Object.entries(indicador.detalle.por_concepto) as [codigo, dato]}<li>{dato.nombre}: {dato.mensajes} mensajes ({codigo}).</li>{/each}</ul>{/if}
    </section>
    <section><h4>Periodo y filtros</h4>
      <p>{describirPeriodo(indicador.periodo)}</p>
      {#each Object.entries(indicador.filtros ?? {}) as [nombre, filtro]}<p>{nombre.replaceAll('_', ' ')}: {filtro || 'Sin restricción'}</p>{:else}<p>Sin filtros adicionales.</p>{/each}
    </section>
    <section><h4>Fuentes</h4><p>{indicador.fuentes?.join(', ') || 'Sin fuente instrumentada'}</p></section>
    <section><h4>Clasificación <BotonAyudaTooltip tamano="sm" texto="El estado técnico indica si se pudo calcular. La madurez metodológica indica hasta dónde puede interpretarse la medida." /></h4><p>Estado técnico: {indicador.estado_tecnico ?? 'no declarado'} · Madurez metodológica: {indicador.madurez_metodologica ?? 'no declarada'}.</p></section>
    {#if indicador.advertencias?.length}
      <section><h4>Advertencias de calidad</h4><ul>{#each indicador.advertencias as aviso}<li>{aviso}</li>{/each}</ul></section>
    {/if}
    <section><h4>Limitaciones</h4>
      {#if indicador.limitaciones?.length}<ul>{#each indicador.limitaciones as limite}<li>{limite}</li>{/each}</ul>
      {:else}<p>No se declararon limitaciones adicionales.</p>{/if}
    </section>
    {#if alDescargarPDF}
      <button class="descargar-ficha" type="button" onclick={descargarFicha}
        disabled={descargando || !descargasHabilitadas}
        aria-label={`Descargar ficha PDF de ${indicador.nombre} desde su explicación`}>
        {descargando ? 'Preparando ficha…' : 'Descargar ficha PDF'}
      </button>
      {#if errorDescarga}<p class="error-descarga" role="alert">{errorDescarga}</p>{/if}
    {/if}
    <footer>Catálogo {indicador.version_catalogo} · definición {indicador.version_definiciones} · interpretación {indicador.version_interpretacion}</footer>
  </div>
</Dialogo>

<style>
  .tarjeta { display: grid; align-content: start; gap: .55rem; min-inline-size: 0; padding: 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); box-shadow: var(--shadow-soft); }
  .tarjeta[data-estado='error_de_calidad'] { border-color: var(--semantic-error); }
  header { display: flex; justify-content: space-between; align-items: center; gap: .6rem; }
  .estado { display: inline-flex; inline-size: fit-content; padding: .22rem .5rem; border-radius: 999px; background: var(--surface-panel); color: var(--ink-secondary); font-size: .68rem; font-weight: 800; letter-spacing: .03em; text-transform: uppercase; }
  .estado.disponible { background: var(--semantic-success-bg); color: var(--semantic-success); }
  .estado.pendiente, .estado.advertencia { background: var(--semantic-warning-bg); color: var(--semantic-warning); }
  .estado.error { background: var(--semantic-error-bg); color: var(--semantic-error); }
  .ficha code { margin: 0; overflow-wrap: anywhere; color: var(--ink-tertiary); font-size: .7rem; }
  h3 { margin: 0; color: var(--ink-primary); font-size: var(--texto-base); line-height: 1.25; }
  .valor { color: var(--accent-main); font-size: clamp(1.6rem, 4vw, 2.35rem); line-height: 1; font-variant-numeric: tabular-nums; }
  .muestra { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .35rem; margin: .2rem 0 0; }
  .muestra div { min-inline-size: 0; padding: .4rem; border-radius: var(--radius-xs); background: var(--surface-panel); }
  dt { color: var(--ink-tertiary); font-size: .62rem; text-transform: uppercase; }
  dd { margin: .15rem 0 0; overflow-wrap: anywhere; color: var(--ink-primary); font-size: var(--texto-xs); font-weight: 750; }
  .ficha { display: grid; gap: 1rem; max-block-size: min(70vh, 42rem); overflow-y: auto; padding-inline-end: .25rem; }
  .ficha p, .ficha ul { margin: .25rem 0 0; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.55; }
  .ficha h4 { margin: 0; color: var(--ink-primary); font-size: var(--texto-sm); }
  .formula { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; }
  .ficha section { min-inline-size: 0; padding: .75rem; border-radius: var(--radius-sm); background: var(--surface-panel); }
  .ficha footer { color: var(--ink-tertiary); font-size: .7rem; }
  .descargar-ficha { min-block-size: 44px; padding: .55rem .75rem; border: 1px solid var(--accent-main); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--accent-main); font: inherit; font-size: var(--texto-xs); font-weight: 800; cursor: pointer; }
  .descargar-ficha:hover, .descargar-ficha:focus-visible { background: var(--accent-surface); }
  .descargar-ficha:disabled { opacity: .55; cursor: wait; }
  .resultado-descarga, .error-descarga { margin: 0; padding: .45rem .55rem; border-radius: var(--radius-xs); font-size: var(--texto-xs); }
  .resultado-descarga { background: var(--semantic-success-bg); color: var(--semantic-success); }
  .error-descarga { background: var(--semantic-error-bg); color: var(--semantic-error); }
  @media (max-width: 34rem) { .formula { grid-template-columns: 1fr; } }
  .tarjeta { position: relative; isolation: isolate; }
  .tarjeta > :not(.trazo-factor) { position: relative; }
  .conteo, .sin-valor { margin: 0; color: var(--ink-tertiary); font-size: var(--texto-xs); line-height: 1.5; }
  .principal { --factor-color: var(--accent-light); border-color: color-mix(in srgb, var(--factor-color) 45%, var(--trazo-suave)); background: linear-gradient(140deg, color-mix(in srgb, var(--factor-color) 9%, var(--surface-paper)), var(--surface-paper) 70%); padding: 1.15rem; box-shadow: 0 6px 20px color-mix(in srgb, var(--factor-color) 9%, transparent); }
  .principal[data-factor='tension'] { --factor-color: var(--accent-light); }
  .principal[data-factor='concepciones'] { --factor-color: var(--help-color); }
  .principal[data-factor='reiteracion'] { --factor-color: var(--semantic-success); }
  .principal .valor { font-size: clamp(2.3rem, 4vw, 3rem); }
  .rotulo-factor { color: var(--ink-secondary); font-size: .6rem; letter-spacing: .05em; font-weight: 800; }
  .trazo-factor { position: absolute; inline-size: 100%; block-size: 100px; inset: auto 0 22%; z-index: -1; opacity: .2; pointer-events: none; }
  .trazo-factor path { stroke: var(--factor-color); stroke-width: 2; stroke-dasharray: 80 30; animation: flujo-factor 20s linear infinite; }
  @keyframes flujo-factor { to { stroke-dashoffset: -440; } }
  @media (prefers-reduced-motion: reduce) { .trazo-factor path { animation: none; } }
</style>
