
<script>
  import ArchivoPreparado from './comun/estado/ArchivoPreparado.svelte';
  import { lectura } from './nucleo/lectura/lectura.svelte.js';
  import { onMount } from 'svelte';
  import { seguirVentanaVisible } from './nucleo/presentacion/ventanaVisible.js';
  import SaltarAlContenido from './comun/base/SaltarAlContenido.svelte';
  import Ajustes from './comun/preferencias/Ajustes.svelte';
  import Carril from './comun/armazon/Carril.svelte';
  import CabeceraGlobal from './comun/armazon/CabeceraGlobal.svelte';
  import ContenidoDeRuta from './comun/armazon/ContenidoDeRuta.svelte';
  import AvisoDeConsultaProfesional from './comun/estado/AvisoDeConsultaProfesional.svelte';
  import ContenedorDeToasts from './comun/estado/ContenedorDeToasts.svelte';
  import ContenedorDeConfirmaciones from './comun/estado/ContenedorDeConfirmaciones.svelte';
  import { esEstudiante } from './nucleo/sesion/rol.js';
  import { rutaDe, rutasDeZona, inicioDe } from './enrutado/rutas.js';
  import { resolver, arbolDe, navegar } from './enrutado/guardas.js';
  import { sesion } from './nucleo/sesion/sesion.svelte.js';
  import { espacio } from './nucleo/espacio/espacio.svelte.js';
  import { historial } from './nucleo/historial/historial.svelte.js';
  import { preferencias } from './nucleo/preferencias/preferencias.svelte.js';
  import { aplicarColores } from './nucleo/preferencias/colores.js';
  import { untrack } from 'svelte';

  let camino = $state(globalThis.location?.pathname ?? '/');
  let consulta = $state(globalThis.location?.search ?? '');
  let carrilAbierto = $state(false);
  let masAbierto = $state(false);
  let ajustesAbiertos = $state(false);
  onMount(() => {
    const raiz = document.getElementById('aplicacion');
    return raiz ? seguirVentanaVisible(raiz).destroy : undefined;
  });

  sesion.sincronizar();

  $effect(() => {
    if (sesion.autenticada && arbol === 'estudiante') {
      untrack(() => {
        historial.cargarLista();
        historial.recuperarSiHaceFalta();
      });
    }
  });

  $effect(() => {
    const alVolver = () => { camino = globalThis.location.pathname; consulta = globalThis.location.search; };
    globalThis.addEventListener('popstate', alVolver);
    return () => globalThis.removeEventListener('popstate', alVolver);
  });

  let sistemaOscuro = $state(
    globalThis.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  );

  const temaOscuro = $derived(
    preferencias.tema === 'oscuro' ||
    (preferencias.tema === 'sistema' && sistemaOscuro)
  );

  $effect(() => {
    const consulta = globalThis.matchMedia?.('(prefers-color-scheme: dark)');
    const alCambiar = () => { sistemaOscuro = Boolean(consulta?.matches); };
    consulta?.addEventListener('change', alCambiar);
    return () => consulta?.removeEventListener('change', alCambiar);
  });

  $effect(() => {
    globalThis.document?.body?.classList.toggle('dark-theme', temaOscuro);
    aplicarColores(preferencias.colores, temaOscuro);
  });

  $effect(() => {
    globalThis.document?.documentElement?.setAttribute('data-escala', preferencias.escalaTexto);
    globalThis.document?.documentElement?.setAttribute('data-animaciones', preferencias.animaciones ? 'si' : 'no');
  });

  const arbol = $derived(arbolDe(sesion.rol, espacio.activo));
  const inicio = $derived(inicioDe(sesion.rol, espacio.activo));
  const destino = $derived(resolver(camino, {
    rol: sesion.rol,
    espacio: espacio.activo,
    acceso: sesion.acceso,
    tutoriaAcademicaSinInvestigacion: sesion.tutoriaAcademicaSinInvestigacion,
    autenticada: sesion.autenticada
  }));

  $effect(() => {
    if (sesion.sincronizada && destino !== camino) {
      globalThis.history?.replaceState({}, '', destino);
      camino = destino;
    }
  });

  const ruta = $derived(rutaDe(destino));
  const principales = $derived(rutasDeZona(arbol, 'principal', sesion.rol, espacio.activo));
  const secundarias = $derived(rutasDeZona(arbol, 'pie', sesion.rol, espacio.activo));
  const perfilables = $derived(rutasDeZona(arbol, 'perfil', sesion.rol, espacio.activo));
  const perfilesDelCarril = $derived(espacio.puedeElegir
    ? rutasDeZona('no-estudiante', 'perfil', sesion.rol, 'profesional') : perfilables);
  const retenido = $derived(destino === '/consentimiento');

  const recursoPublicado = $derived(destino === '/notificaciones' || destino.startsWith('/notificaciones/'));
  const conCarril = $derived(arbol === 'estudiante' && !retenido && !recursoPublicado);

  const puedeNavegar = $derived(!retenido);

  const identidadEnCabecera = $derived(arbol !== 'estudiante');

  let tituloDeH1Visible = $state(true);

  $effect(() => {
    void destino;
    const main = globalThis.document?.getElementById('contenido');
    if (!main || typeof IntersectionObserver === 'undefined' || typeof MutationObserver === 'undefined') {
      tituloDeH1Visible = true;
      return;
    }

    let observadorInterseccion = null;

    function intentarObservarH1() {
      if (observadorInterseccion) return;
      const h1 = main.querySelector('h1');
      if (!h1) return;
      observadorInterseccion = new IntersectionObserver(
        ([entrada]) => { tituloDeH1Visible = entrada.isIntersecting; },
        { threshold: 0 }
      );
      observadorInterseccion.observe(h1);
      observadorMutacion.disconnect();
    }

    const observadorMutacion = new MutationObserver(intentarObservarH1);
    observadorMutacion.observe(main, { childList: true, subtree: true });
    intentarObservarH1();

    return () => {
      observadorMutacion.disconnect();
      observadorInterseccion?.disconnect();
    };
  });

  const mostrarTituloCabecera = $derived(!tituloDeH1Visible);

  const modoZen = $derived(
    destino === inicio && !preferencias.carrilVisible && !preferencias.panelVisible
  );

  $effect(() => {
    globalThis.document?.body?.classList.toggle('zen-mode', modoZen);
  });

  const navGlobal = $derived([
    ...principales.filter((r) =>
      arbol !== 'estudiante' || r.camino !== inicio
    ),
    ...secundarias
  ]);

  $effect(() => {
    if (!sesion.sincronizada || !espacio.esProfesional) return;
    espacio.recordarProfesional(destino + (globalThis.location?.search ?? ''));
  });

  function cambiarDeEspacio(nuevo) {
    if (nuevo === espacio.activo) return;
    navegar(espacio.destinoDe(nuevo), { alAceptar: () => {
      espacio.elegir(nuevo);
      carrilAbierto = false;
      masAbierto = false;
    } });
  }

  function abrirPerfilDelCarril(camino) {
    navegar(camino, { alAceptar: () => {
      if (espacio.puedeElegir) espacio.elegir('profesional');
      carrilAbierto = false;
      masAbierto = false;
    } });
  }

  function ir(destinoPedido) {
    navegar(destinoPedido, { alAceptar: () => {
      carrilAbierto = false;
      masAbierto = false;
      historial.volver();
    } });
  }
