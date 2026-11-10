/** Añade la firma visual de DidaxIa a una instantánea SVG exportable. */
export function agregarMarcaDeAgua(svg, ancho, alto, color, documento = document) {
  const marca = documento.createElementNS('http://www.w3.org/2000/svg', 'text');
  marca.textContent = 'DidaxIa';
  marca.setAttribute('x', String(ancho - 18));
  marca.setAttribute('y', String(alto - 16));
  marca.setAttribute('text-anchor', 'end');
  marca.setAttribute('font-family', "Caveat, 'Patrick Hand', 'Ink Free', 'Segoe Script', cursive");
  marca.setAttribute('font-size', String(Math.max(20, Math.min(34, ancho * 0.045))));
  marca.setAttribute('font-weight', '700');
  marca.setAttribute('fill', color || '#b84f00');
  marca.setAttribute('fill-opacity', '0.62');
  marca.setAttribute('aria-hidden', 'true');
  marca.setAttribute('data-marca-agua', 'didaxia');
  svg.appendChild(marca);
  return marca;
}
