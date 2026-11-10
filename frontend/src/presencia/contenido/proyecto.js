
export const MARCA = 'DidaxIa';

export const DESCRIPCION = 'Tutor de apoyo para el estudio del cálculo diferencial.';

export const AUTORES = Object.freeze([
  'Yeison Javier Muñoz Gómez',
  'Fabián Armando Hoyos Cerón'
]);

export const AUTORES_CON_LINKEDIN = Object.freeze([
  Object.freeze({
    nombre: 'Yeison Javier Muñoz Gómez',
    linkedin: 'https://www.linkedin.com/in/yeison-munozz-pro/',
    github: 'https://github.com/YeisonMunoz69',
    cvlac: 'https://scienti.minciencias.gov.co/cvlac/visualizador/generarCurriculoCv.do?cod_rh=0002366780',
    orcid: 'https://orcid.org/0009-0007-5178-0667',
    correo: 'yjmunoz@unimayor.edu.co'
  }),
  Object.freeze({
    nombre: 'Juan José Caiza Narvaez',
    cargo: 'Profesor',
    linkedin: '', github: '',
    cvlac: 'https://scienti.minciencias.gov.co/cvlac/visualizador/generarCurriculoCv.do?cod_rh=0001752766',
    orcid: 'https://orcid.org/0000-0002-8582-5946',
    correo: 'juanjosecaiza@unimayor.edu.co'
  }),
  Object.freeze({
    nombre: 'Fabián Armando Hoyos Cerón',
    linkedin: 'https://www.linkedin.com/in/fabian-hoyos',
    github: 'https://github.com/fdk06',
    cvlac: 'https://scienti.minciencias.gov.co/cvlac/visualizador/generarCurriculoCv.do?cod_rh=0002366783',
    orcid: 'https://orcid.org/0009-0007-3338-787X',
    correo: 'fahoyos@unimayor.edu.co'
  })
]);

export const MATERIALES_ESTUDIO = 'https://github.com/YeisonMunoz69/didaxia-research-artifacts/tree/v0.1.0';

export const INSTITUCION = 'Institución Universitaria Colegio Mayor del Cauca';

export const PROPOSITO = Object.freeze([
  'DidaxIa es un trabajo de grado que nace de una revisión sistemática de literatura sobre tutores inteligentes y tuvo una evaluación formativa voluntaria con estudiantes universitarios de cálculo diferencial.',
  'Su objetivo es acompañar el estudio: sostener una conversación sobre un ejercicio, nombrar la regla que interviene y mostrar de dónde sale lo que afirma. La evaluación describe uso y percepción; no demuestra un efecto causal sobre el aprendizaje.'
]);

export const LIMITES = Object.freeze([
  'No sustituye al docente. Lo que se acuerde en clase manda sobre lo que diga el tutor.',
  'No garantiza que toda respuesta sea correcta. Es un sistema y puede equivocarse, incluso cuando se explica con seguridad.',
  'Conviene verificar cualquier resultado que vaya a una entrega, a un parcial o a una decisión académica.',
  'No evalúa, no califica y no decide nada sobre la situación académica de nadie.'
]);

export const ACCESO = Object.freeze([
  'Se entra únicamente con la cuenta institucional de correo. No hay acceso anónimo ni registro con una cuenta personal.',
  'El nombre y el correo los aporta el proveedor de identidad de la Institución; el tutor no los pide ni los edita.',
  'Antes de usar el tutor se confirman algunos datos del perfil y se decide sobre el tratamiento de la información.'
]);

export const ESTADO_DEL_PILOTO =
  'La evaluación formativa universitaria se realizó entre el 16 de septiembre y el 9 de ' +
  'octubre de 2026, con participación voluntaria. Sus resultados describen uso, satisfacción ' +
  'y autopercepción, y no establecen un efecto causal sobre el aprendizaje.';

export const RELACION_INSTITUCIONAL =
  `DidaxIa se desarrolla como trabajo de grado en la ${INSTITUCION} y su evaluación formativa ` +
  'se realizó con participación universitaria voluntaria. Las solicitudes institucionales ' +
  'del prototipo fueron firmadas físicamente el 27 de agosto de 2026; esa fecha es distinta ' +
  'del periodo de evaluación.';

