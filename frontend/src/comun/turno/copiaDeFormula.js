import { toast } from '../estado/toasts.svelte.js';

export const CONTEXTO_COPIA_FORMULAS = 'didaxia.copiar-formulas-del-chat';

/** Copia el LaTeX original, nunca el texto duplicado del HTML/MathML de KaTeX.
 * Sólo se habilita dentro de un Turno; obras, fichas y teclas siguen siendo texto.
 */
export function copiaDeFormula(nodo, opciones) {
  let datos = opciones;
  let inicio = null, arrastrando = false;
  // Una fórmula dentro de «Abrir gráfica» conserva la acción del botón;
  // no se crea un segundo control interactivo anidado dentro de él.
  const habilitada = () => datos.habilitada && !nodo.closest('button,a');
  if (!habilitada()) return {}; // Las obras largas no necesitan escuchar cada gesto.
  function atributos() {
    if (!habilitada()) return;
    nodo.setAttribute('role', 'button');
    nodo.setAttribute('tabindex', '0');
    nodo.setAttribute('aria-label', `Copiar fórmula: ${datos.expresion}`);
    nodo.setAttribute('title', 'Copiar fórmula');
    nodo.style.cursor = 'copy';
  }
  function empezar(evento) { inicio = {x:evento.clientX,y:evento.clientY}; arrastrando = false; }
  function mover(evento) {
    if (inicio && Math.hypot(evento.clientX-inicio.x, evento.clientY-inicio.y)>8) arrastrando=true;
  }
  async function copiar() {
    if (!habilitada() || arrastrando) return;
    const seleccion = window.getSelection();
    if (seleccion && !seleccion.isCollapsed && nodo.contains(seleccion.anchorNode)) return;
    try {
      // Los delimitadores permiten pegarla en el redactor como una fórmula,
      // conservando exactamente el LaTeX recibido dentro de ellos.
      await navigator.clipboard.writeText(`$${datos.expresion}$`);
      toast.exito('Fórmula copiada');
    } catch {
      toast.error('No se pudo copiar la fórmula. Selecciónala y copia manualmente.');
    }
  }
  function tecla(evento) {
    if (habilitada() && ['Enter',' '].includes(evento.key)) {
      evento.preventDefault(); arrastrando=false; void copiar();
    }
  }
  function cancelar() { arrastrando=true; inicio=null; }
  atributos();
  nodo.addEventListener('pointerdown', empezar);
  nodo.addEventListener('pointercancel', cancelar);
  window.addEventListener('pointermove', mover);
  nodo.addEventListener('click', copiar);
  nodo.addEventListener('keydown', tecla);
  return {
    update(valor) { datos=valor; atributos(); },
    destroy() {
      nodo.removeEventListener('pointerdown', empezar);
      nodo.removeEventListener('pointercancel', cancelar);
      window.removeEventListener('pointermove', mover);
      nodo.removeEventListener('click', copiar);
      nodo.removeEventListener('keydown', tecla);
    }
  };
}
