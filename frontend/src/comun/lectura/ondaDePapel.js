/** Una hoja flexible con una sola textura; CSS 3D queda como respaldo sin WebGL. */
import { prepararMalla, raicesVisibles } from './mallaDePapel.js';
export const DURACION_HOJA_MS = 2000;
export function prepararHoja(pagina, sentido) {
    const mesa = pagina?.closest('.mesa');
    if (!mesa)
        return { reproducir: fin => fin(), cancelar() { } };
    const caja = pagina.getBoundingClientRect(), origen = mesa.getBoundingClientRect();
    const capa = document.createElement('div');
    capa.className = 'onda-papel';
    capa.setAttribute('aria-hidden', 'true');
    capa.inert = true;
    Object.assign(capa.style, { position: 'absolute', left: `${caja.left - origen.left}px`, top: `${caja.top - origen.top}px`, width: `${caja.width}px`, height: `${caja.height}px`, pointerEvents: 'none', zIndex: '30', perspective: '2200px' });
    let malla;
    try { malla = prepararMalla(pagina, capa, sentido, caja, origen); } catch { malla = null; }
    if (malla) {
        mesa.appendChild(capa);
        let terminada = false, animacion, temporizador, fotograma;
        malla.dibujar(0);
        function cancelar() {
            if (terminada) return;
            terminada = true;
            clearTimeout(temporizador); cancelAnimationFrame(fotograma);
            animacion?.cancel(); malla.liberar(); capa.remove();
        }
        return { cancelar, reproducir(fin) {
            if (terminada) return;
            const inicio = performance.now();
            // La línea de tiempo se puede pausar; la deformación vive en la malla.
            animacion = malla.hoja.animate?.([{ transform: 'translateZ(0)' }, { transform: 'translateZ(0)' }], { duration: DURACION_HOJA_MS, fill: 'forwards' });
            const finalizar = () => { if (!terminada) { cancelar(); fin(); } };
            function pintar(ahora) {
                if (terminada) return;
                const tiempo = animacion ? Number(animacion.currentTime ?? 0) : ahora - inicio;
                const t = Math.min(1, Math.max(0, tiempo / DURACION_HOJA_MS));
                malla.dibujar(.5 - .5 * Math.cos(Math.PI * t));
                if (t >= 1) finalizar();
                else fotograma = requestAnimationFrame(pintar);
            }
            fotograma = requestAnimationFrame(pintar);
            animacion?.finished.then(finalizar, () => {});
            // El respaldo no interrumpe una pausa explícita de la línea de
            // tiempo (inspección de fotogramas); al reanudar vuelve a vigilar.
            const vigilar = () => {
                if (terminada) return;
                if (animacion?.playState === 'paused') temporizador = setTimeout(vigilar, 250);
                else finalizar();
            };
            temporizador = setTimeout(vigilar, DURACION_HOJA_MS + 80);
        } };
    }
    // Respaldo accesible para dispositivos sin aceleración gráfica.
    const hoja = document.createElement('div');
    hoja.className = 'hoja-en-giro';
    Object.assign(hoja.style, { position: 'absolute', inset: '0', transformStyle: 'preserve-3d', transformOrigin: sentido === 'anterior' ? 'right center' : 'left center', willChange: 'transform' });
    const frente = document.createElement('div'), dorso = document.createElement('div');
    frente.className = 'frente-hoja';
    dorso.className = 'dorso-hoja';
    const papel = getComputedStyle(pagina);
    for (const cara of [frente, dorso])
        Object.assign(cara.style, { position: 'absolute', inset: '0', overflow: 'hidden', background: papel.background, borderRadius: papel.borderRadius, backfaceVisibility: 'hidden', boxShadow: 'inset 12px 0 24px -24px var(--ink-primary), 0 12px 32px var(--book-cover-shadow)' });
    dorso.style.transform = 'rotateY(180deg)';
    const fuente = pagina.querySelector('.contenido-pagina');
    if (fuente) {
        const candidatos = raicesVisibles(fuente, caja);
        for (const nodo of candidatos) {
            if (nodo.parentElement?.closest('.seccion-bloque, .pasaje-citado, .franja-prerrequisitos'))
                continue;
            const r = nodo.getBoundingClientRect();
            if (r.bottom < caja.top || r.top > caja.bottom)
                continue;
            const copia = nodo.cloneNode(true);
            copia.removeAttribute('id');
            copia.querySelectorAll('[id]').forEach(n => n.removeAttribute('id'));
            const estilo = getComputedStyle(nodo);
            Object.assign(copia.style, { position: 'absolute', left: `${r.left - caja.left}px`, top: `${r.top - caja.top}px`, width: `${r.width}px`, margin: '0', boxSizing: 'border-box', font: estilo.font, lineHeight: estilo.lineHeight, color: estilo.color });
            frente.appendChild(copia);
        }
    }
    hoja.append(frente, dorso);
    capa.appendChild(hoja);
    mesa.appendChild(capa);
    let terminada = false, animacion, temporizador;
    function cancelar() { if (terminada)
        return; terminada = true; clearTimeout(temporizador); animacion?.cancel(); capa.remove(); }
    return { cancelar, reproducir(fin) {
            if (terminada)
                return;
            const signo = sentido === 'anterior' ? 1 : -1;
            const frames = [
                { transform: 'translate3d(0,0,1px) rotateY(0deg) rotateZ(0deg)' },
                { transform: `translate3d(0,-3px,16px) rotateY(${signo * 32}deg) rotateZ(${signo * .7}deg)`, offset: .25 },
                { transform: `translate3d(0,-6px,28px) rotateY(${signo * 92}deg) rotateZ(${signo * 1.2}deg)`, offset: .52 },
                { transform: `translate3d(0,-2px,12px) rotateY(${signo * 154}deg) rotateZ(${signo * .3}deg)`, offset: .82 },
                { transform: `translate3d(0,0,1px) rotateY(${signo * 180}deg) rotateZ(0deg)` }
            ];
            const finalizar = () => { if (terminada)
                return; cancelar(); fin(); };
            if (hoja.animate) {
                animacion = hoja.animate(frames, { duration: DURACION_HOJA_MS, easing: 'cubic-bezier(.28,.66,.26,1)', fill: 'forwards' });
                animacion.finished.then(finalizar, () => { });
            }
            temporizador = setTimeout(finalizar, DURACION_HOJA_MS);
        } };
}
export function animarOndaDePapel(pagina, sentido, fin) { const hoja = prepararHoja(pagina, sentido); hoja.reproducir(fin); return hoja; }
