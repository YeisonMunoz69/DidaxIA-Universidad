<!--
Rechazar con motivo · `EQ-021` / C2B.

`EQ-021` pide un **motivo comprensible de rechazo**, y este diálogo es donde se
escribe. Sin él no se envía nada.

EL MOTIVO ES PARA EL ESTUDIANTE, NO PARA EL EXPEDIENTE
--------------------------------------------------------
Y eso decide cómo se pide. Quien lee ese texto es alguien a quien acaban de
rechazarle la autorización de su representante legal y necesita saber **qué
corregir**: «ilegible» le sirve, «no cumple» no. La ayuda del campo lo dice en
esos términos en vez de pedir «justificación».

LA VALIDACIÓN ES ACCESIBLE, NO SÓLO VISIBLE
---------------------------------------------
El mensaje viaja por `error` de `Campo.svelte`, que lo ata al control con
`aria-errormessage` y marca `aria-invalid`. Un texto rojo suelto debajo del
campo no lo anuncia ningún lector de pantalla, y quien navega por teclado se
queda sin saber por qué no pasa nada al pulsar.

Se valida **al enviar** y no a cada tecla: marcar en rojo un campo que todavía
se está escribiendo es hostil, y aquí no hay ningún formato que adivinar.

`trim()` EN LOS TRES SITIOS, Y NINGUNO SOBRA
----------------------------------------------
Aquí, porque un motivo de espacios no es un motivo y quien lo escribió merece
enterarse antes de enviarlo. En `api/evidencias.js`, porque la regla no puede
vivir sólo en un formulario que otro componente podría no usar. En el servidor y
en el CHECK de la tabla, porque el frontend es cortesía.



-->
<script>
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Campo from '../../comun/base/Campo.svelte';

  let {
    abierto = $bindable(false),
    intento = 0,
    enviando = false,
    /** Se llama con el motivo ya recortado. */
    alConfirmar,
    alCancelar
  } = $props();

  let motivo = $state('');
  let error = $state('');

  /**
   * El campo se limpia al abrir, no al cerrar.
   *
   * Al cerrar sería lo intuitivo y sería peor: si el envío falla y el diálogo
   * se cierra, quien escribió tres líneas las pierde. Limpiando al abrir, lo
   * anterior sigue ahí mientras el diálogo siga siendo el mismo, y el siguiente
   * rechazo empieza en blanco —que es lo que hay que garantizar, para que un
   * motivo escrito sobre una evidencia no se envíe sobre otra—.
   */
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
