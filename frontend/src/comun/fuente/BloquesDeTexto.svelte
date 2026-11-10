<!--
El texto del corpus, pintado desde bloques tipados.

NO HAY NINGÚN `{@html}` EN ESTE ARCHIVO, Y ÉSA ES LA PROPIEDAD
---------------------------------------------------------------
El backend no entrega Markdown ni HTML: entrega una lista de bloques con tipo
—párrafo, lista, tabla, matemática, regla— y dentro de cada uno una lista de
trozos con tipo —texto, énfasis, fuerte, código, matemática, enlace—. Este
componente los pinta con elementos de Svelte y nodos de texto.

La consecuencia es que **la categoría de ataque no existe**. Un `<script>`
escrito dentro de un fragmento del corpus llega hasta aquí como los catorce
caracteres que es, y se pinta como texto. No hay nada que sanear porque no hay
ninguna cadena de HTML en ningún punto del camino.

Es deliberadamente distinto de sanear: sanear deja siempre la duda de si se
quitó todo. Aquí no hay duda que resolver.

LOS ENLACES
-------------
Sólo llegan con esquema `http` o `https` —el backend degrada cualquier otro a
texto y lo cuenta—, y aun así se pintan con `rel="noopener noreferrer"` y
`target="_blank"`: son de fuera y no deben poder tocar esta pestaña.

LA MATEMÁTICA
--------------
Se delega en `Notacion.svelte`, que es la pieza que el proyecto ya tiene para
esto. Construir un segundo renderizador aquí crearía dos formas de pintar la
misma fórmula, que es justo la deuda que la Fase 6 viene a cerrar; esta fase no
la agrava.



-->
<script>
  import Notacion from '../turno/Notacion.svelte';

  let {
    /** { bloques: [...], enlaces_rechazados: [...], truncado: bool } */
    contenido
  } = $props();

  const bloques = $derived(contenido?.bloques ?? []);

  /** Los tipos de bloque que este componente sabe pintar. Lista cerrada. */
  const CONOCIDOS = [
    'parrafo',
    'encabezado',
    'lista',
    'cita',
    'matematica',
    'tabla',
    'regla'
  ];

  function conocido(tipo) {
    return CONOCIDOS.includes(tipo);
  }

  /** El nivel de encabezado, acotado a h3–h6. */
  function etiquetaDeEncabezado(nivel) {
    const n = Math.min(Math.max(Number(nivel) || 3, 3), 6);
    return `h${n}`;
  }
</script>

