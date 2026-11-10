/** Papel flexible inspirado en HojaDeformable del mockup libro-3d-interactivo.
 * Una malla y una textura de la zona visible, sin copias del árbol del capítulo.
 * WebGL nativo evita otra dependencia. El DOM original sigue siendo accesible.
 */
const COLUMNAS = 64, FILAS = 16;
const motores = new WeakMap();
const texturas = new WeakMap();
const SELECTOR_DE_PAPEL = '.texto-del-corpus > *, .cabecera-detalle, .seccion-bloque, .franja-prerrequisitos, .formulas-concepto, .naturaleza, .pasaje-citado, .continuar-capitulo';

/** Sin leer geometría de capítulos ocultos ni comparar cada bloque con todos
 * los demás. Una raíz ya contiene sus descendientes (p. ej. el pasaje citado).
 */
export function raicesVisibles(fuente, caja) {
  const candidatos = [...fuente.querySelectorAll(SELECTOR_DE_PAPEL)];
  const raices = candidatos.length ? candidatos : [...fuente.children];
  return raices.filter(n => {
    if (n.closest('[hidden]') || n.parentElement?.closest(SELECTOR_DE_PAPEL)) return false;
    // Leer un descendiente de content-visibility:auto puede despertar su
    // diseño. El navegador sabe qué bloques siguen fuera de pantalla.
    if (n.checkVisibility && !n.checkVisibility({ contentVisibilityAuto: true })) return false;
    const r = n.getBoundingClientRect();
    return r.width && r.height && r.bottom > caja.top && r.top < caja.bottom && r.right > caja.left && r.left < caja.right;
  });
}

/** Intersección del papel con los paneles desplazables de la transcripción.
 * Se memoriza por captura: KaTeX puede tener cientos de descendientes que
 * comparten el mismo recorte de una cita, tabla o fórmula horizontal.
 */
export function recorteDeLectura(nodo, caja, memoria = new WeakMap()) {
  if (!nodo || nodo === document.documentElement) return caja;
  if (memoria.has(nodo)) return memoria.get(nodo);
  const padre = recorteDeLectura(nodo.parentElement, caja, memoria);
  const estilo = getComputedStyle(nodo);
  const corta = valor => /^(auto|scroll|hidden|clip)$/.test(valor);
  const x = corta(estilo.overflowX || estilo.overflow), y = corta(estilo.overflowY || estilo.overflow);
  let limite = padre;
  if (x || y) {
    const r = nodo.getBoundingClientRect();
    const izquierda = r.left + nodo.clientLeft, arriba = r.top + nodo.clientTop;
    limite = {
      left: x ? Math.max(padre.left, izquierda) : padre.left,
      right: x ? Math.min(padre.right, izquierda + nodo.clientWidth) : padre.right,
      top: y ? Math.max(padre.top, arriba) : padre.top,
      bottom: y ? Math.min(padre.bottom, arriba + nodo.clientHeight) : padre.bottom
    };
  }
  memoria.set(nodo, limite);
  return limite;
}

export function geometriaDePapel(ancho, alto, progreso, sentido = 'siguiente', salida = new Float32Array((COLUMNAS + 1) * (FILAS + 1) * 8)) {
  const signo = sentido === 'anterior' ? -1 : 1;
  const p = Math.max(0, Math.min(1, progreso)), ola = Math.sin(Math.PI * p);
  for (let j = 0; j <= FILAS; j++) {
    const v = j / FILAS;
    const pliegue = ancho * (1 - p + ((v - .5) * .14 + Math.sin(v * Math.PI * 2) * .025) * ola);
    const radio = Math.max(.0001, ancho * .15 * ola * (1 + (v - .5) * .28));
    for (let i = 0; i <= COLUMNAS; i++) {
      const u = i / COLUMNAS, distancia = Math.max(0, u * ancho - pliegue);
      const angulo = Math.min(Math.PI, distancia / radio);
      const x = distancia > 0 ? pliegue + radio * Math.sin(angulo) - Math.max(0, distancia - Math.PI * radio) : u * ancho;
      const z = radio * (1 - Math.cos(angulo));
      const k = (j * (COLUMNAS + 1) + i) * 8;
      salida[k] = signo * x;
      salida[k + 1] = v * alto;
      salida[k + 2] = z + 1;
      salida[k + 3] = signo > 0 ? u : 1 - u;
      salida[k + 4] = v;
      salida[k + 5] = -signo * Math.sin(angulo); salida[k + 6] = 0; salida[k + 7] = Math.cos(angulo);
    }
  }
  return salida;
}

