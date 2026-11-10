<!--
El aviso de «esto es un hueco declarado, no un error» · extraído el 2026-08-22.

Hasta esta fecha el mismo bloque —borde entero en `--semantic-warning`,
`<strong>` + párrafo, `<code>` para nombrar el archivo— vivía pegado, byte a
byte, en `VistaDelGrupo.svelte`, `FichaDeEstudiante.svelte` y
`ColaDeSupervision.svelte`: las tres pantallas que declaran una decisión de
producto sin tomar en vez de fingir que la pantalla ya está completa. Las
tres se escribieron en la misma sesión, así que la duplicación no venía de
tres decisiones independientes — era una sola idea copiada tres veces.

MISMO LENGUAJE VISUAL QUE `Degradacion.svelte`, SIN IMPORTARLO. Los dos usan
un borde completo (no `border-inline-start`) en un color semántico. No se
reutiliza `Degradacion.svelte` porque sus props están pensadas para un fallo
de red reintentable (`{situacion, explicacion}`), y esto es una nota
PERMANENTE sobre el propio backend — no hay nada que reintentar.

`titulo` es el `<strong>` de arriba; el contenido por defecto (`children`) es
el párrafo de abajo, y admite marcado —`<code>`, `<strong>`— porque cada
pantalla nombra un archivo o una decisión distinta ahí dentro.



-->
<script>
  let {
    /** El `<strong>` de la primera línea. */
    titulo,
    /** El párrafo de abajo — puede traer `<code>`/`<strong>`. */
    children
  } = $props();
</script>

<div class="aviso-pendiente" role="note">
  <strong>{titulo}</strong>
  <p>{@render children?.()}</p>
</div>

<style>
  .aviso-pendiente {
    padding: var(--espacio-md) var(--espacio-lg);
    background: var(--semantic-warning-bg);
    border: 1px solid var(--semantic-warning);
    border-radius: var(--radius-md);
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
  }

  .aviso-pendiente strong { display: block; color: var(--ink-primary); margin-block-end: 0.25rem; }

  /* `max-inline-size: none`: ver el comentario de `MisClases.svelte::
     .frontera` sobre por qué hace falta declararlo explícito —sin esto,
     `estilos/tipografia.css` sigue capando cualquier `<p>` a 62ch—. */
  .aviso-pendiente p { margin: 0; max-inline-size: none; line-height: 1.5; }

  /* `:global()`: el `<code>` llega dentro de `children`, un snippet escrito
     en el archivo que USA este componente —`VistaDelGrupo.svelte`,
     `FichaDeEstudiante.svelte`—, así que Svelte lo marca con el hash de
     scope de ESE archivo, no el de este. Sin `:global()` la regla nunca
     coincide con nada —confirmado por `svelte-check`: «Unused CSS
     selector»— aunque el `<code>` se vea perfectamente en pantalla gracias
     a la cascada normal; es solo que esta regla concreta no era la que lo
     pintaba. */
  .aviso-pendiente :global(code) {
    font-family: var(--fuente-mono);
    font-size: 0.92em;
    background: var(--surface-paper);
    padding: 0.1em 0.35em;
    border-radius: var(--radius-xs);
  }
</style>
