/**
 * Catálogo de fragmentos que el teclado matemático puede insertar.
 *
 * `muestra` conserva por ahora la representación compacta histórica de la
 * tecla. `inserta` es el LaTeX sin delimitadores: el componente visual añade
 * `$...$` al emitirlo. La fase de renderizado matemático podrá cambiar cómo
 * se presenta una tecla sin tocar este contrato de inserción.
 *
 * @typedef {{ muestra: string, vista?: string, inserta?: string, comando?: string | [string, string], nombre: string }} TeclaDeNotacion
 * @typedef {{ id: string, nombre: string, teclas: TeclaDeNotacion[] }} CategoriaDeNotacion
 */

/** @type {TeclaDeNotacion[]} */
export const TECLAS_RAPIDAS = [
  { muestra: '⁄', inserta: '\\frac{\\placeholder{}}{\\placeholder{}}', nombre: 'fracción' },
  { muestra: '□ⁿ', inserta: '\\placeholder{}^{\\placeholder{}}', nombre: 'potencia con casillas' },
  { muestra: 'x²', inserta: 'x^{2}', nombre: 'x al cuadrado' },
  { muestra: '√□', inserta: '\\sqrt{\\placeholder{}}', nombre: 'raíz cuadrada' },
  { muestra: 'lím', inserta: '\\lim_{x \\to 0}', nombre: 'límite' },
  { muestra: 'd/dx', inserta: '\\frac{d}{dx}', nombre: 'derivada de Leibniz' },
  { muestra: "f′", inserta: "f'(x)", nombre: 'derivada de f' },
  { muestra: 'sen', inserta: '\\operatorname{sen}(\\placeholder{})', nombre: 'seno' },
  { muestra: 'cos', inserta: '\\cos(\\placeholder{})', nombre: 'coseno' },
  { muestra: 'ln', inserta: '\\ln(\\placeholder{})', nombre: 'logaritmo natural' },
  { muestra: 'eˣ', inserta: 'e^{x}', nombre: 'exponencial' },
  { muestra: 'π', inserta: '\\pi', nombre: 'pi' }
];

// Estas acciones no dependen de la pestaña: siempre ocupan la primera fila y
// la columna derecha, tanto en el chat como en la graficadora.
export const TECLAS_NAVEGACION = [
  { muestra: '↑', comando: 'moveUp', nombre: 'mover cursor arriba' },
  { muestra: '↓', comando: 'moveDown', nombre: 'mover cursor abajo' },
  { muestra: '←', comando: 'moveToPreviousChar', nombre: 'mover cursor a la izquierda' },
  { muestra: '→', comando: 'moveToNextChar', nombre: 'mover cursor a la derecha' }
];

export const TECLAS_ACCION = [
  { muestra: '⌫', comando: 'deleteBackward', nombre: 'borrar carácter anterior' },
  { muestra: '+', inserta: '+', nombre: 'más' },
  { muestra: '−', inserta: '-', nombre: 'menos' },
  { muestra: '×', inserta: '\\times', nombre: 'multiplicación' },
  // MathLive toma el argumento/selección a la izquierda como numerador y deja
  // una casilla de denominador, como su tecla nativa de división numérica.
  { muestra: '⁄', comando: ['insert', '\\frac{#@}{#?}'], nombre: 'dividir con fracción' }
];