/** Pinta sólo lo que está visible, con los glifos y fuentes ya cargados.
 * No serializa HTML ni carga imágenes/font externos dentro de la textura.
 */
function* pintarTextura(pagina, caja, escala) {
  const canvas = document.createElement('canvas');
  canvas.width = Math.ceil(caja.width * escala); canvas.height = Math.ceil(caja.height * escala);
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Sin lienzo de papel');
  ctx.scale(escala, escala);
  ctx.fillStyle = getComputedStyle(pagina).backgroundColor;
  ctx.fillRect(0, 0, caja.width, caja.height);
  const fuente = pagina.querySelector('.contenido-pagina');
  if (!fuente) return canvas;
  const visible = r => r.width && r.height && r.bottom > caja.top && r.top < caja.bottom && r.right > caja.left && r.left < caja.right;
  const raices = raicesVisibles(fuente, caja);
  const recortes = new WeakMap();
  const enRecorte = (r, c) => c.right > c.left && c.bottom > c.top && r.bottom > c.top && r.top < c.bottom && r.right > c.left && r.left < c.right;
  function recortar(c) {
    ctx.beginPath(); ctx.rect(c.left - caja.left, c.top - caja.top, c.right - c.left, c.bottom - c.top); ctx.clip();
  }
  // No recorrer los miles de nodos de fórmulas de un capítulo fuera de pantalla.
  for (const raiz of raices) for (const nodo of [raiz, ...raiz.querySelectorAll('*')]) {
    if (nodo.closest('.katex-mathml,svg,[hidden]')) continue;
    const r = nodo.getBoundingClientRect();
    if (!visible(r)) continue;
    // El fondo y el borde del panel pertenecen a su caja exterior; sólo sus
    // descendientes quedan recortados por el área interna desplazable.
    const limite = recorteDeLectura(nodo.parentElement, caja, recortes);
    if (!enRecorte(r, limite)) continue;
    const estilo = getComputedStyle(nodo);
    if (estilo.visibility === 'hidden' || estilo.display === 'none') continue;
    ctx.save(); recortar(limite);
    const x = r.left - caja.left, y = r.top - caja.top;
    if (estilo.backgroundColor !== 'rgba(0, 0, 0, 0)' && estilo.backgroundColor !== 'transparent') {
      ctx.fillStyle = estilo.backgroundColor;
      ctx.beginPath(); ctx.roundRect(x, y, r.width, r.height, Math.min(parseFloat(estilo.borderRadius) || 0, r.width / 2, r.height / 2)); ctx.fill();
    }
    // Incluye las barras de fracciones, raíces y recuadros de KaTeX.
    for (const lado of ['Top', 'Bottom', 'Left', 'Right']) {
      const grosor = parseFloat(estilo[`border${lado}Width`]);
      if (!grosor || estilo[`border${lado}Style`] === 'none') continue;
      ctx.fillStyle = estilo[`border${lado}Color`];
      if (lado === 'Top' || lado === 'Bottom') ctx.fillRect(x, lado === 'Top' ? y : y + r.height - grosor, r.width, grosor);
      else ctx.fillRect(lado === 'Left' ? x : x + r.width - grosor, y, grosor, r.height);
    }
    ctx.restore(); yield;
  }
  const rango = document.createRange();
  for (const raiz of raices) {
    const walker = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);
    let texto;
    while ((texto = walker.nextNode())) {
      const padre = texto.parentElement;
      if (!texto.textContent.trim() || padre.closest('.katex-mathml,svg,script,style,[hidden],.solo-lectores')) continue;
      const r = padre.getBoundingClientRect();
      if (!visible(r)) continue;
      const limite = recorteDeLectura(padre, caja, recortes);
      if (!enRecorte(r, limite)) continue;
      const estilo = getComputedStyle(padre);
      if (estilo.visibility === 'hidden' || estilo.display === 'none' || parseFloat(estilo.opacity) === 0) continue;
      ctx.save(); recortar(limite);
      ctx.font = `${estilo.fontStyle} ${estilo.fontWeight} ${estilo.fontSize} ${estilo.fontFamily}`;
      ctx.fillStyle = estilo.color;
      const metricas = ctx.measureText('Mg');
      const ascenso = metricas.fontBoundingBoxAscent ?? parseFloat(estilo.fontSize) * .8;
      const descenso = metricas.fontBoundingBoxDescent ?? parseFloat(estilo.fontSize) * .2;
      // Un rango por palabra y una pintura por línea, en lugar de miles de
      // lecturas de diseño y fillText por carácter al pulsar una página.
      ctx.letterSpacing = estilo.letterSpacing === 'normal' ? '0px' : estilo.letterSpacing;
      let linea;
      const pintar = () => { if (linea) ctx.fillText(linea.texto, linea.x, linea.base); };
      for (const palabra of texto.textContent.matchAll(/\S+\s*/g)) {
        rango.setStart(texto, palabra.index); rango.setEnd(texto, palabra.index + palabra[0].length);
        const rectangulos = [...rango.getClientRects()];
        // Una palabra excepcionalmente larga puede partirse en varias líneas.
        const fragmentos = rectangulos.length > 1 ? [...palabra[0]].map((caracter, i) => {
          rango.setStart(texto, palabra.index + i); rango.setEnd(texto, palabra.index + i + 1);
          return { texto: caracter, r: rango.getBoundingClientRect() };
        }) : [{ texto: palabra[0].replace(/\s+/g, ' '), r: rectangulos[0] }];
        for (const fragmento of fragmentos) {
          const glifo = fragmento.r;
          if (!glifo || !visible(glifo) || !enRecorte(glifo, limite)) continue;
          const base = glifo.top - caja.top + (glifo.height - ascenso - descenso) / 2 + ascenso;
          if (linea && Math.abs(linea.base - base) < .5) linea.texto += fragmento.texto;
          else { pintar(); linea = { texto: fragmento.texto, x: glifo.left - caja.left, base }; }
          yield;
        }
      }
      pintar();
      ctx.restore();
    }
  }
  return canvas;
}

