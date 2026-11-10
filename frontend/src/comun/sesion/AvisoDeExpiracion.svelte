
<script>
  import Icono from '../base/Icono.svelte';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';

  const UMBRAL_SEGUNDOS = 24 * 60 * 60;

  const CADA_MS = 15 * 60 * 1000;

  let descartado = $state(false);

  const restante = $derived(sesion.expiraEnSegundos);

  const cerca = $derived(
    sesion.autenticada && restante > 0 && restante <= UMBRAL_SEGUNDOS && !descartado
  );

  const enPalabras = $derived.by(() => {
    if (restante <= 0) return '';
    const horas = Math.floor(restante / 3600);
    if (horas >= 2) return `en unas ${horas} horas`;
    const minutos = Math.floor(restante / 60);
    if (minutos >= 2) return `en unos ${minutos} minutos`;
    return 'en menos de dos minutos';
  });

  $effect(() => {
    if (!sesion.autenticada) return;
    sesion.consultarVencimiento();
    const reloj = setInterval(() => sesion.consultarVencimiento(), CADA_MS);
    return () => clearInterval(reloj);
  });
</script>

{#if cerca}
  <div class="aviso" role="status">
    <span class="icono"><Icono nombre="candado" medida={14} /></span>
    <p>
      Tu sesión termina <strong>{enPalabras}</strong>. Cuando termine, tendrás
      que volver a entrar con tu cuenta institucional; no se pierde nada de lo
      que hayas guardado.
    </p>
    <button
      type="button"
      class="descartar"
      onclick={() => (descartado = true)}
      aria-label="Ocultar el aviso de fin de sesión"
    >
      <Icono nombre="cerrar" medida={14} />
    </button>
  </div>
{/if}

<style>
  .aviso {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 10px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-inline-start: 3px solid var(--accent-main);
    border-radius: var(--radius-xs);
  }

  .icono { color: var(--accent-main); margin-block-start: 2px; flex-shrink: 0; }

  p {
    margin: 0;
    flex: 1;
    min-inline-size: 0;
    font-size: var(--texto-xs);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  .descartar {
    display: flex;
    align-items: center;
    justify-content: center;
    inline-size: 24px;
    block-size: 24px;
    padding: 0;
    flex-shrink: 0;
    color: var(--ink-tertiary);
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--radius-xs);
    cursor: pointer;
  }

  .descartar:hover { color: var(--ink-primary); border-color: var(--trazo-suave); }
</style>
