import { mount, unmount, tick } from 'svelte';
import MenuDesplegable from './MenuDesplegable.svelte';

/** Mejora progresiva: conserva el select real, sus valores tipados, labels,
 * validación, envío de formulario y todos sus listeners existentes. */
export function menuDesplegable(control) {
  if (!control.hasAttribute('aria-label')) {
    const etiqueta = Array.from(control.labels ?? []).map((label) => {
      const copia = label.cloneNode(true);
      copia.querySelectorAll('select,input,textarea,button').forEach((nodo) => nodo.remove());
      return copia.textContent.trim();
    }).join(' ').trim();
    if (etiqueta) control.setAttribute('aria-label', etiqueta);
  }
  const marco = document.createElement('span');
  marco.className = 'menu-desplegable-marco';
  control.before(marco); marco.appendChild(control);
  control.classList.add('menu-desplegable-nativo');
  const interfaz = mount(MenuDesplegable, { target: marco, props: { control } });
  let activa = true;
  // La selección tipada de Svelte se aplica después de montar la acción.
  const refrescar = () => void tick().then(() => { if (activa) interfaz.refrescar(); });
  refrescar();
  return { update: refrescar, destroy() {
    activa = false;
    void unmount(interfaz);
    if (marco.parentNode) { marco.before(control); marco.remove(); }
    control.classList.remove('menu-desplegable-nativo');
  } };
}
