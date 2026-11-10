<script>
  let { temaOscuro = false, colores = { paleta: 'ambar' } } = $props();
  import Icono from '../../comun/base/Icono.svelte';
  import { ENLACE_AL_TUTOR } from '../../nucleo/configuracion/origenes.js';
</script>

<section class="hero" aria-labelledby="titulo-portada">
  <div class="hero-contenido">
    <div class="hero-texto">
      <p class="sobrelinea">
        <Icono nombre="didaxia" medida={17} />
        <span>Un proyecto académico sobre cálculo diferencial</span>
      </p>
      <h1 id="titulo-portada">Entiende el cálculo <span>paso a paso.</span></h1>
      <p class="bajada">
        DidaxIa acompaña el estudio con conversación en español, explicaciones,
        comprobaciones matemáticas acotadas y representaciones gráficas.
      </p>
      <div class="acciones-hero">
        <a class="accion-principal" href="#recorrido">Conoce la aplicación <span aria-hidden="true">↓</span></a>
        <a class="accion-enlace entrada-tutor" href={ENLACE_AL_TUTOR}>Entrar al tutor <span aria-hidden="true">↗</span></a>
      </div>
      <p class="nota-acceso">Explora la aplicación sin iniciar sesión.</p>
    </div>

    <div class="hero-visual" aria-label="Vistas de DidaxIa en computador y teléfono">
      <svg class="curvas-hero" viewBox="0 0 720 460" fill="none" aria-hidden="true">
        <path class="reticula" d="M24 100H696M24 180H696M24 260H696M24 340H696M100 28V432M220 28V432M340 28V432M460 28V432M580 28V432" />
        <path class="curva-uno" d="M30 302C112 286 126 147 220 154C315 162 308 333 405 342C499 350 504 178 590 174C634 172 663 202 692 222" />
        <path class="curva-dos" d="M27 366C130 360 140 247 230 242C326 238 340 392 439 382C542 371 553 277 693 288" />
        <circle cx="405" cy="342" r="7" class="punto-curva" />
      </svg>

      <figure class="captura-escritorio">
        <div class="barra-captura">
          <span class="marca-captura"><Icono nombre="didaxia" medida={16} /> DidaxIa</span>
          <span>Estudiante · vista de la aplicación</span>
        </div>
        <img
          src={`/imagenes/demostracion/variantes/conversacion-computador-${temaOscuro ? 'oscuro' : 'claro'}-${colores.paleta}.webp`}
          alt="Captura del tutor DidaxIa en computador: conversación de cálculo diferencial y panel lateral de recursos."
          fetchpriority="high"
        />
        <figcaption>Conversación en la interfaz del tutor.</figcaption>
      </figure>

      <figure class="captura-telefono">
        <span class="isla-telefono" aria-hidden="true"></span>
        <img
          src={`/imagenes/demostracion/variantes/conversacion-telefono-${temaOscuro ? 'oscuro' : 'claro'}-${colores.paleta}.webp`}
          alt=""
          aria-hidden="true"
          loading="lazy"
          decoding="async"
        />
        <span class="barra-gestos" aria-hidden="true"></span>
        <figcaption>Vista en teléfono</figcaption>
      </figure>
    </div>
  </div>
  <div class="linea-cierre" aria-hidden="true"></div>
</section>

