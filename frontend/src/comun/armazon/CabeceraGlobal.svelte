<!--
La cabecera · marca global, abrir/plegar columnas, secciones y tema.

Sacado de `Aplicacion.svelte` el 2026-08-22 al partir el armazón en piezas
—ver el mismo comentario en `Carril.svelte`—. Un solo componente para los
dos árboles, y no partido por rol: a diferencia del carril, esta cabecera
no tiene NINGUNA rama condicionada al rol en su propio marcado. Todo lo que
enseña sale de `navGlobal`, que ya llega filtrado por rol desde
`rutasDeZona()` en `Aplicacion.svelte` — partirla aquí inventaría una
frontera de rol que hoy vive solo en los datos, no en este componente.



-->
<script>
  import Icono from '../base/Icono.svelte';
  import EntrarConGoogle from '../sesion/EntrarConGoogle.svelte';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import NotificacionesRecursos from '../recursos/NotificacionesRecursos.svelte';
  import SelectorDeEspacio from './SelectorDeEspacio.svelte';
  import InterruptorDeTema from '../preferencias/InterruptorDeTema.svelte';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import { guardarTemaDeCuenta } from '../../nucleo/preferencias/cuenta.js';
  import { toast } from '../estado/toasts.svelte.js';
  import { ejecutarTransicionCircularDeTema } from '../../nucleo/preferencias/transicionDeTema.js';

  let {
    /** `arbolDe(sesion.rol)`, ya resuelto por quien nos usa. */
    arbol,
    /** Rol autenticado, sólo para rotular el contexto profesional. */
    rol = 'estudiante',
    /** `inicioDe(sesion.rol)`, ya resuelto por quien nos usa · C2B.
        Antes se calculaba aquí con `inicio`, y eso mandaba a una
        investigadora a `/supervision`: dos árboles no bastan para tres roles.
        La única fuente es `rutas.js::inicioDe()`, y llega resuelta para que
        este componente no pueda tener una opinión propia sobre el asunto. */
    inicio,
    /** El camino ya resuelto por las guardas. */
    destino,
    /** `rutaDe(destino)` — para el título de `.donde` y para saber si hay
        que ofrecer el botón de plegar el panel de contexto. */
    ruta,
    /** Si el carril está montado —exclusivo de estudiante desde el
        2026-08-22, ver `Aplicacion.svelte`—. Gatea SOLO los botones de
        abrir/plegar el carril: sin carril, no hay nada que abrir. */
    conCarril,
    /** Si toca pintar la navegación —«no estamos en la pantalla retenida»,
        la misma condición para los dos árboles—. Antes se confundía con
        `conCarril`, que ya no vale para eso: ver el comentario de
        `Aplicacion.svelte` junto a esta prop. */
    puedeNavegar,
    /** Docente/investigador no tiene carril donde poner el logo, «Cerrar
        sesión» ni Ajustes — este booleano plano decide si esos tres
        controles se pintan aquí. Sigue sin haber ninguna rama que compare
        `arbol` con un rol dentro de este componente: la decisión ya viene
        tomada desde `Aplicacion.svelte`. */
    identidadEnCabecera,
    /** Si el `<h1>` de la pantalla actual dejó de verse por scroll —lo
        sigue `Aplicacion.svelte` con `IntersectionObserver`, porque el
        contenedor que hace scroll cambia de una ruta a otra—. `.donde` se
        pinta solo entonces: mientras el `<h1>` está a la vista, repetir su
        texto aquí arriba no orienta, solo lo dice dos veces. */
    mostrarTituloCabecera,
    /** Los enlaces a mostrar, ya resueltos y filtrados por rol —ver la
        cabecera de este archivo—. */
    navGlobal,
    /** En profesionales contiene exclusivamente `/mi-perfil`: va separado de
        las secciones y ocupa el lugar del antiguo cierre de sesión. */
    perfilables = [],
    /** Si el tema vigente es el oscuro. Lo decide `Aplicacion.svelte`
        —depende de `prefers-color-scheme`, que es un efecto de nivel de
        aplicación, no de esta cabecera—. */
    temaOscuro,
    /** Navega y cierra cualquier capa transitoria —el cajón de
        `Carril.svelte` y el menú «Más» de aquí abajo—. */
    ir,
    /** Compartido con `Carril.svelte`: su botón «Abrir el menú» lo enciende. */
    carrilAbierto = $bindable(false),
    /** El menú «Más» de teléfono, más abajo. */
    masAbierto = $bindable(false),
    /** El diálogo de Ajustes. Compartido con `Carril.svelte` en el árbol de
        estudiante; aquí es la única vía cuando `identidadEnCabecera`. */
    ajustesAbiertos = $bindable(false),
    /** `EQ-031` · el espacio activo, o `''` para quien no elige. Llega
        resuelto: esta cabecera sigue sin tener ninguna rama que compare
        `arbol` con un rol, igual que antes de la Fase 7. */
    espacioActivo = '',
    /** Si toca ofrecer el selector. Falso para un estudiante, que no tiene
        entre qué elegir. */
    puedeElegirEspacio = false,
    /** Cambia de espacio. Lo resuelve `Aplicacion.svelte`, que es quien sabe a
        dónde navegar después. */
    alElegirEspacio = () => {}
  } = $props();

  function alTeclearEnMas(evento) {
    if (evento.key === 'Escape') masAbierto = false;
  }
  let confirmandoSalida = $state(false);

  const rolVisible = $derived(
    rol === 'docente' ? 'Profesor' : rol === 'investigador' ? 'Investigador' : ''
  );
