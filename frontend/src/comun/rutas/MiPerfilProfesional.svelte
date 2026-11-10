<!--
Perfil propio de docente e investigador.

La fotografía usa exactamente la misma custodia privada que el estudiante y
Google sigue siendo sólo el valor inicial: una imagen subida por la persona no
se reemplaza al volver a entrar. Los datos de identidad son de solo lectura
porque su autoridad es la cuenta institucional; la facultad docente la gobierna
el equipo para no abrir dos fuentes de verdad.


-->
<script>
  import CargadorCubo from '../base/CargadorCubo.svelte';
  import { onMount } from 'svelte';
  import { cubicOut } from 'svelte/easing';
  import { fade, fly } from 'svelte/transition';
  import PestanasSegmentadas from '../base/PestanasSegmentadas.svelte';
  import BotonAyudaTooltip from '../base/BotonAyudaTooltip.svelte';
  import CabeceraDeRuta from '../../docente/piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../../docente/piezas/PantallaDesplazable.svelte';
  import Degradacion from '../estado/Degradacion.svelte';
  import PanelDeDatosPersonales from '../../estudiante/piezas/PanelDeDatosPersonales.svelte';
  import EntrarConGoogle from '../sesion/EntrarConGoogle.svelte';
  import CompositorDeCorreos from '../../investigador/piezas/CompositorDeCorreos.svelte';
  import ControlNodosDidacticos from '../../investigador/piezas/ControlNodosDidacticos.svelte';
  import BandejaDeReportes from '../../investigador/piezas/BandejaDeReportes.svelte';
  import ReportarProblema from './ReportarProblema.svelte';
  import PreferenciasDeNotificacion from './PreferenciasDeNotificacion.svelte';
  import * as datos from '../../nucleo/api/datos-personales.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';

  let mios = $state(null);
  let foto = $state(null);
  let cargando = $state(true);
  let fallo = $state(null);
  let pestanaActiva = $state('perfil');
  let visitadas = $state(['perfil']);
  $effect(() => { if (!visitadas.includes(pestanaActiva)) visitadas = [...visitadas, pestanaActiva]; });
  let movimientoReducido = $state(false);
  const pestanasProfesionales = [
    { id: 'perfil', titulo: 'Cuenta', icono: 'perfil' },
    { id: 'nodos', titulo: 'Nodos didácticos', icono: 'ajustes' },
    { id: 'comunicaciones', titulo: 'Comunicaciones', icono: 'correo' },
    { id: 'soporte', titulo: 'Soporte', icono: 'supervision' }
  ];
  let pestanas = $derived(sesion.rol === 'investigador'
    ? pestanasProfesionales
    : pestanasProfesionales.filter((item) => ['perfil', 'soporte'].includes(item.id)));

  async function cargar() {
    if (!sesion.autenticada) return;
    cargando = true;
    fallo = null;
    const [perfil, imagen] = await Promise.allSettled([
      datos.consultar(),
      datos.consultarFoto()
    ]);
    if (perfil.status === 'fulfilled') mios = perfil.value;
    else fallo = describir(perfil.reason);
    if (imagen.status === 'fulfilled') foto = imagen.value;
    cargando = false;
  }

  async function guardarFoto(archivo) {
    await datos.guardarFoto(archivo);
    if (foto) URL.revokeObjectURL(foto);
    foto = await datos.consultarFoto();
    globalThis.dispatchEvent?.(new CustomEvent('didaxia:foto-actualizada'));
  }

  async function retirarFoto() {
    await datos.retirarFoto();
    if (foto) URL.revokeObjectURL(foto);
    foto = null;
    globalThis.dispatchEvent?.(new CustomEvent('didaxia:foto-actualizada'));
  }

  $effect(() => {
    sesion.autenticada;
    cargar();
  });

  $effect(() => {
    const actual = foto;
    return () => { if (actual) URL.revokeObjectURL(actual); };
  });

  $effect(() => {
    if (sesion.rol !== 'investigador' && ['nodos', 'comunicaciones'].includes(pestanaActiva)) {
      pestanaActiva = 'perfil';
    }
  });

  onMount(() => {
    const consulta = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (!consulta) return;
    const actualizar = () => { movimientoReducido = consulta.matches; };
    actualizar();
    consulta.addEventListener?.('change', actualizar);
    return () => consulta.removeEventListener?.('change', actualizar);
  });
</script>

