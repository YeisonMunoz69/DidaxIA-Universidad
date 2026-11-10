<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import PestanasSegmentadas from '../../comun/base/PestanasSegmentadas.svelte';
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import { onMount } from 'svelte';
  import CabeceraDeRuta from '../../docente/piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../../docente/piezas/PantallaDesplazable.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import * as api from '../../nucleo/api/consumo-ia.js';
  import { descargarPDF } from '../../nucleo/descargas/pdf.js';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import SelectorFecha from '../../comun/base/SelectorFecha.svelte';
  import { fechaBogota } from '../../nucleo/formato/selectorFecha.js';

  let pestaña = $state('totales');
  const pestañas = [{id:'totales',titulo:'Totales',icono:'analitica-institucional'},{id:'modelos',titulo:'Modelos',icono:'consumo-ia'},{id:'horarios',titulo:'Horarios',icono:'reloj'},{id:'exportacion',titulo:'Exportar',icono:'descargar'}];
  let secciones = $state(['totales','modelos','diaria','horarios','metodologia']);
  let formato = $state('pdf');
  let desde = $state(fechaBogota(-7));
  let hasta = $state(fechaBogota(1));
  let datos = $state(null);
  let corte = $state(null);
  const filtrosPendientes = $derived(Boolean(corte && (desde!==corte.desde || hasta!==corte.hasta)));
  let cargando = $state(true);
  let exportando = $state('');
  let fallo = $state(null);
  let control;

  function visible(valor, sufijo = '') {
    if (valor == null || valor === '') return '—';
    return `${valor}${sufijo}`;
  }

  async function cargar() {
    control?.abort();
    control = new AbortController();
    cargando = true; fallo = null;
    const consulta = {desde,hasta};
    try { datos = await api.resumen(consulta, { señal: control.signal }); corte=consulta; }
    catch (error) { if (error?.name !== 'AbortError') fallo = describir(error); }
    finally { if (!control.signal.aborted) cargando = false; }
  }

  onMount(() => {
    void cargar();
    return () => control?.abort();
  });

  function descargarBlob(blob, nombre) {
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement('a');
    enlace.href = url; enlace.download = nombre; enlace.hidden = true; enlace.rel = 'noopener';
    document.body.appendChild(enlace); enlace.click(); enlace.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function exportar(formato, seleccion = secciones) {
    if (!await confirmarAccion({ tipo:'descarga', titulo:'¿Descargar métricas de modelos de IA?',
      descripcion:`Se preparará un ${formato.toUpperCase()} del ${corte?.desde || desde} al ${corte?.hasta || hasta} (fin exclusivo) con ${seleccion.join(', ')}.`, confirmar:'Descargar' })) return;
    exportando = formato;
    try {
      if (formato === 'pdf') {
        const documento = await api.exportarPDF({ ...(corte || {desde,hasta}), secciones: seleccion });
        const descarga = descargarPDF(documento, `didaxia-consumo-ia-${corte?.desde || desde}-${corte?.hasta || hasta}.pdf`);
        toast.descarga(`Descargando métricas de IA (PDF): ${descarga.nombre}`);
      } else {
        const documento = await api.exportarCSV({ ...(corte || {desde,hasta}), secciones: seleccion });
        const nombre = `didaxia-consumo-ia-${corte?.desde || desde}-${corte?.hasta || hasta}.csv`;
        descargarBlob(documento, nombre); toast.descarga(`Descargando métricas de IA (CSV): ${nombre}`);
      }
    } catch (error) {
      fallo = describir(error);
    } finally { exportando = ''; }
  }

  const maximoHora = $derived(Math.max(1,...(datos?.distribucion_hora_local ?? []).map(fila=>fila.llamadas ?? 0)));
  const pico = $derived((datos?.distribucion_hora_local ?? []).filter(fila=>fila.llamadas != null).reduce((mayor,fila)=>!mayor || fila.llamadas>mayor.llamadas ? fila:mayor,null));
  const maximoDiario = $derived(Math.max(1, ...(datos?.serie_diaria ?? []).map((fila) => fila.llamadas ?? 0)));
</script>

<PantallaDesplazable anchoMaximo="min(86rem, 100%)">
  <CabeceraDeRuta titulo="Consumo institucional de IA" icono="consumo-ia" insignia="Financiero · no KPI" ayuda="Estimaciones de consumo del proveedor, separadas del catálogo de KPI educativos. No son cargos reales. Cada llamada usa la TRM de su fecha histórica; las ausencias no son cero.">
    {#snippet nota()}Medición de proveedor y estimaciones reproducibles. No representa la factura real.{/snippet}
  </CabeceraDeRuta>

  <section class="metodo" aria-labelledby="titulo-metodo">
    <div><span class="sobrelinea">PERIODO CIVIL</span><h2 id="titulo-metodo">America/Bogota <BotonAyudaTooltip texto="Desde se incluye y Hasta se excluye: [desde,hasta). Cada consumo histórico usa la TRM de su fecha." /></h2></div>
    <SelectorFecha etiqueta="Desde (incluido)" bind:value={desde} maximo={fechaBogota()} />
    <SelectorFecha etiqueta="Hasta (excluido)" bind:value={hasta} minimo={desde} maximo={fechaBogota(1)} exclusivo />
    <Boton deshabilitado={cargando || !desde || !hasta} onclick={cargar}>{cargando ? 'Consultando…' : 'Aplicar periodo'}</Boton>
  </section>

  {#if filtrosPendientes}<p role="status">Aplica el nuevo período para actualizar los resultados. Las descargas conservan el corte consultado: {corte.desde} – {corte.hasta} (exclusivo).</p>{/if}
  <div class="navegacion-secciones"><PestanasSegmentadas opciones={pestañas} activa={pestaña} alElegir={(id)=>pestaña=id} etiqueta="Secciones de consumo" prefijo="consumo" /></div>
  {#if fallo}<Degradacion respuesta={fallo} alReintentar={cargar} />
  {:else if cargando && !datos}<CargadorCubo mensaje="Consultando consumo institucional…" pantallaCompleta />
  {:else if datos}
    <div id="consumo-panel-totales" role="tabpanel" tabindex="0" aria-labelledby="consumo-pestana-totales" hidden={pestaña!=='totales'}>
    <section class="tarjetas" aria-label="Totales del periodo">
      <article><span>Llamadas</span><strong>{datos.totales?.llamadas ?? 0}</strong><small>{datos.totales?.medidas ?? 0} con medición</small></article>
      <article><span>Tokens de entrada</span><strong>{visible(datos.totales?.entrada_total)}</strong><small>ausencia ≠ cero</small></article>
      <article><span>Tokens de salida</span><strong>{visible(datos.totales?.salida)}</strong><small>respuesta del proveedor</small></article>
      <article><span>Estimación USD</span><strong>{visible(datos.costos?.estimado_usd, ' USD')}</strong><small>{datos.costos?.estimado_usd == null ? 'cobertura incompleta' : 'no es cargo real'}</small></article>
      <article><span>Estimación COP</span><strong>{visible(datos.costos?.estimado_cop, ' COP')}</strong><small>TRM histórica por llamada</small></article>
      <article><span>TRM actual</span><strong>{visible(datos.trm_actual?.pesos_por_usd)}</strong><small>{visible(datos.trm_actual?.fecha)} · {datos.trm_actual?.desactualizada ? 'desactualizada' : 'última disponible'}</small></article>
    </section>

    <aside class="advertencia">
      <strong>Cobertura del cálculo.</strong>
      {datos.costos?.llamadas_sin_tarifa_o_medicion ?? 0} llamadas no tienen tarifa o medición suficiente y {datos.costos?.llamadas_sin_trm_historica ?? 0} no tienen TRM histórica. Los {datos.costos?.llamadas_locales_api_usd_cero ?? 0} consumos locales tienen costo API cero; su infraestructura no está calculada.
    </aside>

    <section class="serie-diaria"><h2>Uso por día <BotonAyudaTooltip texto={datos.regla_supresion || 'Los grupos pequeños se suprimen; no son cero llamadas.'} /></h2><ul class="barras">{#each datos.serie_diaria ?? [] as fila (fila.fecha)}<li><span>{fila.fecha}</span><div aria-hidden="true">{#if fila.llamadas != null}<i style={`--valor:${fila.llamadas/maximoDiario*100}%`}></i>{/if}</div><strong>{fila.estado==='suprimido'?'Suprimido':visible(fila.llamadas)}</strong></li>{:else}<li>Sin observaciones.</li>{/each}</ul></section>
    <Boton variante="secundario" deshabilitado={Boolean(exportando) || cargando} onclick={()=>exportar('pdf',['totales','diaria'])}>PDF de totales</Boton>
    </div>
    <div id="consumo-panel-modelos" role="tabpanel" tabindex="0" aria-labelledby="consumo-pestana-modelos" hidden={pestaña!=='modelos'}>
      <div class="titulo-seccion"><div><span class="sobrelinea">PROCEDENCIA</span><h2 id="titulo-modelos">Proveedor, modelo y caché</h2></div><div class="acciones"><Boton variante="secundario" deshabilitado={Boolean(exportando) || cargando} onclick={() => exportar('csv')}>{exportando === 'csv' ? 'Preparando…' : 'Descargar CSV'}</Boton><Boton deshabilitado={Boolean(exportando) || cargando} onclick={() => exportar('pdf')}>{exportando === 'pdf' ? 'Preparando…' : 'Descargar PDF'}</Boton></div></div>
      <div class="tabla"><table><thead><tr><th>Proveedor</th><th>Modelo respondido</th><th>Llamadas</th><th>Medidas</th><th>Cache hit</th><th>Cache miss</th><th>Entrada</th><th>Salida</th></tr></thead><tbody>{#each datos.por_modelo ?? [] as fila (`${fila.proveedor}-${fila.modelo}`)}<tr><td>{fila.proveedor}</td><td>{fila.modelo}</td><td>{fila.llamadas}</td><td>{fila.medidas}</td><td>{visible(fila.entrada_cache_hit)}{#if fila.entrada_total > 0 && fila.entrada_cache_hit != null}<meter min="0" max={fila.entrada_total} value={fila.entrada_cache_hit} aria-label={`Tokens de entrada recuperados de caché: ${fila.modelo}`}></meter><small>{(fila.entrada_cache_hit/fila.entrada_total*100).toFixed(1)}%</small>{/if}</td><td>{visible(fila.entrada_cache_miss)}</td><td>{visible(fila.entrada_total)}</td><td>{visible(fila.salida)}</td></tr>{:else}<tr><td colspan="8">No hubo llamadas en el periodo.</td></tr>{/each}</tbody></table></div>
      <Boton variante="secundario" deshabilitado={Boolean(exportando) || cargando} onclick={()=>exportar('pdf',['modelos'])}>PDF de modelos</Boton>
    </div>

    <div id="consumo-panel-horarios" role="tabpanel" tabindex="0" aria-labelledby="consumo-pestana-horarios" hidden={pestaña!=='horarios'}>
      <h2>Horas de mayor uso del sistema <BotonAyudaTooltip texto="No equivale a las franjas tarifarias pico UTC del proveedor. Los grupos pequeños se suprimen; no son horas sin uso." /></h2>
      {#if pico}<p>Mayor conteo publicable: <strong>{String(pico.hora).padStart(2,'0')}:00 · {pico.llamadas} llamadas</strong></p>{:else}<p>Sin desglose horario publicable.</p>{/if}
      <div class="histograma" aria-label="Llamadas por hora local">{#each datos.distribucion_hora_local ?? [] as fila (fila.hora)}<div class="hora-barra" class:pico={fila.llamadas != null && fila.llamadas===pico?.llamadas}><span>{fila.llamadas==null?'—':fila.llamadas}</span><div class="barra-hora">{#if fila.llamadas!=null}<i style={`height:${fila.llamadas/maximoHora*100}%`}></i>{:else}<span class="suprimida">⋯</span>{/if}</div><small>{String(fila.hora).padStart(2,'0')}</small></div>{/each}</div>
      <details><summary>Ver valores y estado por hora</summary><div class="tabla"><table><thead><tr><th>Hora</th><th>Llamadas</th><th>Estado</th></tr></thead><tbody>{#each datos.distribucion_hora_local ?? [] as fila (fila.hora)}<tr><td>{String(fila.hora).padStart(2,'0')}:00</td><td>{visible(fila.llamadas)}</td><td>{fila.estado}</td></tr>{/each}</tbody></table></div></details>
      <Boton variante="secundario" deshabilitado={Boolean(exportando) || cargando} onclick={()=>exportar('pdf',['horarios'])}>PDF de horarios</Boton>
    </div>
    <div id="consumo-panel-exportacion" role="tabpanel" tabindex="0" aria-labelledby="consumo-pestana-exportacion" hidden={pestaña!=='exportacion'}>
      <h2>Centro de exportación</h2><p>Selecciona el contenido. El período, las fuentes y los límites acompañan siempre la descarga.</p>
      <fieldset class="seleccion-exportacion"><legend>Secciones del informe</legend>{#each [{id:'totales',texto:'Totales y finanzas'},{id:'modelos',texto:'Modelos y caché'},{id:'diaria',texto:'Serie diaria'},{id:'horarios',texto:'Horarios'},{id:'metodologia',texto:'Metodología y TRM'}] as opcion}<label><input type="checkbox" bind:group={secciones} value={opcion.id}/>{opcion.texto}</label>{/each}</fieldset>
      <fieldset class="formato"><legend>Formato</legend><label><input type="radio" bind:group={formato} value="pdf"/>PDF</label><label><input type="radio" bind:group={formato} value="csv"/>CSV</label></fieldset>
      <Boton deshabilitado={Boolean(exportando) || cargando || !secciones.length} onclick={()=>exportar(formato)}>Descargar selección</Boton>
    <aside class="metodologia"><h2>Definiciones y límites</h2><p>{datos.regla_supresion}.</p><ul>{#each datos.advertencias ?? [] as aviso}<li>{aviso}</li>{/each}</ul><p>Fuente TRM: {datos.trm_actual?.fuente}. Las tarifas de DeepSeek están versionadas por modelo, franja UTC y vigencia.</p></aside>
    </div>
  {/if}
</PantallaDesplazable>

<style>
  .navegacion-secciones{min-width:0}.navegacion-secciones :global(.contenedor){margin-block:.25rem}

  [hidden]{display:none!important} [role=tabpanel]{min-width:0;animation:panel .2s ease-out}.serie-diaria{margin-block:1rem}.histograma{display:flex;gap:.25rem;overflow-x:auto;padding:.8rem 0;margin:1rem 0}.hora-barra{flex:1;min-width:28px;display:grid;gap:.4rem;text-align:center;color:var(--ink-secondary);font-size:var(--texto-xs)}.barra-hora{height:150px;display:flex;align-items:end;justify-content:center;background:var(--surface-panel);border-radius:var(--radius-xs)}.barra-hora i{display:block;width:80%;background:var(--color-sky);border-radius:var(--radius-xs)}.pico i{background:var(--accent-main)}.suprimida{align-self:center}.seleccion-exportacion,.formato{display:flex;flex-wrap:wrap;gap:.75rem;padding:1rem;border:1px solid var(--trazo-suave);border-radius:var(--radius-md);margin:1rem 0}.seleccion-exportacion label,.formato label{display:flex;align-items:center;gap:.5rem;min-height:44px;color:var(--ink-primary)}meter{display:block;width:100%;accent-color:var(--color-emerald)}@keyframes panel{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:none}}@media(prefers-reduced-motion:reduce){[role=tabpanel]{animation:none}}

  .sobrelinea{font-size:var(--texto-2xs);font-weight:800;letter-spacing:.12em;color:var(--accent-main)}
  .metodo{display:grid;grid-template-columns:minmax(16rem,1fr) repeat(2,minmax(10rem,.45fr)) auto;gap:.75rem;align-items:end;padding:1rem;border:1px solid var(--trazo-suave);border-radius:var(--radius-md);background:var(--surface-card)}
  h2{margin:.2rem 0;color:var(--ink-primary);font-size:var(--texto-lg)} p{color:var(--ink-secondary)}
  .tarjetas{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.7rem;margin-block:1rem}.tarjetas article{display:grid;gap:.2rem;min-inline-size:0;padding:1rem;border:1px solid var(--trazo-suave);border-radius:var(--radius-md);background:var(--surface-card)}.tarjetas span,.tarjetas small{color:var(--ink-secondary);font-size:var(--texto-xs)}.tarjetas strong{overflow-wrap:anywhere;color:var(--ink-primary);font-size:var(--texto-xl)}
  .advertencia,.metodologia{padding:.9rem 1rem;border-inline-start:4px solid var(--semantic-warning);border-radius:var(--radius-sm);background:var(--semantic-warning-bg);color:var(--ink-primary)}
  .titulo-seccion{display:flex;justify-content:space-between;gap:1rem;align-items:end;margin-block:1.2rem .6rem}.acciones{display:flex;gap:.5rem;flex-wrap:wrap}
  .tabla{max-inline-size:100%;overflow-x:auto;border:1px solid var(--trazo-suave);border-radius:var(--radius-sm)}table{inline-size:100%;border-collapse:collapse;min-inline-size:42rem;background:var(--surface-card)}th,td{padding:.65rem;text-align:start;border-block-end:1px solid var(--trazo-suave);color:var(--ink-primary);font-size:var(--texto-xs)}th{background:var(--surface-subtle);color:var(--ink-secondary)}
  .barras{display:grid;gap:.55rem;padding:0;list-style:none}.barras li{display:grid;grid-template-columns:6.2rem minmax(4rem,1fr) 5rem;gap:.5rem;align-items:center;color:var(--ink-secondary);font-size:var(--texto-xs)}.barras div{block-size:.55rem;overflow:hidden;border-radius:99px;background:var(--surface-subtle)}.barras i{display:block;inline-size:var(--valor);block-size:100%;background:var(--accent-main)}
  @media(max-width:64rem){.metodo{grid-template-columns:1fr 1fr}.metodo>div{grid-column:1/-1}.tarjetas{grid-template-columns:repeat(2,minmax(0,1fr))}}
  @media(max-width:42rem){.metodo,.tarjetas{grid-template-columns:1fr}.metodo>*{grid-column:1}.titulo-seccion{align-items:flex-start;flex-direction:column}.acciones{inline-size:100%}.barras li{grid-template-columns:5.3rem minmax(3rem,1fr) 4.7rem}}
  @media(max-width:42rem){.metodo > :global(button){grid-column:1/-1;width:100%}.metodo{grid-template-columns:repeat(2,minmax(0,1fr));padding:.75rem}.metodo>*{grid-column:auto}.metodo>div:first-child,.metodo>:last-child{grid-column:1/-1}.tarjetas{grid-template-columns:repeat(2,minmax(0,1fr))}.tarjetas article{padding:.75rem}.tarjetas strong{font-size:var(--texto-lg)}}
</style>
