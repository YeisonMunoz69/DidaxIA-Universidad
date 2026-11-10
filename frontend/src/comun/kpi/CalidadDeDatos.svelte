<script>
  import BotonAyudaTooltip from '../base/BotonAyudaTooltip.svelte';
  let { calidad } = $props();
  const perfiles = $derived(calidad?.perfiles ?? {});
  const telemetria = $derived(calidad?.telemetria ?? {});
  const instrumentos = $derived(calidad?.instrumentos_prototipo ?? null);
  const metricas = $derived(calidad?.metricas ?? {});
  const reglas = $derived(calidad?.reglas ?? {});

  function mostrar(valor, sufijo = '') {
    return valor === null || valor === undefined ? 'Sin observación' : `${valor}${sufijo}`;
  }
</script>

<section class="calidad" aria-label="Calidad de datos">
  <article>
    <span class="sobrelinea">PERFILES</span><h2>Completitud académica</h2>
    <div class="cifras"><p><strong>{mostrar(perfiles.completos)}</strong> completos</p><p><strong>{mostrar(perfiles.incompletos)}</strong> incompletos</p></div>
    <dl>{#each Object.entries(perfiles.faltantes_por_campo ?? {}) as [campo, cantidad]}
      <div><dt>{campo}</dt><dd>{cantidad} sin declarar</dd></div>
    {/each}</dl>
  </article>

  {#if instrumentos}
    <article>
      <span class="sobrelinea">INSTRUMENTO-PROTOTIPO</span><h2>Cobertura de los tres fenómenos <BotonAyudaTooltip tamano="sm" ariaLabel="Cómo interpretar la cobertura de los instrumentos" texto="Estos conteos muestran cuántas oportunidades llegaron a cada regla durante el periodo. No son puntuaciones de ansiedad ni de aprendizaje. Los pasos no forman una cohorte única: sondeo y corrección pueden ocurrir en turnos distintos. Un cero describe oportunidades observadas; un KPI sin denominador permanece sin dato." /></h2>
      <dl>
        <div><dt>Mensajes analizables PS-Anx</dt><dd>{mostrar(instrumentos.mensajes_analizables_ps_anx)}</dd></div>
        <div><dt>Trazas referenciadas</dt><dd>{mostrar(instrumentos.trazas_referenciadas)}</dd></div>
        <div><dt>Trazas legibles</dt><dd>{mostrar(instrumentos.trazas_legibles)}</dd></div>
        <div><dt>Trazas faltantes</dt><dd>{mostrar(instrumentos.trazas_faltantes)}</dd></div>
        <div><dt>Sondeos ofrecidos</dt><dd>{mostrar(instrumentos.sondeos_ofrecidos)}</dd></div>
        <div><dt>Sondeos clasificados</dt><dd>{mostrar(instrumentos.sondeos_clasificados)}</dd></div>
        <div><dt>Intentos matemáticos verificables</dt><dd>{mostrar(instrumentos.intentos_verificables)}</dd></div>
        <div><dt>Correcciones candidatas</dt><dd>{mostrar(instrumentos.correcciones_candidatas)}</dd></div>
        <div><dt>Reintentos observados</dt><dd>{mostrar(instrumentos.reintentos_observados)}</dd></div>
      </dl>
    </article>
  {/if}

  <article>
    <span class="sobrelinea">TELEMETRÍA</span><h2>Cobertura y retrasos</h2>
    <dl>
      <div><dt>Eventos observados</dt><dd>{mostrar(telemetria.eventos)}</dd></div>
      <div><dt>Sin clase</dt><dd>{mostrar(telemetria.sin_clase)}</dd></div>
      <div><dt>Sin concepto</dt><dd>{mostrar(telemetria.sin_concepto)}</dd></div>
      <div><dt>Sin turno</dt><dd>{mostrar(telemetria.sin_turno)}</dd></div>
      <div><dt>Corpus desconocido</dt><dd>{mostrar(telemetria.corpus_desconocido)}</dd></div>
      <div><dt>Modelo desconocido</dt><dd>{mostrar(telemetria.modelo_desconocido)}</dd></div>
      <div><dt>Reintentos duplicados</dt><dd>{mostrar(telemetria.duplicados)}</dd></div>
      <div><dt>Conflictos de idempotencia</dt><dd>{mostrar(telemetria.conflictos_idempotencia)}</dd></div>
      <div><dt>Eventos incompatibles</dt><dd>{mostrar(telemetria.eventos_incompatibles)}</dd></div>
      <div><dt>Retraso mayor a 1 hora</dt><dd>{mostrar(telemetria.retrasados)}</dd></div>
      <div><dt>Retraso p95</dt><dd>{mostrar(telemetria.retraso_p95_segundos, ' s')}</dd></div>
    </dl>
    <p class="nota">{telemetria.tipos_observados?.length ?? 0} de {telemetria.tipos_definidos ?? '—'} tipos definidos tuvieron observaciones en el periodo. Esto describe observación, no disponibilidad del productor.</p>
    <details>
      <summary>Cobertura real por productor</summary>
      <ul class="productores">{#each telemetria.cobertura_por_productor ?? [] as productor (productor.tipo)}
        <li><span>{productor.tipo}</span><strong>{productor.eventos}</strong><small>{productor.productor}</small></li>
      {/each}</ul>
    </details>
    {#if telemetria.periodos_observacion_baja?.length}
      <p class="nota"><strong>Observación baja:</strong> {telemetria.periodos_observacion_baja.map((item) => `${item.fecha} (${item.eventos})`).join(', ')}.</p>
    {/if}
  </article>

  <article>
    <span class="sobrelinea">PUBLICACIÓN</span><h2>Estados del catálogo</h2>
    <dl>{#each Object.entries(metricas.por_estado ?? {}) as [estado, cantidad]}
      <div><dt>{estado.replaceAll('_', ' ')}</dt><dd>{cantidad}</dd></div>
    {/each}</dl>
    <p class="nota">{mostrar(metricas.no_calculables)} indicadores no publican valor en este corte. El tablero y los PDF muestran sólo resultados calculados; los estados pendientes permanecen en el catálogo.</p>
  </article>

  <article class="reglas">
    <span class="sobrelinea">REGLAS ACTIVAS</span><h2>Protecciones metodológicas</h2>
    <ul>
      <li>No se divide por cero.</li>
      <li>Una ausencia nunca se representa con un cero simulado.</li>
      <li>Cada indicador aplica su muestra mínima declarada.</li>
      <li>Los periodos se interpretan en America/Bogota.</li>
      <li>Las métricas conductuales no se presentan como diagnósticos clínicos.</li>
      <li>Un trámite de supresión abierto bloquea la consulta del actor y la eliminación personal se ejecuta por sujeto.</li>
      <li>{reglas.supresion?.motivo_sin_supresion_de_celdas ?? 'La política de supresión de celdas no está definida.'}</li>
    </ul>
  </article>
</section>

<style>
  .calidad { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem; }
  article { min-inline-size: 0; padding: 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); box-shadow: var(--shadow-soft); }
  .sobrelinea { color: var(--accent-main); font-size: .68rem; font-weight: 850; letter-spacing: .08em; }
  h2 { margin: .2rem 0 .8rem; color: var(--ink-primary); font-size: var(--texto-base); }
  .cifras { display: flex; gap: .6rem; margin-block-end: .6rem; }
  .cifras p { flex: 1; margin: 0; padding: .6rem; border-radius: var(--radius-xs); background: var(--surface-panel); color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .cifras strong { display: block; color: var(--ink-primary); font-size: var(--texto-lg); }
  dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .4rem; margin: 0; }
  dl div { min-inline-size: 0; padding: .5rem; border-radius: var(--radius-xs); background: var(--surface-panel); }
  dt { overflow-wrap: anywhere; color: var(--ink-tertiary); font-size: .68rem; text-transform: capitalize; }
  dd { margin: .2rem 0 0; color: var(--ink-primary); font-size: var(--texto-sm); font-weight: 750; font-variant-numeric: tabular-nums; }
  .nota, li { color: var(--ink-secondary); font-size: var(--texto-xs); line-height: 1.55; }
  details { margin-block-start: .7rem; }
  summary { color: var(--ink-primary); font-size: var(--texto-xs); font-weight: 800; cursor: pointer; }
  .productores { display: grid; gap: .25rem; max-block-size: 15rem; overflow: auto; margin: .55rem 0 0; padding: 0; list-style: none; }
  .productores li { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: .5rem; padding: .35rem .45rem; border-radius: var(--radius-xs); background: var(--surface-panel); }
  .productores span { overflow-wrap: anywhere; }
  .productores small { color: var(--ink-tertiary); }
  .reglas ul { margin: 0; padding-inline-start: 1.2rem; }
  @media (max-width: 48rem) { .calidad { grid-template-columns: 1fr; } }
  @media (max-width: 28rem) { dl { grid-template-columns: 1fr; } }
</style>
