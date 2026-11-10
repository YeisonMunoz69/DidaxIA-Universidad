<!--
La dimensión del representante · `EQ-016` / `EQ-021`.

Los seis estados que `EstadoRepresentante` declara, el plazo que informa el
servidor, la versión requerida del documento y la carga del PDF.

⚠️ SIN VERSIÓN REQUERIDA NO SE OFRECE CARGA, Y ESTE ERA EL FALLO
------------------------------------------------------------------
Hasta la corrección de C1 este panel no recibía la versión del representante y
pintaba el selector de PDF siempre. Con `GET /api/consentimiento/versiones`
devolviendo `representante: null` —el estado real de cualquier base de este
árbol— el recorrido invitaba a buscar una autorización, firmarla, escanearla y
subirla, para que `POST /api/representante/evidencia` la rechazara con `409` y
`sin_version`. La comprobación existía en las otras dos dimensiones y aquí
faltaba, así que el menor era el único a quien la interfaz le pedía trabajo
imposible.

Se usa el mismo `hayVersion()` que `DecisionConjunta.svelte`: una sola
definición de «hay documento publicado» para las tres dimensiones, que es lo
que impide que una vuelva a divergir.

⚠️ EL PLAZO LO DICE EL BACKEND, SIEMPRE
-----------------------------------------
`limite` llega en la respuesta y lo fija `declarar_perfil()` en la misma
sentencia que la edad, con el reloj de la base. Aquí sólo se formatea y se
compara con la hora del navegador **para redactar** («quedan tres días»), nunca
para decidir si venció: eso lo decide el estado que manda el servidor. Un reloj
adelantado diría «vencido» sobre un plazo abierto, y uno atrasado lo contrario.

✅ LA PLANTILLA APROBADA SE DESCARGA COMO PDF FECHADO
------------------------------------------------
El servidor parte del Word aprobado por los docentes, conserva su maquetación y
estampa en el pie la fecha civil de Colombia en que el estudiante lo descarga.
El padre, madre o representante lo diligencia y firma; la carga posterior sigue
aceptando exclusivamente PDF y se registra contra la versión vigente.