</script>

<SaltarAlContenido />

<div class="armazon">
  {#if conCarril && !lectura.inmersiva}
    <Carril {arbol} {inicio} {destino} perfilables={perfilesDelCarril} {navGlobal} {ir}
            irAlPerfil={abrirPerfilDelCarril}
            bind:carrilAbierto bind:ajustesAbiertos />
  {/if}

  <div class="trabajo">
    {#if !lectura.inmersiva}<CabeceraGlobal {arbol} rol={sesion.rol} {inicio} {destino} {ruta} {conCarril} {puedeNavegar} {identidadEnCabecera}
                    {mostrarTituloCabecera}
                    {navGlobal} {perfilables} {temaOscuro} {ir}
                    espacioActivo={espacio.activo}
                    puedeElegirEspacio={espacio.puedeElegir}
                    alElegirEspacio={cambiarDeEspacio}
                    bind:carrilAbierto bind:masAbierto bind:ajustesAbiertos />{/if}


    {#if sesion.autenticada && !esEstudiante(sesion.rol) && espacio.esTutor}
      <AvisoDeConsultaProfesional />
    {/if}

    <ContenidoDeRuta sincronizada={sesion.sincronizada} {ruta} {destino} {consulta} {arbol} {inicio} {ir} />
  </div>
</div>

<Ajustes bind:abierto={ajustesAbiertos} {arbol} {temaOscuro} />
<ContenedorDeToasts />
<ContenedorDeConfirmaciones />
<ArchivoPreparado />

<style>

  .armazon {
    flex: 1;
    min-block-size: 0;
    display: flex;
    height: 100%;
    overflow: hidden;
  }


  .trabajo {
    flex: 1;
    min-inline-size: 0;
    min-block-size: 0;
    display: flex;
    flex-direction: column;
    background: var(--surface-paper);
    position: relative;
    overflow: hidden;
    height: 100%;
  }

</style>
