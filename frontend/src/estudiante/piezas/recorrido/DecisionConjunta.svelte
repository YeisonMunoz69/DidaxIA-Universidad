
<script>
  import CargadorCubo from '../../../comun/base/CargadorCubo.svelte';
  import Boton from '../../../comun/base/Boton.svelte';
  import Icono from '../../../comun/base/Icono.svelte';
  import Dialogo from '../../../comun/base/Dialogo.svelte';
  import { hayVersion, textoDeVersion } from '../../../nucleo/api/consentimiento.js';

  let {
    esMenor = false,
    versionTitular = null,
    versionAsentimiento = null,
    alDecidir,
    errorDelServidor = '',
    sinVersion = false,
    alcancesFaltantes = [],
    puedeAceptar = true,
    puedeRechazar = true,
    motivoDeLaPolitica = ''
  } = $props();

  const requeridas = $derived(
    esMenor
      ? [
          {
            alcance: 'titular',
            rotulo: 'Documento que autorizas',
            nombre: 'la autorización del tratamiento',
            version: versionTitular
          },
          {
            alcance: 'asentimiento',
            rotulo: 'Tu propio acuerdo',
            nombre: 'tu propio acuerdo como menor de edad',
            version: versionAsentimiento
          }
        ]
      : [
          {
            alcance: 'titular',
            rotulo: 'Documento que autorizas',
            nombre: 'la autorización del tratamiento',
            version: versionTitular
          }
        ]
  );

  const faltantes = $derived(requeridas.filter((r) => !hayVersion(r.version)));
  const publicadas = $derived(faltantes.length === 0);

  let documentosRotos = $state({});
  let documentosComprobados = $state(false);
  const hayDocumentoRoto = $derived(Object.keys(documentosRotos).length > 0);

  $effect(() => {
    const documentos = publicadas
      ? requeridas.map((r) => ({ codigo: r.version.codigo, huella: r.version.huella_contenido }))
      : [];
    let vigente = true;
    documentosRotos = {};
    documentosComprobados = false;
    if (!documentos.length) return;

    Promise.allSettled(documentos.map(async ({ codigo, huella }) => {
      const recibido = await textoDeVersion(codigo);
      if (!recibido?.cuerpo || recibido.huella_contenido !== huella) {
        throw new Error('el documento no corresponde a la huella publicada');
      }
      return codigo;
    })).then((resultados) => {
      if (!vigente) return;
      const rotos = {};
      resultados.forEach((resultado, i) => {
        if (resultado.status === 'rejected') {
          rotos[documentos[i].codigo] = resultado.reason?.message || 'no se pudo cargar';
        }
      });
      documentosRotos = rotos;
      documentosComprobados = true;
    });

    return () => { vigente = false; };
  });

  const aceptarDisponible = $derived(
    publicadas && documentosComprobados && !hayDocumentoRoto && puedeAceptar && !enviando
  );
  const rechazarDisponible = $derived(
    publicadas && documentosComprobados && !hayDocumentoRoto && puedeRechazar && !enviando
  );

  let enviando = $state(false);
  let confirmando = $state('');

  function pedir(decision) {
    const disponible = decision === 'otorgado' ? aceptarDisponible : rechazarDisponible;
    if (!disponible) return;
    confirmando = decision;
  }

  async function confirmar() {
    if (enviando) return;
    const decision = confirmando;
    enviando = true;
    try {
      await alDecidir(decision);
      confirmando = '';
    } catch {
      confirmando = '';
    } finally {
      enviando = false;
    }
  }

  const NOMBRE_DE_ALCANCE = {
    titular: 'la autorización del tratamiento',
    asentimiento: 'tu propio acuerdo como menor de edad',
    representante: 'la autorización de tu representante'
  };

  const faltantesDelServidor = $derived(
    alcancesFaltantes.map((a) => NOMBRE_DE_ALCANCE[a] ?? a).join(' y ')
  );
