<script>
  import { onMount, onDestroy } from 'svelte';
  import { pedir } from '../../nucleo/api/cliente.js';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  let { cursos = [], alActualizar = () => {} } = $props();
  const base = '/investigacion/factores/relectura';
  let clase = $state('');
  let periodo = $state('historial');
  let desde = $state('');
  let hasta = $state('');
  let maximo = $state(10);
  let vista = $state(null);
  let trabajo = $state(null);
  let ocupado = $state(false);
  let consultando = $state(false);
  let error = $state('');
  let reloj;
  let desmontado = false;
  const control = new AbortController();
  const activo = $derived(['en_cola', 'en_curso'].includes(trabajo?.estado));
  const bloqueado = $derived(ocupado || activo);
  const estados = { en_cola: 'Lote confirmado', en_curso: 'Analizando conversaciones',
    completado: 'Lote terminado', interrumpido: 'Lote interrumpido' };
  const tituloEstado = $derived(trabajo?.estado === 'interrumpido'
    && trabajo?.resumen?.llamadas_finalizadas >= trabajo?.resumen?.objetivo_llamadas
    ? 'Lote terminado con lecturas pendientes' : estados[trabajo?.estado]);
  const objetivo = $derived(trabajo?.resumen?.objetivo_llamadas ?? Math.min(
    trabajo?.maximo_llamadas ?? 0, trabajo?.resumen?.pendientes_iniciales ?? trabajo?.resumen?.pendientes ?? trabajo?.maximo_llamadas ?? 0));
  const finalizadas = $derived(trabajo?.resumen?.llamadas_finalizadas ?? Math.max(0,
    (trabajo?.resumen?.llamadas ?? 0) - (activo ? 1 : 0)));
  const porcentaje = $derived(objetivo > 0 ? Math.min(100, Math.round(finalizadas / objetivo * 100)) : 0);
  const recorridoTerminado = $derived(!activo && objetivo > 0 && finalizadas >= objetivo);
  const motivos = {
    plazo_proveedor: 'DeepSeek no respondió dentro del tiempo disponible para una lectura.',
    conexion_proveedor: 'No se pudo conectar con DeepSeek.',
    limite_proveedor: 'DeepSeek rechazó la llamada por un límite de uso o solicitudes.',
    credencial_proveedor: 'DeepSeek rechazó las credenciales configuradas en el servidor.',
    configuracion_proveedor: 'Falta la configuración de DeepSeek en el servidor.',
    proveedor_no_disponible: 'DeepSeek devolvió un error y no se guardó esa lectura.',
    salida_truncada: 'DeepSeek devolvió una respuesta incompleta.',
    salida_proveedor_invalida: 'DeepSeek no devolvió el formato de respuesta esperado.',
    salida_semantica_invalida: 'La interpretación de DeepSeek no pasó la validación del formato o de la evidencia.',
    salida_conductual_invalida: 'La lectura de los tres factores no pasó la validación de la rúbrica o de sus citas.',
    proveedor_sin_lectura: 'No se obtuvo una lectura válida del proveedor.',
    ejecucion_interrumpida: 'La ejecución se interrumpió. Puede deberse a un reinicio o a un error interno.'
  };
  const rechazos = {
    cita_no_literal_o_extensa: 'La cita no pertenece al mensaje actual o supera 240 caracteres',
    factores_incompletos: 'No se recibieron los tres factores',
    factores_repetidos: 'Los factores están repetidos o falta alguno',
    factor_desconocido: 'Se recibió un factor fuera de la rúbrica',
    estado_oportunidad_invalida: 'El estado o la oportunidad tienen formato inválido',
    motivo_invalido: 'La explicación está vacía o supera el límite',
    deteccion_sin_oportunidad: 'Se declaró una detección sin oportunidad',
    estructura_invalida: 'La lectura tiene una estructura inválida'
  };

  function fallo(e) {
    error = e?.cuerpo?.detalle || e?.message || 'No se pudo consultar el análisis. Intenta de nuevo.';
  }
  function intervalo(datos) {
    const fecha = valor => new Intl.DateTimeFormat('es-CO', { timeZone: 'America/Bogota', dateStyle: 'medium', timeStyle: 'short' }).format(new Date(valor));
    const inicio = datos?.desde?.startsWith('1970-01-01') ? 'Inicio del historial disponible' : datos?.desde ? fecha(datos.desde) : '';
    return inicio && datos?.hasta ? `${inicio} → ${fecha(datos.hasta)} (fin excluido)` : 'Corte de la consulta';
  }
  function alcance() {
    if (periodo === 'periodo' && (!desde || !hasta || desde >= hasta)) {
      throw new Error('Elige una fecha inicial y una fecha final posterior. La final queda fuera del intervalo.');
    }
    return { clase: clase || null, ...(periodo === 'periodo'
      ? { desde: `${desde}T00:00:00-05:00`, hasta: `${hasta}T00:00:00-05:00` } : {}) };
  }
  async function consultarPendientes() {
    if (bloqueado) return;
    ocupado = true; error = ''; vista = null;
    try { vista = await pedir(`${base}/vista-previa`, { metodo: 'POST', cuerpo: alcance(), señal: control.signal }); }
    catch (e) { if (!desmontado) fallo(e); }
    finally { ocupado = false; }
  }
  async function ejecutarLote() {
    if (bloqueado || !vista || !vista.resumen.pendientes) return;
    const previa = vista;
    const presupuesto = Number(maximo);
    if (!Number.isInteger(presupuesto) || presupuesto < 1 || presupuesto > 200) {
      error = 'Elige un máximo entre 1 y 200 llamadas.'; return;
    }
    ocupado = true; error = '';
    try {
      const nombre = previa.clase ? cursos.find(c => c.id === previa.clase)?.nombre || 'Curso seleccionado' : 'Todos los cursos';
      if (!await confirmarAccion({ titulo: '¿Analizar el historial pendiente?', confirmar: 'Analizar lote', cancelar: 'Cancelar',
        descripcion: `${nombre}. ${intervalo(previa)}. Hay ${previa.resumen.pendientes} turnos pendientes. Se usarán como máximo ${presupuesto} llamadas a DeepSeek, con consumo de créditos. Se guardarán lecturas complementarias para actualizar KPI, perfiles e informes. Las lecturas válidas de esta versión se reutilizan. Los demás pendientes requieren otro lote confirmado.` })) return;
      if (desmontado) return;
      trabajo = await pedir(`${base}/trabajos/${previa.id}`, { metodo: 'POST',
        cuerpo: { confirmar: true, maximo_llamadas: presupuesto }, señal: control.signal });
      vista = null;
      programar();
    } catch (e) { if (!desmontado) fallo(e); }
    finally { ocupado = false; }
  }
  function programar() {
    clearTimeout(reloj);
    if (!desmontado && ['en_cola', 'en_curso'].includes(trabajo?.estado)) reloj = setTimeout(consultarAvance, 3000);
  }
  async function consultarAvance() {
    if (!trabajo || desmontado || consultando) return;
    error = ''; consultando = true;
    try {
      trabajo = await pedir(`${base}/trabajos/${trabajo.id}`, { señal: control.signal });
      if (!['en_cola', 'en_curso'].includes(trabajo.estado)) await alActualizar();
    } catch (e) { if (!desmontado) fallo(e); }
    finally { consultando = false; programar(); }
  }
  onMount(async () => {
    try {
      const respuesta = await pedir(`${base}/ultimo`, { señal: control.signal });
      if (!desmontado) { trabajo = respuesta.trabajo; programar(); }
    } catch (e) { if (!desmontado) fallo(e); }
  });
  onDestroy(() => { desmontado = true; control.abort(); clearTimeout(reloj); });
