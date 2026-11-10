<!--
La tarjeta de «aquí no hay nada que mostrar todavía» · extraída el 2026-08-22.

Tres pantallas de docente —`MisClases.svelte` (tres veces: sin clases, sin
selección, y de nuevo sin clases desde el panel angosto), `ColaDeSupervision.
svelte` («nada pendiente con estos filtros») y `FichaDeEstudiante.svelte`
(«ningún estudiante seleccionado»)— pintaban la misma idea —icono en un
círculo, texto centrado, tarjeta con borde punteado— con CSS casi idéntico y
pequeñas divergencias de color que nadie había decidido a propósito, solo
heredado copia a copia.

TRES TONOS, PORQUE NO SON EL MISMO MENSAJE
---------------------------------------------
`tono="invitacion"` es el rediseño que se pidió el 2026-08-22 para
`MisClases.svelte`: acento, icono grande con un rebote al entrar, título en
negrita — para «te falta elegir o crear algo». `tono="exito"` es el icono
verde de `ColaDeSupervision.svelte`: no invita a nada, dice que no queda
trabajo pendiente, un estado POSITIVO. `tono="neutro"` es el que ya tenía
`FichaDeEstudiante.svelte`: gris, sin implicar ni una cosa ni la otra —«nada
seleccionado todavía» no es ni un logro ni una invitación—.

`exito`/`neutro` SON BYTE A BYTE EL CSS QUE YA TENÍAN, no un rediseño
disfrazado de refactor: mismo tamaño de círculo (56px), mismo borde punteado
neutro, mismo texto `--texto-sm`/`--ink-tertiary`. Solo cambió el nombre del
selector. `invitacion` es la única que trae el aspecto nuevo, porque es la
única a la que se le pidió.

`titulo` es opcional a propósito: `ColaDeSupervision.svelte`/
`FichaDeEstudiante.svelte` nunca tuvieron un título de dos partes, solo
icono + una línea de texto — inventarles uno ahora sería una decisión de
contenido que nadie pidió, no una limpieza de CSS.



-->
<script>
  import Icono from '../../comun/base/Icono.svelte';

  let {
    /** Nombre del icono central (`Icono.svelte`). */
    icono,
    /** Opcional — sin esto, la tarjeta es solo icono + texto. */
    titulo = '',
    /** El texto principal. */
    texto,
    /** 'invitacion' (acento, «faltа elegir/crear algo») · 'exito' (verde,
        «nada pendiente, todo bien») · 'neutro' (gris, no implica nada). */
    tono = 'neutro',
    /** `invitacion` ya usaba 22 sobre un círculo de 64px; `exito`/`neutro`
        ya usaban 28 sobre uno de 56px —proporciones distintas que cada
        pantalla eligió por su cuenta—. Prop, no una talla fija, para no
        aplanar esa diferencia al extraer el componente. */
    medidaIcono = tono === 'invitacion' ? 22 : 28
  } = $props();
</script>

<div class="tarjeta-vacia {tono}">
  <div class="circulo-icono-vacio">
    <Icono nombre={icono} medida={medidaIcono} />
  </div>
  {#if titulo}<h3>{titulo}</h3>{/if}
  <p>{texto}</p>
</div>

<style>
  .tarjeta-vacia {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: var(--espacio-sm);
    padding: var(--espacio-xl) var(--espacio-lg);
    border-radius: var(--radius-md);
  }

  .tarjeta-vacia.exito,
  .tarjeta-vacia.neutro {
    background: var(--surface-panel);
    border: 1px dashed var(--trazo);
  }

  .tarjeta-vacia.invitacion {
    gap: 10px;
    max-inline-size: 26rem;
    border-radius: var(--radius-lg);
    border: 1.5px dashed var(--accent-main);
    background: var(--accent-surface);
  }

  .circulo-icono-vacio {
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .exito .circulo-icono-vacio,
  .neutro .circulo-icono-vacio {
    inline-size: 56px;
    block-size: 56px;
  }

  .exito .circulo-icono-vacio {
    background: var(--semantic-success-bg);
    color: var(--semantic-success);
  }

  .neutro .circulo-icono-vacio {
    background: var(--surface-paper);
    color: var(--ink-tertiary);
    border: 1px solid var(--trazo-suave);
  }

  .invitacion .circulo-icono-vacio {
    inline-size: 64px;
    block-size: 64px;
    margin-block-end: 4px;
    background: var(--surface-paper);
    border: 1.5px solid var(--accent-main);
    color: var(--accent-main);
    /* Rebote sutil al entrar, para que el ojo aterrice en el icono
       primero — solo en `invitacion`: es la única que quiere llamar la
       atención, `exito`/`neutro` son informativas, no invitaciones. */
    animation: popIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  @keyframes popIn {
    from { transform: scale(0.88); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }

  .invitacion h3 { margin: 0; font-size: var(--texto-lg); font-weight: 700; color: var(--accent-main); }

  .tarjeta-vacia p { margin: 0; font-size: var(--texto-sm); color: var(--ink-tertiary); line-height: 1.4; }

  .invitacion p { color: var(--ink-secondary); }
</style>
