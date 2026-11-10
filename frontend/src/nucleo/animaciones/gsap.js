import { gsap } from 'gsap';

export function reduccionDeMovimiento() {
  return typeof window !== 'undefined'
    && Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
}

export function animarEntradaMensaje(nodo) {
  if (!nodo || typeof window === 'undefined') return;

  gsap.fromTo(
    nodo,
    {
      opacity: 0,
      y: 22,
      scale: 0.96
    },
    {
      opacity: 1,
      y: 0,
      scale: 1,
      duration: 0.45,
      ease: 'power3.out'
    }
  );
}

export function animarEntradaLoader(nodo) {
  if (!nodo || typeof window === 'undefined') return;

  gsap.fromTo(
    nodo,
    {
      opacity: 0,
      y: 16,
      scale: 0.92
    },
    {
      opacity: 1,
      y: 0,
      scale: 1,
      duration: 0.42,
      ease: 'back.out(1.6)'
    }
  );
}

export function animarGiroTema(nodoIcono) {
  if (!nodoIcono || typeof window === 'undefined') return;

  const svg = nodoIcono.querySelector('svg') || nodoIcono;
  gsap.fromTo(
    svg,
    { rotation: 0, scale: 0.75 },
    {
      rotation: 360,
      scale: 1,
      duration: 0.55,
      ease: 'back.out(2)',
      clearProps: 'transform'
    }
  );
}

export function animarPestanaTeclas(contenedor) {
  if (!contenedor || typeof window === 'undefined' || reduccionDeMovimiento()) return;

  const teclas = contenedor.querySelectorAll('.tecla');
  if (!teclas.length) return;

  gsap.fromTo(
    teclas,
    {
      opacity: 0,
      y: 8,
      scale: 0.94
    },
    {
      opacity: 1,
      y: 0,
      scale: 1,
      duration: 0.22,
      stagger: 0.012,
      ease: 'power2.out',
      clearProps: 'transform,opacity'
    }
  );
}

export { ejecutarTransicionCircularDeTema } from '../preferencias/transicionDeTema.js';

export function animarDesplazamientoAbajo(elemento, duracion = 0.38) {
  if (!elemento || typeof window === 'undefined') return;

  gsap.killTweensOf(elemento);
  gsap.to(elemento, {
    scrollTop: () => elemento.scrollHeight,
    duration: duracion,
    ease: 'power2.out',
    overwrite: 'auto'
  });
}