</script>

<details class="relectura">
  <summary>Actualizar análisis histórico de los tres factores</summary>
  <div class="contenido">
    <p>Consulta cuántos turnos aún necesitan lectura semántica. Elige el alcance de este análisis; es independiente de los filtros del tablero.</p>
    <div class="controles">
      <label>Curso<select bind:value={clase} disabled={bloqueado} onchange={() => vista = null}>
        <option value="">Todos los cursos</option>
        {#each cursos as curso (curso.id)}<option value={curso.id}>{curso.nombre}</option>{/each}
      </select></label>
      <label>Historial<select bind:value={periodo} disabled={bloqueado} onchange={() => vista = null}>
        <option value="historial">Todo el historial disponible</option><option value="periodo">Un periodo específico</option>
      </select></label>
      {#if periodo === 'periodo'}
        <label>Desde<input type="date" bind:value={desde} disabled={bloqueado} onchange={() => vista = null} /></label>
        <label>Hasta (fecha excluida)<input type="date" bind:value={hasta} disabled={bloqueado} onchange={() => vista = null} /></label>
      {/if}
      <button type="button" disabled={bloqueado} onclick={consultarPendientes}>{ocupado ? 'Consultando…' : 'Consultar pendientes sin IA'}</button>
    </div>
    {#if vista}
      <div class="previa" aria-live="polite">
        <strong>{vista.resumen.pendientes} pendientes</strong>
        <span>{vista.resumen.candidatos} turnos elegibles · {vista.resumen.reutilizados} con lectura válida</span>
        <span>{intervalo(vista)}</span>
        {#if vista.resumen.lecturas_anteriores}
          <p>{vista.resumen.lecturas_anteriores} turnos tienen lecturas de una versión anterior. Se conservan, pero requieren nueva evaluación para la rúbrica actual; cada nueva lectura consume una llamada.</p>
        {/if}
        <p>Consulta sin llamadas a DeepSeek. Sólo se incluyen conversaciones elegibles para investigación; los turnos recientes con lectura válida ya están incluidos en las métricas.</p>
        {#if vista.resumen.pendientes}
          <label>Máximo de llamadas en este lote<input type="number" min="1" max="200" step="1" bind:value={maximo} disabled={bloqueado} /></label>
          <button type="button" onclick={ejecutarLote} disabled={bloqueado}>Analizar pendientes…</button>
        {:else}<p>No queda historial pendiente en este alcance y versión.</p>{/if}
      </div>
    {/if}
    {#if trabajo}
      <section class="avance" aria-label="Avance del análisis histórico" aria-live="polite">
        <strong>{tituloEstado ?? trabajo.estado}</strong>
        <span>{trabajo.clase ? cursos.find(c => c.id === trabajo.clase)?.nombre || 'Curso seleccionado' : 'Todos los cursos'}</span>
        <span>{intervalo(trabajo)}</span>
        <div class="progreso" class:esperando={activo}>
          <div class="rotulo-progreso"><span>Progreso de las llamadas de este lote</span><strong>{objetivo ? `${porcentaje}%` : activo ? 'Preparando…' : 'Sin llamadas nuevas'}</strong></div>
          {#if objetivo}
            <div class="barra" role="progressbar" aria-label="Llamadas completadas del lote" aria-valuemin="0" aria-valuemax={objetivo} aria-valuenow={Math.min(finalizadas, objetivo)} aria-valuetext={`${finalizadas} de ${objetivo} llamadas terminadas`}>
              <div class="relleno" style={`width: ${porcentaje}%`}></div>
            </div>
            <span>{finalizadas} de {objetivo} llamadas terminadas · hasta {trabajo.maximo_llamadas} permitidas</span>
          {:else if activo}<div class="barra indeterminada" role="progressbar" aria-label="Preparando el análisis"><div class="relleno"></div></div>{/if}
          {#if activo}<p class="fase"><span class="pulso" aria-hidden="true"></span>{trabajo.resumen.fase === 'esperando_proveedor' ? 'Esperando la respuesta de DeepSeek…' : trabajo.resumen.fase === 'guardando_lectura' ? 'Validando y guardando la lectura…' : 'Revisando el historial y las lecturas disponibles…'}</p>{/if}
        </div>
        <dl>
          <div><dt>Llamadas utilizadas</dt><dd>{trabajo.resumen.llamadas ?? 0} / {trabajo.maximo_llamadas}</dd></div>
          <div><dt>Lecturas guardadas</dt><dd>{trabajo.resumen.guardados ?? 0}</dd></div>
          <div><dt>Lecturas no válidas</dt><dd>{trabajo.resumen.descartados ?? 0}</dd></div>
          <div><dt>Lecturas reutilizadas</dt><dd>{trabajo.resumen.reutilizados ?? 0}</dd></div>
          <div><dt>Turnos aún pendientes</dt><dd>{trabajo.resumen.pendientes ?? 'Consultando'}</dd></div>
        </dl>
        {#if trabajo.actualizado_en}<span>Último avance registrado: {new Intl.DateTimeFormat('es-CO', { timeZone: 'America/Bogota', timeStyle: 'medium' }).format(new Date(trabajo.actualizado_en))}</span>{/if}
        {#if activo}<p>El análisis continúa aunque salgas de esta pantalla. Puedes regresar para consultar su avance.</p>
        {:else if trabajo.estado === 'interrumpido' && !recorridoTerminado}<p class="motivo" role="status">{motivos[trabajo.motivo] || 'El lote se interrumpió sin un motivo detallado registrado.'}</p><p>Se conservaron las lecturas terminadas. Consulta los pendientes y confirma otro lote para continuar; no se completan resultados con ceros. Esperar o consultar el avance no reanuda un lote interrumpido.</p>
        {:else}<p>{trabajo.resumen.pendientes ?? 0} pendientes en este recorrido. Las lecturas guardadas se incorporan al recalcular KPI, perfiles e informes del periodo elegido.</p>{/if}
        {#if !activo && (trabajo.resumen.descartados ?? 0) > 0}
          <p class="motivo">{trabajo.resumen.descartados} lecturas fueron rechazadas y siguen pendientes. Las {trabajo.resumen.guardados ?? 0} lecturas guardadas se conservan; los rechazos no se cuentan como ausencia de los factores.</p>
        {/if}
        {#if Object.keys(trabajo.resumen.rechazos_por_motivo ?? {}).length}
          <ul aria-label="Motivos de las lecturas rechazadas">
            {#each Object.entries(trabajo.resumen.rechazos_por_motivo) as [codigo, cantidad]}
              <li>{rechazos[codigo] || motivos[codigo] || 'Lectura no evaluable'}: {cantidad}</li>
            {/each}
          </ul>
        {/if}
        <p>Una llamada analiza un turno del estudiante con su contexto para los tres factores. Las lecturas reutilizadas ya existían y no consumen llamadas nuevas.</p>
        <button type="button" disabled={consultando} onclick={consultarAvance}>{consultando ? 'Consultando avance…' : 'Consultar avance y actualizar métricas'}</button>
        {#if !activo && (trabajo.resumen.pendientes ?? 0) > 0}<button type="button" disabled={bloqueado} onclick={consultarPendientes}>Consultar pendientes para continuar</button>{/if}
      </section>
    {/if}
    {#if error}<p class="error" role="alert">{error}</p>{/if}
  </div>
</details>

<style>
  .relectura { border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); }
  summary { padding: 1rem; cursor: pointer; font-weight: 750; color: var(--ink-primary); min-block-size: 44px; }
  .contenido { padding: 0 1rem 1rem; display: grid; gap: .85rem; }
  p { margin: 0; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.5; }
  .controles { display: flex; flex-wrap: wrap; align-items: end; gap: .75rem; }
  label { display: grid; gap: .3rem; color: var(--ink-secondary); font-size: var(--texto-xs); min-inline-size: 0; }
  select, input { min-block-size: 44px; max-inline-size: 100%; border: 1px solid var(--trazo); border-radius: var(--radius-sm); padding: .5rem; background: var(--surface-panel); color: var(--ink-primary); font: inherit; }
  button { min-block-size: 44px; padding: .6rem .85rem; border: 1px solid var(--accent-main); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--accent-main); font: inherit; font-size: var(--texto-sm); font-weight: 750; cursor: pointer; }
  button:disabled { opacity: .5; cursor: wait; }
  button:focus-visible, summary:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 3px; }
  .previa, .avance { display: grid; gap: .6rem; padding: .85rem; border-radius: var(--radius-sm); background: var(--surface-panel); color: var(--ink-primary); }
  .previa strong { font-size: 1.5rem; }
  span { color: var(--ink-secondary); font-size: var(--texto-xs); }
  dl { display: flex; flex-wrap: wrap; gap: 1.25rem; margin: 0; }
  dt { font-size: var(--texto-xs); color: var(--ink-secondary); } dd { margin: .25rem 0 0; font-weight: 750; }
  .error { color: var(--semantic-error); }
  .progreso { display: grid; gap: .45rem; min-inline-size: 0; }
  .rotulo-progreso { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .5rem; }
  .barra { position: relative; overflow: hidden; block-size: .8rem; border-radius: 99px; background: var(--surface-paper); border: 1px solid var(--trazo-suave); }
  .relleno { block-size: 100%; border-radius: inherit; background: var(--accent-main); transition: width .35s ease; }
  .esperando .barra::after { content: ''; position: absolute; inset: 0; background: linear-gradient(100deg, transparent 25%, color-mix(in srgb, var(--accent-light) 40%, transparent) 50%, transparent 75%); transform: translateX(-100%); animation: avance 2s linear infinite; }
  .indeterminada .relleno { inline-size: 25%; animation: avance 2s linear infinite; }
  .fase { display: flex; align-items: center; gap: .5rem; }
  .pulso { flex: 0 0 .5rem; block-size: .5rem; border-radius: 50%; background: var(--accent-main); animation: pulso 1.5s ease-in-out infinite; }
  .motivo { color: var(--semantic-warning); font-weight: 700; }
  @keyframes avance { to { transform: translateX(100%); } }
  @keyframes pulso { 50% { opacity: .35; } }
  @media(prefers-reduced-motion: reduce) { .relleno { transition: none; } .esperando .barra::after, .indeterminada .relleno, .pulso { animation: none; } }
  @media(max-width: 36rem) { .controles { display: grid; grid-template-columns: 1fr; } .previa button, .avance button { inline-size: 100%; } }
</style>
