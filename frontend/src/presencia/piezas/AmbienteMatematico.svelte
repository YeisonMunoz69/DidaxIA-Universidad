<!-- Ambiente animado compartido por Inicio y las páginas públicas. Sin video ni red. -->
<div class="ambiente" aria-hidden="true">
  <svg class="curvas" viewBox="0 0 1440 900" preserveAspectRatio="none">
    <path class="curva curva-principal" d="M-100 600 C 180 180, 520 730, 805 420 S 1250 130, 1540 450" />
    <path class="curva curva-secundaria" d="M-100 340 C 230 720, 560 80, 880 500 S 1280 760, 1540 270" />
    <path class="curva curva-terciaria" d="M-100 760 C 280 410, 420 210, 760 370 S 1230 720, 1540 560" />
  </svg>
  <span class="bruma bruma-a"></span>
  <span class="bruma bruma-b"></span>
  <span class="simbolo simbolo-a">∫</span>
  <span class="simbolo simbolo-b">f′(x)</span>
  <span class="simbolo simbolo-c">lim</span>
  <span class="simbolo simbolo-d">dy/dx</span>
  <div class="velo"></div>
</div>

<style>
  .ambiente {
    position: fixed;
    inset: 0;
    z-index: 0;
    overflow: hidden;
    pointer-events: none;
    background:
      radial-gradient(ellipse at 18% 30%, color-mix(in srgb, var(--accent-surface) 76%, transparent), transparent 46%),
      radial-gradient(ellipse at 84% 68%, color-mix(in srgb, var(--decorative-contrast-glow) 62%, transparent), transparent 48%),
      var(--surface-canvas);
  }
  .curvas {
    position: absolute;
    inset: -5% -4%;
    inline-size: 108%;
    block-size: 110%;
    overflow: visible;
    opacity: .72;
    filter: drop-shadow(0 0 12px color-mix(in srgb, var(--accent-main) 16%, transparent));
    animation: deriva 34s ease-in-out infinite alternate;
  }
  .curva {
    fill: none;
    stroke: var(--accent-main);
    stroke-width: 1.65;
    stroke-linecap: round;
    vector-effect: non-scaling-stroke;
    stroke-dasharray: 120 24;
    animation: recorrer 34s linear infinite;
  }
  .curva-principal { opacity: .22; stroke-width: 2.1; stroke-dasharray: 220 32; animation-duration: 42s; }
  .curva-secundaria { opacity: .12; stroke-dasharray: 110 30; animation-direction: reverse; animation-duration: 53s; }
  .curva-terciaria { opacity: .11; stroke-dasharray: 70 42; animation-duration: 31s; }
  .bruma {
    position: absolute;
    inline-size: min(44vw, 34rem);
    aspect-ratio: 1;
    border-radius: 50%;
    background: radial-gradient(circle, color-mix(in srgb, var(--accent-main) 10%, transparent), transparent 68%);
    filter: blur(8px);
    animation: respirar 14s ease-in-out infinite alternate;
  }
  .bruma-a { inset: 8% auto auto 8%; }
  .bruma-b { inset: auto 5% 0 auto; animation-delay: -7s; animation-duration: 19s; }
  .simbolo {
    position: absolute;
    color: var(--ink-tertiary);
    font-family: var(--fuente-mono);
    font-weight: 700;
    opacity: .11;
    animation: flotar 13s ease-in-out infinite alternate;
  }
  .simbolo-a { inset: 18% 20% auto auto; font-size: 4rem; }
  .simbolo-b { inset: auto auto 22% 16%; font-size: 2.1rem; animation-delay: -2s; }
  .simbolo-c { inset: 28% auto auto 13%; font-size: 2rem; animation-delay: -5s; }
  .simbolo-d { inset: auto 12% 18% auto; font-size: 2rem; animation-delay: -7s; }
  .velo {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, color-mix(in srgb, var(--surface-canvas) 4%, transparent), color-mix(in srgb, var(--surface-canvas) 36%, transparent));
  }
  @keyframes recorrer { to { stroke-dashoffset: -720; } }
  @keyframes deriva { to { transform: translate3d(1.2%, -1%, 0) scale(1.015); } }
  @keyframes respirar { to { transform: translate3d(3vw, -2vh, 0) scale(1.12); opacity: .7; } }
  @keyframes flotar { to { transform: translate3d(12px, -16px, 0) rotate(2deg); opacity: .22; } }
  @media (prefers-reduced-motion: reduce) {
    .curvas, .curva, .bruma, .simbolo { animation: none; }
  }
  @media (max-width: 48rem) {
    .curvas { inset: -3% -26%; inline-size: 152%; opacity: .56; }
    .bruma { inline-size: 74vw; }
    .simbolo-a { inset-inline-end: 8%; font-size: 3rem; }
    .simbolo-b { inset-inline-start: 7%; }
  }
</style>
