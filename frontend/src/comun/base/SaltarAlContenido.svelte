<!--
Enlace de salto para teclado. Visible al recibir foco.

Sin él, quien navega por teclado tiene que tabular por toda la navegación en
CADA pantalla antes de llegar al contenido. En la conversación, que es la ruta
donde el estudiante pasa el tiempo, eso son decenas de pulsaciones por turno.

Va como PRIMER elemento del documento, antes que nada. Si va después, no
cumple su función.

No se oculta con `display: none`: eso lo retiraría del orden de tabulación y
dejaría de existir. Se desplaza fuera de la pantalla y vuelve al recibir foco.



-->
<script>
  let { destino = '#contenido', texto = 'Saltar al contenido' } = $props();
</script>

<a class="saltar" href={destino}>{texto}</a>

<style>
  .saltar {
    position: absolute;
    inset-block-start: 0;
    inset-inline-start: 0;
    z-index: 100;
    padding: 0.6em 1em;
    background: var(--surface-paper);
    color: var(--ink-primary);
    border-radius: 0 0 var(--radius-sm) 0;
    box-shadow: var(--shadow-soft);
    transform: translateY(-120%);
    transition: var(--transition-fast);
  }

  .saltar:focus-visible { transform: none; }
</style>
