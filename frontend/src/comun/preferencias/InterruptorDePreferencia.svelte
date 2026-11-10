<script>
  let { nombre, pista, valor, alCambiar } = $props();
</script>

<label class="fila">
  <span class="texto"><strong>{nombre}</strong><small>{pista}</small></span>
  <input type="checkbox" role="switch" aria-label={nombre} checked={valor}
    onchange={(evento) => alCambiar(evento.currentTarget.checked)} />
  <span class="interruptor" class:activo={valor} aria-hidden="true"><span></span></span>
</label>

<style>
  .fila { position:relative; display:flex; align-items:center; justify-content:space-between; gap:1rem; min-inline-size:0; min-block-size:4.25rem; padding:.8rem 1rem; background:var(--surface-paper); border:1px solid var(--trazo-suave); border-radius:var(--radius-md); cursor:pointer; }
  .fila:hover { border-color:var(--trazo); }
  .fila:focus-within { outline:2px solid var(--accent-main); outline-offset:2px; }
  .texto { display:grid; gap:.2rem; min-inline-size:0; }
  strong { color:var(--ink-primary); font-size:var(--texto-sm); }
  small { color:var(--ink-tertiary); font-size:var(--texto-xs); line-height:1.4; }
  input { position:absolute; inset:0; opacity:0; cursor:pointer; }
  .interruptor { flex:none; display:flex; align-items:center; inline-size:2.7rem; block-size:1.6rem; padding:.16rem; border:1px solid var(--trazo); border-radius:var(--radius-pill); background:var(--surface-panel); transition:var(--transition); }
  .interruptor.activo { border-color:transparent; background:var(--accent-main); }
  .interruptor span { inline-size:1.15rem; block-size:1.15rem; border-radius:50%; background:var(--surface-paper); box-shadow:var(--shadow-soft); transition:transform .2s ease; }
  .interruptor.activo span { transform:translateX(1.08rem); }
  @media (prefers-reduced-motion:reduce) { .interruptor, .interruptor span { transition:none; } }
</style>
