<!--
Los estados del recorrido que no son un formulario · tabla de `EQ-016`.

Bloqueo por rechazo, bloqueo por revocación, eliminación solicitada y
mantenimiento. Los cuatro tienen la misma forma —qué pasó, qué significa, qué
se puede hacer— y por eso comparten componente en vez de repetir cuatro
tarjetas casi iguales.

⚠️ LAS TRES COSAS QUE ESTA PANTALLA NO PUEDE HACER
----------------------------------------------------
1. **No representa el mantenimiento como falta de consentimiento.** `EQ-024` lo
   prohíbe: un 503 significa «no puedo comprobarlo», no «no has autorizado». Un
   estado que se enseña como pendiente le pediría a alguien volver a decidir
   algo que quizá ya decidió.
2. **No inventa plazos.** El límite del representante y las fechas del trámite
   de supresión vienen del servidor y se muestran tal cual llegan; el navegador
   no los calcula ni los completa cuando faltan.
3. **No promete lo que no hay.** Volver a aceptar sólo se ofrece si existe una
   versión requerida publicada; hoy no la hay en ninguna base de este árbol.



-->
<script>
  import Icono from '../../../comun/base/Icono.svelte';
  import Boton from '../../../comun/base/Boton.svelte';
  import { navegar } from '../../../enrutado/navegar.js';

  let {
    /** El `acceso` calculado por el servidor. Nunca uno deducido aquí. */
    acceso,
    /** Vuelve a preguntar el estado. Se ofrece cuando reintentar tiene sentido. */
    alReintentar = null,
    /** Contenido extra que la pantalla quiera colgar debajo (la reaceptación). */
    children = null
  } = $props();

  /**
   * Qué se dice en cada estado.
   *
   * Un objeto y no una cadena de `{#if}`: los cuatro textos se leen juntos, que
   * es la única forma de notar si uno promete algo que otro niega.
   */
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

  /* El tono es un borde de acento, no un fondo saturado: el lenguaje del
     proyecto no usa bloques de color plano para decir «atención». */
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

  /* A 360 px las acciones se apilan en vez de desbordar la tarjeta.

     30rem y no un corte propio: `D-31` decidió que las bandas tienen una sola
     fuente «o en dos meses habrá siete bandas distintas», y este árbol ya usa
     30rem para el mismo caso —una tarjeta angosta— en otras cinco hojas.
     Añadir un 26rem habría sido la sexta banda. */
  @media (max-width: 30rem) {
    .acciones :global(.boton) { inline-size: 100%; }
  }
</style>
