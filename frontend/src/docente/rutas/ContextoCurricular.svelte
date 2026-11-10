<!--
Configuración del contexto del curso.

Qué se está viendo, con qué notación, con qué material.

ES LO ÚNICO QUE EL DOCENTE CONFIGURA DEL SISTEMA, y por eso conviene decir qué
NO configura: no fija el nivel de ayuda —eso es dominio y lo decide el
servidor—, no elige qué se le responde a quién, y no toca el corpus. Conserva
una referencia curricular propia de cada clase para el trabajo docente.

LA NOTACIÓN IMPORTA MÁS DE LO QUE PARECE. Un curso que escribe `sen` y un
sistema que responde `sin` producen un desajuste que el estudiante lee como
error suyo. Es el tipo de fricción que la consulta docente señaló y que no
cuesta nada evitar.



-->
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

  /**
   * `[valor, nombre, pista]`. Las mismas dos opciones que ya aceptaba el
   * servidor —`panel_docente.py` no da para más: «qué ES un contexto
   * curricular» sigue sin decidirse como producto (`PM-B21`)—, con una
   * frase de una línea explicando la diferencia en vez de dejar que el
   * nombre solo hable por sí mismo.
   */
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
    <!-- Una columna, no dos: la rejilla lado a lado que se probó primero
         se pidió deshacer — Unidad arriba, Notación debajo de eso. -->
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

    <!-- `justify-content: center`: el botón quedaba a la izquierda del
         todo, «a un lado» — se pidió que fuera al centro de su fila. -->
    <div class="acciones">
      <!-- Sin icono: el texto ya dice lo que hace, y el «check» a 14px se
           leía como un adorno suelto —«el churito»— más que como parte del
           botón. Mismo criterio que el botón de crear clase del modal de
           `MisClases.svelte`. -->
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
  /* El envoltorio de scroll —antes `.contexto-desplazable`/`.contexto` en
     este archivo— se extrajo a `docente/piezas/PantallaDesplazable.svelte`
     el 2026-08-22, junto con las otras tres copias casi idénticas del
     mismo arreglo. Esta pantalla es la única que le pasa props no
     default: `anchoMaximo="min(70rem, 100%)"` en vez de 78rem
     —`.tarjeta-formulario` de más abajo ya limita su propio ancho a
     48rem, así que 78rem le sobraba de más—, y `relleno`/`espacio` más
     ajustados —ver el comentario de `.tarjeta-formulario` sobre el
     scroll mínimo que motivó el recorte—. */
  .tarjeta-formulario {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    /* Relleno vertical más ajustado que el horizontal, mismo motivo que
       el `relleno`/`espacio` que este archivo le pasa a
       `PantallaDesplazable` más arriba — al volver a una sola columna
       (Unidad arriba, Notación debajo), el formulario creció en alto y a
       ventanas de ~650-715px de alto —una laptop común, sin pantalla
       completa— aparecía un scroll mínimo, más molesto que útil. */
    padding: var(--espacio-md) var(--espacio-lg);
    /* Una columna: «Unidad» y «Notación» van una debajo de la otra, no
       lado a lado —se probó la rejilla de dos columnas y se pidió
       deshacerla—, así que el formulario vuelve a un ancho de lectura
       cómodo en vez de estirarse para llenar dos columnas. */
    max-inline-size: 48rem;
    /* Centra el formulario DENTRO de `.contexto`, que es más ancho que
       él: sin esto, un elemento con `max-inline-size` propio en un
       contenedor `flex-direction: column` se queda pegado al borde de
       inicio (izquierda) en vez de centrarse — reportado como «muy
       pegado al lado izquierdo». */
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

  /*
    Mismo estilo de opción que `comun/preferencias/Ajustes.svelte` y
    `estudiante/piezas/ElegirNotacion.svelte` —radio nativo oculto,
    círculo dibujado aparte—, reutilizado en vez de reinventado: son tres
    sitios que preguntan «¿cuál de estas dos/tres cosas?» con la misma
    forma visual, y antes este era el único con `<input>` a secas sin
    ningún estilo. Ver el comentario de `Ajustes.svelte::.opcion-fila`.
  */
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

  /* `justify-content: center`: el botón se veía «a un lado» —pegado al
     borde de inicio del formulario— y se pidió que quedara al centro de
     su fila. */
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
