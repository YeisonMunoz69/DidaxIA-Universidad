<!--
El carril lateral · historial (si aplica) y perfil.

Sacado de `Aplicacion.svelte` el 2026-08-22 al partir el armazón en piezas:
ese archivo se había vuelto el único sitio donde tocar cualquier cosa del
marco —carril, cabecera, enrutado, tema— y crecía con cada pantalla nueva de
docente o estudiante que necesitara un ajuste ahí. Este componente es
SOLO el carril; `CabeceraGlobal.svelte` es la cabecera, y `Aplicacion.svelte`
sigue siendo quien decide QUÉ pantalla se monta y compone las piezas.

Compartido por los dos árboles, no partido en `CarrilEstudiante`/
`CarrilDocente`: lo único que cambia entre uno y otro es el panel de
`CarrilHistorial.svelte` —historial de conversaciones, un concepto que no
existe para docente ni investigador—, y ese panel ya se monta condicionado
a `arbol === 'estudiante'`. El resto (perfil y ajustes) es el mismo marco para
cualquier rol. La marca global vive en `CabeceraGlobal.svelte` para conservar
una entrada al inicio visible también cuando el carril está plegado.



-->
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
    /** `arbolDe(sesion.rol)`, ya resuelto por quien nos usa. */
    arbol,
    /** `inicioDe(sesion.rol)`, ya resuelto por quien nos usa · C2B.
        Antes se calculaba aquí con `inicio`, y eso mandaba a una
        investigadora a `/supervision`: dos árboles no bastan para tres roles.
        La única fuente es `rutas.js::inicioDe()`, y llega resuelta para que
        este componente no pueda tener una opinión propia sobre el asunto. */
    inicio,
    /** El camino ya resuelto por las guardas —no `camino` a secas—, para
        marcar qué enlace de perfil está activo. */
    destino,
    /** `rutasDeZona(arbol, 'perfil')`. Vacío en el árbol no-estudiante hoy. */
    perfilables,
    navGlobal = [],
    /** Navega y cierra cualquier capa transitoria —el cajón de este carril y
        el menú «Más» de `CabeceraGlobal.svelte`—. Vive en `Aplicacion.svelte`
        porque es la única pieza que conoce las dos capas a la vez. */
    ir,
    irAlPerfil = ir,
    /** Abierto como cajón en teléfono. Compartido con `CabeceraGlobal.svelte`
        —su botón «Abrir el menú» también lo escribe—. */
    carrilAbierto = $bindable(false),
    /** El diálogo de Ajustes. El botón de aquí abajo lo abre. */
    ajustesAbiertos = $bindable(false)
  } = $props();

  /** @type {HTMLElement | undefined} */
  let carril = $state();

  /*
   * EL CAJÓN CERRADO SE VUELVE `inert`, PERO SOLO CUANDO ES UN CAJÓN.
   *
   * Medido a 375 px el 2026-08-20: con el menú cerrado, DIEZ tabulaciones a
   * ciegas antes del primer control visible. `.carril` se traslada fuera de
   * la pantalla con `transform` —ver la hoja de estilos— pero `transform` no
   * saca nada del orden de tabulación: los nueve controles del cajón (nueva
   * conversación, los enlaces, ajustes…) seguían alcanzándose con Tab aunque
   * no se vieran.
   *
   * `inert` los saca del todo, y solo tiene que aplicarse en el mismo corte
   * que la hoja de estilos usa para convertir el carril en cajón. Desde
   * `PM-F20` ese corte es `48rem` —`--corte-tableta`—, no `60rem`: entre
   * 48 y 75rem el carril ya es la columna angosta y fija de la banda de
   * tableta —`D-31`—, y `carrilAbierto` ni siquiera se usa para mostrarla,
   * así que aplicar `inert` ahí por estar `!carrilAbierto` dejaría esa
   * columna VISIBLE pero inerte — exactamente el defecto que esto arregla,
   * cometido al revés—. `@media` no admite `var()`, el literal se repite
   * a propósito.
   */
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

  // El carril abierto en teléfono se cierra con Esc, como cualquier capa que
  // tapa lo que hay debajo. Sin esto, quien navega por teclado queda dentro.
  function alTeclearEnCarril(evento) {
    if (evento.key === 'Escape') carrilAbierto = false;
  }

  // Al abrirlo se lleva el foco dentro; si no, el lector de pantalla sigue
  // anunciando el botón que lo abrió y el carril no existe para él.
  $effect(() => {
    if (carrilAbierto) carril?.focus();
  });
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions
     El carril no es un control, pero en teléfono se convierte en una capa
     que tapa la pantalla, y una capa así tiene que cerrarse con Esc. -->
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

  <!-- `PM-F20`: «Secciones» y «Más secciones» viven en `CabeceraGlobal.svelte`.
       Este carril vuelve a ser lo único que su rótulo dice: conversaciones
       (si aplica) y perfil, no secciones del sistema. -->
  <div class="bajo">
    <!-- `EQ-020` · siete días de sesión, y se avisa antes de que terminen. El
         aviso va aquí, junto a la identidad, porque es de la sesión y no de la
         pantalla en la que se esté. No renueva el plazo: sólo lo consulta. -->
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
            <!--
              ⚠️ AQUÍ SE NOMBRABA UNA SESIÓN ANÓNIMA, Y ESA SESIÓN NO EXISTE.

              Era el rótulo de quien no estaba autenticado, de cuando
              `GET /api/sesion` abría una sesión anónima al consultarla. `EQ-020`
              retiró esa vía, así que no hay ninguna sesión que nombrar: lo que
              hay es nadie identificado. Se dice eso, en vez de dar nombre a una
              identidad que el servidor no reconoce.
            -->
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

