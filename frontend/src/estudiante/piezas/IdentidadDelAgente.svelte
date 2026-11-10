<!--
La declaración de sistema automatizado.

En el primer mensaje y en la identidad visible. RP-20 y RP-17.

POR QUÉ EL TEXTO VIVE AQUÍ Y NO VIAJA EN EL TURNO
--------------------------------------------------
`08-Contrato-del-Turno.md` §10: si viajara, un turno cualquiera podría
alterarlo. La declaración de que esto es un sistema automatizado es
precisamente lo que no puede depender de lo que el sistema genere.

LA REDACCIÓN NO ES LIBRE. `RP-20` es inusualmente específico: el aviso emplea
formulaciones del tipo «indicios» y nunca del tipo «tienes ansiedad
matemática». Aquí no se nombra ningún estado del estudiante, y ésa es la línea
que no se cruza al reescribirlo.

NO DICE «HOLA, SOY TU TUTOR». Presentarse como una persona es lo contrario de
declararse automatizado, y el mockup previo lo hacía. Dice qué es y qué no
puede hacer, que es lo que permite calibrar cuánto confiar.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

-->
<script>
  let {
    /** `completa` en el primer mensaje; `breve` en la cabecera. */
    forma = 'completa'
  } = $props();
</script>

{#if forma !== 'breve'}
  <section class="identidad">
    <h2>Asistente automatizado de cálculo diferencial</h2>
    <p>
      Esto no es una persona. Es un sistema que resuelve y explica derivadas
      con el material de tu curso, y que <strong>marca cada paso</strong> según
      lo haya comprobado con un motor matemático o lo haya redactado.
    </p>
    <p>
      Cuando no tiene material del curso que respalde algo, lo dice en vez de
      inventarlo. Si algo se sale del cálculo diferencial, te lo explica en
      lugar de intentar responderlo.
    </p>
  </section>
{/if}

<style>
  .identidad {
    padding: 12px 18px;
    background: var(--surface-panel);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
    margin-block-end: 0.5rem;
    max-inline-size: 100%;
  }

  h2 {
    margin: 0 0 0.35rem;
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-primary);
  }

  p {
    margin: 0 0 0.3rem;
    font-size: 12px;
    line-height: 1.45;
    color: var(--ink-secondary);
    max-inline-size: 100%;
  }

  p:last-child { margin-block-end: 0; }

  @media (max-width: 75rem) {
    .identidad {
      padding: 10px 14px;
    }
  }
</style>
