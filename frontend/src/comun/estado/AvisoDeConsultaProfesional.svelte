<!--
La señal de que este uso del Tutor no evalúa a nadie · `EQ-031` · §6.5

Un renglón discreto, no una alerta. Aparece **una vez por pantalla** y no por
mensaje: repetirlo en cada turno lo convertiría en ruido que se deja de leer,
que es justo lo contrario de lo que una advertencia de datos necesita.

QUÉ DICE, Y POR QUÉ DICE TAMBIÉN LA SEGUNDA MITAD
--------------------------------------------------
La primera mitad es la garantía de `EQ-031`: estos turnos quedan fuera de
evaluación, diagnóstico, alertas y KPI. La segunda dice que **sí se guardan**,
en el historial personal de quien pregunta.

Decirlo entero no es un exceso de honestidad: el encargo lo pide con todas las
letras —*«no prometas anonimato si el historial sí se almacena asociado a la
identidad»*— y `EQ-031` conserva esas conversaciones a propósito, para que un
profesional pueda retomarlas. Callar la segunda mitad dejaría entender que no
queda rastro, y queda.

`role="note"` y no `role="alert"`: no hay nada que atender ni que se acabe de
producir. Un `alert` interrumpiría al lector de pantalla en cada montaje de la
pantalla para decir algo que no es una novedad.


-->
<script>
  import Icono from '../base/Icono.svelte';
  import BotonAyudaTooltip from '../base/BotonAyudaTooltip.svelte';
</script>

<p class="aviso-profesional" role="note">
  <Icono nombre="escudo" medida={14} />
  <span class="aviso-completo">
    <strong>Consulta profesional.</strong>
    No genera evaluación, diagnóstico, alertas ni indicadores de estudiante.
    Se guarda en tu historial personal.
  </span>
  <span class="aviso-compacto"><strong>Consulta profesional</strong> · historial personal</span>
  <span class="ayuda-aviso"><BotonAyudaTooltip tamano="sm" posicion="abajo" texto="Esta consulta profesional no genera evaluación, diagnóstico, alertas ni indicadores de estudiante. La conversación sí se guarda en tu historial personal." ariaLabel="Alcance de la consulta profesional" /></span>
</p>

<style>
  /* Discreto por construcción: color secundario, sin fondo de aviso y sin
     borde de color. Lo que lo distingue del cuerpo es el icono y la negrita
     inicial, no un bloque que reclame la pantalla. */
  .aviso-profesional {
    /* `.trabajo` es una columna y el contenido de la ruta crece: sin esto, un
       hilo largo aplastaría el renglón hasta hacerlo ilegible. */
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin: 0;
    padding: 0.4rem 0.9rem;
    max-inline-size: none;
    border-block-end: 1px solid var(--ink-ghost);
    background: var(--surface-panel);
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
    line-height: 1.4;
  }

  .aviso-profesional strong { color: var(--ink-secondary); font-weight: 600; }

  .aviso-profesional :global(svg) { color: var(--accent-main); flex-shrink: 0; }
  .aviso-compacto, .ayuda-aviso { display: none; }
  @media (min-width: 48.0625rem) {
    .aviso-completo { display: none; }
    .aviso-compacto, .ayuda-aviso { display: inline-flex; align-items: center; }
  }

  /* En teléfono el renglón se convierte en dos y no se recorta: el texto
     completo es el que da la garantía, así que no hay una versión corta. */
  @media (max-width: 48rem) {
    .aviso-profesional { padding-inline: 0.75rem; align-items: flex-start; }
    .aviso-profesional :global(svg) { margin-block-start: 2px; }
  }
</style>
