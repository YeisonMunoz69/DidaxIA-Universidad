<!--
El área de composición. `PM-F2x` fase 6-c: las fórmulas se editan ya
renderizadas, con islas de MathLive incrustadas en el texto.

Mezcla texto y fórmulas en un mismo mensaje. Envía lo que el estudiante
escribió, SIN REESCRIBIRLO.

«SIN REESCRIBIRLO» ES LITERAL, Y ES LO ÚNICO QUE HAY QUE VIGILAR AQUÍ
---------------------------------------------------------------------
Este componente no recorta espacios, no cambia comillas, no arregla paréntesis
y no convierte `x2` en `x^2`. `RP-01` obliga a normalizar a forma canónica
única ANTES de procesar y esa normalización es del servidor: cualquier arreglo
«inofensivo» de aquí crearía un segundo normalizador, y la garantía de forma
única dejaría de serlo el día que los dos discrepen.

Lo único que se comprueba antes de enviar es que haya ALGO escrito, y eso no es
normalizar: es no mandar un turno vacío.

EL CAMPO ES UNA LISTA DE SEGMENTOS, NO UN `<textarea>`
--------------------------------------------------------
Cada segmento es texto plano (un `<span contenteditable>`) o una fórmula (una
`<IslaDeFormula>`, ver `nucleo/formato/segmentos.js`). Los dos tipos nunca
quedan adyacentes del mismo tipo —lo garantiza `aSegmentos()`, la misma
función que ya usaba el resaltado de esta pantalla—, así que el modelo
siempre alterna, o es un único tramo de texto.

LO QUE SE ENVÍA SE LEE DEL DOM EN EL INSTANTE DE ENVIAR, NO DEL ESTADO
--------------------------------------------------------------------------
`segmentos` (el `$state`) gobierna la ESTRUCTURA —cuántos tramos hay, en qué
orden— para que Svelte sepa qué montar. La cadena que de verdad viaja a
`alEnviar()` se arma recorriendo `campoMixto.children` en ese instante: cada
tramo de texto aporta su `textContent`, cada isla aporta `$` + su
`math-field.value` + `$`. Es la misma garantía que ya tenía un único
`<textarea>` con `bind:value` —una lectura directa de lo que el navegador
tiene ahora, nunca una copia que pudo desincronizarse un evento atrás—,
generalizada de «el `.value` de un control» a «el recorrido de los hijos de
un contenedor».

LOS TRAMOS DE TEXTO NO SE REESCRIBEN EN CADA TECLA
------------------------------------------------------
Si la plantilla interpolara `{s.valor}` dentro del `<span>`, cada pulsación
dispararía: el navegador ya insertó el carácter → Svelte vuelve a poner ese
mismo contenido → **el cursor salta al principio**, porque Svelte no sabe
dónde estaba el caret al reescribir el `textContent`. La acción
`contenidoInicial` escribe el contenido UNA VEZ, al montar el nodo —cuando
nace un tramo nuevo: al partir uno en el `$` que cierra una fórmula, al
insertar un símbolo, al fusionar dos tramos tras borrar la isla entre
ellos—, y de ahí en adelante el navegador es su dueño. Un tramo que solo
gana caracteres (tecleo normal, sin cerrar ninguna fórmula) NUNCA cambia de
identidad —mismo `id`, mismo nodo— y por eso nunca se vuelve a escribir.

UNA ISLA NO NACE VACÍA
--------------------------
`redactor.prueba.js`/`segmentos-de-redactor.prueba.js` protegen
`'me costó $50 y no me sale'`: un `$` suelto es un dólar, no el principio de
una fórmula. Por eso ninguna isla se crea al teclear el primer `$` — nace ya
con contenido, cuando el segundo `$` cierra el par, o cuando una tecla de
`TecladoDeNotacion` inserta un fragmento ya completo.

INTRO HACE PÁRRAFO EN TELÉFONO; EN PC ENVÍA, SALVO MAYÚS+INTRO
---------------------------------------------------------------------
Un `<span contenteditable>` no tiene la garantía de un `<textarea>` sobre lo
que hace Intro por dentro —insertar un `<div>`, un `<br>`, según el
navegador—, y un `<br>` no aparece en `textContent`: si el navegador lo
metiera solo, el salto de línea desaparecería de lo que se envía sin que
nada lo avisara. Por eso Mayús+Intro inserta un nodo de texto `'\n'` a mano
—`insertarSaltoDeLinea()`— en vez de confiar en el navegador.

EL BOTÓN NO DESAPARECE MIENTRAS SE ESPERA: se deshabilita. Un control que se
quita del árbol mueve el foco a donde el navegador decida, y quien navega con
teclado pierde el sitio en cada turno.

`VistaPreviaDeFormula` YA NO VIVE AQUÍ, Y ES A PROPÓSITO
------------------------------------------------------------
Existía para ver que `x^2+1` se dibujaba como se esperaba ANTES de enviar —
la razón dejó de aplicar el día que las fórmulas empezaron a editarse ya
renderizadas, en su propia isla, en el mismo sitio donde se escriben. Y
tenía un costo que no se veía hasta comparar los dos: `VistaPreviaDeFormula`
llama a `renderizar()` de `notacion.js`, un KaTeX aparte del que ya vive
dentro de cada `<math-field>` — dos motores pintando la misma fórmula por
caminos distintos es exactamente la clase de duplicación que este árbol
evita en todos los demás sitios («dos definiciones de qué es notación
acaban discrepando», `notacion.js`). Se retiró en vez de mantenerse como
adorno.

