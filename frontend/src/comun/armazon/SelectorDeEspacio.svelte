<!--
El selector de espacio de trabajo · `EQ-031`

Dos botones segmentados en la cabecera, junto al distintivo de rol: «Tutor» y
el nombre del espacio profesional de quien mira. Cambiar de espacio NO cambia
el rol, no cierra la sesión y no pide volver a autenticarse — lo dice `EQ-031`
y lo cumple `espacio.svelte.js`, que sólo guarda una preferencia de interfaz.

POR QUÉ DOS BOTONES Y NO UN INTERRUPTOR
----------------------------------------
Un interruptor obliga a leer su estado para saber a dónde lleva —«¿encendido
es Tutor o es Profesor?»—, y con dos espacios que se llaman distinto según el
rol eso no se adivina. Dos botones dicen los dos destinos a la vez y el activo
se marca con `aria-pressed`, que es lo que un lector de pantalla anuncia.

NO DEPENDE DEL COLOR, Y ESO ES EL MOTIVO DEL `<span class="marca">`
--------------------------------------------------------------------
El botón activo cambia fondo y color, pero eso solo no basta —§14 del encargo,
y es la misma regla que `rutas.js` ya sigue con `aria-current`—. Lleva además
`aria-pressed` para el lector y un punto visible para quien no distingue el
contraste de fondo. Tres señales, ninguna imprescindible por separado.



-->
<script>
  import { ESPACIO_PROFESIONAL, ESPACIO_TUTOR } from '../../enrutado/espacios.js';

  let {
    /** El espacio activo, ya validado contra el rol por `espacio.svelte.js`. */
    activo,
    /** Cómo se llama el espacio profesional de quien mira: «Profesor» o
        «Investigador». Llega resuelto: este componente no conoce roles. */
    rotuloProfesional,
    /** Cambia de espacio. Quien nos usa decide a dónde navegar. */
    alElegir
  } = $props();

  const OPCIONES = $derived([
    { valor: ESPACIO_TUTOR, rotulo: 'Tutor' },
    { valor: ESPACIO_PROFESIONAL, rotulo: rotuloProfesional }
  ]);
</script>

<div class="selector" role="group" aria-label="Espacio de trabajo">
  {#each OPCIONES as opcion (opcion.valor)}
    <button
      type="button"
      class="opcion"
      class:activa={activo === opcion.valor}
      aria-pressed={activo === opcion.valor}
      onclick={() => alElegir(opcion.valor)}
    >
      <span class="marca" aria-hidden="true"></span>
      <span class="rotulo">{opcion.rotulo}</span>
    </button>
  {/each}
</div>

<style>
  /* Un riel con dos casillas. `inline-flex` y no `grid`: los dos rótulos miden
     distinto —«Tutor» frente a «Investigador»— y repartirlos a partes iguales
     dejaría uno holgado y otro apretado. */
  .selector {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: 2px;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    background: var(--surface-panel);
    box-shadow: var(--shadow-soft);
    flex-shrink: 0;
  }

  /* La tipografía de la marca, la misma que el distintivo de rol de
     `CabeceraGlobal.svelte`: el selector y el distintivo son la misma idea
     —quién soy y dónde estoy trabajando— y se leen como una sola pieza. */
  .opcion {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.28rem 0.6rem;
    border: 1px solid transparent;
    border-radius: calc(var(--radius-sm) - 2px);
    background: transparent;
    color: var(--ink-secondary);
    font-family: var(--fuente-manuscrita);
    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.015em;
    line-height: 1;
    white-space: nowrap;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .opcion:hover { color: var(--ink-primary); background: var(--surface-paper); }

  .opcion:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 1px;
  }

  .opcion.activa {
    background: var(--accent-surface);
    border-color: var(--accent-main);
    color: var(--accent-main);
  }

  /* La tercera señal, la que no depende del color ni del lector: el activo
     lleva punto, el otro no. */
  .marca {
    inline-size: 6px;
    block-size: 6px;
    border-radius: 50%;
    background: currentColor;
    opacity: 0;
    transition: var(--transition-fast);
  }

  .opcion.activa .marca { opacity: 1; }

  /* Teléfono: el área táctil sube a 44px de alto —§14— sin que el riel crezca
     de más. El punto se retira: a este ancho compite con el rótulo, y las otras
     dos señales (fondo y `aria-pressed`) siguen ahí. */
  @media (max-width: 48rem) {
    .opcion {
      min-block-size: 44px;
      padding-inline: 0.7rem;
      font-size: 16px;
    }

    .marca { display: none; }
    .rotulo { min-inline-size: 0; overflow: hidden; text-overflow: ellipsis; }
  }

  @media (prefers-reduced-motion: reduce) {
    .opcion, .marca { transition: none; }
  }
</style>
