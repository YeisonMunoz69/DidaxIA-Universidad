
<script>
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import Boton from '../../comun/base/Boton.svelte';

  let {
    abierto = $bindable(false),
    intento = 0,
    enviando = false,
    alConfirmar,
    alCancelar
  } = $props();
</script>

<Dialogo bind:abierto tipo="confirmar" titulo="Aprobar esta autorización" bloqueado={enviando}>
  <p>
    Va a aprobar el <strong>intento {intento}</strong> de este estudiante.
  </p>
  <p class="consecuencia">
    La decisión queda registrada con su autor y su fecha, y <strong>no se puede
    deshacer desde aquí</strong>: corregirla exige que el estudiante cargue un
    documento nuevo.
  </p>

  {#snippet acciones()}
    <Boton variante="secundario" deshabilitado={enviando} onclick={alCancelar}>
      Cancelar
    </Boton>

    <Boton deshabilitado={enviando} onclick={alConfirmar}>
      {enviando ? 'Aprobando…' : 'Aprobar'}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  p { margin: 0 0 var(--espacio-sm); font-size: var(--texto-sm); color: var(--ink-secondary); }
  p:last-child { margin-block-end: 0; }
  .consecuencia { color: var(--ink-primary); }
</style>
