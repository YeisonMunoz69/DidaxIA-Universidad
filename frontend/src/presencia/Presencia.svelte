<!--
La raíz de la superficie pública · `D0` §10.1.

Es el equivalente de `Aplicacion.svelte` para `didaxia.pro`, y **es un archivo
distinto a propósito**. Lo que aquélla hace —sincronizar la sesión, calcular
el acceso, aplicar guardas, cargar el historial, montar el carril, seguir las
preferencias— no tiene sentido en una portada anónima, y meterlo detrás de un
`{#if}` habría dejado esas llamadas dentro del mismo paquete que se descarga
al abrir `didaxia.pro`.

LO QUE ESTA SUPERFICIE NO HACE, Y ES SU CONTRATO ENTERO
---------------------------------------------------------
No consulta `/api/sesion` ni ninguna otra ruta del backend. No carga Google
Identity Services. Sólo conserva en `localStorage` la preferencia visual de
tema —sin identidad ni telemetría—; no usa `sessionStorage` ni cookies. No
importa el árbol del estudiante, del docente ni del investigador.
No usa `enrutado/rutas.js` —la tabla privada— y no ejecuta ninguna lógica
conductual. No depende de PostgreSQL.

Eso se comprueba y no se promete: `pruebas/contrato/superficie-publica.prueba.js`
recorre el grafo de importaciones desde este archivo y falla si alcanza
cualquiera de esos módulos.

EL ENRUTADO SON ENLACES NORMALES
-----------------------------------
Sin biblioteca de enrutado y sin manipular la historia: cada página es un
documento y `<a href="/privacidad">` recarga. Cuatro páginas estáticas no
justifican un enrutador, y así el botón de atrás, «abrir en pestaña nueva» y
copiar el enlace funcionan sin escribir una línea. El camino se lee una vez al
montar; en producción `Caddyfile` devuelve `indice.html` para cualquier ruta,
igual que `vite.config.js` en desarrollo.

EL ARMAZÓN ES EL DE LA APLICACIÓN, Y ESO SÍ SE COMPARTE
----------------------------------------------------------
`#aplicacion` mide `100dvh` (`base.css`), así que lo que se desplaza tiene que
hacerlo por dentro — la misma regla de `13-Lenguaje-de-Diseno.md` §8. De ahí
`.desplazable` con `min-block-size: 0`, igual que `PantallaDesplazable.svelte`
en el árbol del docente. Los tokens y la tipografía también son los mismos:
`principal.js` carga las tres hojas antes de montar cualquiera de las dos
superficies.


Lenguaje declarado en OE3-Implementacion/13-Lenguaje-de-Diseno.md

-->
<script>
  import "./entrada-tutor.css";
  import SaltarAlContenido from '../comun/base/SaltarAlContenido.svelte';
  import CabeceraPublica from './piezas/CabeceraPublica.svelte';
  import PiePublico from './piezas/PiePublico.svelte';
  import BarraDesplazamiento from './piezas/BarraDesplazamiento.svelte';
  import AmbienteMatematico from './piezas/AmbienteMatematico.svelte';
  import PantallaNoEncontrada from '../comun/base/PantallaNoEncontrada.svelte';
  import { normalizar, paginaDe } from './rutas.js';
  import { guardarTema, leerTema } from '../nucleo/preferencias/tema.js';
  import { aplicarColores, leerColoresPublicos, guardarColoresPublicos, PALETAS, configuracionDe } from '../nucleo/preferencias/colores.js';

  let {
    /**
     * El camino a pintar. Por defecto, el de la barra de direcciones.
     *
     * Es una prop y no una lectura suelta de `location` para que las pruebas
     * puedan montar cada página sin tocar el `location` de jsdom, que no es
     * reasignable.
     */
    camino = globalThis.location?.pathname ?? '/'
  } = $props();

  const actual = $derived(normalizar(camino));
  const pagina = $derived(paginaDe(actual));
  let elementoDesplazable = $state(null);
  let scrollProgreso = $state(0);
  let tema = $state(leerTema());
  let colores = $state(inicializarColores());
  function inicializarColores() {
    if (normalizar(camino) !== '/') return leerColoresPublicos();
    const elegida = configuracionDe(PALETAS[Math.floor(Math.random() * PALETAS.length)].id);
    guardarColoresPublicos(elegida);
    return elegida;
  }
  let sistemaOscuro = $state(
    globalThis.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  );
  const temaOscuro = $derived(
    tema === 'oscuro' || (tema === 'sistema' && sistemaOscuro)
  );

  $effect(() => {
    const consulta = globalThis.matchMedia?.('(prefers-color-scheme: dark)');
    const alCambiar = () => { sistemaOscuro = Boolean(consulta?.matches); };
    consulta?.addEventListener('change', alCambiar);
    return () => consulta?.removeEventListener('change', alCambiar);
  });

  $effect(() => {
    globalThis.document?.body?.classList.toggle('dark-theme', temaOscuro);
    globalThis.document?.documentElement?.classList.toggle('dark-theme', temaOscuro);
    aplicarColores(colores,temaOscuro);
  });

  function alDesplazar() {
    if (!elementoDesplazable) return;
    const maxScroll = elementoDesplazable.scrollHeight - elementoDesplazable.clientHeight;
    scrollProgreso = maxScroll > 0
      ? Math.min(1, Math.max(0, elementoDesplazable.scrollTop / maxScroll))
      : 0;
  }
