
<script>
  import Icono from '../../../comun/base/Icono.svelte';
  import EntrarConGoogle from '../../../comun/sesion/EntrarConGoogle.svelte';

</script>

<div class="entrada">
  <div class="escena" aria-hidden="true">
    <div class="orbita orbita-uno"></div>
    <div class="orbita orbita-dos"></div>
    <span class="ficha ficha-derivada">f′(x)</span>
    <span class="ficha ficha-limite">lim</span>
    <span class="ficha ficha-integral">∫</span>
    <svg viewBox="0 0 420 220" focusable="false">
      <path class="cuadricula" d="M0 44H420M0 88H420M0 132H420M0 176H420M70 0V220M140 0V220M210 0V220M280 0V220M350 0V220" />
      <path class="curva-sombra" d="M8 175 C70 170 82 40 145 52 S220 190 278 127 S344 30 412 62" />
      <path class="curva" d="M8 175 C70 170 82 40 145 52 S220 190 278 127 S344 30 412 62" />
    </svg>
    <div class="punto-activo"><span></span></div>
  </div>

  <div class="acceso">
    <p class="promesa">DidaxIa es tu espacio para comprender, practicar y continuar donde lo dejaste.</p>
    <div class="boton-google"><EntrarConGoogle /></div>
    <p class="pie">
      <Icono nombre="candado" medida={12} />
      <span>No hay acceso anónimo · cuenta institucional protegida</span>
    </p>
  </div>
</div>

<style>
  .entrada {
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) minmax(260px, 0.85fr);
    gap: clamp(1.25rem, 4vw, 3rem);
    align-items: center;
    min-block-size: 300px;
  }

  .escena {
    position: relative;
    min-block-size: 270px;
    overflow: hidden;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-lg);
    background:
      radial-gradient(circle at 74% 24%, color-mix(in srgb, var(--accent-main) 20%, transparent), transparent 25%),
      linear-gradient(145deg, var(--surface-canvas), var(--surface-panel));
    box-shadow: var(--shadow-card);
  }

  .escena svg {
    position: absolute;
    inset: 12% -4% 2%;
    inline-size: 108%;
    block-size: 86%;
  }

  .cuadricula { fill: none; stroke: var(--ink-ghost); stroke-width: 1; }
  .curva-sombra { fill: none; stroke: var(--accent-main); stroke-width: 13; opacity: 0.12; }
  .curva {
    fill: none;
    stroke: var(--accent-main);
    stroke-width: 4;
    stroke-linecap: round;
    stroke-dasharray: 700;
    animation: recorrer-curva 5.5s cubic-bezier(.65, 0, .35, 1) infinite;
  }

  .orbita {
    position: absolute;
    border: 1px solid color-mix(in srgb, var(--accent-main) 35%, transparent);
    border-radius: 50%;
    animation: respirar 4s ease-in-out infinite;
  }
  .orbita-uno { inline-size: 150px; block-size: 150px; inset: 20px 28px auto auto; }
  .orbita-dos { inline-size: 92px; block-size: 92px; inset: 49px 57px auto auto; animation-delay: -1.2s; }

  .ficha {
    position: absolute;
    z-index: 2;
    display: grid;
    place-items: center;
    min-inline-size: 45px;
    block-size: 34px;
    padding-inline: 10px;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-pill);
    background: var(--surface-blur);
    color: var(--ink-primary);
    font-family: var(--fuente-mono);
    font-weight: 700;
    box-shadow: var(--shadow-soft);
    animation: flotar 4.8s ease-in-out infinite;
  }
  .ficha-derivada { inset: 22px auto auto 24px; }
  .ficha-limite { inset: auto 22px 22px auto; animation-delay: -1.7s; }
  .ficha-integral { inset: auto auto 28px 34px; animation-delay: -3.1s; }

  .punto-activo {
    position: absolute;
    inset: 39% 31% auto auto;
    inline-size: 22px;
    block-size: 22px;
    border-radius: 50%;
    border: 1px solid var(--accent-main);
    animation: pulso 2s ease-out infinite;
  }
  .punto-activo span { display: block; margin: 7px; inline-size: 6px; block-size: 6px; border-radius: 50%; background: var(--accent-main); }

  .acceso { display: flex; flex-direction: column; gap: 1.15rem; align-items: flex-start; }

  .promesa { margin: 0; max-inline-size: 30ch; font-size: clamp(1.05rem, 2vw, 1.35rem); line-height: 1.4; color: var(--ink-secondary); }

  .boton-google { display: flex; inline-size: 100%; }

  .pie {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 6px;
    margin: 0;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    text-align: start;
  }

  @keyframes recorrer-curva {
    0% { stroke-dashoffset: 700; opacity: 0.18; }
    38%, 70% { stroke-dashoffset: 0; opacity: 1; }
    100% { stroke-dashoffset: -700; opacity: 0.18; }
  }
  @keyframes respirar { 50% { transform: scale(1.08); opacity: 0.55; } }
  @keyframes flotar { 50% { transform: translateY(-7px) rotate(1deg); } }
  @keyframes pulso { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--accent-main) 35%, transparent); } 70% { box-shadow: 0 0 0 18px transparent; } }

  @media (max-width: 48rem) {
    .entrada { grid-template-columns: 1fr; min-block-size: 0; gap: 1rem; }
    .escena { min-block-size: 185px; }
    .acceso { align-items: stretch; }
    .promesa { max-inline-size: none; text-align: center; }
    .boton-google, .pie { justify-content: center; }
  }

  @media (prefers-reduced-motion: reduce) {
    .curva, .orbita, .ficha, .punto-activo { animation: none; }
  }

  :global(html[data-animaciones='no']) .curva,
  :global(html[data-animaciones='no']) .orbita,
  :global(html[data-animaciones='no']) .ficha,
  :global(html[data-animaciones='no']) .punto-activo { animation: none; }
</style>
