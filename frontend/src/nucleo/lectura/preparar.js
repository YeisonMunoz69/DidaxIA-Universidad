/** Precálculo del corpus en pausas pequeñas; no monta DOM oculto ni usa HTML del servidor. */
import { renderizar } from '../formato/notacion.js';
import { registrarLimpiezaDeLectura } from './cache.js';
let generacion = 0;
registrarLimpiezaDeLectura(() => {
    generacion++;
    globalThis.performance?.clearMarks?.('didaxia:corpus-preparado');
});
function expresionesDe(nodo, salida) {
    if (!nodo || typeof nodo !== 'object')
        return;
    if (Array.isArray(nodo)) {
        for (const parte of nodo)
            expresionesDe(parte, salida);
        return;
    }
    if (nodo.tipo === 'matematica') {
        salida.push({ expresion: nodo.latex ?? nodo.texto, bloque: Boolean(nodo.latex) });
    }
    for (const valor of Object.values(nodo)) {
        if (Array.isArray(valor))
            for (const parte of valor)
                expresionesDe(parte, salida);
    }
}
export async function prepararTextoDelCorpus(datos) {
    const vigente = generacion, expresiones = [];
    expresionesDe(datos?.contenido, expresiones);
    let i = 0;
    while (i < expresiones.length && vigente === generacion) {
        await new Promise(resolve => {
            const trabajar = () => {
                const inicio = performance.now();
                while (i < expresiones.length && vigente === generacion && performance.now() - inicio < 4) {
                    const { expresion, bloque } = expresiones[i++];
                    renderizar(expresion, { bloque });
                }
                resolve();
            };
            if (globalThis.requestIdleCallback)
                requestIdleCallback(trabajar, { timeout: 100 });
            else
                setTimeout(trabajar, 0);
        });
    }
    // Señal local de rendimiento. No se transmite ni conserva fuera de la RAM.
    if (vigente === generacion && datos?.parte?.identificador) {
        globalThis.performance?.mark?.('didaxia:corpus-preparado', { detail: datos.parte.identificador });
    }
}