</script>

<SaltarAlContenido />

<div
  bind:this={elementoDesplazable}
  class="desplazable"
  onscroll={alDesplazar}
>
  <!-- Barra de progreso cinematográfica al deslizar -->
  <div
    class="barra-progreso-scroll"
    style:transform="scaleX({scrollProgreso})"
    aria-hidden="true"
  ></div>

  <!-- Componente flotante de desplazamiento estandarizado para didaxia.pro -->
  <BarraDesplazamiento contenedor={elementoDesplazable} />

  <AmbienteMatematico />

  <CabeceraPublica actual={pagina ? actual : ''} {temaOscuro}
    {colores} alElegirColores={c => { colores=c; guardarColoresPublicos(c); }}
    alElegirTema={(nuevo) => { tema = nuevo; guardarTema(nuevo); }} />

  <main id="contenido">
    {#if actual === '/'}
      {#if pagina}
        {@const Pagina = pagina.componente}
        <Pagina {temaOscuro} {colores} />
      {/if}
    {:else}
      <div class="columna">
        {#if pagina}
          {@const Pagina = pagina.componente}
          <Pagina />
        {:else}
          <!--
            `T-13`, igual que en el árbol privado: «no existe» no se disfraza de
            portada. Redirigir en silencio a `/` haría perder la dirección
            tecleada antes de poder copiarla para reportarla.
          -->
          <PantallaNoEncontrada camino={actual} />
        {/if}
      </div>
    {/if}
  </main>

  <PiePublico />
</div>

<style>
  /*
    DOS CAPAS, Y LAS DOS IMPORTAN — mismo reparto que
    `docente/piezas/PantallaDesplazable.svelte`: `.desplazable` es quien
    scrollea, a ancho completo, y `.columna` sólo centra y acolcha. Juntas en
    el mismo elemento, la barra de desplazamiento aparecería en el borde de la
    columna centrada y no en el de la ventana.
  */
  .desplazable {
    position: relative;
    flex: 1;
    min-block-size: 0;
    overflow-y: auto;
    inline-size: 100%;
    display: flex;
    flex-direction: column;
    background: var(--surface-canvas);
    isolation: isolate;
    /* Oculta la barra nativa para dar paso al componente flotante estandarizado */
    scrollbar-width: none;
  }

  .desplazable::-webkit-scrollbar {
    display: none;
    inline-size: 0;
    block-size: 0;
  }

  /* Barra de progreso de lectura cinematográfica */
  .barra-progreso-scroll {
    position: sticky;
    top: 0;
    left: 0;
    inline-size: 100%;
    block-size: 3px;
    background: var(--accent-gradient);
    transform-origin: 0% 50%;
    z-index: 100;
    pointer-events: none;
    transition: transform 0.08s ease-out;
  }

  main,
  :global(.pie) {
    position: relative;
    z-index: 1;
  }

  main {
    flex: 1;
    inline-size: 100%;
  }

  .columna {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    gap: var(--espacio-2xl);
    inline-size: 100%;
    /* `min(…, 100%)` y no un ancho fijo: a 320 px la columna es la pantalla
       menos el relleno, y nada provoca desplazamiento horizontal. */
    max-inline-size: min(82rem, 100%);
    margin-inline: auto;
    padding: var(--espacio-2xl) var(--espacio-lg);
  }


  @media (max-width: 48rem) {
    .columna {
      gap: var(--espacio-xl);
      padding: var(--espacio-xl) var(--espacio-md);
    }
  }
</style>