RIESGO QUE ESTE ARCHIVO NO RESUELVE, Y SE DICE
--------------------------------------------------
Cada tramo de texto es su PROPIO `contenteditable`, no una única región
compartida —así el mapeo «qué segmento se está editando» es directo, por
`data-segmento-id`, y no exige leer la selección para adivinarlo—. Falta
verificar con un lector de pantalla real si el conjunto se anuncia con
sentido: es la tanda 6-f del plan, no una promesa ya cumplida aquí.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

-->
<script>
  import { onMount, tick } from 'svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import TecladoDeNotacion from './TecladoDeNotacion.svelte';
  import IslaDeFormula from './IslaDeFormula.svelte';
  import { nuevoIdDeSegmento, serializar } from '../../nucleo/formato/segmentos.js';
  import {
    actualizarTexto,
    eliminarFormula,
    insertarFormula,
    segmentoDeFormula,
    segmentoDeTexto
  } from './redactor/edicionDeSegmentos.js';
  import {
    colocarCaret,
    colocarCaretEnPosicion,
    contenidoInicial,
    enfocarSegmentoEnDOM,
    insertarTextoEnSeleccion,
    posicionDelCaret
  } from './redactor/seleccionDelRedactor.js';
  import { serializarDesdeDOM } from './redactor/serializacionDelRedactor.js';

  let {
    /** true mientras hay un turno en vuelo. */
    ocupado = false,
    /** Se invoca con el texto TAL CUAL. */
    alEnviar,
    /** ¿Están desplegadas las teclas? Recogidas al empezar: ver `.acciones`. */
    tecladoAbierto = $bindable(false),
    /** Oculta el acceso flotante al panel mientras se compone el mensaje. */
    editando = $bindable(false)
  } = $props();

  // Un id hoisted y no `segmentos[0].id`: leer el propio `$state` para
  // fijar el valor inicial de otro solo captura ese primer valor y Svelte
  // lo avisa (`state_referenced_locally`) porque casi siempre es un
  // descuido — aquí no lo es, pero se evita la señal de alarma en vez de
  // acallarla.
  const idInicial = nuevoIdDeSegmento();

  /** @type {import('../../nucleo/formato/segmentos.js').Segmento[]} */
  let segmentos = $state([{ id: idInicial, tipo: 'texto', valor: '' }]);
  /** El id del último segmento que tuvo el foco — sigue sirviendo de
      destino para `insertar()` aunque el foco ya se haya ido al botón
      «Símbolos», que es justo lo que pasa al pulsar una tecla del cajón. */
  let ultimoSegmentoId = $state(idInicial);
  /** @type {HTMLDivElement | undefined} */
  let campoMixto;
  /** @type {HTMLFormElement | undefined} */
  let formulario;
  /** La selección del texto puede perderse al tocar una pestaña del panel. */
  const posicionesDeTexto = new Map();

  function pantallaTactil() {
    return typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches;
  }

  /** @param {HTMLElement} span */
  function recordarPosicionDeTexto(span) {
    const id = Number(span.dataset.segmentoId);
    const ancla = window.getSelection()?.anchorNode;
    if (Number.isFinite(id) && ancla && span.contains(ancla)) {
      posicionesDeTexto.set(id, posicionDelCaret(span));
    }
  }

  const SUGERENCIAS_PLACEHOLDER = [
    'Escribe tu duda o fórmula (ej. ¿cuál es la derivada de x² · cos(x)?)...',
    'Pregunta sobre límites, derivadas o reglas de derivación...',
    'Pulsa ∑ Símbolos para insertar fracciones, potencias y raíces...',
    'Escribe fórmulas entre $...$ o usa el teclado matemático...'
  ];

  let indicePlaceholder = $state(0);
  let placeholderTexto = $derived(SUGERENCIAS_PLACEHOLDER[indicePlaceholder]);

  $effect(() => {
    const intervalo = setInterval(() => {
      indicePlaceholder = (indicePlaceholder + 1) % SUGERENCIAS_PLACEHOLDER.length;
    }, 4500);
    return () => clearInterval(intervalo);
  });

  const hayAlgo = $derived(
    segmentos.some((s) => s.tipo === 'formula' || s.valor.trim().length > 0)
  );

  // ── Foco y caret ──────────────────────────────────────────────────────

  /** @param {FocusEvent} evento */
  function alEnfocarSegmento(evento) {
    editando = true;
    const objetivo = /** @type {HTMLElement | null} */ (evento.target);
    const span = /** @type {HTMLElement | null} */ (objetivo?.closest?.('[data-segmento-id]'));
    if (!span) return;
    // MathLive no siempre recoge su teclado al salir de la isla. Sobre un
    // teléfono taparía el editor de texto y competiría con el teclado nativo.
    if (span.classList.contains('segmento-texto')) {
      window.mathVirtualKeyboard?.hide?.();
      if (pantallaTactil()) tecladoAbierto = false;
    } else if (pantallaTactil()) {
      // MathLive edita la isla; el panel único del redactor aporta las teclas.
      window.mathVirtualKeyboard?.hide?.();
      tecladoAbierto = true;
    }
    ultimoSegmentoId = Number(span.dataset.segmentoId);
  }

  /** @param {number} id */
  function alTocarFormula(id) {
    ultimoSegmentoId = id;
    editando = true;
    if (pantallaTactil()) {
      window.mathVirtualKeyboard?.hide?.();
      tecladoAbierto = true;
    }
  }

  /** @param {FocusEvent} evento */
  function alSalirDelRedactor(evento) {
    const span = /** @type {HTMLElement | null} */ (evento.target)?.closest?.('.segmento-texto');
    if (span) recordarPosicionDeTexto(span);
    // El foco puede pasar del math-field (shadow DOM) al texto en el mismo
    // gesto. Esperar un cuadro evita parpadear el control flotante entre ambos.
    requestAnimationFrame(() => {
      if (!campoMixto?.contains(document.activeElement) && !tecladoAbierto) editando = false;
    });
  }

  function alternarTeclado() {
    window.mathVirtualKeyboard?.hide?.();
    if (tecladoAbierto) {
      // En navegadores táctiles, pulsar un botón no siempre desenfoca
      // <math-field>. Sin blur, el siguiente toque no emite focusin y el
      // teclado no volvería a abrirse.
      if (pantallaTactil()) {
        campoMixto?.querySelector(`[data-segmento-id="${ultimoSegmentoId}"] math-field`)?.blur?.();
      }
      tecladoAbierto = false;
      return;
    }
    const activo = /** @type {HTMLElement | null} */ (document.activeElement);
    if (activo?.classList.contains('segmento-texto')) recordarPosicionDeTexto(activo);
    if (pantallaTactil()) activo?.blur?.();
    tecladoAbierto = true;
    editando = true;
  }

  function cerrarTeclados() {
    const activo = /** @type {HTMLElement | null} */ (document.activeElement);
    if (activo?.classList.contains('segmento-texto')) recordarPosicionDeTexto(activo);
    window.mathVirtualKeyboard?.hide?.();
    campoMixto?.querySelectorAll('math-field').forEach((campo) => campo.blur());
    activo?.blur?.();
    tecladoAbierto = false;
    editando = false;
  }

  onMount(() => {
    /** @param {PointerEvent} evento */
    const alTocarFuera = (evento) => {
      if (formulario?.contains(/** @type {Node} */ (evento.target))) return;
      // Leer, seleccionar o desplazar el hilo no abandona el borrador.
      if (evento.target instanceof Element && evento.target.closest('.hilo')) return;
      if (!tecladoAbierto && !editando) return;
      tecladoAbierto = false;
      editando = false;
      window.mathVirtualKeyboard?.hide?.();
      if (campoMixto?.contains(document.activeElement)) {
        /** @type {HTMLElement} */ (document.activeElement)?.blur?.();
      }
    };
    document.addEventListener('pointerdown', alTocarFuera);
    return () => document.removeEventListener('pointerdown', alTocarFuera);
  });

  /** @param {number} indice @param {'inicio'|'final'} extremo */
  function enfocarSegmento(indice, extremo) {
    if (!campoMixto) return;
    enfocarSegmentoEnDOM(campoMixto, segmentos, indice, extremo);
  }

  /** @param {number} indice @param {'forward'|'backward'} direccion */
  function moverFocoHacia(indice, direccion) {
    const vecino = direccion === 'forward' ? indice + 1 : indice - 1;
    if (vecino >= 0 && vecino < segmentos.length) {
      enfocarSegmento(vecino, direccion === 'forward' ? 'inicio' : 'final');
      return;
    }
    const nuevo = segmentoDeTexto('');
    segmentos = direccion === 'forward' ? [...segmentos, nuevo] : [nuevo, ...segmentos];
    tick().then(() => {
      enfocarSegmento(direccion === 'forward' ? segmentos.length - 1 : 0, 'inicio');
    });
  }

  // ── El tramo de texto: escribir, partir, pegar, saltar el borde ────────

  /** @param {number} id @param {HTMLElement} span */
  function actualizarValorDelSegmento(id, span) {
    const contenido = span.textContent ?? '';
    const resultado = actualizarTexto(segmentos, id, contenido);
    // Una fórmula final necesita un destino de texto real para continuar con
    // el teclado del teléfono. No se añade nada al mensaje: el tramo va vacío.
    segmentos = resultado.segmentos.at(-1)?.tipo === 'formula'
      ? [...resultado.segmentos, segmentoDeTexto('')]
      : resultado.segmentos;
    if (resultado.foco) {
      tick().then(() => enfocarSegmento(resultado.foco.indice, resultado.foco.extremo));
    }
  }

  /** @param {number} id @param {Event} evento */
  function alEscribirEnTexto(id, evento) {
    const span = /** @type {HTMLElement} */ (evento.currentTarget);
    const contenido = span.textContent ?? '';
    span.dataset.vacio = contenido.length === 0 ? 'true' : 'false';
    recordarPosicionDeTexto(span);
    actualizarValorDelSegmento(id, span);
  }

  /** @param {number} id @param {KeyboardEvent} evento */
  function alTeclearEnTexto(id, evento) {
    if (evento.isComposing || evento.keyCode === 229) return;
    const indice = segmentos.findIndex((s) => s.id === id);
    if (indice === -1) return;
    const span = /** @type {HTMLElement} */ (evento.currentTarget);

    if (evento.key === 'Enter') {
      evento.preventDefault();
      if (evento.shiftKey || pantallaTactil()) {
        insertarTextoEnSeleccion('\n');
        actualizarValorDelSegmento(id, span);
      } else {
        enviar();
      }
      return;
    }

    if (evento.key === 'Backspace' && posicionDelCaret(span) === 0) {
      if (indice > 0) {
        evento.preventDefault();
        if (segmentos[indice - 1].tipo === 'formula') {
          eliminarIsla(segmentos[indice - 1].id);
        } else {
          const anterior = segmentos[indice - 1];
          anterior.valor += span.textContent ?? '';
          segmentos = [...segmentos.slice(0, indice), ...segmentos.slice(indice + 1)];
          tick().then(() => {
            if (!campoMixto) return;
            const nodoAnt = campoMixto.querySelector(`[data-segmento-id="${anterior.id}"]`);
            if (nodoAnt) colocarCaret(/** @type {HTMLElement} */ (nodoAnt), 'final');
          });
        }
        return;
      }
    }

    if (evento.key === 'ArrowLeft' && !evento.shiftKey && posicionDelCaret(span) === 0) {
      if (indice > 0) {
        evento.preventDefault();
        enfocarSegmento(indice - 1, 'final');
        return;
      }
    }

    if (evento.key === 'ArrowRight' && !evento.shiftKey && posicionDelCaret(span) === (span.textContent?.length ?? 0)) {
      if (indice < segmentos.length - 1) {
        evento.preventDefault();
        enfocarSegmento(indice + 1, 'inicio');
        return;
      }
    }
  }

  /** Algunos teclados móviles insertan un párrafo sin emitir keydown. */
  function antesDeEscribir(id, evento) {
    if (evento.isComposing || !['insertParagraph', 'insertLineBreak'].includes(evento.inputType)) return;
    evento.preventDefault();
    const span = evento.currentTarget;
    insertarTextoEnSeleccion('\n');
    actualizarValorDelSegmento(id, span);
  }

  /** @param {number} id @param {ClipboardEvent} evento */
  function alPegar(id, evento) {
    evento.preventDefault();
    const texto = evento.clipboardData?.getData('text/plain') ?? '';
    if (!insertarTextoEnSeleccion(texto)) return;
    const span = /** @type {HTMLElement} */ (evento.currentTarget);
    actualizarValorDelSegmento(id, span);
  }

  // ── La isla: salir por el borde, borrarla entera ────────────────────────

  /** @param {number} id @param {'forward'|'backward'} direccion */
  function alSalirDeIsla(id, direccion) {
    const indice = segmentos.findIndex((s) => s.id === id);
    if (indice === -1) return;
    moverFocoHacia(indice, direccion);
  }

  /** @param {number} id */
  function eliminarIsla(id) {
    const resultado = eliminarFormula(segmentos, id);
    segmentos = resultado.segmentos;
    tick().then(() => {
      if (!campoMixto || !resultado.foco) return;
      const nodo = campoMixto.querySelector(`[data-segmento-id="${resultado.foco.id}"]`);
      if (nodo) {
        colocarCaretEnPosicion(/** @type {HTMLElement} */ (nodo), resultado.foco.posicion);
      }
    });
  }

  // ── El teclado de símbolos: inserta en el tramo activo ────────────────

  /** @param {string} fragmentoConDelimitadores p.ej. `'$\\frac{a}{b}$'` */
  function insertar(fragmentoConDelimitadores) {
    const latex = fragmentoConDelimitadores.slice(1, -1);
    const indice = segmentos.findIndex((s) => s.id === ultimoSegmentoId);
    const segmento = indice === -1 ? null : segmentos[indice];

    if (segmento?.tipo === 'formula') {
      const nodo = /** @type {any} */ (
        campoMixto?.querySelector(`[data-segmento-id="${segmento.id}"] math-field`)
      );
      nodo?.focus?.();
      nodo?.executeCommand?.(['insert', latex]);
      return;
    }

    const indiceTexto = indice === -1 || segmento?.tipo !== 'texto' ? segmentos.length - 1 : indice;
    const sTexto = segmentos[indiceTexto];
    const span = /** @type {HTMLElement|null} */ (
      campoMixto?.querySelector(`[data-segmento-id="${sTexto?.id}"]`)
    );

    const seleccion = window.getSelection();
    const posicionActual = span && seleccion?.anchorNode && span.contains(seleccion.anchorNode)
      ? posicionDelCaret(span)
      : null;
    const pos = posicionActual ?? posicionesDeTexto.get(sTexto?.id) ?? (sTexto?.valor.length ?? 0);
    const resultado = insertarFormula(segmentos, indiceTexto, pos, latex);
    segmentos = resultado.segmentos;
    tick().then(() => {
      if (resultado.foco) enfocarSegmento(resultado.foco.indice, resultado.foco.extremo);
    });
  }

  /** @param {string | [string, string]} comando */
  function ejecutarComandoDeTeclado(comando) {
    const segmento = segmentos.find((s) => s.id === ultimoSegmentoId);
    if (segmento?.tipo === 'texto') {
      const span = /** @type {HTMLElement|null} */ (
        campoMixto?.querySelector(`[data-segmento-id="${segmento.id}"]`)
      );
      if (!span) return;
      const texto = span.textContent ?? segmento.valor;
      const seleccion = window.getSelection();
      const posicion = seleccion?.anchorNode && span.contains(seleccion.anchorNode)
        ? posicionDelCaret(span)
        : posicionesDeTexto.get(segmento.id) ?? texto.length;
      if (Array.isArray(comando) && comando[1] === '\\frac{#@}{#?}') {
        const numero = texto.slice(0, posicion).match(/\d+(?:[.,]\d+)?$/)?.[0];
        if (!numero) {
          insertar('$\\frac{\\placeholder{}}{\\placeholder{}}$');
          return;
        }
        const indice = segmentos.findIndex((s) => s.id === segmento.id);
        segmentos = [
          ...segmentos.slice(0, indice),
          segmentoDeTexto(texto.slice(0, posicion - numero.length)),
          segmentoDeFormula(`\\frac{${numero}}{\\placeholder{}}`),
          segmentoDeTexto(texto.slice(posicion)),
          ...segmentos.slice(indice + 1)
        ];
        void tick().then(() => enfocarSegmento(indice + 1, 'final'));
        return;
      }
      if (comando === 'deleteBackward' && posicion > 0) {
        const nuevo = texto.slice(0, posicion - 1) + texto.slice(posicion);
        span.textContent = nuevo;
        segmentos = actualizarTexto(segmentos, segmento.id, nuevo).segmentos;
        colocarCaretEnPosicion(span, posicion - 1);
        posicionesDeTexto.set(segmento.id, posicion - 1);
        return;
      }
      const desplazamiento = {
        moveToPreviousChar: -1,
        moveToNextChar: 1
      }[typeof comando === 'string' ? comando : ''];
      let nuevaPosicion = desplazamiento ? posicion + desplazamiento : posicion;
      if (comando === 'moveUp') {
        const inicio = texto.lastIndexOf('\n', posicion - 1) + 1;
        if (inicio > 0) {
          const finAnterior = inicio - 1;
          const inicioAnterior = texto.lastIndexOf('\n', finAnterior - 1) + 1;
          nuevaPosicion = Math.min(finAnterior, inicioAnterior + posicion - inicio);
        }
      } else if (comando === 'moveDown') {
        const fin = texto.indexOf('\n', posicion);
        if (fin >= 0) {
          const inicioSiguiente = fin + 1;
          const finSiguiente = texto.indexOf('\n', inicioSiguiente);
          nuevaPosicion = Math.min(finSiguiente < 0 ? texto.length : finSiguiente,
            inicioSiguiente + posicion - (texto.lastIndexOf('\n', posicion - 1) + 1));
        }
      }
      if (nuevaPosicion !== posicion) {
        nuevaPosicion = Math.max(0, Math.min(texto.length, nuevaPosicion));
        colocarCaretEnPosicion(span, nuevaPosicion);
        posicionesDeTexto.set(segmento.id, nuevaPosicion);
      }
      return;
    }
    if (segmento?.tipo !== 'formula') return;
    const nodo = /** @type {any} */ (
      campoMixto?.querySelector(`[data-segmento-id="${segmento.id}"] math-field`)
    );
    if (!nodo) return;
    if (comando === 'deleteBackward' && !nodo.value?.trim()) {
      eliminarIsla(segmento.id);
      return;
    }
    nodo.focus?.();
    nodo.executeCommand?.(comando);
  }

  /** Somete el turno: texto con `$…$` de vuelta. `RP-01`. */
  function enviar() {
    if (ocupado) return;
    const desdeDOM = serializarDesdeDOM(campoMixto);
    const mensaje = desdeDOM || serializar(segmentos);
    if (!mensaje.trim()) return;
    alEnviar?.(mensaje);
    segmentos = [segmentoDeTexto('')];
    posicionesDeTexto.clear();
    tecladoAbierto = false;
    tick().then(() => enfocarSegmento(0, 'inicio'));
  }

  /** @param {HTMLElement} nodo */
  function escucharClicEnCaja(nodo) {
    const alInteractuar = (evento) => {
      if (evento.defaultPrevented || evento.button !== 0) return;
      const objetivo = /** @type {HTMLElement} */ (evento.target);
      if (
        objetivo.closest('button') ||
        objetivo.closest('math-field') ||
        objetivo.closest('.eliminar-formula') ||
        objetivo.closest('[data-segmento-id]')
      ) {
        return;
      }
      const ultimo = segmentos.length - 1;
      enfocarSegmento(ultimo >= 0 ? ultimo : 0, 'final');
    };
    // Tras completar el gesto: en pointerdown el foco nativo del fondo lo
    // quitaba de nuevo. click mantiene el foco dentro del gesto del usuario
    // para el teclado táctil y no se dispara al desplazar la caja.
    nodo.addEventListener('click', alInteractuar);
    return {
      destroy() {
        nodo.removeEventListener('click', alInteractuar);
      }
    };
  }
