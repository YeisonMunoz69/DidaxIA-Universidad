<!--
Filtrado de la cola.

Por urgencia, curso o tipo.

FILTRAR ES LO QUE HACE POSIBLE LA REVISIÓN POR MUESTREO. `RU-12` diseña la cola
para revisión por muestreo y por excepción, no para revisarlo todo; sin filtros,
«por excepción» no se puede ejercer y la única estrategia disponible es bajar
por la lista, que es la que el requisito descarta.

Los controles nativos conservan el contrato de filtros de DD-05. La mejora
compartida menuDesplegable añade la lista visual, búsqueda y cierre con Escape;
las pruebas verifican teclado, labels, bloqueo y valores tipados.



-->
<script>
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  let {
    /** { urgencia, clase, tipo } — se enlaza con la ruta. */
    filtros = $bindable({ urgencia: '', clase: '', tipo: '' }),
    /** Las clases del docente, para no escribirlas a mano. */
    clases = []
  } = $props();

  const URGENCIAS = [['', 'Cualquier urgencia'], ['alta', 'Alta'],
                     ['normal', 'Normal'], ['baja', 'Baja']];
  const TIPOS = [['', 'Cualquier tipo'], ['respuesta', 'Respuesta al estudiante'],
                 ['sin-fuente', 'Sin material que la respalde'],
                 ['degradado', 'Turno degradado']];
</script>

<fieldset class="filtros">
  <legend>Acotar la cola</legend>

  <label>
    Urgencia
    <select use:menuDesplegable={filtros.urgencia} bind:value={filtros.urgencia}>
      {#each URGENCIAS as [v, t] (v)}<option value={v}>{t}</option>{/each}
    </select>
  </label>

  <label>
    Clase
    <select use:menuDesplegable={filtros.clase} bind:value={filtros.clase}>
      <option value="">Cualquier clase</option>
      {#each clases as c (c.id)}<option value={c.id}>{c.nombre}</option>{/each}
    </select>
  </label>

  <label>
    Tipo
    <select use:menuDesplegable={filtros.tipo} bind:value={filtros.tipo}>
      {#each TIPOS as [v, t] (v)}<option value={v}>{t}</option>{/each}
    </select>
  </label>
</fieldset>

<style>
  .filtros {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 1.1rem;
    margin: 0;
    padding: var(--espacio-md) var(--espacio-lg);
    background: var(--surface-panel);
    /* Marco de la REGIÓN de filtros: separa, no delimita un control. */
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
  }

  /* `margin-block-start` negativo: sin esto, el navegador coloca el
     `<legend>` A CABALLO del borde superior del `<fieldset>` —es
     literalmente para qué existe la «muesca» nativa de un legend—, así
     que el trazo recto del borde asomaba por debajo de la píldora
     redondeada en vez de quedar tapado del todo. Reportado como «se ve lo
     que pasa por detrás». Se levanta la píldora entera por encima de la
     línea del borde en vez de dejarla superpuesta. */
  legend {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    margin-inline-start: -2px;
    margin-block-start: -0.9em;
    border-radius: var(--radius-pill, 9999px);
    background: var(--accent-surface);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 600;
    border: 1px solid var(--accent-main);
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.3em;
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
    font-weight: 500;
  }

  /* Un `<select use:menuDesplegable>` SÍ es un control: `1.4.11` le pide 3.0 y `--ink-ghost` está
     exento de medirse. Los tres de esta cola ya salieron una vez por debajo del
     objetivo táctil —medidos en 31 px el 2026-08-14— y el borde era la otra
     mitad del mismo descuido.

     `appearance: none` + flecha propia · 2026-08-22 · sin esto, al hacer
     clic el navegador pinta SU chrome nativo del control —distinto en cada
     sistema, y ajeno al lenguaje «tinta y papel»—, reportado como «un
     estilo feo». La flecha se dibuja con dos gradientes en vez de una
     imagen: hereda `currentColor` a través de un token, no un archivo
     aparte que mantener. */
  select {
    padding: 0.5em 2.1em 0.5em 0.7em;
    background-color: var(--surface-paper);
    background-image:
      linear-gradient(45deg, transparent 50%, var(--ink-secondary) 50%),
      linear-gradient(135deg, var(--ink-secondary) 50%, transparent 50%);
    background-position:
      calc(100% - 1.1em) center,
      calc(100% - 0.75em) center;
    background-size: 0.35em 0.35em;
    background-repeat: no-repeat;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-trazado);
    color: var(--ink-primary);
    font-size: var(--texto-sm);
    font-family: inherit;
    appearance: none;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  select:hover { border-color: var(--ink-tertiary); }

  /* `:focus`, no `:focus-visible`: un `<select use:menuDesplegable>` es un desplegable que se
     abre al hacer clic, y quien lo abrió con el mouse necesita ver el
     mismo aro que quien llega por teclado — no es el caso de un botón
     cualquiera, donde `:focus-visible` evita un aro en cada clic. */
  select:focus {
    border-color: var(--accent-main);
    outline: none;
    box-shadow: 0 0 0 2px var(--accent-glow);
  }
</style>
