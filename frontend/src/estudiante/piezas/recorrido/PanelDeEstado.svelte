
<script>
  import Icono from '../../../comun/base/Icono.svelte';
  import Boton from '../../../comun/base/Boton.svelte';
  import { navegar } from '../../../enrutado/navegar.js';

  let {
    acceso,
    alReintentar = null,
    children = null
  } = $props();

  const TEXTOS = {
    bloqueado_por_rechazo: {
      icono: 'cerrar',
      tono: 'bloqueo',
      titulo: 'No autorizaste el tratamiento de tus datos',
      cuerpo:
        'Sin esa autorización el tutor no puede funcionar, porque las finalidades que cubre son las necesarias para prestarlo. Tu decisión quedó registrada y no se borró nada.',
      queSePuede: [
        'Consultar y descargar la información que el sistema ya tiene sobre ti.',
        'Volver a decidir cuando exista una versión publicada del documento.'
      ]
    },
    bloqueado_por_revocacion: {
      icono: 'cerrar',
      tono: 'bloqueo',
      titulo: 'Retiraste tu autorización',
      cuerpo:
        'El tutor quedó bloqueado en el momento en que se registró la revocación, y no se inició ningún tratamiento nuevo desde entonces. Revocar no borra lo que ya existía: para eso está la solicitud de eliminación.',
      queSePuede: [
        'Consultar y descargar tu información.',
        'Solicitar la eliminación de tus datos desde «Mis datos».',
        'Volver a autorizar cuando exista una versión publicada del documento.'
      ]
    },
    eliminacion_solicitada: {
      icono: 'basura',
      tono: 'tramite',
      titulo: 'Tienes una solicitud de eliminación en curso',
      cuerpo:
        'Mientras el trámite siga abierto, el tutor no está disponible y no se registra ningún dato nuevo. Tus datos todavía no se han eliminado.',
      queSePuede: [
        'Ver el estado del trámite y sus plazos en «Mis datos».',
        'Cancelarlo desde allí, dentro del plazo que informa el sistema.'
      ]
    },
    mantenimiento: {
      icono: 'reiniciar',
      tono: 'mantenimiento',
      titulo: 'El servicio está en mantenimiento',
      cuerpo:
        'No puedo consultar tu estado ahora mismo, así que prefiero no enseñarte algo que no puedo comprobar. Esto no significa que falte ninguna autorización tuya.',
      queSePuede: [
        'Volver a intentarlo en un momento.',
        'Lo que hayas escrito en esta pantalla se conserva mientras tanto.'
      ]
    }
  };

  const texto = $derived(TEXTOS[acceso] ?? null);
</script>

{#if texto}
  <section class="panel {texto.tono}" aria-labelledby="titulo-estado">
    <div class="cabecera">
      <span class="marca-icono"><Icono nombre={texto.icono} medida={18} /></span>
      <h2 id="titulo-estado">{texto.titulo}</h2>
    </div>

    <p class="cuerpo">{texto.cuerpo}</p>

    <div class="que-se-puede">
      <p class="rotulo">Lo que puedes hacer ahora:</p>
      <ul>
        {#each texto.queSePuede as linea (linea)}
          <li><span class="vinieta" aria-hidden="true">·</span><span>{linea}</span></li>
        {/each}
      </ul>
    </div>

    {@render children?.()}

    <div class="acciones">
      {#if acceso !== 'mantenimiento'}
        <Boton variante="secundario" onclick={() => navegar('/mis-datos')}>
          <Icono nombre="datos" medida={15} />
          Ir a Mis datos
        </Boton>
      {/if}
      {#if alReintentar}
        <Boton variante={acceso === 'mantenimiento' ? 'principal' : 'discreto'} onclick={alReintentar}>
          <Icono nombre="reiniciar" medida={15} />
          Volver a comprobar
        </Boton>
      {/if}
    </div>
  </section>
{/if}

<style>
  .panel {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-sm);
    padding: 14px 16px;
    background: var(--surface-paper);
    border: 1.5px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
  }

  .panel.bloqueo { border-inline-start: 3px solid var(--semantic-error); }
  .panel.tramite { border-inline-start: 3px solid var(--accent-main); }
  .panel.mantenimiento { border-inline-start: 3px solid var(--ink-tertiary); }

  .cabecera {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .marca-icono {
    display: flex;
    align-items: center;
    color: var(--ink-secondary);
    flex-shrink: 0;
  }

  h2 {
    margin: 0;
    font-size: var(--texto-lg);
    font-weight: 700;
    color: var(--ink-primary);
    line-height: 1.25;
  }

  .cuerpo {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.5;
    color: var(--ink-secondary);
  }

  .rotulo {
    margin: 0 0 4px;
    font-size: var(--texto-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ink-tertiary);
  }

  .que-se-puede ul {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .que-se-puede li {
    display: flex;
    gap: 8px;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  .vinieta { color: var(--accent-main); font-weight: 700; }

  .acciones {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-block-start: 2px;
  }

  @media (max-width: 30rem) {
    .acciones :global(.boton) { inline-size: 100%; }
  }
</style>