-->
<script>
  import Icono from '../../../comun/base/Icono.svelte';
  import CargaDeEvidencia from './CargaDeEvidencia.svelte';
  import { hayVersion } from '../../../nucleo/api/consentimiento.js';

  let {
    /** `estado.representante` tal como llegó del servidor. */
    representante,
    /**
     * La versión requerida del alcance `representante`, o `null`.
     *
     * Sale de `GET /api/consentimiento/versiones`; puede ser `null` en una
     * base sin publicación, y de eso depende la oferta de carga.
     */
    version = null,
    /** `async () => void`, descarga autenticada del PDF con fecha. */
    alDescargar,
    /** `async (archivo) => void`, para la carga binaria. */
    alSubir,
    errorDelServidor = '',
    reservaPendiente = false,
    motivo = '',
    versionesNoDisponibles = false,
    alReintentarVersiones = () => {},
    alComprobarEstado = () => {}
  } = $props();

  /**
   * Qué significa cada estado y si el backend puede recibir una carga en él.
   *
   * Los seis de `EstadoRepresentante`, ninguno inventado. `subir` sólo dice si
   * el ESTADO admite una carga; que además exista versión publicada es la otra
   * condición, y las dos tienen que cumplirse.
   */
  const ESTADOS = {
    pendiente_documento: {
      titulo: 'Falta la autorización de tu representante',
      cuerpo:
        'Tu representante tiene que firmar la autorización y tú subirla aquí en PDF. Mientras no esté aprobada, el tutor sigue bloqueado.',
      tono: 'espera',
      subir: true
    },
    documento_recibido: {
      titulo: 'Recibimos la autorización',
      cuerpo:
        'Tu PDF está esperando revisión. Esta pantalla comprobará el resultado automáticamente.',
      tono: 'espera',
      subir: false
    },
    aprobado: {
      titulo: 'La autorización quedó aprobada',
      cuerpo: 'La revisión terminó y la autorización de tu representante es válida.',
      tono: 'listo',
      subir: false
    },
    rechazado: {
      titulo: 'La autorización necesita una corrección',
      cuerpo: 'Puedes repetir los pasos y enviar un PDF corregido para una nueva revisión.',
      tono: 'bloqueo',
      subir: true
    },
    vencido: {
      titulo: 'Se cumplió el plazo inicial de autorización',
      cuerpo:
        'Aún puedes entregar el PDF firmado para revisión. La fecha inicial queda registrada; enviarlo ahora no habilita el tutor hasta que se apruebe.',
      tono: 'bloqueo',
      subir: true
    },
    no_requerido: {
      titulo: 'No necesitas autorización de un representante',
      cuerpo: 'Según la edad que declaraste, esta autorización no te corresponde.',
      tono: 'listo',
      subir: false
    }
  };

  const info = $derived(ESTADOS[representante?.estado] ?? ESTADOS.pendiente_documento);

  /** ¿Hay un documento publicado contra el que registrar la evidencia? */
  const publicada = $derived(hayVersion(version));
  // Una versión publicada puede no corresponder al PDF empaquetado. El API
  // lo comprueba con la misma regla que la descarga y lo comunica aquí.
  const formatoDisponible = $derived(version?.formato_disponible !== false);

  /**
   * La carga se ofrece sólo si se cumplen LAS DOS condiciones.
   *
   * El estado tiene que admitirla y debe existir un formato descargable. El
   * servidor admite una entrega tardía sin mover el plazo histórico (véase
   * test_un_vencido_puede_cargar_todavia); ocultarla aquí bloqueaba al menor.
   */
  const ofreceCarga = $derived(info.subir && publicada && formatoDisponible);
  const recibido = $derived(representante?.estado === 'documento_recibido');
  const aprobado = $derived(representante?.estado === 'aprobado');
  const requiereDocumento = $derived(
    ['pendiente_documento', 'rechazado', 'vencido'].includes(representante?.estado)
  );
  const muestraCamino = $derived(
    ['pendiente_documento', 'rechazado', 'vencido', 'documento_recibido', 'aprobado'].includes(
      representante?.estado
    )
  );

  let descargando = $state(false);
  let descargado = $state(false);
  let errorDeDescarga = $state('');

  async function descargar() {
    if (descargando || typeof alDescargar !== 'function') return;
    descargando = true;
    errorDeDescarga = '';
    try {
      descargado = await alDescargar() !== false || descargado;
    } catch (error) {
      errorDeDescarga = error?.estadoDelServidor === 'formato_no_corresponde'
        ? 'El formato aún no coincide con la autorización vigente. No prepares otro documento: avisa al equipo del proyecto.'
        : error?.detalle || 'No pudimos preparar el formato. Vuelve a intentarlo; no se registró ninguna carga.';
    } finally {
      descargando = false;
    }
  }

  /**
   * El límite en lenguaje humano, o `''` si el servidor no mandó ninguno.
   *
   * `null` es un estado real —el plazo nace al declarar la minoría de edad, y
   * antes de eso no existe—, así que no se rellena con una fecha calculada aquí.
   */
  const limiteLegible = $derived.by(() => {
    if (!representante?.limite) return '';
    const fecha = new Date(representante.limite);
    if (Number.isNaN(fecha.getTime())) return '';
    return fecha.toLocaleString('es-CO', { dateStyle: 'long', timeStyle: 'short' });
  });

  /**
   * Cuántos días faltan, para redactar. NO para decidir si venció.
   *
   * Devuelve `null` cuando no hay límite o cuando ya pasó: en ese caso el texto
   * no dice nada y manda el estado del servidor.
   */
  const diasRestantes = $derived.by(() => {
    if (!representante?.limite) return null;
    const fecha = new Date(representante.limite);
    if (Number.isNaN(fecha.getTime())) return null;
    const dias = Math.ceil((fecha.getTime() - Date.now()) / 86_400_000);
    return dias > 0 ? dias : null;
  });
</script>