function firma(pagina, caja) {
  return [caja.left, caja.top, caja.width, caja.height, pagina.querySelector('.contenido-pagina')?.scrollTop || 0, globalThis.devicePixelRatio || 1].join(':');
}
function texturaVisible(pagina, caja, escala) {
  const previa = texturas.get(pagina);
  if (previa?.firma === firma(pagina, caja)) return previa.canvas;
  const pintura = pintarTextura(pagina, caja, escala);
  let paso; do { paso = pintura.next(); } while (!paso.done);
  return paso.value;
}

/** Prepara únicamente las páginas visibles con un presupuesto de 4 ms de reposo.
 * Cualquier cambio de contenido, desplazamiento, tamaño o tema invalida la
 * captura. No hay almacenamiento persistente ni lecturas del capítulo oculto.
 */
export function vigilarPapel(mesa, permitido = () => true) {
  if (!mesa || !globalThis.requestIdleCallback) return () => {};
  let version = 0, espera, pendiente, destruido = false;
  const paginas = () => [...mesa.querySelectorAll('.pagina')];
  function cancelar() { clearTimeout(espera); cancelIdleCallback(pendiente); }
  function invalidar() {
    version++; cancelar();
    paginas().forEach(p => texturas.delete(p));
    espera = setTimeout(preparar, 180);
  }
  function preparar() {
    if (destruido || !permitido()) return;
    if (mesa.querySelector('.onda-papel')) { espera = setTimeout(preparar, 180); return; }
    const actual = version;
    let motor = motores.get(mesa);
    try { if (!motor || motor.gl.isContextLost()) motor = crearMotor(mesa); } catch { return; }
    if (!motor) return;
    const visibles = paginas().filter(p => { const r = p.getBoundingClientRect(); return r.width && r.height && r.bottom > 0 && r.top < innerHeight; });
    let pintura, pagina, caja;
    function paso(plazo) {
      if (destruido || actual !== version || !permitido()) return;
      if (mesa.querySelector('.onda-papel')) { espera = setTimeout(preparar, 180); return; }
      const inicio = performance.now();
      while (performance.now() - inicio < 4 && plazo.timeRemaining() > 1) {
        if (!pintura) {
          pagina = visibles.shift(); if (!pagina) return;
          caja = pagina.getBoundingClientRect();
          pintura = pintarTextura(pagina, caja, Math.min(globalThis.devicePixelRatio || 1, 1.5));
        }
        let siguiente;
        try { siguiente = pintura.next(); } catch { return; }
        if (siguiente.done) {
          texturas.set(pagina, { firma: firma(pagina, caja), canvas: siguiente.value });
          pintura = null;
        }
      }
      pendiente = requestIdleCallback(paso);
    }
    pendiente = requestIdleCallback(paso);
  }
  const contenido = new MutationObserver(cambios => {
    // Deshabilitar los botones de navegación no cambia la imagen del papel.
    const cambiaPagina = c => {
      const elemento = c.target.nodeType === 1 ? c.target : c.target.parentElement;
      if (elemento?.closest('.onda-papel')) return false;
      if (elemento?.closest('.pagina')) return true;
      return c.type === 'childList' && [...c.addedNodes, ...c.removedNodes].some(n => n.nodeType === 1 && (n.matches('.pagina') || n.querySelector('.pagina')));
    };
    if (cambios.some(cambiaPagina)) invalidar();
    else if (cambios.some(c => c.type === 'childList' && [...c.removedNodes].some(n => n.nodeType === 1 && n.matches('.onda-papel')))) {
      clearTimeout(espera); espera = setTimeout(preparar, 180);
    }
  });
  contenido.observe(mesa, { subtree: true, childList: true, characterData: true, attributes: true });
  const tema = new MutationObserver(invalidar);
  tema.observe(document.documentElement, { attributes: true });
  mesa.addEventListener('scroll', invalidar, true); window.addEventListener('resize', invalidar);
  document.fonts?.ready.then(() => { if (!destruido) invalidar(); });
  invalidar();
  return () => { destruido = true; cancelar(); paginas().forEach(p => texturas.delete(p)); contenido.disconnect(); tema.disconnect(); mesa.removeEventListener('scroll', invalidar, true); window.removeEventListener('resize', invalidar); };
}

