<!--
Qué has autorizado, y cómo retirarlo · `EQ-016` / `EQ-022`.

Es el «lugar comprensible» desde el que se revoca: al lado de lo que el sistema
guarda sobre uno, no escondido dentro del trámite de onboarding, que es una
pantalla por la que sólo se pasa al principio.

⚠️ REVOCAR NO BORRA, Y ESO SE DICE EN EL DIÁLOGO
--------------------------------------------------
`EQ-022`: *«revocar bloquea inmediatamente el tutor y todo tratamiento opcional
futuro, sin eliminar automáticamente el historial»*. Confundir las dos cosas es
el error caro de esta pantalla: quien quiere que se borren sus datos y sólo
revoca se queda creyendo que lo consiguió. Por eso el diálogo dice qué hace y
qué no, y señala el trámite de eliminación como lo que sí borra.

EL CLIENTE NO ELIGE QUÉ VERSIÓN REVOCA
----------------------------------------
`POST .../revocar` no recibe nada: ni versión, ni decisión, ni comprobante. El
servidor resuelve la concesión efectivamente otorgada —aunque su documento haya
vencido o haya sido desplazado— y el repositorio la vuelve a exigir dentro de la
transacción. Son dos rutas independientes porque `EQ-016` declara las tres
dimensiones separadas: un menor puede retirar su asentimiento sin tocar el
consentimiento del titular.



-->
<script>
  import Boton from '../../../comun/base/Boton.svelte';
  import Icono from '../../../comun/base/Icono.svelte';
  import Dialogo from '../../../comun/base/Dialogo.svelte';
  import ReciboDelActo from '../recorrido/ReciboDelActo.svelte';
  import * as consentimiento from '../../../nucleo/api/consentimiento.js';
  import { describir, clasificar } from '../../../nucleo/errores/degradacion.js';
  import { navegar } from '../../../enrutado/navegar.js';

  let {
    /** El estado vigente completo de `GET /api/onboarding/estado`. */
    estado,
    /** Se llama tras una revocación, para que la pantalla recargue todo. */
    alCambiar
  } = $props();

  /** Cómo se lee cada estado de acceso, para el resumen de arriba. */
  const ACCESO = {
    habilitado: { texto: 'Puedes usar el tutor', tono: 'listo' },
    onboarding_pendiente: { texto: 'Falta completar tu registro', tono: 'espera' },
    esperando_representante: { texto: 'Falta la autorización de tu representante', tono: 'espera' },
    bloqueado_por_rechazo: { texto: 'El tutor está bloqueado porque no autorizaste', tono: 'bloqueo' },
    bloqueado_por_revocacion: { texto: 'El tutor está bloqueado porque retiraste tu autorización', tono: 'bloqueo' },
    eliminacion_solicitada: { texto: 'Tienes una solicitud de eliminación en curso', tono: 'bloqueo' },
    mantenimiento: { texto: 'No se puede comprobar tu estado ahora mismo', tono: 'espera' }
  };

  const resumen = $derived(
    ACCESO[estado?.acceso] ?? { texto: 'Estado no disponible', tono: 'espera' }
  );

  const esMenor = $derived(
    typeof estado?.perfil?.edad === 'number' && estado.perfil.edad < 18
  );

  /** Se puede revocar lo que está efectivamente otorgado. Nada más. */
  const puedeRevocarTitular = $derived(estado?.consentimiento?.estado === 'otorgado');
  const puedeRevocarAsentimiento = $derived(
    esMenor && estado?.asentimiento?.estado === 'otorgado'
  );

  /** `''`, `titular` o `asentimiento`: qué confirmación está abierta. */
  let revocando = $state('');
  let enviando = $state(false);
  let motivo = $state('');
  let recibo = $state(null);

  const TEXTOS = {
    titular: {
      titulo: '¿Retirar tu autorización?',
      consecuencia:
        'El tutor quedará bloqueado en cuanto se registre, y no se iniciará ningún tratamiento nuevo.',
      boton: 'Sí, retirar mi autorización'
    },
    asentimiento: {
      titulo: '¿Retirar tu acuerdo?',
      consecuencia:
        'El tutor quedará bloqueado aunque tu representante siga autorizando, porque las tres autorizaciones son independientes.',
      boton: 'Sí, retirar mi acuerdo'
    }
  };

  async function confirmar() {
    // Dos pulsaciones seguidas serían dos eventos de revocación; el segundo
    // recibiría un 409 —ya no hay concesión que retirar— pero el botón no debe
    // permitir llegar ahí.
    if (enviando || !revocando) return;
    const cual = revocando;
    enviando = true;
    motivo = '';
    try {
      const respuesta =
        cual === 'titular'
          ? await consentimiento.revocarTitular()
          : await consentimiento.revocarAsentimiento();
      recibo = respuesta?.recibo ?? null;
      revocando = '';
      alCambiar?.(respuesta);
    } catch (e) {
      const clase = clasificar(e);
      if (clase === 'conflicto' && e?.estadoDelServidor === 'sin_concesion') {
        motivo = 'No hay ninguna autorización otorgada que retirar. Vuelve a cargar la página para ver cómo quedó.';
      } else {
        motivo = e?.detalle || describir(e).titulo;
      }
      revocando = '';
    } finally {
      enviando = false;
    }
  }