<PantallaDesplazable anchoMaximo="min(72rem, 100%)">
  <CabeceraDeRuta titulo="Mi perfil" icono="perfil-institucional" insignia="Cuenta institucional">
    {#snippet nota()}
      Tu identidad profesional y tu fotografía, visibles en los espacios de docencia e investigación.
    {/snippet}
  </CabeceraDeRuta>

  {#if sesion.autenticada}
    <PestanasSegmentadas opciones={pestanas} activa={pestanaActiva}
      alElegir={(id) => pestanaActiva = id} etiqueta="Secciones de mi perfil" prefijo="mi-perfil" />

    {#each visitadas as panel (panel)}
      <div
        id={`mi-perfil-panel-${panel}`}
        class="subpantalla"
        hidden={panel !== pestanaActiva}
        role="tabpanel"
        aria-labelledby={`mi-perfil-pestana-${panel}`}
        tabindex="0"
        in:fly={{ y: movimientoReducido ? 0 : 12, duration: movimientoReducido ? 0 : 210, easing: cubicOut }}
        out:fade={{ duration: movimientoReducido ? 0 : 90 }}>
        {#if panel === 'perfil'}
          <div class="encabezado-subpantalla">
            <span class="sobretitulo">Cuenta institucional</span>
            <h2>Perfil y cuenta</h2>
            <p>Tu identidad, la fotografía que eliges mostrar y los avisos que deseas recibir.</p>
          </div>
          {#if fallo}
            <Degradacion respuesta={fallo} alReintentar={cargar} />
          {:else if cargando}
            <CargadorCubo mensaje="Consultando tu perfil…" pantallaCompleta />
          {:else if mios}
            <PanelDeDatosPersonales
              {mios}
              perfil={mios.perfil ?? null}
              {foto}
              modoProfesional
              alGuardarFoto={guardarFoto}
              alRetirarFoto={retirarFoto} />
          {/if}
          <PreferenciasDeNotificacion />
          <section class="sesion-profesional" aria-labelledby="titulo-sesion">
            <div>
              <h3 id="titulo-sesion">Sesión profesional</h3>
              <p>Cierra esta sesión cuando termines de trabajar en un equipo compartido.</p>
            </div>
            <EntrarConGoogle />
          </section>
        {:else if panel === 'nodos' && sesion.rol === 'investigador'}
          <ControlNodosDidacticos />
        {:else if panel === 'comunicaciones' && sesion.rol === 'investigador'}
          <div class="encabezado-subpantalla">
            <span class="sobretitulo">Difusión institucional</span>
            <div class="titulo-subpantalla"><h2>Comunicaciones</h2><BotonAyudaTooltip texto="Prepara y envía mensajes desde el canal autorizado del equipo investigador. Los borradores se conservan mientras permaneces en Mi perfil, aunque cambies de pestaña; no se guardan en el navegador." /></div>
          </div>
          <CompositorDeCorreos />
        {:else if panel === 'soporte'}
          <div class="encabezado-subpantalla">
            <span class="sobretitulo">Ayuda y seguimiento</span>
            <div class="titulo-subpantalla"><h2>Soporte e incidencias</h2><BotonAyudaTooltip texto="Informa un problema y consulta su estado. El equipo investigador puede atender los reportes recibidos. Los cambios del seguimiento se aplican sólo al guardar." /></div>
          </div>
          {#if sesion.rol === 'investigador'}
            <div class="acciones-soporte"><ReportarProblema compacto /><details><summary>Mis reportes</summary><ReportarProblema /></details></div>
            <BandejaDeReportes />
          {:else}<ReportarProblema />{/if}
        {/if}
      </div>
    {/each}
  {/if}
</PantallaDesplazable>

<style>
  .subpantalla { display: grid; gap: 1.1rem; min-inline-size: 0; }
  .subpantalla[hidden] { display: none; }
  .titulo-subpantalla { display:flex; gap:.5rem; align-items:center; }
  .acciones-soporte { display:flex; flex-wrap:wrap; align-items:start; gap:.7rem; }
  .acciones-soporte details { flex:1; min-inline-size:0; }
  .acciones-soporte summary { padding:.55rem .7rem; border:1px solid var(--trazo); border-radius:var(--radius-sm); color:var(--ink-secondary); font-size:var(--texto-sm); cursor:pointer; min-block-size:2.6rem; }
  .acciones-soporte details[open] { flex-basis:100%; display:grid; gap:.7rem; }
  .subpantalla:focus-visible { outline: 3px solid var(--accent-main); outline-offset: 3px; border-radius: var(--radius-md); }
  .encabezado-subpantalla { display: grid; gap: .25rem; padding-inline: .15rem; }
  .sobretitulo { color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
  h2 { margin: 0; color: var(--ink-primary); font-size: var(--texto-xl); }
  .encabezado-subpantalla p { margin: 0; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .sesion-profesional {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem 1.1rem;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-lg);
    background: var(--surface-panel);
    box-shadow: var(--shadow-soft);
  }
  h3 { margin: 0; color: var(--ink-primary); font-size: var(--texto-md); }
  p { margin: .2rem 0 0; max-inline-size: none; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .sesion-profesional :global(.salir) { inline-size: auto; white-space: nowrap; }
  @media (max-width: 36rem) {
    .sesion-profesional { align-items: stretch; flex-direction: column; }
    .sesion-profesional :global(.salir) { inline-size: 100%; }
  }
</style>