const VERTEX = `
attribute vec2 coordenada;
uniform vec2 tamano; uniform float progreso; uniform mediump float anterior;
uniform vec2 origen; uniform vec2 viewport; uniform mediump float sombra;
varying mediump vec2 tex; varying mediump vec3 luz;
void main(){
  float ola=sin(3.14159265*progreso);
  float pliegue=tamano.x*(1.0-progreso+((coordenada.y-0.5)*0.14+sin(coordenada.y*6.2831853)*0.025)*ola);
  float radio=max(0.0001,tamano.x*0.15*ola*(1.0+(coordenada.y-0.5)*0.28));
  float distancia=max(0.0,coordenada.x*tamano.x-pliegue);
  float angulo=min(3.14159265,distancia/radio);
  float x=distancia>0.0 ? pliegue+radio*sin(angulo)-max(0.0,distancia-3.14159265*radio) : coordenada.x*tamano.x;
  float signo=anterior>0.5 ? -1.0 : 1.0;
  vec3 p=vec3(signo*x,coordenada.y*tamano.y,radio*(1.0-cos(angulo))+1.0);p.xy+=origen;
  if(sombra>0.5){p.xy+=vec2(12.0,18.0);p.z=0.0;}
  float perspectiva=1800.0/(1800.0-p.z);
  vec2 pantalla=(p.xy-viewport*0.5)*perspectiva+viewport*0.5;
  gl_Position=vec4(pantalla.x/viewport.x*2.0-1.0,1.0-pantalla.y/viewport.y*2.0,-p.z/1800.0,1.0);
  tex=vec2(anterior>0.5 ? 1.0-coordenada.x : coordenada.x,coordenada.y);
  luz=vec3(-signo*sin(angulo),0.0,cos(angulo));
}`;
const FRAGMENT = `
precision mediump float;
uniform sampler2D papel; uniform vec3 reverso; uniform float anterior; uniform float sombra; uniform float fuerza;
varying vec2 tex; varying vec3 luz;
void main(){
  if(sombra>0.5){gl_FragColor=vec4(0.05,0.04,0.03,fuerza*0.16);return;}
  bool frente=anterior>0.5 ? !gl_FrontFacing : gl_FrontFacing;
  vec3 color=frente ? texture2D(papel,tex).rgb : reverso;
  float relieve=0.72+0.28*abs(normalize(luz).z);
  relieve+=0.06*normalize(luz).x;
  gl_FragColor=vec4(color*relieve,1.0);
}`;

