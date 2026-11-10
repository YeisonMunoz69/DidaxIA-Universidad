<script>
  import ConfirmacionArtesanal from '../base/ConfirmacionArtesanal.svelte';
  import { confirmaciones } from './confirmaciones.svelte.js';
  let abierto = $state(false);
  $effect(() => { abierto = Boolean(confirmaciones.solicitud); });
  $effect(() => { if (!abierto && confirmaciones.solicitud) confirmaciones.responder(false); });
</script>

{#if confirmaciones.solicitud}
  <ConfirmacionArtesanal bind:abierto tipo={confirmaciones.solicitud.tipo}
    titulo={confirmaciones.solicitud.titulo} descripcion={confirmaciones.solicitud.descripcion}
    confirmar={confirmaciones.solicitud.confirmar} cancelar={confirmaciones.solicitud.cancelar}
    alternativa={confirmaciones.solicitud.alternativa}
    alAlternativa={() => confirmaciones.responder('alternativa')}
    alConfirmar={() => confirmaciones.responder(true)} />
{/if}