</script>

<svelte:window onkeydown={(evento) => {
  if (evento.key === 'Escape' && identidadEnCabecera && carrilAbierto) carrilAbierto = false;
}} />

<header class="cabecera" class:con-recursos={puedeNavegar && ['estudiante','docente'].includes(rol)} class:profesional={identidadEnCabecera || puedeElegirEspacio} class:con-carril={conCarril}>
  {#if conCarril || identidadEnCabecera}
    <button class="icono-solo abrir" aria-label="Abrir el menú"
            data-tooltip="Abrir el menú"
            aria-expanded={carrilAbierto}
            onclick={() => { masAbierto = false; carrilAbierto = !carrilAbierto; }}>
      <Icono nombre="menu" />
    </button>
  {/if}
  <!-- Una sola marca global para escritorio, tableta y teléfono. -->
  <div class="identidad-producto" class:con-selector={puedeElegirEspacio && rolVisible}>
    <a class="marca-cabecera" href={inicio} aria-label="Ir al inicio de DidaxIa"
       onclick={(e) => { e.preventDefault(); ir(inicio); }}>
      <Icono nombre="didaxia" medida={27} />
      <span>DidaxIa</span>
    </a>
    {#if rolVisible}
      <span class="distintivo-rol"><i aria-hidden="true">→</i>{rolVisible}</span>
    {/if}
    {#if puedeElegirEspacio && rolVisible}
      <SelectorDeEspacio activo={espacioActivo} rotuloProfesional={rolVisible}
                         alElegir={alElegirEspacio} />
    {/if}
  </div>

  <!--
    `PM-F20`: «Secciones» y «Más secciones», que antes vivían en el carril,
    están aquí — el mismo enlace, dibujado dos veces con `{@render}` y
    mostrado UNA sola vez según el ancho, nunca las dos.

    EN TABLETA Y ESCRITORIO VA EN LÍNEA, CON ICONO Y TEXTO — hay sitio
    y un enlace mudo no se explica solo. EN TELÉFONO SE AGRUPA TRAS
    «Más» — un `<details>` de verdad, no una imitación con `aria-*` a
    mano: `DD-05` pide HTML nativo primero, y un menú desplegable es
    justo el caso que `<details>` ya resuelve —teclado, anuncio de
    «contraído/expandido»— sin una sola línea de JavaScript.

    ⚠️ NO SE CIERRA SOLO AL TOCAR FUERA NI CON UN CLIC AJENO. Es el
    precio de no reimplementarlo a mano: `<details>` no lo hace de
    serie y añadir esa vigilancia es escribir la trampa de foco que
    `Dialogo.svelte` ya delega en `<dialog>` para OTRO caso. Sí se
    cierra con Esc —`alTeclearEnMas`— y al elegir un enlace —`ir()`—,
    que son los dos caminos por los que de verdad se sale de él.

    Los dos por debajo de `puedeNavegar`: retenido en el consentimiento —lo
    único que lo apaga hoy, y solo existe para estudiante— no hay a dónde
    navegar todavía.

    ✅ **2026-08-22 · más `mostrarTituloCabecera`.** Antes `.donde` decía lo
    mismo que el `<h1>` de la pantalla, los dos a la vez desde el primer
    instante —redundante, y en los dos árboles: `/conceptos`,
    `/mis-datos`… ya lo hacían antes de esta tanda—. Ahora solo aparece
    cuando el `<h1>` ya se perdió de vista por scroll, que es cuando de
    verdad hace falta la orientación.
  -->
  {#if ruta?.titulo && destino !== inicio && mostrarTituloCabecera}
    <p class="donde">{ruta.titulo}</p>
  {/if}

  {#if puedeNavegar && ['estudiante','docente'].includes(rol)}
    <div class="recursos-centro"><NotificacionesRecursos {ir} {rol} /></div>
  {/if}
  <div class="cabecera-derecha">
    {#if puedeNavegar && navGlobal.length || sesion.autenticada}
      {#snippet enlaceNav(r)}
        <a href={r.camino}
           aria-current={r.camino === destino ? 'page' : undefined}
           data-tooltip={r.titulo}
           onclick={(e) => { e.preventDefault(); ir(r.camino); }}>
          <Icono nombre={r.icono} medida={22} />
          <span class="rotulo">{r.titulo}</span>
        </a>
      {/snippet}

      {#if puedeNavegar}<nav class="secciones-cabecera" aria-label="Secciones">
        <ul>
          {#each navGlobal as r (r.camino)}
            <li>{@render enlaceNav(r)}</li>
          {/each}
        </ul>
      </nav>{/if}

      <!-- svelte-ignore a11y_no_noninteractive_element_interactions
           `<details>` YA es interactivo —lo abre y cierra Espacio o Intro
           sobre su `<summary>` de serie—, pero la lista del linter no lo
           reconoce como tal. El mismo caso que el `<aside>` del carril en
           `Carril.svelte`: cerrar con Esc es lo único que `<details>` no
           trae de fábrica. -->
      <details class="mas" bind:open={masAbierto} onkeydown={alTeclearEnMas}>
        <summary class="icono-solo" aria-label="Más secciones"
                 data-tooltip="Más" onclick={() => { carrilAbierto = false; }}>
          <Icono nombre="mas" />
        </summary>
        <nav aria-label="Más secciones">
          <ul>
            {#if puedeNavegar && !identidadEnCabecera}
              {#each navGlobal as r (r.camino)}
                <li>{@render enlaceNav(r)}</li>
              {/each}
            {/if}
            {#if puedeNavegar && identidadEnCabecera}
              {#if perfilables[0]}
                <li class="solo-movil"><a href={perfilables[0].camino}
                    onclick={(evento) => { evento.preventDefault(); ir(perfilables[0].camino); }}>
                  <Icono nombre={perfilables[0].icono} medida={20} /><span>Mi perfil</span>
                </a></li>
              {/if}
            {/if}
            <li class="solo-movil"><button type="button" onclick={() => { masAbierto = false; ajustesAbiertos = true; }}>
              <Icono nombre="ajustes" medida={20} /><span>Ajustes de cuenta</span>
            </button></li>
            {#if sesion.autenticada}
              <li class="salida"><button class="cerrar-sesion" type="button"
                onclick={() => { masAbierto = false; confirmandoSalida = true; }}>
                <Icono nombre="cerrar-sesion" medida={20} /><span>Cerrar sesión</span>
              </button></li>
            {/if}
          </ul>
        </nav>
      </details>
    {/if}

    <div class="acciones-cabecera">
      <InterruptorDeTema oscuro={temaOscuro} alCambiar={(nuevoTema, evento) => {
        ejecutarTransicionCircularDeTema(evento, nuevoTema, () => {
          void guardarTemaDeCuenta(nuevoTema).catch(() => toast.alerta('El tema cambió en este dispositivo; no se pudo guardar en tu cuenta.'));
        });
      }} />

      {#if identidadEnCabecera}
        <!-- Acceso directo al perfil; Más conserva el cierre de sesión. -->
        <button class="icono-solo" aria-label="Ajustes" data-tooltip="Ajustes"
                onclick={() => (ajustesAbiertos = true)}>
          <Icono nombre="ajustes" />
        </button>
        {#if perfilables[0]}
          <a class="icono-solo cuenta-cabecera" href={perfilables[0].camino}
             aria-label="Mi perfil" data-tooltip="Mi perfil"
             aria-current={perfilables[0].camino === destino ? 'page' : undefined}
             onclick={(evento) => { evento.preventDefault(); ir(perfilables[0].camino); }}>
            <Icono nombre={perfilables[0].icono} medida={25} />
          </a>
        {/if}
      {/if}

      <!-- Solo donde hay panel que plegar, y solo en estudiante: es
           `PanelDeContexto.svelte` de `Conversacion.svelte`, un concepto
           que no existe fuera de ese árbol. Antes esto se gateaba solo con
           `destino === inicio`, y como `INICIO['no-estudiante']` es
           `/supervision`, un docente en la cola de supervisión veía este
           botón sin que gobernara nada — confirmado en el navegador el
           2026-08-22, en la misma revisión que quitó el carril de ese
           árbol: un botón más sin efecto es justo la sobrecarga que se
           quería evitar. -->
      {#if arbol === 'estudiante' && destino === inicio}
        <button class="icono-solo plegar"
                aria-label="Mostrar u ocultar el panel de contexto"
                data-tooltip="Herramientas"
                aria-pressed={preferencias.panelVisible}
                onclick={() => preferencias.alternarPanel()}>
          <Icono nombre="panel-der" />
        </button>
      {/if}
    </div>
  </div>
  {#if identidadEnCabecera && carrilAbierto}
    <nav class="menu-profesional" aria-label="Menú principal">
      <ul>
        {#each navGlobal as r (r.camino)}
          <li><a href={r.camino} aria-current={r.camino === destino ? 'page' : undefined}
            onclick={(evento) => { evento.preventDefault(); carrilAbierto = false; ir(r.camino); }}>
            <Icono nombre={r.icono} medida={20} />{r.titulo}
          </a></li>
        {/each}
      </ul>
    </nav>
  {/if}
</header>
<EntrarConGoogle mostrarControl={false} bind:confirmandoSalida />

<style>
  .cabecera {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: var(--espacio-sm);
    padding: 8px 18px;
    background: var(--surface-blur);
    backdrop-filter: blur(20px) saturate(1.4);
    -webkit-backdrop-filter: blur(20px) saturate(1.4);
    border-block-end: 1px solid var(--ink-ghost);
    /* Encima del acceso flotante al contexto (18), debajo de su hoja (60). */
    z-index: 30;
    position: relative;
    transition: var(--transition);
  }

  /* El «ir a inicio» de docente/investigador, versión de cabecera del
     `.marca` de `Carril.svelte` —mismo trazo, mucho más compacto: aquí
     comparte fila con el resto, no una columna entera para sí solo. */
  .marca-cabecera {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-family: var(--fuente-manuscrita);
    font-size: 23px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--ink-primary);
    text-decoration: none;
    transition: opacity var(--transition-fast);
  }

  .identidad-producto {
    order: 2;
    display: inline-flex;
    align-items: center;
    gap: .65rem;
    flex-shrink: 0;
  }

  .distintivo-rol {
    display: inline-flex;
    align-items: center;
    gap: .38rem;
    color: var(--ink-secondary);
    font-family: var(--fuente-manuscrita);
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -.015em;
    line-height: 1;
    white-space: nowrap;
  }

  .distintivo-rol i { color: var(--accent-main); font-style: normal; font-size: .8em; }

  /* El control del carril marca su borde. En escritorio la marca pertenece a
     la zona de trabajo y por eso va DESPUÉS de ese control, no pegada al borde
     exterior izquierdo como si aún viviera dentro del sidebar. */
  .donde { order: 3; }
  .cabecera-derecha { order: 4; }

  .recursos-centro { position:absolute; left:50%; transform:translateX(-50%); }
  .cabecera.profesional.con-recursos .recursos-centro { position:static; transform:none; margin-left:auto; order:3; }
  .cabecera.con-recursos .donde { display:none; }
  .cabecera.con-recursos .cabecera-derecha { margin-left:auto; }
  @media(max-width:480px) {
    .cabecera.con-recursos { padding-inline:8px; gap:4px; }
    .cabecera.con-recursos .marca-cabecera span { display:none; }
    .cabecera.con-recursos .marca-cabecera { gap:0; }
    .cabecera.con-recursos .acciones-cabecera { gap:4px; padding-inline-start:4px; }
  }

  .marca-cabecera:hover { opacity: 0.85; }
  .marca-cabecera:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 2px; }

  /* Neutraliza el `inline-size: 100%` de `EntrarConGoogle.svelte::.salir`
     —pensado para la columna del carril—: aquí el botón se ve del tamaño
     de su propio texto, como cualquier otro control de esta fila. */
  .cuenta-cabecera { display: inline-flex; width: max-content; flex-shrink: 0; }

  /* Mismo giro que `Carril.svelte::button[aria-label="Ajustes"]` — el CSS
     con ámbito de Svelte no cruza de un componente a otro, así que el
     botón de Ajustes de aquí necesita su propia copia de la regla para
     comportarse igual que el del carril de estudiante. */
  button[aria-label="Ajustes"] :global(svg) {
    transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  button[aria-label="Ajustes"]:hover :global(svg) {
    transform: rotate(90deg) scale(1.12);
  }

  /* Aparece con scroll, no de golpe al montarse la ruta —mismo lenguaje de
     transición suave que `entrarVista`/`popIn` ya usan en el resto del
     árbol de docente—. */
  .donde {
    margin: 0;
    margin-inline-start: auto;
    font-family: var(--fuente-manuscrita);
    font-size: 24px;
    font-weight: 700;
    color: var(--ink-primary);
    letter-spacing: -0.01em;
    animation: aparecerDonde 0.18s ease;
  }

  @keyframes aparecerDonde {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .cabecera-derecha {
    margin-inline-start: auto;
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .acciones-cabecera {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    padding-inline-start: 0.5rem;
    border-inline-start: 1px solid var(--ink-ghost);
  }

  /* ── Botones de icono solo · compartidos en trazo con `Carril.svelte`,
     duplicados a propósito: ver la nota en `CarrilHistorial.svelte`. ── */

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

  /* El botón dice si su columna está fuera o dentro. `aria-pressed` lo anuncia
     y el fondo lo enseña: dos señales, no solo el color. */
  .icono-solo[aria-pressed='true'] {
    background: var(--accent-surface);
    border-color: var(--accent-main);
    color: var(--accent-main);
  }

  /* `.abrir` y `.icono-solo` empatan en especificidad (una clase cada
     una), así que quien gane depende del ORDEN en la hoja: esta regla
     tiene que ir DESPUÉS de `.icono-solo` —arriba— para que su
     `display: none` no pierda contra el `display: inline-flex` de esa
     regla. Bug real, encontrado en el navegador el 2026-08-22: al
     partir `Aplicacion.svelte` el orden se invirtió sin querer al
     mover bloques de un lado a otro, y el botón «Abrir el menú» quedó
     visible también en escritorio —donde no gobierna nada, el carril
     ya está en el flujo normal— sin que nada lo delatara salvo verlo
     en pantalla. */
  .abrir { display: none; }
  .cabecera > .abrir { order: 1; margin-inline-end: .25rem; }

  /* Desplazamiento inteligente para abrir/plegar el panel derecho. El control
     del historial vive ahora dentro de su propio carril lateral. */
  button.plegar[data-tooltip="Herramientas"]:hover :global(svg) {
    transform: translateX(3px);
  }

  /* ── Secciones en la cabecera ─────────────────────────────────────────
     Dos presentaciones del mismo `navGlobal`, nunca las dos visibles a la
     vez — el `@media` de más abajo decide cuál. `48.0625rem` y no
     `48rem`: es `--corte-tableta` con el límite exclusivo, el mismo
     convenio que ya usa `enBandaDeTableta()` en `preferencias.svelte.js`
     para el mismo corte. `@media` no admite `var()`, el literal se repite
     a propósito. */

  .secciones-cabecera { display: none; }

  .secciones-cabecera ul,
  .mas nav ul {
    display: flex;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .secciones-cabecera ul { align-items: center; gap: 0.3rem; }

  /* En línea van con icono accesible y tooltip flotante */
  .secciones-cabecera a {
    position: relative;
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
    text-decoration: none;
    overflow: visible;
    box-shadow: var(--shadow-soft);
    transition: all 0.2s ease-out;
  }

  .secciones-cabecera a :global(svg) {
    inline-size: 22px;
    block-size: 22px;
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .secciones-cabecera a:hover {
    background: var(--surface-panel);
    border-color: var(--accent-main);
    color: var(--accent-main);
    transform: translateY(-2px);
    box-shadow: var(--shadow-soft);
  }

  .secciones-cabecera a:hover :global(svg) {
    transform: scale(1.15);
  }

  .secciones-cabecera a:active { transform: translateY(0) scale(0.95); }

  .secciones-cabecera .rotulo {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }

  .mas nav a {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4em 0.65em;
    border-radius: var(--radius-sm);
    color: var(--ink-secondary);
    font-size: var(--texto-sm);
    white-space: normal;
    overflow-wrap: anywhere;
    transition: var(--transition-fast);
  }

  .mas nav a:hover { background: var(--surface-panel); color: var(--ink-primary); }
  .solo-movil { display: none; }
  .mas nav button { display: flex; align-items: center; gap: .4rem; inline-size: 100%; min-block-size: 44px; padding: .4em .65em; border: 0; border-radius: var(--radius-sm); background: transparent; color: var(--ink-secondary); font: inherit; text-align: start; cursor: pointer; }
  .mas nav button:hover { background: var(--surface-panel); color: var(--ink-primary); }
  .salida { border-block-start: 1px solid var(--trazo-suave); margin-block-start: .3rem; padding-block-start: .3rem; }
  .mas nav button.cerrar-sesion { color: var(--cuenta-peligro); font-weight: 600; }
  .mas nav button.cerrar-sesion:hover { background: var(--cuenta-peligro-bg); color: var(--cuenta-peligro-hover); }
  .menu-profesional { display: none; position: absolute; inset-block-start: 100%; inset-inline-start: .5rem; z-index: 26; inline-size: min(18rem, calc(100vw - 1rem)); padding: .5rem; border: 1px solid var(--trazo); border-radius: var(--radius-md); background: var(--surface-paper); box-shadow: var(--shadow-float); }
  .menu-profesional ul { list-style: none; margin: 0; padding: 0; }
  .menu-profesional a { display: flex; align-items: center; gap: .6rem; min-block-size: 44px; padding: .5rem; border-radius: var(--radius-sm); color: var(--ink-primary); text-decoration: none; }
  .menu-profesional a:hover, .menu-profesional a[aria-current='page'] { background: var(--accent-surface); color: var(--accent-main); }

  /* La ruta activa, igual que ya se marca en `Carril.svelte`: fondo y
     color, no solo un signo que dependa de verlo. */
  .secciones-cabecera a[aria-current='page'],
  .mas nav a[aria-current='page'] { background: var(--accent-surface); color: var(--accent-main); }

  .mas { position: relative; }

  /* `<summary>` no trae el triángulo por defecto en los dos motores a la
     vez con la misma regla, así que se apagan los dos marcadores posibles
     y el icono de `mas` hace su trabajo. */
  .mas summary {
    list-style: none;
    cursor: pointer;
  }

  .mas summary::-webkit-details-marker { display: none; }
  .mas summary::marker { content: ''; }

  .mas nav {
    position: absolute;
    inset-inline-end: 0;
    inset-block-start: calc(100% + 0.4rem);
    z-index: 25;
    min-inline-size: 12rem;
    inline-size: max-content;
    max-inline-size: calc(100vw - 2 * max(.75rem, env(safe-area-inset-left, 0px)));
    background: var(--surface-paper);
    border: 1px solid var(--trazo);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-float);
    padding: 0.4rem;
  }

  .mas nav ul { flex-direction: column; gap: 0.1rem; }

  /* Aquí sí al tamaño del dedo: es un menú de teléfono por definición —en
     ancho libre ni se monta, ver el `@media` de abajo—. */
  .mas nav a { min-block-size: 44px; }

  @media (min-width: 48.0625rem) {
    .secciones-cabecera { display: block; }
    .mas { display: block; }
    .cabecera.con-carril .secciones-cabecera { display: none; }
  }

  @media (max-width: 75rem) {
    /* NO se toca el ancho del carril aquí: ver la nota en
       `Carril.svelte::.carril` sobre por qué 16rem no cambia en este
       corte —el botón oficial de Google necesita ese margen. Lo único
       que cede en este corte es esta cabecera. */
    .cabecera { padding: 10px 16px; }
    .donde { display: none; }

    /* En 1024 px el rótulo escrito repite el rol que ya queda marcado en el
       selector y empuja el último control de cuenta fuera del viewport.
       Conservar la marca y el selector mantiene toda la información; retirar
       sólo esta duplicación deja visibles navegación, ajustes y perfil. */
    .distintivo-rol { display: none; }
  }

  @media (max-width: 48rem) {
    .abrir { display: inline-flex; }
    .cabecera { gap:.75rem; padding:8px max(10px, env(safe-area-inset-right)) 8px max(10px, env(safe-area-inset-left)); }
    .icono-solo { inline-size:44px; block-size:44px; }
    .marca-cabecera { min-inline-size:44px; min-block-size:44px; justify-content:center; }
    .menu-profesional { display: block; }
    .solo-movil { display: block; }

    /* Un único renglón. Perfil y ajustes permanecen accesibles en «Más»;
       el cambio de espacio y el tema conservan acceso directo. */
    .cabecera.profesional {
      display: grid;
      grid-template-columns: 44px 44px minmax(0, 1fr) 50px;
      column-gap: .5rem;
      padding: 8px max(8px, env(safe-area-inset-right)) 8px max(8px, env(safe-area-inset-left));
      -webkit-text-size-adjust: 100%;
    }
    .cabecera.profesional .identidad-producto {
      grid-column: 3;
      grid-row: 1;
      justify-self: center;
      min-inline-size: 0;
      max-inline-size: 100%;
      gap: .65rem;
    }
    .cabecera.profesional .identidad-producto :global(.selector) { min-inline-size: 0; flex-shrink: 1; }
    .cabecera.profesional .identidad-producto :global(.selector .opcion) {
      padding-inline: .4rem;
      font-size: 14px;
      min-inline-size: 44px;
    }
    .cabecera.profesional .icono-solo :global(svg),
    .cabecera.profesional .mas summary :global(svg) { inline-size: 18px; block-size: 18px; }
    .cabecera.profesional .marca-cabecera :global(svg) { inline-size: 19px; block-size: 19px; }
    .cabecera.profesional > .abrir {
      grid-column: 1;
      grid-row: 1;
      justify-self: start;
      margin-inline-end:0;
    }
    .cabecera.profesional .cabecera-derecha {
      display: contents;
    }
    .cabecera.profesional .acciones-cabecera { display: contents; }
    .cabecera.profesional .mas { grid-column: 2; grid-row: 1; }
    .cabecera.profesional .acciones-cabecera :global(.tema) { grid-column: 4; grid-row: 1; justify-self: end; }
    /* La campana ocupa una columna explícita, sin crear una segunda fila. */
    .cabecera.profesional.con-recursos {
      grid-template-columns: 44px 44px minmax(0, 1fr) 44px 50px;
    }
    .cabecera.profesional.con-recursos .recursos-centro {
      grid-column: 4;
      grid-row: 1;
      justify-self: center;
      margin-left: 0;
    }
    .cabecera.profesional.con-recursos .acciones-cabecera :global(.tema) { grid-column: 5; }
    .cabecera.profesional .acciones-cabecera > button,
    .cabecera.profesional .cuenta-cabecera { display: none; }

    /* El menú se alinea con el borde del encabezado: desde la segunda
       columna, retrocede el ancho del botón de menú y la separación.
       Así caben sus enlaces también en 320 px. */
    .cabecera.profesional .mas nav {
      inset-inline-start: calc(-44px - .5rem);
      inset-inline-end: auto;
      inline-size: min(18rem, calc(100vw - 2rem - env(safe-area-inset-left, 0px) - env(safe-area-inset-right, 0px)));
    }

    .cabecera.profesional .mas summary,
    .cabecera.profesional > .abrir { inline-size: 44px; block-size: 44px; }

    .cabecera.profesional .marca-cabecera { min-inline-size: 20px; }

    .marca-cabecera span {
      position: absolute;
      inline-size: 1px;
      block-size: 1px;
      overflow: hidden;
      clip-path: inset(50%);
    }

    .distintivo-rol { display: none; }

    /* En teléfono el carril es un cajón, así que plegarlo no significa nada:
       el botón de plegar se retira y manda el de abrir. */
    .plegar { display: none; }
  }

  @media (max-width: 23rem) {
    .cabecera.profesional .identidad-producto :global(.selector .opcion) {
      padding-inline: .2rem;
      font-size: 12px;
    }
    .cabecera.profesional .marca-cabecera :global(svg) { inline-size: 19px; }
    /* Se estrechan las separaciones; los controles mantienen su área táctil. */
    .cabecera.profesional.con-recursos { column-gap: 2px; padding-inline: max(4px, env(safe-area-inset-left)); }
    .cabecera.profesional.con-recursos .identidad-producto { gap: .2rem; }
    .cabecera.profesional.con-recursos .mas { position: static; }
    .cabecera.profesional.con-recursos .mas nav { inset-inline: 8px; inline-size: auto; }

  }

  @media (prefers-reduced-motion: reduce) {
    .icono-solo:hover,
    .icono-solo:active,
    .secciones-cabecera a:hover,
    .secciones-cabecera a:active { transform: none; }
    [data-tooltip]:hover::after,
    [data-tooltip]:focus-visible::after { animation: none; }
    .donde { animation: none; }
  }
</style>