/** @type {CategoriaDeNotacion[]} */
export const CATEGORIAS_DE_NOTACION = [
  {
    id: 'numeros', nombre: '123',
    teclas: [
      { muestra: '7', inserta: '7', nombre: 'siete' },
      { muestra: '8', inserta: '8', nombre: 'ocho' },
      { muestra: '9', inserta: '9', nombre: 'nueve' },
      { muestra: '÷', inserta: '\\div', nombre: 'división' },
      { muestra: '⌫', comando: 'deleteBackward', nombre: 'borrar carácter anterior' },
      { muestra: '4', inserta: '4', nombre: 'cuatro' },
      { muestra: '5', inserta: '5', nombre: 'cinco' },
      { muestra: '6', inserta: '6', nombre: 'seis' },
      { muestra: '×', inserta: '\\times', nombre: 'multiplicación' },
      { muestra: '←', comando: 'moveToPreviousChar', nombre: 'mover cursor a la izquierda' },
      { muestra: '1', inserta: '1', nombre: 'uno' },
      { muestra: '2', inserta: '2', nombre: 'dos' },
      { muestra: '3', inserta: '3', nombre: 'tres' },
      { muestra: '−', inserta: '-', nombre: 'menos' },
      { muestra: '→', comando: 'moveToNextChar', nombre: 'mover cursor a la derecha' },
      { muestra: '0', inserta: '0', nombre: 'cero' },
      { muestra: '.', inserta: '.', nombre: 'separador decimal' },
      { muestra: '(', inserta: '(', nombre: 'abrir paréntesis' },
      { muestra: ')', inserta: ')', nombre: 'cerrar paréntesis' },
      { muestra: '+', inserta: '+', nombre: 'más' },
      { muestra: 'x', inserta: 'x', nombre: 'variable x' },
      { muestra: 'j', inserta: 'j', nombre: 'variable j' },
      { muestra: 'a', inserta: 'a', nombre: 'variable a' },
      { muestra: 'x□', vista: 'x^{\\square}', inserta: '^{\\placeholder{}}', nombre: 'potencia' },
      { muestra: '=', inserta: '=', nombre: 'igual' }
    ]
  },
  {
    id: 'operadores', nombre: 'Operadores y básicos',
    teclas: [
      { muestra: 'x', inserta: 'x', nombre: 'variable x' },
      { muestra: '⁄', inserta: '\\frac{\\placeholder{}}{\\placeholder{}}', nombre: 'fracción con casillas vacías' },
      { muestra: '□ⁿ', inserta: '\\placeholder{}^{\\placeholder{}}', nombre: 'potencia con casillas vacías' },
      { muestra: '^□', inserta: '^{\\placeholder{}}', nombre: 'exponente casilla vacía' },
      { muestra: 'x^□', inserta: 'x^{\\placeholder{}}', nombre: 'x elevado a casilla vacía' },
      { muestra: 'x²', inserta: 'x^{2}', nombre: 'x al cuadrado' },
      { muestra: '√□', inserta: '\\sqrt{\\placeholder{}}', nombre: 'raíz cuadrada con casilla vacía' },
      { muestra: 'ⁿ√□', inserta: '\\sqrt[\\placeholder{}]{\\placeholder{}}', nombre: 'raíz con índice' },
      { muestra: '_□', inserta: '_{\\placeholder{}}', nombre: 'subíndice casilla vacía' },
      { muestra: 'x_□', inserta: 'x_{\\placeholder{}}', nombre: 'x con subíndice' },
      { muestra: '(□)', inserta: '\\left(\\placeholder{}\\right)', nombre: 'paréntesis' },
      { muestra: '[□]', inserta: '\\left[\\placeholder{}\\right]', nombre: 'corchetes' },
      { muestra: '|□|', inserta: '\\left|\\placeholder{}\\right|', nombre: 'valor absoluto' },
      { muestra: '+', inserta: '+', nombre: 'más' },
      { muestra: '−', inserta: '-', nombre: 'menos' },
      { muestra: '·', inserta: '\\cdot', nombre: 'multiplicación' },
      { muestra: '/', inserta: '/', nombre: 'división' },
      { muestra: '=', inserta: '=', nombre: 'igual' },
      { muestra: '≠', inserta: '\\neq', nombre: 'distinto de' },
      { muestra: '<', inserta: '<', nombre: 'menor que' },
      { muestra: '>', inserta: '>', nombre: 'mayor que' },
      { muestra: '≤', inserta: '\\leq', nombre: 'menor o igual que' },
      { muestra: '≥', inserta: '\\geq', nombre: 'mayor o igual que' },
      { muestra: '±', inserta: '\\pm', nombre: 'más menos' },
      { muestra: 'π', inserta: '\\pi', nombre: 'pi' },
      { muestra: 'e', inserta: 'e', nombre: 'número e' },
      { muestra: '∞', inserta: '\\infty', nombre: 'infinito' }
    ]
  },
  {
    id: 'derivadas', nombre: 'Derivadas',
    teclas: [
      { muestra: 'd/dx', inserta: '\\frac{d}{dx}\\left(\\placeholder{}\\right)', nombre: 'derivada respecto de x, notación de Leibniz' },
      { muestra: 'dy/dx', inserta: '\\frac{dy}{dx}', nombre: 'derivada de y respecto de x' },
      { muestra: "f′(x)", inserta: "f'(x)", nombre: 'primera derivada de f' },
      { muestra: "f″(x)", inserta: "f''(x)", nombre: 'segunda derivada de f' },
      { muestra: "f′(□)", inserta: "f'(\\placeholder{})", nombre: 'derivada evaluada en casilla' },
      { muestra: 'Dₓ[f]', inserta: 'D_x[\\placeholder{}]', nombre: 'derivada de f, notación de Euler' },
      { muestra: 'Δy/Δx', inserta: '\\frac{\\Delta y}{\\Delta x}', nombre: 'cociente incremental' },
      { muestra: 'h→0', inserta: 'h \\to 0', nombre: 'h tiende a cero' },
      { muestra: '·', inserta: '\\cdot', nombre: 'punto de multiplicación' }
    ]
  },
  {
    id: 'funciones', nombre: 'Funciones y trigonometría',
    teclas: [
      { muestra: '⁄', inserta: '\\frac{\\placeholder{}}{\\placeholder{}}', nombre: 'fracción' },
      { muestra: '√□', inserta: '\\sqrt{\\placeholder{}}', nombre: 'raíz cuadrada' },
      { muestra: 'sen', inserta: '\\operatorname{sen}(\\placeholder{})', nombre: 'seno' },
      { muestra: 'cos', inserta: '\\cos(\\placeholder{})', nombre: 'coseno' },
      { muestra: 'tan', inserta: '\\tan(\\placeholder{})', nombre: 'tangente' },
      { muestra: 'ln', inserta: '\\ln(\\placeholder{})', nombre: 'logaritmo natural' },
      { muestra: 'log', inserta: '\\log(\\placeholder{})', nombre: 'logaritmo' },
      { muestra: 'eˣ', inserta: 'e^{\\placeholder{}}', nombre: 'exponencial' },
      { muestra: 'sec', inserta: '\\sec(\\placeholder{})', nombre: 'secante' },
      { muestra: 'csc', inserta: '\\csc(\\placeholder{})', nombre: 'cosecante' },
      { muestra: 'cot', inserta: '\\cot(\\placeholder{})', nombre: 'cotangente' },
      { muestra: '|x|', inserta: '\\left|\\placeholder{}\\right|', nombre: 'valor absoluto' },
      { muestra: 'arcsen', inserta: '\\operatorname{arcsen}(\\placeholder{})', nombre: 'arcoseno' },
      { muestra: 'arccos', inserta: '\\arccos(\\placeholder{})', nombre: 'arcocoseno' },
      { muestra: 'arctan', inserta: '\\arctan(\\placeholder{})', nombre: 'arcotangente' }
    ]
  },
  {
    id: 'limites', nombre: 'Límites',
    teclas: [
      { muestra: 'límₐ', inserta: '\\lim_{x \\to a} \\placeholder{}', nombre: 'límite cuando x tiende a a' },
      { muestra: 'lím₀', inserta: '\\lim_{x \\to 0} \\placeholder{}', nombre: 'límite cuando x tiende a cero' },
      { muestra: 'lím∞', inserta: '\\lim_{x \\to \\infty} \\placeholder{}', nombre: 'límite cuando x tiende a infinito' },
      { muestra: 'lím⁺', inserta: '\\lim_{x \\to a^+} \\placeholder{}', nombre: 'límite lateral por la derecha' },
      { muestra: 'lím⁻', inserta: '\\lim_{x \\to a^-} \\placeholder{}', nombre: 'límite lateral por la izquierda' },
      { muestra: '→', inserta: '\\to', nombre: 'tiende a' },
      { muestra: '∞', inserta: '\\infty', nombre: 'infinito' },
      { muestra: '0/0', inserta: '\\frac{0}{0}', nombre: 'cero sobre cero' },
      { muestra: '∞/∞', inserta: '\\frac{\\infty}{\\infty}', nombre: 'infinito sobre infinito' },
      { muestra: 'Δx', inserta: '\\Delta x', nombre: 'incremento de x' },
      { muestra: 'ε', inserta: '\\varepsilon', nombre: 'épsilon' },
      { muestra: 'δ', inserta: '\\delta', nombre: 'delta' }
    ]
  }
];
