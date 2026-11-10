<!-- Fase 7E · Ficha individual con actividad e indicios auditados. -->
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import { onMount } from 'svelte';
  import { cubicOut } from 'svelte/easing';
  import { fade, fly } from 'svelte/transition';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import CabeceraDeRuta from '../piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../piezas/PantallaDesplazable.svelte';
  import EstadoVacio from '../piezas/EstadoVacio.svelte';
  import DirectorioDeEstudiantes from '../piezas/DirectorioDeEstudiantes.svelte';
  import VectorConductual from '../piezas/VectorConductual.svelte';
  import TarjetaKPI from '../../comun/kpi/TarjetaKPI.svelte';
  import PerfilDeProporciones from '../../comun/kpi/PerfilDeProporciones.svelte';
  import { visibleEnTablero, factorPrincipal, ordenarFactores } from '../../comun/kpi/visibilidad.js';
  import ActividadDeClase from '../piezas/ActividadDeClase.svelte';
  import ReporteDeSesion from '../piezas/ReporteDeSesion.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import BotonExplicacion from '../../comun/base/BotonExplicacion.svelte';
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import PestanasSegmentadas from '../../comun/base/PestanasSegmentadas.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import Notacion from '../../comun/turno/Notacion.svelte';
  import * as api from '../../nucleo/api/clases.js';
  import { descargarPDF } from '../../nucleo/descargas/pdf.js';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { navegar } from '../../enrutado/navegar.js';
  import { CAMINOS } from '../../enrutado/caminos.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { untrack } from 'svelte';
  import {
    FACULTADES_ADMITIDAS,
    facultadAdmitida,
    programaAdmitido,
    programasDe
  } from '../../nucleo/configuracion/programas.js';

  function consulta() {
    if (typeof globalThis.location === 'undefined') return { clase: '', id: '' };
    const parametros = new URLSearchParams(globalThis.location.search);
    return { clase: parametros.get('clase') ?? '', id: parametros.get('id') ?? '' };
  }

  let destino = $state(consulta());
  let ficha = $state(null);
  let analitica = $state(null);
  let indicadoresAnteproyecto = $derived((analitica?.indicadores_anteproyecto ?? []).filter(visibleEnTablero));
  let indicadoresActividad = $derived((analitica?.indicadores_actividad ?? []).filter(visibleEnTablero));
  let fallo = $state(null);
  let cargando = $state(false);
  let noEncontrada = $state(false);
  let dias = $state(30);
  let mostrarAyuda = $state(false);
  let ayudaCobertura = $state(false);
  let descargandoFicha = $state(false);
  let errorDescargaFicha = $state('');
  let peticion = 0;
  let editando = $state(false);
  let guardandoPerfil = $state(false);
  let errorPerfil = $state('');
  let facultadEditada = $state('');
  let programaEditado = $state('');
  let semestreEditado = $state('');
  let rectificandoEdad = $state(false);
  let edadNueva = $state('');
  let motivoEdad = $state('');
  let guardandoEdad = $state(false);
  let errorEdad = $state('');
  let modoProyeccion = $state(false);
  let seccionEstudiantes = $state('directorio');
  let clasesDisponibles = $state([]);
  let claseComparativa = $state('');
  let cargandoClases = $state(false);
  let errorClases = $state('');
  let pestanaFicha = $state('actividad');
  let accionesAbiertas = $state(false);
  let movimientoReducido = $state(false);
  const pestanasFicha = [
    { id: 'actividad', titulo: 'Actividad', icono: 'analitica' },
    { id: 'fenomenos', titulo: 'Fenómenos', icono: 'evidencias' },
    { id: 'validez', titulo: 'Validez', icono: 'grafica' },
    { id: 'expediente', titulo: 'Expediente', icono: 'escudo' }
  ];

  onMount(() => {
    const consulta = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (!consulta) return;
    const actualizar = () => { movimientoReducido = consulta.matches; };
    actualizar();
    consulta.addEventListener?.('change', actualizar);
    return () => consulta.removeEventListener?.('change', actualizar);
  });

  $effect(() => {
    const alVolver = () => { destino = consulta(); };
    globalThis.addEventListener('popstate', alVolver);
    return () => globalThis.removeEventListener('popstate', alVolver);
  });

  async function cargar() {
    const { clase, id } = destino;
    if (!clase || !id) return;
    const actual = ++peticion;
    fallo = null;
    noEncontrada = false;
    cargando = true;
    try {
      const hasta = new Date();
      const desde = new Date(hasta.getTime() - dias * 86400000);
      const opciones = { desde: desde.toISOString(), hasta: hasta.toISOString() };
      const [identidad, actividad] = sesion.rol === 'investigador'
        ? await Promise.all([
            Promise.resolve(null), api.fichaInstitucional(clase, id, opciones)
          ])
        : await Promise.all([
            api.ficha(clase, id), api.analiticaDeIntegrante(clase, id, opciones)
          ]);
      if (actual === peticion) {
        ficha = identidad ?? { clase: actividad.clase, estudiante: actividad.estudiante };
        analitica = actividad;
      }
    } catch (e) {
      if (actual !== peticion) return;
      const descrito = describir(e);
      ficha = null;
      analitica = null;
      if (descrito?.codigo === 404 || e?.codigo === 404 || e?.estado === 404) {
        noEncontrada = true;
      } else {
        fallo = descrito;
      }
    } finally {
      if (actual === peticion) cargando = false;
    }
  }

  async function descargarFicha() {
    if (!analitica || descargandoFicha) return;
    if (!await confirmarAccion({ tipo:'descarga', titulo:'¿Descargar ficha pedagógica?',
      descripcion:`Se generará el PDF de ${estudiante?.nombre ?? 'este estudiante'} con actividad, fenómenos observados y cobertura de evidencia del periodo consultado.`, confirmar:'Descargar PDF' })) return;
    descargandoFicha = true;
    errorDescargaFicha = '';
    try {
      const documento = await api.pdfDeFichaIndividual(
        destino.clase, destino.id, sesion.rol,
        { desde: analitica.periodo.desde, hasta: analitica.periodo.hasta }
      );
      descargarPDF(documento, `didaxia-ficha-${destino.clase}.pdf`);
      toast.descarga('Descargando ficha pedagógica en PDF.');
    } catch (error) {
      errorDescargaFicha = describir(error)?.mensaje ?? 'No se pudo descargar la ficha.';
    } finally {
      descargandoFicha = false;
    }
  }

  async function cargarClasesDisponibles() {
    if (!mostrandoDirectorio || cargandoClases) return;
    cargandoClases = true;
    errorClases = '';
    try {
      clasesDisponibles = sesion.rol === 'investigador'
        ? await api.clasesInstitucionales()
        : await api.mias();
      if (!claseComparativa || !clasesDisponibles.some((item) => item.id === claseComparativa)) {
        claseComparativa = clasesDisponibles[0]?.id ?? '';
      }
    } catch (e) {
      errorClases = describir(e)?.mensaje ?? 'No se pudieron consultar las clases.';
    } finally {
      cargandoClases = false;
    }
  }

  $effect(() => { void destino; void dias; cargar(); });

  $effect(() => {
    void mostrandoDirectorio;
    void sesion.rol;
    // La lectura de `cargandoClases` vive dentro de la función. No debe
    // convertirse en dependencia del efecto: si lo hace, cada finalización
    // inicia otra consulta y el selector permanece deshabilitado a intervalos.
    if (mostrandoDirectorio) untrack(() => { void cargarClasesDisponibles(); });
  });

  const estudiante = $derived(ficha?.estudiante ?? null);
  const clase = $derived(ficha?.clase ?? null);
  const mostrandoDirectorio = $derived(!destino.clase || !destino.id);
  const actividad = $derived(analitica?.actividad ?? {});
  const respuesta = $derived(analitica?.respuesta ?? {});
  const coberturaEvidencia = $derived(analitica?.cobertura_evidencia ?? null);
  const vector = $derived({
    motivo: analitica?.indicios_conductuales?.motivo,
    componentes: analitica?.indicios_conductuales?.componentes,
    observables: analitica?.indicios_conductuales?.observables ?? [],
    periodo: analitica?.periodo,
    rasgos: Object.fromEntries(
      (analitica?.indicios_conductuales?.componentes ?? []).map((item) => [
        item.clave_origen, item.valor
      ])
    ),
    confianza: analitica?.indicios_conductuales?.confianza_calibrada ?? null,
    observaciones: analitica?.indicios_conductuales?.observaciones ?? null
  });
  const cifras = $derived([
    { rotulo: 'Turnos', valor: actividad.turnos_registrados ?? 0, icono: 'conversacion' },
    { rotulo: 'Conversaciones', valor: actividad.conversaciones ?? 0, icono: 'historial' },
    { rotulo: 'Días con actividad', valor: actividad.dias_con_actividad ?? 0, icono: 'grafica' },
    { rotulo: 'Sin fuente', valor: respuesta.sin_fuente ?? 0, icono: 'biblioteca' }
  ]);

  function inicial(nombre) {
    return String(nombre || 'E').trim().charAt(0).toLocaleUpperCase('es');
  }
  function fechaLegible(valor, conHora = false) {
    const fecha = new Date(valor);
    if (Number.isNaN(fecha.getTime())) return 'Fecha no disponible';
    return new Intl.DateTimeFormat('es-CO', {
      day: 'numeric', month: 'short', year: 'numeric',
      ...(conHora ? { hour: 'numeric', minute: '2-digit' } : {})
    }).format(fecha);
  }

  function abrirEdicion() {
    facultadEditada = estudiante?.facultad ?? '';
    programaEditado = estudiante?.programa ?? '';
    semestreEditado = estudiante?.semestre == null ? '' : String(estudiante.semestre);
    errorPerfil = '';
    editando = true;
  }

  function abrirDesdeDirectorio(persona) {
    navegar(`${CAMINOS.estudiante}?clase=${encodeURIComponent(persona.clase.id)}&id=${encodeURIComponent(persona.identificador)}`);
  }

  async function guardarPerfil() {
    const facultad = String(facultadEditada ?? '').trim();
    const programa = String(programaEditado ?? '').trim();
    const semestre = Number(semestreEditado);
    if (!facultadAdmitida(facultad) || !programaAdmitido(programa, facultad)) {
      errorPerfil = 'Selecciona una facultad y uno de sus programas.';
      return;
    }
    if (!Number.isInteger(semestre) || semestre < 1 || semestre > 20) {
      errorPerfil = 'El semestre debe ser un número entre 1 y 20.';
      return;
    }
    guardandoPerfil = true;
    errorPerfil = '';
    try {
      const funcion = sesion.rol === 'investigador'
        ? api.corregirPerfilInstitucional
        : api.corregirPerfil;
      await funcion(destino.clase, destino.id, { facultad, programa, semestre });
      editando = false;
      await cargar();
      toast.exito('Perfil académico corregido.');
    } catch (e) {
      errorPerfil = describir(e)?.mensaje ?? 'No se pudo guardar la corrección.';
    } finally {
      guardandoPerfil = false;
    }
  }

  function abrirRectificacionEdad() {
    edadNueva = estudiante?.edad == null ? '' : String(estudiante.edad);
    motivoEdad = '';
    errorEdad = '';
    rectificandoEdad = true;
  }

  async function guardarRectificacionEdad() {
    const edad = Number(edadNueva);
    const motivo = motivoEdad.trim();
    if (!Number.isInteger(edad) || edad < 0 || edad > 120) {
      errorEdad = 'La edad debe ser un número entero entre 0 y 120.';
      return;
    }
    if (motivo.length < 8) {
      errorEdad = 'Explica el motivo en al menos 8 caracteres.';
      return;
    }
    guardandoEdad = true;
    errorEdad = '';
    try {
      await api.rectificarEdad(destino.clase, destino.id, edad, motivo);
      rectificandoEdad = false;
      await cargar();
      toast.exito('Rectificación de edad registrada.');
    } catch (e) {
      errorEdad = describir(e)?.mensaje ?? 'No se pudo registrar la rectificación.';
    } finally {
      guardandoEdad = false;
    }
  }

  $effect(() => {
    if (programaEditado && !programasDe(facultadEditada).includes(programaEditado)) {
      programaEditado = '';
    }
  });