function crearMotor(mesa) {
  const canvas = document.createElement('canvas');
  canvas.className = 'hoja-en-giro'; canvas.dataset.motor = 'malla';
  const gl = canvas.getContext('webgl', { alpha: true, antialias: false, depth: true, premultipliedAlpha: true });
  if (!gl) return null;
  const programa = gl.createProgram();
  for (const [tipo, fuente] of [[gl.VERTEX_SHADER, VERTEX], [gl.FRAGMENT_SHADER, FRAGMENT]]) {
    const shader = gl.createShader(tipo); gl.shaderSource(shader, fuente); gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) { gl.deleteShader(shader); gl.deleteProgram(programa); return null; }
    gl.attachShader(programa, shader); gl.deleteShader(shader);
  }
  gl.linkProgram(programa);
  if (!gl.getProgramParameter(programa, gl.LINK_STATUS)) { gl.deleteProgram(programa); return null; }
  gl.useProgram(programa);
  const vertices = gl.createBuffer(), indices = gl.createBuffer(), textura = gl.createTexture();
  const caras = [];
  for (let j = 0; j < FILAS; j++) for (let i = 0; i < COLUMNAS; i++) {
    const a = j * (COLUMNAS + 1) + i, b = a + COLUMNAS + 1;
    caras.push(a, b, a + 1, a + 1, b, b + 1);
  }
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indices); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(caras), gl.STATIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER, vertices);
  const coordenadas = new Float32Array((COLUMNAS + 1) * (FILAS + 1) * 2);
  for (let j = 0; j <= FILAS; j++) for (let i = 0; i <= COLUMNAS; i++) {
    const k = (j * (COLUMNAS + 1) + i) * 2; coordenadas[k] = i / COLUMNAS; coordenadas[k + 1] = j / FILAS;
  }
  gl.bufferData(gl.ARRAY_BUFFER, coordenadas, gl.STATIC_DRAW);
  const atributo = gl.getAttribLocation(programa, 'coordenada');
  gl.enableVertexAttribArray(atributo); gl.vertexAttribPointer(atributo, 2, gl.FLOAT, false, 8, 0);
  gl.bindTexture(gl.TEXTURE_2D, textura);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  gl.depthFunc(gl.LEQUAL);
  const uniformes = Object.fromEntries(['origen', 'viewport', 'reverso', 'anterior', 'sombra', 'fuerza', 'tamano', 'progreso'].map(n => [n, gl.getUniformLocation(programa, n)]));
  const motor = { canvas, gl, uniformes, cantidad: caras.length };
  motores.set(mesa, motor);
  return motor;
}

