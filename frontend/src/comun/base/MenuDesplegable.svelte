<script>
  import { onMount, tick } from 'svelte';
  let { control } = $props();
  let opciones = $state([]), elegido = $state(''), abierto = $state(false), buscar = $state('');
  let bloqueado = $state(false), indice = $state(0), nombre = $state('Opciones');
  let buscador = $state(null), panel;
  let tactil = false;
  const id = $props.id();
  const normalizar = (texto) => texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es');
  const filtradas = $derived(opciones.filter((opcion) => normalizar(opcion.texto).includes(normalizar(buscar))));
  let posicion = $state('');
  function ubicar() {
    const r = control.getBoundingClientRect();
    const ancho = Math.min(Math.max(r.width, 230), window.innerWidth - 24);
    const izquierda = Math.max(12, Math.min(r.left, window.innerWidth - ancho - 12));
    const espacio = window.innerHeight - r.bottom - 16;
    const arriba = espacio < 220 && r.top > espacio;
    posicion = `left:${izquierda}px;width:${ancho}px;${arriba ? `bottom:${window.innerHeight - r.top + 5}px` : `top:${r.bottom + 5}px`};max-height:${Math.max(140, (arriba ? r.top : espacio) - 12)}px`;
  }
  function sincronizar() {
    opciones = Array.from(control.options, (opcion, i) => ({ texto: opcion.textContent, valor: opcion.value, indice: i, deshabilitada: opcion.disabled }));
    elegido = control.selectedOptions[0]?.textContent || 'Elegir…';
    bloqueado = control.disabled;
    nombre = control.getAttribute('aria-label') || 'Opciones';
  }
  export function refrescar() { sincronizar(); }
  $effect(() => {
    control.setAttribute('aria-expanded', String(abierto));
    control.setAttribute('aria-controls', `${id}-lista`);
    if (abierto && filtradas[indice]) control.setAttribute('aria-activedescendant', `${id}-${indice}`);
    else control.removeAttribute('aria-activedescendant');
  });
  async function abrir() {
    if (control.disabled) return;
    sincronizar(); buscar = ''; indice = Math.max(0, control.selectedIndex); ubicar(); abierto = true;
    await tick();
    if (globalThis.matchMedia?.('(pointer: fine)')?.matches) buscador?.focus();
  }
  function cerrar(foco = false) { abierto = false; if (foco && !tactil) control.focus(); }
  function elegir(opcion) {
    if (!opcion || opcion.deshabilitada) return;
    control.selectedIndex = opcion.indice;
    control.dispatchEvent(new Event('input', { bubbles: true }));
    control.dispatchEvent(new Event('change', { bubbles: true }));
    sincronizar(); cerrar(true);
  }
  function teclado(evento) {
    tactil = false;
    if (evento.key === 'Escape' && abierto) { evento.preventDefault(); evento.stopPropagation(); cerrar(true); return; }
    if (['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(evento.key) && (evento.target === control || evento.key !== ' ')) {
      evento.preventDefault();
      if (!abierto) { void abrir(); return; }
      if (evento.key === 'Enter' || evento.key === ' ') elegir(filtradas[indice]);
      else {
        const paso = evento.key === 'ArrowUp' ? -1 : 1;
        indice = evento.key === 'Home' ? 0 : evento.key === 'End' ? filtradas.length - 1 : Math.max(0, Math.min(filtradas.length - 1, indice + paso));
        document.getElementById(`${id}-${indice}`)?.scrollIntoView?.({ block: 'nearest' });
      }
    }
    if (evento.key === 'Tab') cerrar();
  }
  onMount(() => {
    sincronizar();
    const observador = new MutationObserver(sincronizar);
    observador.observe(control, { childList: true, subtree: true, attributes: true, characterData: true,
      attributeFilter: ['disabled', 'value', 'label', 'selected', 'aria-label'] });
    const pointer = (evento) => { if (!control.disabled) { evento.preventDefault(); tactil = evento.pointerType === 'touch'; if (!tactil) control.focus(); } };
    const clic = (evento) => { evento.preventDefault(); abierto ? cerrar() : void abrir(); };
    const fuera = (evento) => { if (!control.contains(evento.target) && !panel?.contains(evento.target)) cerrar(); };
    const cambio = () => { sincronizar(); setTimeout(sincronizar, 0); };
    control.addEventListener('pointerdown', pointer); control.addEventListener('click', clic); control.addEventListener('keydown', teclado);
    control.addEventListener('change', cambio);
    document.addEventListener('pointerdown', fuera); window.addEventListener('resize', ubicar); document.addEventListener('scroll', ubicar, true);
    const destino = control.closest('dialog') || document.body;
    destino.appendChild(panel);
    return () => {
      observador.disconnect(); control.removeEventListener('pointerdown', pointer); control.removeEventListener('click', clic); control.removeEventListener('keydown', teclado); control.removeEventListener('change', cambio);
      document.removeEventListener('pointerdown', fuera); window.removeEventListener('resize', ubicar); document.removeEventListener('scroll', ubicar, true);
      panel?.remove();
    };
  });
</script>

<div class="apariencia" class:bloqueado aria-hidden="true"><span class="marca"></span><span class="valor">{elegido}</span><span class="flecha" class:abierto>⌄</span></div>
<div class="panel" bind:this={panel} hidden={!abierto} style={posicion} onkeydown={teclado} role="dialog" tabindex="-1" aria-label={abierto ? `Elegir ${nombre}` : undefined}>
  {#if abierto}
  <div class="cabecera"><strong>{nombre}</strong><button type="button" aria-label="Cerrar opciones" onclick={() => cerrar(true)}>×</button></div>
  {#if opciones.length > 6}<input bind:this={buscador} aria-label={`Buscar en ${nombre}`} placeholder="Buscar opción…" bind:value={buscar} oninput={() => indice = 0} />{/if}
  <div id={`${id}-lista`} class="lista" role="listbox" aria-label={`Opciones de ${nombre}`}>
    {#each filtradas as opcion, i (opcion.indice)}
      <button type="button" id={`${id}-${i}`} role="option" aria-selected={control.selectedIndex === opcion.indice} class:seleccionada={control.selectedIndex === opcion.indice} class:enfocada={indice === i} disabled={opcion.deshabilitada} onclick={() => elegir(opcion)}><span>{opcion.texto}</span>{#if control.selectedIndex === opcion.indice}<span aria-hidden="true">✓</span>{/if}</button>
    {:else}<p>No hay coincidencias.</p>{/each}
  </div>
  {/if}
</div>

<style>
  .apariencia{position:absolute;inset:0;display:flex;align-items:center;gap:.5rem;padding:.55rem .7rem;pointer-events:none;border:1px solid var(--trazo);border-radius:var(--radius-sm);background:var(--surface-paper);color:var(--ink-primary);box-shadow:var(--shadow-soft);font-size:var(--texto-sm)}.valor{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.marca{width:6px;height:6px;flex:none;border-radius:50%;background:var(--accent-main)}.flecha{transition:transform .2s}.flecha.abierto{transform:rotate(180deg)}.bloqueado{opacity:.55}
  .panel{position:fixed;z-index:1100;display:flex;flex-direction:column;gap:.4rem;padding:.5rem;overflow:hidden;background:var(--surface-paper);color:var(--ink-primary);border:1px solid var(--trazo-suave);border-radius:var(--radius-md);box-shadow:var(--shadow-float);animation:entrada .18s ease-out;box-sizing:border-box}.panel[hidden]{display:none}.cabecera{display:flex;align-items:center;justify-content:space-between;gap:.5rem;font-size:var(--texto-xs)}.cabecera button{min-width:44px;min-height:44px;border:0;background:transparent;color:var(--ink-secondary);font-size:1.5rem}.panel input{width:100%;min-height:44px;box-sizing:border-box;border:1px solid var(--trazo);border-radius:var(--radius-sm);background:var(--surface-panel);color:var(--ink-primary);padding:.5rem;font:inherit;font-size:16px}.lista{min-height:0;overflow:auto;overscroll-behavior:contain}.lista button{width:100%;min-height:44px;display:flex;justify-content:space-between;gap:.5rem;text-align:start;padding:.6rem;border:0;border-radius:var(--radius-xs);background:transparent;color:var(--ink-primary);font:inherit;font-size:var(--texto-sm);cursor:pointer}.lista button:hover,.lista button.enfocada,.lista button.seleccionada{background:var(--accent-surface);color:var(--accent-main)}.lista button:disabled{opacity:.45;cursor:not-allowed}button:focus-visible{outline:2px solid var(--help-color);outline-offset:-2px}@keyframes entrada{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}@media(prefers-reduced-motion:reduce){.panel{animation:none}.flecha{transition:none}}
</style>
