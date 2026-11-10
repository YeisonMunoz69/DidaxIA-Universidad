<!--
DD-13 · Los conceptos que el turno invocó.

Al lado de la conversación. Es lo que las docentes pidieron: que la regla
mencionada sea reconocible sin salir del hilo.

Se alimenta del campo `conceptos` del turno, que va a nivel de turno y no de
bloque: un mismo concepto puede aparecer en varios bloques y repetirlo no
aportaría nada.

DE DÓNDE SALE ESE CAMPO, DESDE `D-28`
--------------------------------------
Del **nodo del material que el turno citó**: las páginas del banco ancladas en
el `nodo_grafo` de los fragmentos que la recuperación usó de verdad. Un turno
sin corpus utilizable no invoca nada y el panel va vacío, por el mismo criterio
con que la procedencia declara `sin-fuente`.

⛔ **Nunca del diagnóstico.** `D-28` descarta por escrito alimentarlo con la
concepción candidata, y el motivo no es de contenido sino de puerta: este panel
lo abre el sistema y **acumula toda la conversación**, así que una concepción
diagnosticada quedaría a la vista turno tras turno. `RP-18`.

Por eso el rótulo dice «Para consultar» y no «Lo que se ha nombrado»: lo que
aquí aparece es material relacionado, no una lista de lo que el tutor dijo.

ACUMULA LOS DE LA CONVERSACIÓN, NO SOLO LOS DEL ÚLTIMO TURNO. Un panel que se
vacía en cada respuesta obligaría a subir por el hilo para reencontrar la regla
de hace dos turnos, que es exactamente lo que este panel existe para evitar.
Se deduplica por identificador, y quien no tiene identificador por su nombre.

NO DECIDE CUÁLES MOSTRAR. El servidor manda los que invocó y aquí se presentan
todos. Elegir sería tomar una decisión pedagógica en el cliente, que es lo que
§2 del contrato prohíbe.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
Origen de esta pieza: OE3-Implementacion/09-Aportes-de-la-Consulta-Docente.md

-->
<script>
  import EnlaceAConcepto from './EnlaceAConcepto.svelte';
  import { esNombreHumano } from '../../nucleo/presentacion/identificadores.js';

  let {
    /** Los conceptos ya acumulados por la conversación. */
    conceptos = [],
    alAbrir = null
  } = $props();

  const unicos = $derived(
    [...new Map(conceptos.map((c) => [c?.id || c?.nombre, c])).values()]
      .filter((c) => esNombreHumano(c?.nombre))
  );
</script>

{#if unicos.length}
  <aside class="panel" aria-labelledby="panel-conceptos-titulo">
    <h2 id="panel-conceptos-titulo">Para consultar</h2>
    <ul>
      {#each unicos as c (c.id || c.nombre)}
        <li><EnlaceAConcepto concepto={c} {alAbrir} /></li>
      {/each}
    </ul>
  </aside>
{/if}

<style>
  /*
    SIN CAJA PROPIA, Y ES UN CAMBIO DEL 2026-08-16.

    Llevaba fondo, relleno y radio. Desde que la conversación tiene un panel de
    contexto de verdad —una columna con su fondo y su borde—, esta pieza vive
    DENTRO de él: manteniendo su caja salían dos paneles anidados, uno con el
    fondo del otro, que es el aspecto que el lenguaje llama «saturado».

    Quien la monte en otro sitio le pone la caja fuera. Es la regla de siempre:
    el contenedor decide el continente.

    ⚠️ Se quita el ADORNO, no el elemento: nada de `display: contents`. Sacaría
    el `<aside>` del árbol de accesibilidad en más de un navegador, y con él la
    región y el nombre que `aria-labelledby` le da. Invisible no es lo mismo que
    inexistente.
  */
  .panel { display: flex; flex-direction: column; }

  h2 {
    margin: 0 0 0.5rem;
    font-size: var(--texto-xs);
    font-weight: 600;
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  ul { margin: 0; padding: 0; list-style: none; }

  /* Cada concepto es un objetivo pulsable, así que le toca el mínimo de
     `WCAG 2.2 · 2.5.8` — y con el dedo, los 44 que `base.css` fija. */
  li {
    display: flex;
    align-items: center;
    min-block-size: 24px;
    padding-block: 0.25rem;
    font-size: var(--texto-sm);
  }
</style>
