
<script>
  import { ayudaContextual } from '../base/ayudaContextual.js';
  import Icono from '../base/Icono.svelte';
  import EntrarConGoogle from '../sesion/EntrarConGoogle.svelte';
  import AvisoDeExpiracion from '../sesion/AvisoDeExpiracion.svelte';
  import CarrilHistorial from './CarrilHistorial.svelte';
  import BotonNuevaConversacion from './BotonNuevaConversacion.svelte';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import * as datosPersonales from '../../nucleo/api/datos-personales.js';

  let {
    arbol,
    inicio,
    destino,
    perfilables,
    navGlobal = [],
    ir,
    irAlPerfil = ir,
    carrilAbierto = $bindable(false),
    ajustesAbiertos = $bindable(false)
  } = $props();

  let carril = $state();

  let carrilEsCajon = $state(
    globalThis.matchMedia?.('(max-width: 48rem)').matches ?? false
  );
  let alturaVisible = $state('100dvh');
  let inicioVisible = $state('0px');
  $effect(() => {
    if (!carrilEsCajon || !carrilAbierto) return;
    const viewport = globalThis.visualViewport;
    const actualizar = () => {
      alturaVisible = viewport ? `${viewport.height}px` : '100dvh';
      inicioVisible = viewport ? `${viewport.offsetTop}px` : '0px';
    };
    actualizar();
    viewport?.addEventListener('resize', actualizar);
    viewport?.addEventListener('scroll', actualizar);
    return () => {
      viewport?.removeEventListener('resize', actualizar);
      viewport?.removeEventListener('scroll', actualizar);
    };
  });
  const compacto = $derived(!carrilEsCajon && !preferencias.carrilVisible);
  let fotoFallida = $state(false);
  let revisionFoto = $state(0);
  let nombreCuenta = $state('');

  $effect(() => {
    revisionFoto;
    fotoFallida = false;
  });

  $effect(() => {
    if (!sesion.autenticada) {
      nombreCuenta = '';
      return;
    }
    const controlador = new AbortController();
    datosPersonales.consultar({ señal: controlador.signal })
      .then((respuesta) => { nombreCuenta = String(respuesta?.nombre ?? '').trim(); })
      .catch(() => {});
    return () => controlador.abort();
  });

  $effect(() => {
    const refrescar = () => { revisionFoto += 1; };
    globalThis.addEventListener?.('didaxia:foto-actualizada', refrescar);
    return () => globalThis.removeEventListener?.('didaxia:foto-actualizada', refrescar);
  });

  $effect(() => {
    const consulta = globalThis.matchMedia?.('(max-width: 48rem)');
    const alCambiar = () => { carrilEsCajon = Boolean(consulta?.matches); };
    consulta?.addEventListener('change', alCambiar);
    return () => consulta?.removeEventListener('change', alCambiar);
  });

  function alTeclearEnCarril(evento) {
    if (evento.key === 'Escape') carrilAbierto = false;
  }

  $effect(() => {
    if (carrilAbierto) carril?.focus();
  });
</script>


