<!--
Lo pendiente de revisión.

Con aprobar, editar o rechazar por elemento. RU-12. Diseñada para revisión
POR MUESTREO Y POR EXCEPCION, no para revisar todo: con treinta o sesenta
estudiantes revisar cada respuesta es insostenible, y el sistema no lo
pide.

QUÉ HACE ESTA PANTALLA PARA QUE «POR MUESTREO» SEA POSIBLE
-----------------------------------------------------------
Tres cosas, y ninguna es un adorno: filtra, dice cuántos quedan, y **no ofrece
aprobar en bloque**. La ausencia del botón de aprobar todo es la decisión más
importante de esta ruta — con él la revisión se vuelve un trámite de un clic y
deja de ser revisión, que es justo lo que `RU-12` compra.

LA CANTIDAD SE DICE, NO SE ESCONDE. Un docente que no sabe si le quedan seis o
seiscientos no puede decidir cómo muestrear.

DECISIÓN RATIFICADA: REVISIÓN AUTOMÁTICA POR EXCEPCIÓN
------------------------------------------------------
No existe un «modo supervisión» global ni un interruptor que detenga las
respuestas antes de entregarlas. Los turnos degradados o marcados llegan a
esta cola automáticamente; el docente revisa sólo los casos que lo necesitan
y cualquier corrección se agrega después como una aclaración identificada,
sin reescribir la respuesta original. Así se conserva el historial y se evita
convertir la revisión pedagógica en una aprobación obligatoria de cada turno.



