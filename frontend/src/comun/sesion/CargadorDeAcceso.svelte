
<span class="cargador" role="status" aria-label="Verificando tu cuenta con Google">
  <svg viewBox="0 0 48 48" aria-hidden="true">
    <circle class="orbita orbita-1" cx="24" cy="24" r="20" />
    <circle class="orbita orbita-2" cx="24" cy="24" r="15" />
    <g class="reloj">
      <path d="M17 12h14M17 36h14M19 13c0 6 3 7 5 11-2 4-5 5-5 11M29 13c0 6-3 7-5 11 2 4 5 5 5 11" />
      <path class="arena" d="M20.5 31h7L24 26z" />
    </g>
  </svg>
  <span class="solo-lectura-asistida">Verificando tu cuenta con Google…</span>
</span>

<style>
  .cargador {
    display: grid;
    place-items: center;
    inline-size: 46px;
    block-size: 46px;
    border: 1px solid var(--trazo-suave);
    border-radius: 50%;
    background: var(--surface-paper);
    color: var(--accent-main);
    box-shadow: var(--shadow-soft);
    animation: aparecer .18s ease-out both;
  }
  svg { inline-size: 38px; block-size: 38px; overflow: visible; }
  .orbita { fill: none; stroke: currentColor; stroke-width: 1.4; stroke-dasharray: 12 9; opacity: .24; transform-origin: 24px 24px; animation: orbitar 2s linear infinite; }
  .orbita-2 { stroke-dasharray: 5 8; opacity: .38; animation-direction: reverse; animation-duration: 1.45s; }
  .reloj { fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; transform-origin: 24px 24px; animation: voltear 2s cubic-bezier(.65, 0, .35, 1) infinite; }
  .arena { fill: currentColor; stroke: none; opacity: .72; animation: arena 1s ease-in-out infinite alternate; }
  @keyframes aparecer { from { opacity: 0; transform: scale(.72); } }
  @keyframes orbitar { to { transform: rotate(360deg); } }
  @keyframes voltear { 0%, 42% { transform: rotate(0); } 58%, 100% { transform: rotate(180deg); } }
  @keyframes arena { to { transform: translateY(-2px); opacity: .38; } }
  @media (prefers-reduced-motion: reduce) {
    .cargador, .orbita, .reloj, .arena { animation: none; }
  }
</style>
