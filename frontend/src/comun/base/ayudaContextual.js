import { mount, unmount } from 'svelte';
import GloboAyuda from './GloboAyuda.svelte';
let cerrarActual;
let siguienteId = 0;
export function ayudaContextual(nodo, opciones = {}) {
  let parametros = opciones;
  let titulo = nodo.getAttribute('title') || '';
  const descripcionAnterior = nodo.getAttribute('aria-describedby');
  const id = `ayuda-contextual-${++siguienteId}`;
  let componente;
  let anfitrion;
  let temporizador;
  let ignorarHover = false;
  let modalActivo = false;
  let fijada = false;
  function recogerTitulo() {
    if (nodo.hasAttribute('title')) {
      titulo = nodo.getAttribute('title') || '';
      nodo.removeAttribute('title');
    }
  }
  recogerTitulo();
  const observador = new MutationObserver(recogerTitulo);
  observador.observe(nodo, { attributes: true, attributeFilter: ['title'] });
  function cerrar() {
    clearTimeout(temporizador);
    modalActivo = false; fijada = false;
    if (componente) {
      const anterior = componente;
      const contenedor = anfitrion;
      componente = null;
      anfitrion = null;
      void unmount(anterior).then(() => contenedor.remove());
    }
    if (descripcionAnterior) nodo.setAttribute('aria-describedby', descripcionAnterior);
    else nodo.removeAttribute('aria-describedby');
    if (parametros.movil) nodo.setAttribute('aria-expanded', 'false');
    if (cerrarActual === cerrar) cerrarActual = null;
  }
  function abrir() {
    clearTimeout(temporizador);
    const texto = parametros.texto ?? titulo;
    if (componente || !texto) return;
    const movil = window.matchMedia?.('(max-width: 48rem)').matches ?? false;
    if (movil && !parametros.movil) return;
    cerrarActual?.(); cerrarActual = cerrar;
    modalActivo = movil;
    anfitrion = document.createElement('div');
    (nodo.closest('dialog') ?? document.body).append(anfitrion);
    anfitrion.addEventListener('pointerenter', () => clearTimeout(temporizador));
    anfitrion.addEventListener('pointerleave', programarCierre);
    componente = mount(GloboAyuda, { target: anfitrion, props: {
      texto, id, movil, interactiva: !!parametros.movil, caja: nodo.getBoundingClientRect(), obtenerCaja: () => nodo.getBoundingClientRect(), alCerrar: cerrar
    } });
    if (!movil) nodo.setAttribute('aria-describedby', [descripcionAnterior, id].filter(Boolean).join(' '));
    if (parametros.movil) nodo.setAttribute('aria-expanded', 'true');
  }
  function programarCierre() { if (modalActivo || fijada) return; temporizador = setTimeout(cerrar, 180); }
  function alEntrar(evento) { if (evento.pointerType !== 'touch' && !ignorarHover && !window.matchMedia?.('(max-width: 48rem)').matches) abrir(); }
  function alSalir() { ignorarHover = false; programarCierre(); }
  function alFoco() { if (!window.matchMedia?.('(max-width: 48rem)').matches) abrir(); }
  function alClic() { if (parametros.movil) { if (componente && fijada) cerrar(); else { abrir(); fijada = true; } } }
  function fuera(evento) { if (!nodo.contains(evento.target) && !anfitrion?.contains(evento.target)) cerrar(); }
  function escape(evento) { if (evento.key === 'Escape' && componente && !modalActivo) { evento.preventDefault(); evento.stopPropagation(); ignorarHover = true; cerrar(); } }
  nodo.addEventListener('pointerenter', alEntrar); nodo.addEventListener('pointerleave', alSalir);
  nodo.addEventListener('focus', alFoco); nodo.addEventListener('blur', programarCierre); nodo.addEventListener('click', alClic);
  document.addEventListener('pointerdown', fuera); document.addEventListener('keydown', escape);
  window.addEventListener('resize', cerrar);
  function alDesplazar() { if (!modalActivo) componente?.reubicar?.(); }
  document.addEventListener('scroll', alDesplazar, true);
  return {
    update(nuevas) { parametros = nuevas ?? {}; cerrar(); },
    destroy() {
      cerrar(); observador.disconnect();
      nodo.removeEventListener('pointerenter', alEntrar); nodo.removeEventListener('pointerleave', alSalir);
      nodo.removeEventListener('focus', alFoco); nodo.removeEventListener('blur', programarCierre); nodo.removeEventListener('click', alClic);
      document.removeEventListener('pointerdown', fuera); document.removeEventListener('keydown', escape);
      window.removeEventListener('resize', cerrar); document.removeEventListener('scroll', alDesplazar, true);
    }
  };
}
