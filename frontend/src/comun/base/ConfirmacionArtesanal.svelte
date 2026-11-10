<script>
  import Dialogo from './Dialogo.svelte';
  import Boton from './Boton.svelte';
  let { abierto = $bindable(false), tipo='confirmar', titulo, descripcion,
    confirmar='Confirmar', cancelar='Volver', alternativa='', alAlternativa, alConfirmar, bloqueado=false, children } = $props();
</script>

<Dialogo bind:abierto {tipo} {titulo} {bloqueado}>
  <p>{descripcion}</p>
  {@render children?.()}
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => abierto = false} deshabilitado={bloqueado}>{cancelar}</Boton>
    <Boton variante={alternativa ? 'secundario' : 'principal'} onclick={alConfirmar} deshabilitado={bloqueado}>{bloqueado ? 'Procesando…' : confirmar}</Boton>
    {#if alternativa}<Boton variante="exito" onclick={alAlternativa} deshabilitado={bloqueado}>{alternativa}</Boton>{/if}
  {/snippet}
</Dialogo>

<style>
  p { margin:0; line-height:1.55; overflow-wrap:anywhere; }
</style>
