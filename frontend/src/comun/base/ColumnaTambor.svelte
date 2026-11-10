<script>
  import { onMount, tick } from 'svelte';
  let { etiqueta, opciones, value = $bindable(''), alCambiar = () => {} } = $props();
  let columna = $state(null), temporizador;
  let preparada = false, desplazando = false, arrastre = null, evitarClic = false;
  const id = $props.id();
  const indice = $derived(Math.max(0, opciones.findIndex((opcion) => opcion.valor === value)));
  $effect(() => {
    const destino = indice * 44;
    if (columna && preparada && !desplazando && Math.abs(columna.scrollTop - destino) > 2) columna.scrollTop = destino;
    return () => clearTimeout(temporizador);
  });
  function elegir(i) {
    const opcion = opciones[Math.max(0, Math.min(opciones.length - 1, i))];
    if (opcion) { value = opcion.valor; alCambiar(value); }
  }
  function desplazamiento() {
    if (!preparada) return;
    desplazando = true;
    elegir(Math.round(columna.scrollTop / 44));
    clearTimeout(temporizador);
    temporizador = setTimeout(() => { desplazando = false; }, 120);
  }
  function iniciar(evento) {
    if (evento.pointerType !== 'mouse' || evento.button !== 0) return;
    arrastre = { y: evento.clientY, top: columna.scrollTop, id: evento.pointerId };
  }
  function mover(evento) {
    if (!arrastre) return;
    const delta = arrastre.y - evento.clientY;
    if (Math.abs(delta) > 4) {
      evitarClic = true; evento.preventDefault();
      columna.setPointerCapture(evento.pointerId); columna.scrollTop = arrastre.top + delta;
    }
  }
  function terminar() { arrastre = null; }
  function clic(evento, i) {
    if (evitarClic) { evento.preventDefault(); evitarClic = false; return; }
    desplazando = false; elegir(i); columna.scrollTop = i * 44;
  }
  function teclado(evento) {
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End', 'PageUp', 'PageDown'].includes(evento.key)) return;
    evento.preventDefault();
    elegir(evento.key === 'Home' ? 0 : evento.key === 'End' ? opciones.length - 1 : indice + ({ArrowUp:-1,ArrowDown:1,PageUp:-5,PageDown:5}[evento.key] || 0));
  }
  onMount(() => { void tick().then(() => { if (columna) { columna.scrollTop = indice * 44; preparada = true; } }); });
</script>
<div class="grupo"><span class="etiqueta">{etiqueta}</span>
  <div class="tambor" bind:this={columna} role="listbox" aria-label={etiqueta} aria-activedescendant={`${id}-${indice}`} tabindex="0" onkeydown={teclado} onscroll={desplazamiento} onpointerdown={iniciar} onpointermove={mover} onpointerup={terminar} onpointercancel={terminar}>
    <div class="espaciador" aria-hidden="true"></div>
    {#each opciones as opcion, i (opcion.valor)}<button type="button" id={`${id}-${i}`} role="option" tabindex="-1" aria-selected={opcion.valor === value} class:elegida={opcion.valor === value} onclick={(evento) => clic(evento,i)}>{opcion.texto}</button>{/each}
    <div class="espaciador" aria-hidden="true"></div>
  </div>
</div>
<style>
  .grupo{min-width:0;flex:1}.etiqueta{display:block;text-align:center;color:var(--ink-secondary);font-size:var(--texto-xs);font-weight:750;padding:.4rem}.tambor{height:220px;overflow-y:auto;overscroll-behavior:contain;scroll-snap-type:y mandatory;scrollbar-width:none}.tambor::-webkit-scrollbar{display:none}.espaciador{height:88px;flex:none}.tambor button{display:block;width:100%;height:44px;min-height:44px;padding:0 .2rem;border:0;background:transparent;color:var(--ink-tertiary);font:inherit;font-size:var(--texto-sm);scroll-snap-align:center;cursor:pointer}.tambor button.elegida{font-weight:800;color:var(--ink-primary);font-size:var(--texto-base)}.tambor:focus-visible{outline:2px solid var(--help-color);outline-offset:-2px}
</style>
