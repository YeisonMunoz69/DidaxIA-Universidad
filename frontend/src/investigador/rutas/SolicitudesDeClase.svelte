
<script>
  import CabeceraDeRuta from '../../docente/piezas/CabeceraDeRuta.svelte';
  import SolicitudesDeMatricula from '../../comun/clases/SolicitudesDeMatricula.svelte';
</script>

<div class="desplazable">
  <section class="solicitudes-institucionales">
    <CabeceraDeRuta titulo="Solicitudes de matrícula" icono="clases"
      insignia="Gestión institucional" notaGrande>
      {#snippet nota()}
        Revisa ingresos y cambios de clase. Cada aprobación conserva el origen,
        el destino, el actor y la fecha, y mantiene una sola clase vigente.
      {/snippet}
    </CabeceraDeRuta>

    <div class="panel">
      <SolicitudesDeMatricula titulo="Pendientes de la institución" />
    </div>
  </section>
</div>

<style>
  .desplazable { flex: 1; min-block-size: 0; inline-size: 100%; overflow-y: auto; }
  .solicitudes-institucionales { display: flex; inline-size: min(78rem, 100%); min-block-size: 100%; margin-inline: auto; padding: var(--espacio-lg); flex-direction: column; gap: var(--espacio-lg); }
  .panel { flex: 1; min-block-size: 24rem; padding: var(--espacio-lg); border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-panel); box-shadow: var(--shadow-soft); }
</style>
