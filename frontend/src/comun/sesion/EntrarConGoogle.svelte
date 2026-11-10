
<script>
  import { toast } from '../estado/toasts.svelte.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { clasificar, describir } from '../../nucleo/errores/degradacion.js';
  import { navegar, arbolDe } from '../../enrutado/navegar.js';
  import { inicioDe } from '../../enrutado/caminos.js';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import Icono from '../base/Icono.svelte';
  import Boton from '../base/Boton.svelte';
  import Dialogo from '../base/Dialogo.svelte';
  import CargadorDeAcceso from './CargadorDeAcceso.svelte';
  import { cargarGuion, guionListo } from '../../nucleo/sesion/google.js';

  let { cliente = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? '', mostrarControl = true,
    confirmandoSalida = $bindable(false) } = $props();

  let fase = $state('cargando');
  let hueco = $state(null);
  let fallo = $state(null);
  let pintado = false;
  let anchoHueco = $state(0);

  const anchoBoton = $derived(Math.max(200, Math.min(210, Math.floor(anchoHueco) || 210)));

  $effect(() => {
    if (!hueco || typeof ResizeObserver === 'undefined') return;
    anchoHueco = hueco.getBoundingClientRect().width;
    const observador = new ResizeObserver(([entrada]) => {
      if (entrada) anchoHueco = entrada.contentRect.width;
    });
    observador.observe(hueco);
    return () => observador.disconnect();
  });


  async function iniciarCarga() {
    if (!cliente) return;
    fase = 'cargando';
    fallo = null;
    try {
      await cargarGuion();
      if (!guionListo()) throw new Error('el guion llegó incompleto');
      fase = 'listo';
    } catch {
      fase = 'sin-guion';
    }
  }

  $effect(() => {
    if (mostrarControl && cliente && !pintado) {
      iniciarCarga();
    }
  });

  function explicar(error) {
    if (clasificar(error) === 'sin-sesion') {
      return 'Esa cuenta no se admite. Entra con tu cuenta institucional del dominio de la universidad.';
    }
    return describir(error)?.titulo || 'No se pudo entrar con Google. Vuelve a intentarlo.';
  }

  async function alRecibirCredencial(respuesta) {
    if (!respuesta?.credential) {
      fallo = 'Google no entregó la credencial esperada.';
      return;
    }
    fallo = null;
    const antes = sesion.rol;
    fase = 'autenticando';
    try {
      await sesion.entrarConGoogle(respuesta.credential);
      if (arbolDe(antes) !== arbolDe(sesion.rol) || sesion.rol === 'docente' || sesion.rol === 'investigador') {
        navegar(inicioDe(sesion.rol));
      }
    } catch (e) {
      fallo = explicar(e);
      fase = 'listo';
    }
  }

  let sistemaOscuro = $state(
    typeof window !== 'undefined' && Boolean(window.matchMedia?.('(prefers-color-scheme: dark)').matches)
  );

  $effect(() => {
    const consulta = globalThis.matchMedia?.('(prefers-color-scheme: dark)');
    const alCambiar = () => { sistemaOscuro = Boolean(consulta?.matches); };
    consulta?.addEventListener('change', alCambiar);
    return () => consulta?.removeEventListener('change', alCambiar);
  });

  const esOscuro = $derived(
    preferencias.tema === 'oscuro' ||
    (preferencias.tema === 'sistema' && sistemaOscuro)
  );

  let ultimoRenderizado = { el: null, firma: null };

  $effect(() => {
    if (fase !== 'listo' || !hueco) return;
    const temaActual = esOscuro ? 'filled_black' : 'outline';
    const ancho = anchoBoton;
    const firma = `${temaActual}:${ancho}`;
    if (ultimoRenderizado.el === hueco && ultimoRenderizado.firma === firma) return;
    const esPrimerPintado = ultimoRenderizado.el !== hueco;
    ultimoRenderizado = { el: hueco, firma };

    const pintar = () => {
      hueco.innerHTML = '';
      globalThis.google?.accounts?.id?.initialize({
        client_id: cliente,
        callback: alRecibirCredencial,
        auto_select: false,
        cancel_on_tap_outside: true
      });
      globalThis.google?.accounts?.id?.renderButton(hueco, {
        type: 'standard',
        theme: temaActual,
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        width: ancho,
        locale: 'es'
      });
      hueco.style.opacity = '1';
    };

    if (esPrimerPintado) {
      pintar();
    } else {
      hueco.style.transition = 'opacity 0.12s ease';
      hueco.style.opacity = '0';
      setTimeout(pintar, 120);
    }
  });

  const anuncio = $derived({
    cargando: 'Conectando con Google…',
    autenticando: 'Verificando tu cuenta con Google…',
    listo: '',
    'sin-guion': 'No se pudo conectar con Google. Vuelve a intentarlo.'
  }[fase] ?? '');

  const rotulo = $derived({
    cargando: 'Conectando…',
    autenticando: 'Verificando…',
    'sin-guion': 'Reintentar con Google'
  }[fase] ?? 'Iniciar sesión con Google');

  let cerrando = $state(false);

  async function cerrarSesion() {
    if (cerrando) return;
    cerrando = true;
    try {
      await sesion.cerrar();
      confirmandoSalida = false;
      toast.alerta('Sesión finalizada correctamente.');
      navegar('/consentimiento');
    } finally {
      cerrando = false;
    }
  }