<section class="representante {info.tono}" aria-labelledby="titulo-representante">
  <header class="cabecera">
    <span class="marca-icono"><Icono nombre="escudo" medida={17} /></span>
    <div>
      <h2 id="titulo-representante">{info.titulo}</h2>
      <p class="cuerpo">{info.cuerpo}</p>
    </div>
  </header>

  {#if limiteLegible && requiereDocumento}
    <p class="plazo">
      <Icono nombre="candado" medida={13} />
      <span>
        {representante?.estado === 'vencido' ? 'Plazo inicial: ' : 'Entrega hasta el '}
        <strong><time datetime={representante.limite}>{limiteLegible}</time></strong>
        {#if diasRestantes !== null}
          <span class="restante">· {diasRestantes === 1 ? 'queda 1 día' : `quedan ${diasRestantes} días`}</span>
        {/if}
      </span>
    </p>
  {/if}

  {#if representante?.estado === 'rechazado' && motivo}
    <div class="motivo-rechazo" role="status">
      <strong>Qué debes corregir</strong>
      <p>{motivo}</p>
    </div>
  {/if}

  {#if publicada && (formatoDisponible || recibido || aprobado) && muestraCamino}
    <ol class="camino" aria-label="Pasos para entregar la autorización">
      <li class:completo={descargado || recibido || aprobado} style="--orden: 0">
        <span class="numero" aria-hidden="true">{descargado || recibido || aprobado ? '✓' : '1'}</span>
        <div class="contenido-paso">
          <strong>Descarga el formato</strong>
          <small>La fecha del día se completa automáticamente.</small>
          {#if requiereDocumento}
            <button type="button" class="boton-descarga" onclick={descargar} disabled={descargando}>
              <Icono nombre="descarga" medida={15} />
              {descargando ? 'Preparando PDF…' : descargado ? 'Descargar de nuevo' : 'Descargar PDF'}
            </button>
          {/if}
          {#if errorDeDescarga}
            <p class="aviso-paso" role="alert">{errorDeDescarga}</p>
          {/if}
        </div>
      </li>

      <li class:completo={recibido || aprobado} style="--orden: 1">
        <span class="numero" aria-hidden="true">{recibido || aprobado ? '✓' : '2'}</span>
        <div class="contenido-paso">
          <strong>Tu representante lo completa y firma</strong>
          <small>Puede firmarlo en papel o con una firma digital válida.</small>
        </div>
      </li>

      <li class:completo={aprobado} class:en-revision={recibido} style="--orden: 2">
        <span class="numero" aria-hidden="true">{aprobado ? '✓' : '3'}</span>
        <div class="contenido-paso">
          <strong>{recibido ? 'En revisión' : aprobado ? 'Autorización aprobada' : 'Sube el PDF firmado'}</strong>
          {#if recibido}
            <p class="revisando" role="status">
              <span class="punto-vivo" aria-hidden="true"></span>
              No necesitas recargar esta página.
            </p>
          {:else if ofreceCarga}
            <CargaDeEvidencia
              {alSubir}
              {errorDelServidor}
              {reservaPendiente}
            />
          {/if}
        </div>
      </li>
    </ol>

  {:else if versionesNoDisponibles}
    <div class="sin-version" role="alert">
      <Icono nombre="candado" medida={15} />
      <div>
        <strong>No pudimos comprobar el formato de autorización</strong>
        <p>Puede ser un problema temporal de conexión. Tu registro sigue guardado.</p>
        <button type="button" class="boton-descarga" onclick={alReintentarVersiones}>Volver a comprobar</button>
      </div>
    </div>
  {:else if publicada && !formatoDisponible}
    <div class="sin-version" role="alert">
      <Icono nombre="candado" medida={15} />
      <div>
        <strong>El formato todavía no está listo para descargarse</strong>
        <p>No uses un documento hecho por tu cuenta. Tu registro sigue guardado; el equipo debe corregir la publicación del formato.</p>
        <button type="button" class="boton-descarga" onclick={alReintentarVersiones}>Comprobar de nuevo</button>
      </div>
    </div>
  {:else if !publicada}
    <div class="sin-version" role="note">
      <Icono nombre="candado" medida={15} />
      <div>
        <strong>Todavía no hay un documento de autorización publicado</strong>
        <p>
          No es un fallo del sistema ni algo que puedas resolver por tu cuenta.
          No hace falta que consigas ninguna autorización mientras tanto.
        </p>
      </div>
    </div>
  {/if}

  {#if errorDelServidor && !recibido}
    <button type="button" class="boton-descarga" onclick={alComprobarEstado}>Comprobar si el archivo llegó</button>
  {/if}
</section>

<style>
  .representante {
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-inline-size: 0;
  }

  .cabecera { display: flex; align-items: flex-start; gap: 10px; }
  .marca-icono { display: flex; margin-block-start: 2px; color: var(--accent-main); flex: none; }

  h2 { margin: 0; color: var(--ink-primary); font-size: var(--texto-lg); line-height: 1.25; }
  .cuerpo { margin: 3px 0 0; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.45; }

  .plazo {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0;
    padding: 7px 9px;
    border-radius: var(--radius-xs);
    background: var(--accent-surface);
    color: var(--ink-primary);
    font-size: var(--texto-xs);
    line-height: 1.4;
  }
  .restante { color: var(--ink-secondary); }

  .motivo-rechazo {
    padding: 10px 12px;
    border-inline-start: 3px solid var(--semantic-warning);
    border-radius: var(--radius-xs);
    background: var(--accent-surface);
    color: var(--ink-primary);
  }
  .motivo-rechazo strong { font-size: var(--texto-sm); }
  .motivo-rechazo p { margin: 3px 0 0; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.45; }

  .camino {
    display: grid;
    gap: 0;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .camino li {
    --linea: var(--trazo);
    position: relative;
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    gap: 11px;
    min-inline-size: 0;
    padding-block-end: 18px;
    opacity: 0;
    transform: translateY(7px);
    animation: aparece-paso 360ms ease-out forwards;
    animation-delay: calc(var(--orden) * 110ms);
  }

  .camino li:not(:last-child)::after {
    content: '';
    position: absolute;
    inset-block: 34px 0;
    inset-inline-start: 16px;
    inline-size: 2px;
    background: linear-gradient(var(--accent-main), var(--linea));
  }

  .camino li:last-child { padding-block-end: 0; }

  .numero {
    position: relative;
    z-index: 1;
    display: grid;
    place-items: center;
    inline-size: 34px;
    block-size: 34px;
    border: 2px solid var(--accent-main);
    border-radius: 50%;
    background: var(--surface-panel);
    color: var(--accent-main);
    font-size: var(--texto-sm);
    font-weight: 800;
  }

  .completo .numero { background: var(--accent-main); color: var(--accent-on-main); }
  .en-revision .numero { animation: pulso-revision 1.6s ease-in-out infinite; }

  .contenido-paso { display: flex; flex-direction: column; gap: 5px; min-inline-size: 0; padding-block-start: 5px; }
  .contenido-paso > strong { color: var(--ink-primary); font-size: var(--texto-sm); }
  .contenido-paso > small { color: var(--ink-secondary); font-size: var(--texto-xs); line-height: 1.4; }

  .boton-descarga {
    align-self: flex-start;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    min-block-size: 42px;
    margin-block-start: 3px;
    padding: 8px 12px;
    border: 0;
    border-radius: var(--radius-sm);
    background: var(--accent-main);
    color: var(--accent-on-main);
    font: inherit;
    font-size: var(--texto-sm);
    font-weight: 700;
  }
  .boton-descarga:disabled { opacity: 0.65; cursor: wait; }

  .aviso-paso { margin: 0; color: var(--semantic-error); font-size: var(--texto-xs); line-height: 1.4; }

  .revisando {
    display: flex;
    align-items: center;
    gap: 7px;
    margin: 0;
    color: var(--ink-secondary);
    font-size: var(--texto-xs);
  }
  .punto-vivo { inline-size: 7px; block-size: 7px; border-radius: 50%; background: var(--accent-main); animation: latido 1.2s ease-in-out infinite; }

  .sin-version {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 9px;
    padding: 12px;
    border: 1px dashed var(--trazo);
    border-radius: var(--radius-sm);
    background: var(--surface-canvas);
    color: var(--ink-primary);
  }
  .sin-version p { margin: 4px 0 0; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.45; }

  @keyframes aparece-paso { to { opacity: 1; transform: translateY(0); } }
  @keyframes pulso-revision { 50% { box-shadow: 0 0 0 7px color-mix(in srgb, var(--accent-main) 14%, transparent); } }
  @keyframes latido { 50% { opacity: 0.35; transform: scale(0.78); } }

  :global(html[data-animaciones='no']) .camino li,
  :global(html[data-animaciones='no']) .en-revision .numero,
  :global(html[data-animaciones='no']) .punto-vivo { animation: none; opacity: 1; transform: none; }

  @media (prefers-reduced-motion: reduce) {
    .camino li, .en-revision .numero, .punto-vivo { animation: none; opacity: 1; transform: none; }
  }

  @media (max-width: 30rem) {
    .boton-descarga { inline-size: 100%; justify-content: center; }
  }
</style>