-->
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import TarjetaDeRevision from '../piezas/TarjetaDeRevision.svelte';
  import FiltrosDeCola from '../piezas/FiltrosDeCola.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import CabeceraDeRuta from '../piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../piezas/PantallaDesplazable.svelte';
  import EstadoVacio from '../piezas/EstadoVacio.svelte';
  import { onMount, untrack } from 'svelte';
  import * as api from '../../nucleo/api/supervision.js';
  import * as apiClases from '../../nucleo/api/clases.js';
  import { describir } from '../../nucleo/errores/degradacion.js';

  let filtros = $state({ urgencia: '', clase: '', tipo: '' });
  let elementos = $state([]);
  let clases = $state([]);
  let total = $state(0);
  let cargando = $state(false);
  let fallo = $state(null);

  /**
   * Páginas de verdad, no un tope que crece · reescrito el 2026-08-22.
   *
   * La primera versión acumulaba con «Cargar más» —un `tope` cada vez
   * mayor, sin `desde`—, y a pedido explícito («el mecanismo en sí» se
   * sentía raro, y el texto del botón confuso) se cambió por paginación
   * fija: `TAMANO_PAGINA` elementos por página, con `desde` —nuevo en
   * `api.listar()`, `rutas/supervision.py` y los dos almacenes de
   * `ColaDeRevision`— diciendo cuántos saltarse. La lista nunca crece más
   * allá de una página, así que el scroll vertical no vuelve a acumularse
   * con dieciocho pendientes reales.
   */
  const TAMANO_PAGINA = 6;
  let pagina = $state(0);   // 0-indexado

  const totalPaginas = $derived(Math.max(1, Math.ceil(total / TAMANO_PAGINA)));

  async function cargar() {
    cargando = true;
    fallo = null;
    try {
      const r = await api.listar({ ...filtros, tope: TAMANO_PAGINA, desde: pagina * TAMANO_PAGINA });
      elementos = r?.elementos ?? [];
      total = r?.total ?? elementos.length;
    } catch (e) {
      fallo = describir(e);
    } finally {
      cargando = false;
    }
  }

  async function actualizarSilenciosamente() {
    if (cargando || globalThis.document?.visibilityState === 'hidden') return;
    try {
      const r = await api.listar({
        ...filtros, tope: TAMANO_PAGINA, desde: pagina * TAMANO_PAGINA
      });
      elementos = r?.elementos ?? [];
      total = r?.total ?? elementos.length;
      // Si la última fila de la última página desapareció en otra sesión,
      // vuelve a una página que exista antes del próximo ciclo.
      const ultima = Math.max(0, Math.ceil(total / TAMANO_PAGINA) - 1);
      if (pagina > ultima) {
        pagina = ultima;
        await cargar();
      }
    } catch {
      /* El sondeo auxiliar no tapa una cola que ya se puede leer. */
    }
  }

  // Al cambiar los filtros se vuelve a pedir, y la página vuelve a la
  // primera: una página 3 acumulada con un filtro nuevo podría pedir
  // «desde» más allá de lo que ese filtro tiene.
  //
  // `untrack(cargar)` Y NO `cargar()` A SECAS: `cargar()` lee `pagina`
  // antes de su primer `await` —para armar `desde`—, y esa lectura
  // síncrona dentro de un `$effect` lo vuelve una dependencia MÁS de este
  // efecto, aunque nunca se lea con un `void pagina` explícito. Sin
  // `untrack`, `irAPagina()` de más abajo escribía `pagina` para cambiar
  // de página, ese cambio volvía a disparar ESTE efecto, y su primera
  // línea —`pagina = 0`— deshacía el cambio antes de que la petición
  // llegara a completarse. Mismo bug, mismo arreglo, que la versión
  // anterior de esta pantalla con `tope` — ver el historial de commits.
  $effect(() => {
    // Se leen para que el efecto dependa de ellos.
    void filtros.urgencia; void filtros.clase; void filtros.tipo;
    pagina = 0;
    untrack(cargar);
  });

  function irAPagina(nueva) {
    if (nueva < 0 || nueva >= totalPaginas || nueva === pagina) return;
    pagina = nueva;
    cargar();
  }

  $effect(() => {
    apiClases.mias().then((c) => (clases = c ?? [])).catch(() => (clases = []));
  });

  onMount(() => {
    // Las excepciones nacen en otras sesiones. Una consulta corta mientras la
    // pestaña está visible y otra al recuperar el foco evitan la recarga manual
    // sin mantener conexiones abiertas ni consultar en segundo plano.
    const alVolver = () => {
      if (globalThis.document?.visibilityState !== 'hidden') actualizarSilenciosamente();
    };
    const intervalo = globalThis.setInterval?.(actualizarSilenciosamente, 3000);
    globalThis.addEventListener?.('focus', alVolver);
    globalThis.document?.addEventListener?.('visibilitychange', alVolver);
    return () => {
      if (intervalo !== undefined) globalThis.clearInterval?.(intervalo);
      globalThis.removeEventListener?.('focus', alVolver);
      globalThis.document?.removeEventListener?.('visibilitychange', alVolver);
    };
  });

  /** Tras actuar sobre un elemento, se quita de la lista sin recargar entera. */
  function quitar(id) {
    elementos = elementos.filter((e) => e.id !== id);
    total = Math.max(0, total - 1);
  }

  const actuar = (fn) => async (id, extra) => {
    try {
      await fn(id, extra);
      quitar(id);
    } catch (e) {
      fallo = describir(e);
    }
  };
</script>

