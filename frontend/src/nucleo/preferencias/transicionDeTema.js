function movimientoReducido() {
  return typeof window !== 'undefined'
    && Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
}

export function ejecutarTransicionCircularDeTema(evento, nuevoTema, callbackCambio) {
  if (typeof document === 'undefined') return;
  const aplicar = () => {
    document.body.classList.toggle('dark-theme', nuevoTema === 'oscuro');
    document.documentElement.classList.toggle('dark-theme', nuevoTema === 'oscuro');
    callbackCambio?.();
  };

  if (!document.startViewTransition || movimientoReducido()) {
    aplicar();
    return;
  }

  let x = window.innerWidth / 2;
  let y = window.innerHeight / 2;
  const tactil = evento?.touches?.[0] ?? evento?.changedTouches?.[0];
  if (tactil) {
    x = tactil.clientX; y = tactil.clientY;
  } else if (Number.isFinite(evento?.clientX) && Number.isFinite(evento?.clientY)
      && (evento.clientX !== 0 || evento.clientY !== 0)) {
    x = evento.clientX; y = evento.clientY;
  } else {
    const limites = evento?.currentTarget?.getBoundingClientRect?.();
    if (limites) {
      x = limites.left + limites.width / 2;
      y = limites.top + limites.height / 2;
    }
  }

  const radio = Math.hypot(
    Math.max(x, window.innerWidth - x),
    Math.max(y, window.innerHeight - y)
  );
  const transicion = document.startViewTransition(aplicar);
  transicion.ready.then(() => {
    document.documentElement.animate?.(
      { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radio}px at ${x}px ${y}px)`] },
      { duration: 450, easing: 'cubic-bezier(0.2, 0, 0, 1)', pseudoElement: '::view-transition-new(root)' }
    );
  }).catch(() => {});
}
