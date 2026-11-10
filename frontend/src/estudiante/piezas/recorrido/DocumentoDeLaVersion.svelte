
<script>
  import CargadorCubo from '../../../comun/base/CargadorCubo.svelte';
  import Boton from '../../../comun/base/Boton.svelte';
  import MarkdownSeguro from '../../../comun/base/MarkdownSeguro.svelte';
  import { textoDeVersion } from '../../../nucleo/api/consentimiento.js';

  let {
    codigo = '',
    rotulo = 'documento',
    alFallarElDocumento = () => {},
    pagina = false
  } = $props();

  let abierto = $state(false);
  let cargando = $state(false);
  let documento = $state(null);
  let error = $state('');

  async function abrir() {
    abierto = true;
    if (documento || cargando) return;
    cargando = true;
    error = '';
    try {
      documento = await textoDeVersion(codigo);
    } catch (fallo) {
      error =
        fallo?.datos?.detalle ||
        'No se pudo cargar el documento. No aceptes nada que no hayas podido leer.';
      alFallarElDocumento(codigo, error);
    } finally {
      cargando = false;
    }
  }

  $effect(() => {
    if (pagina && codigo) abrir();
  });
</script>

{#if codigo}
  <div class="documento-version" class:pagina>
    {#if !abierto && !pagina}
      <Boton variante="secundario" onclick={abrir}>Leer el {rotulo} completo</Boton>
    {:else}
      <div class="marco">
        {#if cargando}
          <CargadorCubo mensaje="Cargando el documento…" pantallaCompleta />
        {:else if error}

          <p class="estado error" role="alert">{error}</p>
        {:else if documento && pagina}
          <MarkdownSeguro texto={documento.cuerpo} />
          <p class="pie">
            <span class="etiqueta">Huella SHA-256 de este texto</span>
            <span class="monoespaciado huella">{documento.huella_contenido}</span>
          </p>
        {:else if documento}


          <pre
            class="cuerpo"
            tabindex="0"
            role="region"
            aria-label={`Texto completo del ${rotulo}`}>{documento.cuerpo}</pre>
          <p class="pie">
            <span class="etiqueta">Huella de este texto</span>
            <span class="monoespaciado huella">{documento.huella_contenido}</span>
          </p>
          <p class="nota">
            Es el SHA-256 del documento que acabas de leer. Puedes copiarlo y
            comprobarlo por tu cuenta; queda guardado con tu decisión.
          </p>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .documento-version {
    margin-top: 8px;
  }

  .marco {
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    background: var(--surface-paper);
  }

  .documento-version.pagina .marco { padding: clamp(1rem, 3vw, 2.5rem); }

  .cuerpo {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    max-height: 24rem;
    overflow-y: auto;
    margin: 0;
    font-family: inherit;
    font-size: var(--texto-sm);
    line-height: 1.55;
  }


  .estado {
    margin: 0;
    font-size: var(--texto-sm);
  }

  .error {
    color: var(--semantic-error);
  }

  .pie {
    margin: 10px 0 0;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .etiqueta {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  .huella {
    font-size: var(--texto-xs);
    overflow-wrap: anywhere;
    user-select: all;
  }

  .nota {
    margin: 8px 0 0;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }
</style>
