
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import { onMount } from 'svelte';
  import CabeceraDeRuta from '../piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../piezas/PantallaDesplazable.svelte';
  import EstadoVacio from '../piezas/EstadoVacio.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import TableroKPI from '../../comun/kpi/TableroKPI.svelte';
  import * as apiClases from '../../nucleo/api/clases.js';
  import * as apiKpi from '../../nucleo/api/kpi.js';
  import { pedir } from '../../nucleo/api/cliente.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import SelectorFecha from '../../comun/base/SelectorFecha.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import Boton from '../../comun/base/Boton.svelte';

  let clases = $state([]);
  let seleccion = $state('');
  let desde = $state(fechaLocal(-7));
  let hasta = $state(fechaLocal(0));
  let datos = $state(null);
  let cargando = $state(true);
  let fallo = $state(null);
  let peticion = 0;
  let clasesParaEliminar = $state([]);
  let seleccionEliminar = $state('');
  let claseAEliminar = $state(null);
  let confirmandoEliminacion = $state(false);
  let motivo = $state('');
  let nombreConfirmado = $state('');
  let eliminando = $state(false);
  let errorEliminacion = $state('');
  let avisoEliminacion = $state('');
  const esInvestigador = $derived(sesion.rol === 'investigador');
  const insigniaKpi = $derived(datos?.version_catalogo?.replace(/^kpi\./i, 'KPI ') ?? 'KPI');

  function fechaLocal(desplazamiento) {
    const fecha = new Date(Date.now() + desplazamiento * 86400000);
    const partes = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit'
    }).formatToParts(fecha);
    const de = (tipo) => partes.find((parte) => parte.type === tipo)?.value;
    return `${de('year')}-${de('month')}-${de('day')}`;
  }

  function periodo() {
    return { desde: `${desde}T00:00:00-05:00`, hasta: `${hasta}T23:59:59.999-05:00` };
  }

  async function iniciar() {
    cargando = true;
    fallo = null;
    try {
      if (esInvestigador) {
        const parametros = new URLSearchParams(periodo());
        clases = (await pedir(`/investigacion/resumen?${parametros}`))?.cursos ?? [];
        clasesParaEliminar = await apiClases.clasesInstitucionales();
      } else {
        clases = (await apiClases.mias()) ?? [];
      }
      const solicitada = new URLSearchParams(location.search).get('clase');
      if (solicitada && clases.some((clase) => clase.id === solicitada)) seleccion = solicitada;
      else if (!seleccion && clases.length) seleccion = clases[0].id;
      if (seleccion) await cargar();
    } catch (error) {
      fallo = describir(error);
    } finally {
      cargando = false;
    }
  }

  async function cargar() {
    if (!seleccion) return;
    const actual = ++peticion;
    cargando = true;
    fallo = null;
    try {
      const nuevo = esInvestigador
        ? await apiKpi.indicadoresInstitucional({ clase: seleccion, ...periodo() })
        : await apiKpi.indicadoresDocente(seleccion, periodo());
      if (actual === peticion) datos = nuevo;
    } catch (error) {
      if (actual === peticion) {
        datos = null;
        fallo = describir(error);
      }
    } finally {
      if (actual === peticion) cargando = false;
    }
  }

  onMount(iniciar);

  function prepararEliminacion() {
    claseAEliminar = clasesParaEliminar.find((clase) => clase.id === seleccionEliminar) ?? null;
    if (!claseAEliminar) return;
    motivo = ''; nombreConfirmado = ''; errorEliminacion = ''; avisoEliminacion = '';
    confirmandoEliminacion = true;
  }

  async function eliminarClase() {
    if (!claseAEliminar || eliminando || nombreConfirmado !== claseAEliminar.nombre || motivo.trim().length < 5) return;
    eliminando = true; errorEliminacion = '';
    const clase = claseAEliminar;
    try {
      await apiClases.archivar(clase.id, motivo.trim());
      confirmandoEliminacion = false;
      clases = clases.filter((item) => item.id !== clase.id);
      clasesParaEliminar = clasesParaEliminar.filter((item) => item.id !== clase.id);
      seleccionEliminar = '';
      if (seleccion === clase.id) { ++peticion; seleccion = ''; datos = null; }
      avisoEliminacion = `La clase ${clase.nombre} fue eliminada de las vistas activas. Sus matrículas se cerraron y su historial se conserva.`;
    } catch (error) {
      errorEliminacion = error?.detalle || 'No se pudo cerrar la clase. Revisa la conexión y vuelve a intentarlo.';
    } finally { eliminando = false; }
  }
</script>

