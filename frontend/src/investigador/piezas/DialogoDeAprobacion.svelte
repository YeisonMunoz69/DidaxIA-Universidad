<!--
Confirmar una aprobación · `EQ-023` / C2B.

Un paso intermedio entre el botón y la escritura. No es ceremonia: aprobar la
autorización del representante legal de un menor **habilita el acceso de esa
persona al sistema** y no hay operación que lo deshaga —`representante_revision`
sólo admite `INSERT`, y un disparador rechaza `UPDATE` y `DELETE`—. La vía para
corregir es que el estudiante cargue un documento nuevo, que depende de él y no
de quien se equivocó.

QUÉ DICE EL TEXTO, Y POR QUÉ DICE ESO
---------------------------------------
Que la decisión queda registrada con su autor y su fecha, y que no se puede
deshacer desde aquí. Las dos cosas son ciertas y las dos importan antes de
pulsar. No se pide escribir nada ni repetir el número: el gesto ya es
deliberado, y una fricción mayor haría que se buscara la forma de saltárselo.

CERRAR NO CANCELA UNA PETICIÓN EN VUELO
-----------------------------------------
Mientras `enviando` está puesto, `Dialogo.svelte` bloquea las tres vías de
cierre —Esc, la X y el clic fuera—. Cerrar a mitad dejaría a quien aprobó sin
saber si quedó registrado, y la respuesta honesta a esa duda es reintentar, que
puede resolver dos veces lo mismo.



-->
<script>
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import Boton from '../../comun/base/Boton.svelte';

  let {
    abierto = $bindable(false),
    /** Para nombrar el intento sin nombrar a nadie. */
    intento = 0,
    /** Petición en vuelo: bloquea el cierre y el doble envío. */
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
    <!-- `deshabilitado` mientras hay una petición: es la mitad de la defensa
         contra el doble envío. La otra mitad está en la ruta, que ignora una
         segunda llamada aunque este botón llegara a pulsarse dos veces. -->
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
