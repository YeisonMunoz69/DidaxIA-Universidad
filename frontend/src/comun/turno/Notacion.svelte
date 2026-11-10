<!--
Una expresión matemática renderizada.

Recibe la expresión YA NORMALIZADA por el backend. `RP-01` obliga a normalizar a
forma canónica única ANTES de procesar, y esa normalización es del servidor: si
el cliente también normalizara habría dos normalizadores y la garantía de forma
única dejaría de serlo.

La alternativa explícita sigue teniendo prioridad. Cuando el contenido editorial
no la trae, la expresión original se conserva como nombre accesible en vez de
inyectar una advertencia visible dentro del texto de la obra.

Si la expresión no se puede renderizar se muestra el fallo con la expresión en
crudo. No se adivina: `RP-18` dice que ante la imposibilidad de verificar el
estado seguro es no afirmar, y aquí el equivalente es no inventar una lectura.

UNA FÓRMULA LARGA SE DESPLAZA DENTRO DE SU CAJA, Y ESTO NO SE DEDUJO: SE MIDIÓ
------------------------------------------------------------------------------
KaTeX en `displayMode` deja el elemento `.katex` **más estrecho que lo que
pinta**. Medido el 2026-08-14 con la derivada de un cociente a 327 px de caja:
`.katex` declaraba **302 de ancho y su contenido medía 540**. Nada recortaba
—ningún ancestro tenía `overflow` distinto de `visible`— y la página **no
crecía a lo ancho**, así que el lado derecho de la fracción se pintaba fuera de
la caja y no había forma de llegar a él.

Eso es lo peor de un defecto de disposición: **la comprobación de que la página
no desborda lo da por bueno**, porque a nivel de página no desborda. La revisión
móvil del 2026-08-14 lo dio por bueno por eso mismo, hasta que se midió el
`scrollWidth` de la caja en vez del de la página.

Las tres declaraciones de abajo vienen del prototipo de la Calculadora
(`repo-2/frontend/src/components/ChatArea.svelte`), que se topó con lo mismo y
lo dejó comentado: *«las soluciones contienen fracciones largas»*. Se lleva la
técnica, no el código: allí vivía en la burbuja del mensaje y aquí vive en el
bloque de notación, que es quien sabe que su contenido es una fórmula.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

-->
<script>
  import { getContext } from 'svelte';
  import { copiaDeFormula, CONTEXTO_COPIA_FORMULAS } from './copiaDeFormula.js';
  const copiable = getContext(CONTEXTO_COPIA_FORMULAS) ?? false;
  import { renderizar } from '../../nucleo/formato/notacion.js';

  let {
    expresion = '',
    alternativo = '',
    /** true si va en su propia línea, false si va dentro de un párrafo. */
    bloque = false,
    compacto = false,
    agrandar = false
  } = $props();

  // `PM-F02`. El renderizado lo hace `nucleo/formato/notacion.js`, que envuelve
  // a KaTeX y **devuelve el fallo en vez de pintarlo en rojo**: una fórmula
  // medio dibujada es una afirmación a medias, y `RP-18` dice que ante lo que
  // no se puede sostener el estado seguro es no afirmar.
  const pintada = $derived(renderizar(expresion, { bloque, agrandar }));
  const listo = $derived(Boolean(pintada.html));
  const nombreAccesible = $derived(
    alternativo?.trim() || `Expresión matemática: ${expresion}`
  );
</script>

{#if listo}
  <span class="notacion" class:bloque class:compacto role="math"
        aria-label={nombreAccesible}>
    <!-- El marcado NO viene del servidor: lo produce KaTeX aquí a partir de
         una cadena que recibe como texto. Es la diferencia con `Prosa.svelte`,
         donde `{@html}` está prohibido porque el contenido lo compone un
         modelo de lenguaje. Ver la cabecera de `nucleo/formato/notacion.js`. -->
    <span class="formula" use:copiaDeFormula={{habilitada:copiable,expresion}}>{@html pintada.html}</span>
  </span>
{:else}
  <!-- No se adivina la lectura. Se enseña la expresión en crudo, que es lo
       que de verdad llegó, y se dice que no se pudo interpretar. -->
  <span class="fallo">
    No se pudo mostrar la expresión
    {#if expresion}<code class="crudo">{expresion}</code>{/if}
  </span>
{/if}

<style>
  .notacion {
    font-family: var(--fuente-mono);
    background: var(--surface-panel);
    padding: 0.1em 0.35em;
    border-radius: var(--radius-xs);
  }

  .bloque {
    display: block;
    padding: 0.8em 1em;
    margin-block: 0.6em;
    text-align: center;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-soft);
    /* La barra sale sola cuando hace falta y no cuando no. Ver la cabecera. */
    overflow-x: auto;
  }

  .bloque.compacto {
    padding: 0.35em 0.6em;
    margin-block: 0.25em;
    font-size: var(--texto-sm);
  }

  /*
    `:global` porque este marcado lo genera KaTeX, no la plantilla: sin él
    Svelte quita las dos reglas al no encontrar quien las use, y el defecto
    vuelve sin que nadie toque nada.

    `max-content` para que el elemento mida lo que de verdad pinta —es la mitad
    que falta, y sin ella `overflow-x` no tiene nada que desplazar—; `100 %` de
    mínimo para que una fórmula corta siga centrada en toda la caja.
  */
  .bloque :global(.katex-display) {
    inline-size: max-content;
    min-inline-size: 100%;
    margin: 0;
  }

  .bloque :global(.katex-display > .katex) { white-space: nowrap; }

  .fallo {
    font-size: var(--texto-sm);
    color: var(--semantic-error);
  }

  .crudo {
    font-family: var(--fuente-mono);
    margin-inline-start: 0.4em;
  }
</style>
