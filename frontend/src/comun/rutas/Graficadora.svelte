<script>
  import { menuDesplegable } from '../base/menuDesplegable.js';
  import { ayudaContextual } from '../base/ayudaContextual.js';
  import { onMount } from 'svelte';
  import { confirmarAccion } from '../estado/confirmaciones.svelte.js';
  import { toast } from '../estado/toasts.svelte.js';
  import Grafica from '../turno/Grafica.svelte';
  import AsaPanelGrafica from '../turno/AsaPanelGrafica.svelte';
  import IslaDeFormula from '../../estudiante/piezas/IslaDeFormula.svelte';
  import TecladoDeNotacion from '../../estudiante/piezas/TecladoDeNotacion.svelte';
  import Icono from '../base/Icono.svelte';
  import BotonAyudaTooltip from '../base/BotonAyudaTooltip.svelte';
  import { prepararCurvas } from '../../nucleo/api/graficadora.js';

  let { definicionInicial = null, integrada = false, clase = undefined,
    conversacion = undefined, turno = undefined, concepto = undefined,
    alternativo = 'Gráfica interactiva de las funciones elegidas' } = $props();

  function curvasDeLaConversacion(definicion) {
    if (!definicion) return [];
    try {
      const datos = JSON.parse(definicion);
      if (Array.isArray(datos.curvas) && datos.curvas.length) return datos.curvas;
      if (datos.funcion_js) return [{
        ...datos,
        tipo: 'funcion', variable: datos.variable || 'x',
        expresion: datos.expresion || '', funcion_js: datos.funcion_js,
        limite_destino: datos.limite_destino, limite_x: datos.limite_x
      }];
    } catch { /* Una definición dañada se muestra como error en Grafica. */ }
    return [];
  }

  const curvasOriginales = $derived(curvasDeLaConversacion(definicionInicial));
  const nombreOriginal = $derived(curvasOriginales.length === 1 && /^[a-zA-Z]$/.test(curvasOriginales[0].nombre_funcion ?? '')
    ? `${curvasOriginales[0].nombre_funcion}(${curvasOriginales[0].variable || 'x'}) del tutor` : 'ƒ del tutor');
  const maximoAdicionales = $derived(Math.max(0, 4 - curvasOriginales.length));

  let siguienteId = 2;
  let entradas = $state([]);
  let definicion = $state('');
  let ocupada = $state(false);
  let error = $state('');
  let panelAbierto = $state(false);
  let tabulacionAbierta = $state(false);
  let seccionEscritorio = $state('funciones');
  let alturaPanelMovil = $state(280);
  let esMovil = $state(false);
  let entradaActiva = $state(null);
  let curvasOcultas = $state([]);
  const curvaActiva = $derived(entradas.find((curva) => curva.id === entradaActiva) ?? entradas[0]);
  let solicitudActual = 0;
  let firmaDibujada = '';
  const firmaEntradas = $derived(JSON.stringify(entradas.map(({ tipo, variable, expresion, destino }) => ({ tipo, variable, expresion, destino }))));
  let listaMontada = $state(false);
  let estadosDeCurva = $state({});
  const estadosAnteriores = new Map();
  const curvasEditadas = new Set();
  const firmaCurva = (curva) => JSON.stringify([curva.tipo, curva.variable, curva.expresion, curva.destino]);
  const estadoCampo = $derived(curvaActiva && estadosDeCurva[curvaActiva.id]?.firma === firmaCurva(curvaActiva)
    ? estadosDeCurva[curvaActiva.id].estado : 'neutro');
  let relojDibujo;

  // Sólo permite enviar el operador completo al servidor. El CAS verifica
  // su destino; el cliente no infiere el valor matemático.
  const destinoIncluido = entrada => /^\$*\s*(?:\\lim(?![a-zA-Z])|lim\s*(?:[a-zA-Zθ]\s*)?(?:-+>|→))/.test(entrada.expresion.trim());
  const destinoFaltante = entrada => entrada.tipo === 'limite' && !entrada.destino.trim() && !destinoIncluido(entrada);

  function marcarEstado(id, firma, estado) {
    estadosAnteriores.set(id, { firma, estado });
    estadosDeCurva = { ...estadosDeCurva, [id]: { firma, estado } };
  }

  const ejemplos = [
    { nombre: 'Hueco en x = 1', curvas: [{ tipo: 'limite', variable: 'x', expresion: '(x^3-1)/(x-1)', destino: '1' }] },
    { nombre: 'Seno entre x', curvas: [{ tipo: 'limite', variable: 'x', expresion: 'sin(x)/x', destino: '0' }] },
    { nombre: 'Salto por tramos', curvas: [{ tipo: 'limite', variable: 'x', expresion: 'Piecewise((-2,x<0),(2,True))', destino: '0' }] },
    { nombre: 'Función y derivada', curvas: [
      { tipo: 'funcion', variable: 'x', expresion: 'x^2-4', destino: '' },
      { tipo: 'derivada', variable: 'x', expresion: 'x^2-4', destino: '' }
    ] }
  ];

  function aplicarEjemplo(ejemplo) {
    if (integrada) return;
    entradas = ejemplo.curvas.map((curva) => ({ id: siguienteId++, ...curva }));
    curvasOcultas = [];
    entradaActiva = entradas[0].id;
    void dibujar();
  }

  function agregar() {
    if (entradas.length >= (integrada ? maximoAdicionales : 4)) return;
    const nueva = { id: siguienteId++, tipo: 'funcion', variable: 'x', expresion: '', destino: '' };
    entradas = [...entradas, nueva];
    entradaActiva = nueva.id;
  }

  function quitar(id) {
    if (!integrada && entradas.length <= 1) return;
    const indice = entradas.findIndex((entrada) => entrada.id === id);
    entradas = entradas.filter((entrada) => entrada.id !== id);
    const indiceGrafica = indice + (integrada ? curvasOriginales.length : 0);
    curvasOcultas = curvasOcultas.filter((oculta) => oculta !== indiceGrafica).map((oculta) => oculta > indiceGrafica ? oculta - 1 : oculta);
    if (entradaActiva === id) entradaActiva = entradas[0]?.id ?? null;
    void dibujar();
  }

  function duplicar(id) {
    if (entradas.length >= (integrada ? maximoAdicionales : 4)) return;
    const original = entradas.find((entrada) => entrada.id === id);
    if (!original) return;
    const copia = { ...original, id: siguienteId++ };
    entradas = [...entradas, copia];
    entradaActiva = copia.id;
    void dibujar();
  }

  function alternarVisibilidad(id) {
    const indice = entradas.findIndex((entrada) => entrada.id === id) + (integrada ? curvasOriginales.length : 0);
    if (indice < 0) return;
    curvasOcultas = curvasOcultas.includes(indice)
      ? curvasOcultas.filter((oculta) => oculta !== indice)
      : [...curvasOcultas, indice];
  }

  function insertarSimbolo(fragmento) {
    const entrada = entradas.find((curva) => curva.id === entradaActiva) ?? entradas[0];
    if (!entrada) return;
    const campo = document.getElementById(`expresion-curva-${entrada.id}`);
    campo?.focus();
    campo?.executeCommand?.(['insert', fragmento.slice(1, -1)]);
  }

  function ejecutarComando(comando) {
    const campo = document.getElementById(`expresion-curva-${entradaActiva}`);
    campo?.focus();
    campo?.executeCommand?.(comando);
  }

  async function dibujar() {
    // Una respuesta anterior no debe reemplazar un dibujo más reciente.
    // Al elegir un ejemplo durante la preparación inicial había una carrera:
    // el segundo intento se ignoraba por `ocupada`.
    const solicitud = ++solicitudActual;
    const firma = firmaEntradas;
    const idEditada = entradaActiva;
    clearTimeout(relojDibujo);
    const incompleta = entradas.findIndex((entrada) => !entrada.expresion.trim() || destinoFaltante(entrada));
    if (incompleta !== -1) {
      error = `La función ${incompleta + 1} necesita una expresión completa.`;
      if (idEditada !== null && curvaActiva) marcarEstado(idEditada, firmaCurva(curvaActiva), 'invalida');
      ocupada = false;
      return;
    }
    ocupada = true;
    error = '';
    try {
      if (integrada && !entradas.length) {
        definicion = definicionInicial;
        firmaDibujada = firma;
        return;
      }
      const respuesta = await prepararCurvas(entradas.map(({ tipo, variable, expresion, destino }) => ({
        tipo, variable, expresion, destino
      })));
      if (solicitud !== solicitudActual || firma !== firmaEntradas) return;
      const curvas = integrada ? [...curvasOriginales, ...respuesta.curvas] : respuesta.curvas;
      const foco = curvas.find((curva) => curva.tipo === 'limite');
      definicion = JSON.stringify({
        ...(integrada ? JSON.parse(definicionInicial) : {}),
        curvas,
        funcion_js: curvas[0].funcion_js,
        expresion: curvas.length === 1 ? curvas[0].expresion : '',
        limite_destino: foco?.limite_destino ?? null,
        limite_x: foco?.limite_x ?? null
      });
      firmaDibujada = firma;
      for (const entrada of entradas) marcarEstado(entrada.id, firmaCurva(entrada), 'valida');
    } catch (fallo) {
      if (solicitud !== solicitudActual || firma !== firmaEntradas) return;
      error = fallo?.detalle || 'No se pudo preparar la gráfica. Revisa la expresión y vuelve a intentarlo.';
      if (fallo?.clase === 'peticion-invalida' && idEditada !== null) {
        const actual = entradas.find((entrada) => entrada.id === idEditada);
        if (actual) marcarEstado(idEditada, firmaCurva(actual), 'invalida');
      }
    } finally {
      if (solicitud === solicitudActual) ocupada = false;
    }
  }

  $effect(() => {
    if (!listaMontada) return;
    firmaEntradas;
    clearTimeout(relojDibujo);
    let huboCambio = false;
    for (const entrada of entradas) {
      const firma = firmaCurva(entrada);
      if (estadosAnteriores.get(entrada.id)?.firma !== firma) {
        huboCambio = true;
        marcarEstado(entrada.id, firma, entrada.expresion.trim() ? 'comprobando'
          : curvasEditadas.has(entrada.id) ? 'invalida' : 'neutro');
      }
    }
    if (huboCambio) error = '';
    if (firmaEntradas === firmaDibujada || entradas.some((entrada) => !entrada.expresion.trim()
      || destinoFaltante(entrada))) return;
    relojDibujo = setTimeout(() => { if (firmaEntradas !== firmaDibujada) void dibujar(); }, 420);
    return () => clearTimeout(relojDibujo);
  });

  function dibujarCambiosCompletos() {
    if (entradas.every((entrada) => entrada.expresion.trim()) && firmaEntradas !== firmaDibujada) {
      void dibujar();
    }
  }

  function alternarFunciones() {
    if (!esMovil) {
      abrirSeccionEscritorio('funciones');
      return;
    }
    if (!panelAbierto && esMovil) tabulacionAbierta = false;
    panelAbierto = !panelAbierto;
    if (!panelAbierto) dibujarCambiosCompletos();
  }

  function abrirSeccionEscritorio(seccion) {
    seccionEscritorio = seccionEscritorio === seccion ? '' : seccion;
    panelAbierto = seccionEscritorio === 'funciones';
    tabulacionAbierta = seccionEscritorio === 'tabla';
    if (!panelAbierto) dibujarCambiosCompletos();
  }

  function cerrarFunciones() {
    panelAbierto = false;
    dibujarCambiosCompletos();
  }

  async function guardarFunciones() {
    if (!integrada || !entradas.length || entradas.some((entrada) => !entrada.expresion.trim())) return;
    if (!await confirmarAccion({ tipo:'descarga', titulo:'¿Guardar funciones de la gráfica?',
      descripcion:`Se descargará un archivo JSON con ${entradas.length} ${entradas.length === 1 ? 'función adicional' : 'funciones adicionales'} para volver a cargarlas en esta gráfica.`, confirmar:'Descargar JSON' })) return;
    const curvas = entradas.map(({ tipo, variable, expresion, destino }) => ({ tipo, variable, expresion, destino }));
    const url = URL.createObjectURL(new Blob([JSON.stringify({ version: 1, curvas }, null, 2)], { type: 'application/json' }));
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = 'didaxia-funciones.json';
    enlace.click();
    toast.descarga('Descargando funciones de la gráfica en JSON.');
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  async function cargarFunciones(evento) {
    const archivo = evento.currentTarget.files?.[0];
    evento.currentTarget.value = '';
    if (!archivo) return;
    try {
      const guardado = JSON.parse(await archivo.text());
      if (guardado?.version !== 1 || !Array.isArray(guardado.curvas)
          || guardado.curvas.length > maximoAdicionales
          || guardado.curvas.some((curva) => !['funcion', 'limite', 'derivada'].includes(curva.tipo)
            || !/^[a-zA-Zθ]$/.test(curva.variable)
            || typeof curva.expresion !== 'string' || !curva.expresion.trim() || curva.expresion.length > 2000
            || typeof curva.destino !== 'string' || curva.destino.length > 24)) {
        throw new Error('Archivo de funciones no válido para esta gráfica.');
      }
      entradas = guardado.curvas.map((curva) => ({ ...curva, id: siguienteId++ }));
      entradaActiva = entradas[0]?.id ?? null;
      error = '';
      void dibujar();
    } catch (fallo) {
      error = fallo?.message || 'No se pudieron cargar las funciones.';
    }
  }

  $effect(() => {
    if (esMovil && tabulacionAbierta) panelAbierto = false;
  });

  onMount(() => {
    if (integrada) {
      definicion = definicionInicial;
      firmaDibujada = firmaEntradas;
    } else {
      entradas = [{ id: 1, tipo: 'funcion', variable: 'x', expresion: 'x^2', destino: '' }];
      entradaActiva = 1;
    }
    const consulta = window.matchMedia?.('(max-width: 48rem)');
    const adaptar = () => {
      esMovil = Boolean(consulta?.matches);
      panelAbierto = !esMovil;
      tabulacionAbierta = !esMovil && seccionEscritorio === 'tabla';
    };
    adaptar();
    consulta?.addEventListener('change', adaptar);
    listaMontada = true;
    return () => { clearTimeout(relojDibujo); consulta?.removeEventListener('change', adaptar); };
  });
</script>

<main class="laboratorio-graficas" class:integrada class:tabla-visible={esMovil && tabulacionAbierta}
      class:cajon-escritorio={!esMovil && seccionEscritorio !== ''}
      style={`--altura-panel-movil: ${alturaPanelMovil}px`}
      onpointerdown={(evento) => {
        if (esMovil && panelAbierto && !evento.target?.closest?.('.panel-funciones, .navegacion-movil')) cerrarFunciones();
      }}>
  {#if !panelAbierto}<h1 class="solo-lectores">Graficadora</h1>{/if}
  <nav class="muelle-escritorio" aria-label="Paneles de la graficadora">
    <button use:ayudaContextual type="button" class:seleccionado={seccionEscritorio === 'funciones'} aria-label="Funciones" title="Funciones" aria-pressed={seccionEscritorio === 'funciones'} onclick={() => abrirSeccionEscritorio('funciones')}>ƒ<span>Funciones</span></button>
    <button use:ayudaContextual type="button" class:seleccionado={seccionEscritorio === 'tabla'} aria-label="Tabla de valores" title="Tabla de valores" aria-pressed={seccionEscritorio === 'tabla'} onclick={() => abrirSeccionEscritorio('tabla')}>▦<span>Tabla</span></button>
    <button use:ayudaContextual type="button" class:seleccionado={seccionEscritorio === 'herramientas'} aria-label="Herramientas de análisis" title="Herramientas de análisis" aria-pressed={seccionEscritorio === 'herramientas'} onclick={() => abrirSeccionEscritorio('herramientas')}>⌖<span>Herramientas</span></button>
    <button use:ayudaContextual type="button" class:seleccionado={seccionEscritorio === 'ajustes'} aria-label="Ajustes de la gráfica" title="Ajustes de la gráfica" aria-pressed={seccionEscritorio === 'ajustes'} onclick={() => abrirSeccionEscritorio('ajustes')}>⚙<span>Ajustes</span></button>
  </nav>
  <button class="abrir-panel" type="button" aria-expanded={panelAbierto}
          aria-controls="panel-funciones" onclick={alternarFunciones}>
    {panelAbierto ? 'Ocultar funciones' : `Funciones (${entradas.length})`}
  </button>

  {#if panelAbierto}
  <aside class="panel-funciones" id="panel-funciones" aria-label="Funciones para dibujar">
    <div class="asa-funciones-movil"><AsaPanelGrafica bind:altura={alturaPanelMovil} /></div>
    <header><p class="ceja">Exploración matemática</p><div class="titulo-funciones"><h1>Funciones</h1>
      <BotonAyudaTooltip tamano="sm" posicion="abajo" texto="Escribe una función para verla en el plano. Puedes añadir hasta cuatro curvas y compararlas. La gráfica se actualiza al completar cada expresión." ariaLabel="Cómo usar el panel de funciones" />
    </div></header>
    {#if integrada}<p class="origen-conversacion">La curva del tutor permanece visible. Las que añadas son temporales.</p>{/if}
    {#if !integrada}<details class="ejemplos"><summary>Probar un ejemplo</summary><div aria-label="Ejemplos para explorar">
      {#each ejemplos as ejemplo}
        <button type="button" onclick={() => aplicarEjemplo(ejemplo)}>{ejemplo.nombre}</button>
      {/each}
    </div></details>{/if}

    <form onsubmit={(evento) => { evento.preventDefault(); void dibujar(); }}>
    <div class="pestanas-curvas" role="tablist" aria-label="Curvas en el plano">
      {#if integrada}<span class="curva-original">{nombreOriginal}</span>{/if}
      {#each entradas as entrada, indice (entrada.id)}
        <button type="button" role="tab" aria-selected={entradaActiva === entrada.id} class:seleccionada={entradaActiva === entrada.id} onclick={() => entradaActiva = entrada.id}>
          <i class={`muestra serie-${indice + (integrada ? curvasOriginales.length : 0)}`}></i> f{indice + 1 + (integrada ? curvasOriginales.length : 0)}({entrada.variable || 'x'})
        </button>
      {/each}
      <button type="button" class="agregar-curva" onclick={agregar} disabled={entradas.length >= (integrada ? maximoAdicionales : 4)} aria-label="Añadir función">＋</button>
    </div>
    {#if curvaActiva}
      <div class="acciones-curva" role="group" aria-label={`Acciones de la curva ${entradas.indexOf(curvaActiva) + 1}`}>
        <button use:ayudaContextual type="button" aria-label={curvasOcultas.includes(entradas.indexOf(curvaActiva) + (integrada ? curvasOriginales.length : 0)) ? 'Mostrar curva' : 'Ocultar curva'}
                title={curvasOcultas.includes(entradas.indexOf(curvaActiva) + (integrada ? curvasOriginales.length : 0)) ? 'Mostrar curva' : 'Ocultar curva'}
                aria-pressed={!curvasOcultas.includes(entradas.indexOf(curvaActiva) + (integrada ? curvasOriginales.length : 0))}
                onclick={() => alternarVisibilidad(curvaActiva.id)}><Icono nombre="visible" medida={19} /></button>
        <button use:ayudaContextual type="button" aria-label="Duplicar curva" title="Duplicar curva" disabled={entradas.length >= (integrada ? maximoAdicionales : 4)}
                onclick={() => duplicar(curvaActiva.id)}><Icono nombre="duplicar" medida={19} /></button>
        <button use:ayudaContextual type="button" aria-label="Quitar curva" title="Quitar curva" disabled={!integrada && entradas.length <= 1}
                onclick={() => quitar(curvaActiva.id)}><Icono nombre="eliminar" medida={19} /></button>
      </div>
    {:else if integrada}
      <p class="instruccion-agregar">Pulsa ＋ para comparar otra función con la gráfica del tutor.</p>
    {/if}
    {#if curvaActiva}
      <fieldset class="fila-curva" aria-label={`Editar curva ${entradas.indexOf(curvaActiva) + 1}`}>
        <legend class="solo-lectores">Curva {entradas.indexOf(curvaActiva) + 1}</legend>
        <label>Qué dibujar
          <select use:menuDesplegable={curvaActiva.tipo} bind:value={curvaActiva.tipo}>
            <option value="funcion">Función</option>
            <option value="limite">Límite de una función</option>
            <option value="derivada">Derivada de una función</option>
          </select>
        </label>
        <details class="opciones-avanzadas"><summary>Variable y sintaxis avanzada</summary>
          <label>Variable
            <input use:ayudaContextual type="text" bind:value={curvaActiva.variable} maxlength="1" pattern="[a-zA-Zθ]"
                   required title="Una letra para la variable de la función" autocomplete="off" spellcheck="false" />
          </label>
          <p>Elige una letra, por ejemplo <code>x</code>, <code>t</code> o <code>j</code>. Usa <code>^</code> para potencias y <code>Piecewise((-2,j&lt;0),(2,True))</code> para tramos. El plano usa esa variable en el eje horizontal.</p>
        </details>
        <div class="expresion" class:valida={estadoCampo === 'valida'} class:invalida={estadoCampo === 'invalida'}>
          <div class="etiqueta-con-ayuda"><label for={`expresion-curva-${curvaActiva.id}`}>Expresión</label>
            <BotonAyudaTooltip tamano="sm" posicion="abajo" texto="Escribe la función con la variable elegida. Puedes pegar fórmulas con fracciones, raíces, senos y logaritmos, o escribir sqrt(ln(x^2+1))*sen(x). En Función escribe solo la expresión, sin d/dx. Usa Piecewise((valor, condición), (valor, True)) para tramos." ariaLabel="Ayuda para escribir la expresión" />
          </div>
          {#key curvaActiva.id}
            <IslaDeFormula id={`expresion-curva-${curvaActiva.id}`} bind:valor={curvaActiva.expresion}
                            aria-label="Expresión" aria-invalid={estadoCampo === 'invalida'}
                            oninput={() => curvasEditadas.add(curvaActiva.id)} />
          {/key}
          {#if estadoCampo === 'valida'}<span class="estado-expresion">Se puede graficar</span>{/if}
          {#if estadoCampo === 'invalida'}<span class="estado-expresion">Revisa la expresión</span>{/if}
        </div>
        {#if curvaActiva.tipo === 'limite' || curvaActiva.tipo === 'derivada'}
          <label>{curvaActiva.tipo === 'limite' ? 'Tiende a' : 'Evaluar derivada en (opcional)'}
            <input type="text" bind:value={curvaActiva.destino} maxlength="24" required={curvaActiva.tipo === 'limite' && !destinoIncluido(curvaActiva)}
                   placeholder="1, pi/2, oo…" autocomplete="off" spellcheck="false" />
          </label>
        {/if}
      </fieldset>
    {/if}
    {#if curvaActiva}<div class="teclado" aria-label="Símbolos para la expresión activa">
      <TecladoDeNotacion alInsertar={insertarSimbolo} alComando={ejecutarComando} />
    </div>{/if}
    <div class="acciones">
      {#if curvaActiva}<button type="submit" class="principal" disabled={ocupada}>{ocupada ? 'Preparando…' : 'Dibujar y comparar'}</button>{/if}
    </div>
    </form>
    {#if error}<p class="error" role="alert">{error}</p>{/if}
  </aside>
  {/if}
  {#if error && !panelAbierto}<p class="error error-flotante" role="alert">{error} <button type="button" onclick={alternarFunciones}>Editar función</button></p>{/if}
  {#if definicion}
    <section class="plano" aria-label="Gráfica resultante">
      {#key definicion}
        <Grafica {definicion} laboratorio inmersiva bind:tabulacionAbierta bind:curvasOcultas bind:alturaPanelMovil
                 panelEscritorio={esMovil ? '' : seccionEscritorio}
                 funcionesAbiertas={panelAbierto} alAlternarFunciones={alternarFunciones}
                 alCerrarFunciones={cerrarFunciones}
                 alGuardarFunciones={integrada ? guardarFunciones : null}
                 alCargarFunciones={integrada ? cargarFunciones : null}
                 hayFuncionesParaGuardar={integrada && entradas.length > 0 && entradas.every((entrada) => entrada.expresion.trim())}
                 {clase} {conversacion} {turno} {concepto}
                 {alternativo} />
      {/key}
    </section>
  {/if}
  {#if !definicion && !ocupada}<p class="sin-grafica" role="status">{error || 'Todavía no hay una gráfica para mostrar.'}</p>{/if}
</main>

<style>
  .laboratorio-graficas { position: relative; flex: 1; min-block-size: 0; inline-size: 100%; overflow: hidden; color: var(--ink-primary); }
  .laboratorio-graficas.integrada { block-size: min(68dvh, 42rem); min-block-size: 24rem; }
  .solo-lectores { position: absolute; inline-size: 1px; block-size: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
  .plano { position: absolute; inset: 0; min-inline-size: 0; min-block-size: 0; }
  .muelle-escritorio { position: absolute; z-index: 10; inset-block: 0; inset-inline-start: 0; display: grid; align-content: start; gap: .25rem; inline-size: 3.5rem; padding: .45rem .2rem; border-inline-end: 1px solid var(--trazo-suave); background: var(--surface-panel); }
  .muelle-escritorio button { display: grid; place-items: center; gap: .1rem; min-inline-size: 0; min-block-size: 3.6rem; padding: .3rem .1rem; border: 0; border-radius: var(--radius-sm); background: transparent; color: var(--ink-secondary); font-size: 1.3rem; }
  .muelle-escritorio button span { max-inline-size: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 10px; line-height: 1.1; }
  .muelle-escritorio button.seleccionado { background: var(--accent-surface); color: var(--accent-main); }
  .plano { inset-inline-start: 3.5rem; }
  .laboratorio-graficas.cajon-escritorio .plano { inset-inline-start: 24.5rem; }
  .laboratorio-graficas .panel-funciones { inset-inline-start: 3.5rem; inset-block-start: 0; inset-block-end: 0; inline-size: 21rem; border-radius: 0; box-shadow: none; }
  .laboratorio-graficas .abrir-panel { display: none; }
  .abrir-panel { position: absolute; z-index: 8; inset-block-start: 4.25rem; inset-inline-start: .75rem; box-shadow: var(--shadow-float); font-weight: 750; }
  .panel-funciones { position: absolute; z-index: 7; inset-block-start: 7.5rem; inset-block-end: .75rem; inset-inline-start: .75rem; inline-size: min(25rem, calc(100% - 1.5rem)); overflow-y: auto; overscroll-behavior: contain; padding: 1rem; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-lg); background: var(--surface-panel); box-shadow: var(--shadow-float); }
  .asa-funciones-movil { display: none; }
  header { max-inline-size: 54rem; }
  .ceja { margin: 0; color: var(--accent-main); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; font-size: var(--texto-xs); }
  .titulo-funciones { display: flex; align-items: center; gap: .4rem; }
  h1 { margin: .2rem 0 .4rem; font-size: var(--texto-xl); }
  header p:last-child { margin: 0; color: var(--ink-secondary); line-height: 1.55; }
  .ejemplos { margin-block: .75rem; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .ejemplos summary, .opciones-avanzadas summary { cursor: pointer; font-weight: 700; }
  .ejemplos > div { display: flex; flex-wrap: wrap; gap: .4rem; margin-block-start: .5rem; }
  .ejemplos button { min-block-size: 34px; padding: .35rem .55rem; font-size: var(--texto-xs); }
  button, input, select { font: inherit; }
  button { min-block-size: 42px; padding: .55rem .9rem; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); cursor: pointer; }
  button:disabled { opacity: .6; cursor: not-allowed; }
  button:hover:not(:disabled), button:focus-visible { border-color: var(--accent-main); }
  form { padding: 0; }
  .pestanas-curvas { display: flex; flex-wrap: wrap; gap: .35rem; margin-block: .6rem; }
  .pestanas-curvas button { min-block-size: 38px; padding: .35rem .55rem; font-weight: 750; }
  .pestanas-curvas .seleccionada { border-color: var(--accent-main); background: var(--accent-surface); color: var(--accent-main); }
  .pestanas-curvas .agregar-curva { font-size: 1.2rem; }
  .curva-original { display: inline-flex; align-items: center; min-block-size: 38px; padding: .35rem .55rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); color: var(--ink-secondary); font-weight: 750; }
  .origen-conversacion, .instruccion-agregar { margin: .35rem 0; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .acciones-curva { display: flex; justify-content: flex-end; gap: .35rem; margin-block: .35rem; }
  .acciones-curva button { display: inline-grid; place-items: center; inline-size: 42px; block-size: 42px; padding: 0; }
  .acciones-curva button[aria-pressed='false'] { opacity: .55; }
  .fila-curva { display: grid; gap: .7rem; min-inline-size: 0; margin: .7rem 0; padding: .8rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); }
  legend { font-weight: 750; }
  .muestra { display: inline-block; inline-size: .75rem; block-size: .75rem; margin-inline-end: .25rem; border-radius: 50%; vertical-align: middle; }
  .serie-0 { background: var(--color-violet-light); }.serie-1 { background: var(--color-sky-light); }.serie-2 { background: var(--color-emerald-light); }.serie-3 { background: var(--color-rose-light); }
  label { display: grid; gap: .25rem; color: var(--ink-secondary); font-size: var(--texto-sm); font-weight: 650; }
  .expresion { display: grid; gap: .25rem; min-inline-size: 0; color: var(--ink-secondary); font-size: var(--texto-sm); font-weight: 650; }
  .etiqueta-con-ayuda { display: flex; align-items: center; gap: .35rem; }
  input, select { min-block-size: 42px; padding: .5rem .65rem; border: 1px solid var(--trazo-fuerte); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-primary); }
  .expresion :global(math-field) { display: block; inline-size: 100%; min-block-size: 42px; max-inline-size: 100%; overflow-x: auto; }
  .expresion.valida :global(math-field) { border-color: var(--semantic-success); background: var(--semantic-success-bg); }
  .expresion.invalida :global(math-field) { border-color: var(--semantic-error); background: var(--semantic-error-bg); }
  .estado-expresion { font-size: var(--texto-xs); }
  .expresion.valida .estado-expresion { color: var(--semantic-success); }
  .expresion.invalida .estado-expresion { color: var(--semantic-error); }
  .teclado { min-inline-size: 0; margin-block: .35rem .75rem; }
  .opciones-avanzadas { color: var(--ink-secondary); font-size: var(--texto-sm); }
  .opciones-avanzadas label { margin-block-start: .5rem; }
  .opciones-avanzadas p { line-height: 1.4; }
  .quitar { color: var(--semantic-error); }
  .ayuda { margin: .6rem 0; color: var(--ink-secondary); font-size: var(--texto-sm); }
  code { color: var(--ink-primary); }
  .acciones { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: .6rem; }
  .principal { background: var(--accent-main); border: 0; color: var(--accent-on-main); font-weight: 750; }
  .error { padding: .75rem; border: 1px solid var(--semantic-error); border-radius: var(--radius-sm); color: var(--semantic-error); }
  .error-flotante { position: absolute; z-index: 8; inset-block-start: 7.5rem; inset-inline-start: .75rem; inline-size: min(27rem, calc(100% - 1.5rem)); background: var(--surface-panel); box-shadow: var(--shadow-float); }
  .error-flotante button { display: block; margin-block-start: .5rem; }
  .sin-grafica { position: absolute; inset: 50% auto auto 50%; transform: translate(-50%, -50%); inline-size: min(26rem, 90%); text-align: center; color: var(--ink-secondary); }
  @media (max-width: 48rem) {
    .muelle-escritorio { display: none; }
    .plano, .laboratorio-graficas.cajon-escritorio .plano { inset-inline-start: 0; }
    .laboratorio-graficas .panel-funciones { inset-block-start: auto; inset-block-end: calc(3.85rem + env(safe-area-inset-bottom)); inset-inline: 0; inline-size: 100%; box-shadow: var(--shadow-float); }
    .laboratorio-graficas.integrada { block-size: min(72dvh, 43rem); }
    .abrir-panel { display: none; }
    .panel-funciones { inset-block-start: auto; inset-block-end: calc(3.85rem + env(safe-area-inset-bottom)); inset-inline: 0; inline-size: 100%; block-size: min(var(--altura-panel-movil), calc(100% - 7rem)); max-block-size: none; padding: .75rem; border-radius: var(--radius-lg) var(--radius-lg) 0 0; }
    .asa-funciones-movil { position: sticky; inset-block-start: 0; z-index: 3; display: block; background: var(--surface-panel); }
    .panel-funciones header { display: none; }
    .ejemplos { margin-block: .25rem; }
    .fila-curva { margin: .3rem 0; }
  }
</style>