export const ICONO_PALETA_PINCEL_SVG = `
  <g id="paleta">
    <path d="M 270 148 C 170 142 65 210 65 330 C 65 460 160 550 280 550 C 380 550 435 480 395 440 C 355 400 330 365 330 330 C 330 295 385 240 415 285 C 435 315 445 280 435 240 C 415 165 350 152 270 148 Z" fill="#edf6fc" stroke="#111116" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M 100 440 C 140 515 210 542 280 542 C 365 542 418 485 390 445 C 368 418 340 375 338 345 C 340 365 365 410 385 432 C 405 455 365 528 275 528 C 195 528 125 490 92 415 Z" fill="#cbe3f5" opacity="0.85" />
    <path d="M 95 315 C 95 245 130 190 190 168" fill="none" stroke="#ffffff" stroke-width="8" stroke-linecap="round" />
    <circle cx="100" cy="335" r="4.5" fill="#ffffff" />
    <g transform="translate(235, 205)">
      <ellipse cx="0" cy="0" rx="34" ry="32" fill="#f7ab3b" stroke="#111116" stroke-width="13" />
      <path d="M -16 -12 C -12 -22 5 -24 16 -16" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" />
      <circle cx="16" cy="-10" r="2.5" fill="#ffffff" />
    </g>
    <g transform="translate(155, 240)">
      <circle cx="0" cy="0" r="33" fill="#eb5838" stroke="#111116" stroke-width="13" />
      <path d="M -16 -12 C -12 -22 5 -24 15 -16" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" />
      <circle cx="16" cy="-9" r="2.5" fill="#ffffff" />
    </g>
    <g transform="translate(125, 335)">
      <circle cx="0" cy="0" r="34" fill="#f26eb4" stroke="#111116" stroke-width="13" />
      <path d="M -17 -13 C -13 -23 5 -25 16 -17" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" />
      <circle cx="17" cy="-10" r="2.5" fill="#ffffff" />
    </g>
    <g transform="translate(168, 420)">
      <circle cx="0" cy="0" r="33" fill="#2d72d9" stroke="#111116" stroke-width="13" />
      <path d="M -16 -12 C -12 -22 5 -24 15 -16" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" />
      <circle cx="15" cy="-9" r="2.5" fill="#ffffff" />
    </g>
    <g transform="translate(255, 448)">
      <circle cx="0" cy="0" r="33" fill="#58ba7d" stroke="#111116" stroke-width="13" />
      <path d="M -16 -12 C -12 -22 5 -24 15 -16" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" />
      <circle cx="15" cy="-9" r="2.5" fill="#ffffff" />
    </g>
    <g transform="translate(328, 442)">
      <circle cx="0" cy="0" r="21" fill="#be93dc" stroke="#111116" stroke-width="11" />
      <path d="M -10 -8 C -7 -14 3 -15 10 -10" fill="none" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round" />
    </g>
  </g>
  <g id="pincel">
    <path d="M 314 246 L 368 418 C 386 476 405 528 414 542 C 422 554 416 564 402 558 C 388 552 370 514 346 432 L 294 256 Z" fill="#9e5628" stroke="#111116" stroke-width="13" stroke-linejoin="round" stroke-linecap="round" />
    <path d="M 312 250 L 362 414 C 378 466 396 515 404 535 C 400 538 388 522 370 460 L 322 256 Z" fill="#ba6e37" />
    <path d="M 334 278 L 366 414" stroke="#e29b61" stroke-width="4.5" stroke-linecap="round" />
    <g id="ferula">
      <path d="M 283 176 L 326 195 L 307 242 L 264 223 Z" fill="#2f628b" stroke="#111116" stroke-width="13" stroke-linejoin="round" />
      <path d="M 294 181 L 314 190 L 297 232 L 277 223 Z" fill="#579ec7" />
      <path d="M 273 203 L 316 222" stroke="#111116" stroke-width="9" stroke-linecap="round" />
      <path d="M 276 204 L 313 221" stroke="#7cbde4" stroke-width="3" stroke-linecap="round" />
    </g>
    <g id="cerdas">
      <path d="M 283 175 C 270 156 256 122 268 76 C 272 60 282 58 290 70 C 305 92 322 135 326 194 Z" fill="#7b3f1d" stroke="#111116" stroke-width="13" stroke-linejoin="round" stroke-linecap="round" />
      <path d="M 284 172 C 274 153 268 126 276 86 C 285 104 305 142 316 186 Z" fill="#9b562a" />
      <path d="M 280 162 C 275 140 274 118 280 98" stroke="#5c2c11" stroke-width="2.5" stroke-linecap="round" fill="none" />
      <path d="M 292 168 C 291 146 294 125 299 110" stroke="#5c2c11" stroke-width="2.5" stroke-linecap="round" fill="none" />
      <path d="M 271 100 C 265 85 269 72 274 65 C 280 57 286 64 290 72 C 294 82 291 94 286 102 C 280 108 274 106 271 100 Z" fill="#e23a36" stroke="#111116" stroke-width="4" stroke-linejoin="round" />
      <path d="M 278 61 C 281 57 286 60 288 67 C 285 71 280 69 278 61 Z" fill="#2c72dd" />
    </g>
  </g>
`;
