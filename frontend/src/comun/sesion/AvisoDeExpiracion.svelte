<!--
«Tu sesión termina pronto» · `EQ-020`: siete días, y se avisa antes.

⚠️ ESTO NO RENUEVA NADA, Y ES LA MITAD DEL PUNTO
--------------------------------------------------
`POST /api/sesion/renovar` **informa** el tiempo restante; no lo extiende. Los
siete días se cuentan desde que la sesión se abrió, y renovarlos al consultarlos
convertiría el plazo en «siete días sin cerrar la pestaña». Este aviso consulta
y avisa; volver a entrar es una acción de la persona, no un efecto de mirar.

Tampoco lo renueva empezar una conversación: `POST /api/sesion/reiniciar` cambia
sólo el identificador de conversación y conserva `creada_en`. Cuando no era así,
quien empezaba una conversación cada seis días conservaba la sesión para siempre.

EL PLAZO LO CUENTA EL SERVIDOR
--------------------------------
Se publican los **segundos que faltan** y no el instante de vencimiento, porque
un plazo relativo no depende del reloj del navegador: uno adelantado avisaría
tarde y uno atrasado no avisaría nunca. Aquí sólo se convierte a horas o días
para redactarlo.



-->
<script>
  import Icono from '../base/Icono.svelte';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';

  /**
   * Cuándo empieza a avisarse: un día antes.
   *
   * Con siete días de sesión, avisar antes sería ruido permanente y avisar en
   * la última hora dejaría a alguien a mitad de un ejercicio.
   */
  const UMBRAL_SEGUNDOS = 24 * 60 * 60;

  /** Cada cuánto se vuelve a preguntar mientras el aviso está a la vista. */
  const CADA_MS = 15 * 60 * 1000;

  let descartado = $state(false);

  const restante = $derived(sesion.expiraEnSegundos);

  const cerca = $derived(
    sesion.autenticada && restante > 0 && restante <= UMBRAL_SEGUNDOS && !descartado
  );

  /** El plazo en palabras. Redondea hacia abajo: no promete de más. */
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
    // Se consulta al montar y luego de vez en cuando: el estado compartido sólo
    // se actualiza cuando algo pregunta, y una pestaña abierta toda la tarde no
    // vería acercarse el vencimiento.
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