<!-- Solo en teléfono, y solo con el carril abierto. Es un botón y no un
     `<div>` con `onclick` para que cierre también con teclado. -->
{#if carrilAbierto}
  <button class="velo" aria-label="Cerrar el menú"
          onclick={() => (carrilAbierto = false)}></button>
{/if}

<style>
  .cabecera-del-cajon { display: none; }
  /* NO a 13rem: con el relleno de este panel, el botón oficial de Google
     —`EntrarConGoogle.svelte`— no terminaba de caber. Medido en el
     navegador; ver también el corte de `CabeceraGlobal.svelte` a 75rem,
     donde la cabecera se encoge pero este ancho no cambia. */
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

  /*
    `.alto` ES QUIEN CRECE, NO `.carril` — arreglo de un bug real reportado
    el 2026-08-22: con muchas conversaciones, `.carril` scrolleaba entero
    (tenía su propio `overflow-y: auto`) y `.bajo` —Ajustes, Cerrar sesión,
    Mis datos— se iba fuera de vista al bajar por la lista, junto con
    «Nueva conversación» arriba.

    `flex: 1; min-block-size: 0` es lo que le da a `CarrilHistorial.svelte`
    un `<nav>` con una altura real de la que calcular su propio scroll —ver
    su comentario—; sin `min-block-size: 0` un hijo `flex: 1` no se encoge
    por debajo de su contenido natural, y `nav` nunca activaría su scroll
    porque `.alto` seguiría creciendo con él. `.bajo`, sin `flex`, se queda
    con su alto natural y `.carril` (una columna flex normal, sin
    `overflow`) lo deja siempre visible al final. */
  .alto {
    flex: 1;
    min-block-size: 0;
    display: flex;
    flex-direction: column;
  }


  .carril:focus-visible { outline-offset: -2px; }

  /*
    En escritorio, plegar conserva un carril compacto de accesos permanentes.
    Cada enlace sigue teniendo caja, nombre accesible y foco visible: el ancho
    reducido nunca oculta un elemento que todavía participe de la tabulación.
    En móvil sí se usa el patrón de cajón superpuesto y, al cerrarlo, sale por
    completo del árbol de interacción.

    Se decide leyendo `preferencias.carrilVisible` DIRECTAMENTE —no una prop
    heredada de `Aplicacion.svelte`—, así esta regla no necesita alcanzar una
    clase puesta en un ancestro fuera de este componente.
  */
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

  /* Compartido en trazo con los `icono-solo` de `CabeceraGlobal.svelte`,
     pero son dos componentes aparte tras el 2026-08-22: se duplica a
     propósito, ver la nota en `CarrilHistorial.svelte`. */
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

  /* Micro-rotación para el botón de Ajustes, único `icono-solo` de aquí. */
  button[aria-label="Ajustes"] :global(svg) {
    transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  button[aria-label="Ajustes"]:hover :global(svg) {
    transform: rotate(90deg) scale(1.12);
  }

  /* ── Móvil (< 48rem): cajón superpuesto, con velo ────────────────────
     El carril sale del flujo y pasa a ser una capa, que es lo que ya hacía
     `movil.html`. En una pantalla de 375 px, ni siquiera los `12rem`
     estrechos de la tableta caben junto a la conversación.

     `48rem` == `--corte-tableta`; `@media` no admite `var()`, el literal
     se repite a propósito. Y tiene que ser ESTE corte y no otro:
     `carrilEsCajon` —ver el `<script>`— usa la misma condición para saber
     cuándo el carril cerrado debe llevar `inert`. Si los dos cortes no
     coincidieran, la columna angosta de tableta —siempre visible— podría
     quedar marcada `inert` sin estarlo, o al revés. */
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

    /* En teléfono el carril es un cajón: la preferencia de plegado —que
       solo tiene sentido en escritorio/tableta, donde esconde la columna
       entera— no debe dejarlo invisible aquí también. */
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
