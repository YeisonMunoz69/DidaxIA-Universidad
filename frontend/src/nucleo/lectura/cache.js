/** RAM de la sesión. Peticiones compartidas, fallos recuperables, sin disco. */
const almacenes = new Map();
const limpiezas = new Set();
export function registrarLimpiezaDeLectura(limpiar) { limpiezas.add(limpiar); }
export function cacheDeLectura(cargar, preparar = null) {
    if (almacenes.has(cargar))
        return almacenes.get(cargar);
    const valores = new Map(), pendientes = new Map();
    const consultados = new Set();
    let generacion = 0;
    const clave = args => JSON.stringify(args);
    const cache = {
        consultados,
        ver: (...args) => valores.get(clave(args)),
        pedir(...args) {
            const id = clave(args), vigente = generacion;
            if (valores.has(id))
                return Promise.resolve(valores.get(id));
            if (pendientes.has(id))
                return pendientes.get(id);
            const p = Promise.resolve().then(() => cargar(...args)).then(async (datos) => {
                if (preparar && vigente === generacion)
                    await preparar(datos);
                if (vigente === generacion) {
                    valores.set(id, datos);
                    pendientes.delete(id);
                }
                return datos;
            }).catch(fallo => {
                if (vigente === generacion) pendientes.delete(id);
                throw fallo;
            });
            pendientes.set(id, p);
            return p;
        },
        precargar(...args) { void cache.pedir(...args).catch(() => { }); },
        limpiar() { generacion++; valores.clear(); pendientes.clear(); consultados.clear(); }
    };
    almacenes.set(cargar, cache);
    return cache;
}
export function limpiarCachesDeLectura() {
    for (const cache of almacenes.values())
        cache.limpiar();
    for (const limpiar of limpiezas)
        limpiar();
}