<style>
  .hero {
    position: relative;
    overflow: hidden;
    padding: clamp(var(--espacio-2xl), 6vw, 5.5rem) var(--espacio-lg) var(--espacio-2xl);
    background: transparent;
  }

  .hero-contenido {
    display: grid;
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    align-items: center;
    gap: clamp(var(--espacio-2xl), 5vw, 5rem);
    inline-size: min(100%, 82rem);
    margin-inline: auto;
  }

  .hero-texto {
    position: relative;
    z-index: 2;
    max-inline-size: 42rem;
  }

  .sobrelinea {
    display: flex;
    align-items: center;
    gap: var(--espacio-sm);
    margin: 0 0 var(--espacio-lg);
    color: var(--ink-tertiary);
    font-size: var(--texto-sm);
    font-weight: 600;
    letter-spacing: 0.015em;
  }

  .sobrelinea :global(svg) { color: var(--accent-main); flex: none; }

  h1 {
    max-inline-size: 13ch;
    margin: 0;
    color: var(--ink-primary);
    font-size: clamp(2.8rem, 5.3vw, 5.25rem);
    font-weight: 760;
    line-height: 0.99;
    letter-spacing: -0.055em;
    text-wrap: balance;
  }

  h1 span { color: var(--accent-main); }

  .bajada {
    max-inline-size: 39rem;
    margin: var(--espacio-lg) 0 0;
    color: var(--ink-secondary);
    font-size: clamp(var(--texto-base), 1.4vw, var(--texto-lg));
    line-height: var(--interlinea-comoda);
  }

  .acciones-hero {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--espacio-md) var(--espacio-lg);
    margin-block-start: var(--espacio-xl);
  }

  .accion-principal,
  .accion-enlace {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--espacio-sm);
    min-block-size: 48px;
    font-weight: 650;
    text-decoration: none;
    transition: background-color 180ms ease, color 180ms ease, transform 180ms ease;
  }

  .accion-principal {
    padding: 0.7rem 1rem;
    border-radius: var(--radius-trazado);
    color: var(--accent-on-main);
    background: var(--accent-main);
  }

  .accion-principal:hover { background: var(--accent-hover); transform: translateY(-1px); }

  .accion-enlace {
    color: var(--ink-secondary);
    text-decoration: underline;
    text-decoration-color: var(--trazo-suave);
    text-underline-offset: 0.25em;
  }

  .accion-enlace:hover { color: var(--accent-main); text-decoration-color: currentColor; }

  .accion-principal:focus-visible,
  .accion-enlace:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 4px;
  }

  .nota-acceso {
    margin: var(--espacio-sm) 0 0;
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
  }

  .hero-visual {
    position: relative;
    isolation: isolate;
    min-inline-size: 0;
    padding: clamp(var(--espacio-lg), 3vw, var(--espacio-2xl));
  }

  .curvas-hero {
    position: absolute;
    z-index: -1;
    inset: -4% -9% 0 -8%;
    inline-size: 118%;
    block-size: 108%;
    overflow: visible;
  }

  .reticula {
    stroke: var(--trazo-suave);
    stroke-width: 0.7;
    opacity: 0.34;
  }

  .curva-uno,
  .curva-dos {
    stroke-linecap: round;
    stroke-width: 2.4;
    stroke-dasharray: 1300;
    stroke-dashoffset: 1300;
    animation: dibujar-curva 1200ms cubic-bezier(0.22, 0.62, 0.24, 1) 120ms forwards;
  }

  .curva-uno { stroke: var(--accent-main); opacity: 0.5; }
  .curva-dos { stroke: var(--decorative-contrast); opacity: 0.45; animation-delay: 220ms; }
  .punto-curva { fill: var(--accent-main); opacity: 0.72; }

  @keyframes dibujar-curva { to { stroke-dashoffset: 0; } }

  .captura-escritorio {
    position: relative;
    z-index: 1;
    inline-size: 100%;
    margin: 0;
    overflow: hidden;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-xl);
    background: var(--surface-paper);
    box-shadow: var(--shadow-float);
    transform: rotate(-1deg);
    animation: entrar-captura 520ms ease-out both;
  }

  @keyframes entrar-captura {
    from { opacity: 0; transform: translateY(12px) rotate(-1deg); }
    to { opacity: 1; transform: translateY(0) rotate(-1deg); }
  }

  .barra-captura {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--espacio-sm);
    min-block-size: 42px;
    padding: 0 var(--espacio-md);
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
  }

  .marca-captura {
    display: inline-flex;
    align-items: center;
    gap: var(--espacio-xs);
    color: var(--ink-primary);
    font-family: var(--fuente-manuscrita);
    font-size: var(--texto-sm);
    font-weight: 700;
  }

  .marca-captura :global(svg) { color: var(--accent-main); }

  .captura-escritorio > img {
    display: block;
    inline-size: 100%;
    aspect-ratio: 16 / 9;
    object-fit: cover;
    object-position: center;
    background: var(--surface-canvas);
  }

  .captura-escritorio figcaption {
    padding: var(--espacio-xs) var(--espacio-md) var(--espacio-sm);
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
  }

  .captura-telefono {
    position: absolute;
    z-index: 2;
    inset-inline-end: 0;
    inset-block-end: -0.6rem;
    inline-size: clamp(104px, 18vw, 168px);
    margin: 0;
    padding: 5px;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-xl);
    background: var(--surface-paper);
    box-shadow: var(--shadow-float);
    transform: rotate(3deg);
    transition: transform 200ms ease;
  }

  .captura-telefono:hover { transform: rotate(1deg) translateY(-3px); }

  .captura-telefono img {
    display: block;
    inline-size: 100%;
    block-size: auto;
    border-radius: var(--radius-lg);
  }

  .isla-telefono {
    display: block;
    inline-size: 34%;
    block-size: 0.32rem;
    margin: 0.08rem auto 0.3rem;
    border-radius: 999px;
    background: color-mix(in srgb, var(--ink-primary) 84%, black);
  }

  .barra-gestos {
    display: block;
    inline-size: 34%;
    block-size: 0.12rem;
    margin: 0.32rem auto 0.1rem;
    border-radius: 999px;
    background: color-mix(in srgb, var(--ink-secondary) 76%, transparent);
  }

  .captura-telefono figcaption {
    padding: 0.25rem 0.3rem 0.1rem;
    color: var(--ink-tertiary);
    font-size: 0.65rem;
    text-align: center;
  }

  .linea-cierre {
    inline-size: min(100%, 82rem);
    block-size: 1px;
    margin: clamp(var(--espacio-2xl), 5vw, 4rem) auto 0;
    background: var(--trazo-suave);
  }

  @media (max-width: 75rem) {
    .hero-contenido { grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr); gap: var(--espacio-xl); }
    .hero-visual { padding: var(--espacio-lg); }
  }

  @media (max-width: 48rem) {
    .hero { padding: var(--espacio-2xl) var(--espacio-md) var(--espacio-xl); }
    .hero-contenido { grid-template-columns: minmax(0, 1fr); gap: var(--espacio-xl); }
    .hero-texto { max-inline-size: 39rem; }
    h1 { max-inline-size: 14ch; font-size: clamp(2.65rem, 12vw, 4rem); }
    .bajada { font-size: var(--texto-base); }
    .hero-visual { margin-inline: -0.25rem; padding: var(--espacio-md) var(--espacio-xs) var(--espacio-lg); }
    .curvas-hero { inset: -8% -5% -8%; inline-size: 110%; block-size: 116%; }
    .captura-escritorio { transform: none; }
    .captura-telefono { inset-inline-end: -0.15rem; inset-block-end: -0.15rem; inline-size: clamp(94px, 25vw, 132px); }
    .captura-telefono:hover { transform: none; }
    .linea-cierre { margin-block-start: var(--espacio-2xl); }
  }

  @media (prefers-reduced-motion: reduce) {
    .curva-uno,
    .curva-dos,
    .captura-escritorio { animation: none; stroke-dashoffset: 0; }
    .accion-principal,
    .accion-enlace,
    .captura-telefono { transition: none; }
    .accion-principal:hover,
    .captura-telefono:hover { transform: none; }
  }
</style>
