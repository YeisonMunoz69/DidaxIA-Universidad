<!--
Un elemento de la cola.

Qué se iba a decir, en qué contexto, y las tres acciones.

LAS TRES ACCIONES NO SON DOS. Aprobar, editar y rechazar. Un docente que
corrige antes de aprobar está haciendo algo distinto de aprobar, y el registro
tiene que poder distinguirlos: `RP-17` pide poder reconstruir qué se emitió y
quién lo decidió. Fundir «editar» en «aprobar» perdería justo esa diferencia.

RECHAZAR TAMBIÉN CORRIGE. La propuesta queda registrada como rechazada, pero el
texto que escribe el docente llega al estudiante como aclaración. Así la acción
no es un descarte silencioso ni duplica el significado de «aprobar».

LO QUE SE MUESTRA ES LO QUE SE IBA A DECIR, con sus sellos. El docente revisa
la respuesta como la vería el estudiante, y por eso reutiliza `Turno` en vez de
un formato propio: revisar sobre una representación distinta de la que se emite
es revisar otra cosa.

Y CUANDO NO HUBO RESPUESTA, SE PINTA LA DEGRADACION Y NO UN HUECO
------------------------------------------------------------------
La mitad de lo que entra en esta cola son turnos que degradaron: su `turno` es
`{ situacion, ultima_fase, explicacion }` y NO trae bloques. Pintarlo con
`Turno` dejaba «Se iba a responder:» seguido de nada — visto en el navegador el
2026-08-11, en cuanto la cola tuvo su primer elemento de verdad. Un hueco se
lee como «el sistema iba a callarse», que es distinto de «el sistema falló», y
la segunda es justo la información por la que el turno está aquí.

No se rellena nada: el servidor manda ese dato entero y lo que faltaba era
elegir el componente que sabe pintarlo. `RP-17` prohíbe inventar en el cliente,
no leer lo que llegó.

Y POR ESO «APROBAR» NO SIEMPRE ESTA. Aprobar es emitir lo propuesto; sobre un
turno sin propuesta no emite nada y solo parece que hace algo. Un botón que
finge una acción es peor que su ausencia en una pantalla de revisión.



-->
<script>
  import Turno from '../../comun/turno/Turno.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Campo from '../../comun/base/Campo.svelte';
  import { emitirEvento } from '../../nucleo/api/telemetria.js';

  let {
    /** { id, recibido, urgencia, clase, tipo, mensaje, turno } */
    elemento,
    alAprobar,
    alEditar,
    alRechazar
  } = $props();

  let modo = $state('ver');          // ver · editando · rechazando
  let texto = $state('');
  let motivo = $state('');

  // Se distingue por el dato y no por `tipo`: lo que decide cómo pintar es
  // que el cuerpo sea una degradación, y eso lo dice el propio cuerpo.
  const degradacion = $derived(elemento?.turno?.situacion ? elemento.turno : null);
  const propuesta = $derived(elemento?.turno?.bloques ?? []);

  function textoEditableDelBloque(bloque) {
    if (bloque?.tipo === 'notacion' || bloque?.tipo === 'expresion-citada') {
      return `$${bloque.contenido ?? ''}$`;
    }
    return bloque?.contenido ?? '';
  }

  function abrirEdicion() {
    texto = propuesta.map(textoEditableDelBloque).join('\n\n');
    modo = 'editando';
  }

  /** Una revisión cuenta como abierta cuando la tarjeta llega al área visible. */
  function observarRevision(nodo) {
    let anotada = false;
    const anotar = () => {
      if (anotada) return;
      anotada = true;
      void emitirEvento('supervision.abierta', {
        clase: elemento?.clase,
        conversacion: elemento?.sesion,
        turno: elemento?.turno?.turno,
        metadatos: { item: elemento?.id },
      });
    };
    if (!globalThis.IntersectionObserver) {
      anotar();
      return {};
    }
    const observador = new IntersectionObserver((entradas) => {
      if (entradas.some((entrada) => entrada.isIntersecting && entrada.intersectionRatio >= 0.5)) {
        anotar();
        observador.disconnect();
      }
    }, { threshold: 0.5 });
    observador.observe(nodo);
    return { destroy: () => observador.disconnect() };
  }
</script>

