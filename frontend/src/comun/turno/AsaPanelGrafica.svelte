<script>
  import { ayudaContextual } from '../base/ayudaContextual.js';
  let { altura = $bindable(280) } = $props();
  let arrastrando = $state(false);
  let origenY = 0;
  let alturaInicial = 280;

  function limites(elemento) {
    const contenedor = elemento.closest('.grafica, .laboratorio-graficas');
    const disponible = contenedor?.getBoundingClientRect().height ?? window.innerHeight;
    return { minimo: 150, maximo: Math.max(150, Math.floor(disponible - 112)) };
  }

  function ajustar(valor, elemento) {
    const { minimo, maximo } = limites(elemento);
    altura = Math.max(minimo, Math.min(maximo, Math.round(valor)));
  }

  function iniciar(evento) {
    if (!evento.isPrimary || evento.button !== 0) return;
    evento.preventDefault();
    origenY = evento.clientY;
    alturaInicial = altura;
    arrastrando = true;
    evento.currentTarget.setPointerCapture(evento.pointerId);
  }

  function mover(evento) {
    if (arrastrando) ajustar(alturaInicial + origenY - evento.clientY, evento.currentTarget);
  }

  function terminar(evento) {
    if (!arrastrando) return;
    arrastrando = false;
    if (evento.currentTarget.hasPointerCapture(evento.pointerId)) {
      evento.currentTarget.releasePointerCapture(evento.pointerId);
    }
  }

  function teclado(evento) {
    const paso = evento.shiftKey ? 80 : 32;
    const limitesActuales = limites(evento.currentTarget);
    if (evento.key === 'ArrowUp') ajustar(altura + paso, evento.currentTarget);
    else if (evento.key === 'ArrowDown') ajustar(altura - paso, evento.currentTarget);
    else if (evento.key === 'Home') ajustar(limitesActuales.minimo, evento.currentTarget);
    else if (evento.key === 'End') ajustar(limitesActuales.maximo, evento.currentTarget);
    else return;
    evento.preventDefault();
  }
</script>

<button use:ayudaContextual type="button" class="asa-panel" class:arrastrando
        aria-label={`Altura del panel: ${altura} píxeles. Arrastra o usa las flechas arriba y abajo.`}
        title="Arrastra para cambiar la altura del panel"
        onpointerdown={iniciar} onpointermove={mover}
        onpointerup={terminar} onpointercancel={terminar} onkeydown={teclado}>
  <span aria-hidden="true"></span>
</button>

<style>
  .asa-panel {
    position: sticky; inset-block-start: 0; z-index: 2;
    display: grid; place-items: center; inline-size: 100%; min-block-size: 44px;
    margin: -.75rem 0 0; padding: 0; border: 0; border-radius: var(--radius-sm);
    background: var(--surface-paper); cursor: ns-resize; touch-action: none;
  }
  .asa-panel span { inline-size: 2.4rem; block-size: .3rem; border-radius: var(--radius-pill); background: var(--trazo); }
  .asa-panel:hover span, .asa-panel.arrastrando span { background: var(--accent-main); }
  .asa-panel:focus-visible { outline: 2px solid var(--accent-main); outline-offset: -2px; }
  @media (prefers-reduced-motion: no-preference) {
    .asa-panel span { transition: inline-size 140ms ease, background-color 140ms ease; }
    .asa-panel:hover span, .asa-panel.arrastrando span { inline-size: 3rem; }
  }
</style>