</script>

<section class="autorizaciones" aria-labelledby="titulo-autorizaciones">
  <div class="cabecera">
    <Icono nombre="escudo" medida={16} />
    <h2 id="titulo-autorizaciones">Tus autorizaciones</h2>
  </div>

  <p class="resumen {resumen.tono}">{resumen.texto}</p>

  <dl class="dimensiones">
    <div class="dimension">
      <dt>Tratamiento de tus datos</dt>
      <dd>
        {estado?.consentimiento?.estado ?? 'sin dato'}
        {#if estado?.consentimiento?.version}
          <span class="version">· versión {estado.consentimiento.version}</span>
        {/if}
        {#if estado?.consentimiento?.al_dia === false && estado?.consentimiento?.estado === 'otorgado'}
          <span class="nota">Hay una versión nueva que aceptar.</span>
        {/if}
      </dd>
    </div>

    {#if esMenor}
      <div class="dimension">
        <dt>Tu propio acuerdo</dt>
        <dd>
          {estado?.asentimiento?.estado ?? 'sin dato'}
          {#if estado?.asentimiento?.version}
            <span class="version">· versión {estado.asentimiento.version}</span>
          {/if}
        </dd>
      </div>

      <div class="dimension">
        <dt>Autorización de tu representante</dt>
        <dd>{estado?.representante?.estado ?? 'sin dato'}</dd>
      </div>
    {/if}
  </dl>

  {#if motivo}
    <p class="aviso" role="alert">{motivo}</p>
  {/if}

  {#if recibo}
    <ReciboDelActo {recibo} titulo="Tu decisión quedó registrada" />
  {/if}

  <div class="acciones">
    {#if puedeRevocarTitular}
      <Boton variante="secundario" onclick={() => (revocando = 'titular')} deshabilitado={enviando}>
        <Icono nombre="cerrar" medida={15} />
        Retirar mi autorización
      </Boton>
    {/if}
    {#if puedeRevocarAsentimiento}
      <Boton variante="secundario" onclick={() => (revocando = 'asentimiento')} deshabilitado={enviando}>
        <Icono nombre="cerrar" medida={15} />
        Retirar mi acuerdo
      </Boton>
    {/if}
    {#if estado?.acceso && estado.acceso !== 'habilitado' && estado.acceso !== 'eliminacion_solicitada'}
      <Boton variante="discreto" onclick={() => navegar('/consentimiento')}>
        Ir al recorrido de autorización
      </Boton>
    {/if}
  </div>
</section>

<Dialogo
  abierto={Boolean(revocando)}
  titulo={revocando ? TEXTOS[revocando].titulo : ''}
>
  <p>{revocando ? TEXTOS[revocando].consecuencia : ''}</p>
  <p>
    <strong>Retirar la autorización no borra nada.</strong> Lo que el sistema ya
    guardó sigue guardado. Si lo que quieres es que se elimine, usa
    «Eliminar mis datos» en esta misma pantalla.
  </p>
  <p class="nota-version">
    El sistema retira exactamente la autorización que diste; esta pantalla no
    elige ninguna versión.
  </p>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (revocando = '')} deshabilitado={enviando}>
      Volver
    </Boton>
    <Boton onclick={confirmar} deshabilitado={enviando}>
      {enviando ? 'Registrando…' : revocando ? TEXTOS[revocando].boton : ''}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  .autorizaciones {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px 14px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
  }

  .cabecera { display: flex; align-items: center; gap: 8px; color: var(--ink-secondary); }

  h2 {
    margin: 0;
    font-size: var(--texto-base);
    font-weight: 700;
    color: var(--ink-primary);
  }

  .resumen {
    margin: 0;
    padding: 6px 10px;
    font-size: var(--texto-sm);
    font-weight: 600;
    border-radius: var(--radius-xs);
    border-inline-start: 3px solid var(--ink-tertiary);
    background: var(--surface-canvas);
    color: var(--ink-primary);
  }

  .resumen.listo { border-inline-start-color: var(--accent-main); }
  .resumen.espera { border-inline-start-color: var(--ink-tertiary); }
  .resumen.bloqueo { border-inline-start-color: var(--semantic-error); }

  .dimensiones { margin: 0; display: flex; flex-direction: column; gap: 6px; }

  .dimension dt {
    font-size: var(--texto-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-tertiary);
  }

  .dimension dd {
    margin: 0;
    font-size: var(--texto-sm);
    color: var(--ink-primary);
  }

  .version { color: var(--ink-secondary); }

  .nota {
    display: block;
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
  }

  .aviso {
    margin: 0;
    padding: 8px 10px;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--semantic-error);
    background: var(--surface-paper);
    border: 1px solid var(--semantic-error);
    border-radius: var(--radius-xs);
  }

  .aviso::before { content: '⚠ '; }

  .acciones { display: flex; flex-wrap: wrap; gap: 8px; }

  .nota-version { color: var(--ink-secondary); font-size: var(--texto-sm); }

  @media (max-width: 30rem) {
    .acciones { flex-direction: column; }
    .acciones :global(.boton) { inline-size: 100%; }
  }
</style>
