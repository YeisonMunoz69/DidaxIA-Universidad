export function marcasDeEscala(minimo, maximo, pixeles) {
  const amplitud = maximo - minimo;
  if (!Number.isFinite(amplitud) || amplitud <= 0 || pixeles <= 0) return [];
  const objetivo = amplitud / Math.max(2, Math.floor(pixeles / 75));
  const potencia = 10 ** Math.floor(Math.log10(objetivo));
  const paso = [1, 2, 5, 10].map((base) => base * potencia).find((valor) => valor >= objetivo) ?? 10 * potencia;
  const primero = Math.ceil((minimo - 1e-10 * paso) / paso);
  const ultimo = Math.floor((maximo + 1e-10 * paso) / paso);
  if (ultimo - primero > 30) return [];
  return Array.from({ length: Math.max(0, ultimo - primero + 1) }, (_, indice) => {
    const valor = (primero + indice) * paso;
    return { valor, texto: String(Number(valor.toPrecision(8))), porcentaje: ((valor - minimo) / amplitud) * 100 };
  });
}

export function reticulaDeEscala(caja, ancho, alto) {
  const [izquierda, arriba, derecha, abajo] = caja;
  const x = marcasDeEscala(izquierda, derecha, ancho);
  const y = marcasDeEscala(abajo, arriba, alto);
  const menores = (marcas, minimo, maximo) => {
    if (marcas.length < 2) return [];
    const paso = marcas[1].valor - marcas[0].valor;
    const primera = Math.ceil(minimo / (paso / 5));
    const ultima = Math.floor(maximo / (paso / 5));
    if (ultima - primera > 180) return [];
    return Array.from({ length: ultima - primera + 1 }, (_, indice) => {
      const orden = primera + indice;
      return orden % 5 === 0 ? null : ((orden * paso / 5 - minimo) / (maximo - minimo)) * 100;
    }).filter((valor) => valor !== null && valor >= 0 && valor <= 100);
  };
  const limitar = (valor, minimo, maximo) => Math.max(minimo, Math.min(maximo, valor));
  const ejeX = limitar(((arriba - 0) / (arriba - abajo)) * alto, 18, alto - 18);
  const ejeY = limitar(((0 - izquierda) / (derecha - izquierda)) * ancho, 27, ancho - 20);
  return {
    x, y, ancho, alto,
    menoresX: menores(x, izquierda, derecha),
    menoresY: menores(y, abajo, arriba),
    ejeX, ejeY,
    rotuloXDebajo: ejeX < alto - 25,
    rotuloYIzquierda: ejeY > 36
  };
}