</script>

<PantallaDesplazable anchoMaximo="min(78rem, 100%)">
  <CabeceraDeRuta titulo={mostrandoDirectorio ? 'Estudiantes' : estudiante?.nombre ?? 'Ficha de estudiante'}
                  icono="estudiante"
                  insignia={mostrandoDirectorio
                    ? ({ directorio: 'Directorio', ranking: 'Ranking de actividad', estadisticas: 'Estadísticas de uso', reporte: 'Reporte de sesión' }[seccionEstudiantes])
                    : clase?.nombre || 'Ficha individual'}>
    {#snippet nota()}
      {mostrandoDirectorio
        ? 'Consulta el directorio, compara la actividad por clase o revisa sus estadísticas sin entrar a una ficha individual.'
        : 'Seguimiento individual dentro de la clase seleccionada y el periodo elegido.'}
    {/snippet}
    {#snippet accion()}
      {#if !mostrandoDirectorio}
        <label class="periodo"><span>Periodo</span><select use:menuDesplegable={dias} bind:value={dias}>
          <option value={7}>7 días</option><option value={30}>30 días</option><option value={90}>90 días</option>
        </select></label>
        <Boton variante="secundario" onclick={() => navegar(CAMINOS.estudiante)}>
          <Icono nombre="flecha-izq" medida={14} /><span>Todos los estudiantes</span>
        </Boton>
      {/if}
    {/snippet}
  </CabeceraDeRuta>

  {#if fallo}<Degradacion respuesta={fallo} alReintentar={cargar} />{/if}
  {#if mostrandoDirectorio}
    <div class="subpantallas" role="tablist" aria-label="Vistas de estudiantes">
      {#if sesion.rol === 'investigador'}
        <button type="button" onclick={() => navegar(CAMINOS.conversacionesInvestigacion)}>
          Conversaciones
        </button>
      {/if}
      <button type="button" role="tab" aria-selected={seccionEstudiantes === 'directorio'}
              class:activa={seccionEstudiantes === 'directorio'} onclick={() => (seccionEstudiantes = 'directorio')}>
        Directorio
      </button>
      <button type="button" role="tab" aria-selected={seccionEstudiantes === 'ranking'}
              class:activa={seccionEstudiantes === 'ranking'} onclick={() => (seccionEstudiantes = 'ranking')}>
        Ranking de actividad
      </button>
      <button type="button" role="tab" aria-selected={seccionEstudiantes === 'estadisticas'}
              class:activa={seccionEstudiantes === 'estadisticas'} onclick={() => (seccionEstudiantes = 'estadisticas')}>
        Estadísticas de uso
      </button>
      <button type="button" role="tab" aria-selected={seccionEstudiantes === 'reporte'}
              class:activa={seccionEstudiantes === 'reporte'} onclick={() => (seccionEstudiantes = 'reporte')}>
        Reporte de sesión
      </button>
    </div>

    {#if seccionEstudiantes === 'directorio'}
      <DirectorioDeEstudiantes rol={sesion.rol} alElegir={abrirDesdeDirectorio} />
    {:else}
      <section class="selector-clase" aria-labelledby="selector-clase-titulo">
        <div>
          <span>COMPARACIÓN POR CLASE</span>
          <h2 id="selector-clase-titulo">Elige la clase de cálculo</h2>
        </div>
        <label>Clase
          <select use:menuDesplegable={claseComparativa} bind:value={claseComparativa} disabled={!clasesDisponibles.length}>
            {#each clasesDisponibles as opcion (opcion.id)}
              <option value={opcion.id}>{opcion.nombre}</option>
            {/each}
          </select>
        </label>
      </section>
      {#if errorClases}<p class="error-clases" role="alert">{errorClases}</p>{/if}
      {#if cargandoClases && !clasesDisponibles.length}
        <CargadorCubo mensaje="Consultando las clases disponibles…" compacto />
      {:else if claseComparativa}
        {#if seccionEstudiantes === 'reporte'}
          <ReporteDeSesion clase={claseComparativa} rol={sesion.rol} />
        {:else}
          <ActividadDeClase
            clase={claseComparativa}
            rol={sesion.rol}
            vista={seccionEstudiantes}
            alElegir={abrirDesdeDirectorio}
            bind:proyectar={modoProyeccion}
          />
        {/if}
      {:else if !errorClases}
        <EstadoVacio icono="clase" tono="neutro" titulo="Todavía no hay clases"
          texto="Crea o registra una clase para poder comparar la actividad de sus estudiantes." />
      {/if}
    {/if}
  {:else if cargando && !ficha}
    <CargadorCubo mensaje="Preparando la ficha…" pantallaCompleta />
  {:else if noEncontrada}
    <EstadoVacio icono="estudiante" tono="neutro" titulo="No encontramos esta ficha"
      texto="La clase puede no ser tuya, o esa persona ya no está matriculada en ella." />
  {:else if estudiante}
    <section class="identidad" aria-labelledby="identidad-titulo">
      <span class="avatar" aria-hidden="true">
        <span>{inicial(estudiante.nombre)}</span>
        {#if ['docente', 'investigador'].includes(sesion.rol) && estudiante.tiene_foto && destino.clase && estudiante.identificador}
          <img src={api.fotoDeIntegrante(destino.clase, estudiante.identificador)} alt=""
               onerror={(evento) => evento.currentTarget.remove()} />
        {/if}
      </span>
      <div class="datos">
        <span class="sobrelinea">SEGUIMIENTO DE LA CLASE</span>
        <h2 id="identidad-titulo">{estudiante.nombre}</h2>
        <p><Icono nombre="check" medida={13} /> Matriculado desde el
          <time datetime={estudiante.desde}>{fechaLegible(estudiante.desde)}</time>
        </p>
        <p class="trayectoria">
          <Icono nombre="clases" medida={13} />
          {estudiante.facultad || 'Facultad pendiente'} ·
          {estudiante.programa || 'Programa pendiente'} ·
          {estudiante.semestre ? `Semestre ${estudiante.semestre}` : 'Semestre pendiente'}
        </p>
      </div>
      <div class="acciones-ficha">
        <button class="editar accion-principal" type="button" onclick={descargarFicha} disabled={descargandoFicha || !analitica}
                aria-label="Descargar ficha individual PDF">
          <Icono nombre="descargar" medida={15} /> <span>{descargandoFicha ? 'Generando…' : 'Descargar PDF'}</span>
        </button>
        <div class="grupo-acciones">
          <button class="editar" type="button" aria-expanded={accionesAbiertas} aria-controls="menu-acciones-ficha"
                  onclick={() => accionesAbiertas = !accionesAbiertas}>
            <Icono nombre="mas" medida={15} /> <span>Acciones</span>
          </button>
          {#if accionesAbiertas}
            <div id="menu-acciones-ficha" class="menu-acciones">
              <button type="button" onclick={() => { accionesAbiertas = false; abrirEdicion(); }}>Corregir perfil académico</button>
              {#if sesion.rol === 'investigador'}
                <button type="button" onclick={() => { accionesAbiertas = false; abrirRectificacionEdad(); }}>Rectificar edad declarada</button>
              {/if}
              <button type="button" onclick={() => { accionesAbiertas = false; mostrarAyuda = !mostrarAyuda; }}>Cómo interpretar esta ficha</button>
            </div>
          {/if}
        </div>
      </div>
    </section>

    {#if errorDescargaFicha}<p role="alert">{errorDescargaFicha}</p>{/if}

    {#if mostrarAyuda}
      <aside class="explicacion">
        <strong>Cómo leer esta ficha</strong>
        <p>Resume actividad observada en el Tutor durante el periodo elegido. Los indicios se derivan del lenguaje y pueden equivocarse: orientan el acompañamiento, no son un diagnóstico ni una calificación. Las consultas profesionales quedan excluidas.</p>
      </aside>
    {/if}

    <PestanasSegmentadas opciones={pestanasFicha} activa={pestanaFicha}
      alElegir={(id) => pestanaFicha = id} etiqueta="Secciones de la ficha individual" prefijo="ficha" />

    {#key pestanaFicha}
      <div id={`ficha-panel-${pestanaFicha}`} class="contenido-pestana" role="tabpanel"
        aria-labelledby={`ficha-pestana-${pestanaFicha}`} tabindex="0"
        in:fly={{ y: movimientoReducido ? 0 : 8, duration: movimientoReducido ? 0 : 180, easing: cubicOut }}
        out:fade={{ duration: movimientoReducido ? 0 : 90 }}>
      {#if pestanaFicha === 'actividad'}
    <div class="cifras">
      {#each cifras as cifra (cifra.rotulo)}
        <article><span><Icono nombre={cifra.icono} medida={17} /></span><div><strong>{cifra.valor}</strong><small>{cifra.rotulo}</small></div></article>
      {/each}
    </div>

    <section class="panel" aria-labelledby="conversaciones-titulo">
      <header><div><span>ACTIVIDAD RECIENTE</span><h3 id="conversaciones-titulo">Conversaciones</h3></div><small>Sin mostrar el texto</small></header>
      <ul>
        {#each analitica?.conversaciones ?? [] as conversacion (conversacion.sesion)}
          <li><span class="icono-hilo"><Icono nombre="conversacion" medida={15} /></span><div><strong>{fechaLegible(conversacion.ultimo, true)}</strong><small>{conversacion.turnos} turno{conversacion.turnos === 1 ? '' : 's'}</small></div></li>
        {:else}
          <li class="vacio">Todavía no hay conversaciones en este periodo.</li>
        {/each}
      </ul>
    </section>

    {#if indicadoresActividad.length}
      <section class="panel" aria-label="KPI de la actividad individual">
        <header><div><span>ACTIVIDAD INDIVIDUAL</span><h3>Indicadores observables</h3></div></header>
        <PerfilDeProporciones indicadores={indicadoresActividad} />
        <div class="indicadores-individuales">
          {#each indicadoresActividad as indicador (indicador.codigo)}
            <TarjetaKPI {indicador} />
          {/each}
        </div>
      </section>
    {/if}

      {:else if pestanaFicha === 'fenomenos'}
    <p class="instrumento-prototipo"><strong>Instrumento-Prototipo</strong> · Método e interpretación en la explicación de cada indicador.</p>
    <section class="panel" aria-labelledby="anteproyecto-titulo">
      <header><div><span>INSTRUMENTO-PROTOTIPO</span><h3 id="anteproyecto-titulo">Fenómenos e indicadores observables del diálogo</h3></div></header>
      <p>Frecuencias y secuencias observadas en este periodo; abre el botón de expansión para conocer cada cálculo.</p>
      {#if indicadoresAnteproyecto.length}
        <PerfilDeProporciones indicadores={indicadoresAnteproyecto} />
        <div class="indicadores-individuales">
          <div class="principales" aria-label="Factores principales del estudio">
            {#each ordenarFactores(indicadoresAnteproyecto).filter(item => factorPrincipal(item, indicadoresAnteproyecto)) as indicador (indicador.codigo)}
              <TarjetaKPI {indicador} principal={factorPrincipal(indicador, indicadoresAnteproyecto)} />
            {/each}
          </div>
          {#each indicadoresAnteproyecto.filter(item => !factorPrincipal(item, indicadoresAnteproyecto)) as indicador (indicador.codigo)}
            <TarjetaKPI {indicador} />
          {/each}
        </div>
      {:else}<p class="vacio">{analitica?.indicios_conductuales?.motivo ?? 'No hay oportunidades verificables para estos fenómenos en el periodo seleccionado.'}</p>{/if}
    </section>
    <VectorConductual {vector} />

      {:else if pestanaFicha === 'validez'}

    <section class="panel cobertura-evidencia" aria-labelledby="cobertura-evidencia-titulo">
      <header>
        <div><span>MEDIDA DE APOYO</span><h3 id="cobertura-evidencia-titulo">Cobertura de evidencia de la estimación <BotonAyudaTooltip tamano="sm" posicion="abajo" texto="Resume cuánta evidencia observable alimenta esta estimación. Es una heurística experimental: no calibra una probabilidad de acierto ni permite diagnosticar al estudiante." ariaLabel="Qué significa cobertura de evidencia" /></h3></div>
        <BotonExplicacion etiqueta="Explicar cobertura de evidencia" abierto={ayudaCobertura} alAbrir={() => ayudaCobertura = true} texto="Abre la fórmula ponderada, sus pesos, un ejemplo y los límites de la cobertura de evidencia." />
      </header>
      <div class="contenido-cobertura">
        {#if coberturaEvidencia?.estado === 'disponible'}
          <p class="valor-cobertura"><strong>{Math.round(coberturaEvidencia.valor * 100)}%</strong><span>de cobertura observable</span></p>
        {:else}
          <p class="sin-cobertura"><strong>Evidencia insuficiente</strong><span>Se requieren al menos 5 turnos, 2 conversaciones y 2 días activos.</span></p>
        {/if}
        <p>{coberturaEvidencia?.interpretacion ?? 'La medida todavía no está disponible para esta ficha.'}</p>
        {#if coberturaEvidencia}
          <Dialogo bind:abierto={ayudaCobertura} titulo="Cobertura de evidencia: fórmula e interpretación" ancho="42rem">
            <div class="formula-cobertura">
              <strong>Fórmula</strong>
              <Notacion
                expresion={coberturaEvidencia.formula_latex ?? coberturaEvidencia.formula}
                alternativo="Fórmula ponderada de cobertura de evidencia"
                bloque
                compacto
              />
            </div>
            <p><strong>Pesos:</strong> turnos 30%, conversaciones 20%, días activos 15%, datos válidos 20% y recencia 15%.</p>
            <p>Turnos: se satura a 15. Conversaciones: a 4. Días activos: a 5. Datos válidos: respuestas sin degradación ni falta de fuente, divididas por respuestas registradas. Recencia: 1 hasta 7 días, 0,5 entre más de 7 y 14 días y 0 después de 14; se mide respecto al final del periodo.</p>
            <p><strong>Ejemplo:</strong> 15 turnos, 4 conversaciones, 5 días activos, 8 de 10 respuestas válidas y actividad hace 3 días: 0,30 + 0,20 + 0,15 + 0,16 + 0,15 = 0,96 (96%).</p>
            <p>Alto significa mayor cobertura según esta heurística; bajo, menos evidencia observable. Ausente significa que no cumple los mínimos. No es confianza calibrada: una respuesta con fuente puede ser incorrecta y una conversación extensa puede contener errores.</p>
            <ul class="limitaciones">
              {#each coberturaEvidencia.limitaciones ?? [] as limitacion}<li>{limitacion}</li>{/each}
            </ul>
          </Dialogo>
        {/if}
      </div>
    </section>

      {:else if pestanaFicha === 'expediente'}
    <section class="panel expediente" aria-labelledby="expediente-titulo">
      <header><div><span>REGISTRO INSTITUCIONAL</span><h3 id="expediente-titulo">Matrícula en la clase</h3></div></header>
      <div class="datos-expediente">
        <p><strong>Clase</strong><span>{clase?.nombre ?? 'Clase no disponible'}</span></p>
        <p><strong>Desde</strong><span>{fechaLegible(estudiante.desde)}</span></p>
        <p><strong>Programa</strong><span>{estudiante.programa || 'Pendiente'}</span></p>
        <p><strong>Semestre</strong><span>{estudiante.semestre ?? 'Pendiente'}</span></p>
      </div>
    </section>
    <aside class="explicacion">
      <strong>Consentimiento y acceso</strong>
      <BotonAyudaTooltip tamano="sm" ariaLabel="Cómo se protege el acceso a esta ficha" texto="Esta ficha solo presenta información autorizada para tu rol. El estado documental del consentimiento no se expone aquí; las rectificaciones de edad requieren revisión del régimen aplicable." />
    </aside>
    {#if sesion.rol === 'investigador'}
      <section class="panel rectificaciones" aria-labelledby="rectificaciones-titulo">
        <header><div><span>TRÁMITE HISTÓRICO</span><h3 id="rectificaciones-titulo">Rectificaciones de edad</h3></div><small>Edad vigente: {estudiante.edad ?? 'sin declarar'}</small></header>
        <button class="editar" type="button" onclick={abrirRectificacionEdad}><Icono nombre="editar" medida={15} /> Rectificar edad declarada</button>
        <p class="nota-edicion">Si la edad vigente ya es correcta, no vuelvas a rectificarla. Un cambio entre minoría y mayoría de edad requiere que el estudiante entre a Mi cuenta → Autorizaciones y complete de nuevo su decisión. El investigador corrige el dato; la autorización la registra el estudiante.</p>
        <ul>{#each analitica?.rectificaciones_edad ?? [] as rectificacion (rectificacion.id)}
          <li><div><strong>{rectificacion.valor_anterior} → {rectificacion.valor_nuevo} años · {rectificacion.estado.replaceAll('_', ' ')}</strong><small>{fechaLegible(rectificacion.registrada_en, true)} · {rectificacion.motivo}</small>{#if rectificacion.reconsentimiento_necesario}<small>Exige un nuevo consentimiento por cambio de categoría de edad.</small>{/if}</div></li>
        {:else}<li class="vacio">No hay rectificaciones de edad registradas.</li>{/each}</ul>
      </section>
    {/if}
      {/if}
      </div>
    {/key}
  {/if}
</PantallaDesplazable>

<Dialogo bind:abierto={editando} tipo="confirmar" titulo="Corregir perfil académico">
  <p class="nota-edicion">
    Esta corrección queda auditada. Nombre, correo y edad no se cambian aquí;
    la edad altera el régimen de consentimiento y requiere otro procedimiento.
  </p>
  <div class="formulario-perfil">
    <label>Facultad
      <select use:menuDesplegable={facultadEditada} bind:value={facultadEditada}>
        <option value="" disabled>Selecciona una facultad</option>
        {#each FACULTADES_ADMITIDAS as opcion}<option value={opcion}>{opcion}</option>{/each}
      </select>
    </label>
    <label>Programa
      <select use:menuDesplegable={programaEditado} bind:value={programaEditado} disabled={!facultadEditada}>
        <option value="" disabled>Selecciona un programa</option>
        {#each programasDe(facultadEditada) as opcion}<option value={opcion}>{opcion}</option>{/each}
      </select>
    </label>
    <label>Semestre
      <input type="number" min="1" max="20" bind:value={semestreEditado} />
    </label>
  </div>
  {#if errorPerfil}<p class="error-perfil" role="alert">{errorPerfil}</p>{/if}
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (editando = false)} deshabilitado={guardandoPerfil}>Cancelar</Boton>
    <Boton onclick={guardarPerfil} deshabilitado={guardandoPerfil}>
      {guardandoPerfil ? 'Guardando…' : 'Guardar corrección'}
    </Boton>
  {/snippet}
</Dialogo>

<Dialogo bind:abierto={rectificandoEdad} tipo="confirmar" titulo="Rectificar edad declarada" bloqueado={guardandoEdad}>
  <p class="nota-edicion">La edad anterior no se sobrescribe en la historia. Si cambia entre minoría y mayoría de edad, el sistema exigirá reconsentimiento para investigación, pero conservará la tutoría académica sin incluirla en KPI, perfiles o exportaciones de estudio.</p>
  <div class="formulario-perfil">
    <label>Edad nueva
      <input type="number" min="0" max="120" bind:value={edadNueva} />
    </label>
    <label>Motivo de la rectificación
      <textarea rows="4" maxlength="500" bind:value={motivoEdad} placeholder="Describe la evidencia o solicitud que justifica el cambio"></textarea>
    </label>
  </div>
  {#if errorEdad}<p class="error-perfil" role="alert">{errorEdad}</p>{/if}
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (rectificandoEdad = false)} deshabilitado={guardandoEdad}>Cancelar</Boton>
    <Boton onclick={guardarRectificacionEdad} deshabilitado={guardandoEdad}>{guardandoEdad ? 'Registrando…' : 'Registrar rectificación'}</Boton>
  {/snippet}
</Dialogo>

<style>
  .principales { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(auto-fit, minmax(min(18rem, 100%), 1fr)); gap: .8rem; }
  .instrumento-prototipo { margin: 0; color: var(--ink-tertiary); font-size: var(--texto-xs); line-height: 1.5; }
  .contenido-pestana { display: grid; gap: 1rem; min-inline-size: 0; }
  .contenido-pestana:focus-visible { outline: 3px solid var(--accent-main); outline-offset: 3px; border-radius: var(--radius-md); }
  .contenido-pestana > * { min-inline-size: 0; }
  .datos-expediente { display: grid; gap: 0; padding: .35rem 1rem; }
  .datos-expediente p { display: flex; justify-content: space-between; gap: 1rem; margin: 0; padding: .7rem 0; border-block-end: 1px solid var(--trazo-suave); color: var(--ink-secondary); font-size: var(--texto-sm); overflow-wrap: anywhere; }
  .datos-expediente p:last-child { border-block-end: 0; }
  .datos-expediente strong { flex: none; color: var(--ink-primary); }
  .datos-expediente span { min-inline-size: 0; text-align: end; }
  .instrumento-prototipo strong { color: var(--ink-secondary); }
  .indicadores-individuales { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(18rem, 100%), 1fr)); gap: .8rem; }
  .subpantallas { display: flex; flex-wrap: wrap; gap: .45rem; padding: .3rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-panel); }
  .subpantallas button { min-block-size: 2.55rem; padding: .45rem .8rem; border: 1px solid transparent; border-radius: var(--radius-sm); background: transparent; color: var(--ink-secondary); font: inherit; font-size: var(--texto-sm); font-weight: 750; cursor: pointer; }
  .subpantallas button:hover, .subpantallas button:focus-visible { color: var(--accent-main); border-color: var(--trazo-suave); }
  .subpantallas button.activa { background: var(--accent-main); color: var(--accent-on-main); }
  .selector-clase { display: flex; align-items: end; justify-content: space-between; gap: 1rem; padding: .9rem 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); }
  .selector-clase span { color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; letter-spacing: .08em; }
  .selector-clase h2 { margin: .15rem 0 0; font-size: var(--texto-md); }
  .selector-clase label { display: grid; gap: .25rem; min-inline-size: min(24rem, 100%); color: var(--ink-secondary); font-size: var(--texto-xs); font-weight: 750; }
  .error-clases { margin: 0; padding: .75rem; border-radius: var(--radius-sm); background: var(--semantic-error-bg); color: var(--semantic-error); }
  .periodo { display: grid; gap: .2rem; color: var(--ink-tertiary); font-size: var(--texto-xs); font-weight: 700; }
  select { min-block-size: 2.35rem; padding: .4rem .75rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); }
  .identidad { position: relative; display: flex; align-items: center; gap: 1rem; min-inline-size: 0; padding: 1.15rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: linear-gradient(135deg, var(--surface-paper), var(--surface-panel)); box-shadow: var(--shadow-soft); }
  .avatar { position: relative; display: grid; place-items: center; flex: 0 0 72px; aspect-ratio: 1; overflow: hidden; border: 2px solid var(--accent-main); border-radius: 50%; background: var(--accent-surface); color: var(--accent-main); font-size: var(--texto-lg); font-weight: 800; }
  .avatar img { position: absolute; inset: 0; inline-size: 100%; block-size: 100%; object-fit: cover; }
  .datos { display: grid; gap: .28rem; min-inline-size: 0; }
  .datos h2 { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sobrelinea { color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; letter-spacing: .08em; }
  h2, h3 { margin: 0; color: var(--ink-primary); }
  h2 { font-size: var(--texto-xl); } h3 { font-size: var(--texto-md); }
  .datos p { display: flex; align-items: center; gap: .35rem; min-inline-size: 0; margin: 0; color: var(--ink-secondary); font-size: var(--texto-sm); overflow-wrap: anywhere; }
  .trayectoria { flex-wrap: wrap; }
  .acciones-ficha { display: flex; align-self: flex-start; flex: none; gap: .45rem; margin-inline-start: auto; }
  .grupo-acciones { position: relative; }
  .menu-acciones { position: absolute; z-index: 8; inset-block-start: calc(100% + .35rem); inset-inline-end: 0; display: grid; gap: .15rem; min-inline-size: min(17rem, calc(100vw - 2rem)); padding: .35rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); box-shadow: var(--shadow-soft); }
  .menu-acciones button { min-block-size: 2.75rem; padding: .55rem .7rem; border: 0; border-radius: var(--radius-sm); background: transparent; color: var(--ink-primary); font: inherit; font-size: var(--texto-sm); text-align: start; cursor: pointer; }
  .menu-acciones button:hover { background: var(--surface-panel); }
  .menu-acciones button:focus-visible { outline: 3px solid var(--accent-main); outline-offset: 1px; }
  .editar { display: inline-flex; align-items: center; gap: .35rem; min-block-size: 2rem; padding: .3rem .6rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-secondary); font: inherit; font-size: var(--texto-xs); font-weight: 700; cursor: pointer; }
  .editar:hover { border-color: var(--accent-main); color: var(--accent-main); }
  .explicacion { padding: .9rem 1rem; border-inline-start: 3px solid var(--accent-main); border-radius: var(--radius-sm); background: var(--accent-surface); color: var(--ink-secondary); font-size: var(--texto-sm); }
  .explicacion p { margin: .25rem 0 0; max-inline-size: 75ch; }
  .cifras { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .75rem; }
  .cifras article { display: flex; align-items: center; gap: .7rem; padding: .9rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); box-shadow: var(--shadow-soft); }
  .cifras article > span, .icono-hilo { display: grid; place-items: center; inline-size: 2.2rem; block-size: 2.2rem; border-radius: 50%; background: var(--accent-surface); color: var(--accent-main); }
  .cifras article div { display: grid; } .cifras strong { color: var(--ink-primary); font-size: var(--texto-lg); } .cifras small { color: var(--ink-tertiary); }
  .contenido-cobertura { display: grid; gap: .55rem; padding: 1rem; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .contenido-cobertura p { margin: 0; max-inline-size: 85ch; }
  .valor-cobertura, .sin-cobertura { display: flex; align-items: baseline; flex-wrap: wrap; gap: .45rem; }
  .valor-cobertura strong { color: var(--accent-main); font-size: var(--texto-xl); }
  .sin-cobertura strong { color: var(--ink-primary); }
  .formula-cobertura { display: grid; gap: .25rem; margin-block-start: .55rem; }
  .formula-cobertura > strong { color: var(--ink-primary); }
  .contenido-cobertura .limitaciones { margin-block-start: .35rem; padding-inline-start: 1.2rem; list-style: disc; }
  .contenido-cobertura .limitaciones li { display: list-item; padding: .15rem 0; }
  .contenido-pestana :global(.vector) { max-inline-size: none; }
  .contenido-pestana :global(.katex-display) { max-inline-size: 100%; overflow-x: auto; overflow-y: hidden; }
  .panel { overflow: hidden; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); box-shadow: var(--shadow-soft); }
  .panel header { display: flex; justify-content: space-between; gap: 1rem; align-items: end; padding: 1rem; border-block-end: 1px solid var(--trazo-suave); }
  .panel header span { color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; letter-spacing: .08em; }
  .panel header small { color: var(--ink-tertiary); }
  ul { display: grid; gap: .1rem; margin: 0; padding: .5rem; list-style: none; }
  li { display: flex; align-items: center; gap: .7rem; max-inline-size: none; padding: .55rem; border-radius: var(--radius-sm); }
  li:hover { background: var(--surface-panel); } li div { display: grid; } li strong { color: var(--ink-primary); font-size: var(--texto-sm); } li small { color: var(--ink-tertiary); }
  li.vacio { padding: 1.3rem; color: var(--ink-tertiary); font-size: var(--texto-sm); }
  .nota-edicion { margin-block-start: 0; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.5; }
  .formulario-perfil { display: grid; gap: .8rem; }
  .formulario-perfil label { display: grid; gap: .3rem; color: var(--ink-secondary); font-size: var(--texto-sm); font-weight: 700; }
  .formulario-perfil select, .formulario-perfil input, .formulario-perfil textarea { min-block-size: 2.5rem; padding: .5rem .7rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); font: inherit; }
  .formulario-perfil textarea { resize: vertical; }
  .rectificaciones li { align-items: flex-start; }
  .error-perfil { margin: .75rem 0 0; color: var(--semantic-error); font-size: var(--texto-sm); }
  @media (max-width: 64rem) { .cifras { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 48rem) { .identidad { align-items: flex-start; flex-wrap: wrap; } .acciones-ficha { inline-size: 100%; margin-inline-start: 0; } .acciones-ficha > * { flex: 1 1 0; } .acciones-ficha .editar { justify-content: center; inline-size: 100%; min-block-size: 2.75rem; } .selector-clase { align-items: stretch; flex-direction: column; } .selector-clase label { min-inline-size: 0; } }
  @media (max-width: 36rem) { .subpantallas { display: grid; grid-template-columns: 1fr; } .subpantallas button { inline-size: 100%; } }
  @media (max-width: 28rem) { .identidad { gap: .7rem; padding: .8rem; } .avatar { flex-basis: 3rem; } .datos { flex: 1 1 calc(100% - 4rem); } .cifras article { gap: .45rem; padding: .65rem; } .cifras article > span { flex: none; } .cifras strong { font-size: var(--texto-md); } .panel header { align-items: flex-start; flex-wrap: wrap; } }
</style>
