<!--
Volver a demostrar que eres tú, ahora · `EQ-022`, hito R3 y R7-A.

POR QUÉ ESTO NO ES «ENTRAR» OTRA VEZ
--------------------------------------
`POST /api/sesion/google` acepta cualquier `id_token` válido según su contrato
normal: exigirle frescura de segundos convertiría un inicio de sesión legítimo
con un token de hace un minuto en un fallo sin explicación.

`POST /api/sesion/reautenticar` es otra cosa. Comprueba cinco condiciones y las
dos últimas son las que importan aquí: que el `sub` sea el de **esta** sesión
—un token perfectamente firmado de otra cuenta institucional no reautentica a
ésta— y que Google lo haya **firmado hace un momento**. Sin esa segunda
comprobación, un token todavía vigente de hace cincuenta minutos habría servido,
y lo que se acreditaría sería cuándo llegó el token, no cuándo se autenticó la
persona.

⚠️ EL CLIENTE NO ACREDITA NADA
--------------------------------
Este componente entrega el `id_token` y ya está. No manda ninguna fecha, no
guarda el token y no escribe `reautenticada_en` en ningún sitio: la prueba la
construye el servidor con su propio reloj y `POST /api/datos/supresion` la
consume sin recibir nada del cuerpo. Una marca de tiempo enviada desde aquí no
demostraría nada.



-->
<script>
  import CargadorCubo from '../base/CargadorCubo.svelte';
  import Icono from '../base/Icono.svelte';
  import { cargarGuion, guionListo, pintarBoton } from '../../nucleo/sesion/google.js';
  import { reautenticar } from '../../nucleo/api/sesion.js';
  import { describir, clasificar } from '../../nucleo/errores/degradacion.js';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';

  let {
    /** `(vigentePorSegundos) => void` cuando el servidor acreditó la frescura. */
    alAcreditar,
    cliente = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ''
  } = $props();

  /** `cargando` · `listo` · `sin-guion` · `enviando`. */
  let fase = $state('cargando');
  let hueco = $state(null);
  let fallo = $state('');

  async function iniciarCarga() {
    if (!cliente) return;
    fase = 'cargando';
    fallo = '';
    try {
      await cargarGuion();
      if (!guionListo()) throw new Error('el guion llegó incompleto');
      fase = 'listo';
    } catch {
      fase = 'sin-guion';
    }
  }

  $effect(() => {
    iniciarCarga();
  });

  let sistemaOscuro = $state(
    typeof window !== 'undefined' &&
      Boolean(window.matchMedia?.('(prefers-color-scheme: dark)').matches)
  );

  const esOscuro = $derived(
    preferencias.tema === 'oscuro' ||
      (preferencias.tema === 'sistema' && sistemaOscuro)
  );

  async function alRecibirCredencial(respuesta) {
    if (!respuesta?.credential) {
      fallo = 'Google no entregó la credencial esperada.';
      return;
    }
    fallo = '';
    fase = 'enviando';
    try {
      const acreditada = await reautenticar(respuesta.credential);
      alAcreditar?.(Number(acreditada?.vigente_por_segundos ?? 0));
      fase = 'listo';
    } catch (e) {
      fase = 'listo';
      const clase = clasificar(e);
      if (clase === 'sin-sesion') {
        // El servidor distingue en el cuerpo por qué no sirve, y las dos
        // razones se arreglan de forma distinta: una cuenta equivocada y un
        // token viejo no son el mismo problema para quien está delante.
        fallo =
          e?.estadoDelServidor === 'sujeto_distinto'
            ? 'Ese acceso es de otra cuenta. Entra con la misma cuenta con la que iniciaste sesión.'
            : e?.detalle ||
              'Ese acceso no es lo bastante reciente. Vuelve a entrar con Google ahora mismo.';
      } else {
        fallo = describir(e)?.titulo ?? 'No se pudo comprobar tu identidad.';
      }
    }
  }

  $effect(() => {
    if (fase !== 'listo' || !hueco) return;
    pintarBoton(hueco, {
      cliente,
      callback: alRecibirCredencial,
      tema: esOscuro ? 'filled_black' : 'outline',
      ancho: 240,
      // «Continuar con Google» y no «Iniciar sesión»: no se está entrando, se
      // está volviendo a demostrar quién es quien ya entró.
      texto: 'continue_with'
    });
  });
</script>

<div class="reautenticar">
  {#if !cliente}
    <p class="aviso" role="status">
      Entrar con la cuenta institucional no está configurado en este equipo, así
      que este trámite no se puede completar desde aquí.
    </p>
  {:else if fase === 'sin-guion'}
    <p class="aviso" role="alert">No se pudo conectar con Google.</p>
    <button type="button" class="reintentar" onclick={iniciarCarga}>
      <Icono nombre="google" medida={15} />
      Volver a intentarlo
    </button>
  {:else if fase === 'enviando'}
    <p class="estado" role="status">
      <span class="pulso"></span>
      Comprobando tu identidad con Google…
    </p>
  {:else if fase === 'cargando'}
    <CargadorCubo mensaje="Conectando con Google…" compacto />
  {/if}

  <div class="hueco" bind:this={hueco} hidden={fase !== 'listo'}></div>

  {#if fallo}
    <p class="aviso" role="alert">{fallo}</p>
  {/if}
</div>

<style>
  .reautenticar {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .hueco { min-block-size: 40px; }

  .estado {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
  }

  .pulso {
    inline-size: 8px;
    block-size: 8px;
    border-radius: 50%;
    background: var(--accent-main);
    animation: latido 1.1s ease-in-out infinite;
  }

  @keyframes latido {
    0%, 100% { opacity: 0.35; transform: scale(0.85); }
    50%      { opacity: 1;    transform: scale(1); }
  }

  .aviso {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--semantic-error);
  }

  .reintentar {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    font-family: inherit;
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-primary);
    background: var(--surface-paper);
    border: 1px solid var(--trazo);
    border-radius: var(--radius-trazado);
    cursor: pointer;
  }

  .reintentar:hover { background: var(--surface-canvas); }
</style>
