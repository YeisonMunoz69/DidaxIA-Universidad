<script>
  import AlternarGrafica from '../../estudiante/piezas/AlternarGrafica.svelte';
  import ElegirNotacion from '../../estudiante/piezas/ElegirNotacion.svelte';
</script>

<div class="panel-animado grupos-matematica">
  <div class="grupo">
    <ElegirNotacion />
  </div>
  <div class="grupo">
    <span class="grupo-titulo">Representación visual</span>
    <AlternarGrafica />
  </div>
</div>

<style>
  .panel-animado {
    animation: aparecerSuave 0.22s cubic-bezier(0.22, 1, 0.36, 1);
  }

  @keyframes aparecerSuave {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .grupos-matematica {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-lg);
  }

  .grupo {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-xs);
    margin: 0;
    padding: 0;
    border: 0;
  }

  .grupo-titulo {
    display: block;
    padding: 0;
    margin-block-end: var(--espacio-xs);
    font-size: var(--texto-sm);
    font-weight: 500;
    color: var(--ink-secondary);
  }
</style>
