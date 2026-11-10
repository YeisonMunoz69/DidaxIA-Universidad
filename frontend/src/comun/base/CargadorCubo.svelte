
<script>
  let { mensaje = 'Cargando…', pantallaCompleta = false, compacto = false } = $props();
</script>

<div class="cargador-cubo" class:pantalla-completa={pantallaCompleta} class:compacto>
  <div class="escena" aria-hidden="true">
    <div class="spinner"><div></div><div></div><div></div><div></div><div></div><div></div></div>
  </div>
  <p role="status" aria-live="polite" aria-atomic="true">{mensaje}</p>
</div>

<style>
  .cargador-cubo {
    --lado: 70.4px;
    --borde: 3.5px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 1.25rem;
    padding: 2rem 1rem;
    box-sizing: border-box;
    inline-size: 100%;
    min-inline-size: 0;
    flex-shrink: 0;
  }
  .pantalla-completa { flex: 1; min-block-size: 20rem; }
  .compacto { --lado: 45.76px; --borde: 2.275px; gap: .8rem; padding: 1.25rem 1rem; }
  .escena {
    display: grid;
    place-items: center;
    inline-size: calc(var(--lado) * 1.85);
    block-size: calc(var(--lado) * 1.85);
    flex-shrink: 0;
  }
  .spinner {
    --clr: var(--accent-main);
    --clr-alpha: color-mix(in srgb, var(--accent-main) 12%, transparent);
    width: var(--lado);
    height: var(--lado);
    position: relative;
    animation: spinner 1.6s infinite ease;
    transform-style: preserve-3d;
  }
  .spinner > div {
    box-sizing: border-box;
    background-color: var(--clr-alpha);
    height: 100%;
    position: absolute;
    width: 100%;
    border: var(--borde) solid var(--clr);
  }
  .spinner > div:nth-of-type(1) { transform: translateZ(calc(var(--lado) / -2)) rotateY(180deg); }
  .spinner > div:nth-of-type(2) { transform: rotateY(-270deg) translateX(50%); transform-origin: top right; }
  .spinner > div:nth-of-type(3) { transform: rotateY(270deg) translateX(-50%); transform-origin: center left; }
  .spinner > div:nth-of-type(4) { transform: rotateX(90deg) translateY(-50%); transform-origin: top center; }
  .spinner > div:nth-of-type(5) { transform: rotateX(-90deg) translateY(50%); transform-origin: bottom center; }
  .spinner > div:nth-of-type(6) { transform: translateZ(calc(var(--lado) / 2)); }
  p {
    margin: 0;
    max-inline-size: min(32rem, 100%);
    color: var(--ink-secondary);
    font-size: var(--texto-sm);
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
  @keyframes spinner {
    0% { transform: rotate(45deg) rotateX(-25deg) rotateY(25deg); }
    50% { transform: rotate(45deg) rotateX(-385deg) rotateY(25deg); }
    100% { transform: rotate(45deg) rotateX(-385deg) rotateY(385deg); }
  }
  @media (prefers-reduced-motion: reduce) {
    .spinner { animation: none; transform: rotate(45deg) rotateX(-25deg) rotateY(25deg); }
  }
</style>
