
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import Campo from '../../comun/base/Campo.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import CabeceraDeRuta from '../piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../piezas/PantallaDesplazable.svelte';
  import * as api from '../../nucleo/api/contexto-curricular.js';
  import * as apiClases from '../../nucleo/api/clases.js';
  import { describir } from '../../nucleo/errores/degradacion.js';

  let unidad = $state('');
  let notacion = $state('sen');
  let observaciones = $state('');
  let fallo = $state(null);
  let guardado = $state(false);
  let clases = $state([]);
  let claseSeleccionada = $state('');
  let cargando = $state(true);
  let consultandoContexto = $state(false);

  const NOTACIONES_CURSO = [
    ['sen', 'sen, cos, tan', 'La notación en español — la que trae el sistema por defecto.'],
    ['sin', 'sin, cos, tan', 'La notación de la mayoría de libros y calculadoras en inglés.']
  ];

  async function cargar() {
    if (!claseSeleccionada) return;
    consultandoContexto = true;
    fallo = null;
    guardado = false;
    try {
      const c = await api.leer(claseSeleccionada);
      unidad = c?.unidad ?? '';
      notacion = c?.notacion ?? 'sen';
      observaciones = c?.observaciones ?? '';
    } catch (e) { fallo = describir(e); }
    finally { consultandoContexto = false; }
  }

  async function guardar() {
    fallo = null;
    guardado = false;
    try {
      await api.guardar({ clase: claseSeleccionada, unidad, notacion, observaciones });
      guardado = true;
    } catch (e) { fallo = describir(e); }
  }

  async function iniciar() {
    cargando = true;
    fallo = null;
    try {
      clases = await apiClases.mias();
      claseSeleccionada = clases[0]?.id ?? '';
      if (claseSeleccionada) await cargar();
    } catch (e) {
      fallo = describir(e);
    } finally {
      cargando = false;
    }
  }

  $effect(() => { iniciar(); });
</script>

