export const OFERTA_ACADEMICA = Object.freeze({
  'Facultad de Ingeniería': Object.freeze([
    'Tecnología en Desarrollo de Software',
    'Ingeniería Informática',
    'Ingeniería Multimedia'
  ]),
  'Facultad de Arte y Diseño': Object.freeze([
    'Tecnología en Delineante de Arquitectura e Ingeniería',
    'Arquitectura',
    'Diseño Visual'
  ]),
  'Facultad de Educación': Object.freeze([
    'Licenciatura en Español e Inglés',
    'Licenciatura en Música'
  ]),
  'Facultad de Ciencias Sociales y de la Administración': Object.freeze([
    'Tecnología en Gestión Empresarial',
    'Tecnología en Gestión Comercial y de Mercados',
    'Tecnología en Gestión Financiera',
    'Administración de Empresas',
    'Administración Financiera'
  ])
});

export const FACULTADES_ADMITIDAS = Object.freeze(Object.keys(OFERTA_ACADEMICA));
export const PROGRAMAS_ADMITIDOS = Object.freeze(Object.values(OFERTA_ACADEMICA).flat());

export function facultadAdmitida(valor) {
  return FACULTADES_ADMITIDAS.includes(String(valor ?? '').trim());
}

export function programasDe(facultad) {
  return OFERTA_ACADEMICA[String(facultad ?? '').trim()] ?? [];
}

export function programaAdmitido(valor, facultad = '') {
  const programa = String(valor ?? '').trim();
  return facultad ? programasDe(facultad).includes(programa) : PROGRAMAS_ADMITIDOS.includes(programa);
}