export function prepararMalla(pagina, capa, sentido, caja, mesaCaja) {
  const mesa = pagina.closest('.mesa');
  const motor = motores.get(mesa) || crearMotor(mesa);
  if (!motor || motor.gl.isContextLost()) return null;
  const { gl, canvas, uniformes } = motor;
  const limite = gl.getParameter(gl.MAX_TEXTURE_SIZE) / Math.max(mesaCaja.width, mesaCaja.height);
  const escala = Math.min(globalThis.devicePixelRatio || 1, 1.25, limite);
  const textura = texturaVisible(pagina, caja, Math.min(globalThis.devicePixelRatio || 1, 1.5, limite));
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, textura);
  texturas.delete(pagina);
  textura.width = textura.height = 1;
  canvas.width = Math.ceil(mesaCaja.width * escala); canvas.height = Math.ceil(mesaCaja.height * escala);
  gl.viewport(0, 0, canvas.width, canvas.height);
  // El lienzo ocupa la mesa completa, aunque su contenedor mida una página.
  // La regla global de imágenes/canvas (max-inline-size:100%) lo comprimía
  // sólo en horizontal y convertía el giro en una franja de texto estrecha.
  Object.assign(canvas.style, { position: 'absolute', left: `${mesaCaja.left - caja.left}px`, top: `${mesaCaja.top - caja.top}px`, width: `${mesaCaja.width}px`, height: `${mesaCaja.height}px`, maxInlineSize: 'none' });
  const color = getComputedStyle(pagina).backgroundColor.match(/[\d.]+/g)?.slice(0, 3).map(Number) || [255, 248, 236];
  gl.uniform3fv(uniformes.reverso, color.map(c => c / 255));
  gl.uniform2f(uniformes.viewport, mesaCaja.width, mesaCaja.height);
  gl.uniform2f(uniformes.origen, (sentido === 'anterior' ? caja.right : caja.left) - mesaCaja.left, caja.top - mesaCaja.top);
  gl.uniform1f(uniformes.anterior, sentido === 'anterior' ? 1 : 0);
  gl.uniform2f(uniformes.tamano, caja.width, caja.height);
  capa.appendChild(canvas);
  let actual = 0;
  // Geometría sólo bajo demanda para diagnóstico; la animación la calcula GPU.
  Object.defineProperty(canvas, 'formaDePapel', { configurable: true, get: () => ({ progreso: actual, puntos: geometriaDePapel(caja.width, caja.height, actual, sentido), columnas: COLUMNAS, filas: FILAS }) });
  return {
    hoja: canvas,
    dibujar(progreso) {
      actual = progreso;
      gl.uniform1f(uniformes.progreso, progreso);
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.uniform1f(uniformes.fuerza, Math.sin(Math.PI * progreso));
      gl.disable(gl.DEPTH_TEST);
      gl.uniform1f(uniformes.sombra, 1); gl.drawElements(gl.TRIANGLES, motor.cantidad, gl.UNSIGNED_SHORT, 0);
      gl.enable(gl.DEPTH_TEST);
      gl.uniform1f(uniformes.sombra, 0); gl.drawElements(gl.TRIANGLES, motor.cantidad, gl.UNSIGNED_SHORT, 0);
    },
    liberar() {
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([0, 0, 0, 0]));
      delete canvas.formaDePapel; canvas.remove();
    }
  };
}
