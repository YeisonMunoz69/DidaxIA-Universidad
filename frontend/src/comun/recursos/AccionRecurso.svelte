<script>
  import Icono from '../base/Icono.svelte';
  import Boton from '../base/Boton.svelte';
  let { icono, children, type = 'button', disabled = false, class: clase = '', ...resto } = $props();
  const variante = $derived(clase.split(' ').includes('primario') ? 'principal' : 'secundario');
</script>

<Boton tipo={type} {variante} deshabilitado={disabled} class={`boton ${variante} ${clase}`} {...resto}>
  <span class:guardar={icono === 'guardar'}><Icono nombre={icono} medida={19} /></span>
  {@render children?.()}
</Boton>

<style>
  span { display:inline-flex; }
  .guardar { color:var(--semantic-success); }
</style>
