<!--
Las preferencias de pantalla, en un solo sitio.

Tema, escala de texto, animaciones, notación y representaciones gráficas.
Sigue estrictamente el lenguaje de diseño «tinta y papel» y los tokens de la aplicación.
-->
<script>
  import { untrack } from 'svelte';
  import Dialogo from '../base/Dialogo.svelte';
  import { toast } from '../estado/toasts.svelte.js';
  import Icono from '../base/Icono.svelte';
  import AccionesDeAjustes from './AccionesDeAjustes.svelte';
  import SeccionLienzo from './SeccionLienzo.svelte';
  import SeccionMatematica from './SeccionMatematica.svelte';
  import SeccionVisual from './SeccionVisual.svelte';
  import SelectorDeColor from './SelectorDeColor.svelte';
  import { guardarInterfaz } from '../../nucleo/preferencias/cuenta.js';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';

  let {
    abierto = $bindable(false),
    /** `arbolDe(sesion.rol)`. La pestaña «Notación y Gráficas» solo tiene
        efecto en el árbol de estudiante —notación de las derivadas y
        gráficas inline son cosas que se ven en `Conversacion.svelte`, que
        docente/investigador no visita—, así que no se ofrece ahí. Sin
        esto por defecto sigue mostrándose todo, que es el comportamiento
        de siempre para quien no pase la prop. */
    arbol = 'estudiante',
    temaOscuro = false
  } = $props();

  let seccion = $state('apariencia'); // 'apariencia' | 'lienzo' | 'matematica'
  let guardando = $state(false);
  let falloGuardado = $state('');
  let confirmado = false;
  let estabaAbierto = false;


  /** Guarda el estado inicial al abrir para poder cancelar */
  let snapshot = $state({
    tema: 'sistema',
    escala: 'normal',
    animaciones: true,
    fondoConversacion: false,
    intensidadFondoConversacion: 45,
    opacidadPregunta: 18,
    opacidadRespuesta: 10,
    notacion: '',
    grafica: true,
    colores: preferencias.colores
  });

  $effect(() => {
    if (abierto && !estabaAbierto) {
      estabaAbierto = true; confirmado = false; falloGuardado = '';
      // `untrack`: sin él, este efecto lee `preferencias.*` y Svelte las
      // vuelve dependencias suyas, así que CADA cambio mientras el diálogo
      // sigue abierto —tocar un radio, pulsar Restablecer— volvía a
      // ejecutarlo y pisaba `snapshot` con el valor que se acababa de
      // poner. «Cancelar» dejaba de tener a qué volver: siempre coincidía
      // con lo último tocado.
      untrack(() => {
        snapshot = {
          tema: preferencias.tema,
          escala: preferencias.escalaTexto,
          animaciones: preferencias.animaciones,
          fondoConversacion: preferencias.fondoDuranteConversacion,
          intensidadFondoConversacion: preferencias.intensidadFondoConversacion,
          opacidadPregunta: preferencias.opacidadPregunta,
          opacidadRespuesta: preferencias.opacidadRespuesta,
          notacion: preferencias.notacion,
          grafica: preferencias.graficaVisible,
          colores: {...preferencias.colores}
        };
      });
    } else if (!abierto && estabaAbierto) {
      estabaAbierto = false;
      if (!confirmado) untrack(restaurar);
    }
  });

  const PESTANAS = $derived(
    arbol === 'estudiante'
      ? [
          { id: 'apariencia', nombre: 'Apariencia', corto: 'Apariencia', icono: 'sol' },
          { id: 'color', nombre: 'Color', corto: 'Color', icono: 'sol' },
          { id: 'lienzo', nombre: 'Lienzo del Chat', corto: 'Lienzo', icono: 'pantalla' },
          { id: 'matematica', nombre: 'Notación y Gráficas', corto: 'Notación', icono: 'grafica' }
        ]
      : [
          { id: 'apariencia', nombre: 'Apariencia', corto: 'Apariencia', icono: 'sol' },
          { id: 'color', nombre: 'Color', corto: 'Color', icono: 'sol' },
          { id: 'lienzo', nombre: 'Lienzo del Chat', corto: 'Lienzo', icono: 'pantalla' }
        ]
  );

  function alRestablecer() {
    preferencias.restablecer();
    // El diálogo sigue abierto a propósito —a diferencia de Guardar—: es
    // el momento de ver que de verdad volvió a lo predeterminado antes de
    // decidir si guardarlo o seguir ajustando.
    toast.exito('Ajustes restablecidos. Revisa el resultado antes de guardar.');
  }

  function restaurar() {
    preferencias.elegirColores(snapshot.colores);
    preferencias.elegirTema(snapshot.tema);
    preferencias.elegirEscala(snapshot.escala);
    preferencias.alternarAnimaciones(snapshot.animaciones);
    preferencias.alternarFondoConversacion(snapshot.fondoConversacion);
    preferencias.elegirIntensidadFondoConversacion(snapshot.intensidadFondoConversacion);
    preferencias.elegirOpacidadPregunta(snapshot.opacidadPregunta);
    preferencias.elegirOpacidadRespuesta(snapshot.opacidadRespuesta);
    preferencias.elegirNotacion(snapshot.notacion);
    preferencias.alternarGrafica(snapshot.grafica);
  }
  function alCancelar() { if (!guardando) { restaurar(); abierto = false; } }

  async function alGuardar() {
    if (guardando) return;
    guardando = true; falloGuardado = '';
    try {
      await guardarInterfaz(); confirmado = true; abierto = false;
      toast.exito('Configuración guardada en tu cuenta.');
    } catch { falloGuardado = 'La vista previa sigue activa, pero no se pudo guardar en tu cuenta. Reintenta Guardar o cancela.'; }
    finally { guardando = false; }
  }
