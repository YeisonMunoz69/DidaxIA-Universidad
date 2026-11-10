/**
 * Utilidades de animación y micro-interacciones cinéticas con GSAP.
 *
 * Sigue los principios del Lenguaje de Diseño (OE3-Implementacion/13-Lenguaje-de-Diseno.md):
 * - Curvas de desaceleración naturales (power3.out, back.out).
 * - Seguro bajo jsdom / SSR.
 */
import { gsap } from 'gsap';

/**
 * Comprueba si el entorno es seguro para animar.
 * @returns {boolean}
 */
export function reduccionDeMovimiento() {
  return typeof window !== 'undefined'
    && Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
}

/**
 * Directiva de acción para Svelte 5 que anima la entrada de un mensaje en el chat.
 * @param {HTMLElement} nodo
 */
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

/**
 * Directiva de acción para animar la aparición del indicador de carga/pensamiento.
 * @param {HTMLElement} nodo
 */
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

/**
 * Anima la rotación suave y dinámica del icono de cambio de tema.
 * @param {HTMLElement} nodoIcono
 */
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

/**
 * Anima la transición de las teclas al cambiar de pestaña en el teclado de símbolos.
 * @param {HTMLElement} contenedor
 */
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

/**
 * Revela el tema nuevo como una onda que nace en el control que la disparó.
 * La View Transitions API crea las dos capturas; Web Animations gobierna el
 * `clip-path` de la nueva. Sin soporte o con movimiento reducido, cambia al
 * instante y conserva exactamente la misma actualización de estado.
 *
 * @param {MouseEvent | TouchEvent | KeyboardEvent | null} evento
 * @param {'claro' | 'oscuro'} nuevoTema
 * @param {() => void} callbackCambio — guarda la preferencia
 */
export { ejecutarTransicionCircularDeTema } from '../preferencias/transicionDeTema.js';

/**
 * Desplaza suavemente un contenedor con scroll hacia abajo con interpolación fluida a 60fps.
 * Evalúa scrollHeight de forma dinámica en cada cuadro de animación para sincronizarse
 * con expansiones CSS de cajones o teclados.
 *
 * @param {HTMLElement} elemento
 * @param {number} [duracion=0.38]
 */
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