<!--
  Leyenda arriba, tres columnas debajo — cambiado el 2026-08-22, a pedido
  explícito tras la versión anterior (cuerpo+franja lateral en una fila).

  `.leyenda` (urgencia + clase/tipo) ocupa todo el ancho, como cabecera de la
  tarjeta. Debajo, `.fila` reparte PREGUNTA · RESPUESTA · ACCIONES en tres
  columnas de `grid` —no un `<table>`: la columna de respuesta es contenido
  rico (una burbuja de `Turno`, con sus sellos, o el formulario de editar),
  que no cabe bien en una celda de tabla—. `align-items: start` porque cada
  columna tiene su propia altura natural y no tiene sentido estirarlas a la
  más alta —una pregunta de una línea no necesita la altura de una respuesta
  con varios bloques—. En pantallas angostas (`@media` más abajo) las tres
  columnas se apilan, como cualquier grid de una sola columna.
-->
<article class="tarjeta" use:observarRevision>
  <header class="leyenda">
    <span class="urgencia {elemento?.urgencia ?? 'normal'}">
      <span class="punto" aria-hidden="true"></span>
      {elemento?.urgencia ?? 'normal'}
    </span>
    <span class="meta">
      {elemento?.clase ?? 'sin clase'} · {elemento?.tipo ?? 'sin tipo'}
    </span>
  </header>

  <div class="fila">
    <div class="col-pregunta">
      {#if elemento?.mensaje}
        <span class="rotulo">Preguntó:</span>
        <p class="pregunta">{elemento.mensaje}</p>
      {/if}
    </div>

    <div class="col-respuesta">
      {#if modo === 'editando'}
        <Campo etiqueta="Tu aclaración" bind:valor={texto} multilinea
               ayuda="Llegará después de la respuesta original. Escribe las fórmulas entre $...$ para verlas con notación matemática." />
      {:else if modo === 'rechazando'}
        <Campo etiqueta="Respuesta corregida" bind:valor={motivo} multilinea
               ayuda="La propuesta quedará rechazada y esta corrección aparecerá junto a la respuesta original. Escribe las fórmulas entre $...$." />
      {:else if degradacion}
        <span class="rotulo">No llegó a responder:</span>
        <!-- Sin `alReintentar`: reintentar el turno es del estudiante. Desde
             aquí, la acción del docente es responder o rechazar. -->
        <Degradacion respuesta={degradacion} />
      {:else}
        <span class="rotulo">Se iba a responder:</span>
        <Turno turno={elemento?.turno} autor="tutor" />
      {/if}
    </div>

    <div class="col-acciones">
      {#if modo === 'editando'}
        <Boton deshabilitado={!texto.trim()}
               onclick={() => { alEditar?.(elemento.id, texto); modo = 'ver'; }}>
          Enviar aclaración
        </Boton>
        <Boton variante="secundario" onclick={() => (modo = 'ver')}>Cancelar</Boton>

      {:else if modo === 'rechazando'}
        <Boton deshabilitado={!motivo.trim()}
               onclick={() => { alRechazar?.(elemento.id, motivo); modo = 'ver'; }}>
          Rechazar y corregir
        </Boton>
        <Boton variante="secundario" onclick={() => (modo = 'ver')}>Cancelar</Boton>

      {:else}
        {#if propuesta.length}
          <Boton onclick={() => alAprobar?.(elemento.id)}>Aprobar</Boton>
          <Boton variante="secundario" onclick={abrirEdicion}>Editar</Boton>
        {:else}
          <!-- No hay qué editar: hay que escribirlo. El nombre lo dice, y la
               emisión sigue siendo la misma que la de editar, que es la que
               `RP-17` distingue de aprobar. -->
          <Boton onclick={abrirEdicion}>Responder yo</Boton>
        {/if}
        <Boton variante="discreto" onclick={() => (modo = 'rechazando')}>Rechazar y corregir</Boton>
      {/if}
    </div>
  </div>
</article>

<style>
  /*
    Compactada el 2026-08-22: reportado que cada tarjeta «está muy grande»
    tras revisar la cola con dieciocho pendientes reales. `padding`/`gap`
    bajan un escalón (`--espacio-lg`→`--espacio-md`, `0.7rem`→`0.55rem`), y
    `.col-respuesta :global(.burbuja)` más abajo reduce el propio relleno de
    `Turno` —pensado para una conversación a pantalla completa, no para una
    tarjeta de revisión— sin tocar `Turno.svelte`: sigue siendo el MISMO
    componente que ve el estudiante, con sus mismos sellos, solo con menos
    aire alrededor en este contexto concreto.
  */
  .tarjeta {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    padding: var(--espacio-sm) var(--espacio-md);
    background: var(--surface-panel);
    /* Canto de tarjeta: REGIÓN. */
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
    transition: var(--transition);
  }

  .tarjeta:hover { border-color: var(--trazo); }

  .leyenda {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: var(--texto-xs);
    padding-block-end: 0.5rem;
    border-block-end: 1px solid var(--trazo-suave);
  }

  /* Las tres columnas: pregunta · respuesta · acciones. `minmax` en las dos
     primeras para que el texto pueda envolver sin forzar la columna a su
     ancho de contenido; `acciones` es de ancho fijo, la «última columna»
     que se pidió. `align-items: start` porque cada columna tiene su propia
     altura y no hace falta que la más corta se estire a la de la más
     alta — ver el comentario del marcado. */
  .fila {
    display: grid;
    grid-template-columns: minmax(10rem, 1fr) minmax(14rem, 1.6fr) 8.5rem;
    align-items: start;
    gap: var(--espacio-md);
  }

  .col-pregunta,
  .col-respuesta { min-inline-size: 0; }

  .urgencia {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 0.2em 0.6em;
    border-radius: var(--radius-pill, 9999px);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    border: 1px solid transparent;
  }

  .punto {
    inline-size: 6px;
    block-size: 6px;
    border-radius: 50%;
    background: currentColor;
    flex-shrink: 0;
  }

  .alta   { color: var(--semantic-error);   background: var(--semantic-error-bg);   border-color: var(--semantic-error); }
  .normal { color: var(--ink-secondary);    background: var(--surface-paper);       border-color: var(--trazo-suave); }
  .baja   { color: var(--ink-tertiary);     background: var(--surface-paper);       border-color: var(--trazo-suave); }

  .meta { color: var(--ink-tertiary); }

  .rotulo {
    display: block;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    margin-block-end: 0.2rem;
  }

  .pregunta { margin: 0.2rem 0 0; font-size: var(--texto-sm); }

  .col-respuesta { display: flex; flex-direction: column; }

  /* Reduce el relleno que `Turno.svelte` trae para una burbuja de chat a
     pantalla completa — aquí es una tarjeta entre otras, no la
     conversación. Solo cosmético (relleno, tamaño de letra, margen
     inferior): los sellos, el texto y la estructura siguen intactos, es el
     mismo componente. */
  .col-respuesta :global(.turno) {
    max-inline-size: 100%;
    margin-block-end: 0;
  }

  .col-respuesta :global(.burbuja) {
    padding: 8px 11px;
    font-size: 12.5px;
  }

  .col-respuesta :global(.autor-turno) { margin-block-end: 2px; }

  /* La columna de acciones: ancho fijo, la «última columna» que se pidió.
     Botones apilados, con `Cancelar` siempre debajo del botón de acción
     principal (editando/rechazando) para que el orden visual coincida con
     el de tabulación.

     `align-self: center` —contra el `align-items: start` de `.fila`—:
     pedido el 2026-08-22 para que el grupo de botones (dos o tres, según
     el modo) quede centrado de arriba abajo dentro de la fila en vez de
     pegado a la línea de la leyenda. Pregunta y respuesta se quedan
     arriba (`.fila` sigue en `start` para ellas) porque son texto de
     lectura, que empieza arriba por convención; los botones no se leen,
     se pulsan, y centrados quedan a media altura sin importar si la
     respuesta de al lado es una línea o un párrafo entero. */
  .col-acciones {
    align-self: center;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  /* `Boton.svelte` usa `--texto-base` y `1.1em` de relleno horizontal —
     pensado para un botón suelto, no para una columna de 8.5rem—. «Responder
     yo» es el único rótulo de los cuatro que no cabía en una línea con eso:
     envolvía a dos renglones y quedaba visiblemente más alto que
     «Aprobar»/«Editar»/«Rechazar» al lado —reportado el 2026-08-22—. Se
     reduce aquí, solo en este contexto, sin tocar `Boton.svelte`: los otros
     tres rótulos ya cabían de sobra, así que esto no les cambia nada visible
     más que unos píxeles de relleno. */
  .col-acciones :global(.boton) {
    padding-inline: 0.7em;
    font-size: 13px;
    white-space: nowrap;
  }

  /* Tarjeta angosta (teléfono/tableta angosta): las tres columnas se
     apilan, como cualquier grid de una sola columna — sin franja lateral
     que reservar, `.col-acciones` vuelve a ser una fila de botones. */
  @media (max-width: 40rem) {
    .fila {
      grid-template-columns: 1fr;
      gap: 0.6rem;
    }

    .col-acciones {
      flex-direction: row;
      flex-wrap: wrap;
      padding-block-start: 0.4rem;
      border-block-start: 1px solid var(--trazo-suave);
    }
  }
</style>