</script>

<Dialogo bind:abierto titulo="Ajustes" ancho="44rem" class="dialogo-ajustes" bloqueado={guardando}>


  <!-- Pestañas de sección -->
  <nav class="pestanas" aria-label="Secciones de ajustes">
    {#each PESTANAS as p (p.id)}
      <button
        type="button"
        class="tab-btn"
        class:activa={seccion === p.id}
        aria-label={p.nombre}
        aria-current={seccion === p.id ? 'page' : undefined}
        onclick={() => (seccion = p.id)}>
        <Icono nombre={p.icono} medida={15} />
        <span class="nombre-largo" aria-hidden="true">{p.nombre}</span>
        <span class="nombre-corto" aria-hidden="true">{p.corto}</span>
      </button>
    {/each}
  </nav>

  <div class="cuerpo-seccion">

    {#if seccion === 'apariencia'}
      <SeccionVisual />
    {:else if seccion === 'color'}
      <SelectorDeColor valor={preferencias.colores} alElegir={c => preferencias.elegirColores(c)} oscuro={temaOscuro} activo={abierto} />
    {:else if seccion === 'lienzo'}
      <SeccionLienzo />
    {:else if seccion === 'matematica'}
      <SeccionMatematica />
    {/if}

  </div>

  {#snippet acciones()}
    {#if falloGuardado}<p class="fallo-guardado" role="alert">{falloGuardado}</p>{/if}
    {#if guardando}<p role="status">Guardando en tu cuenta…</p>{/if}
    <AccionesDeAjustes {alRestablecer} {alCancelar} {alGuardar} bloqueado={guardando} />
  {/snippet}
</Dialogo>

<style>
  /* Pestañas superiores */
  :global(dialog.dialogo-ajustes[open]) {
    display:flex;
    flex-direction:column;
    inline-size:min(44rem, calc(100vw - 2rem));
    max-block-size:calc(100dvh - 2rem);
    overflow:hidden;
  }
  :global(dialog.dialogo-ajustes .cuerpo) {
    min-block-size:0;
    overflow-y:auto;
  }
  :global(dialog.dialogo-ajustes .acciones) {
    flex:none;
    margin-block-start:1rem;
  }
  :global(dialog.dialogo-ajustes .btn-cerrar-x) {
    min-inline-size:44px;
    min-block-size:44px;
  }

  .pestanas {
    display: flex;
    gap: 4px;
    padding: 4px;
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-pill);
    margin-block-end: 1.25rem;
    overflow-x:auto;
    scrollbar-width:thin;
  }

  .tab-btn {
    flex: 1 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-block-size:44px;
    padding: 8px 14px;
    border: 1px solid transparent;
    border-radius: var(--radius-pill);
    background: transparent;
    color: var(--ink-secondary);
    font-size: var(--texto-sm);
    font-weight: 500;
    font-family: inherit;
    cursor: pointer;
    transition: var(--transition);
    white-space: nowrap;
  }
  .nombre-corto { display:none; }

  .tab-btn:hover:not(.activa) {
    background: var(--surface-canvas);
    color: var(--ink-primary);
  }

  .tab-btn.activa {
    background: var(--surface-paper);
    border-color: var(--trazo-suave);
    color: var(--accent-main);
    font-weight: 600;
    box-shadow: var(--shadow-soft);
  }

  .cuerpo-seccion {
    display: flex;
    flex-direction: column;
    min-block-size: 19rem;
    min-inline-size:0;
  }

  @media (max-width:48rem) {
    :global(dialog.dialogo-ajustes) { padding:1rem; }
    .pestanas { margin-block-end:1rem; }
    .tab-btn { flex:1 1 0; min-inline-size:0; padding:.5rem .35rem; font-size:var(--texto-xs); }
    .tab-btn :global(svg), .nombre-largo { display:none; }
    .nombre-corto { display:inline; }
  }

</style>