<PantallaDesplazable anchoMaximo="min(70rem, 100%)" relleno="var(--espacio-lg)" espacio="var(--espacio-md)">
  <CabeceraDeRuta titulo="Contexto curricular" icono="contexto" insignia="Configuración del curso">
    {#snippet nota()}
      Conserva la referencia curricular de cada clase para el trabajo docente.
      <strong>No modifica las conversaciones ni el nivel de ayuda</strong>:
      este último lo decide el sistema turno a turno.
    {/snippet}
  </CabeceraDeRuta>

  <details class="ayuda-contexto">
    <summary aria-label="Qué se configura en Contexto curricular">&lt;?&gt;</summary>
    <div>
      <strong>¿Qué se hace aquí?</strong>
      <p>Elige una de tus clases y registra la unidad vigente, la forma de escribir las funciones trigonométricas y las notas curriculares que deben conservarse como referencia del curso.</p>
      <p>No cambia respuestas anteriores, calificaciones ni el nivel de ayuda de cada estudiante.</p>
    </div>
  </details>

  {#if fallo}
    <Degradacion respuesta={fallo} alReintentar={cargar} />
  {/if}

  {#if cargando}
    <CargadorCubo mensaje="Consultando contexto de la clase…" pantallaCompleta />
  {:else if clases.length === 0}
    <div class="sin-clases">
      <Icono nombre="clases" medida={32} />
      <strong>Primero crea una clase</strong>
      <span>El contexto curricular pertenece a una clase concreta.</span>
    </div>
  {:else}
  <form class="tarjeta-formulario" onsubmit={(e) => { e.preventDefault(); guardar(); }}>
    <label class="selector-clase">
      <span>Clase que vas a configurar</span>
      <select use:menuDesplegable={claseSeleccionada} bind:value={claseSeleccionada} onchange={cargar} disabled={cargando}>
        {#each clases as clase (clase.id)}
          <option value={clase.id}>{clase.nombre}</option>
        {/each}
      </select>
    </label>
    {#if consultandoContexto}
      <CargadorCubo mensaje="Consultando contexto de la clase…" />
    {:else}

    <Campo etiqueta="Unidad que se está viendo" bind:valor={unidad}
           ayuda="Por ejemplo: reglas de derivación." />

    <fieldset class="notacion">
      <legend>Notación de las funciones trigonométricas</legend>
      <div class="lista-opciones">
        {#each NOTACIONES_CURSO as [valor, nombre, pista] (valor)}
          <label class="opcion-fila" class:activa={notacion === valor}>
            <input type="radio" name="notacion-curso" value={valor} bind:group={notacion} />
            <span class="circulo-radio" aria-hidden="true">
              <span class="punto-radio"></span>
            </span>
            <span class="cuerpo-opcion">
              <span class="nombre-opcion">{nombre}</span>
              <span class="pista">{pista}</span>
            </span>
          </label>
        {/each}
      </div>
    </fieldset>

    <Campo etiqueta="Notas para el sistema" bind:valor={observaciones} multilinea
           ayuda="Qué se ha visto ya en clase y qué todavía no." />


    <div class="acciones">

      <Boton tipo="submit">Guardar</Boton>
      {#if guardado}
        <span class="hecho">
          <Icono nombre="check" medida={13} />
          <span>Guardado</span>
        </span>
      {/if}
    </div>
    {/if}
  </form>
  {/if}
</PantallaDesplazable>

<style>
  .ayuda-contexto { align-self: flex-end; position: relative; z-index: 2; }
  .ayuda-contexto summary {
    display: grid; place-items: center; inline-size: 2.2rem; block-size: 2.2rem;
    border: 1px solid var(--trazo-suave); border-radius: 999px; cursor: pointer;
    color: var(--accent-main); background: var(--surface-paper); font-weight: 700;
    list-style: none;
  }
  .ayuda-contexto summary::-webkit-details-marker { display: none; }
  .ayuda-contexto > div {
    position: absolute; inset-inline-end: 0; margin-block-start: .5rem;
    inline-size: min(25rem, calc(100vw - 2rem)); padding: var(--espacio-md);
    border: 1px solid var(--trazo-suave); border-radius: var(--radius-md);
    background: var(--surface-paper); box-shadow: var(--shadow-float);
  }
  .ayuda-contexto p { margin: .5rem 0 0; max-inline-size: none; color: var(--ink-secondary); line-height: 1.5; }
  .selector-clase { display: grid; gap: .4rem; font-weight: 600; color: var(--ink-primary); }
  .selector-clase select {
    inline-size: 100%; min-block-size: 2.75rem; padding-inline: .8rem;
    border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm);
    background: var(--surface-paper); color: var(--ink-primary); font: inherit;
  }
  .sin-clases {
    display: grid; justify-items: center; gap: .5rem; padding: 3rem;
    border: 1px dashed var(--trazo-suave); border-radius: var(--radius-md);
    color: var(--ink-secondary); background: var(--surface-panel);
  }
  .tarjeta-formulario {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    padding: var(--espacio-md) var(--espacio-lg);
    max-inline-size: 48rem;
    align-self: center;
    inline-size: 100%;
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
  }

  fieldset.notacion {
    margin: 0;
    padding: 0;
    border: 0;
  }

  legend {
    padding: 0;
    margin-block-end: var(--espacio-xs);
    font-size: var(--texto-xs);
    font-weight: 600;
    color: var(--ink-secondary);
  }

  .lista-opciones {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-xs);
  }

  .opcion-fila {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: var(--espacio-sm);
    padding: var(--espacio-sm) var(--espacio-md);
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: var(--transition);
  }

  .opcion-fila:hover { border-color: var(--trazo); }
  .opcion-fila.activa { border-color: var(--accent-main); }

  .opcion-fila input[type="radio"] {
    position: absolute;
    opacity: 0;
    inline-size: 0;
    block-size: 0;
    pointer-events: none;
  }

  .circulo-radio {
    inline-size: 18px;
    block-size: 18px;
    border-radius: 50%;
    border: 1.5px solid var(--trazo);
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-block-start: 2px;
    transition: var(--transition);
  }

  .opcion-fila:hover .circulo-radio { border-color: var(--ink-secondary); }
  .opcion-fila.activa .circulo-radio { border-color: var(--accent-main); }

  .punto-radio {
    inline-size: 8px;
    block-size: 8px;
    border-radius: 50%;
    background: var(--accent-main);
    transform: scale(0);
    transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .opcion-fila.activa .punto-radio { transform: scale(1); }

  .cuerpo-opcion { display: flex; flex-direction: column; gap: 2px; }

  .nombre-opcion {
    font-family: var(--fuente-mono);
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-primary);
  }

  .pista {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    line-height: 1.35;
  }

  .acciones { display: flex; align-items: center; justify-content: center; gap: 0.7rem; }

  .hecho {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: var(--radius-pill, 9999px);
    background: var(--semantic-success-bg);
    color: var(--semantic-success);
    font-size: var(--texto-sm);
    font-weight: 600;
  }
</style>
