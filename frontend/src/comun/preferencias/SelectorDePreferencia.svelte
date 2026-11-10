<script>
  import Icono from '../base/Icono.svelte';
  let { titulo, icono, nombre, opciones, valor, alElegir, variante = 'tema' } = $props();
  const iconosTema = { claro: 'sol', oscuro: 'tema', sistema: 'pantalla' };
</script>

<fieldset class="selector">
  <legend><Icono nombre={icono} medida={16} /> {titulo}</legend>
  <div class="opciones" class:tarjetas={variante === 'tema'} class:segmentos={variante === 'escala'}>
    {#each opciones as opcion (opcion.id)}
      <label class="opcion" class:activa={valor === opcion.id}>
        <input type="radio" name={nombre} value={opcion.id} checked={valor === opcion.id}
          onchange={() => alElegir(opcion.id)} />
        {#if variante === 'tema'}
          <span class="miniatura" class:oscuro={opcion.id === 'oscuro'} class:sistema={opcion.id === 'sistema'} aria-hidden="true">
            <span class="mini-linea"></span><span class="mini-linea corta"></span>
          </span>
          <span class="nombre-tema"><Icono nombre={iconosTema[opcion.id]} medida={16} /> {opcion.nombre}</span>
          <span class="marca" aria-hidden="true"><Icono nombre="check" medida={12} /></span>
        {:else}
          <span class="letra" class:mediana={opcion.id === 'comoda'} class:grande={opcion.id === 'grande'} aria-hidden="true">A</span>
          <span class="texto-segmento"><strong>{opcion.nombre}</strong><small>{opcion.pista}</small></span>
        {/if}
      </label>
    {/each}
  </div>
</fieldset>

<style>
  .selector { min-inline-size:0; margin:0; padding:0; border:0; }
  legend { display:flex; align-items:center; gap:.4rem; margin-block-end:.7rem; padding:0; color:var(--ink-primary); font-size:var(--texto-sm); font-weight:700; }
  .opciones { display:grid; gap:.65rem; min-inline-size:0; grid-template-columns:repeat(3,minmax(0,1fr)); }
  .opcion { position:relative; min-inline-size:0; cursor:pointer; transition:var(--transition); }
  input { position:absolute; inset:0; opacity:0; cursor:pointer; }
  .opcion:focus-within { outline:2px solid var(--accent-main); outline-offset:2px; }
  .tarjetas .opcion { display:grid; gap:.55rem; padding:.65rem; border:1px solid var(--trazo-suave); border-radius:var(--radius-md); background:var(--surface-paper); }
  .tarjetas .opcion:hover, .segmentos .opcion:hover { border-color:var(--trazo); }
  .tarjetas .opcion.activa { border-color:var(--accent-main); background:var(--accent-surface); box-shadow:var(--shadow-soft); }
  .miniatura { display:grid; align-content:center; gap:.35rem; block-size:3.4rem; padding:.75rem; border:1px solid var(--muestra-claro-trazo); border-radius:var(--radius-sm); background:var(--muestra-claro-fondo); }
  .miniatura.oscuro { background:var(--muestra-oscuro-fondo); border-color:var(--muestra-oscuro-trazo); }
  .miniatura.sistema { background:linear-gradient(90deg,var(--muestra-claro-fondo) 50%,var(--muestra-oscuro-fondo) 50%); }
  .mini-linea { inline-size:70%; block-size:.25rem; border-radius:var(--radius-pill); background:var(--muestra-claro-trazo); }
  .mini-linea.corta { inline-size:45%; }
  .oscuro .mini-linea { background:var(--muestra-oscuro-trazo); }
  .nombre-tema { display:flex; align-items:center; gap:.3rem; color:var(--ink-primary); font-size:var(--texto-sm); font-weight:600; white-space:nowrap; }
  .marca { position:absolute; inset-block-start:.85rem; inset-inline-end:.85rem; display:grid; place-items:center; inline-size:1.15rem; block-size:1.15rem; border-radius:50%; background:var(--accent-main); color:var(--surface-paper); opacity:0; }
  .activa .marca { opacity:1; }
  .segmentos { gap:0; padding:.25rem; border:1px solid var(--trazo-suave); border-radius:var(--radius-pill); background:var(--surface-panel); }
  .segmentos .opcion { display:flex; align-items:center; justify-content:center; gap:.5rem; min-block-size:3.4rem; padding:.4rem .5rem; border:1px solid transparent; border-radius:var(--radius-pill); text-align:center; }
  .segmentos .opcion.activa { border-color:var(--accent-main); background:var(--surface-paper); box-shadow:var(--shadow-soft); }
  .letra { flex:none; color:var(--accent-main); font-weight:700; font-size:1rem; }
  .letra.mediana { font-size:1.15rem; }
  .letra.grande { font-size:1.3rem; }
  .texto-segmento { display:grid; gap:.1rem; min-inline-size:0; color:var(--ink-primary); font-size:var(--texto-xs); line-height:1.2; }
  .texto-segmento small { color:var(--ink-tertiary); font-size:var(--texto-xs); }
  @media (max-width:36rem) { .tarjetas .opcion { padding:.45rem; } .miniatura { block-size:2.8rem; } .nombre-tema { font-size:var(--texto-xs); } .segmentos .opcion { flex-direction:column; gap:0; padding:.45rem .2rem; } }
</style>
