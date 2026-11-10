const normalizar = texto => String(texto ?? '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
const categorias = [
    ['Integrales', /integral|antideriv/],
    ['Límites', /limit|continuidad/],
    ['Derivadas', /derivad|derivar|tangente|diferencial/],
    ['Álgebra', /algebra|potencia|trigonom|simplific|equivalencia|conjugado|cociente|raiz|misma respuesta|respuestas distintas/],
    ['Funciones', /funcion|composicion|dominio|representacion/]
];
/** El título manda: términos amplios de búsqueda no cambian el tema explícito. */
export function temaDeConcepto(concepto) {
    for (const texto of [concepto.nombre, (concepto.terminos_busqueda ?? []).join(' ')]) {
        const coincidencia = categorias.find(([, patron]) => patron.test(normalizar(texto)));
        if (coincidencia)
            return coincidencia[0];
    }
    return 'Fundamentos';
}
/** Sólo destaca notación que YA figura en el texto docente. */
export function formulasDelConcepto(secciones) {
    const encontradas = new Set();
    for (const seccion of secciones ?? []) {
        for (const m of String(seccion.texto ?? '').matchAll(/\$\$?([^$]+)\$\$?/g)) {
            const latex = m[1].trim();
            if (latex.length > 5 && /[=\\^]/.test(latex))
                encontradas.add(latex);
        }
    }
    return [...encontradas].slice(0, 3);
}
