<!--
Un párrafo del banco de conceptos, con su notación dibujada.

Las páginas de `DD-13` son Markdown escrito por docentes y llegan con `$x^3$`,
`**así**` y `` `C-M18` `` dentro. Pintarlas como texto plano enseña las marcas;
convertirlas a HTML y volcarlas con `{@html}` abriría la puerta que
`Prosa.svelte` tiene cerrada a propósito.

Por eso `trozos()` devuelve una lista con su tipo y aquí se elige el elemento
para cada uno. **El único `{@html}` es el de KaTeX**, que genera su marcado en
este proceso a partir de texto — la misma justificación que `notacion.js` ya
escribe, y no una nueva.

Una fórmula que KaTeX no entiende NO se pinta a medias: se enseña su fuente
entre comillas de código. `RP-18`: ante lo que no se puede sostener, el estado
seguro es no afirmar, y media fórmula es una afirmación a medias.



-->
<script>
  import { renderizar, trozos } from '../../nucleo/formato/notacion.js';

  let { texto = '' } = $props();

  /**
   * Los cortes de línea del archivo NO son cortes de línea del texto.
   *
   * El banco está escrito con las líneas cortadas a mano a unos noventa
   * caracteres, que es cómodo para revisarlo en el editor y sale ilegible en
   * una pantalla estrecha: cada corte se convertiría en un renglón. Se unen los
   * saltos sueltos y se conservan los dobles, que en Markdown separan párrafos.
   *
   * NO se unen los que preceden a una viñeta, una tabla o una cita: ahí el
   * salto sí significa algo, y unirlos fundiría una lista en un párrafo. La
   * continuación SANGRADA de una viñeta sí se une —es la misma frase partida
   * por el ancho del editor—; tratarla como línea aparte rompía cada viñeta
   * larga en dos, que es lo que se vio en el navegador el 2026-08-11.
   */
  const plano = $derived(
    String(texto ?? '').replace(/([^\n])\n(?!\n|[ \t]*[-*|>#]|[ \t]*$)/g, '$1 ')
  );

  /**
   * Los bloques editoriales del texto: párrafos, listas, citas y tablas.
   *
   * Una viñeta se pinta como viñeta y no como una línea que empieza por guion.
   * Es la única estructura que el banco usa además del párrafo, así que no hace
   * falta un conversor de Markdown para reconocerla — y no tenerlo es lo que
   * mantiene cerrada la puerta del `{@html}`.
   */
  const bloques = $derived(agrupar(plano));

  function agrupar(fuente) {
    const salida = [];
    const lineas = fuente.split('\n');
    for (let indice = 0; indice < lineas.length; indice += 1) {
      const linea = lineas[indice];
      const viñeta = /^\s*[-*]\s+(.*)$/.exec(linea);
      const numerada = /^\s*\d+[.)]\s+(.*)$/.exec(linea);
      const cita = /^\s*>\s?(.*)$/.exec(linea);
      const subtitulo = /^\s*#{1,6}\s+(.*)$/.exec(linea);
      const ultimo = salida[salida.length - 1];
      if (viñeta) {
        if (ultimo?.tipo === 'lista') ultimo.lineas.push(viñeta[1]);
        else salida.push({ tipo: 'lista', lineas: [viñeta[1]] });
      } else if (numerada) {
        if (ultimo?.tipo === 'numerada') ultimo.lineas.push(numerada[1]);
        else salida.push({ tipo: 'numerada', lineas: [numerada[1]] });
      } else if (cita) {
        if (ultimo?.tipo === 'cita') ultimo.lineas.push(cita[1]);
        else salida.push({ tipo: 'cita', lineas: [cita[1]] });
      } else if (subtitulo) {
        salida.push({ tipo: 'subtitulo', lineas: [subtitulo[1]] });
      } else if (/^\s*\|.*\|\s*$/.test(linea)) {
        const filas = [];
        let cursor = indice;
        while (cursor < lineas.length && /^\s*\|.*\|\s*$/.test(lineas[cursor])) {
          filas.push(lineas[cursor].trim().slice(1, -1).split('|').map((celda) => celda.trim()));
          cursor += 1;
        }
        indice = cursor - 1;
        const separador = filas.findIndex((fila) => fila.every((celda) => /^:?-{3,}:?$/.test(celda)));
        if (separador >= 0) filas.splice(separador, 1);
        if (filas.length) salida.push({ tipo: 'tabla', lineas: filas });
      } else if (linea.trim()) {
        if (ultimo?.tipo === 'parrafo') ultimo.lineas.push(linea);
        else salida.push({ tipo: 'parrafo', lineas: [linea] });
      } else {
        salida.push({ tipo: 'corte', lineas: [] });
      }
    }
    return salida.filter((b) => b.tipo !== 'corte');
  }

  const partir = (t) =>
    trozos(t).map((p) => (p.tipo === 'formula' ? { ...p, ...renderizar(p.valor, { agrandar: true }) } : p));
</script>

{#snippet pintar(fuente)}{#each partir(fuente) as p, i (i)}{#if p.tipo === 'texto'}{p.valor}{:else if p.tipo === 'enfasis'}<strong>{p.valor}</strong>{:else if p.tipo === 'matiz'}<em>{p.valor}</em>{:else if p.tipo === 'codigo'}<code>{p.valor}</code>{:else if p.html}<span class="formula">{@html p.html}</span>{:else}<code class="sin-dibujar">{p.valor}</code>{/if}{/each}{/snippet}

{#each bloques as b, i (i)}
  {#if b.tipo === 'lista'}
    <ul class="texto">
      {#each b.lineas as l, j (j)}<li>{@render pintar(l)}</li>{/each}
    </ul>
  {:else if b.tipo === 'numerada'}
    <ol class="texto">
      {#each b.lineas as l, j (j)}<li>{@render pintar(l)}</li>{/each}
    </ol>
  {:else if b.tipo === 'cita'}
    <blockquote class="texto">{@render pintar(b.lineas.join(' '))}</blockquote>
  {:else if b.tipo === 'subtitulo'}
    <h4>{@render pintar(b.lineas[0])}</h4>
  {:else if b.tipo === 'tabla'}
    <!-- svelte-ignore a11y_no_noninteractive_tabindex
         La caja recibe foco para desplazar tablas anchas con el teclado. -->
    <div class="tabla-desplazable" tabindex="0" role="region" aria-label="Tabla del concepto">
      <table>
        <tbody>
          {#each b.lineas as fila, filaIndice (filaIndice)}
            <tr>
              {#each fila as celda, celdaIndice (celdaIndice)}
                <td class:encabezado={filaIndice === 0}>{@render pintar(celda)}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <p class="texto">{@render pintar(b.lineas.join(' '))}</p>
  {/if}
{/each}

<style>
  .texto {
    margin: 0 0 0.5rem;
    font-size: var(--texto-base);
    color: var(--ink-secondary);
  }

  ul.texto, ol.texto { padding-inline-start: 1.35rem; }

  li { padding-block: 0.15rem; }

  code { font-family: var(--fuente-mono); font-size: 0.92em; }

  blockquote.texto {
    padding: .75rem 1rem;
    border-inline-start: 3px solid var(--accent-main);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    background: var(--accent-surface);
    color: var(--ink-secondary);
  }

  h4 {
    margin: .9rem 0 .45rem;
    color: var(--ink-primary);
    font-size: var(--texto-sm);
  }

  .tabla-desplazable {
    max-inline-size: 100%;
    margin-block: .75rem;
    overflow-x: auto;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
  }

  table { inline-size: 100%; border-collapse: collapse; font-size: var(--texto-sm); }
  td { min-inline-size: 8rem; padding: .55rem .7rem; border-block-end: 1px solid var(--trazo-suave); color: var(--ink-secondary); }
  tr:last-child td { border-block-end: 0; }
  td.encabezado { background: var(--surface-canvas); color: var(--ink-primary); font-weight: 700; }

  /* No se pinta como fórmula lo que no se pudo dibujar. */
  .sin-dibujar { color: var(--ink-tertiary); }
</style>
