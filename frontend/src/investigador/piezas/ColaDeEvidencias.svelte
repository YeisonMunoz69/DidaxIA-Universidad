<!--
La cola de autorizaciones por revisar · `EQ-023` / C2B.

Filtros, lista y continuación. No decide nada sobre una evidencia: sólo dice
cuál se está mirando.

PAGINA CON EL CURSOR DEL SERVIDOR, Y CON NADA MÁS
---------------------------------------------------
No hay número de página, ni desplazamiento, ni un total. Se pide la primera
página, se guarda el `cursor_siguiente` que venga y se pide la siguiente con él;
cuando llega `null`, se acabó. **El cursor no se compone ni se manipula**: es
opaco a propósito, y un cliente que intentara construirlo dependería de una
forma interna que el backend puede cambiar sin avisar.

Por eso el gesto es «cargar más» y no «página 3». Con paginación por cursor no
existe la página 3 —existe «lo que sigue a esto»— y ofrecer un número obligaría
a inventarlo.

EL TOTAL NO SE ENSEÑA, Y NO ES UN OLVIDO
------------------------------------------
`ColaDeSupervision.svelte` sí lo enseña, y hace bien: allí sirve para decidir
cómo muestrear. Aquí el backend no lo devuelve, y no lo devuelve a propósito —
contar exige recorrer la tabla entera en cada página—. Inventar un «al menos N»
a partir de lo cargado diría algo distinto cada vez que alguien pulsa «cargar
más», que es peor que no decir nada.

SELECCIONAR NO CAMBIA LA DIRECCIÓN
------------------------------------
Los elementos son botones, no enlaces. El identificador de la autorización de un
menor no tiene por qué quedarse en el historial del navegador ni en una
dirección que se copia y se pega. `07` §11 ya dice que las guardas del cliente
son cortesía; esto es lo contrario —una decisión sobre qué NO se publica— y se
sostiene sola.



-->
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import FilaDeEvidencia from './FilaDeEvidencia.svelte';
  import EstadoVacio from '../../docente/piezas/EstadoVacio.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import { FILTROS } from '../../nucleo/api/evidencias.js';

  let {
    /** Las evidencias ya cargadas, acumuladas página a página. */
    evidencias = [],
    /** El filtro vigente. `$bindable` porque el selector lo escribe. */
    filtro = $bindable('pendiente'),
    /** Identificador de la que está abierta, o `0`. */
    seleccionada = 0,
    /** Si hay una petición en vuelo. */
    cargando = false,
    /** Si queda otra página: el servidor mandó `cursor_siguiente`. */
    hayMas = false,
    /** `describir(error)` o `null`. */
    fallo = null,
    alSeleccionar,
    alCargarMas,
    alReintentar
  } = $props();

  const ROTULOS = {
    pendiente: 'Sin revisar',
    aprobada: 'Aprobadas',
    rechazada: 'Rechazadas',
    todos: 'Todas'
  };

  /**
   * Cuántas filas cargadas comparte cada estudiante.
   *
   * Se cuenta sobre lo que hay en pantalla y el rótulo lo dice así —«en la
   * lista»— porque es lo único cierto: el servidor no informa cuántos intentos
   * tiene una persona en total, y decir «3 intentos» cuando podrían ser cinco
   * sería una cifra inventada sobre una decisión que alguien va a tomar.
   */
  const porSujeto = $derived(
    evidencias.reduce((cuenta, e) => {
      cuenta[e.sujeto] = (cuenta[e.sujeto] ?? 0) + 1;
      return cuenta;
    }, {})
  );

  const vacia = $derived(!cargando && !fallo && evidencias.length === 0);
</script>

<section class="cola" aria-label="Cola de autorizaciones">
  <fieldset class="filtros">
    <legend class="solo-lectura-asistida">Filtrar por estado</legend>
    {#each FILTROS as valor (valor)}
      <label class="opcion" class:activa={filtro === valor}>
        <input type="radio" name="estado-de-evidencia" value={valor} bind:group={filtro} />
        <span>{ROTULOS[valor]}</span>
      </label>
    {/each}
  </fieldset>

  {#if fallo}
    <!-- `EQ-024` · un 403 o un 503 NO se pintan como lista vacía. Decirle a
         una investigadora que su cola está limpia cuando le retiraron el rol,
         o cuando la base no responde, es una mentira que se puede actuar. -->
    <Degradacion respuesta={fallo} alReintentar={fallo.reintentable ? alReintentar : null} />
  {/if}

  {#if cargando && evidencias.length === 0}
    <CargadorCubo mensaje="Cargando la cola…" pantallaCompleta />
  {/if}

  {#if vacia}
    <EstadoVacio
      icono="check"
      tono="exito"
      texto={filtro === 'pendiente'
        ? 'No queda ninguna autorización por revisar.'
        : 'Ninguna autorización con este filtro.'} />
  {/if}

  {#if evidencias.length}
    <ul class="lista">
      {#each evidencias as e (e.evidencia)}
        <li>
          <FilaDeEvidencia
            evidencia={e}
            seleccionada={seleccionada === e.evidencia}
            hermanos={porSujeto[e.sujeto] ?? 1}
            {alSeleccionar} />
        </li>
      {/each}
    </ul>
  {/if}

  {#if hayMas}
    <div class="continuar">
      <Boton variante="secundario" deshabilitado={cargando} onclick={alCargarMas}>
        {cargando ? 'Cargando…' : 'Cargar más'}
      </Boton>
    </div>
  {/if}
</section>

<style>
  .cola {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    min-inline-size: 0;
  }

  .filtros {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0;
    padding: 0;
    border: 0;
  }

  .opcion {
    padding: 4px 12px;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-pill, 9999px);
    background: var(--surface-panel);
    color: var(--ink-secondary);
    font-size: var(--texto-sm);
    font-weight: 600;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .opcion:hover { border-color: var(--accent-main); color: var(--accent-main); }

  .opcion.activa {
    border-color: var(--accent-main);
    background: var(--accent-surface);
    color: var(--accent-main);
  }

  /* El radio real sigue en el árbol —lo necesita el teclado y el lector de
     pantalla—, sólo que no se dibuja: la píldora es su presentación.
     `:focus-visible` del control pinta el anillo sobre la etiqueta. */
  .opcion input {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }

  .opcion:has(input:focus-visible) {
    outline: 2px solid var(--accent-main);
    outline-offset: 2px;
  }

  .lista {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  /* `estilos/tipografia.css` trae `:where(p, li) { max-inline-size:
     var(--ancho-lectura) }` global; sin esto cada fila queda capada al ancho
     de lectura aunque la columna tenga más. Mismo mecanismo documentado en
     `ColaDeSupervision.svelte::.lista > li`. */
  .lista > li { max-inline-size: none; }

  .continuar { display: flex; justify-content: center; }
</style>