{#snippet trozos(lista)}
  {#each lista ?? [] as trozo, i (i)}
    {#if trozo.tipo === 'matematica'}
      <Notacion expresion={trozo.texto} />
    {:else if trozo.tipo === 'fuerte'}
      <strong>{trozo.texto}</strong>
    {:else if trozo.tipo === 'enfasis'}
      <em>{trozo.texto}</em>
    {:else if trozo.tipo === 'codigo'}
      <code>{trozo.texto}</code>
    {:else if trozo.tipo === 'enlace'}
      <a href={trozo.destino} target="_blank" rel="noopener noreferrer">
        {trozo.texto}
        <span class="externo" aria-hidden="true">↗</span>
        <span class="solo-lectores"> (se abre en otra pestaña)</span>
      </a>
    {:else}
      {trozo.texto}
    {/if}
  {/each}
{/snippet}

<div class="texto-del-corpus">
  {#each bloques as bloque, indice (indice)}
    {#if bloque.tipo === 'parrafo'}
      <p>{@render trozos(bloque.trozos)}</p>
    {:else if bloque.tipo === 'encabezado'}
      <svelte:element this={etiquetaDeEncabezado(bloque.nivel)}>
        {@render trozos(bloque.trozos)}
      </svelte:element>
    {:else if bloque.tipo === 'matematica'}
      <div class="formula"><Notacion expresion={bloque.latex} bloque /></div>
    {:else if bloque.tipo === 'lista' && bloque.ordenada}
      <ol>
        {#each bloque.elementos as elemento, i (i)}
          <li>{@render trozos(elemento)}</li>
        {/each}
      </ol>
    {:else if bloque.tipo === 'lista'}
      <ul>
        {#each bloque.elementos as elemento, i (i)}
          <li>{@render trozos(elemento)}</li>
        {/each}
      </ul>
    {:else if bloque.tipo === 'cita'}
      <blockquote>{@render trozos(bloque.trozos)}</blockquote>
    {:else if bloque.tipo === 'tabla'}
      <!-- La tabla se desplaza dentro de su caja y NO empuja la página: en
           360 px una tabla de cinco columnas rompería el ancho del documento
           entero. La regla vive aquí y no en el ancestro por eso.

           `tabindex="0"` SOBRE UNA REGIÓN NO INTERACTIVA ES DELIBERADO.
           Un contenedor que se desplaza y no se puede enfocar es inalcanzable
           para quien no usa ratón: no hay forma de llevar el foco dentro para
           empujarlo con las flechas. El patrón recomendado —`role="region"`
           con nombre accesible y `tabindex="0"`— es justo el que la regla
           general desaconseja, porque la regla no distingue un contenedor
           desplazable de un `div` cualquiera. Aquí sí importa la diferencia. -->
      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
      <div class="tabla-desplazable" tabindex="0" role="region" aria-label="Tabla del material">
        <table>
          <thead>
            <tr>
              {#each bloque.encabezados as celda, i (i)}
                <th scope="col">{@render trozos(celda)}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each bloque.filas as fila, f (f)}
              <tr>
                {#each fila as celda, c (c)}
                  <td>{@render trozos(celda)}</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else if bloque.tipo === 'regla'}
      <hr />
    {:else if !conocido(bloque.tipo)}
      <!-- Un tipo que este componente no conoce NO se pinta como párrafo por
           si acaso: se declara. Callarlo dejaría al estudiante leyendo algo
           cuya forma nadie decidió, y al equipo sin saber que el contrato
           creció. -->
      <p class="desconocido">
        Este material trae una parte que esta versión todavía no sabe mostrar.
      </p>
    {/if}
  {/each}

  {#if contenido?.truncado}
    <p class="aviso">
      El material es muy extenso y aquí se muestra sólo su comienzo.
    </p>
  {/if}
</div>

<style>
  /* ⚠️ **Nombre propio y no `.texto`.**
     El armazón ya tiene una clase `texto` —la del bloque «Tu cuenta» del
     carril— y las dos convivían en el mismo documento. No rompía el estilo,
     porque Svelte los aísla, pero sí rompía cualquier consulta por clase: la
     prueba de navegador medía el carril creyendo que medía el corpus. Se vio
     en Chromium, no en jsdom. */
  .texto-del-corpus {
    color: var(--ink-primary);
    line-height: 1.65;
    /* `anywhere` y no `break-word`, y la diferencia se ve en un teléfono.
       Las dos parten una palabra que no cabe, pero **sólo `anywhere` cuenta
       para el ancho mínimo del contenido**: con `break-word`, una palabra
       larguísima —o el nombre de un teorema sin espacios— sigue fijando el
       ancho intrínseco del bloque, y el contenedor flex del armazón crece con
       él. Medido en Chromium a 360 px. */
    overflow-wrap: anywhere;
    min-width: 0;
  }

  .texto-del-corpus :global(p) {
    margin: 0 0 var(--espacio-md);
  }

  .texto-del-corpus :global(h3),
  .texto-del-corpus :global(h4),
  .texto-del-corpus :global(h5),
  .texto-del-corpus :global(h6) {
    margin: var(--espacio-lg) 0 var(--espacio-sm);
    line-height: 1.3;
  }

  ol,
  ul {
    margin: 0 0 var(--espacio-md);
    padding-inline-start: 1.5em;
  }

  li {
    margin-bottom: var(--espacio-xs);
  }

  blockquote {
    margin: 0 0 var(--espacio-md);
    padding: var(--espacio-sm) var(--espacio-md);
    border-inline-start: 3px solid var(--trazo-suave);
    color: var(--ink-secondary);
  }

  .formula {
    margin: var(--espacio-md) 0;
    overflow-x: auto;
  }

  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.92em;
    background: var(--surface-panel);
    border-radius: var(--radius-xs);
    padding: 0.1em 0.35em;
  }

  hr {
    border: 0;
    border-top: 1px solid var(--trazo-suave);
    margin: var(--espacio-lg) 0;
  }

  .tabla-desplazable {
    overflow-x: auto;
    /* Con `min-width: 0` en el artículo, esto cierra la otra mitad: la caja no
       se pasa de su contenedor aunque la tabla de dentro sea más ancha. */
    max-width: 100%;
    margin: 0 0 var(--espacio-md);
    /* Se puede enfocar para desplazarla con el teclado: sin esto, una tabla
       ancha es inalcanzable para quien no usa ratón. */
    border-radius: var(--radius-sm);
  }

  .tabla-desplazable:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 2px;
  }

  table {
    border-collapse: collapse;
    min-width: 100%;
    font-size: var(--texto-sm);
  }

  th,
  td {
    border: 1px solid var(--trazo-suave);
    padding: var(--espacio-xs) var(--espacio-sm);
    text-align: start;
    vertical-align: top;
  }

  th {
    background: var(--surface-panel);
  }

  a {
    color: var(--accent-main);
  }

  .externo {
    font-size: 0.85em;
  }

  .desconocido,
  .aviso {
    font-size: var(--texto-sm);
    color: var(--semantic-warning);
    background: var(--semantic-warning-bg);
    padding: var(--espacio-sm) var(--espacio-md);
    border-radius: var(--radius-sm);
  }

  .solo-lectores {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    padding: 0;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
</style>