<PantallaDesplazable>
  <CabeceraDeRuta titulo="Cola de supervisión" icono="supervision" insignia="Revisión pedagógica">
    {#snippet accion()}
      <span class="badge-cuenta">
        {#if cargando}Cargando…
        {:else}{total} pendiente{total === 1 ? '' : 's'}
        {/if}
      </span>
    {/snippet}
    {#snippet nota()}
      Está pensada para revisar <strong>por muestreo y por excepción</strong>.
      No hace falta pasar por todas: acota con los filtros y mira lo que más lo
      pida.
    {/snippet}
  </CabeceraDeRuta>

  <details class="ayuda-supervision">
    <summary><Icono nombre="chispa" medida={15} /> ¿Cómo funciona esta revisión?</summary>
    <p>La cola recibe excepciones pedagógicas de tus clases. Al corregir, la respuesta original se conserva y tu texto llega al estudiante como una aclaración posterior; no se publica en su nombre ni se reescribe el historial.</p>
  </details>

  <FiltrosDeCola bind:filtros {clases} />

  {#if fallo}
    <Degradacion respuesta={fallo} alReintentar={cargar} />
  {/if}

  {#if cargando && !elementos.length && !fallo}
    <CargadorCubo mensaje="Consultando casos de supervisión…" pantallaCompleta />
  {:else if !cargando && !elementos.length && !fallo}
    <EstadoVacio icono="check" texto="No queda nada pendiente con estos filtros." tono="exito" />
  {/if}

  <ul class="lista">
    {#each elementos as e (e.id)}
      <li>
        <TarjetaDeRevision
          elemento={e}
          alAprobar={actuar(api.aprobar)}
          alEditar={actuar(api.editar)}
          alRechazar={actuar(api.rechazar)} />
      </li>
    {/each}
  </ul>

  {#if totalPaginas > 1}
    <nav class="paginacion" aria-label="Páginas de la cola">
      <button type="button" onclick={() => irAPagina(pagina - 1)} disabled={cargando || pagina === 0}>
        Anterior
      </button>
      <span class="indicador-pagina">Página {pagina + 1} de {totalPaginas}</span>
      <button type="button" onclick={() => irAPagina(pagina + 1)} disabled={cargando || pagina >= totalPaginas - 1}>
        Siguiente
      </button>
    </nav>
  {/if}
</PantallaDesplazable>

<style>
  /*
    El envoltorio de scroll —antes `.cola-desplazable`/`.cola` en este mismo
    archivo— se extrajo a `docente/piezas/PantallaDesplazable.svelte` el
    2026-08-22: era una de cuatro copias casi idénticas del mismo arreglo
    (el bug real que resuelve, y la razón de las dos capas separadas, está
    documentado allá). La lista de `TarjetaDeRevision` sigue en una sola
    columna a propósito —ver el docstring del módulo—: son tarjetas de
    altura variable con acciones que pueden crecer al editar, y el mosaico
    de dos columnas que se probó primero se veía descuadrado con datos
    reales de altura muy distinta.
  */
  .badge-cuenta {
    padding: 4px 12px;
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-pill, 9999px);
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-secondary);
    white-space: nowrap;
  }
  .ayuda-supervision { align-self: flex-end; max-inline-size: 42rem; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .ayuda-supervision summary { display: inline-flex; align-items: center; gap: .4rem; cursor: pointer; color: var(--accent-main); font-weight: 700; }
  .ayuda-supervision p { margin: .6rem 0 0; padding: .75rem .9rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-panel); }


  /* Una columna de tarjetas horizontales — ver el comentario más arriba
     sobre por qué se abandonó el mosaico de dos columnas. */
  .lista {
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  /* `max-inline-size: none`: `estilos/tipografia.css` trae
     `:where(p, li) { max-inline-size: var(--ancho-lectura) }` global —el
     mismo mecanismo ya documentado en `MisClases.svelte::.frontera`, solo
     que esta vez cae sobre `<li>` y no sobre un `<p>`—. Sin esto, cada
     tarjeta quedaba capada a ~534px de ancho de lectura aunque `.lista`
     tuviera 1208px disponibles: la franja de acciones y el cuerpo se
     apretaban dentro de esa columna angosta en vez de usar el ancho real
     de la pantalla. Confirmado con `getBoundingClientRect` el 2026-08-22. */
  .lista > li { max-inline-size: none; }

  .paginacion {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--espacio-md);
    align-self: center;
    padding-block-start: var(--espacio-sm);
  }

  .paginacion button {
    padding: 0.5em 1.1em;
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-pill, 9999px);
    color: var(--ink-secondary);
    font-size: var(--texto-sm);
    font-weight: 600;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .paginacion button:hover:not(:disabled) { border-color: var(--accent-main); color: var(--accent-main); }

  .paginacion button:disabled { opacity: 0.5; cursor: not-allowed; }

  .indicador-pagina {
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-secondary);
    font-variant-numeric: tabular-nums;
  }
</style>
