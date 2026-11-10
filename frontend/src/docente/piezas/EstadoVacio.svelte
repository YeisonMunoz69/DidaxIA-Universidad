
<script>
  import Icono from '../../comun/base/Icono.svelte';

  let {
    icono,
    titulo = '',
    texto,
    tono = 'neutro',
    medidaIcono = tono === 'invitacion' ? 22 : 28
  } = $props();
</script>

<div class="tarjeta-vacia {tono}">
  <div class="circulo-icono-vacio">
    <Icono nombre={icono} medida={medidaIcono} />
  </div>
  {#if titulo}<h3>{titulo}</h3>{/if}
  <p>{texto}</p>
</div>

<style>
  .tarjeta-vacia {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: var(--espacio-sm);
    padding: var(--espacio-xl) var(--espacio-lg);
    border-radius: var(--radius-md);
  }

  .tarjeta-vacia.exito,
  .tarjeta-vacia.neutro {
    background: var(--surface-panel);
    border: 1px dashed var(--trazo);
  }

  .tarjeta-vacia.invitacion {
    gap: 10px;
    max-inline-size: 26rem;
    border-radius: var(--radius-lg);
    border: 1.5px dashed var(--accent-main);
    background: var(--accent-surface);
  }

  .circulo-icono-vacio {
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .exito .circulo-icono-vacio,
  .neutro .circulo-icono-vacio {
    inline-size: 56px;
    block-size: 56px;
  }

  .exito .circulo-icono-vacio {
    background: var(--semantic-success-bg);
    color: var(--semantic-success);
  }

  .neutro .circulo-icono-vacio {
    background: var(--surface-paper);
    color: var(--ink-tertiary);
    border: 1px solid var(--trazo-suave);
  }

  .invitacion .circulo-icono-vacio {
    inline-size: 64px;
    block-size: 64px;
    margin-block-end: 4px;
    background: var(--surface-paper);
    border: 1.5px solid var(--accent-main);
    color: var(--accent-main);
    animation: popIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  @keyframes popIn {
    from { transform: scale(0.88); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }

  .invitacion h3 { margin: 0; font-size: var(--texto-lg); font-weight: 700; color: var(--accent-main); }

  .tarjeta-vacia p { margin: 0; font-size: var(--texto-sm); color: var(--ink-tertiary); line-height: 1.4; }

  .invitacion p { color: var(--ink-secondary); }
</style>
