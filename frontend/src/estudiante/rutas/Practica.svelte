<script>
  import AnimacionBallenaDeepSeek from '../../comun/estado/AnimacionBallenaDeepSeek.svelte';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import { navegar } from '../../enrutado/navegar.js';
</script>

<section class="proximamente" aria-labelledby="titulo-practica" class:sin-animacion={!preferencias.animaciones}>
  <h1 id="titulo-practica">Página disponible pronto<span class="puntos" aria-hidden="true">…</span></h1>
  <p>Estamos preparando este espacio de práctica. Puedes continuar con el tutor.</p>
  <AnimacionBallenaDeepSeek amplio />
  <button type="button" onclick={() => navegar('/')}>Volver al tutor</button>
</section>

<style>
  .proximamente { inline-size: min(100%, 46rem); margin-inline: auto; padding: clamp(1rem, 4vw, 2.5rem);
    display: grid; align-content: center; gap: 1rem; min-block-size: 100%; }
  h1 { margin: 0; font-size: clamp(1.4rem, 4vw, 2rem); color: var(--ink-primary); }
  p { margin: 0; color: var(--ink-secondary); line-height: 1.6; }
  button { justify-self: start; min-block-size: 44px; padding: .6rem 1rem; border-radius: var(--radius-sm);
    border: 1px solid var(--trazo); background: var(--surface-paper); color: var(--ink-primary); font: inherit; cursor: pointer; }
  .puntos { display: inline-block; animation: esperar 1.8s ease-in-out infinite; }
  .sin-animacion .puntos { animation: none; }
  @keyframes esperar { 50% { opacity: .3; } }
  @media (prefers-reduced-motion: reduce) { .puntos { animation: none; } }
</style>
