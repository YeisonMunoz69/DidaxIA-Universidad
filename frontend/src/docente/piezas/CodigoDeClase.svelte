<!--
DD-12 · El código, para compartirlo.

Muestra el código de la clase y permite regenerarlo.

REGENERAR NO EXPULSA A QUIEN YA ENTRO. Invalida el código, no la matrícula. Es
la distinción que evita que un docente vacíe su clase sin querer al rotar el
código porque se filtró.

Y ESO SE DICE EN PANTALLA, NO SOLO AQUÍ. Un docente que duda de si va a echar a
sus treinta estudiantes no rota el código, y entonces el código filtrado sigue
circulando. La confirmación explica la consecuencia real antes de pedirla.

EL CÓDIGO NO ES UNA CREDENCIAL, y por eso se muestra a la vista y se puede
copiar. Identifica una agrupación; no autentica a nadie. Tratarlo como secreto
daría a entender lo contrario.

Presentación compacta, desde el 2026-08-22
-------------------------------------------
Único consumidor: `docente/rutas/MisClases.svelte`. Antes era una tarjeta
grande y siempre visible con el código a `texto-xl`/700; ahora vive junto al
nombre de la clase en la cabecera del panel de detalle, y el usuario pidió
explícitamente que fuera «sutil» — se restiliza como una fila compacta en
vez de un bloque que compite por la atención. La lógica —copiar,
confirmar antes de regenerar— no cambia; solo el tamaño y la disposición.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
Origen de esta pieza: OE3-Implementacion/09-Aportes-de-la-Consulta-Docente.md

-->
<script>
  import Boton from '../../comun/base/Boton.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';

  let {
    codigo = '',
    /** Se invoca al confirmar. Quien nos usa hace la petición. */
    alRegenerar = null
  } = $props();

  let confirmando = $state(false);
  let copiado = $state(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(codigo);
      copiado = true;
      setTimeout(() => (copiado = false), 2000);
    } catch {
      // Sin permiso de portapapeles el código sigue a la vista y se puede
      // seleccionar a mano. No se avisa de un fallo que no impide nada.
    }
  }
</script>

<div class="codigo">
  <span class="rotulo" id="rotulo-codigo">
    <Icono nombre="clase" medida={12} />
    <span>Código de la clase</span>
  </span>
  <output class="valor" aria-labelledby="rotulo-codigo">{codigo || '—'}</output>

  <div class="acciones">
    <!-- `<span>` envolvente y no `class` en `<Boton>`: mismo motivo que
         `MisClases.svelte::.disparador-crear` —comprobado que Svelte
         reemplaza el `class` del componente por completo en vez de
         sumarlo—. `--semantic-success`/`-bg` ya cambian de valor entre
         tema claro y oscuro en `tokens.css`, así que no hace falta un
         color aparte para cada uno. -->
    <span class="boton-copiar" class:copiado>
      <Boton variante="secundario" onclick={copiar} deshabilitado={!codigo}>
        <Icono nombre={copiado ? 'check' : 'copiar'} medida={13} />
        <span>{copiado ? 'Copiado' : 'Copiar'}</span>
      </Boton>
    </span>
    <Boton variante="discreto" onclick={() => (confirmando = true)}
           deshabilitado={!alRegenerar}>
      Regenerar
    </Boton>
  </div>

  <Dialogo bind:abierto={confirmando} titulo="¿Regenerar el código de la clase?" tipo="confirmar">
      <p>
        <strong>El código actual dejará de servir.</strong>
        Quien ya está en la clase <strong>sigue dentro</strong>: se invalida el
        código, no la matrícula. Solo tendrás que repartir el nuevo.
      </p>
      <div class="acciones">
        <Boton variante="secundario" onclick={() => (confirmando = false)}>
          Dejarlo como está
        </Boton>
        <Boton onclick={() => { alRegenerar?.(); confirmando = false; }}>
          Regenerar el código
        </Boton>
      </div>
  </Dialogo>
</div>

<style>
  /* Fila compacta, no tarjeta: comparte la cabecera del panel de detalle
     con el nombre de la clase, y no debe competir con él por la atención.
     `flex-wrap` es la salida cuando el nombre de la clase es largo y no
     queda sitio junto al código en una pantalla angosta. */
  .codigo {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.7rem;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
  }

  .rotulo {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: var(--texto-xs);
    font-weight: 600;
    color: var(--ink-tertiary);
  }

  .valor {
    font-family: var(--fuente-mono);
    font-size: var(--texto-sm);
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--accent-main);
  }

  .acciones { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-inline-start: auto; }

  /* `display: contents`: el `<span>` no debe alterar el `flex` de
     `.acciones` —mismo motivo que `MisClases.svelte::.disparador-crear`,
     ver su comentario—. El botón «Copiar» se pone verde mientras dice
     «Copiado», la misma confirmación visual que
     `MisClases.svelte::.confirmacion-creada` ya usa —dos segundos,
     controlados por `copiado` en el `<script>`—. */
  .boton-copiar { display: contents; }

  .boton-copiar.copiado :global(.boton) {
    background: var(--semantic-success-bg);
    border-color: var(--semantic-success);
    color: var(--semantic-success);
  }

</style>
