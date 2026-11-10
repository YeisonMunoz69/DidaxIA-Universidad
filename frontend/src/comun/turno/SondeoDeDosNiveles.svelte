
<script>
  let {
    sondeo,
    alResponder = () => {},
    ocupado = false
  } = $props();

  let resultado = $state('');
  let razon = $state('');

  let estado = $state('abierto');

  const razones = $derived(sondeo?.razones ?? []);
  const completo = $derived(resultado.trim() !== '' && razon !== '');
  const bloqueado = $derived(ocupado || estado === 'enviando');

  let enviado = $state(null);

  async function entregar(payload) {
    estado = 'enviando';
    try {
      await alResponder(payload);
      estado = 'confirmado';
    } catch {
      estado = 'error';
    }
  }

  function responder(evento) {
    evento.preventDefault();
    if (!completo || bloqueado) return;
    enviado = { nodo: sondeo.nodo, resultado: resultado.trim(), razon };
    return entregar(enviado);
  }

  function reintentar() {
    if (bloqueado || !enviado) return;
    return entregar(enviado);
  }
</script>

{#if sondeo && estado !== 'confirmado'}
  <section class="sondeo" aria-label="Pregunta corta de diagnóstico">
    <p class="presentacion">
      Una pregunta corta, para ver por dónde va la duda. Puedes contestarla o
      seguir con lo tuyo.
    </p>

    <form onsubmit={responder}>
      <label class="calculo">
        <span class="enunciado">{sondeo.enunciado}</span>
        <input
          type="text"
          bind:value={resultado}
          disabled={bloqueado}
          autocomplete="off"
          spellcheck="false"
          placeholder="Escribe solo el resultado"
        />
      </label>

      <fieldset>
        <legend>¿Por qué ese resultado?</legend>
        {#each razones as opcion (opcion.id)}
          <label class="razon">
            <input
              type="radio"
              name="razon-{sondeo.nodo}"
              value={opcion.id}
              bind:group={razon}
              disabled={bloqueado}
            />
            <span>{opcion.texto}</span>
          </label>
        {/each}
      </fieldset>

      <div class="acciones">
        <button type="submit" disabled={!completo || bloqueado}>Responder</button>
        {#if estado === 'error'}

          <button type="button" class="reintentar" onclick={reintentar}>
            Reintentar
          </button>
        {/if}
        <button type="button" class="omitir" onclick={() => (estado = 'confirmado')}>
          Sigo con lo mío
        </button>
      </div>


      <p class="pista" aria-live="polite">
        {#if estado === 'enviando'}
          Enviando tu respuesta…
        {:else if estado === 'error'}
          No se pudo enviar. Tu respuesta sigue aquí: puedes reintentarlo.
        {:else if !completo}
          Escribe el resultado y elige una razón para poder enviarlo.
        {/if}
      </p>
    </form>
  </section>
{/if}

<style>
  .sondeo {
    margin-block-start: var(--espacio-sm);
    padding: var(--espacio-md);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-trazado);
    background: var(--surface-panel);
  }

  .presentacion {
    margin: 0 0 var(--espacio-sm);
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
  }

  .calculo {
    display: block;
    margin-block-end: var(--espacio-md);
  }

  .enunciado {
    display: block;
    margin-block-end: 0.35rem;
    font-weight: 600;
  }

  .calculo input {
    inline-size: 100%;
    min-block-size: 44px;
    padding: 0.4em 0.7em;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-trazado);
    background: var(--surface-paper);
    font: inherit;
  }

  fieldset {
    margin: 0 0 var(--espacio-md);
    padding: 0;
    border: 0;
  }

  legend {
    padding: 0;
    margin-block-end: 0.35rem;
    font-weight: 600;
    font-size: var(--texto-sm);
  }

  .razon {
    display: flex;
    gap: 0.5rem;
    align-items: flex-start;
    padding: 0.35rem 0;
    font-size: var(--texto-sm);
    cursor: pointer;
  }

  .acciones {
    display: flex;
    gap: var(--espacio-sm);
    flex-wrap: wrap;
  }

  button {
    min-block-size: 44px;
    padding: 0.4em 0.9em;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-trazado);
    background: var(--surface-paper);
    font-size: var(--texto-sm);
    transition: var(--transition-fast);
  }

  button:hover:not([disabled]) {
    border-color: var(--accent-main);
    color: var(--accent-main);
  }

  button[disabled] {
    color: var(--ink-tertiary);
    cursor: not-allowed;
  }

  .pista {
    margin: var(--espacio-sm) 0 0;
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
    min-block-size: 1.5em;
  }
</style>
