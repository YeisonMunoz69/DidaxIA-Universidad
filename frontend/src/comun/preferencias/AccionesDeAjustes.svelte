<script>
  import Boton from '../base/Boton.svelte';
  import Icono from '../base/Icono.svelte';

  let { alRestablecer, alCancelar, alGuardar, bloqueado=false } = $props();
</script>

<div class="barra-acciones">
  <div class="lado-izq">
    <button type="button" class="btn-restablecer" onclick={alRestablecer} disabled={bloqueado}>
      <Icono nombre="reiniciar" medida={13} />
      <span>Restablecer</span>
    </button>
  </div>
  <div class="lado-der">
    <button type="button" class="btn-cancelar" onclick={alCancelar} disabled={bloqueado}>Cancelar</button>
    <Boton onclick={alGuardar} disabled={bloqueado}>Guardar</Boton>
  </div>
</div>

<style>
  .barra-acciones {
    display: flex;
    align-items: center;
    justify-content: space-between;
    inline-size: 100%;
    gap: var(--espacio-md);
    margin-block-start: var(--espacio-xs);
  }

  .lado-izq,
  .lado-der {
    display: flex;
    align-items: center;
    gap: var(--espacio-sm);
  }

  .btn-restablecer {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-block-size: 44px;
    padding: 7px 12px;
    background: transparent;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-xs);
    font-family: inherit;
    font-size: var(--texto-xs);
    font-weight: 500;
    color: var(--ink-secondary);
    cursor: pointer;
    transition: var(--transition);
  }

  .btn-restablecer:hover {
    border-color: var(--trazo);
    color: var(--ink-primary);
    background: var(--surface-canvas);
  }

  .btn-cancelar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-block-size: 44px;
    padding: 8px 16px;
    background: transparent;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    color: var(--ink-secondary);
    font-family: inherit;
    font-size: var(--texto-sm);
    font-weight: 500;
    cursor: pointer;
    transition: var(--transition);
  }

  .btn-cancelar:hover {
    background: var(--surface-canvas);
    border-color: var(--trazo);
    color: var(--ink-primary);
  }

  @media (max-width:36rem) {
    .barra-acciones { flex-wrap:wrap; }
    .lado-der { flex:1; justify-content:flex-end; }
  }
</style>
