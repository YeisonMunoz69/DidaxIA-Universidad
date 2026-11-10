
<script>
  import CargadorCubo from '../base/CargadorCubo.svelte';
  import Boton from '../base/Boton.svelte';
  import Icono from '../base/Icono.svelte';
  import PantallaNoEncontrada from '../base/PantallaNoEncontrada.svelte';
  import Degradacion from '../estado/Degradacion.svelte';
  import { describir, FalloDeRed } from '../../nucleo/errores/degradacion.js';

  let {
    sincronizada = false,
    ruta = null,
    destino = '/',
    consulta = '',
    arbol = 'estudiante',
    inicio = '/',
    ir,
    recargar = () => globalThis.location?.reload()
  } = $props();

  const carga = $derived.by(() => {
    if (!sincronizada || !ruta?.cargar || ruta.pendiente) return null;
    const cargar = ruta.cargar;
    return Promise.resolve().then(() => cargar());
  });

  function falloDeCarga(error) {
    return describir(globalThis.navigator?.onLine === false
      ? new FalloDeRed('sin-red', { causa: error }) : error);
  }

  function reintentarCarga() {
    if (globalThis.navigator?.onLine === false) return;
    recargar();
  }
</script>

<main id="contenido">
  {#if !sincronizada}
    <CargadorCubo mensaje="Comprobando la sesión…" pantallaCompleta />
  {:else if !ruta}
    <div class="ruta-ausente"><PantallaNoEncontrada camino={destino} {inicio} alInicio={() => ir(inicio)} /></div>
  {:else if ruta.pendiente}
    <section class="pendiente">
      <div class="tarjeta-pendiente">
        <div class="icono-pendiente">
          <Icono nombre={ruta.icono || 'practica'} medida={32} />
        </div>
        <span class="insignia-desarrollo">En preparación pedagógica</span>
        <h1>{ruta.titulo}</h1>
        <p class="intro-pendiente">
          Esta pantalla está declarada y <strong>todavía no se ha construido</strong>.
        </p>
        <p class="tarea">Corresponde a <code>{ruta.pendiente}</code>.</p>
        <div class="accion-pendiente">
          <Boton onclick={() => ir(inicio)}>
            <Icono nombre="conversacion" medida={15} />
            <span>Ir a la conversación</span>
          </Boton>
        </div>
      </div>
    </section>
  {:else if ruta.cargar}

    {#key ruta.camino}
    {#await carga}
      <CargadorCubo mensaje={`Cargando ${ruta.titulo}…`} pantallaCompleta />
    {:then modulo}
      {@const Pantalla = modulo.default}
      <Pantalla caminoActual={destino} consultaActual={consulta} />
    {:catch error}
      <div class="fallo-ruta">
        <Degradacion respuesta={falloDeCarga(error)} alReintentar={reintentarCarga} />
        <p class="ayuda-recarga">Restablece la conexión antes de reintentar. Se recargará esta pantalla.</p>
      </div>
    {/await}
    {/key}
  {/if}
</main>

<style>
  main {
    flex: 1;
    min-block-size: 0;
    min-inline-size: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 0;
    position: relative;
    height: 100%;
  }

  .fallo-ruta {
    flex: 1;
    min-block-size: 0;
    min-inline-size: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: var(--espacio-lg);
    inline-size: 100%;
    max-inline-size: 72rem;
    margin-inline: auto;
    box-sizing: border-box;
  }
  .ayuda-recarga { color: var(--ink-secondary); font-size: var(--texto-sm); }

  .pendiente {
    padding: var(--espacio-xl) var(--espacio-lg);
    display: flex;
    justify-content: center;
    align-items: center;
    inline-size: 100%;
    margin-inline: auto;
  }

  .tarjeta-pendiente {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: var(--espacio-sm);
    padding: var(--espacio-xl) var(--espacio-lg);
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
    max-inline-size: 34rem;
    inline-size: 100%;
    animation: entrarVista 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .icono-pendiente {
    display: flex;
    align-items: center;
    justify-content: center;
    inline-size: 64px;
    block-size: 64px;
    border-radius: 50%;
    background: var(--accent-surface);
    color: var(--accent-main);
    margin-block-end: 4px;
  }

  .insignia-desarrollo {
    display: inline-block;
    padding: 3px 10px;
    border-radius: var(--radius-pill, 9999px);
    background: var(--surface-paper);
    color: var(--ink-secondary);
    border: 1px solid var(--trazo-suave);
    font-size: var(--texto-xs);
    font-weight: 600;
  }

  .tarjeta-pendiente h1 {
    margin: 0;
    font-size: var(--texto-xl);
    font-weight: 700;
    color: var(--ink-primary);
  }

  .intro-pendiente {
    margin: 0;
    font-size: var(--texto-base);
    color: var(--ink-secondary);
    line-height: 1.5;
  }

  .ruta-ausente { flex: 1; min-block-size: 0; overflow-y: auto; }
  .tarea { font-size: var(--texto-xs); color: var(--ink-tertiary); }
  .tarea code { font-family: var(--fuente-mono); color: var(--accent-main); }
  .accion-pendiente { margin-block-start: var(--espacio-sm); }
  code { font-family: var(--fuente-mono); }
</style>