<aside class="carril" class:abierto={carrilAbierto} class:plegado={!preferencias.carrilVisible}
       style:--altura-visible={alturaVisible} style:--inicio-visible={inicioVisible}
       bind:this={carril}
       tabindex="-1"
       inert={carrilEsCajon && !carrilAbierto}
       onkeydown={alTeclearEnCarril}>
  <div class="cabecera-del-cajon">
    <strong>Historial</strong>
    <button class="icono-solo" aria-label="Cerrar historial" onclick={() => (carrilAbierto = false)}>
      <Icono nombre="cerrar" />
    </button>
  </div>
  <div class="control-del-carril">
    <button use:ayudaContextual class="icono-solo alternar-carril"
            aria-label="Mostrar u ocultar el historial"
            title={preferencias.carrilVisible ? 'Contraer historial' : 'Expandir historial'}
            aria-pressed={preferencias.carrilVisible}
            onclick={() => preferencias.alternarCarril()}>
      <Icono nombre="panel-izq" />
    </button>
  </div>
  {#if compacto}
    <div class="carril-compacto" aria-label="Accesos rápidos">
      {#if arbol === 'estudiante'}
        <BotonNuevaConversacion compacto />
      {/if}
      <nav class="nav-compacta" aria-label="Secciones">
        {#each navGlobal as r (r.camino)}
          <a use:ayudaContextual href={r.camino} title={r.titulo} aria-label={r.titulo}
             aria-current={r.camino === destino ? 'page' : undefined}
             onclick={(evento) => { evento.preventDefault(); ir(r.camino); }}>
            <Icono nombre={r.icono} medida={18} />
          </a>
        {/each}
      </nav>
      <div class="base-compacta">
        {#if perfilables[0]}
          <a use:ayudaContextual class="perfil-compacto" href={perfilables[0].camino} title={nombreCuenta || perfilables[0].titulo}
             aria-label={nombreCuenta ? `${nombreCuenta}, ${perfilables[0].titulo}` : perfilables[0].titulo}
             onclick={(evento) => { evento.preventDefault(); irAlPerfil(perfilables[0].camino); }}>
            <span class="avatar" aria-hidden="true">
              {#if sesion.autenticada && !fotoFallida}
                <img src={`/api/datos-personales/foto?v=${revisionFoto}`} alt="" onerror={() => (fotoFallida = true)} />
              {:else}<Icono nombre="estudiante" medida={16} />{/if}
            </span>
          </a>
        {/if}
        <button use:ayudaContextual class="icono-solo" aria-label="Ajustes" title="Ajustes"
                onclick={() => (ajustesAbiertos = true)}><Icono nombre="ajustes" /></button>
      </div>
    </div>
  {:else}
  <div class="alto">
    {#if arbol === 'estudiante'}
      <CarrilHistorial bind:carrilAbierto />
    {/if}
  </div>


  <div class="bajo">

    <AvisoDeExpiracion />

    <div class="identidad">
      {#if sesion.sincronizada && (destino !== '/' || sesion.autenticada)}
        <EntrarConGoogle />
      {/if}

      <div class="quien">
        {#each perfilables as r (r.camino)}
          <a class="perfil" href={r.camino}
             aria-current={r.camino === destino ? 'page' : undefined}
             onclick={(e) => { e.preventDefault(); irAlPerfil(r.camino); }}>
            <span class="avatar" aria-hidden="true">
              {#if sesion.autenticada && !fotoFallida}
                <img
                  src={`/api/datos-personales/foto?v=${revisionFoto}`}
                  alt=""
                  onerror={() => (fotoFallida = true)}
                />
              {:else}
                <Icono nombre="estudiante" medida={15} />
              {/if}
            </span>

            <span class="texto">
              <span class="nombre">
                {sesion.autenticada ? (nombreCuenta || 'Tu cuenta') : 'Sin sesión iniciada'}
              </span>
              <span class="sub">{r.titulo}</span>
            </span>
          </a>
        {/each}

        <button class="icono-solo" aria-label="Ajustes"
                onclick={() => { ajustesAbiertos = true; carrilAbierto = false; }}>
          <Icono nombre="ajustes" />
        </button>
      </div>
    </div>
  </div>
  {/if}
</aside>


{#if carrilAbierto}
  <button class="velo" aria-label="Cerrar el menú"
          onclick={() => (carrilAbierto = false)}></button>
{/if}

<style>
  .cabecera-del-cajon { display: none; }
  .carril {
    inline-size: 16rem;
    width: 16rem;
    min-inline-size: 16rem;
    flex-basis: 16rem;
    box-sizing: border-box;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    padding: 16px 14px 14px;
    background: var(--surface-panel);
    border-inline-end: 1px solid var(--trazo-suave);
    transition: inline-size 220ms cubic-bezier(.22,1,.36,1), padding 220ms cubic-bezier(.22,1,.36,1);
  }

  .alto {
    flex: 1;
    min-block-size: 0;
    display: flex;
    flex-direction: column;
  }


  .carril:focus-visible { outline-offset: -2px; }

  .carril.plegado {
    inline-size: 3.75rem;
    width: 3.75rem;
    min-inline-size: 3.75rem;
    max-inline-size: 3.75rem;
    flex-basis: 3.75rem;
    padding: 10px 8px;
    gap: 0;
  }

  .control-del-carril {
    flex: 0 0 auto;
    display: flex;
    justify-content: flex-end;
  }

  .carril.plegado .control-del-carril { justify-content: center; margin-block-end: .55rem; }

  .alternar-carril:hover :global(svg) { transform: translateX(-2px); }
  .carril.plegado .alternar-carril:hover :global(svg) { transform: translateX(2px); }

  .carril-compacto {
    flex: 1;
    min-block-size: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: .55rem;
  }

  .nav-compacta {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: .4rem;
  }

  .nav-compacta a,
  .perfil-compacto {
    inline-size: 42px;
    block-size: 42px;
    display: grid;
    place-items: center;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    color: var(--ink-secondary);
    text-decoration: none;
    transition: var(--transition-fast);
  }

  .nav-compacta a:hover,
  .nav-compacta a[aria-current='page'],
  .perfil-compacto:hover {
    border-color: var(--accent-main);
    background: var(--accent-surface);
    color: var(--accent-main);
  }

  .base-compacta {
    margin-block-start: auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: .45rem;
  }

  .perfil-compacto .avatar {
    inline-size: 31px;
    block-size: 31px;
    display: grid;
    place-items: center;
    overflow: hidden;
    border: 1.5px solid var(--accent-main);
    border-radius: 50%;
    background: var(--accent-surface);
  }

  .perfil-compacto .avatar img { inline-size: 100%; block-size: 100%; object-fit: cover; }

  .bajo { flex-shrink: 0; display: flex; flex-direction: column; gap: var(--espacio-md); }

  .identidad {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-sm);
    padding-block-start: var(--espacio-md);
    border-block-start: 1px solid var(--ink-ghost);
  }

  .quien { display: flex; align-items: center; gap: 0.5rem; }

  .perfil {
    flex: 1;
    min-inline-size: 0;
    display: flex;
    align-items: center;
    gap: 0.7em;
    min-block-size: 44px;
    padding: 6px 10px;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    background: transparent;
    text-decoration: none;
    cursor: pointer;
    box-shadow: var(--shadow-soft);
    transition: all 0.2s ease-out;
  }

  .perfil .avatar {
    inline-size: 28px;
    block-size: 28px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--accent-surface);
    border: 1.5px solid var(--accent-main);
    border-radius: 50%;
    color: var(--accent-main);
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
    overflow: hidden;
  }

  .perfil .avatar img { inline-size: 100%; block-size: 100%; object-fit: cover; }

  .perfil:hover {
    background: var(--surface-panel);
    border-color: var(--accent-main);
    transform: translateY(-2px);
    box-shadow: var(--shadow-soft);
  }

  .perfil:hover .avatar { transform: scale(1.12); }

  .perfil:hover .sub { color: var(--accent-main); }

  .perfil:active { transform: translateY(0) scale(0.97); }

  .perfil[aria-current='page'] {
    background: var(--accent-surface);
    border-color: var(--accent-main);
  }

  .perfil .texto { display: flex; flex-direction: column; min-inline-size: 0; }

  .perfil .nombre {
    color: var(--ink-primary);
    font-size: 12.5px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .perfil .sub { color: var(--ink-secondary); font-size: 10.5px; }

  .icono-solo {
    position: relative;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    inline-size: 38px;
    block-size: 38px;
    padding: 0;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--ink-secondary);
    font: inherit;
    cursor: pointer;
    overflow: visible;
    box-shadow: var(--shadow-soft);
    transition: all 0.2s ease-out;
  }

  .icono-solo :global(svg) {
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .icono-solo:hover {
    background: var(--surface-panel);
    border-color: var(--accent-main);
    color: var(--accent-main);
    transform: translateY(-2px);
    box-shadow: var(--shadow-soft);
  }

  .icono-solo:active { transform: translateY(0) scale(0.95); }

  button[aria-label="Ajustes"] :global(svg) {
    transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  button[aria-label="Ajustes"]:hover :global(svg) {
    transform: rotate(90deg) scale(1.12);
  }

  @media (max-width: 48rem) {
    .cabecera-del-cajon { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
    .control-del-carril { display: none; }
    .carril {
      position: fixed;
      inset-block-start: var(--inicio-visible);
      inset-block-end: auto;
      block-size: var(--altura-visible);
      padding-block-start: max(16px, env(safe-area-inset-top));
      padding-block-end: max(14px, env(safe-area-inset-bottom));
      inset-inline-start: 0;
      z-index: 80;
      inline-size: min(17rem, 84vw);
      width: min(17rem, 84vw);
      min-inline-size: 0;
      max-inline-size: none;
      flex-basis: auto;
      transform: translateX(-102%);
      transition: transform 0.2s cubic-bezier(0.22, 1, 0.36, 1);
      box-shadow: var(--shadow-float);
    }

    .carril.abierto { transform: none; }

    .carril.plegado { display: flex; }

    .carril.plegado {
      inline-size: min(17rem, 84vw);
      width: min(17rem, 84vw);
      min-inline-size: 0;
      max-inline-size: none;
      flex-basis: auto;
      padding: 16px 14px 14px;
      gap: var(--espacio-md);
      padding-block-start: max(16px, env(safe-area-inset-top));
      padding-block-end: max(14px, env(safe-area-inset-bottom));
    }

    .velo {
      position: fixed;
      inset: 0;
      z-index: 70;
      background: var(--velo-modal);
      border: 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .carril { transition: none; }
    .icono-solo:hover, .icono-solo:active { transform: none; }
  }
</style>