</script>

<form class="redactor" bind:this={formulario} class:con-teclado={tecladoAbierto} onsubmit={(e) => { e.preventDefault(); enviar(); }}>
  <div class="caja-de-entrada" use:escucharClicEnCaja>
    {#if editando || tecladoAbierto}
      <button type="button" class="cerrar-teclados" aria-label="Cerrar teclado"
              title="Cerrar teclado" onclick={cerrarTeclados}>
        <Icono nombre="teclado-cerrar" medida={19} />
      </button>
    {/if}
    <div class="campo">
      <span class="etiqueta solo-lectura-asistida" id="etiqueta-redactor">Escribe tu duda o tu intento</span>

      <div class="campo-mixto"
           bind:this={campoMixto}
           role="group"
           aria-labelledby="etiqueta-redactor"
           aria-describedby="redactor-ayuda"
           onfocusin={alEnfocarSegmento}
           onfocusout={alSalirDelRedactor}>
        {#each segmentos as s, indice (s.id)}
          {#if s.tipo === 'texto'}
            <span class="segmento segmento-texto"
                  data-segmento-id={s.id}
                  data-placeholder={placeholderTexto}
                  data-vacio={!s.valor ? 'true' : 'false'}
                  contenteditable="true"
                  role="textbox"
                  aria-multiline="true"
                  tabindex="0"
                  use:contenidoInicial={s.valor}
                  oninput={(e) => alEscribirEnTexto(s.id, e)}
                  onbeforeinput={(e) => antesDeEscribir(s.id, e)}
                  enterkeyhint={pantallaTactil() ? 'enter' : 'send'}
                  onkeydown={(e) => alTeclearEnTexto(s.id, e)}
                  onkeyup={(e) => recordarPosicionDeTexto(e.currentTarget)}
                  onpointerup={(e) => recordarPosicionDeTexto(e.currentTarget)}
                  onpaste={(e) => alPegar(s.id, e)}
            ></span>
          {:else}
            <span class="segmento segmento-formula" data-segmento-id={s.id}>
              <IslaDeFormula bind:valor={s.valor}
                             alInteractuar={() => alTocarFormula(s.id)}
                             alSalir={(/** @type {'forward'|'backward'} */ direccion) =>
                               alSalirDeIsla(s.id, direccion)}
                             alEliminar={() => eliminarIsla(s.id)}
                             alEnviar={enviar} />
              {#if segmentos[indice + 1]?.tipo === 'texto'}
                <button type="button" class="continuar-texto"
                        aria-label="Continuar escribiendo texto después de la fórmula"
                        onclick={() => enfocarSegmento(indice + 1, 'inicio')}>Texto ↗</button>
              {/if}
              <button type="button" class="eliminar-formula"
                      aria-label="Eliminar esta fórmula"
                      onclick={() => eliminarIsla(s.id)}>
                <Icono nombre="cerrar" medida={12} />
              </button>
            </span>
          {/if}
        {/each}
      </div>
      <p id="redactor-ayuda" class="ayuda solo-lectura-asistida">
        Puedes escribir en español y notación —entre <code>$…$</code>— en el mismo
        mensaje: se ve ya renderizada. En teléfono, Intro hace un párrafo nuevo y el
        botón de la flecha envía. En computador, Intro envía y Mayús + Intro hace un párrafo nuevo.
      </p>
    </div>

    <div class="acciones">
      <div class="acciones-izq">
        <button type="button" class="btn-simbolos"
                class:activo={tecladoAbierto}
                onclick={alternarTeclado}
                data-tooltip={tecladoAbierto ? 'Ocultar teclado matemático' : 'Teclado matemático'}
                data-tooltip-pos="arriba"
                aria-expanded={tecladoAbierto}
                aria-controls="teclado-de-notacion">
          <span class="simbolo-sigma" aria-hidden="true">∑</span>
          <span>{tecladoAbierto && pantallaTactil() ? 'Ocultar teclado' : 'Símbolos'}</span>
        </button>
      </div>

      <button type="submit" class="btn-enviar"
              data-tooltip={pantallaTactil() ? 'Enviar mensaje' : 'Enviar mensaje (Intro)'}
              data-tooltip-pos="arriba"
              aria-label={ocupado ? 'Esperando respuesta…' : pantallaTactil() ? 'Enviar mensaje' : 'Enviar mensaje (o presiona Enter)'}
              disabled={!hayAlgo || ocupado}>
        {#if ocupado}
          <span class="cargando-puntos" aria-hidden="true">…</span>
        {:else}
          <Icono nombre="enviar" medida={18} />
        {/if}
      </button>
    </div>
  </div>

  <!--
    EL CAJÓN SE QUEDA MONTADO, Y ES `inert` QUIEN LO CIERRA.

    `grid-template-rows: 0fr → 1fr` anima hasta el alto de contenido —
    `height: 0 → auto` no se anima en CSS estándar—, y por eso el cajón se
    queda siempre en el árbol, colapsado por CSS y no por montaje. Lo cierra
    `inert`, el mismo mecanismo que ya usa el carril/panel del armazón para
    su propio cajón: sin él, doce botones quedarían alcanzables por teclado
    aunque no se vean.
  -->
  <div class="cajon-teclado" id="teclado-de-notacion"
       class:abierto={tecladoAbierto} inert={!tecladoAbierto}>
    <div class="cajon-interior">
      <div class="cabecera-teclado-movil">
        <span>Teclado matemático</span>
        <button type="button" onclick={alternarTeclado} aria-label="Ocultar teclado matemático">
          Ocultar
        </button>
      </div>
      <TecladoDeNotacion alInsertar={insertar} alComando={ejecutarComandoDeTeclado} />
    </div>
  </div>
</form>

<style>
  .cerrar-teclados { display: none; }
  /* --corte-escritorio de tokens.css; CSS no admite var() en esta consulta. */
  @media (max-width: 75rem), (pointer: coarse) {
    .cerrar-teclados { position: absolute; inset-block-start: 2px; inset-inline-end: 2px;
      z-index: 4; display: grid; place-items: center; inline-size: 44px; block-size: 44px;
      border: 0; border-radius: var(--radius-sm); background: transparent;
      color: var(--ink-secondary); cursor: pointer; }
    .cerrar-teclados:hover { color: var(--accent-main); background: var(--surface-panel); }
    .caja-de-entrada:has(.cerrar-teclados) .campo { padding-inline-end: 2rem; }
  }
  .redactor {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    /* NO `max-inline-size: var(--ancho-lectura)`: ese tope es para prosa
       —párrafos, burbujas de `Turno.svelte`— y aquí encogía el redactor
       muy por debajo de lo que ya deja libre `.pie` en
       `Conversacion.svelte`, angostando de paso el teclado de notación
       que vive dentro. El ancho lo pone quien nos envuelve. */
    inline-size: 100%;
    transition: var(--transition);
  }

  /*
    LA CAJA FLOTANTE, DEL MOCKUP —`.input-box`—.

    Agrupa el campo y la fila de acciones en un solo panel con su propio
    fondo, y se resalta entera al enfocar cualquier tramo de dentro
    (`:focus-within`). El borde de VERDAD —el que `WCAG 2.2 · 1.4.11` exige
    medido— sigue siendo el de `.campo-mixto`, más abajo, sin tocar: este
    panel es un marco alrededor, no un sustituto.

    Sin gradiente y sin sombra fuerte, que es la misma regla que ya declara
    `Boton.svelte` para los botones: el lenguaje de este proyecto los
    prohíbe los dos, y el mockup los usa en su versión de esta caja. Un
    fondo plano y un resalte de foco bastan para el mismo efecto de "panel
    que responde".
  */
  .caja-de-entrada {
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 0.4rem;
    padding: 12px 16px;
    background: var(--surface-paper);
    border: 1.5px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
    transition: all 0.2s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .caja-de-entrada:hover {
    border-color: var(--trazo);
    box-shadow: var(--shadow-card-hover);
    transform: translateY(-1px);
  }

  .caja-de-entrada:focus-within {
    border-color: var(--accent-main);
    box-shadow: 0 0 0 3px var(--accent-glow), var(--shadow-card-hover);
    transform: translateY(-1px);
  }

  .campo {
    display: flex;
    flex-direction: column;
    gap: 0;
    padding: 0;
    flex: 1;
    min-block-size: 0;
  }

  .etiqueta { font-size: var(--texto-sm); font-weight: 500; }

  /*
    EL CAMPO MIXTO: TEXTO Y FÓRMULAS EN EL MISMO FLUJO.

    Los tramos permanecen inline para que una fórmula intercalada no convierta
    la prosa larga en columnas flexibles con espacio muerto a la derecha. Cada tramo de texto es su
    propio `contenteditable`; cada isla, un componente aparte. El navegador
    reparte el cursor y el foco entre ellos con el mismo mecanismo que entre
    cualquier par de elementos enfocables — lo que SÍ hace falta a mano es
    saltar el borde cuando el vecino es una isla, y eso lo hacen los
    manejadores de teclado del guion, no esta hoja de estilos.
  */
  .campo-mixto {
    position: relative;
    display: block;
    gap: 0;
    padding: 0.2em 0.1em;
    min-block-size: 2.2rem;
    max-block-size: 8rem;
    overflow-y: auto;
    border: none;
    font-size: var(--texto-base);
    line-height: 1.4;
    color: var(--ink-primary);
    background: transparent;
    cursor: text;
    caret-color: var(--accent-main);
  }

  .segmento-texto {
    display: inline;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    min-inline-size: 8px;
    min-block-size: 1.4em;
    cursor: text;
    caret-color: var(--accent-main);
  }

  .segmento-texto:last-child {
    min-inline-size: 60px;
    min-block-size: 2.2rem;
  }

  .segmento-texto:last-child:empty,
  .segmento-texto:last-child[data-vacio="true"] {
    display: inline-block;
  }

  .segmento-texto:only-child {
    display: block;
    inline-size: 100%;
    min-inline-size: 100%;
    min-block-size: 2.2rem;
  }

  .segmento-texto:only-child:empty::before,
  .segmento-texto:only-child[data-vacio="true"]::before {
    content: attr(data-placeholder);
    position: absolute;
    top: 0.2em;
    left: 0.1em;
    right: 0.1em;
    color: var(--ink-tertiary);
    opacity: 0.65;
    pointer-events: none;
    user-select: none;
    line-height: 1.4;
    white-space: normal;
    word-break: break-word;
    cursor: text;
  }

  .segmento-texto:focus,
  .segmento-texto:focus-visible {
    outline: none;
    box-shadow: none;
    border-color: transparent;
    background: transparent;
  }

  .segmento-formula {
    display: inline-flex;
    align-items: center;
    margin-inline: 1px;
    gap: 0.15rem;
  }

  .continuar-texto { display: none; }

  @media (pointer: coarse) {
    .continuar-texto {
      display: inline-flex;
      align-items: center;
      min-block-size: 32px;
      padding: 0 .35rem;
      border: 1px solid var(--trazo-suave);
      border-radius: var(--radius-xs);
      background: var(--surface-panel);
      color: var(--accent-main);
      font: inherit;
      font-size: var(--texto-xs);
      cursor: pointer;
    }
  }

  /* Oculto hasta que se necesita —al pasar el ratón o al enfocar algo
     dentro de la isla—, y NO con `display`/`visibility`: sigue alcanzable
     por teclado y por lector de pantalla aunque no se vea todavía. */
  .eliminar-formula {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    inline-size: 1.1rem;
    block-size: 1.1rem;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: var(--radius-xs);
    color: var(--ink-tertiary);
    opacity: 0;
    transition: var(--transition-fast);
  }

  .segmento-formula:hover .eliminar-formula,
  .segmento-formula:focus-within .eliminar-formula {
    opacity: 1;
  }

  .eliminar-formula:hover {
    color: var(--semantic-error);
    background: var(--semantic-error-bg);
  }

  .ayuda {
    margin: 0;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  .ayuda code { font-family: var(--fuente-mono); }

  /* Los símbolos a la izquierda y el envío a la derecha: la acción que cierra
     el turno queda donde el pulgar la busca, y la que solo ayuda a escribir no
     compite con ella. */
  .acciones {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-block-start: auto;
    padding-block-start: 0.4rem;
    flex-shrink: 0;
  }

  .acciones-izq {
    display: flex;
    align-items: center;
  }

  .btn-simbolos {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 6px 12px;
    min-block-size: 32px;
    background: transparent;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    color: var(--ink-secondary);
    font: inherit;
    font-size: 12px;
    font-weight: 600;
    line-height: 1;
    cursor: pointer;
    transition: var(--transition);
  }

  .btn-simbolos:hover,
  .btn-simbolos.activo {
    background: var(--accent-surface);
    color: var(--accent-main);
    border-color: var(--accent-main);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px var(--accent-glow);
  }

  .btn-simbolos:active {
    transform: translateY(0) scale(0.96);
  }

  .simbolo-sigma {
    display: inline-block;
    font-family: var(--fuente-mono);
    font-size: 13.5px;
    font-weight: 700;
    line-height: 1;
    position: relative;
    top: -1.5px;
    transform-origin: center center;
    transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .btn-simbolos span:not(.simbolo-sigma) {
    display: inline-block;
    line-height: 1;
  }

  .btn-simbolos.activo .simbolo-sigma {
    transform: rotate(15deg) scale(1.15);
  }

  .btn-enviar {
    background: var(--accent-gradient);
    color: var(--surface-paper);
    border: none;
    border-radius: 50%;
    width: 34px;
    height: 34px;
    min-width: 34px;
    min-height: 34px;
    display: inline-flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    transition: var(--transition);
    box-shadow: 0 2px 8px var(--accent-glow);
    flex-shrink: 0;
  }

  .btn-enviar :global(svg) {
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .btn-enviar:hover:not(:disabled) {
    transform: translateY(-1.5px) scale(1.06);
    box-shadow: 0 4px 16px var(--accent-glow);
    filter: brightness(1.1);
  }

  .btn-enviar:hover:not(:disabled) :global(svg) {
    transform: scale(1.15);
  }

  .btn-enviar:active:not(:disabled) {
    transform: translateY(0) scale(0.93);
  }

  .btn-enviar:disabled {
    opacity: 0.45;
    cursor: not-allowed;
    filter: grayscale(0.7);
    box-shadow: none;
  }

  .cargando-puntos {
    font-size: 14px;
    line-height: 1;
    letter-spacing: 1px;
    display: inline-block;
    animation: pulsoPuntos 1.2s ease-in-out infinite;
  }

  @keyframes pulsoPuntos {
    0%, 100% {
      transform: scale(0.85);
      opacity: 0.4;
    }
    50% {
      transform: scale(1.2);
      opacity: 1;
    }
  }

  /*
    EL CAJÓN SE COLAPSA CON `grid-template-rows`, NO CON `height`.

    `height: 0 → auto` —lo que hace el mockup— no se anima en CSS estándar:
    el navegador salta a `auto`, no interpola hacia él. `grid-template-rows`
    con unidades `fr` sí admite transición, y es la técnica real para
    animar algo hasta su alto de contenido. `overflow: hidden` en
    `.cajon-interior` es quien de verdad recorta mientras la fila mide
    `0fr` — sin él el contenido se saldría por fuera del recorte de la
    rejilla.
  */
  .cajon-teclado {
    display: grid;
    grid-template-rows: 0fr;
    transition: grid-template-rows 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .cajon-teclado.abierto { grid-template-rows: 1fr; }

  .cajon-interior {
    overflow: hidden;
    opacity: 0;
    transition: opacity 0.25s ease 0.05s;
  }

  .cajon-teclado.abierto .cajon-interior {
    opacity: 1;
    transition: opacity 0.3s ease 0.1s;
  }

  .cabecera-teclado-movil { display: none; }

  /* ── Móvil y tableta ──────────────────────────────────────────────────
     `05` §10: aquí el teclado de notación es la vía principal de escribir
     matemática, así que lo que se recorta es el área de prosa —de tres
     renglones a dos— y no él. Mismo corte que `TecladoDeNotacion.svelte`
     a propósito: el teclado sigue en rejilla plana en las dos bandas
     estrechas —`D-31`—, y este redactor va con él. `75rem` ==
     `--corte-escritorio`; `@media` no admite `var()`, el literal se
     repite a propósito. */

  @media (max-width: 75rem) {
    .redactor { gap: 0.45rem; }
    .campo-mixto { min-block-size: 4.5rem; max-block-size: 9rem; }
    .con-teclado .campo-mixto { min-block-size: 1.8rem; max-block-size: 4rem; }

    .cabecera-teclado-movil {
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-block-size: 42px;
      padding: 0.15rem 0.5rem;
      border: 1px solid var(--trazo-suave);
      border-block-end: 0;
      border-radius: var(--radius-sm) var(--radius-sm) 0 0;
      background: var(--surface-panel);
      color: var(--ink-secondary);
      font-size: var(--texto-xs);
      font-weight: 600;
    }

    .cabecera-teclado-movil button {
      min-block-size: 38px;
      padding-inline: 0.7rem;
      border: 1px solid var(--trazo);
      border-radius: var(--radius-xs);
      background: var(--surface-paper);
      color: var(--ink-primary);
      font: inherit;
      cursor: pointer;
    }
  }

  @media (max-height: 38rem) and (pointer: coarse) {
    .caja-de-entrada { flex-direction: row; align-items: center; padding: 4px 8px; }
    .campo { min-inline-size: 0; }
    .acciones { flex: none; margin: 0; padding: 0; }
    .campo-mixto, .con-teclado .campo-mixto { min-block-size: 1.8rem; max-block-size: 3rem; }
    .cabecera-teclado-movil { display: none; }
  }
</style>