<PantallaDesplazable anchoMaximo="min(86rem, 100%)">
  <CabeceraDeRuta titulo="Indicadores del grupo" icono="grupo" insignia={insigniaKpi}>
    {#snippet nota()}
      Cada resultado declara su población, periodo, muestra y calidad. Sólo aparecen cifras calculadas para este corte; los datos ausentes nunca se sustituyen por cero.
    {/snippet}
  </CabeceraDeRuta>

  <form class="filtros" onsubmit={(evento) => { evento.preventDefault(); cargar(); }}>
    <label><span>Clase</span><select use:menuDesplegable={seleccion} bind:value={seleccion} disabled={!clases.length}>
      {#each clases as clase (clase.id)}<option value={clase.id}>{clase.nombre}</option>{/each}
    </select></label>
    <SelectorFecha etiqueta="Desde" bind:value={desde} maximo={fechaLocal(0)} />
    <SelectorFecha etiqueta="Hasta" bind:value={hasta} minimo={desde} maximo={fechaLocal(0)} />
    <button type="submit" disabled={!seleccion || cargando}>{cargando ? 'Calculando…' : 'Aplicar periodo'}</button>
  </form>

  {#if fallo}
    <Degradacion respuesta={fallo} alReintentar={seleccion ? cargar : iniciar} />
  {:else if !cargando && !clases.length}
    <EstadoVacio icono="grupo" titulo={esInvestigador ? 'No hay clases institucionales' : 'Aún no tienes clases'}
      texto="Cuando exista una clase aprobada podrás calcular aquí sus indicadores." />
  {:else if cargando && !datos}
    <CargadorCubo mensaje="Calculando indicadores con sus reglas de calidad…" pantallaCompleta />
  {:else if datos}
    <section class="corte">
      <div><span>Población elegible</span><strong>{datos.poblacion?.estudiantes_elegibles ?? '—'}</strong></div>
      <div><span>Clases en alcance</span><strong>{datos.poblacion?.clases ?? '—'}</strong></div>
      <p>Periodo interpretado en <strong>{datos.periodo?.zona_horaria}</strong>. Intervalo {datos.periodo?.intervalo}.</p>
    </section>
    <TableroKPI {datos} />
  {/if}

  {#if esInvestigador}
    <details class="gestion-clases">
      <summary>Eliminar clase y desmatricular estudiantes</summary>
      <p>La clase dejará de aparecer en los grupos y sus estadísticas. Las cuentas y las conversaciones se conservan con su historial; los estudiantes podrán solicitar otra clase.</p>
      <label><span>Clase que deseas eliminar</span>
        <select bind:value={seleccionEliminar} disabled={eliminando}>
          <option value="">Selecciona una clase</option>
          {#each clasesParaEliminar as clase (clase.id)}<option value={clase.id}>{clase.nombre}</option>{/each}
        </select>
      </label>
      <button type="button" onclick={prepararEliminacion} disabled={!seleccionEliminar || eliminando}>Revisar eliminación</button>
      {#if avisoEliminacion}<p role="status">{avisoEliminacion}</p>{/if}
    </details>
  {/if}
</PantallaDesplazable>

<Dialogo bind:abierto={confirmandoEliminacion} titulo="Eliminar clase y cerrar matrículas" tipo="eliminar" bloqueado={eliminando} ancho="36rem">
  <p>Vas a cerrar <strong>{claseAEliminar?.nombre}</strong>, desmatricular a sus estudiantes y cancelar las solicitudes pendientes. Se conservarán las conversaciones y la pertenencia histórica a esta clase.</p>
  <label class="campo-eliminacion">Motivo<textarea bind:value={motivo} minlength="5" maxlength="240" rows="3"></textarea></label>
  <label class="campo-eliminacion">Escribe el nombre de la clase para confirmar<input bind:value={nombreConfirmado} autocomplete="off" /></label>
  {#if errorEliminacion}<p role="alert">{errorEliminacion}</p>{/if}
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => { confirmandoEliminacion = false; }} deshabilitado={eliminando}>Cancelar</Boton>
    <Boton onclick={eliminarClase} deshabilitado={eliminando || motivo.trim().length < 5 || nombreConfirmado !== claseAEliminar?.nombre}>{eliminando ? 'Cerrando clase…' : 'Eliminar clase y desmatricular'}</Boton>
  {/snippet}
</Dialogo>

<style>
  .gestion-clases { margin-block-start: 1rem; padding: 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-panel); }
  .gestion-clases summary { cursor: pointer; font-weight: 700; color: var(--ink-primary); }
  .gestion-clases p { color: var(--ink-secondary); line-height: 1.6; }
  .gestion-clases label { max-inline-size: 32rem; }
  .gestion-clases button { min-block-size: 44px; margin-block-start: .8rem; padding: .55rem .9rem; border: 1px solid var(--trazo); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); cursor: pointer; }
  .campo-eliminacion { display: grid; gap: .4rem; margin-block: .8rem; }
  .campo-eliminacion input, .campo-eliminacion textarea { inline-size: 100%; padding: .6rem; border: 1px solid var(--trazo); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); font: inherit; }
  .filtros { display: grid; grid-template-columns: minmax(13rem, 1.5fr) repeat(2, minmax(10rem, .8fr)) auto; align-items: end; gap: .7rem; padding: .9rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-panel); }
  label { display: grid; gap: .28rem; min-inline-size: 0; color: var(--ink-tertiary); font-size: var(--texto-xs); font-weight: 750; }
  select { min-block-size: 2.6rem; min-inline-size: 0; padding: .48rem .65rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); font: inherit; }
  .filtros button { min-block-size: 2.6rem; padding: .5rem .9rem; border: 1px solid transparent; border-radius: var(--radius-sm); background: var(--accent-main); color: var(--accent-on-main); font: inherit; font-weight: 750; cursor: pointer; }
  .filtros button:disabled { opacity: .62; cursor: wait; }
  .corte { display: grid; grid-template-columns: repeat(2, auto) 1fr; align-items: center; gap: .7rem; padding: .75rem .9rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); }
  .corte div { display: grid; padding-inline-end: .7rem; border-inline-end: 1px solid var(--trazo-suave); }
  .corte span, .corte p { margin: 0; color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .corte strong { color: var(--ink-primary); font-variant-numeric: tabular-nums; }
  .corte p { justify-self: end; text-align: end; }
  @media (max-width: 60rem) { .filtros { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 36rem) { .filtros { grid-template-columns: 1fr; } .corte { grid-template-columns: repeat(2, 1fr); } .corte p { grid-column: 1 / -1; justify-self: start; text-align: start; } }
</style>