</script>

{#if mostrarControl && sesion.autenticada}
  <button type="button" class="salir" onclick={() => (confirmandoSalida = true)}>
    <Icono nombre="cerrar-sesion" medida={20} />
    Cerrar sesión
  </button>
{:else if mostrarControl && !cliente}
  <span class="aviso aviso-desactivado" role="status">
    Entrar con la cuenta institucional no está configurado en este equipo
  </span>
{:else if mostrarControl}
  <div class="entrar">
    {#if fase === 'listo'}
      <div class="hueco-google" bind:this={hueco}></div>
    {:else if fase === 'autenticando'}
      <CargadorDeAcceso />
    {:else if fase === 'cargando'}
      <div class="esqueleto-google" aria-busy="true">
        <Icono nombre="google" medida={16} />
        <span>Cargando…</span>
      </div>
    {:else}
      <button type="button" class="propio" onclick={iniciarCarga}>
        <Icono nombre="google" medida={16} />
        <span class="rotulo-propio">{rotulo}</span>
      </button>
    {/if}


    <span class="aviso status-sr" role="status">{anuncio}</span>

    {#if fallo}
      <span class="aviso aviso-error" role="alert">{fallo}</span>
    {/if}
  </div>
{/if}

<Dialogo bind:abierto={confirmandoSalida} tipo="cerrar-sesion" titulo="¿Cerrar sesión institucional?" bloqueado={cerrando}>
  <p>
    Se cerrará tu sesión <strong>en el servidor</strong>, no sólo en este
    navegador: para volver tendrás que entrar otra vez con tu cuenta
    institucional.
  </p>
  <p>
    No se pierde nada de lo que hayas guardado. Tus conversaciones y tus
    autorizaciones siguen donde están.
  </p>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (confirmandoSalida = false)} deshabilitado={cerrando}>
      Seguir en la sesión
    </Boton>
    <Boton onclick={cerrarSesion} deshabilitado={cerrando}>
      {cerrando ? 'Cerrando…' : 'Sí, cerrar sesión'}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  .entrar {
    display: flex;
    flex-direction: column;
    align-items: center;
    inline-size: 100%;
    background: transparent;
    gap: 0.35rem;
  }

  .hueco-google {
    display: flex;
    justify-content: center;
    align-items: center;
    inline-size: 100%;
    min-block-size: 40px;
    background: transparent;
    border-radius: var(--radius-sm);
    overflow: hidden;
    animation: fadeIn 0.2s ease-out;
  }

  .hueco-google :global(iframe) {
    border: none;
  }

  .esqueleto-google {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    inline-size: 100%;
    max-inline-size: 210px;
    min-block-size: 40px;
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    color: var(--ink-tertiary);
    font-size: 12.5px;
    opacity: 0.8;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: scale(0.97); }
    to   { opacity: 1; transform: scale(1); }
  }

  .status-sr {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }

  .aviso-error {
    display: block;
    max-inline-size: 100%;
    color: var(--estado-fallo, var(--ink-tertiary));
    font-size: var(--texto-xs);
    text-align: center;
  }

  .aviso-desactivado {
    max-inline-size: 100%;
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
    text-align: center;
  }

  .aviso:empty { display: none; }

  .propio {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    inline-size: 100%;
    max-inline-size: 210px;
    block-size: 40px;
    padding: 8px 12px;
    box-sizing: border-box;
    background: var(--surface-paper);
    border: 1.5px solid var(--trazo);
    border-radius: var(--radius-sm);
    color: var(--ink-primary);
    box-shadow: var(--shadow-soft);
    font: inherit;
    font-size: 12.5px;
    font-weight: 500;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .rotulo-propio {
    min-inline-size: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .propio :global(.icono),
  .esqueleto-google :global(.icono) {
    flex-shrink: 0;
  }

  .propio:hover {
    border-color: var(--accent-main);
    background: var(--surface-panel);
  }

  .salir {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: .5rem;
    inline-size: 100%;
    padding: 6px 10px;
    background: transparent;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-sm);
    color: var(--ink-secondary);
    font: inherit;
    font-size: 12px;
    cursor: pointer;
    transition: var(--transition-fast);
  }

  .salir:hover {
    color: var(--ink-primary);
    border-color: var(--ink-tertiary);
    background: var(--surface-hover, var(--surface-panel));
  }
</style>
