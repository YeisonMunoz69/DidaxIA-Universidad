
<script>
  import Turno from '../../comun/turno/Turno.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Campo from '../../comun/base/Campo.svelte';
  import { emitirEvento } from '../../nucleo/api/telemetria.js';

  let {
    elemento,
    alAprobar,
    alEditar,
    alRechazar
  } = $props();

  let modo = $state('ver');
  let texto = $state('');
  let motivo = $state('');

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

          <Boton onclick={abrirEdicion}>Responder yo</Boton>
        {/if}
        <Boton variante="discreto" onclick={() => (modo = 'rechazando')}>Rechazar y corregir</Boton>
      {/if}
    </div>
  </div>
</article>

<style>
  .tarjeta {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    padding: var(--espacio-sm) var(--espacio-md);
    background: var(--surface-panel);
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

  .col-respuesta :global(.turno) {
    max-inline-size: 100%;
    margin-block-end: 0;
  }

  .col-respuesta :global(.burbuja) {
    padding: 8px 11px;
    font-size: 12.5px;
  }

  .col-respuesta :global(.autor-turno) { margin-block-end: 2px; }

  .col-acciones {
    align-self: center;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .col-acciones :global(.boton) {
    padding-inline: 0.7em;
    font-size: 13px;
    white-space: nowrap;
  }

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
