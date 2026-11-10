
<script>
  import Boton from '../../comun/base/Boton.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';

  let {
    codigo = '',
    alRegenerar = null
  } = $props();

  let confirmando = $state(false);
  let copiado = $state(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(codigo);
      copiado = true;
      setTimeout(() => (copiado = false), 2000);
    } catch {
    }
  }
</script>

<div class="codigo">
  <span class="rotulo" id="rotulo-codigo">
    <Icono nombre="clase" medida={12} />
    <span>Código de la clase</span>
  </span>
  <output class="valor" aria-labelledby="rotulo-codigo">{codigo || '—'}</output>

  <div class="acciones">

    <span class="boton-copiar" class:copiado>
      <Boton variante="secundario" onclick={copiar} deshabilitado={!codigo}>
        <Icono nombre={copiado ? 'check' : 'copiar'} medida={13} />
        <span>{copiado ? 'Copiado' : 'Copiar'}</span>
      </Boton>
    </span>
    <Boton variante="discreto" onclick={() => (confirmando = true)}
           deshabilitado={!alRegenerar}>
      Regenerar
    </Boton>
  </div>

  <Dialogo bind:abierto={confirmando} titulo="¿Regenerar el código de la clase?" tipo="confirmar">
      <p>
        <strong>El código actual dejará de servir.</strong>
        Quien ya está en la clase <strong>sigue dentro</strong>: se invalida el
        código, no la matrícula. Solo tendrás que repartir el nuevo.
      </p>
      <div class="acciones">
        <Boton variante="secundario" onclick={() => (confirmando = false)}>
          Dejarlo como está
        </Boton>
        <Boton onclick={() => { alRegenerar?.(); confirmando = false; }}>
          Regenerar el código
        </Boton>
      </div>
  </Dialogo>
</div>

<style>
  .codigo {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.7rem;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
  }

  .rotulo {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: var(--texto-xs);
    font-weight: 600;
    color: var(--ink-tertiary);
  }

  .valor {
    font-family: var(--fuente-mono);
    font-size: var(--texto-sm);
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--accent-main);
  }

  .acciones { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-inline-start: auto; }

  .boton-copiar { display: contents; }

  .boton-copiar.copiado :global(.boton) {
    background: var(--semantic-success-bg);
    border-color: var(--semantic-success);
    color: var(--semantic-success);
  }

</style>
