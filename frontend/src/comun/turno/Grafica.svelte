
<script>
  import { descargarBlob } from '../../nucleo/descargas/archivo.js';
  import { toast } from '../estado/toasts.svelte.js';
  import { menuDesplegable } from '../base/menuDesplegable.js';
  import { ayudaContextual } from '../base/ayudaContextual.js';
  import { onMount } from 'svelte';
  import JXG from 'jsxgraph';
  import { protegerTrazadoSVG } from '../../nucleo/presentacion/recorteGrafica.js';
  import { compilarCurva, describirPunto } from '../../nucleo/presentacion/dominioGrafica.js';
  import Dialogo from '../base/Dialogo.svelte';
  import BotonAyudaTooltip from '../base/BotonAyudaTooltip.svelte';
  import ReportarProblema from '../rutas/ReportarProblema.svelte';
  import Notacion from './Notacion.svelte';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import { agregarMarcaDeAgua } from '../../nucleo/presentacion/marcaDeAgua.js';
  import {
    emitirEvento,
    identificadorDeGrafica,
  } from '../../nucleo/api/telemetria.js';
  import {
    ajustarCajaAProporcion,
    agregarFondoDeTema,
    agregarNotasDeAnalisis
  } from '../../nucleo/presentacion/exportacionGrafica.js';
  import {
    calcularTangente,
  } from '../../nucleo/presentacion/analisisTangente.js';
  import { aplicarAbscisasManuales, destinoNumerico, elegirAbscisasConFocos, leerDecimalDeTabla, mostrarDecimalDeTabla, tabularCurvas } from '../../nucleo/presentacion/tabulacionGrafica.js';
  import { reticulaDeEscala } from '../../nucleo/presentacion/escalasGrafica.js';
  import AsaPanelGrafica from './AsaPanelGrafica.svelte';
  import TecladoNumericoTabla from './TecladoNumericoTabla.svelte';

  let {
    definicion = null,
    alternativo = '',
    compacto = false,
    laboratorio = false,
    inmersiva = false,
    panelEscritorio = '',
    tabulacionAbierta = $bindable(false),
    alturaPanelMovil = $bindable(280),
    funcionesAbiertas = false,
    alAlternarFunciones = null,
    alCerrarFunciones = null,
    alGuardarFunciones = null,
    alCargarFunciones = null,
    hayFuncionesParaGuardar = false,
    curvasOcultas = $bindable([]),
    chip = false,
    clase = undefined,
    conversacion = undefined,
    turno = undefined,
    concepto = undefined,
    soloLectura = false,
  } = $props();

  const visible = $derived(laboratorio || preferencias.graficaVisible);

  const datos = $derived.by(() => {
    if (!definicion) return null;
    try {
      const parseado = JSON.parse(definicion);
      return parseado?.funcion_js || parseado?.curvas?.some((curva) => curva.funcion_js)
        ? parseado : null;
    } catch {
      return null;
    }
  });

  const variablePresentada = $derived.by(() => {
    const candidata = datos?.curvas?.[0]?.variable ?? datos?.variable;
    return /^[a-zA-Zθ]$/.test(candidata ?? '') ? candidata : 'x';
  });

  const expresionPresentable = $derived.by(() => {
    if (typeof datos?.expresion !== 'string') return '';
    let expresion = datos.expresion.trim();
    if (expresion.startsWith('$$') && expresion.endsWith('$$')) {
      expresion = expresion.slice(2, -2).trim();
    } else if (expresion.startsWith('$') && expresion.endsWith('$')) {
      expresion = expresion.slice(1, -1).trim();
    } else if (expresion.startsWith('\\(') && expresion.endsWith('\\)')) {
      expresion = expresion.slice(2, -2).trim();
    }
    const nombre = /^[a-zA-Z]$/.test(datos.nombre_funcion ?? '') ? datos.nombre_funcion : 'f';
    return expresion ? `${nombre}(${variablePresentada}) = ${expresion}` : '';
  });

  let tablero = $state(null);
  let pizarraActual = $state(null);
  let noSePudoDibujar = $state(false);
  let pantallaCompleta = $state(false);
  let seccionMovil = $state('');
  const panelMovilAbierto = $derived(funcionesAbiertas ||
    (seccionMovil !== '' && (seccionMovil !== 'funciones' || !alAlternarFunciones)
      && (seccionMovil !== 'tabla' || tabulacionAbierta)));
  let marcasVista = $state({ x: [], y: [], menoresX: [], menoresY: [], ancho: 1, alto: 1, ejeX: 0, ejeY: 0 });
  let mostrarFuncion = $state(true);
  let mostrarDerivada = $state(true);
  let mostrarCuadricula = $state(true);
  let mostrarEjes = $state(true);
  let puntoActivo = $state(false);
  let tangenteActiva = $state(false);
  let secanteActiva = $state(false);
  let explicacionTangenteVisible = $state(false);
  let explicacionSecanteVisible = $state(false);
  let abrirTangenteAlActivar = $state(true);
  let abrirSecanteAlActivar = $state(true);
  let textoTangenteVisible = $state(true);
  let textoSecanteVisible = $state(true);
  let formulaTangenteVisible = $state(true);
  let formulaSecanteVisible = $state(true);
  let procesoTangenteVisible = $state(false);
  let procesoSecanteVisible = $state(false);
  let xAnalisis = $state(0);
  let deltaSecante = $state(1);
  let estadoExportacion = $state('');
  let confirmacionExportacion = $state(false);
  let formatoPendiente = $state('');
  let opcionesExportacion = $state({ cuadricula: true, valores: true, guias: true, notas: true });
  let mostrarMuestras = $state(true);
  let curvaTabulada = $state(0);
  let tablaDesde = $state(-8);
  let tablaHasta = $state(8);
  let opcionesTablaVisibles = $state(false);
  let abscisasManuales = $state({});
  let abscisasAdicionales = $state([]);
  let ordenTabla = $state('ascendente');
  let tablaOrdenada = $state(true);
  let tablaEstabaAbierta = false;
  let nuevaAbscisa = $state('');
  let mensajeAbscisa = $state('');
  let movilTabla = $state(false);
  let editorNumero = $state(null);
  let errorNumero = $state('');
  let anclaNumero;
  let rangoTablaIniciado = false;
  let generacionAnotada = false;
  let aperturaNormalAnotada = false;
  const ultimaInteraccion = new Map();

  onMount(() => {
    if (datos?.mostrar_tangente && Number.isFinite(Number(datos.punto_x))) {
      xAnalisis = Number(datos.punto_x);
      puntoActivo = true;
      tangenteActiva = true;
      explicacionTangenteVisible = abrirTangenteAlActivar;
    }
    const consulta = window.matchMedia?.('(max-width: 48rem)');
    const actualizar = () => { movilTabla = Boolean(consulta?.matches); };
    actualizar();
    consulta?.addEventListener('change', actualizar);
    return () => consulta?.removeEventListener('change', actualizar);
  });

  const curvas = $derived(datos?.curvas?.length
    ? datos.curvas.map((curva) => ({ ...curva, evaluar: compilarCurva(curva) }))
    : datos?.funcion_js ? [{ ...datos, evaluar: compilarCurva(datos) }] : []);
  const funcion = $derived(curvas[0]?.evaluar ?? null);
  const derivada = $derived(compilar(datos?.derivada_js));
  const destino = $derived(destinoNumerico(datos?.limite_x ?? datos?.limite_destino ?? curvas.find((curva) => curva.tipo === 'limite')?.limite_x ?? curvas.find((curva) => curva.tipo === 'limite')?.limite_destino));
  const destinoTablaOriginal = $derived(
    curvas[Number(curvaTabulada)]?.limite_x ?? curvas[Number(curvaTabulada)]?.limite_destino
    ?? (curvas.length === 1 ? (datos?.limite_x ?? datos?.limite_destino) : null)
  );
  const destinoTabla = $derived(destinoNumerico(destinoTablaOriginal));
  const ventanaInicial = $derived(calcularVentana(funcion, destino ?? 0, destino === null ? 8 : 4));
  const evaluadoresTabla = $derived([
    ...curvas.map((curva) => curva.evaluar),
    ...(derivada ? [derivada] : [])
  ]);
  function nombreCurva(curva, indice) {
    if (curva.tipo === 'derivada') return `Derivada ${indice + 1}`;
    const variable = /^[a-zA-Zθ]$/.test(curva.variable ?? '') ? curva.variable : variablePresentada;
    if (/^[a-zA-Z]$/.test(curva.nombre_funcion ?? '')) return `${curva.nombre_funcion}(${variable})`;
    return curvas.length === 1 ? `f(${variable})` : `f${indice + 1}(${variable})`;
  }
  const nombresTabla = $derived([
    ...curvas.map(nombreCurva),
    ...(derivada ? [`f′(${variablePresentada})`] : [])
  ]);
  const abscisasBase = $derived(aplicarAbscisasManuales(
    elegirAbscisasConFocos(tablaDesde, tablaHasta, destinoTablaOriginal, evaluadoresTabla), abscisasManuales
  ));
  const entradasTabla = $derived.by(() => {
    if (!abscisasBase.length) return [];
    const base = abscisasBase.map((x, indiceOrigen) => ({ x, origen: 'base', indiceOrigen }));
    const nuevas = abscisasAdicionales.map((x, indiceOrigen) => ({ x, origen: 'adicional', indiceOrigen }));
    if (!tablaOrdenada) return [...nuevas.reverse(), ...base];
    return [...base, ...nuevas].sort((a, b) => ordenTabla === 'descendente' ? b.x - a.x : a.x - b.x);
  });
  const puntosTabla = $derived(tabularCurvas(entradasTabla.map((fila) => fila.x), evaluadoresTabla)
    .map((fila, indice) => ({ ...fila, ...entradasTabla[indice] })));
  const rotuloXEje = $derived(inmersiva && !pantallaCompleta && marcasVista.ejeX < 112
    ? 122
    : marcasVista.ejeX + (marcasVista.rotuloXDebajo ? 16 : -7));
  const grafica = $derived(identificadorDeGrafica(definicion));
  const contextoReporte = $derived.by(() => [
    'Origen: gráfica interactiva.',
    grafica ? `Gráfica: ${grafica}` : '',
    conversacion ? `Conversación: ${conversacion}` : '',
    turno ? `Turno: ${turno}` : '',
    clase ? `Clase: ${clase}` : '',
    concepto ? `Concepto: ${concepto}` : ''
  ].filter(Boolean).join('\n'));
  const tangente = $derived.by(() => tangenteActiva
    ? calcularTangente(funcion, derivada, Number(xAnalisis))
    : null);
  const secante = $derived.by(() => {
    if (!secanteActiva || !funcion) return null;
    const x = Number(xAnalisis);
    const delta = Number(deltaSecante);
    const y = funcion(x);
    const otroY = funcion(x + delta);
    if (!Number.isFinite(x) || !Number.isFinite(delta) || delta === 0 ||
        !Number.isFinite(y) || !Number.isFinite(otroY)) {
      return { disponible: false, motivo: 'Elige dos puntos con valores finitos y Δx distinto de cero.' };
    }
    return { disponible: true, x, y, delta, otroY, pendiente: (otroY - y) / delta };
  });
  const notasVisibles = $derived([
    ...(tangenteActiva && explicacionTangenteVisible ? [{
      titulo: 'Recta tangente',
      lineas: tangente?.disponible ? [
        ...(textoTangenteVisible ? [`a = ${numero(tangente.x)} · f(a) = ${numero(tangente.y)} · f′(a) = ${numero(tangente.pendiente)}`] : []),
        ...(formulaTangenteVisible ? [
          'y = f(a) + f′(a)(x − a)',
          `y = ${numero(tangente.y)} + ${numero(tangente.pendiente)}(x − ${numero(tangente.x)})`
        ] : [])
      ] : [tangente?.motivo || 'Tangente no disponible.']
    }] : []),
    ...(secanteActiva && explicacionSecanteVisible ? [{
      titulo: 'Recta secante',
      lineas: secante?.disponible ? [
        ...(textoSecanteVisible ? [`a = ${numero(secante.x)} · Δx = ${numero(secante.delta)} · m = ${numero(secante.pendiente)}`] : []),
        ...(formulaSecanteVisible ? [
          'm = [f(a + Δx) − f(a)] / Δx',
          `y = ${numero(secante.y)} + ${numero(secante.pendiente)}(x − ${numero(secante.x)})`
        ] : [])
      ] : [secante?.motivo || 'Secante no disponible.']
    }] : [])
  ]);

  function numero(valor) {
    return Number.isFinite(valor) ? String(Number(valor.toFixed(4))) : '—';
  }

  function puntoEnFormula(valor) {
    return valor < 0 ? `(${numero(valor)})` : numero(valor);
  }

  function alternarTangente() {
    tangenteActiva = !tangenteActiva;
    explicacionTangenteVisible = tangenteActiva && abrirTangenteAlActivar;
    procesoTangenteVisible = false;
  }

  function alternarSecante() {
    secanteActiva = !secanteActiva;
    explicacionSecanteVisible = secanteActiva && abrirSecanteAlActivar;
    procesoSecanteVisible = false;
  }

  function alternarCurva(indice) {
    curvasOcultas = curvasOcultas.includes(indice)
      ? curvasOcultas.filter((actual) => actual !== indice)
      : [...curvasOcultas, indice];
  }

  function anotar(tipo, metadatos = {}) {
    if (soloLectura) return;
    void emitirEvento(tipo, {
      clase,
      conversacion,
      turno,
      concepto,
      metadatos: { grafica, ...metadatos },
    });
  }

  function temaVisible() {
    return globalThis.document?.body?.classList.contains('dark-theme')
      ? 'oscuro'
      : 'claro';
  }

  function anotarInteraccion(gesto) {
    const ahora = Date.now();
    if (ahora - (ultimaInteraccion.get(gesto) ?? 0) < 750) return;
    ultimaInteraccion.set(gesto, ahora);
    anotar('grafica.interaccion', { gesto });
  }

  function anotarRango(eje = 'ambos') {
    anotar('grafica.rango_cambiado', { eje });
  }

  function observarApertura(nodo) {
    if (chip) return {};
    const registrar = () => {
      if (aperturaNormalAnotada) return;
      aperturaNormalAnotada = true;
      anotar('grafica.abierta', { vista: 'normal' });
    };
    if (!globalThis.IntersectionObserver) {
      registrar();
      return {};
    }
    const observador = new IntersectionObserver((entradas) => {
      if (entradas.some((entrada) => entrada.isIntersecting && entrada.intersectionRatio >= 0.35)) {
        registrar();
        observador.disconnect();
      }
    }, { threshold: 0.35 });
    observador.observe(nodo);
    return { destroy: () => observador.disconnect() };
  }

  function cajaProporcional(caja = ventanaInicial) {
    return ajustarCajaAProporcion(
      caja,
      tablero?.clientWidth || (chip ? 40 : 800),
      tablero?.clientHeight || (chip ? 40 : 400),
    );
  }

  function compilar(js) {
    if (!js) return null;
    try {
      return new Function('x', `
        try {
          const y = (${js});
          return typeof y === 'number' && isFinite(y) ? y : NaN;
        } catch { return NaN; }
      `);
    } catch {
      return null;
    }
  }

  function calcularVentana(evaluar, centro = 0, radio = 8) {
    const izquierda = centro - radio;
    const derecha = centro + radio;
    if (!evaluar) return [izquierda, 6, derecha, -6];
    const valores = [];
    for (let i = 0; i <= 320; i += 1) {
      const x = izquierda + (2 * radio * i) / 320;
      const y = evaluar(x);
      if (Number.isFinite(y)) valores.push(y);
    }
    if (!valores.length) return [izquierda, 6, derecha, -6];
    valores.sort((a, b) => a - b);
    let minimo = valores[0];
    let maximo = valores[valores.length - 1];
    const amplitud = maximo - minimo;
    if (amplitud > 16) {
      minimo = Math.max(minimo - 1.5, -6);
      maximo = Math.min(maximo, minimo + 16);
    } else {
      const margen = Math.max(amplitud * 0.18, 0.75);
      minimo -= margen;
      maximo += margen;
    }
    if (minimo > 0) minimo = Math.min(0, minimo - 1);
    if (maximo < 0) maximo = Math.max(0, maximo + 1);
    return [izquierda, maximo, derecha, minimo];
  }

  function tomarRangoDeLaVista() {
    const caja = pizarraActual?.getBoundingBox?.() ?? ventanaInicial;
    tablaDesde = Number(caja[0].toFixed(5));
    tablaHasta = Number(caja[2].toFixed(5));
    anotarInteraccion('tabular-vista');
  }

  function numeroTabla(valor) {
    if (!Number.isFinite(valor)) return '—';
    return String(Number(valor.toPrecision(7)));
  }

  function abrirNumero(tipo, indice, valor, etiqueta, evento) {
    anclaNumero = evento.currentTarget;
    editorNumero = { tipo, indice, texto: typeof valor === 'number' ? mostrarDecimalDeTabla(valor) : String(valor ?? ''), etiqueta };
    errorNumero = '';
  }

  function cerrarNumero() {
    editorNumero = null;
    errorNumero = '';
    queueMicrotask(() => anclaNumero?.focus());
  }

  function aplicarNumero() {
    if (!editorNumero) return;
    const valor = leerDecimalDeTabla(editorNumero.texto);
    if (valor === null) {
      errorNumero = 'Escribe un número válido; usa la coma para los decimales.';
      return;
    }
    if (editorNumero.tipo === 'desde') tablaDesde = valor;
    else if (editorNumero.tipo === 'hasta') tablaHasta = valor;
    else if (editorNumero.tipo === 'nuevo') {
      nuevaAbscisa = String(valor);
      if (!agregarAbscisa()) { errorNumero = mensajeAbscisa; return; }
    }
    else if (editorNumero.tipo === 'punto') editarAbscisa(editorNumero.indice, valor);
    cerrarNumero();
  }

  function editarAbscisa(indice, valor) {
    if (!Number.isFinite(valor)) {
      return;
    }
    const fila = entradasTabla[indice];
    if (!fila) return;
    if (fila.origen === 'base') abscisasManuales = { ...abscisasManuales, [fila.indiceOrigen]: valor };
    else abscisasAdicionales = abscisasAdicionales.map((actual, posicion) =>
      posicion === fila.indiceOrigen ? valor : actual);
    anotarInteraccion('tabular-punto');
  }

  function editarAbscisaDesdeCampo(indice, evento) {
    const valor = leerDecimalDeTabla(evento.currentTarget.value);
    if (valor === null) {
      evento.currentTarget.value = numeroTabla(puntosTabla[indice]?.x);
      return;
    }
    editarAbscisa(indice, valor);
  }

  function agregarAbscisa() {
    const texto = String(nuevaAbscisa).trim();
    const valor = leerDecimalDeTabla(texto);
    if (valor === null) {
      mensajeAbscisa = 'Escribe un valor numérico de x.';
      return false;
    }
    if (puntosTabla.some((fila) => Math.abs(fila.x - valor) < 1e-8)) {
      mensajeAbscisa = 'Ese valor ya está en la tabla.';
      return false;
    }
    if (puntosTabla.length >= 30) {
      mensajeAbscisa = 'La tabla admite hasta 30 puntos.';
      return false;
    }
    abscisasAdicionales = [...abscisasAdicionales, valor];
    tablaOrdenada = false;
    nuevaAbscisa = '';
    mensajeAbscisa = `Se añadió x = ${numeroTabla(valor)}.`;
    anotarInteraccion('tabular-punto');
    return true;
  }

  function quitarAbscisa(indice) {
    abscisasAdicionales = abscisasAdicionales.filter((_, posicion) => posicion !== indice);
    mensajeAbscisa = 'Se quitó el punto añadido.';
    anotarInteraccion('tabular-punto');
  }

  $effect(() => {
    if (!datos || rangoTablaIniciado) return;
    tablaDesde = ventanaInicial[0];
    tablaHasta = ventanaInicial[2];
    rangoTablaIniciado = true;
  });

  $effect(() => {
    if (!visible || !tablero || !datos) return;

    mostrarFuncion;
    curvasOcultas;
    mostrarDerivada;
    mostrarCuadricula;
    mostrarEjes;
    puntoActivo;
    tangenteActiva;
    secanteActiva;
    xAnalisis;
    deltaSecante;
    pantallaCompleta;
    preferencias.tema;

    noSePudoDibujar = false;
    let pizarra;
    let observadorTamano;
    try {
      if (!tablero.id) {
        tablero.id = 'jxg-' + Math.random().toString(36).slice(2, 10);
      }

      const estilo = getComputedStyle(tablero);
      const colorEje = estilo.getPropertyValue('--trazo-fuerte').trim() || estilo.getPropertyValue('--trazo').trim();
      const colorTexto = estilo.getPropertyValue('--ink-secondary').trim() || estilo.getPropertyValue('--ink-tertiary').trim();
      const bbox = cajaProporcional(chip ? [-5, 2, 5, -2] : ventanaInicial);

      const interactiva = !chip && (!compacto || pantallaCompleta);
      pizarra = JXG.JSXGraph.initBoard(tablero.id, {
        boundingbox: bbox,
        axis: false,
        showCopyright: false,
        showNavigation: false,
        keepAspectRatio: true,
        pan: { enabled: interactiva, needShift: false, needTwoFingers: false },
        zoom: {
          enabled: interactiva,
          wheel: interactiva,
          needShift: false,
          factorX: 1.18,
          factorY: 1.18,
          pinchHorizontal: true,
          pinchVertical: true
        }
      });

      pizarraActual = pizarra;

      if (!chip && mostrarEjes) {
        pizarra.create('axis', [[0, 0], [1, 0]], {
          strokeColor: colorEje,
          strokeWidth: 1.65,
          name: 'x',
          withLabel: true,
          label: { position: 'rt', offset: [-14, 14], strokeColor: colorTexto, fontSize: 13 },
          highlight: false,
          ticks: { visible: false }
        });
        pizarra.create('axis', [[0, 0], [0, 1]], {
          strokeColor: colorEje,
          strokeWidth: 1.65,
          name: 'y',
          withLabel: true,
          label: { position: 'rt', offset: [-18, -14], strokeColor: colorTexto, fontSize: 13 },
          highlight: false,
          ticks: { visible: false }
        });
      }

      trazar(pizarra);
      trazarAnalisis(pizarra);
      let ultimaCaja = '';
      const actualizarEscala = () => {
        const caja = pizarra.getBoundingBox();
        const firma = caja.map((numero) => numero.toPrecision(9)).join(',');
        if (firma === ultimaCaja) return;
        ultimaCaja = firma;
        marcasVista = reticulaDeEscala(caja, tablero.clientWidth, tablero.clientHeight);
      };
      pizarra.on('boundingbox', actualizarEscala);
      actualizarEscala();
      observadorTamano = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => {
        pizarra.updateContainerDims?.();
        ultimaCaja = '';
        actualizarEscala();
      });
      observadorTamano?.observe(tablero);
      if (!chip && !generacionAnotada) {
        generacionAnotada = true;
        anotar('grafica.generada');
      }
    } catch {
      noSePudoDibujar = true;
      if (pizarra) JXG.JSXGraph.freeBoard(pizarra);
      return;
    }

    return () => {
      observadorTamano?.disconnect();
      if (pizarraActual === pizarra) pizarraActual = null;
      JXG.JSXGraph.freeBoard(pizarra);
    };
  });

  function trazar(pizarra) {
    const estilo = getComputedStyle(tablero);
    const colorFuncion = estilo.getPropertyValue('--color-violet-light').trim();
    const colorDerivada = estilo.getPropertyValue('--color-amber-chart').trim();

    const paleta = [
      colorFuncion,
      estilo.getPropertyValue('--color-sky-light').trim(),
      estilo.getPropertyValue('--color-emerald-light').trim(),
      estilo.getPropertyValue('--color-rose-light').trim()
    ];
    if (mostrarFuncion) {
      curvas.forEach((curva, indice) => {
        if (!curvasOcultas.includes(indice)) {
          trazarCurva(
            pizarra, curva.evaluar, paleta[indice], false,
            curva.dominio ? curva.dominio.puntos.filter(p => p.tipo !== 'continuo').map(p => p.x)
              : destinoNumerico(curva.limite_x ?? curva.limite_destino)
          );
        }
      });
    }
    if (datos.derivada_js && mostrarDerivada) {
      trazarCurva(pizarra, derivada, colorDerivada, true);
    }
    if (!chip) {
      curvas.forEach((curva, indice) => {
        if (curva.dominio && !curvasOcultas.includes(indice)) {
          curva.dominio.puntos.forEach(p => trazarPuntoVerificado(pizarra, p, paleta[indice], curva.tipo));
          return;
        }
        const punto = destinoNumerico(curva.limite_x ?? curva.limite_destino);
        if (punto !== null && curva.evaluar && !curvasOcultas.includes(indice)) {
          trazarDestino(pizarra, punto, paleta[indice], curva.evaluar);
        }
      });
    }
  }

  function trazarPuntoVerificado(pizarra, punto, color, tipo) {
    if (!Number.isFinite(punto.x)) return;
    const estilo = getComputedStyle(tablero);
    const fondo = estilo.getPropertyValue('--surface-paper').trim();
    const texto = estilo.getPropertyValue('--ink-primary').trim();
    const marcar = (y, abierto, nombre) => {
      if (!Number.isFinite(y)) return;
      const marca = pizarra.create('point', [punto.x, y], {
        name: nombre, size: abierto ? 5 : 3, fixed: true, highlight: false,
        strokeWidth: 2, strokeColor: color, fillColor: abierto ? fondo : color,
        layer: 12, label: { strokeColor: texto, fontSize: 12 }
      });
      marca.rendNode?.setAttribute('data-punto-dominio', abierto ? 'abierto' : 'cerrado');
      marca.rendNode?.setAttribute('data-abscisa', String(punto.x));
    };
    if (punto.tipo === 'asintota') {
      pizarra.create('line', [[punto.x, 0], [punto.x, 1]], {
        strokeColor: color, dash: 2, strokeOpacity: .5, strokeWidth: 1,
        fixed: true, highlight: false
      });
    }
    if (Number.isFinite(punto.limite) && punto.valor !== punto.limite) marcar(punto.limite, true, 'Límite');
    if (punto.tipo === 'salto') {
      if (punto.izquierda !== punto.valor) marcar(punto.izquierda, true, 'izq.');
      if (punto.derecha !== punto.valor) marcar(punto.derecha, true, 'der.');
    }
    if (punto.estado === 'definida') marcar(punto.valor, false, tipo === 'derivada' ? 'f′(a)' : 'f(a)');
  }

  function trazarDestino(pizarra, a, color, evaluar) {
    const caja = pizarra.getBoundingBox();
    if (a < caja[0] || a > caja[2]) return;
    pizarra.create('line', [[a, 0], [a, 1]], {
      strokeColor: color, strokeWidth: 1.4, dash: 2, strokeOpacity: 0.65,
      fixed: true, highlight: false
    });
    const escala = Math.max(1e-5, (caja[2] - caja[0]) / 20000);
    const izquierda = evaluar(a - escala);
    const derecha = evaluar(a + escala);
    const enPunto = evaluar(a);
    const estilo = getComputedStyle(tablero);
    const fondo = estilo.getPropertyValue('--surface-paper').trim();
    const texto = estilo.getPropertyValue('--ink-primary').trim();
    const aproximado = (y, nombre) => {
      if (!Number.isFinite(y)) return;
      pizarra.create('point', [a, y], {
        name: nombre, size: 4, fixed: true, highlight: false,
        strokeColor: color, fillColor: fondo,
        label: { strokeColor: texto, fontSize: 13, cssStyle: 'font-weight: 700' }
      });
    };
    if (Number.isFinite(izquierda) && Number.isFinite(derecha)) {
      if (Math.abs(izquierda - derecha) <= Math.max(0.015, Math.abs(izquierda) * 0.01)) {
        if (!Number.isFinite(enPunto) || Math.abs(enPunto - izquierda) > 0.015) {
          aproximado((izquierda + derecha) / 2, 'Aproximación');
        }
      } else {
        aproximado(izquierda, 'izq.');
        aproximado(derecha, 'der.');
      }
    }
    if (Number.isFinite(enPunto)) {
      pizarra.create('point', [a, enPunto], {
        name: 'f(a)', size: 3, fixed: true, highlight: false,
        strokeColor: color, fillColor: color,
        label: { strokeColor: texto, fontSize: 13, cssStyle: 'font-weight: 700' }
      });
    }
  }

  function trazarCurva(pizarra, f, color, discontinua, separarEn = null) {
    if (!f) return;
    const atributos = {
      strokeWidth: discontinua ? 2.2 : 3,
      dash: discontinua ? 2 : 0,
      highlight: false
    };
    if (color) atributos.strokeColor = color;
    if (Array.isArray(separarEn)) {
      const cortes = [...new Set(separarEn.filter(Number.isFinite))].sort((a, b) => a - b);
      const fronteras = [-Infinity, ...cortes, Infinity];
      for (let i = 0; i < fronteras.length - 1; i += 1) {
        const desde = fronteras[i], hasta = fronteras[i + 1];
        protegerTrazadoSVG(pizarra.create('functiongraph', [(x) => x > desde && x < hasta ? f(x) : NaN], atributos));
      }
      return;
    }
    if (separarEn !== null) {
      protegerTrazadoSVG(pizarra.create('functiongraph', [(x) => x < separarEn ? f(x) : NaN], atributos));
      protegerTrazadoSVG(pizarra.create('functiongraph', [(x) => x > separarEn ? f(x) : NaN], atributos));
    } else {
      protegerTrazadoSVG(pizarra.create('functiongraph', [f], atributos));
    }
  }

  function trazarAnalisis(pizarra) {
    if (chip || (compacto && !pantallaCompleta) ||
        !(puntoActivo || tangenteActiva || secanteActiva) || !funcion) return;
    const y = funcion(Number(xAnalisis));
    if (!Number.isFinite(y)) return;
    const estilo = getComputedStyle(tablero);
    const color = estilo.getPropertyValue('--color-amber-chart').trim();
    const fondo = estilo.getPropertyValue('--surface-paper').trim();
    const texto = estilo.getPropertyValue('--ink-primary').trim();
    const punto = pizarra.create('point', [Number(xAnalisis), y], {
      name: 'P', size: 4, fixed: true, highlight: false,
      strokeColor: color, fillColor: fondo, label: { strokeColor: texto, fontSize: 13 }
    });
    if (tangenteActiva && tangente?.disponible) {
      const auxiliar = pizarra.create(
        'point',
        [Number(xAnalisis) + 1, y + tangente.pendiente],
        { visible: false }
      );
      pizarra.create('line', [punto, auxiliar], {
        strokeColor: color, strokeWidth: 2, dash: 1, fixed: true
      });
    }
    if (secanteActiva) {
      const otroX = Number(xAnalisis) + Number(deltaSecante);
      const otroY = funcion(otroX);
      if (Number.isFinite(otroY)) {
        const otro = pizarra.create('point', [otroX, otroY], {
          name: 'Q', size: 3, fixed: true, highlight: false,
          strokeColor: color, fillColor: fondo, label: { strokeColor: texto, fontSize: 13 }
        });
        pizarra.create('line', [punto, otro], { strokeColor: color, strokeWidth: 2, dash: 2, fixed: true });
      }
    }
  }

  $effect(() => {
    const pizarra = pizarraActual;
    if (!pizarra || !mostrarMuestras || chip) return;
    const indice = Math.max(0, Math.min(Number(curvaTabulada) || 0, evaluadoresTabla.length - 1));
    const colorToken = ['--color-violet-light', '--color-sky-light', '--color-emerald-light', '--color-rose-light', '--color-amber-chart'][indice];
    const estilo = getComputedStyle(tablero);
    const color = estilo.getPropertyValue(colorToken).trim();
    const creados = [];
    for (const fila of puntosTabla) {
      const y = fila.valores[indice];
      if (y === null) continue;
      creados.push(pizarra.create('segment', [[fila.x, 0], [fila.x, y]], {
        strokeColor: color, strokeOpacity: 0.9, strokeWidth: 1.8,
        dash: 1, fixed: true, highlight: false
      }));
      creados.push(pizarra.create('point', [fila.x, y], {
        name: '', size: 3.5, fixed: true, highlight: false,
        strokeColor: color, fillColor: color
      }));
    }
    for (const objeto of creados) objeto.rendNode?.setAttribute('data-muestra-tabular', 'didaxia');
    return () => {
      if (pizarraActual !== pizarra) return;
      for (const objeto of creados) pizarra.removeObject(objeto);
    };
  });

  function ajustarVista() {
    pizarraActual?.setBoundingBox?.(cajaProporcional(), false);
    pizarraActual?.fullUpdate?.();
    anotarRango();
  }

  function zoom(factor) {
    const actual = pizarraActual?.getBoundingBox?.();
    if (!actual) return;
    const [izq, arriba, der, abajo] = actual;
    const cx = (izq + der) / 2;
    const cy = (arriba + abajo) / 2;
    const ancho = ((der - izq) * factor) / 2;
    const alto = ((arriba - abajo) * factor) / 2;
    pizarraActual.setBoundingBox([cx - ancho, cy + alto, cx + ancho, cy - alto], false);
    anotarInteraccion(factor < 1 ? 'acercar' : 'alejar');
    anotarRango();
  }

  function alternarPantallaCompleta() {
    pantallaCompleta = !pantallaCompleta;
    if (pantallaCompleta) anotar('grafica.abierta', { vista: 'ampliada' });
    setTimeout(() => pizarraActual?.updateContainerDims?.(), 0);
  }

  function cerrarConEscape(evento) {
    if (pantallaCompleta && evento.key === 'Escape') alternarPantallaCompleta();
  }

  function instantanea(opciones = opcionesExportacion) {
    const raiz = pizarraActual?.renderer?.svgRoot;
    if (!raiz) {
      estadoExportacion = 'No se pudo preparar la exportación.';
      return null;
    }
    const copia = raiz.cloneNode(true);
    copia.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    const limites = raiz.getBoundingClientRect();
    const ancho = Math.max(1, Math.round(limites.width || tablero?.clientWidth || 800));
    const alto = Math.max(1, Math.round(limites.height || tablero?.clientHeight || 500));
    copia.setAttribute('width', String(ancho));
    copia.setAttribute('height', String(alto));
    copia.setAttribute('viewBox', `0 0 ${ancho} ${alto}`);
    const estiloTema = getComputedStyle(tablero);
    const fondo = estiloTema.getPropertyValue('--surface-paper').trim();
    agregarFondoDeTema(copia, ancho, alto, fondo);
    if (!opciones.guias) copia.querySelectorAll('[data-muestra-tabular="didaxia"]').forEach((nodo) => nodo.remove());
    const svgNS = 'http://www.w3.org/2000/svg';
    if (opciones.cuadricula && mostrarCuadricula) {
      const reticula = tablero?.parentElement?.querySelector('.reticula');
      if (reticula) {
        const grupo = document.createElementNS(svgNS, 'g');
        grupo.setAttribute('data-reticula-exportada', 'didaxia');
        const color = estiloTema.getPropertyValue('--ink-tertiary').trim() || estiloTema.getPropertyValue('--trazo-fuerte').trim();
        const oscuro = temaVisible() === 'oscuro';
        for (const [selector, opacidad, grosor] of [['.lineas-menores', oscuro ? '.27' : '.13', '.55'], ['.lineas-mayores', oscuro ? '.58' : '.38', '.9']]) {
          const lineas = reticula.querySelector(selector)?.cloneNode(true);
          if (!lineas) continue;
          lineas.setAttribute('stroke', color);
          lineas.setAttribute('stroke-opacity', opacidad);
          lineas.setAttribute('stroke-width', grosor);
          grupo.appendChild(lineas);
        }
        copia.insertBefore(grupo, copia.children[1] ?? null);
      }
    }
    if (opciones.valores && mostrarEjes) {
      const rotulos = tablero?.parentElement?.querySelector('.escalas');
      if (rotulos) {
        const grupo = document.createElementNS(svgNS, 'g');
        grupo.setAttribute('data-valores-exportados', 'didaxia');
        grupo.setAttribute('font-family', 'Arial, sans-serif');
        grupo.setAttribute('font-size', '12');
        grupo.setAttribute('fill', estiloTema.getPropertyValue('--ink-primary').trim() || estiloTema.getPropertyValue('--ink-secondary').trim());
        grupo.setAttribute('stroke', fondo);
        grupo.setAttribute('stroke-width', '3');
        grupo.setAttribute('paint-order', 'stroke');
        for (const rotulo of rotulos.querySelectorAll('text')) grupo.appendChild(rotulo.cloneNode(true));
        copia.appendChild(grupo);
      }
    }
    agregarMarcaDeAgua(
      copia,
      ancho,
      alto,
      getComputedStyle(document.documentElement).getPropertyValue('--accent-main').trim(),
    );
    if (opciones.notas) agregarNotasDeAnalisis(copia, ancho, alto, notasVisibles, {
      fondo,
      texto: estiloTema.getPropertyValue('--ink-primary').trim(),
      borde: estiloTema.getPropertyValue('--trazo-fuerte').trim(),
      acento: estiloTema.getPropertyValue('--accent-main').trim()
    });
    return {
      svg: new XMLSerializer().serializeToString(copia),
      ancho,
      alto,
      fondo
    };
  }

  function descargarTexto(contenido, nombre, tipo) {
    descargarBlob(new Blob([contenido], { type: tipo }), nombre);
  }

  function exportarRaster(captura, formato) {
    const imagen = new Image();
    imagen.onload = () => {
      const escala = 2;
      const lienzo = document.createElement('canvas');
      lienzo.width = captura.ancho * escala;
      lienzo.height = captura.alto * escala;
      const contexto = lienzo.getContext('2d');
      if (!contexto) {
        estadoExportacion = 'El navegador no permite crear la imagen.';
        return;
      }
      contexto.fillStyle = captura.fondo;
      contexto.fillRect(0, 0, lienzo.width, lienzo.height);
      contexto.drawImage(imagen, 0, 0, lienzo.width, lienzo.height);
      const tipo = formato === 'png' ? 'image/png' : 'image/jpeg';
      try {
        lienzo.toBlob((blob) => {
          if (!blob) { estadoExportacion = 'No se pudo preparar la imagen.'; return; }
          descargarBlob(blob, `grafica-didaxia.${formato}`);
          estadoExportacion = `Gráfica preparada como ${formato.toUpperCase()}.`;
          anotar('grafica.exportada', { formato, tema: temaVisible() });
        }, tipo, 0.95);
      } catch { estadoExportacion = 'No se pudo preparar la imagen.'; }
    };
    imagen.onerror = () => (estadoExportacion = 'No se pudo convertir la gráfica a imagen.');
    imagen.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(captura.svg)}`;
  }

  function exportarHtml(captura) {
    const documento = `<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Gráfica de DidaxIa</title><style>html,body{margin:0;min-height:100%;background:${captura.fondo}}body{display:grid;place-items:center;padding:24px;box-sizing:border-box}svg{max-width:100%;height:auto}</style></head><body>${captura.svg}</body></html>`;
    descargarTexto(documento, 'grafica-didaxia.html', 'text/html;charset=utf-8');
    estadoExportacion = 'Gráfica exportada como HTML.';
    anotar('grafica.exportada', { formato: 'html', tema: temaVisible() });
  }

  function exportarPdf(captura) {
    const ventana = window.open('', '_blank');
    if (!ventana) {
      estadoExportacion = 'El navegador bloqueó la ventana de impresión.';
      return;
    }
    ventana.document.write(`<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Gráfica de DidaxIa</title><style>@page{margin:12mm}html,body{margin:0;background:${captura.fondo}}body{display:grid;place-items:center;min-height:100vh}svg{max-width:100%;height:auto}</style></head><body>${captura.svg}</body></html>`);
    ventana.document.close();
    ventana.focus();
    setTimeout(() => ventana.print(), 250);
    estadoExportacion = 'Elige «Guardar como PDF» en la ventana de impresión.';
    anotar('grafica.exportada', { formato: 'pdf', tema: temaVisible() });
  }

  function ejecutarExportacion(formato, opciones = opcionesExportacion) {
    const captura = instantanea(opciones);
    if (!captura) return;
    if (formato === 'svg') {
      descargarTexto(captura.svg, 'grafica-didaxia.svg', 'image/svg+xml;charset=utf-8');
      estadoExportacion = 'Gráfica exportada como SVG.';
      anotar('grafica.exportada', { formato: 'svg', tema: temaVisible() });
    } else if (formato === 'html') {
      exportarHtml(captura);
    } else if (formato === 'pdf') {
      exportarPdf(captura);
    } else {
      exportarRaster(captura, formato);
    }
  }

  function exportar(evento) {
    const formato = evento.currentTarget.value;
    evento.currentTarget.value = '';
    if (!formato) return;
    formatoPendiente = formato;
    opcionesExportacion = { cuadricula: mostrarCuadricula, valores: mostrarEjes, guias: mostrarMuestras, notas: notasVisibles.length > 0 };
    confirmacionExportacion = true;
  }

  function decidirExportacion() {
    const formato = formatoPendiente;
    confirmacionExportacion = false;
    formatoPendiente = '';
    if (formato) { ejecutarExportacion(formato, opcionesExportacion); toast.descarga(formato === 'pdf' ? 'Abriendo impresión para guardar la gráfica en PDF.' : `Preparando gráfica en ${formato.toUpperCase()}…`); }
  }

  function elegirSeccionMovil(seccion) {
    if (seccion === 'tabla' && seccionMovil !== 'tabla') tablaOrdenada = true;
    if (seccion !== 'tabla') editorNumero = null;
    if (seccion === 'funciones' && alAlternarFunciones) {
      const estabaAbierta = funcionesAbiertas;
      alAlternarFunciones();
      seccionMovil = estabaAbierta ? '' : 'funciones';
    } else {
      alCerrarFunciones?.();
      seccionMovil = seccionMovil === seccion ? '' : seccion;
    }
    tabulacionAbierta = seccionMovil === 'tabla';
  }

  $effect.pre(() => {
    if (tabulacionAbierta && !tablaEstabaAbierta) tablaOrdenada = true;
    tablaEstabaAbierta = tabulacionAbierta;
  });

  $effect(() => {
    alturaPanelMovil;
    panelMovilAbierto;
    if (pizarraActual && (laboratorio || pantallaCompleta)) {
      requestAnimationFrame(() => requestAnimationFrame(() => pizarraActual?.updateContainerDims?.()));
    }
  });
</script>

<svelte:window onkeydown={cerrarConEscape} />

<figure class="grafica" class:compacto class:chip class:laboratorio class:inmersiva class:pantalla-completa={pantallaCompleta}
        class:panel-movil-abierto={panelMovilAbierto}
        style={`--altura-panel-movil: ${alturaPanelMovil}px`} use:observarApertura>
  {#if visible && datos && !chip}
    <div class="barra-grafica" aria-label="Herramientas de la gráfica">
      <div class="herramientas-desplazables">
        <div class="grupo-herramientas">
          <span class="rotulo-grupo">Curvas</span>
          {#if curvas.length > 1}
            {#each curvas as curva, indice}
              <button type="button" class:activo={!curvasOcultas.includes(indice)}
                      aria-pressed={!curvasOcultas.includes(indice)}
                      onclick={() => alternarCurva(indice)}>
                <i class={`muestra serie-${indice}`}></i>{nombreCurva(curva, indice)}
              </button>
            {/each}
          {:else}
            <button type="button" class:activo={mostrarFuncion} aria-pressed={mostrarFuncion} onclick={() => (mostrarFuncion = !mostrarFuncion)}><i class="muestra funcion"></i>{nombreCurva(curvas[0], 0)}</button>
          {/if}
          {#if datos.derivada_js}
            <button type="button" class:activo={mostrarDerivada} aria-pressed={mostrarDerivada} onclick={() => (mostrarDerivada = !mostrarDerivada)}><i class="muestra derivada"></i>f′({variablePresentada})</button>
          {/if}
        </div>
        <div class="grupo-herramientas">
          <span class="rotulo-grupo">Vista</span>
          <button type="button" class:activo={mostrarEjes} aria-pressed={mostrarEjes} onclick={() => (mostrarEjes = !mostrarEjes)}>Ejes</button>
          <button type="button" class:activo={mostrarCuadricula} aria-pressed={mostrarCuadricula} onclick={() => (mostrarCuadricula = !mostrarCuadricula)}>Cuadrícula</button>
          <button use:ayudaContextual type="button" onclick={() => zoom(0.8)} title="Acercar" aria-label="Acercar">＋</button>
          <button use:ayudaContextual type="button" onclick={() => zoom(1.25)} title="Alejar" aria-label="Alejar">−</button>
          <button use:ayudaContextual type="button" onclick={ajustarVista} title="Ajustar la gráfica a la función">Ajustar</button>
        </div>
        {#if !compacto || pantallaCompleta}
          <div class="grupo-herramientas">
            <span class="rotulo-grupo">Explorar</span>
            <button type="button" class:activo={puntoActivo} aria-pressed={puntoActivo} onclick={() => (puntoActivo = !puntoActivo)}>Punto</button>
            <button type="button" class:activo={tangenteActiva} aria-pressed={tangenteActiva} onclick={alternarTangente}>Tangente</button>
            <button type="button" class:activo={secanteActiva} aria-pressed={secanteActiva} onclick={alternarSecante}>Secante</button>
          </div>
          {#if puntoActivo || tangenteActiva || secanteActiva}
            <label>x <input type="number" step="0.25" bind:value={xAnalisis}
                            onchange={() => anotarRango('x')} /></label>
          {/if}
          {#if secanteActiva}
            <label>Δx <input type="number" min="0.01" step="0.25" bind:value={deltaSecante}
                             onchange={() => anotarRango('x')} /></label>
          {/if}
          <label class="exportacion grupo-herramientas">
            <span class="rotulo-grupo">Exportar</span>
            <select use:menuDesplegable aria-label="Formato de exportación" onchange={exportar}>
              <option value="">Formato…</option>
              <option value="svg">SVG</option>
              <option value="png">PNG</option>
              <option value="jpg">JPG</option>
              <option value="html">HTML</option>
              <option value="pdf">PDF</option>
            </select>
          </label>
        {/if}
        {#if !soloLectura}<ReportarProblema
          compacto
          presentacion="grafica"
          etiqueta="Reportar error"
          etiquetaAria="Reportar un error en esta gráfica"
          categoriaInicial="visual"
          tituloInicial="Error en una gráfica matemática"
          contexto={contextoReporte}
        />{/if}
      </div>
      {#if !pantallaCompleta}
        <button type="button" class="ampliar" onclick={alternarPantallaCompleta}>Ampliar</button>
      {/if}
    </div>
    {#if pantallaCompleta}
      <button use:ayudaContextual type="button" class="cerrar-ampliada" aria-label="Cerrar gráfica ampliada"
              title="Cerrar gráfica ampliada" onclick={alternarPantallaCompleta}>×</button>
    {/if}
  {/if}
  {#if laboratorio && !pantallaCompleta && panelEscritorio === 'herramientas'}
    <aside class="cajon-grafica-escritorio" aria-label="Herramientas de análisis">
      <h2>Herramientas</h2>
      <p>Explora la curva y compara puntos en el plano.</p>
      <div class="opciones-cajon">
        <button type="button" aria-pressed={puntoActivo} onclick={() => puntoActivo = !puntoActivo}>• Punto notable</button>
        <button type="button" aria-pressed={tangenteActiva} onclick={alternarTangente}>∠ Tangente</button>
        <button type="button" aria-pressed={secanteActiva} onclick={alternarSecante}>╱ Secante</button>
      </div>
      {#if puntoActivo || tangenteActiva || secanteActiva}
        <label>Valor de x <input type="number" step="0.25" bind:value={xAnalisis} onchange={() => anotarRango('x')} /></label>
      {/if}
      {#if secanteActiva}<label>Separación Δx <input type="number" step="0.25" bind:value={deltaSecante} onchange={() => anotarRango('x')} /></label>{/if}
    </aside>
  {:else if laboratorio && !pantallaCompleta && panelEscritorio === 'ajustes'}
    <aside class="cajon-grafica-escritorio" aria-label="Ajustes de la gráfica">
      <h2>Ajustes</h2>
      <div class="opciones-cajon">
        <label><input type="checkbox" bind:checked={mostrarEjes} /> Ejes</label>
        <label><input type="checkbox" bind:checked={mostrarCuadricula} /> Cuadrícula</label>
        <label><input type="checkbox" bind:checked={mostrarMuestras} /> Puntos y guías de tabla</label>
        <label>Orden de la tabla <select use:menuDesplegable={ordenTabla} bind:value={ordenTabla}><option value="ascendente">Menor a mayor</option><option value="descendente">Mayor a menor</option></select></label>
        <fieldset class="preferencias-analisis"><legend>Tangente</legend>
          <label><input type="checkbox" bind:checked={abrirTangenteAlActivar} /> Abrir explicación</label>
          <label><input type="checkbox" bind:checked={textoTangenteVisible} /> Mostrar texto</label>
          <label><input type="checkbox" bind:checked={formulaTangenteVisible} /> Mostrar fórmula</label>
        </fieldset>
        <fieldset class="preferencias-analisis"><legend>Secante</legend>
          <label><input type="checkbox" bind:checked={abrirSecanteAlActivar} /> Abrir explicación</label>
          <label><input type="checkbox" bind:checked={textoSecanteVisible} /> Mostrar texto</label>
          <label><input type="checkbox" bind:checked={formulaSecanteVisible} /> Mostrar fórmula</label>
        </fieldset>
        <label>Exportar <select use:menuDesplegable aria-label="Formato de exportación" onchange={exportar}>
          <option value="">Formato…</option><option value="svg">SVG</option><option value="png">PNG</option>
          <option value="jpg">JPG</option><option value="html">HTML</option><option value="pdf">PDF</option>
        </select></label>
        {#if alGuardarFunciones && hayFuncionesParaGuardar}<button type="button" onclick={alGuardarFunciones}>Guardar funciones en archivo</button>{/if}
        {#if alCargarFunciones}<label>Cargar funciones guardadas <input type="file" accept="application/json,.json" onchange={alCargarFunciones} /></label>{/if}
      </div>
    </aside>
  {/if}
  {#if laboratorio && !pantallaCompleta}
    <div class="controles-lienzo-escritorio" role="group" aria-label="Controles del plano">
      <button use:ayudaContextual type="button" title="Restablecer vista" aria-label="Restablecer vista" onclick={ajustarVista}>⌂</button>
      <button use:ayudaContextual type="button" title="Acercar" aria-label="Acercar" onclick={() => zoom(0.8)}>＋</button>
      <button use:ayudaContextual type="button" title="Alejar" aria-label="Alejar" onclick={() => zoom(1.25)}>−</button>
      <button use:ayudaContextual type="button" title="Ampliar" aria-label="Ampliar gráfica" onclick={alternarPantallaCompleta}>⛶</button>
    </div>
  {/if}
  {#if visible && datos && (laboratorio || pantallaCompleta)}
    <nav class="navegacion-movil" aria-label="Secciones de la gráfica">
      <button type="button" class:activa={funcionesAbiertas || (!alAlternarFunciones && seccionMovil === 'funciones')}
              aria-pressed={funcionesAbiertas || (!alAlternarFunciones && seccionMovil === 'funciones')}
              onclick={() => elegirSeccionMovil('funciones')}><span aria-hidden="true">ƒ</span>Funciones</button>
      <button type="button" class:activa={seccionMovil === 'herramientas'} aria-pressed={seccionMovil === 'herramientas'}
              onclick={() => elegirSeccionMovil('herramientas')}><span aria-hidden="true">⌖</span>Herramientas</button>
      <button type="button" class:activa={seccionMovil === 'tabla'} aria-pressed={seccionMovil === 'tabla'}
              onclick={() => elegirSeccionMovil('tabla')}><span aria-hidden="true">▦</span>Tabla</button>
      <button type="button" class:activa={seccionMovil === 'ajustes'} aria-pressed={seccionMovil === 'ajustes'}
              onclick={() => elegirSeccionMovil('ajustes')}><span aria-hidden="true">⚙</span>Ajustes</button>
    </nav>
    {#if seccionMovil === 'funciones' && !alAlternarFunciones}
      <section class="panel-movil-grafica" aria-label="Funciones del tutor">
        <AsaPanelGrafica bind:altura={alturaPanelMovil} />
        <h3>Funciones</h3>
        {#each curvas as curva, indice}
          <button type="button" aria-pressed={!curvasOcultas.includes(indice)}
                  onclick={() => alternarCurva(indice)}>
            <i class={`muestra serie-${indice}`}></i>{nombreCurva(curva, indice)} · {curva.expresion || 'curva disponible'}
          </button>
        {/each}
      </section>
    {:else if seccionMovil === 'herramientas'}
      <section class="panel-movil-grafica" aria-label="Herramientas de análisis">
        <AsaPanelGrafica bind:altura={alturaPanelMovil} />
        <h3>Herramientas</h3>
        <div class="cuadricula-herramientas">
          <button type="button" aria-pressed={puntoActivo} onclick={() => (puntoActivo = !puntoActivo)}><span aria-hidden="true">•</span>Punto</button>
          <button type="button" aria-pressed={tangenteActiva} onclick={alternarTangente}><span aria-hidden="true">∠</span>Tangente</button>
          <button type="button" aria-pressed={secanteActiva} onclick={alternarSecante}><span aria-hidden="true">╱</span>Secante</button>
          <button type="button" onclick={() => zoom(0.8)}><span aria-hidden="true">＋</span>Acercar</button>
          <button type="button" onclick={() => zoom(1.25)}><span aria-hidden="true">−</span>Alejar</button>
          <button type="button" onclick={ajustarVista}><span aria-hidden="true">⌂</span>Recentrar</button>
        </div>
        {#if puntoActivo || tangenteActiva || secanteActiva}
          <div class="parametros-herramientas"><label>x <input type="number" step="0.25" bind:value={xAnalisis} onchange={() => anotarRango('x')} /></label>
          {#if secanteActiva}<label>Δx <input type="number" step="0.25" bind:value={deltaSecante} onchange={() => anotarRango('x')} /></label>{/if}</div>
        {/if}
      </section>
    {:else if seccionMovil === 'ajustes'}
      <section class="panel-movil-grafica" aria-label="Ajustes de la gráfica">
        <AsaPanelGrafica bind:altura={alturaPanelMovil} />
        <h3>Ajustes</h3>
        <div class="ajustes-moviles">
          <label><input type="checkbox" bind:checked={mostrarEjes} /> Mostrar ejes</label>
          <label><input type="checkbox" bind:checked={mostrarCuadricula} /> Mostrar cuadrícula</label>
          <label><input type="checkbox" bind:checked={mostrarMuestras} /> Puntos de la tabla en la gráfica</label>
          <label>Orden al reabrir la tabla
            <select use:menuDesplegable={ordenTabla} bind:value={ordenTabla} aria-label="Orden de valores de la tabla">
              <option value="ascendente">De menor a mayor</option>
              <option value="descendente">De mayor a menor</option>
            </select>
          </label>
          <fieldset class="preferencias-analisis"><legend>Tangente</legend>
            <label><input type="checkbox" bind:checked={abrirTangenteAlActivar}
              onchange={() => { if (tangenteActiva) explicacionTangenteVisible = abrirTangenteAlActivar; }} /> Abrir explicación al activar</label>
            <label><input type="checkbox" bind:checked={textoTangenteVisible} /> Mostrar texto informativo</label>
            <label><input type="checkbox" bind:checked={formulaTangenteVisible} /> Mostrar fórmula</label>
          </fieldset>
          <fieldset class="preferencias-analisis"><legend>Secante</legend>
            <label><input type="checkbox" bind:checked={abrirSecanteAlActivar}
              onchange={() => { if (secanteActiva) explicacionSecanteVisible = abrirSecanteAlActivar; }} /> Abrir explicación al activar</label>
            <label><input type="checkbox" bind:checked={textoSecanteVisible} /> Mostrar texto informativo</label>
            <label><input type="checkbox" bind:checked={formulaSecanteVisible} /> Mostrar fórmula</label>
          </fieldset>
          {#if datos.derivada_js}<label><input type="checkbox" bind:checked={mostrarDerivada} /> Mostrar derivada</label>{/if}
          <label>Exportar <select use:menuDesplegable aria-label="Formato de exportación móvil" onchange={exportar}>
            <option value="">Formato…</option><option value="svg">SVG</option><option value="png">PNG</option>
            <option value="jpg">JPG</option><option value="html">HTML</option><option value="pdf">PDF</option>
          </select></label>
          {#if alGuardarFunciones && hayFuncionesParaGuardar}
            <button type="button" onclick={alGuardarFunciones}>Guardar funciones en archivo</button>
          {/if}
          {#if alCargarFunciones}<label class="cargar-funciones">Cargar funciones desde archivo
            <input type="file" accept="application/json,.json" onchange={alCargarFunciones} />
          </label>{/if}
          {#if !soloLectura}<ReportarProblema compacto presentacion="grafica" etiqueta="Reportar error"
            etiquetaAria="Reportar un error en esta gráfica" categoriaInicial="visual"
            tituloInicial="Error en una gráfica matemática" contexto={contextoReporte} />{/if}
        </div>
        {#if estadoExportacion}<p role="status">{estadoExportacion}</p>{/if}
      </section>
    {/if}
  {/if}
  {#if visible}
    <div class="escenario-grafica">
      <div class="lienzo" class:compacto class:chip role="img"
         onwheel={() => { anotarInteraccion('desplazar'); anotarRango(); }}
         onpointerup={() => anotarInteraccion('puntero')}
         aria-label={alternativo || (expresionPresentable ? `Gráfica de ${expresionPresentable}` : 'Gráfica matemática')}>
        {#if !chip && mostrarCuadricula}
          <svg class="reticula" viewBox={`0 0 ${marcasVista.ancho} ${marcasVista.alto}`} preserveAspectRatio="none" aria-hidden="true">
            <g class="lineas-menores">
              {#each marcasVista.menoresX as porcentaje}<line x1={porcentaje * marcasVista.ancho / 100} x2={porcentaje * marcasVista.ancho / 100} y1="0" y2={marcasVista.alto} />{/each}
              {#each marcasVista.menoresY as porcentaje}<line x1="0" x2={marcasVista.ancho} y1={marcasVista.alto * (1 - porcentaje / 100)} y2={marcasVista.alto * (1 - porcentaje / 100)} />{/each}
            </g>
            <g class="lineas-mayores">
              {#each marcasVista.x as marca (marca.texto)}<line x1={marca.porcentaje * marcasVista.ancho / 100} x2={marca.porcentaje * marcasVista.ancho / 100} y1="0" y2={marcasVista.alto} />{/each}
              {#each marcasVista.y as marca (marca.texto)}<line x1="0" x2={marcasVista.ancho} y1={marcasVista.alto * (1 - marca.porcentaje / 100)} y2={marcasVista.alto * (1 - marca.porcentaje / 100)} />{/each}
            </g>
          </svg>
        {/if}

        <div class="tablero" bind:this={tablero}>
          {#if !datos}
            <span class="pendiente">Gráfica no disponible</span>
          {:else if noSePudoDibujar}
            <span class="pendiente">No se pudo dibujar la gráfica</span>
          {/if}
        </div>
        {#if !chip && mostrarEjes}
          <svg class="escalas" viewBox={`0 0 ${marcasVista.ancho} ${marcasVista.alto}`} aria-hidden="true">
            {#each marcasVista.x as marca (marca.texto)}
              <text x={marca.porcentaje * marcasVista.ancho / 100} y={rotuloXEje} text-anchor="middle">{marca.texto}</text>
            {/each}
            {#each marcasVista.y as marca (marca.texto)}
              {#if marca.valor !== 0}<text x={marcasVista.ejeY + (marcasVista.rotuloYIzquierda ? -7 : 7)} y={marcasVista.alto * (1 - marca.porcentaje / 100) + 4} text-anchor={marcasVista.rotuloYIzquierda ? 'end' : 'start'}>{marca.texto}</text>{/if}
            {/each}
          </svg>
        {/if}
      </div>
      {#if datos && (!compacto || pantallaCompleta) && notasVisibles.length}
        <div class="notas-analisis" aria-label="Explicaciones de la gráfica">
          {#if tangenteActiva && explicacionTangenteVisible}
            <aside class="nota-analisis" data-nota="tangente" role="status">
              <div class="cabecera-nota"><strong>Recta tangente</strong>
                <button use:ayudaContextual type="button" aria-label="Cerrar explicación de tangente" title="Cerrar explicación" onclick={() => explicacionTangenteVisible = false}>×</button>
              </div>
              {#if tangente?.disponible}
                {#if textoTangenteVisible}<p>En a = {numero(tangente.x)}, f(a) = {numero(tangente.y)} y la pendiente es {numero(tangente.pendiente)}.</p>{/if}
                {#if formulaTangenteVisible}<div class="formula-nota"><Notacion expresion="y = f(a) + f'(a)(x - a)" /></div>{/if}
                {#if textoTangenteVisible}
                <button type="button" class="desplegar-proceso" aria-expanded={procesoTangenteVisible}
                        onclick={() => procesoTangenteVisible = !procesoTangenteVisible}>
                  {procesoTangenteVisible ? 'Ocultar proceso' : 'Ver proceso y resultado'}
                  <span aria-hidden="true">{procesoTangenteVisible ? '⌃' : '⌄'}</span>
                </button>
                {#if procesoTangenteVisible}
                  <ol class="pasos-analisis">
                    <li>Se evalúa el punto P = ({numero(tangente.x)}, {numero(tangente.y)}).</li>
                    <li>{tangente.origen === 'simbolica' ? 'La pendiente proviene de la derivada simbólica.' : 'La pendiente se estima numéricamente al comparar valores cercanos; es aproximada.'}</li>
                    <li>Se sustituyen punto y pendiente en la ecuación de la recta:
                      {#if formulaTangenteVisible}<div class="formula-nota"><Notacion expresion={`y = ${numero(tangente.y)} + ${numero(tangente.pendiente)}(x - ${puntoEnFormula(tangente.x)})`} /></div>{/if}
                    </li>
                  </ol>
                  <p>La recta tangente no es la curva f′(x).</p>
                {/if}
                {/if}
              {:else}
                <p>Tangente no disponible. {tangente?.motivo}</p>
              {/if}
            </aside>
          {/if}
          {#if secanteActiva && explicacionSecanteVisible}
            <aside class="nota-analisis" data-nota="secante" role="status">
              <div class="cabecera-nota"><strong>Recta secante</strong>
                <button use:ayudaContextual type="button" aria-label="Cerrar explicación de secante" title="Cerrar explicación" onclick={() => explicacionSecanteVisible = false}>×</button>
              </div>
              {#if secante?.disponible}
                {#if textoSecanteVisible}<p>Une P = ({numero(secante.x)}, {numero(secante.y)}) y Q = ({numero(secante.x + secante.delta)}, {numero(secante.otroY)}).</p>{/if}
                {#if formulaSecanteVisible}<div class="formula-nota"><Notacion expresion={'m = \\frac{f(a+\\Delta x)-f(a)}{\\Delta x}'} /></div>{/if}
                {#if textoSecanteVisible}
                <button type="button" class="desplegar-proceso" aria-expanded={procesoSecanteVisible}
                        onclick={() => procesoSecanteVisible = !procesoSecanteVisible}>
                  {procesoSecanteVisible ? 'Ocultar proceso' : 'Ver proceso y resultado'}
                  <span aria-hidden="true">{procesoSecanteVisible ? '⌃' : '⌄'}</span>
                </button>
                {#if procesoSecanteVisible}
                  <ol class="pasos-analisis">
                    <li>Se elige Δx = {numero(secante.delta)} y se calcula Q.</li>
                    <li>El cambio de altura {numero(secante.otroY - secante.y)} dividido entre Δx da la pendiente media {numero(secante.pendiente)}.</li>
                    <li>Se sustituye en la recta que pasa por P:
                      {#if formulaSecanteVisible}<div class="formula-nota"><Notacion expresion={`y = ${numero(secante.y)} + ${numero(secante.pendiente)}(x - ${puntoEnFormula(secante.x)})`} /></div>{/if}
                    </li>
                  </ol>
                {/if}
                {/if}
              {:else}
                <p>Secante no disponible. {secante?.motivo}</p>
              {/if}
            </aside>
          {/if}
        </div>
      {/if}
  {#if datos && !chip && (!compacto || pantallaCompleta)}
    <details class="tabulacion" bind:open={tabulacionAbierta}>
      <summary>Tabla<span class="detalle-tabla"> · valores próximos a puntos relevantes</span></summary>
      <div class="asa-tabla-movil"><AsaPanelGrafica bind:altura={alturaPanelMovil} /></div>
      <div class="titulo-tabla-con-ayuda"><h3 class="titulo-tabla-movil">Tabla de valores</h3>
        <BotonAyudaTooltip tamano="sm" posicion="abajo" texto="Puedes cambiar cualquier x, incluso fuera del intervalo, y añadir hasta 30 puntos. La curva y el zoom no cambian. El signo — indica que la función no está definida en ese valor. Al cerrar y reabrir, los puntos se ordenan como elegiste en Ajustes." ariaLabel="Cómo leer y editar la tabla" />
      </div>
      {#if expresionPresentable}<div class="formula-tabla"><Notacion expresion={expresionPresentable} compacto agrandar /></div>{/if}
      <button type="button" class="abrir-opciones-tabla" aria-expanded={opcionesTablaVisibles}
              onclick={() => opcionesTablaVisibles = !opcionesTablaVisibles}>
        {opcionesTablaVisibles ? 'Ocultar opciones' : 'Opciones de tabla'}
      </button>
      <div class="controles-tabla" class:visible-movil={opcionesTablaVisibles}>
        <button type="button" onclick={tomarRangoDeLaVista}>Usar rango visible</button>
        <button type="button" onclick={() => { abscisasManuales = {}; abscisasAdicionales = []; }}
          disabled={!Object.keys(abscisasManuales).length && !abscisasAdicionales.length}>Restablecer puntos</button>
        {#if movilTabla}
          <label>Desde x = <button type="button" class="valor-teclado" aria-label="Desde x ="
            onclick={(evento) => abrirNumero('desde', null, tablaDesde, 'Desde x', evento)}>{mostrarDecimalDeTabla(tablaDesde)}</button></label>
          <label>Hasta x = <button type="button" class="valor-teclado" aria-label="Hasta x ="
            onclick={(evento) => abrirNumero('hasta', null, tablaHasta, 'Hasta x', evento)}>{mostrarDecimalDeTabla(tablaHasta)}</button></label>
        {:else}
          <label>Desde x = <input type="number" step="any" bind:value={tablaDesde} /></label>
          <label>Hasta x = <input type="number" step="any" bind:value={tablaHasta} /></label>
        {/if}
        <label class="casilla"><input type="checkbox" bind:checked={mostrarMuestras} /> Mostrar puntos y guías en la gráfica</label>
        {#if !movilTabla}<label>Orden al reabrir
          <select use:menuDesplegable={ordenTabla} bind:value={ordenTabla} aria-label="Orden de valores de la tabla">
            <option value="ascendente">Menor a mayor</option>
            <option value="descendente">Mayor a menor</option>
          </select>
        </label>{/if}
        {#if evaluadoresTabla.length > 1}
          <label>Resaltar curva
            <select use:menuDesplegable={curvaTabulada} bind:value={curvaTabulada}>
              {#each nombresTabla as nombre, indice}<option value={indice}>{nombre}</option>{/each}
            </select>
          </label>
        {/if}
      </div>
      {#if puntosTabla.length}
        <div class="nuevo-punto-tabla">
          <button type="button" onclick={(evento) => abrirNumero('nuevo', null, '', 'Nuevo valor de X', evento)}>Añadir valor de X</button>
        </div>
        {#if mensajeAbscisa}<p class="mensaje-punto" role="status">{mensajeAbscisa}</p>{/if}
        <div class="tabla-desplazable tabla-matriz">
          <table>
            <caption>Valores de diez puntos del intervalo. «—» indica que la función no está definida.</caption>
            <thead><tr><th scope="col">x</th>{#each puntosTabla as fila, indice}<th scope="col"><input class="abscisa-manual" type="number" step="any" aria-label={`Valor x del punto ${indice + 1}`} value={numeroTabla(fila.x)} onchange={(evento) => editarAbscisaDesdeCampo(indice, evento)} /></th>{/each}</tr></thead>
            <tbody>
              {#each nombresTabla as nombre, indice}
                <tr><th scope="row" class={`serie-${indice}`}>{nombre}</th>
                  {#each puntosTabla as fila}<td class={`serie-${indice}`}>{numeroTabla(fila.valores[indice])}</td>{/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <div class="tabla-desplazable tabla-vertical-movil">
          <table>
            <caption>Valores de la gráfica. «—» indica que la función no está definida.</caption>
            <thead><tr><th scope="col">x</th>{#each nombresTabla as nombre, indice}<th scope="col" class={`serie-${indice}`}>{nombre}</th>{/each}</tr></thead>
            <tbody>
              {#each puntosTabla as fila, indice}
                <tr class:adicional={fila.origen === 'adicional'}><th scope="row">
                  {#if movilTabla}<button type="button" class="abscisa-manual valor-teclado"
                    aria-label={`Valor x del punto ${indice + 1}`}
                    onclick={(evento) => abrirNumero('punto', indice, fila.x, `Punto ${indice + 1}: x`, evento)}>{mostrarDecimalDeTabla(fila.x)}</button>
                  {:else}<input class="abscisa-manual" type="number" step="any"
                    aria-label={`Valor x del punto ${indice + 1}`} value={numeroTabla(fila.x)}
                    onchange={(evento) => editarAbscisaDesdeCampo(indice, evento)} />{/if}
                  {#if fila.origen === 'adicional'}<button type="button" class="quitar-punto"
                    aria-label={`Quitar punto añadido x = ${movilTabla ? mostrarDecimalDeTabla(fila.x) : numeroTabla(fila.x)}`}
                    onclick={() => quitarAbscisa(fila.indiceOrigen)}>×</button>{/if}</th>
                  {#each fila.valores as valor, curva}<td class={`serie-${curva}`}>{movilTabla ? mostrarDecimalDeTabla(valor) : numeroTabla(valor)}</td>{/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if destinoTabla !== null}<p class="nota-tabla">En {variablePresentada} = {numeroTabla(destinoTabla)}, f({variablePresentada}) puede no estar definida aunque la curva se aproxime a un valor. Contrasta ambos lados.</p>{/if}
      {:else}
        <p class="nota-tabla" role="alert">El extremo «Hasta» debe ser mayor que «Desde».</p>
      {/if}
    </details>
  {/if}
    </div>
  {/if}

  {#if editorNumero}
    <TecladoNumericoTabla etiqueta={editorNumero.etiqueta} bind:valor={editorNumero.texto}
      error={errorNumero} alAplicar={aplicarNumero} alCancelar={cerrarNumero} />
  {/if}


  {#if !chip}
    {#if curvas.length > 1}
      <figcaption>{curvas.length} funciones en el mismo plano. Los colores de la tabla corresponden a las curvas.</figcaption>
    {:else if expresionPresentable}
      <figcaption>
        <span>Gráfica de</span>
        <Notacion expresion={expresionPresentable} {alternativo} agrandar />
        {#if datos?.derivada_js}<span>y su derivada.</span>{/if}
      </figcaption>
    {:else if alternativo}
      <figcaption>{alternativo}</figcaption>
    {:else}
      <figcaption>Gráfica matemática</figcaption>
    {/if}
    {/if}
    {#if !chip && curvas.some(c => c.dominio)}
      <details class="detalle-dominio">
        <summary>Dominio y puntos especiales</summary>
        {#each curvas.filter(c => c.dominio) as curva, indice}
          <p><strong>Curva {indice + 1}</strong> · {curva.dominio.alcance}</p>
          {#each curva.dominio.puntos as punto}<p>{describirPunto(punto, curva.tipo, curva.variable, curva.nombre_funcion)}</p>{/each}
          {#if curva.resultado_limite}
            <p>Límite solicitado{curva.resultado_limite.direccion ? ` por la ${curva.resultado_limite.direccion === '+' ? 'derecha' : 'izquierda'}` : ''}: {curva.resultado_limite.valor ?? curva.resultado_limite.estado}.</p>
          {/if}
        {/each}
      </details>
    {/if}
  </figure>

<Dialogo bind:abierto={confirmacionExportacion} tipo="descarga" titulo="Elegir elementos de la exportación" aria-label="Elegir elementos de la exportación" ancho="32rem">
  <p>Selecciona lo que conservará la imagen {formatoPendiente.toUpperCase()}. Las curvas siempre se incluyen; la visibilidad de los ejes respeta la vista actual.</p>
  <div class="seleccion-exportacion">
    <label><input type="checkbox" bind:checked={opcionesExportacion.cuadricula} disabled={!mostrarCuadricula} /> Cuadrícula adaptada al zoom</label>
    <label><input type="checkbox" bind:checked={opcionesExportacion.valores} disabled={!mostrarEjes} /> Números de los ejes</label>
    {#if mostrarMuestras}<label><input type="checkbox" bind:checked={opcionesExportacion.guias} /> Puntos y guías de tabulación</label>{/if}
    {#if notasVisibles.length}<label><input type="checkbox" bind:checked={opcionesExportacion.notas} /> Explicaciones de tangente y secante</label>{/if}
  </div>
  <div class="opciones-exportacion">
    <button type="button" onclick={decidirExportacion}>Exportar {formatoPendiente.toUpperCase()}</button>
    <button type="button" onclick={() => { confirmacionExportacion = false; formatoPendiente = ''; }}>Cancelar</button>
  </div>
</Dialogo>

<style>
  .detalle-dominio { position: absolute; z-index: 5; inset-inline-start: .75rem; inset-block-start: 3rem; max-inline-size: min(28rem, calc(100% - 1.5rem)); max-block-size: 45%; overflow: auto; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-sm); background: var(--surface-paper); padding: .5rem .75rem; font-size: .8rem; }
  .detalle-dominio summary { cursor: pointer; font-weight: 700; min-block-size: 2.75rem; align-content: center; }
  .detalle-dominio p { margin-block: .6rem; }
  .grafica { margin: 0.4rem 0; inline-size: 100%; }
  .grafica.compacto { margin: 0.2rem 0; }
  .grafica.chip { margin: 0; inline-size: auto; }
  .grafica.inmersiva:not(.pantalla-completa) { position: relative; display: flex; flex-direction: column; block-size: 100%; margin: 0; overflow: hidden; }
  .grafica.inmersiva:not(.pantalla-completa) .barra-grafica { position: absolute; z-index: 5; inset-block-start: .5rem; inset-inline: .5rem; box-shadow: var(--shadow-float); }
  .grafica.inmersiva:not(.pantalla-completa) .escenario-grafica { flex: 1; min-block-size: 0; }
  .grafica.inmersiva:not(.pantalla-completa) .lienzo { block-size: 100%; border-radius: 0; }
  @media (min-width: 48.0625rem) {
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) { overflow: visible; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .barra-grafica { inset-block-start: .35rem; inset-inline: .35rem; max-inline-size: max-content; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .barra-grafica .grupo-herramientas:not(:first-child),
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .barra-grafica .ampliar { display: none; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabulacion {
      inset-inline-start: -21rem; inset-inline-end: auto; inset-block-start: 0; inset-block-end: 0;
      inline-size: 21rem; max-inline-size: 21rem; max-block-size: none;
      border-block: 0; border-inline-start: 0; border-radius: 0; box-shadow: none;
    }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabulacion:not([open]) { display: none; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabulacion[open] { display: block; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabulacion summary,
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabla-matriz { display: none; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .titulo-tabla-movil,
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabla-vertical-movil { display: block; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .nuevo-punto-tabla { display: grid; gap: .3rem; margin-block: .65rem; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .nuevo-punto-tabla button { min-block-size: 38px; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-primary); cursor: pointer; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .mensaje-punto { display: block; color: var(--ink-secondary); font-size: var(--texto-xs); }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabla-vertical-movil table { inline-size: 100%; border: 1px solid var(--trazo-suave); }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabla-vertical-movil caption { position: absolute; inline-size: 1px; block-size: 1px; overflow: hidden; clip-path: inset(50%); }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabla-vertical-movil th,
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabla-vertical-movil td { padding: .35rem; border: 1px solid var(--trazo-suave); text-align: start; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabla-vertical-movil tbody tr:nth-child(even) { background: var(--surface-canvas); }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabla-vertical-movil tbody tr.adicional { background: var(--accent-surface); }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabla-vertical-movil .abscisa-manual { inline-size: 5.5rem; min-block-size: 34px; }
    .grafica.inmersiva.laboratorio:not(.pantalla-completa) .tabla-vertical-movil .quitar-punto { border: 0; background: transparent; color: var(--semantic-error); font: inherit; cursor: pointer; }
  }
  .cajon-grafica-escritorio { position: absolute; z-index: 7; inset-block: 0; inset-inline-start: -21rem; display: grid; align-content: start; gap: .8rem; inline-size: 21rem; overflow-y: auto; padding: 1rem; border-inline-end: 1px solid var(--trazo-suave); background: var(--surface-panel); }
  .cajon-grafica-escritorio h2 { margin: 0; font-size: var(--texto-lg); }
  .cajon-grafica-escritorio p { margin: 0; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .opciones-cajon { display: grid; gap: .55rem; }
  .opciones-cajon > button, .opciones-cajon > label { display: flex; align-items: center; gap: .5rem; min-block-size: 42px; padding: .4rem .55rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); font: inherit; font-size: var(--texto-sm); }
  .opciones-cajon > button { cursor: pointer; }
  .opciones-cajon > button[aria-pressed='true'] { border-color: var(--accent-main); background: var(--accent-surface); color: var(--accent-main); }
  .cajon-grafica-escritorio > label { display: grid; gap: .3rem; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .cajon-grafica-escritorio input[type='number'], .cajon-grafica-escritorio select { max-inline-size: 100%; min-block-size: 38px; padding: .3rem; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-primary); }
  .opciones-cajon fieldset { display: grid; gap: .35rem; min-inline-size: 0; margin: 0; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); }
  .opciones-cajon fieldset label { display: flex; align-items: center; gap: .35rem; }
  .controles-lienzo-escritorio { position: absolute; z-index: 6; inset-inline-end: .75rem; inset-block-end: 3rem; display: grid; gap: .2rem; padding: .2rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); box-shadow: var(--shadow-float); }
  .controles-lienzo-escritorio button { inline-size: 2.35rem; block-size: 2.35rem; border: 0; border-radius: var(--radius-xs); background: transparent; color: var(--ink-secondary); font: inherit; font-size: 1.2rem; cursor: pointer; }
  .controles-lienzo-escritorio button:hover, .controles-lienzo-escritorio button:focus-visible { background: var(--accent-surface); color: var(--accent-main); }
  .grafica.inmersiva:not(.pantalla-completa) figcaption { position: absolute; z-index: 3; inset-inline-start: .75rem; inset-block-end: .5rem; max-inline-size: min(30rem, calc(100% - 1.5rem)); padding: .3rem .5rem; background: var(--surface-paper); border-radius: var(--radius-xs); }
  .grafica.pantalla-completa { position: fixed; z-index: 80; inset: 12px; inline-size: auto; margin: 0; padding: 12px; overflow: auto; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-lg); background: var(--surface-panel); box-shadow: var(--shadow-float); }
  .escenario-grafica { position: relative; min-inline-size: 0; }
  .notas-analisis {
    position: absolute;
    z-index: 4;
    inset-block-start: 16px;
    inset-inline-start: 16px;
    display: grid;
    gap: 10px;
    inline-size: min(25rem, calc(100% - 32px));
    max-block-size: calc(100% - 32px);
    overflow-y: auto;
  }
  .nota-analisis {
    min-inline-size: 0;
    padding: .7rem .85rem;
    border: 1px solid var(--trazo-fuerte);
    border-inline-start: 4px solid var(--accent-main);
    border-radius: var(--radius-sm);
    background: var(--surface-paper);
    color: var(--ink-primary);
    box-shadow: var(--shadow-float);
    font-family: var(--fuente-cuerpo);
  }
  .cabecera-nota { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
  .cabecera-nota strong { color: var(--accent-main); font-size: var(--texto-sm); }
  .cabecera-nota button {
    display: grid; place-items: center; inline-size: 1.9rem; block-size: 1.9rem;
    border: 1px solid var(--trazo-suave); border-radius: 50%;
    background: var(--surface-panel); color: var(--ink-primary);
    font: inherit; font-size: 1.25rem; cursor: pointer;
  }
  .cabecera-nota button:hover, .cabecera-nota button:focus-visible { border-color: var(--accent-main); background: var(--accent-surface); }
  .nota-analisis p { margin: .45rem 0 0; color: var(--ink-secondary); font-size: var(--texto-xs); line-height: 1.45; }
  .formula-nota { margin-block-start: .4rem; overflow-x: auto; font-size: var(--texto-sm); }
  .desplegar-proceso { display: flex; justify-content: space-between; align-items: center; inline-size: 100%; min-block-size: 2rem; margin-block-start: .5rem; padding: .3rem .45rem; border: 1px solid var(--accent-main); border-radius: var(--radius-xs); background: var(--accent-surface); color: var(--accent-main); font: inherit; font-size: var(--texto-xs); font-weight: 750; cursor: pointer; }
  .pasos-analisis { margin: .45rem 0 0; padding-inline-start: 1.25rem; color: var(--ink-secondary); font-size: var(--texto-xs); line-height: 1.45; }
  .pasos-analisis li + li { margin-block-start: .3rem; }
  .seleccion-exportacion { display: grid; gap: .55rem; margin-block: 1rem; }
  .seleccion-exportacion label { display: flex; align-items: center; gap: .6rem; min-block-size: 2.25rem; color: var(--ink-primary); }
  .seleccion-exportacion input { inline-size: 1.1rem; block-size: 1.1rem; accent-color: var(--accent-main); }
  .opciones-exportacion { display: flex; flex-wrap: wrap; gap: .5rem; margin-block-start: 1rem; }
  .opciones-exportacion button { min-block-size: 44px; padding: .5rem .75rem; border: 1px solid var(--accent-main); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--accent-main); font: inherit; cursor: pointer; }
  .opciones-exportacion button:first-child { background: var(--accent-main); color: var(--accent-on-main); }

  .barra-grafica { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: stretch; gap: 6px; margin-block-end: 7px; padding: 6px; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-canvas); box-shadow: var(--shadow-soft); }
  .cargar-funciones { display: grid; gap: .3rem; min-inline-size: 0; }
  .cargar-funciones input { max-inline-size: 100%; }
  .herramientas-desplazables { min-inline-size: 0; display: flex; align-items: stretch; gap: 6px; overflow-x: auto; scrollbar-width: thin; }
  .grupo-herramientas { display: inline-flex; align-items: center; gap: 4px; padding-inline-end: 6px; border-inline-end: 1px solid var(--trazo-suave); }
  .rotulo-grupo { padding-inline: 3px; color: var(--ink-tertiary) !important; font-size: 9px !important; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
  .barra-grafica button, .barra-grafica label { min-block-size: 27px; display: inline-flex; align-items: center; gap: 4px; padding: 3px 7px; border: 1px solid var(--trazo-suave); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-secondary); font: inherit; font-size: 10.5px; cursor: pointer; }
  .barra-grafica label.grupo-herramientas { border-block: 0; border-inline-start: 0; border-radius: 0; background: transparent; }
  .barra-grafica button.activo { border-color: var(--accent-main); color: var(--accent-main); background: var(--accent-surface); }
  .muestra { inline-size: 10px; block-size: 10px; border-radius: 2px; background: var(--color-violet-light); }
  .muestra.derivada { background: var(--color-amber-chart); }
  .serie-0 { color: var(--color-violet); }
  .serie-1 { color: var(--color-sky); }
  .serie-2 { color: var(--color-emerald); }
  .serie-3 { color: var(--color-rose); }
  .serie-4 { color: var(--color-orange); }
  .muestra.serie-0 { background: var(--color-violet-light); }
  .muestra.serie-1 { background: var(--color-sky-light); }
  .muestra.serie-2 { background: var(--color-emerald-light); }
  .muestra.serie-3 { background: var(--color-rose-light); }
  .tabulacion { position: absolute; z-index: 6; inset-inline-end: .5rem; inset-block-end: .5rem; inline-size: min(31rem, calc(100% - 1rem)); max-block-size: calc(100% - 1rem); overflow: auto; margin: 0; padding: .65rem; border: 1px solid var(--trazo-fuerte); border-inline-start: 4px solid var(--accent-main); border-radius: var(--radius-sm); background: var(--surface-panel); box-shadow: var(--shadow-float); }
  .navegacion-movil, .panel-movil-grafica, .tabla-vertical-movil, .abrir-opciones-tabla,
  .asa-tabla-movil, .titulo-tabla-movil, .nuevo-punto-tabla, .mensaje-punto { display: none; }
  .tabulacion:not([open]) { inline-size: max-content; max-inline-size: calc(100% - 1rem); }
  .tabulacion summary { cursor: pointer; color: var(--ink-primary); font-weight: 750; font-size: var(--texto-sm); }
  .titulo-tabla-con-ayuda { display: flex; align-items: center; gap: .4rem; margin-block: .35rem; }
  .formula-tabla { margin-block-start: .5rem; overflow-x: auto; color: var(--ink-primary); }
  .controles-tabla { display: flex; flex-wrap: wrap; align-items: center; gap: .6rem; margin-block: .75rem; }
  .controles-tabla label { display: inline-flex; align-items: center; gap: .35rem; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .controles-tabla input[type='number'] { inline-size: 6rem; }
  .controles-tabla input, .controles-tabla select, .controles-tabla button { min-block-size: 38px; padding: .3rem .5rem; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-primary); font: inherit; }
  .controles-tabla .casilla input { min-block-size: auto; }
  .controles-tabla button { cursor: pointer; }
  .valor-teclado { min-inline-size: 5.5rem; min-block-size: 38px; padding: .3rem .45rem; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-primary); font: inherit; font-variant-numeric: tabular-nums; text-align: center; cursor: pointer; }
  .valor-teclado:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 2px; }
  .tabla-desplazable { overflow-x: auto; }
  .tabulacion table { inline-size: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: var(--texto-sm); }
  .tabulacion caption { padding-block: .4rem; color: var(--ink-secondary); text-align: start; }
  .tabulacion th, .tabulacion td { padding: .3rem .5rem; border-block-end: 1px solid var(--trazo-suave); text-align: end; }
  .tabulacion th:first-child { text-align: start; }
  .tabla-matriz table { inline-size: max-content; min-inline-size: 100%; }
  .tabla-matriz th, .tabla-matriz td { min-inline-size: 3.2rem; text-align: center; }
  .tabla-matriz th:first-child { position: sticky; inset-inline-start: 0; z-index: 1; min-inline-size: 3.8rem; background: var(--surface-panel); }
  .tabla-matriz .abscisa-manual { inline-size: 5.5rem; min-block-size: 2rem; padding: .2rem .3rem; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-primary); font: inherit; font-variant-numeric: tabular-nums; text-align: center; }
  .tabla-matriz .abscisa-manual:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 1px; }
  .nota-tabla { margin: .5rem 0 0; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .barra-grafica .ampliar { align-self: stretch; border-color: var(--accent-main); color: var(--accent-main); }
  .barra-grafica input { inline-size: 52px; border: 0; border-inline-start: 1px solid var(--trazo-suave); background: transparent; color: var(--ink-primary); }
  .barra-grafica select { max-inline-size: 82px; border: 0; background: transparent; color: inherit; font: inherit; cursor: pointer; }
  .barra-grafica span { font-size: var(--texto-xs); color: var(--semantic-success); }
  .barra-grafica .estado-exportacion { flex: 0 0 auto; align-self: center; }

  .cerrar-ampliada {
    position: absolute;
    inset-block-start: 8px;
    inset-inline-end: 8px;
    z-index: 5;
    display: grid;
    place-items: center;
    inline-size: 42px;
    block-size: 42px;
    padding: 0;
    border: 1px solid var(--accent-main);
    border-radius: 50%;
    background: var(--surface-paper);
    color: var(--accent-main);
    box-shadow: var(--shadow-float);
    font-size: 24px;
    line-height: 1;
  }
  .cerrar-ampliada:hover { background: var(--accent-surface); transform: scale(1.04); }
  .pantalla-completa .barra-grafica { margin-inline-end: 48px; }

  .grafica.compacto:not(.pantalla-completa) .barra-grafica {
    grid-template-columns: minmax(0, 1fr);
  }
  .grafica.compacto:not(.pantalla-completa) .herramientas-desplazables {
    display: grid;
    gap: 4px;
    overflow: visible;
  }
  .grafica.compacto:not(.pantalla-completa) .grupo-herramientas {
    display: flex;
    flex-wrap: wrap;
    inline-size: 100%;
    padding: 0 0 4px;
    border-inline-end: 0;
    border-block-end: 1px solid var(--trazo-suave);
  }
  .grafica.compacto:not(.pantalla-completa) .grupo-herramientas:last-child {
    padding-block-end: 0;
    border-block-end: 0;
  }
  .grafica.compacto:not(.pantalla-completa) .barra-grafica .ampliar {
    justify-content: center;
    inline-size: 100%;
  }

  .lienzo {
    position: relative;
    inline-size: 100%;
    block-size: min(75vw, 16rem);
    background: var(--surface-paper);
    border: 1px solid var(--trazo-fuerte);
    border-radius: var(--radius-sm);
    overflow: hidden;
    box-shadow: inset 0 0 0 1px var(--surface-paper), var(--shadow-soft);
  }

  .lienzo.compacto {
    block-size: 190px;
  }

  .laboratorio:not(.pantalla-completa) .lienzo { block-size: clamp(22rem, 52vw, 34rem); }

  .pantalla-completa .lienzo { block-size: calc(100vh - 150px); min-block-size: 360px; }

  .lienzo.chip {
    inline-size: 40px;
    block-size: 40px;
    flex-shrink: 0;
  }

  .tablero {
    position: relative;
    z-index: 1;
    background: transparent !important;
    display: flex;
    align-items: center;
    justify-content: center;
    inline-size: 100%;
    block-size: 100%;
  }
  .reticula, .escalas { position: absolute; inset: 0; inline-size: 100%; block-size: 100%; pointer-events: none; }
  .reticula { z-index: 0; color: var(--ink-tertiary); }
  .reticula .lineas-menores { stroke: currentColor; stroke-opacity: .13; stroke-width: .55; }
  .reticula .lineas-mayores { stroke: currentColor; stroke-opacity: .38; stroke-width: .9; }
  :global(body.dark-theme) .reticula .lineas-menores { stroke-opacity: .27; }
  :global(body.dark-theme) .reticula .lineas-mayores { stroke-opacity: .58; }
  .escalas { z-index: 2; overflow: visible; fill: var(--ink-primary); font: 12px var(--fuente-cuerpo); font-variant-numeric: tabular-nums; }
  .escalas text { paint-order: stroke; stroke: var(--surface-paper); stroke-width: 3px; stroke-linejoin: round; }

  .pendiente {
    font-size: var(--texto-sm);
    color: var(--ink-tertiary);
  }

  figcaption {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.35rem;
    margin-block-start: 0.4rem;
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
  }

  @media (max-width: 48rem) {
    .cajon-grafica-escritorio, .controles-lienzo-escritorio { display: none; }
    .grafica.pantalla-completa .escenario-grafica { block-size: 100%; }
    .grafica:is(.inmersiva, .pantalla-completa).panel-movil-abierto .lienzo {
      block-size: max(6rem, calc(100% - min(var(--altura-panel-movil), calc(100% - 7rem))));
      min-block-size: 0;
    }
    .grafica:is(.inmersiva, .pantalla-completa) .barra-grafica { display: none; }
    .grafica:is(.inmersiva, .pantalla-completa) .navegacion-movil {
      position: absolute; z-index: 10; inset-inline: 0; inset-block-end: 0;
      display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
      padding: .25rem max(.25rem, env(safe-area-inset-right)) max(.25rem, env(safe-area-inset-bottom));
      border-block-start: 1px solid var(--trazo-suave); background: var(--surface-paper); box-shadow: var(--shadow-up);
    }
    .navegacion-movil button { display: grid; place-items: center; gap: 0; min-inline-size: 0; min-block-size: 52px; padding: .15rem .05rem; border: 0; border-radius: var(--radius-sm); background: transparent; color: var(--ink-secondary); font: 650 10px var(--fuente-cuerpo); cursor: pointer; }
    .navegacion-movil button span { font-size: 20px; line-height: 1.2; }
    .navegacion-movil button.activa { color: var(--accent-main); background: var(--accent-surface); }
    .navegacion-movil button:focus-visible, .panel-movil-grafica button:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 2px; }
    .grafica:is(.inmersiva, .pantalla-completa) .panel-movil-grafica {
      position: absolute; z-index: 9; inset-inline: 0; inset-block-end: calc(3.85rem + env(safe-area-inset-bottom));
      display: grid; align-content: start; gap: .55rem;
      block-size: min(var(--altura-panel-movil), calc(100% - 7rem)); max-block-size: none;
      overflow-y: auto; overscroll-behavior: contain;
      padding: .75rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-lg) var(--radius-lg) 0 0;
      background: var(--surface-paper); box-shadow: var(--shadow-up);
    }
    .panel-movil-grafica h3 { margin: 0; font-size: var(--texto-md); }
    .panel-movil-grafica button { display: inline-flex; align-items: center; gap: .35rem; min-block-size: 44px; padding: .4rem; border: 1px solid var(--trazo); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); font: inherit; cursor: pointer; }
    .panel-movil-grafica button[aria-pressed='true'] { border-color: var(--accent-main); background: var(--accent-surface); color: var(--accent-main); }
    .panel-movil-grafica .muestra { flex: none; }
    .cuadricula-herramientas { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .35rem; }
    .cuadricula-herramientas button { display: grid; justify-items: center; gap: .1rem; min-inline-size: 0; font-size: var(--texto-xs); }
    .cuadricula-herramientas button span { font-size: 1.15rem; }
    .parametros-herramientas { display: flex; gap: .7rem; }
    .parametros-herramientas label { display: flex; align-items: center; gap: .35rem; }
    .parametros-herramientas input { inline-size: 5.5rem; min-block-size: 38px; }
    .ajustes-moviles { display: grid; gap: .35rem; }
    .ajustes-moviles label { display: flex; align-items: center; gap: .5rem; min-block-size: 42px; }
    .ajustes-moviles select { min-block-size: 40px; }
    .preferencias-analisis { display: grid; gap: .1rem; min-inline-size: 0; margin: .25rem 0; padding: .5rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); }
    .preferencias-analisis legend { padding-inline: .25rem; font-weight: 750; }
    .grafica:is(.inmersiva, .pantalla-completa) .tabulacion[open] {
      position: absolute; z-index: 8; inset-inline: 0; inset-block-end: calc(3.85rem + env(safe-area-inset-bottom));
      inline-size: 100%; max-inline-size: none;
      block-size: min(var(--altura-panel-movil), calc(100% - 7rem)); max-block-size: none;
      padding: .6rem; border-inline-start: 0; border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    }
    .grafica:is(.inmersiva, .pantalla-completa) .tabulacion:not([open]) { display: none; }
    .grafica:is(.inmersiva, .pantalla-completa) .tabulacion summary,
    .grafica:is(.inmersiva, .pantalla-completa) .formula-tabla,
    .grafica:is(.inmersiva, .pantalla-completa) .tabla-matriz,
    .grafica:is(.inmersiva, .pantalla-completa) .nota-edicion { display: none; }
    .grafica:is(.inmersiva, .pantalla-completa) .asa-tabla-movil,
    .grafica:is(.inmersiva, .pantalla-completa) .titulo-tabla-movil { display: block; }
    .grafica:is(.inmersiva, .pantalla-completa) .asa-tabla-movil { position: sticky; inset-block-start: 0; z-index: 3; background: var(--surface-panel); }
    .titulo-tabla-movil { margin: 0 0 .5rem; font-size: var(--texto-md); }
    .grafica:is(.inmersiva, .pantalla-completa) .tabla-vertical-movil { display: block; overflow-x: auto; }
    .grafica:is(.inmersiva, .pantalla-completa) .tabla-vertical-movil caption { position: absolute; inline-size: 1px; block-size: 1px; overflow: hidden; clip-path: inset(50%); }
    .grafica:is(.inmersiva, .pantalla-completa) .tabla-vertical-movil table { min-inline-size: 100%; border: 1px solid var(--trazo); }
    .tabla-vertical-movil th, .tabla-vertical-movil td { border: 1px solid var(--trazo-suave); text-align: start; white-space: nowrap; }
    .tabla-vertical-movil thead th { background: var(--accent-surface); color: var(--ink-primary); font-weight: 750; }
    .tabla-vertical-movil tbody tr:nth-child(even) { background: var(--surface-canvas); }
    .tabla-vertical-movil tbody tr.adicional { background: var(--accent-surface); }
    .tabla-vertical-movil .abscisa-manual { inline-size: 5.5rem; min-block-size: 36px; }
    .tabla-vertical-movil tbody th { white-space: nowrap; }
    .tabla-vertical-movil .quitar-punto { min-inline-size: 32px; min-block-size: 36px; margin-inline-start: .2rem; padding: 0; border: 0; background: transparent; color: var(--semantic-error); font: inherit; cursor: pointer; }
    .grafica:is(.inmersiva, .pantalla-completa) .nuevo-punto-tabla { display: flex; align-items: end; flex-wrap: wrap; gap: .35rem; margin: .5rem 0; }
    .nuevo-punto-tabla button { min-block-size: 38px; padding: .25rem .55rem; border: 1px solid var(--trazo); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-primary); font: inherit; cursor: pointer; }
    .grafica:is(.inmersiva, .pantalla-completa) .mensaje-punto { display: block; margin: .2rem 0; color: var(--ink-secondary); font-size: var(--texto-xs); }
    .grafica:is(.inmersiva, .pantalla-completa) .abrir-opciones-tabla { display: inline-flex; align-items: center; min-block-size: 38px; margin-block-end: .35rem; padding: .25rem .55rem; border: 1px solid var(--trazo); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-secondary); font: inherit; cursor: pointer; }
    .grafica:is(.inmersiva, .pantalla-completa) .controles-tabla { display: none; }
    .grafica:is(.inmersiva, .pantalla-completa) .controles-tabla.visible-movil { display: flex; }
    .grafica:is(.inmersiva, .pantalla-completa) .nota-tabla { margin: .35rem 0; font-size: var(--texto-xs); }
    .grafica:is(.inmersiva, .pantalla-completa) .escenario-grafica { padding-block-end: 3.85rem; }
    .grafica.inmersiva:not(.pantalla-completa) .detalle-tabla { display: none; }
    .grafica.inmersiva:not(.pantalla-completa) .escenario-grafica {
      box-sizing: border-box;
      padding-block-end: 3.5rem;
    }
    .grafica.inmersiva:not(.pantalla-completa) figcaption {
      inline-size: 1px;
      block-size: 1px;
      overflow: hidden;
      clip-path: inset(50%);
      white-space: nowrap;
    }
    .grupo-herramientas { flex: 0 0 auto; }
    .barra-grafica .ampliar { flex: 0 0 auto; }
    .lienzo.compacto { block-size: 175px; }
    .grafica.pantalla-completa { inset: 4px; padding: 7px; }
    .pantalla-completa .barra-grafica { margin-inline-end: 46px; }
    .pantalla-completa .lienzo { block-size: calc(100dvh - 175px); min-block-size: 280px; }
    .notas-analisis { inset-block-start: 8px; inset-inline-start: 8px; inline-size: min(22rem, calc(100% - 16px)); max-block-size: calc(100% - 16px); }
  }

  @media (prefers-reduced-motion: reduce) {
    .cerrar-ampliada:hover { transform: none; }
  }
</style>