</script>

<section class="decision" aria-labelledby="titulo-decision">
  <h2 id="titulo-decision">Lo que vas a aceptar</h2>
  <p class="intro">
    Para usar el tutor debes decidir sobre el tratamiento de tus datos y la
    participación descrita en el documento vigente. No hay nada marcado de antemano.
  </p>

  {#if publicadas}
    <div class="documento">
      {#each requeridas as requerida (requerida.alcance)}
        <a
          class="leer-documento"
          href={`/consentimiento?documento=${encodeURIComponent(requerida.version.codigo)}`}
          target="_blank"
          rel="noopener">
          Leer {requerida.nombre} completo en otra pestaña
        </a>
        <details class="datos-version">
          <summary>Ver código y huella de la versión</summary>
          <p><span class="etiqueta">Versión</span> <span class="monoespaciado">{requerida.version.codigo}</span></p>
          <p><span class="etiqueta">SHA-256</span> <span class="monoespaciado huella">{requerida.version.huella_contenido}</span></p>
        </details>
      {/each}
      {#if !documentosComprobados}
        <CargadorCubo mensaje="Comprobando el documento publicado…" compacto />
      {/if}
      {#if hayDocumentoRoto}

        <p class="documento-roto" role="alert">
          No se pudo mostrar el documento completo, o no coincide con su huella.
          <strong>No puedes aceptar ni rechazar</strong> algo que no has podido
          leer. Vuelve a cargar la página; si sigue igual, avisa al equipo.
        </p>
      {/if}
    </div>
  {:else}

    <div class="sin-version" role="note">
      <div class="sin-version-titulo">
        <Icono nombre="candado" medida={14} />
        <strong>Todavía no puedes decidir</strong>
      </div>
      <p>
        Falta que se publique el texto de
        {#each faltantes as falta, i (falta.alcance)}{i > 0 ? ' y de ' : ''}<strong>{falta.nombre}</strong>{/each}.
        Sin ese texto no se puede aceptar ni rechazar nada, porque no existe
        todavía aquello sobre lo que decidirías.
      </p>
      <p>
        No es un fallo del sistema ni algo que puedas resolver tú. Cuando esté
        publicado, aquí aparecerá su código, su huella y esta misma decisión.
      </p>
    </div>
  {/if}

  {#if sinVersion}
    <p class="error-servidor" role="alert">
      No se registró tu decisión porque falta publicar
      {faltantesDelServidor || 'alguno de los documentos necesarios'}.
      <strong>No se guardó nada.</strong>
    </p>
  {:else if motivoDeLaPolitica}
    <p class="error-servidor" role="alert">
      {motivoDeLaPolitica} <strong>No se guardó nada.</strong>
    </p>
  {:else if errorDelServidor}
    <p class="error-servidor" role="alert">{errorDelServidor}</p>
  {/if}

  <div class="acciones">
    <Boton onclick={() => pedir('otorgado')} deshabilitado={!aceptarDisponible}>
      <Icono nombre="check" medida={15} />
      Acepto y continuar
    </Boton>
    <Boton
      variante="secundario"
      onclick={() => pedir('rechazado')}
      deshabilitado={!rechazarDisponible}
    >
      No acepto
    </Boton>
  </div>

  {#if !publicadas}
    <p class="motivo-desactivado">
      Las dos opciones están desactivadas mientras falte un documento por publicar.
    </p>
  {:else if !puedeAceptar && !puedeRechazar}
    <p class="motivo-desactivado">
      Tu decisión ya está registrada sobre los documentos que rigen ahora. Para
      retirarla, usa «Mis datos»: retirar una autorización es un acto distinto
      de decidir, y tiene su propio trámite.
    </p>
  {:else if !puedeRechazar}
    <p class="motivo-desactivado">
      «No acepto» no está disponible porque no hay ninguna autorización nueva
      pendiente. Lo que ya autorizaste se retira desde «Mis datos».
    </p>
  {/if}
</section>

<Dialogo
  abierto={Boolean(confirmando)}
  titulo={confirmando === 'otorgado' ? '¿Confirmas que aceptas?' : '¿Confirmas que no aceptas?'}
>
  {#if confirmando === 'otorgado'}
    <p>
      Quedará registrado que aceptaste las cuatro partes: privacidad,
      condiciones, participación en la investigación y la medición que
      personaliza el tutor.
      {#if esMenor}
        Como eres menor de 18 años se registran <strong>dos constancias</strong>:
        la autorización del tratamiento y tu propio acuerdo. Aun así seguirá
        faltando la autorización firmada de tu representante.
      {/if}
      Podrás retirarlo cuando quieras desde «Mis datos».
    </p>
  {:else}
    <p>
      Sin esta autorización el tutor no puede funcionar y quedará bloqueado.
      Conservarás únicamente las páginas públicas y podrás volver a decidir más
      adelante.
      {#if esMenor}
        Se registrará tu negativa en las dos dimensiones que te aplican.
      {/if}
      Tu decisión se registra y no se borra nada de lo que ya exista.
    </p>
  {/if}
  {#if publicadas}
    <p class="version-en-dialogo">
      Se registrará sobre
      {#each requeridas as requerida, i (requerida.alcance)}{i > 0 ? ' y ' : ' '}<strong>{requerida.version.codigo}</strong>{/each},
      que {requeridas.length === 1 ? 'es la versión que rige' : 'son las versiones que rigen'}
      ahora. Las elige el servidor, no esta pantalla.
    </p>
  {/if}
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (confirmando = '')} deshabilitado={enviando}>
      Volver
    </Boton>
    <Boton onclick={confirmar} deshabilitado={enviando}>
      {enviando ? 'Registrando…' : 'Sí, confirmar'}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  .decision { display: flex; flex-direction: column; gap: 10px; }

  h2 {
    margin: 0;
    font-size: var(--texto-lg);
    font-weight: 700;
    color: var(--ink-primary);
    line-height: 1.25;
  }

  .intro {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.5;
    color: var(--ink-secondary);
  }

  .documento {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px 12px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
  }

  .leer-documento {
    align-self: flex-start;
    color: var(--accent-main);
    font-size: var(--texto-sm);
    font-weight: 650;
  }

  .datos-version {
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
  }

  .datos-version summary { cursor: pointer; }
  .datos-version p { margin: 6px 0 0; }

  .etiqueta {
    font-size: var(--texto-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-tertiary);
  }

  .monoespaciado {
    font-family: var(--fuente-mono, ui-monospace, monospace);
    font-size: var(--texto-sm);
    color: var(--ink-primary);
  }

  .huella { font-size: var(--texto-xs); overflow-wrap: anywhere; user-select: all; }

  .documento-roto {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--semantic-error);
  }

  .sin-version {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-inline-start: 3px solid var(--ink-tertiary);
    border-radius: var(--radius-sm);
  }

  .sin-version-titulo {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: var(--texto-sm);
    color: var(--ink-primary);
  }

  .sin-version p {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  .error-servidor {
    margin: 0;
    padding: 8px 10px;
    font-size: var(--texto-sm);
    line-height: 1.4;
    color: var(--semantic-error);
    background: var(--surface-paper);
    border: 1px solid var(--semantic-error);
    border-radius: var(--radius-xs);
  }

  .error-servidor::before { content: '⚠ '; }

  .acciones { display: flex; flex-wrap: wrap; gap: 8px; }

  .motivo-desactivado {
    margin: 0;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  .version-en-dialogo { color: var(--ink-secondary); font-size: var(--texto-sm); }

  @media (max-width: 30rem) {
    .acciones { flex-direction: column; }
    .acciones :global(.boton) { inline-size: 100%; }
  }
</style>
