<!-- Ambiente matemático del estado vacío. Es decorativo y no intercepta gestos. -->
<div class="ambiente" aria-hidden="true">
  <div class="halo halo-a"></div>
  <div class="halo halo-b"></div>
  <svg class="curva curva-a" viewBox="0 0 600 240" preserveAspectRatio="none">
    <path d="M-20 175 C80 20 180 25 255 145 S420 260 620 44" />
  </svg>
  <svg class="curva curva-b" viewBox="0 0 600 240" preserveAspectRatio="none">
    <path d="M-10 80 C95 210 205 205 300 75 S500 -18 620 140" />
  </svg>
  <span class="simbolo s1">∂</span>
  <span class="simbolo s2">∫</span>
  <span class="simbolo s3">f′(x)</span>
  <span class="simbolo s4">lim</span>
  <span class="simbolo s5">dy/dx</span>
</div>

<style>
  .ambiente {
    position: absolute;
    inset: 0;
    overflow: hidden;
    pointer-events: none;
    opacity: .78;
  }

  .halo {
    position: absolute;
    inline-size: min(52vw, 46rem);
    aspect-ratio: 1;
    border-radius: 50%;
    filter: blur(58px);
    opacity: .2;
    animation: respirar 9s ease-in-out infinite alternate;
  }
  .halo-a { inset: 8% auto auto 13%; background: var(--accent-main); }
  .halo-b { inset: auto 8% 2% auto; background: var(--decorative-contrast); animation-delay: -4s; }

  .curva {
    position: absolute;
    inline-size: min(72rem, 86vw);
    block-size: min(19rem, 34vh);
    overflow: visible;
    opacity: .2;
    filter: drop-shadow(0 0 14px var(--accent-glow));
  }
  .curva path { fill: none; stroke: var(--accent-main); stroke-width: 2.1; stroke-linecap: round; }
  .curva-a { inset: 9% auto auto 4%; animation: deriva 12s ease-in-out infinite alternate; }
  .curva-b { inset: auto 2% 8% auto; transform: scaleX(-1); opacity: .12; animation: deriva 15s ease-in-out -7s infinite alternate-reverse; }

  .simbolo {
    position: absolute;
    color: color-mix(in srgb, var(--accent-main) 62%, var(--ink-secondary));
    font-family: var(--fuente-mono);
    font-size: clamp(1rem, 2.3vw, 2rem);
    opacity: .24;
    filter: blur(.15px);
    animation: flotar 8s ease-in-out infinite alternate;
  }
  .s1 { left: 12%; top: 24%; }
  .s2 { right: 14%; top: 21%; animation-delay: -2s; font-size: clamp(1.6rem, 3.8vw, 3.2rem); }
  .s3 { left: 18%; bottom: 18%; animation-delay: -5s; }
  .s4 { right: 26%; bottom: 16%; animation-delay: -3s; }
  .s5 { right: 7%; top: 52%; animation-delay: -6s; }

  @keyframes respirar { to { transform: translate3d(5%, -4%, 0) scale(1.12); opacity: .27; } }
  @keyframes deriva { to { transform: translate3d(5vw, 1.2rem, 0) scale(1.035); } }
  @keyframes flotar { to { transform: translate3d(0, -18px, 0) rotate(2deg); opacity: .36; } }

  @media (max-width: 48rem) {
    .ambiente { opacity: .62; }
    .halo { inline-size: 80vw; filter: blur(42px); }
    .halo-a { inset: 24% auto auto -8%; }
    .halo-b { inset: 34% -8% auto auto; }
    .curva { inline-size: 120vw; }
    .s3, .s5 { display: none; }
  }

  @media (prefers-reduced-motion: reduce) {
    .halo, .curva, .simbolo { animation: none; }
  }
</style>
