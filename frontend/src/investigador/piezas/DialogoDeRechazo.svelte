
<script>
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Campo from '../../comun/base/Campo.svelte';

  let {
    abierto = $bindable(false),
    intento = 0,
    enviando = false,
    alConfirmar,
    alCancelar
  } = $props();

  let motivo = $state('');
  let error = $state('');

  $effect(() => {
    if (abierto) {
      motivo = '';
      error = '';
    }
  });

  function enviar() {
    const texto = motivo.trim();
    if (!texto) {
      error = 'Escriba el motivo: es lo que el estudiante verá para saber qué corregir.';
      return;
    }
    error = '';
    alConfirmar?.(texto);
  }
</script>

<Dialogo bind:abierto tipo="eliminar" titulo="Rechazar esta autorización" bloqueado={enviando}>
  <p>
    Va a rechazar el <strong>intento {intento}</strong> de este estudiante.
  </p>

  <Campo
    etiqueta="Motivo del rechazo"
    bind:valor={motivo}
    multilinea={true}
    requerido={true}
    {error}
    rows="4"
    disabled={enviando}
    ayuda="Lo leerá el estudiante. Diga qué tiene que corregir: «la firma no se ve», «falta la segunda página»." />

  <p class="consecuencia">
    La decisión queda registrada con su autor y su fecha. El estudiante podrá
    cargar un documento nuevo; el rechazo se conserva.
  </p>

  {#snippet acciones()}
    <Boton variante="secundario" deshabilitado={enviando} onclick={alCancelar}>
      Cancelar
    </Boton>
    <Boton deshabilitado={enviando} onclick={enviar}>
      {enviando ? 'Rechazando…' : 'Rechazar'}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  p { margin: 0 0 var(--espacio-sm); font-size: var(--texto-sm); color: var(--ink-secondary); }
  .consecuencia { margin-block: var(--espacio-sm) 0; }
</style>
