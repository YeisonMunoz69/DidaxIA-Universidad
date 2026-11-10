<!--
El sello, POR BLOQUE y no por turno.

`RP-01` exige indicar el estado de verificación «en cada paso o resultado, no en
la respuesta completa». Un turno con cinco bloques puede tener tres verificados
simbólicamente y dos que son explicación generada, y el estudiante tiene que
poder distinguirlos.

DOS VALORES Y NO ADMITE UN TERCERO. La tentación de añadir «verificado
parcialmente» o un porcentaje de confianza hay que resistirla: `RP-18` dice que
ante la imposibilidad de verificar, el estado seguro es NO AFIRMAR, y no
«afirmar con reserva». Un porcentaje junto a un resultado es literalmente
afirmar con reserva. Si el sistema no pudo verificar, no emite el resultado.

No se distingue solo por color: cada estado lleva SIGNO y TEXTO. Un sello que
solo cambiara de color no comunicaría nada a quien no percibe ese contraste, y
esto es justo la información que más importa de la respuesta.



-->
<script>
  let {
    /** 'verificado' | 'generado' — los dos únicos valores del contrato. */
    estado
  } = $props();

  const ROTULO = {
    verificado: { signo: '✓', texto: 'Verificado simbólicamente' },
    generado:   { signo: '◇', texto: 'Explicación generada'      }
  };

  const sello = $derived(ROTULO[estado] ?? null);
</script>

{#if sello}
  <span class="sello {estado}">
    <span class="signo" aria-hidden="true">{sello.signo}</span>
    {sello.texto}
  </span>
{:else}
  <!-- Un estado fuera del contrato NO se pinta como si fuera válido: se
       declara. Callarlo dejaría un bloque sin sello, que es justo lo que
       `bloque-sin-sello.prueba.js` existe para impedir. -->
  <span class="sello desconocido">
    <span class="signo" aria-hidden="true">!</span>
    Estado de verificación no reconocido
  </span>
{/if}

<style>
  /* La forma de «insignia», del mockup —`PM-F2x` fase 3—: radio de píldora
     para los tres estados, y solo `verificado` lleva borde y entra con un
     gesto propio. El mockup anima esto por MENSAJE completo
     (`.msg-success`/`flashSuccess`, sobre toda la burbuja); aquí no: `RP-01`
     exige el estado «en cada paso, no en la respuesta completa», y una
     burbuja puede traer un paso verificado junto a otro que no lo es —lo
     comprueba `bloque-sin-sello.prueba.js`—. El destello va en el propio
     sello, que es la unidad correcta, no en la burbuja entera. */
  .sello {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 0.25em 0.7em;
    border-radius: var(--radius-xl);
    font-size: var(--texto-xs);
    font-weight: 600;
    line-height: 1.4;
  }

  .signo { font-weight: 700; }

  .verificado {
    color: var(--semantic-success);
    background: var(--semantic-success-bg);
    border: 1px solid var(--semantic-success);
    animation: destelloSello 1s cubic-bezier(0.22, 1, 0.36, 1) both;
  }

  /* El signo «se dibuja» con un pequeño rebote, como el check animado del
     mockup —sin depender de la longitud de un trazo SVG que aquí no
     existe: el signo es texto, no un icono, por la misma razón por la que
     `Icono.svelte` es decorativo y nunca el único portador del estado. */
  .verificado .signo {
    display: inline-block;
    animation: aparecerSigno 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) 0.15s both;
  }

  @keyframes destelloSello {
    from { box-shadow: 0 0 0 0 var(--color-emerald-glow); }
    50%  { box-shadow: 0 0 0 6px transparent; }
    to   { box-shadow: 0 0 0 0 transparent; }
  }

  @keyframes aparecerSigno {
    from { transform: scale(0.4); opacity: 0; }
    to   { transform: scale(1); opacity: 1; }
  }

  .generado    { color: var(--ink-secondary); background: var(--surface-panel); }
  .desconocido { color: var(--semantic-error); background: var(--semantic-error-bg); }
</style>
