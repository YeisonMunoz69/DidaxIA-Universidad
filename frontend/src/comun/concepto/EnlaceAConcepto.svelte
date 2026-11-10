<!--
DD-13 · El nombre de un concepto, pulsable.

SI EL CLIENTE NO CONOCE EL IDENTIFICADOR, MUESTRA EL NOMBRE SIN ENLACE en
lugar de ocultarlo. Que el banco vaya por detrás del generador es información
útil, no un fallo que tapar: si un concepto se cita y no existe en el banco,
alguien debería enterarse.

No decide qué concepto es relevante. El servidor manda los que invocó.

CÓMO SE SABE SI SE CONOCE. Por si trae `id`, y por nada más. El contrato §6.bis
manda `id` y `nombre`; un concepto sin `id` es uno que el generador citó y el
banco no tiene. Comprobarlo contra una lista local de identificadores sería
mantener aquí una copia del banco, y `DD-13` puso el banco en `contenido/` para
que no hubiera copias.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
Origen de esta pieza: OE3-Implementacion/09-Aportes-de-la-Consulta-Docente.md

-->
<script>
  let {
    /** { id, nombre } — contrato §6.bis */
    concepto,
    /** Se invoca con el identificador cuando el concepto se puede abrir. */
    alAbrir = null
  } = $props();

  const conocido = $derived(Boolean(concepto?.id));
</script>

{#if conocido && typeof alAbrir === 'function'}
  <button type="button" class="enlace" onclick={() => alAbrir(concepto.id)}>
    {concepto.nombre}
  </button>
{:else}
  <span class="suelto">
    {concepto?.nombre ?? 'concepto sin nombre'}
    {#if !conocido}
      <span class="nota">(todavía no está en el banco)</span>
    {/if}
  </span>
{/if}

<style>
  .enlace {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 8px 12px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    color: var(--ink-primary);
    font: inherit;
    font-size: 13px;
    font-weight: 500;
    text-align: start;
    text-decoration: none;
    cursor: pointer;
    box-shadow: var(--shadow-soft);
    transition: var(--transition);
  }

  .enlace:hover {
    background: var(--accent-surface);
    color: var(--accent-main);
    border-color: var(--accent-main);
    transform: translateY(-1px);
    box-shadow: 0 3px 8px var(--accent-glow);
  }

  .suelto {
    display: flex;
    flex-direction: column;
    padding: 8px 12px;
    background: var(--surface-paper);
    border: 1px dashed var(--ink-ghost);
    border-radius: var(--radius-sm);
    color: var(--ink-secondary);
    font-size: 13px;
  }

  /* No se oculta: que el banco vaya por detrás es información, no un fallo. */
  .nota { font-size: 11px; color: var(--ink-tertiary); margin-top: 2px; }
</style>
