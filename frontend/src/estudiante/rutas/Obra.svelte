<!--
La lectura de una obra del corpus · `/obras/LOP` · `EQ-013`.

DOS COSAS EN UNA PANTALLA, Y LA SEGUNDA PUEDE FALTAR
------------------------------------------------------
1. **La ficha de la obra**: título, autoría, páginas del archivo y el estado de
   cada canal de publicación. Se muestra siempre, también —y sobre todo— cuando
   la obra no está autorizada: es lo que permite ir a buscarla a la biblioteca.
2. **La transcripción de una parte**, si el catálogo la declara, la obra la
   autoriza y el archivo está en este servidor. Las tres condiciones se
   comprueban en el servidor; aquí sólo se explica cuál falló.

LA CORRESPONDENCIA DE PÁGINAS SE DICE, NO SE SUPONE
-----------------------------------------------------
Cuando el desfase de una obra no está medido, esta pantalla **lo declara** en
vez de ofrecer un salto a una hoja que nadie ha comprobado.


Lenguaje declarado en OE3-Implementacion/13-Lenguaje-de-Diseno.md

-->
<script>
  import { onDestroy, tick, untrack } from 'svelte';
  import { cacheDeLectura } from '../../nucleo/lectura/cache.js';
  import { lectura } from '../../nucleo/lectura/lectura.svelte.js';
  import { prepararTextoDelCorpus } from '../../nucleo/lectura/preparar.js';
  import LibroInteractivo from '../../comun/lectura/LibroInteractivo.svelte';
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import Boton from '../../comun/base/Boton.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import BloquesDeTexto from '../../comun/fuente/BloquesDeTexto.svelte';
  import VisorDePdf from '../../comun/fuente/VisorDePdf.svelte';
  import { navegar } from '../../enrutado/navegar.js';
  import {
    obra as pedirObra,
    obras as pedirObras,
    parte as pedirParte,
    fragmento as pedirFragmento,
    pdfDeParte,
    pdfCompleto,
    esClaveDeObra,
    esFragmento,
    esNombreDeParte
  } from '../../nucleo/api/fuentes.js';
  import {
    PARAMETRO_DE_RETORNO,
    destinoDeRetorno,
    obraDelCamino
  } from '../../nucleo/fuentes/navegacion.js';

  let {
    caminoActual = globalThis.location?.pathname ?? '',
    consultaActual = globalThis.location?.search ?? '',
    cargarObra = pedirObra,
    cargarObras = pedirObras,
    cargarParte = pedirParte,
    cargarFragmento = pedirFragmento
  } = $props();

  const clave = $derived(obraDelCamino(caminoActual));
  const parametros = $derived(new URLSearchParams(consultaActual));
  const parteFijada = $derived(parametros.get('parte') ?? '');
  const fragmentoDeOrigen = $derived(parametros.get('fragmento') ?? '');
  const originalPedido = $derived(parametros.get('vista') === 'original');
  const volverA = $derived(destinoDeRetorno(parametros.get(PARAMETRO_DE_RETORNO)));

  let estado = $state('cargando');
  let obra = $state(null);
  let partes = $state([]);
  let explicacion = $state('');
  let biblioteca = $state([]);
  let vistaActiva = $state('ficha');
  let documentoElegido = $state('completo');

  let parteAbierta = $state('');
  let estadoDeParte = $state('vacio');
  // Los bloques del corpus se reemplazan completos; nunca se editan aquí.
  // Evita miles de proxies/reactividades por fórmula al cambiar un capítulo.
  let contenido = $state.raw(null);
  let explicacionDeParte = $state('');
  let fragmentoCitado = $state.raw(null);
  // Tres capítulos como máximo: sus fórmulas ya montadas se reutilizan al
  // pasar la hoja. La caché de datos/KaTeX por sí sola no evitaba reconstruir
  // decenas de miles de nodos justo después de la pulsación.
  let capitulosPreparados = $state.raw([]);
  let estadoFragmento = $state('vacio');
  let modoLector = $state(true);
  let transcripcionIniciada = $state(false);
  let cromoCompacto = $state(false);
  let indice;
  let pasaje = $state(null);
  let solicitudParte = 0;
  let destruida = false;
  let preparandoParte = $state(false);
  let partePendiente = $state('');
  const posiciones = new Map();
  const cachePartes = $derived(cacheDeLectura(cargarParte, prepararTextoDelCorpus));
  let scrollAnterior = 0;
  onDestroy(() => { destruida = true; solicitudParte++; lectura.inmersiva = false; });
  $effect(() => { lectura.inmersiva = modoLector && vistaActiva === 'transcripcion'; });
  $effect(() => {
    if (estado === 'listo' && vistaActiva === 'transcripcion') transcripcionIniciada = true;
  });

  function abrirIndice() { indice?.showModal?.(); }
  function cerrarIndice() { indice?.close?.(); }
  function alDesplazar(evento) {
    const posicion = evento.currentTarget.scrollTop;
    if (parteAbierta) posiciones.set(parteAbierta,posicion);
    if (posicion > 72 && posicion > scrollAnterior+3) cromoCompacto = true;
    if (posicion < scrollAnterior-5 || posicion < 40) cromoCompacto = false;
    scrollAnterior = posicion;
  }

  const EXPLICACION = {
    recurso_no_catalogado:
      'Esta obra todavía no está en el catálogo de la biblioteca.',
    obra_no_autorizada:
      'Esta obra todavía no tiene registrada la autorización necesaria para publicar su ' +
      'transcripción aquí. Su ficha bibliográfica sí se puede consultar.',
    recurso_retirado: 'Este material se retiró de la biblioteca.',
    archivo_ausente: 'Esta parte no está disponible en este servidor.',
    recurso_no_servible: 'Esta parte no se puede abrir aquí.',
    pagina_sin_mapeo: 'No se puede señalar la página exacta de esta obra sin comprobarla antes.'
  };

  function explicar(clave_, respaldo) {
    return EXPLICACION[clave_] ?? respaldo ?? 'Este material no se puede abrir aquí.';
  }

  $effect(() => {
    const c = clave;
    const origen = fragmentoDeOrigen;
    const original = originalPedido;
    // También cambia al seguir otro enlace profundo dentro de la misma obra.
    void parteFijada;
    if (!c || !esClaveDeObra(c)) {
      estado = 'no-encontrado';
      explicacion = EXPLICACION.recurso_no_catalogado;
      return;
    }
    const control = new AbortController();
    solicitudParte++;
    posiciones.clear();
    transcripcionIniciada = false;
    preparandoParte = false;
    estado = 'cargando';
    obra = null;
    partes = [];
    parteAbierta = '';
    estadoDeParte = 'vacio';
    contenido = null;
    capitulosPreparados = [];
    cargarObra(c, { señal: control.signal })
      .then((datos) => {
        if (control.signal.aborted) return;
        obra = datos;
        partes = Array.isArray(datos?.partes) ? datos.partes : [];
        documentoElegido = datos?.disponibilidad?.pdf_completo?.servible && !origen
          ? 'completo'
          : 'parte';
        vistaActiva = original ? 'documento' : (origen || (datos?.disponibilidad?.markdown_continuo?.servible && partes.length)) ? 'transcripcion' : ((
          !datos?.disponibilidad?.pdf_completo?.servible &&
          datos?.disponibilidad?.pdf_dividido?.servible
        ) ? 'documento' : 'ficha');
        estado = 'listo';
      })
      .catch((fallo) => {
        if (control.signal.aborted) return;
        explicacion = explicar(fallo?.cuerpo?.motivo, fallo?.mensaje);
        estado = fallo?.cuerpo?.motivo === 'obra_no_autorizada' ? 'no-autorizado' : 'no-encontrado';
      });
    return () => control.abort();
  });

  $effect(() => {
    const control = new AbortController();
    cargarObras({ señal: control.signal })
      .then((datos) => { biblioteca = Array.isArray(datos) ? datos : (datos?.obras ?? []); })
      .catch(() => { biblioteca = []; });
    return () => control.abort();
  });

  /** Mantiene la página anterior mientras una petición todavía no está lista. */
  function abrirParte(nombre) {
    if (!esNombreDeParte(nombre) || !esClaveDeObra(clave)) return Promise.resolve(false);
    const actual = ++solicitudParte;
    const obraPedida = clave;
    const cache = cachePartes;
    explicacionDeParte = '';
    preparandoParte = true;
    partePendiente = nombre;
    if (!contenido) estadoDeParte = 'cargando';
    function aceptar(datos) {
      if (destruida || actual !== solicitudParte || obraPedida !== clave) return false;
      if (!datos?.contenido) {
        explicacionDeParte = EXPLICACION.recurso_no_servible;
        preparandoParte = false;
        if (!contenido) estadoDeParte = 'vacio';
        return false;
      }
      parteAbierta = nombre;
      contenido = datos.contenido;
      if (!capitulosPreparados.some(p => p.nombre === nombre)) {
        capitulosPreparados = [...capitulosPreparados, { nombre, contenido: datos.contenido }];
      }
      estadoDeParte = 'listo'; preparandoParte = false;
      const i = partes.findIndex(p => p.nombre === nombre);
      for (const p of [partes[i-1],partes[i+1]]) if (p) cache.precargar(obraPedida,p.nombre);
      return true;
    }
    const guardada = cache.ver(obraPedida,nombre);
    if (guardada) return Promise.resolve(aceptar(guardada));
    return cache.pedir(obraPedida,nombre).then(aceptar,fallo => {
      if (destruida || actual !== solicitudParte) return false;
      preparandoParte = false;
      explicacionDeParte = explicar(fallo?.cuerpo?.motivo,fallo?.mensaje);
      if (!contenido) estadoDeParte = 'error';
      return false;
    });
  }

  $effect(() => {
    const nombre = parteAbierta, obraPedida = clave, cache = cachePartes;
    const i = partes.findIndex(p => p.nombre === nombre);
    if (i < 0 || !contenido) return;
    const vecinos = [partes[i-1], partes[i+1]].filter(Boolean);
    const conservar = new Set([nombre, ...vecinos.map(p => p.nombre)]);
    untrack(() => { capitulosPreparados = capitulosPreparados.filter(p => conservar.has(p.nombre)); });
    if (!globalThis.requestIdleCallback) return;
    let cancelada = false, turno;
    const pendientes = [];
    function programar() {
      if (!cancelada && !destruida && turno == null && pendientes.length) turno = requestIdleCallback(prepararVecino);
    }
    function prepararVecino(plazo) {
      turno = null;
      if (cancelada || destruida || obraPedida !== clave) return;
      // El montaje de un capítulo extenso puede superar un fotograma. Se
      // hace entre lecturas; durante la ola sólo trabaja la malla de papel.
      if (plazo.timeRemaining() < 1 || document.querySelector('.lector')?.dataset.fase === 'SETTLING') {
        programar(); return;
      }
      const capitulo = pendientes.shift();
      if (!capitulosPreparados.some(p => p.nombre === capitulo.nombre)) {
        capitulosPreparados = [...capitulosPreparados, capitulo];
      }
      programar();
    }
    for (const vecino of vecinos) cache.pedir(obraPedida, vecino.nombre).then(datos => {
      if (cancelada || destruida || !datos?.contenido) return;
      pendientes.push({ nombre: vecino.nombre, contenido: datos.contenido });
      programar();
    }).catch(() => {});
    return () => { cancelada = true; globalThis.cancelIdleCallback?.(turno); };
  });

  async function seleccionarParte(nombre) {
    const abierta = await abrirParte(nombre);
    if (!abierta) return false;
    documentoElegido = 'parte'; vistaActiva = 'transcripcion';
    cromoCompacto = false; scrollAnterior = 0; cerrarIndice();
    if (globalThis.location?.pathname === `/obras/${clave}`) {
      const destino = new URL(globalThis.location.href);
      destino.searchParams.set('parte',nombre);
      globalThis.history?.replaceState(globalThis.history.state,'',destino);
    }
    return true;
  }

  function cambiarObra(evento) {
    const nuevaClave = evento.currentTarget.value;
    if (!esClaveDeObra(nuevaClave) || nuevaClave === clave) return;
    // Navegación interna: conservar el chat en memoria y su destino de retorno.
    const retorno = new URLSearchParams({ volver: volverA });
    navegar(`/obras/${nuevaClave}?${retorno}`);
  }

  // Un enlace profundo conserva su parte. Al entrar desde la biblioteca se
  // abre la primera disponible: PIS sólo tiene PDFs por partes y, sin esta
  // selección inicial, el documento existía pero el visor nunca se montaba.
  $effect(() => {
    if (estado !== 'listo' || parteAbierta || preparandoParte || partes.length === 0 || estadoFragmento === 'cargando') return;
    const parteDeCita = localizacion?.obra === clave ? localizacion.parte?.split(':')?.[1] : '';
    const preferida = parteDeCita || parteFijada;
    const nombre = partes.some((parte) => parte.nombre === preferida)
      ? preferida
      : partes[0].nombre;
    untrack(() => abrirParte(nombre));
    // PIS llega únicamente por volúmenes divididos. En ese caso la entrada
    // útil es el documento de la primera parte y no una ficha que obligue a
    // descubrir manualmente dónde quedó el ejemplar.
    if (!fragmentoDeOrigen && !canal.markdown_continuo?.servible && !canal.pdf_completo?.servible && canal.pdf_dividido?.servible) {
      vistaActiva = 'documento';
    }
  });

  /**
   * La localización del fragmento de origen, **pedida al servidor**.
   *
   * No viaja por la dirección a propósito. Un número de página en la URL sería
   * un dato que el cliente compone, y la correspondencia impresa–interna es
   * justo lo que esta fase no puede dejar que nadie invente: la resuelve el
   * catálogo y aquí sólo se muestra.
   */
  let localizacion = $state(null);

  $effect(() => {
    const id = fragmentoDeOrigen;
    if (!id || !esFragmento(id)) {
      localizacion = null;
      fragmentoCitado = null;
      estadoFragmento = 'vacio';
      return;
    }
    const control = new AbortController();
    localizacion = null;
    fragmentoCitado = null;
    estadoFragmento = 'cargando';
    cargarFragmento(id, { señal: control.signal })
      .then((datos) => {
        if (control.signal.aborted) return;
        localizacion = datos?.localizacion ?? null;
        fragmentoCitado = datos;
        estadoFragmento = 'listo';
      })
      .catch(() => {
        if (control.signal.aborted) return;
        localizacion = null;
        estadoFragmento = 'error';
      });
    return () => control.abort();
  });

  const canal = $derived(obra?.disponibilidad ?? {});

  /** La parte abierta, tal como la declara el catálogo. */
  const parteActual = $derived(partes.find((p) => p.nombre === parteAbierta) ?? null);
  const numeroParte = $derived(partes.findIndex((p) => p.nombre === parteAbierta));
  const partePrevia = $derived(partes[numeroParte-1]);
  const parteSiguiente = $derived(partes[numeroParte+1]);
  const citaEnParte = $derived(fragmentoCitado?.contenido && localizacion?.obra === clave
    && localizacion?.parte === parteActual?.identificador);
  $effect(() => {
    if (!citaEnParte || vistaActiva !== 'transcripcion' || !pasaje || posiciones.has(parteAbierta)) return;
    tick().then(() => pasaje?.scrollIntoView?.({
      behavior: globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
      block: 'center',
    }));
  });
  $effect(() => {
    const nombre = parteAbierta;
    if (vistaActiva !== 'transcripcion' || estadoDeParte !== 'listo') return;
    const posicion = posiciones.get(nombre);
    if (posicion === undefined) return;
    tick().then(() => requestAnimationFrame(() => {
      if (vistaActiva === 'transcripcion' && parteAbierta === nombre) {
        document.querySelector('.obra .contenido-pagina')?.scrollTo?.({top:posicion,behavior:'instant'});
      }
    }));
  });

  /**
   * La hoja del PDF dividido a la que abrir.
   *
   * Sólo cuando la localización corresponde a **esta** parte: abrir la hoja 47
   * de otro capítulo porque el número existía sería peor que no saltar.
   */
  const hojaEnLaParte = $derived(
    localizacion && parteActual && localizacion.parte === parteActual.identificador
      ? localizacion.pagina_interna_en_parte
      : null
  );
  const localizacionEnObra = $derived(localizacion?.obra === clave ? localizacion : null);
