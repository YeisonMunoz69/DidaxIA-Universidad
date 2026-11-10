
<script>
  import ConfianzaDelDiagnostico from './ConfianzaDelDiagnostico.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import BotonExplicacion from '../../comun/base/BotonExplicacion.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import MetodologiaKPI from '../../comun/kpi/MetodologiaKPI.svelte';
  import TarjetaKPI from '../../comun/kpi/TarjetaKPI.svelte';
  import { describirPeriodo } from '../../comun/kpi/periodo.js';
  import { visibleEnTablero } from '../../comun/kpi/visibilidad.js';

  let {
    vector = null
  } = $props();
  let seleccionado = $state(null);
  let ayudaAbierta = $state(false);

  const ROTULO = {
    'PS-Anx':             'Señales de tensión al resolver',
    FAH:                  'Señales de reticencia a pedir ayuda',
    ansiedad_resolucion:  'Señales de tensión al resolver',
    ansiedad_evaluacion:  'Señales de tensión ante la evaluación',
    miedo_pedir_ayuda:    'Señales de reticencia a pedir ayuda',
    autoeficacia:         'Indicios de baja confianza en la propia capacidad'
  };

  const rasgos = $derived(
    vector?.componentes?.filter((item) => item.clave_origen !== 'PS-Anx' && item.estado === 'disponible' && Number.isFinite(item.valor)).map((item) => ({
      ...item, clave: item.clave_origen, rotulo: item.nombre ?? ROTULO[item.clave_origen] ?? item.clave_origen, conocido: true
    })) ?? Object.entries(vector?.rasgos ?? {}).filter(([, valor]) => Number.isFinite(valor)).map(([clave, valor]) => ({
      clave, valor, rotulo: ROTULO[clave] ?? clave, conocido: clave in ROTULO,
      metodologia: null, numerador: null, denominador: null
    }))
  );
</script>

<section class="vector" aria-labelledby="vector-titulo">
  <div class="cabecera-tarjeta">
    <Icono nombre="chispa" medida={18} />
    <h3 id="vector-titulo">Indicios complementarios</h3>
    <BotonAyudaTooltip tamano="sm" posicion="abajo" texto="Estas proporciones resumen señales observables del lenguaje durante el periodo. No miden rasgos psicológicos ni diagnostican al estudiante. Abre el botón de expansión de cada indicio para ver su cálculo y sus límites." ariaLabel="Cómo interpretar los indicios complementarios" />
  </div>


  <ConfianzaDelDiagnostico
    valor={vector?.confianza ?? null}
    observaciones={vector?.observaciones ?? null} />
  {#if vector?.motivo}<p class="advertencia">{vector.motivo}</p>{/if}

  {#if rasgos.length}
    <dl>
      {#each rasgos as r (r.clave)}
        <div class="rasgo">
          <dt class:desconocido={!r.conocido}>{r.rotulo}
            {#if r.metodologia}<BotonExplicacion etiqueta={`Explicar ${r.rotulo}`} alAbrir={() => { seleccionado = r; ayudaAbierta = true; }} />{/if}
          </dt>
          <dd>
            <span class="cifra">{r.valor == null ? 'Sin datos' : `${(r.valor * 100).toFixed(1)} %`}</span>
            {#if r.valor != null && r.denominador != null}<span class="muestra">{r.numerador} de {r.denominador} mensajes</span>{/if}
            {#if r.valor != null}<span class="barra" aria-hidden="true">
              <span class="relleno" style:inline-size="{r.valor * 100}%"></span>
            </span>{/if}
          </dd>
        </div>
      {/each}
    </dl>
  {:else}
    <p class="vacio">Todavía no hay indicios suficientes para este estudiante.</p>
  {/if}
  {#each (vector?.observables ?? []).filter(visibleEnTablero) as indicador (indicador.codigo)}<TarjetaKPI {indicador} />{/each}
</section>

<Dialogo bind:abierto={ayudaAbierta} titulo={seleccionado?.rotulo ?? 'Indicio observable'} ancho="48rem">
  {#if seleccionado}
    <div class="detalle-indicio">
      <p>Mensajes con coincidencia: {seleccionado.numerador} de {seleccionado.denominador}. Unidad: proporción de mensajes del periodo seleccionado; no intensidad psicológica.</p>
      <p>{describirPeriodo(vector?.periodo)}</p>
      <MetodologiaKPI metodologia={seleccionado.metodologia} />
    </div>
  {/if}
</Dialogo>

<style>
  .vector {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-sm);
    padding: var(--espacio-lg);
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
    max-inline-size: var(--ancho-lectura);
  }

  .cabecera-tarjeta { display: flex; align-items: center; gap: 8px; color: var(--ink-secondary); }

  h3 { margin: 0; font-size: var(--texto-md); font-weight: 600; color: var(--ink-primary); }

  .advertencia {
    margin: 0;
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
  }

  dl { margin: 0.4rem 0 0; display: flex; flex-direction: column; gap: 0.2rem; }

  .rasgo {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.6rem;
    border-radius: var(--radius-sm);
    transition: var(--transition-fast);
  }

  .rasgo:hover { background: var(--surface-paper); }

  dt { font-size: var(--texto-sm); color: var(--ink-primary); }
  dt { display: flex; align-items: center; gap: .4rem; }
  .detalle-indicio { max-block-size: 70vh; overflow-y: auto; color: var(--ink-secondary); }
  @media (max-width: 34rem) { .rasgo { grid-template-columns: 1fr; } dd { justify-content: space-between; } }

  .desconocido { font-family: var(--fuente-mono); color: var(--semantic-warning); }

  dd {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0;
  }

  .cifra {
    font-size: var(--texto-sm);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    min-inline-size: 3.5ch;
    text-align: end;
    color: var(--ink-primary);
  }

  .muestra { font-size: var(--texto-xs); color: var(--ink-tertiary); font-variant-numeric: tabular-nums; }

  .barra {
    display: block;
    inline-size: 6rem;
    block-size: 0.45rem;
    background: var(--surface-canvas);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-pill, 9999px);
    overflow: hidden;
  }

  .relleno {
    display: block;
    block-size: 100%;
    background: var(--accent-main);
    border-radius: var(--radius-pill, 9999px);
    transition: inline-size var(--transition);
  }

  .vacio { margin: 0; font-size: var(--texto-sm); color: var(--ink-tertiary); }
</style>
