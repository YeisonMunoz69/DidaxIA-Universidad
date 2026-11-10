  <!--
  La progresión de fases mientras se espera.

  Fase en curso destacada, cumplidas con su marca. Es el componente que el mockup
  ya ensayó y que `DD-11` convirtió en decisión.

  Por qué acumula en vez de sustituir: una espera muda no distingue un sistema que
  trabaja de uno que se colgó. Al terminar se lee el recorrido completo.

  Accesibilidad. `role="status"` con `aria-live="polite"` para que el lector de
  pantalla anuncie cada fase SIN interrumpir lo que esté leyendo — con `assertive`
  cortaría al estudiante a media frase en cada fase, que sería peor que callar.
  Las marcas son `aria-hidden` porque el texto ya dice lo que hay que saber, y la
  animación se desactiva bajo `prefers-reduced-motion`.



  -->
<script>
  import { animarEntradaLoader } from '../../nucleo/animaciones/gsap.js';

  let {
    /** Estado creado con `crearProgreso()`. */
    progreso = null
  } = $props();

  const SIMBOLOS = ['∑', '∫', '∂', 'π', '∇', 'Δ', 'λ', '∞'];
  let indice = $state(0);

  $effect(() => {
    const intervalo = setInterval(() => {
      indice = (indice + 1) % SIMBOLOS.length;
    }, 400);
    return () => clearInterval(intervalo);
  });
</script>

<div class="msg-wrapper agent typing-wrapper active" id="typing-wrapper" use:animarEntradaLoader>
  <div class="typing-indicator" id="typing-indicator" role="status" aria-live="polite">
    <div class="typing-symbols" aria-hidden="true">
      <span class="typing-symbol">{SIMBOLOS[indice % SIMBOLOS.length]}</span>
      <span class="typing-symbol">{SIMBOLOS[(indice + 1) % SIMBOLOS.length]}</span>
      <span class="typing-symbol">{SIMBOLOS[(indice + 2) % SIMBOLOS.length]}</span>
    </div>
    <span class="typing-text">{progreso?.actual?.texto || 'Recibiendo tu consulta…'}</span>
  </div>
</div>

  <style>
    .typing-wrapper {
      display: flex;
      margin-block: 16px 20px;
      align-self: flex-start;
    }

    .typing-indicator {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 20px;
      background: var(--surface-panel);
      border: 1px solid var(--ink-ghost);
      border-radius: var(--radius-md);
      border-end-start-radius: 4px;
      inline-size: fit-content;
      box-shadow: var(--shadow-soft);
    }

    .typing-symbols {
      display: flex;
      gap: 5px;
      align-items: center;
    }

    .typing-symbol {
      color: var(--accent-main);
      font-size: 16px;
      font-weight: bold;
      font-family: var(--fuente-mono);
      animation: pulseSymbol 1.5s ease-in-out infinite;
      display: inline-block;
      min-inline-size: 14px;
      text-align: center;
    }

    .typing-symbol:nth-child(2) {
      animation-delay: 0.15s;
    }

    .typing-symbol:nth-child(3) {
      animation-delay: 0.3s;
    }

    @keyframes pulseSymbol {
      0%, 100% {
        opacity: 0.3;
        transform: scale(0.85) translateY(0);
      }
      50% {
        opacity: 1;
        transform: scale(1.15) translateY(-2px);
      }
    }

    .typing-text {
      font-size: 13px;
      font-family: var(--fuente-texto);
      color: var(--ink-secondary);
      font-weight: 500;
      letter-spacing: 0.01em;
    }

    @media (prefers-reduced-motion: reduce) {
      .typing-wrapper { animation: none; }
      .typing-symbol { animation: none; }
    }
  </style>