</script>

<article class="obra" class:modo-lector={modoLector && vistaActiva === 'transcripcion'} class:compacta={cromoCompacto}>
  <div class="barra-superior">
    <nav class="volver" aria-label="Volver">
      <Boton variante="discreto" aria-label="Volver a la conversación" onclick={() => navegar(volverA)}>
        ← <span class="retorno-largo">Volver a la conversación</span><span class="retorno-corto">Volver</span>
      </Boton>
    </nav>
    {#if vistaActiva === 'transcripcion'}
      <span class="capitulo-compacto">{parteActual?.titulo || obra?.titulo || 'Lectura'}</span>
    {/if}

    {#if biblioteca.length}
      <label class="selector-obra">
        <span>Elegir libro</span>
        <select use:menuDesplegable={clave} value={clave} onchange={cambiarObra} aria-label="Seleccionar obra del curso">
          {#each biblioteca as item (item.clave)}
            <option value={item.clave}>{item.titulo || item.clave}</option>
          {/each}
        </select>
      </label>
    {/if}
  </div>

  {#if estado === 'cargando'}
    <div class="estado-ruta">
      <h1>Obra del curso</h1>
      <CargadorCubo mensaje="Buscando la obra…" pantallaCompleta />
    </div>
  {:else if estado === 'no-encontrado' || estado === 'no-autorizado'}
    <div class="estado-ruta">
      <h1>Obra del curso</h1>
      <p class="aviso" role="status">{explicacion}</p>
    </div>
  {:else}
    <div class="cabecera-obra">
      <div class="cubierta" aria-hidden="true">
        <span>{obra?.titulo?.trim()?.[0] || clave?.[0]}</span>
        <i></i>
      </div>
      <div class="identidad-obra">
        <p class="etiqueta">Biblioteca del curso</p>
        <h1>{obra?.titulo || clave}</h1>
        <p class="resumen-obra">
          {partes.length} {partes.length === 1 ? 'parte disponible' : 'partes disponibles'}
          {#if obra?.paginas_del_archivo} · {obra.paginas_del_archivo} páginas{/if}
        </p>
      </div>
    </div>

    <nav class="pestanas-obra" aria-label="Secciones de la obra">
      <button type="button" aria-label="Ficha" class:activa={vistaActiva === 'ficha'} aria-pressed={vistaActiva === 'ficha'} onclick={() => (vistaActiva = 'ficha')}>
        <Icono nombre="datos" medida={16} /><span>Ficha</span>
      </button>
      <button type="button" aria-label={`Contenido, ${partes.length} partes`} class:activa={vistaActiva === 'partes'} aria-pressed={vistaActiva === 'partes'} onclick={() => (vistaActiva = 'partes')}>
        <Icono nombre="conceptos" medida={16} /><span>Contenido</span><strong>{partes.length}</strong>
      </button>
      <button type="button" aria-label="Documento" class:activa={vistaActiva === 'documento'} aria-pressed={vistaActiva === 'documento'} onclick={() => (vistaActiva = 'documento')} disabled={!canal.pdf_dividido?.servible && !canal.pdf_completo?.servible}>
        <Icono nombre="descarga" medida={16} /><span>Documento</span>
      </button>
      <button type="button" aria-label="Transcripción" class:activa={vistaActiva === 'transcripcion'} aria-pressed={vistaActiva === 'transcripcion'} onclick={() => (vistaActiva = 'transcripcion')} disabled={!parteAbierta}>
        <Icono nombre="fuente" medida={16} /><span>Transcripción</span>
      </button>
    </nav>

    <div class="panel-obra">
      {#if vistaActiva === 'ficha'}
        <section class="vista ficha-vista" aria-labelledby="ficha-de-la-obra">
          <h2 id="ficha-de-la-obra">Sobre este libro</h2>
          <dl class="ficha">
            <div>
              <dt>Identificador</dt>
              <dd><code>{obra?.clave ?? clave}</code></dd>
            </div>
            {#if obra?.paginas_del_archivo}
              <div><dt>Extensión</dt><dd>{obra.paginas_del_archivo} páginas</dd></div>
            {/if}
            <div>
              <dt>Correspondencia</dt>
              <dd>{obra?.desfase_medido ? 'Paginación verificada con el archivo.' : 'Sin correspondencia de página verificada.'}</dd>
            </div>
            <div>
              <dt>Lectura institucional</dt>
              <dd>{canal.markdown_continuo?.servible ? 'Transcripción disponible dentro de DidaxIa.' : 'La ficha está disponible; la transcripción no.'}</dd>
            </div>
          </dl>
          {#if fragmentoDeOrigen}
            <p class="origen">Llegaste desde el material <code>{fragmentoDeOrigen}</code>.</p>
          {/if}
          <button type="button" class="accion-principal" onclick={() => (vistaActiva = partes.length ? 'partes' : 'documento')}>
            Explorar el libro <span aria-hidden="true">→</span>
          </button>
        </section>
      {:else if vistaActiva === 'partes'}
        <section class="vista contenido-vista" aria-labelledby="partes-de-la-obra">
          <div class="titulo-vista">
            <div><p>Índice</p><h2 id="partes-de-la-obra">Contenido del libro</h2></div>
            <span>{partes.length} {partes.length === 1 ? 'parte' : 'partes'}</span>
          </div>
          {#if partes.length === 0}
            <p class="aviso" role="status">Esta obra no tiene partes transcritas catalogadas.</p>
          {:else}
            <ol class="partes">
              {#each partes as parte, indice (parte.identificador)}
                <li>
                  <button type="button" class:activa={parteAbierta === parte.nombre} aria-pressed={parteAbierta === parte.nombre} onclick={() => seleccionarParte(parte.nombre)}>
                    <span class="numero-parte">{String(indice + 1).padStart(2, '0')}</span>
                    <span class="datos-parte">
                      <span class="titulo">{parte.titulo || parte.nombre}</span>
                      <span class="rastro">Páginas {parte.pagina_impresa_inicial}–{parte.pagina_impresa_final}</span>
                    </span>
                    <span class="flecha-parte" aria-hidden="true">›</span>
                  </button>
                </li>
              {/each}
            </ol>
          {/if}
        </section>
      {:else if vistaActiva === 'documento'}
        <section class="vista documento-vista" aria-labelledby="documentos-de-la-obra">
          <div class="titulo-vista">
            <div><p>Ejemplar digital</p><h2 id="documentos-de-la-obra">Documento original</h2></div>
            {#if canal.pdf_completo?.servible && parteActual && canal.pdf_dividido?.servible}
              <div class="selector-documento" aria-label="Versión del documento">
                <button type="button" class:activa={documentoElegido === 'parte'} aria-pressed={documentoElegido === 'parte'} onclick={() => (documentoElegido = 'parte')}>Parte</button>
                <button type="button" class:activa={documentoElegido === 'completo'} aria-pressed={documentoElegido === 'completo'} onclick={() => (documentoElegido = 'completo')}>Libro completo</button>
              </div>
            {:else if parteActual}
              <button type="button" class="enlace-vista" onclick={() => (vistaActiva = 'partes')}>Cambiar parte</button>
            {/if}
          </div>
          {#if documentoElegido === 'parte' && parteActual && canal.pdf_dividido?.servible}
            <VisorDePdf fuente={pdfDeParte(clave, parteActual.nombre)} titulo={`PDF de «${parteActual.titulo || parteActual.nombre}»`} paginaInterna={hojaEnLaParte} paginaImpresa={hojaEnLaParte ? localizacionEnObra?.pagina_impresa : null} exacta={localizacionEnObra?.exacta ?? true} />
          {:else if canal.pdf_completo?.servible}
            <VisorDePdf fuente={pdfCompleto(clave)} titulo="PDF completo de la obra" paginaInterna={localizacionEnObra?.pagina_interna_en_obra ?? null} paginaImpresa={localizacionEnObra?.pagina_impresa ?? null} exacta={localizacionEnObra?.exacta ?? true} />
          {:else}
            <p class="aviso">No hay un documento disponible para esta selección.</p>
          {/if}
        </section>
      {/if}
      {#if vistaActiva === 'transcripcion' || transcripcionIniciada}
        <section class="vista transcripcion-vista" hidden={vistaActiva !== 'transcripcion'} aria-labelledby="texto-de-la-parte">
          {#if estadoDeParte === 'cargando'}
            <CargadorCubo mensaje="Abriendo la parte…" pantallaCompleta />
          {:else if estadoDeParte === 'listo'}
            {#if preparandoParte}<p class="estado-parte" role="status">Preparando la siguiente parte…</p>{/if}
            {#if explicacionDeParte}<p class="estado-parte" role="alert">{explicacionDeParte}<button type="button" onclick={() => seleccionarParte(partePendiente)}>Reintentar</button></p>{/if}
            <LibroInteractivo titulo={parteActual?.titulo || 'Lectura de la obra'} mostrarCabecera={false} unaPagina
              identidad={parteAbierta} pagina={Math.max(1, numeroParte+1)} total={partes.length}
              anterior={partePrevia?.titulo || partePrevia?.nombre} siguiente={parteSiguiente?.titulo || parteSiguiente?.nombre}
              alAnterior={() => seleccionarParte(partePrevia.nombre)} alSiguiente={() => seleccionarParte(parteSiguiente.nombre)} {alDesplazar}>
              {#snippet simple()}
                <div class="hoja-transcrita">
                  <p class="naturaleza">Transcripción institucional · {obra?.titulo}</p>
                  {#if citaEnParte}
                    <details open class="pasaje-citado" bind:this={pasaje} aria-label="Fragmento citado en la conversación" tabindex="-1">
                      <summary class="rotulo-cita">Pasaje citado · {fragmentoCitado.identificador}<span> Contraer / ampliar</span></summary>
                      <div class="texto-cita"><BloquesDeTexto contenido={fragmentoCitado.contenido} /></div>
                      <div class="acciones-cita">
                      {#if canal.pdf_dividido?.servible || canal.pdf_completo?.servible}
                        <button type="button" class="enlace-vista" onclick={() => (vistaActiva = 'documento')}>Ver este pasaje en el PDF original ↗</button>
                      {/if}
                      <button type="button" class="enlace-vista" onclick={() => { pasaje.open = false; }}>Ver contexto completo en el libro ↓</button>
                      </div>
                    </details>
                  {:else if fragmentoDeOrigen && estadoFragmento === 'error'}
                    <p class="aviso">No se pudo localizar el pasaje citado. Esta es la transcripción de la parte seleccionada.</p>
                  {/if}
                  {#each capitulosPreparados as capitulo (capitulo.nombre)}
                    <div class="capitulo-transcrito" data-parte={capitulo.nombre} hidden={capitulo.nombre !== parteAbierta}>
                      <BloquesDeTexto contenido={capitulo.contenido} />
                    </div>
                  {/each}
                </div>
              {/snippet}
            </LibroInteractivo>
          {:else}
            <p class="aviso" role="status">{explicacionDeParte || EXPLICACION.recurso_no_servible}</p>
          {/if}
          <footer class="barra-lectura-inferior">
            <div class="titulo-lectura"><p>Lectura accesible</p><h2 id="texto-de-la-parte">{parteActual?.titulo || 'Transcripción'}</h2></div>
            <div class="acciones-lector">
              <button type="button" class="enlace-vista" onclick={abrirIndice}>Ver índice</button>
              <button type="button" class="alternar-ampliacion" onclick={() => (modoLector = !modoLector)} aria-label={modoLector ? 'Reducir lectura' : 'Ampliar lectura'} aria-pressed={modoLector} title={modoLector ? 'Reducir lectura' : 'Ampliar lectura'}><Icono nombre={modoLector ? 'reducir' : 'ampliar'} medida={20} /></button>
            </div>
          </footer>
        </section>
      {/if}
    </div>
  {/if}
  <dialog class="indice-lectura" bind:this={indice} aria-labelledby="titulo-indice-lectura">
    <header><div><p>Índice del libro</p><h2 id="titulo-indice-lectura">{obra?.titulo || 'Contenido'}</h2></div><button type="button" onclick={cerrarIndice} aria-label="Cerrar índice">×</button></header>
    <ol>{#each partes as parte, numero (parte.identificador)}<li><button type="button" aria-current={parte.nombre === parteAbierta ? 'page' : undefined} onclick={() => seleccionarParte(parte.nombre)}><span>{String(numero+1).padStart(2,'0')}</span><strong>{parte.titulo || parte.nombre}</strong></button></li>{/each}</ol>
  </dialog>
</article>

<style>
  .transcripcion-vista[hidden] { display: none; }
  @supports (content-visibility: auto) {
    /* Conserva el texto completo para búsqueda y accesibilidad. El navegador
       aplaza la disposición de bloques que aún quedan lejos de la lectura. */
    .hoja-transcrita :global(.texto-del-corpus > *) {
      content-visibility: auto;
      contain-intrinsic-size: auto 5rem;
    }
  }
  .retorno-corto, .capitulo-compacto { display: none; }
  .acciones-lector { display: flex; gap: .3rem; flex-shrink: 0; align-items: center; }
  .acciones-lector button { min-height: 44px; }
  .alternar-ampliacion { display: grid; place-items: center; min-width: 44px; border: 1px solid var(--trazo-suave); border-radius: 999px; background: var(--surface-paper); color: var(--accent-main); cursor: pointer; }
  .acciones-lector button:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 2px; }
  .barra-lectura-inferior { display: flex; align-items: center; justify-content: space-between; gap: .5rem; flex: 0 0 auto; padding: .25rem .5rem; border-top: 1px solid var(--trazo-suave); }
  .titulo-lectura { min-width: 0; }
  .titulo-lectura p { margin: 0 0 .15rem; color: var(--accent-main); font-size: .62rem; font-weight: 750; text-transform: uppercase; letter-spacing: .06em; }
  .barra-lectura-inferior h2 { font-size: .85rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .obra.modo-lector { width: 100%; max-width: none; height: 100%; padding: 0; gap: 0; grid-template-rows: auto minmax(0, 1fr); background: var(--surface-canvas); }
  .modo-lector .barra-superior { flex-direction: row; align-items: center; padding: .25rem max(.5rem, env(safe-area-inset-right)) .25rem max(.5rem, env(safe-area-inset-left)); gap: .4rem; border-bottom: 1px solid var(--trazo-suave); }
  .modo-lector .selector-obra, .modo-lector .cabecera-obra, .modo-lector .pestanas-obra, .modo-lector .titulo-vista { display: none; }
  .modo-lector .capitulo-compacto { display: block; flex: 1; min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: var(--ink-secondary); font: 600 .85rem/1.4 Georgia, serif; }
  .modo-lector .panel-obra { border: 0; border-radius: 0; box-shadow: none; }
  .obra .transcripcion-vista { height: 100%; min-height: 0; display: flex; flex-direction: column; overflow: hidden; padding: .5rem; box-sizing: border-box; }
  .transcripcion-vista :global(.lector) { flex: 1; min-height: 0; }
  .obra .hoja-transcrita { max-width: 52rem; width: 100%; margin: 0 auto; padding: clamp(1.2rem,4vw,3rem); background: transparent; border: 0; border-radius: 0; box-shadow: none; box-sizing: border-box; }
  .hoja-transcrita :global(.texto-del-corpus) { font-family: Georgia, 'Times New Roman', serif; font-size: clamp(1rem,1.2vw,1.12rem); line-height: 1.75; }
  .pasaje-citado { padding: .5rem .8rem; margin-block: .5rem 1rem; border-inline-start: 3px solid var(--accent-main); border-radius: 0 .6rem .6rem 0; background: var(--accent-surface); animation: pulso-cita 2s ease; scroll-margin-block: 1rem; }
  .texto-cita { max-height: min(18vh,7rem); overflow: auto; }
  .acciones-cita { display: flex; flex-wrap: wrap; gap: .2rem .5rem; border-top: 1px solid var(--trazo-suave); }
  .acciones-cita .enlace-vista { min-height: 44px; font-size: .72rem; text-align: left; }
  .rotulo-cita { cursor: pointer; min-height: 44px; align-content: center; color: var(--accent-main); font: 700 .72rem/1.4 system-ui,sans-serif; letter-spacing: .05em; text-transform: uppercase; }
  .estado-parte { position: absolute; z-index: 40; inset: auto 1rem 3rem; margin: 0; padding: .5rem 1rem; background: var(--surface-panel); border: 1px solid var(--trazo); border-radius: .5rem; font-size: .8rem; }
  .rotulo-cita span { font-weight: 400; text-transform: none; font-size: .65rem; }
  @keyframes pulso-cita { 50% { box-shadow: 0 0 0 8px color-mix(in srgb,var(--accent-main) 12%,transparent); } }
  .indice-lectura { inset: 0 0 0 auto; margin: 0; width: min(90vw,26rem); max-height: 100dvh; height: 100dvh; padding: 1rem; border: 0; border-inline-start: 1px solid var(--trazo-suave); background: var(--surface-paper); color: var(--ink-primary); box-sizing: border-box; }
  .indice-lectura[open] { animation: entrar-indice .24s ease-out; }
  @keyframes entrar-indice { from { opacity: 0; transform: translateX(16px); } to { opacity: 1; transform: none; } }
  .indice-lectura::backdrop { background: var(--velo-modal); backdrop-filter: blur(3px); }
  .indice-lectura header { display: flex; justify-content: space-between; gap: 1rem; align-items: start; }
  .indice-lectura header p { margin: 0; font-size: .75rem; color: var(--accent-main); }
  .indice-lectura h2 { font: 700 1.4rem/1.25 Georgia,serif; margin: .3rem 0 1rem; }
  .indice-lectura button { min-height: 44px; color: inherit; background: transparent; border: 0; cursor: pointer; }
  .indice-lectura header button { min-width: 44px; font-size: 1.5rem; }
  .indice-lectura ol { list-style: none; padding: 0; margin: 0; }
  .indice-lectura li button { width: 100%; display: flex; gap: 1rem; padding: .8rem .5rem; text-align: start; border-bottom: 1px solid var(--trazo-suave); }
  .indice-lectura li span { color: var(--accent-main); font-family: var(--fuente-mono); }
  .indice-lectura li button[aria-current] { background: var(--accent-surface); }
  @media (max-width: 47.999rem) {
    .modo-lector .retorno-largo { display: none; }
    .modo-lector .retorno-corto { display: inline; }
    .obra .hoja-transcrita { padding: 1rem 1.1rem 2rem; }
    .modo-lector .transcripcion-vista { padding: 0; }
    .compacta.modo-lector :global(.controles-libro) { display: none; }
    .modo-lector :global(.mesa) { padding: 0; border-radius: 0; }
    .modo-lector :global(.pagina-simple) { border: 0; border-radius: 0; }
  }
  @media (prefers-reduced-motion: reduce) { .pasaje-citado, .indice-lectura[open] { animation: none; } }
  .obra {
    width: min(100%, 78rem);
    min-width: 0;
    block-size: 100%;
    min-block-size: 0;
    margin: 0 auto;
    padding: clamp(.75rem, 2vw, 1.5rem);
    display: grid;
    grid-template-rows: auto auto auto minmax(0, 1fr);
    gap: clamp(.75rem, 1.6vw, 1.2rem);
    overflow: hidden;
    overflow-x: hidden;
    box-sizing: border-box;
  }

  .barra-superior {
    min-inline-size: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .selector-obra {
    min-inline-size: 0;
    display: grid;
    grid-template-columns: auto minmax(12rem, 28rem);
    align-items: center;
    gap: .6rem;
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
    font-weight: 700;
  }

  .selector-obra select {
    inline-size: 100%;
    min-inline-size: 0;
    min-block-size: 42px;
    padding: .55rem 2.2rem .55rem .8rem;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-sm);
    background: var(--surface-panel);
    color: var(--ink-secondary);
    font: inherit;
    font-weight: 600;
    text-overflow: ellipsis;
    box-shadow: var(--shadow-soft);
  }

  .cabecera-obra {
    min-inline-size: 0;
    display: flex;
    align-items: center;
    gap: clamp(1rem, 2.5vw, 1.8rem);
  }

  .cubierta {
    position: relative;
    flex: 0 0 auto;
    inline-size: clamp(4.25rem, 8vw, 6rem);
    aspect-ratio: .72;
    display: grid;
    place-items: center;
    border-radius: 4px 10px 10px 4px;
    color: var(--book-cover-ink);
    background:
      radial-gradient(circle at 78% 18%, var(--book-cover-glint) 0 3px, transparent 4px),
      linear-gradient(145deg, var(--book-cover-start), var(--book-cover-end) 72%);
    box-shadow: 0 13px 25px var(--book-cover-shadow), inset 5px 0 8px var(--book-cover-depth), inset -1px 0 var(--book-page-glint);
    font-family: var(--fuente-manuscrita);
    font-size: clamp(1.8rem, 4vw, 2.7rem);
    font-weight: 800;
  }

  .cubierta::after {
    content: '';
    position: absolute;
    inset: 7px 6px;
    border: 1px solid var(--book-cover-detail);
    border-radius: 2px 7px 7px 2px;
  }

  .cubierta i { position: absolute; inset-inline-start: 5px; inset-block: 0; inline-size: 2px; background: var(--book-cover-thread); }
  .identidad-obra { min-inline-size: 0; }
  .identidad-obra h1 { max-inline-size: 48rem; }

  .resumen-obra {
    margin: .4rem 0 0;
    color: var(--ink-tertiary);
    font-size: var(--texto-sm);
  }

  .etiqueta {
    margin: 0;
    font-size: var(--texto-xs);
    color: var(--accent-main);
    font-weight: 750;
    letter-spacing: .07em;
    text-transform: uppercase;
  }

  h1 {
    margin: .2rem 0 0;
    font-size: clamp(1.35rem, 2.5vw, 2rem);
    line-height: 1.15;
    letter-spacing: -.025em;
    overflow-wrap: anywhere;
  }

  .pestanas-obra {
    display: flex;
    align-items: stretch;
    gap: .25rem;
    padding: .3rem;
    overflow-x: auto;
    scrollbar-width: none;
    background: var(--surface-canvas);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
  }

  .pestanas-obra::-webkit-scrollbar { display: none; }

  .pestanas-obra button {
    flex: 1 0 auto;
    min-block-size: 42px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: .45rem;
    padding: .5rem .9rem;
    border: 1px solid transparent;
    border-radius: calc(var(--radius-md) - .25rem);
    background: transparent;
    color: var(--ink-secondary);
    font: inherit;
    font-size: var(--texto-sm);
    font-weight: 650;
    cursor: pointer;
  }

  .pestanas-obra button:hover:not(:disabled) { color: var(--ink-primary); background: var(--surface-panel); }
  .pestanas-obra button.activa { color: var(--accent-main); background: var(--surface-panel); border-color: var(--trazo-suave); box-shadow: var(--shadow-soft); }
  .pestanas-obra button:disabled { opacity: .42; cursor: default; }
  .pestanas-obra strong { min-inline-size: 1.35rem; padding: .05rem .35rem; border-radius: 999px; background: var(--accent-surface); font-size: .68rem; }

  .panel-obra {
    min-block-size: 0;
    overflow: hidden;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-lg);
    background: var(--surface-panel);
    box-shadow: 0 16px 44px color-mix(in srgb, var(--ink-primary) 8%, transparent);
  }

  .vista {
    block-size: 100%;
    min-block-size: 0;
    overflow-y: auto;
    overflow-x: hidden;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
    touch-action: pan-y;
    padding: clamp(1rem, 3vw, 2rem);
    box-sizing: border-box;
    animation: entrar-vista .22s cubic-bezier(.22,1,.36,1);
  }

  @keyframes entrar-vista { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: none; } }

  .vista h2 { margin: 0; color: var(--ink-primary); font-size: clamp(1.15rem, 2vw, 1.45rem); }

  .ficha {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: .75rem;
    margin: 1.2rem 0;
  }

  .ficha div {
    min-block-size: 5.4rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: .7rem;
    padding: 1rem;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    background: var(--surface-canvas);
  }

  dt {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  dd {
    margin: 0;
    font-size: var(--texto-sm);
    color: var(--ink-primary);
    font-weight: 600;
    overflow-wrap: anywhere;
  }

  .origen { color: var(--ink-tertiary); font-size: var(--texto-sm); }

  .accion-principal {
    min-block-size: 44px;
    display: inline-flex;
    align-items: center;
    gap: .65rem;
    padding: .65rem 1rem;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    background: var(--accent-main);
    color: var(--accent-contrast);
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }

  .titulo-vista { display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; margin-block-end: 1rem; }
  .titulo-vista p { margin: 0 0 .2rem; color: var(--accent-main); font-size: var(--texto-xs); font-weight: 750; text-transform: uppercase; letter-spacing: .06em; }
  .titulo-vista > span { color: var(--ink-tertiary); font-size: var(--texto-xs); }

  .partes {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: .55rem;
  }

  .partes button {
    width: 100%;
    min-height: 62px;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: .75rem;
    padding: .65rem .8rem;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    background: var(--surface-canvas);
    color: var(--ink-primary);
    font: inherit;
    text-align: start;
    cursor: pointer;
  }

  .partes button:hover,
  .partes button.activa {
    border-color: var(--accent-main);
    background: var(--accent-surface);
  }

  .partes button:focus-visible {
    outline: 2px solid var(--accent-main);
    outline-offset: 2px;
  }

  .numero-parte { color: var(--accent-main); font: 700 .72rem/1 var(--fuente-mono); }
  .datos-parte { min-inline-size: 0; display: flex; flex-direction: column; gap: .15rem; }
  .titulo { font-size: var(--texto-sm); font-weight: 650; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .rastro {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    font-variant-numeric: tabular-nums;
  }

  .flecha-parte { color: var(--ink-tertiary); font-size: 1.4rem; }
  .enlace-vista { padding: .4rem .65rem; border: 0; background: transparent; color: var(--accent-main); font: inherit; font-size: var(--texto-sm); font-weight: 700; cursor: pointer; }
  .selector-documento { flex: 0 0 auto; display: flex; gap: .2rem; padding: .2rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-pill, 999px); background: var(--surface-canvas); }
  .selector-documento button { min-block-size: 32px; padding: .3rem .7rem; border: 0; border-radius: inherit; background: transparent; color: var(--ink-secondary); font: inherit; font-size: var(--texto-xs); font-weight: 700; cursor: pointer; }
  .selector-documento button.activa { background: var(--surface-paper); color: var(--accent-main); box-shadow: var(--shadow-soft); }
  .documento-vista { display: flex; flex-direction: column; }
  .documento-vista :global(.visor-pdf) { flex: 1; min-block-size: 22rem; }

  .naturaleza {
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
    border-inline-start: 3px solid var(--accent-main);
    padding-inline-start: var(--espacio-sm);
    margin: 0 0 var(--espacio-md);
  }

  .hoja-transcrita {
    max-inline-size: 48rem;
    margin-inline: auto;
    padding: clamp(1rem, 4vw, 3rem);
    border-radius: 2px;
    background: var(--book-paper);
    box-shadow: 0 12px 30px color-mix(in srgb, var(--ink-primary) 8%, transparent);
    font-family: ui-serif, Georgia, Cambria, 'Times New Roman', serif;
    line-height: 1.72;
  }

  .aviso {
    font-size: var(--texto-sm);
    color: var(--semantic-warning);
    background: var(--semantic-warning-bg);
    padding: var(--espacio-md);
    border-radius: var(--radius-sm);
  }

  .estado-ruta { grid-row: 2 / -1; align-self: center; justify-self: center; text-align: center; }

  @media (max-width: 48rem) {
    .obra { padding: .6rem; gap: .65rem; }
    .barra-superior { align-items: stretch; flex-direction: column; gap: .5rem; }
    .selector-obra { grid-template-columns: 1fr; gap: .25rem; }
    .cabecera-obra { gap: .85rem; }
    .cubierta { inline-size: 3.65rem; border-radius: 3px 7px 7px 3px; }
    .resumen-obra { font-size: var(--texto-xs); }
    .pestanas-obra { border-radius: var(--radius-sm); }
    .pestanas-obra button { min-inline-size: 3rem; padding-inline: .65rem; }
    .pestanas-obra button span { display: none; }
    .vista { padding: .9rem; }
    .ficha, .partes { grid-template-columns: 1fr; }
    .titulo-vista { align-items: flex-start; }
    .titulo-vista > span { display: none; }
    .selector-documento button { padding-inline: .55rem; }
    .documento-vista :global(.visor-pdf) { min-block-size: 18rem; }
  }

  @media (prefers-reduced-motion: reduce) {
    .vista { animation: none; }
  }
</style>
