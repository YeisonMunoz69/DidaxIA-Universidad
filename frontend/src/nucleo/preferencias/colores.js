export const PALETAS = [
  ['ambar','Ámbar y cielo','#A84D08','#FBBF24','#147AB6','#38BDF8'],
  ['zafiro','Zafiro real','#1E4F85','#9CC8F6','#C68A3B','#F5CC91'],
  ['electrico','Azul eléctrico','#2453C7','#A8BCFF','#9D3DAA','#ECA7E8'],
  ['esmeralda','Esmeralda andina','#1F6247','#8FD5B3','#B26A30','#E7B288'],
  ['jade','Jade y menta','#17665B','#90D8C8','#7C5089','#D4A5E7'],
  ['amatista','Amatista','#6C3A93','#D3B0EE','#44877D','#92DAD1'],
  ['indigo','Índigo cósmico','#454990','#BDBFFF','#AF667C','#EFA8BD'],
  ['rubi','Rubí carmesí','#9E2947','#F4A9BC','#398C90','#8AD7DB'],
  ['coral','Coral cálido','#A83E37','#F3B1A5','#2F8797','#8ACEDA'],
  ['ocre','Ocre solar','#856015','#E4C884','#5C579E','#BBB5F3'],
  ['terracota','Terracota y cobre','#9C482E','#EDB49D','#548A75','#ACD4BB'],
  ['turquesa','Turquesa glaciar','#166473','#88D4DF','#9C6749','#DFB597'],
  ['orquidea','Orquídea','#953673','#E9AFD7','#499F96','#90D8CA'],
  ['caramelo','Caramelo y bronce','#7B5234','#DDB995','#628D9A','#A6D5DE'],
  ['grafito','Grafito minimalista','#41464C','#C3C8CE','#707985','#8995A4'],
  ['vinotinto','Beige y vinotinto','#701D36','#E7B3C3','#4C8792','#78C9D7','#F7F1E8','#EDE3D5','#F1E9DE'],
  ['salvia','Salvia y concreto','#425C50','#B6CDBB','#A2745C','#E1BDA5','#F4F5F2','#E4E8E1','#EDF0EA'],
  ['lino','Lino tranquilo','#645548','#D2BFA9','#718497','#A9C2DC','#F7F3EE','#E9E1D6','#F0EAE2'],
  ['oliva','Papel oliva','#5E6042','#C6C993','#856286','#CEACD5','#F6F5EE','#E4E2D3','#EEECDD'],
  ['lavanda','Lavanda tenue','#6C5A74','#D7BFE1','#709684','#A9D8BC','#FAF7FB','#EDE5F0','#F3EEF6'],
  ['noche','Noche y aurora','#215565','#95DAE2','#AA4E84','#EF97CF'],
  ['oceano','Océano y arena','#225D89','#8ACDF0','#BA8043','#F1CA92'],
  ['bosque','Bosque y lavanda','#326448','#99D8B5','#8963A4','#D7B4F5'],
  ['ciruela','Ciruela y jade','#753D72','#E0AEDC','#358D82','#90DDD1'],
  ['cobre','Cobre y azul','#884F31','#EAB69B','#377EA9','#87C7F2'],
  ['cereza','Cereza y hielo','#922E4F','#F0ADCA','#348C9A','#8BD9E9']
].map(([id,nombre,acentoClaro,acentoOscuro,contrasteClaro,contrasteOscuro,papel,lienzo,panel]) =>
  ({ id,nombre,acentoClaro,acentoOscuro,contrasteClaro,contrasteOscuro,papel,lienzo,panel }));

export const PARTES_COLOR = [
  {id:'main',nombre:'Principal',uso:'Botones y enlaces',token:'--accent-main'},
  {id:'hover',nombre:'Al pasar el cursor',uso:'Respuesta al señalar',token:'--accent-hover'},
  {id:'light',nombre:'Acento de apoyo',uso:'Detalles y selecciones',token:'--accent-light'},
  {id:'surface',nombre:'Superficie de acento',uso:'Fondos suaves',token:'--accent-surface'},
  {id:'surfaceHover',nombre:'Superficie al señalar',uso:'Fondos activos',token:'--accent-surface-hover'},
  {id:'glow',nombre:'Luz del acento',uso:'Resplandor decorativo',token:'--accent-glow'},
  {id:'gradient',nombre:'Degradado',uso:'Transición de tonos',token:'--accent-gradient'},
  {id:'contraste',nombre:'Segundo halo',uso:'Color que se superpone',token:'--decorative-contrast'}
];
export const COLOR_INICIAL = Object.freeze(configuracionDe('ambar'));
export function configuracionDe(id) {
  const p = PALETAS.find(p => p.id === id) ?? PALETAS[0];
  return Object.fromEntries([['paleta',p.id],...['Claro','Oscuro'].flatMap(modo=>
    PARTES_COLOR.map(parte=>[parte.id+modo,p.id]))]);
}
const HEX = /^#[0-9a-f]{6}$/i;
const admitida = id => PALETAS.some(p=>p.id===id);
function familiaCercana(hex,campo) {
  return PALETAS.reduce((mejor,p)=>{
    const distancia=c=>rgb(c).reduce((s,v,i)=>s+(v-rgb(hex)[i])**2,0);
    return distancia(p[campo])<distancia(mejor[campo]) ? p : mejor;
  }).id;
}
export function normalizarColores(datos) {
  const base = configuracionDe(datos?.paleta);
  for (const modo of ['Claro','Oscuro']) {
    if (HEX.test(datos?.['acento'+modo] ?? '')) {
      const fuente=familiaCercana(datos['acento'+modo],'acento'+modo);
      for (const parte of PARTES_COLOR.filter(p=>p.id!=='contraste')) base[parte.id+modo]=fuente;
    }
    if (HEX.test(datos?.['contraste'+modo] ?? '')) base['contraste'+modo]=familiaCercana(datos['contraste'+modo],'contraste'+modo);
  }
  for (const clave of Object.keys(base)) {
    if (admitida(datos?.[clave])) base[clave]=datos[clave];
  }
  return base;
}
const rgb = h => [1,3,5].map(i => parseInt(h.slice(i,i+2),16));
export function mezclar(a,b,t) {
  return '#' + rgb(a).map((v,i) => Math.round(v*(1-t)+rgb(b)[i]*t).toString(16).padStart(2,'0')).join('').toUpperCase();
}
const luminancia = h => rgb(h).map(v => v/255).map(v => v<=.04045 ? v/12.92 : ((v+.055)/1.055)**2.4)
  .reduce((s,v,i) => s+v*[.2126,.7152,.0722][i],0);
export function contraste(a,b) {
  return (Math.max(luminancia(a),luminancia(b))+.05)/(Math.min(luminancia(a),luminancia(b))+.05);
}
function calibrar(color,fondos,oscuro) {
  const extremo = oscuro ? '#FFFFFF' : '#000000';
  for (let i=0;i<=100;i++) {
    const candidato=mezclar(color,extremo,i/100);
    const hover=mezclar(candidato,extremo,.16);
    const superficies=[...fondos,mezclar(fondos[0],candidato,.12)];
    const tinta=oscuro ? fondos[0] : '#FFFFFF';
    if (superficies.every(f => contraste(candidato,f)>=4.5 && contraste(hover,f)>=4.5)
      && contraste(tinta,candidato)>=4.5 && contraste(tinta,hover)>=4.5) return candidato;
  }
  return extremo;
}
const cachePaletas = new Map();
function tokensDePaleta(id,oscuro) {
  const clave=id+':'+oscuro;
  if (cachePaletas.has(clave)) return cachePaletas.get(clave);
  const p=PALETAS.find(p => p.id===id) ?? PALETAS[0];
  const calida=Boolean(p.papel);
  const papel=oscuro ? (calida ? '#241A21' : '#181D27') : p.papel ?? '#FFFFFF';
  const panel=oscuro ? (calida ? '#1B1218' : '#0F1319') : p.panel ?? '#F5F6F9';
  const lienzo=oscuro ? (calida ? '#130C10' : '#07090E') : p.lienzo ?? '#EDEEF2';
  const solicitado=p[oscuro ? 'acentoOscuro' : 'acentoClaro'];
  const main=calibrar(solicitado,[papel,panel,lienzo],oscuro);
  const hover=mezclar(main,oscuro ? '#FFFFFF' : '#000000',.16);
  const tokens = {
    '--accent-main':main,'--accent-hover':hover,'--accent-light':main,
    '--accent-surface':mezclar(papel,main,.08),'--accent-surface-hover':mezclar(papel,main,.12),
    '--accent-glow':`rgba(${rgb(main).join(',')},0.14)`,
    '--accent-gradient':`linear-gradient(135deg,${main},${hover})`,
    '--accent-on-main':oscuro ? papel : '#FFFFFF',
    '--decorative-contrast':p[oscuro ? 'contrasteOscuro' : 'contrasteClaro'],
    '--decorative-contrast-glow':`rgba(${rgb(p[oscuro ? 'contrasteOscuro' : 'contrasteClaro']).join(',')},0.1)`,
    '--surface-paper':papel,'--surface-panel':panel,'--surface-canvas':lienzo,
    '--surface-elevated':oscuro ? (calida ? '#2D2129' : '#1E2433') : papel,
    '--surface-blur':`rgba(${rgb(papel).join(',')},0.82)`,
    '--ink-primary':oscuro ? '#F1F3F7' : '#0C1222',
    '--ink-secondary':oscuro ? '#A9B5C7' : '#4A5568',
    '--ink-tertiary':oscuro ? '#A4B1C4' : '#514E60',
    '--trazo':oscuro ? '#8A93A3' : '#6E7683',
    '--trazo-suave':oscuro ? '#3E4757' : calida ? '#B7AEA8' : '#B6BECB'
  };
  cachePaletas.set(clave,tokens);
  return tokens;
}
export function tokensDeColor(datos,oscuro) {
  const c=normalizarColores(datos), modo=oscuro ? 'Oscuro' : 'Claro';
  const tokens={...tokensDePaleta(c.paleta,oscuro)};
  for (const parte of PARTES_COLOR) tokens[parte.token]=tokensDePaleta(c[parte.id+modo],oscuro)[parte.token];
  const fondos=['--surface-paper','--surface-panel','--surface-canvas','--accent-surface','--accent-surface-hover'].map(k=>tokens[k]);
  for (const clave of ['--accent-main','--accent-hover','--accent-light']) tokens[clave]=calibrar(tokens[clave],fondos,oscuro);
  tokens['--decorative-contrast-glow']=`rgba(${rgb(tokens['--decorative-contrast']).join(',')},0.1)`;
  return tokens;
}
export function aplicarColores(datos,oscuro,nodo=globalThis.document?.body) {
  if (!nodo) return;
  const c=normalizarColores(datos);
  const tokens=tokensDeColor(c,oscuro);
  const original=JSON.stringify(c)===JSON.stringify(COLOR_INICIAL);
  for (const [clave,valor] of Object.entries(tokens)) {
    if (original && clave!=='--decorative-contrast') nodo.style.removeProperty(clave);
    else nodo.style.setProperty(clave,valor);
  }
  nodo.dataset.paleta=c.paleta;
  if (nodo === globalThis.document?.body) {
    const documento=nodo.ownerDocument;
    const papel=documento.defaultView.getComputedStyle(nodo).getPropertyValue('--surface-paper').trim()
      || tokens['--surface-paper'];
    documento.documentElement.style.backgroundColor=papel;
    documento.documentElement.style.colorScheme=oscuro ? 'dark' : 'light';
    let etiquetas=[...documento.head.querySelectorAll('meta[name="theme-color"]')];
    if (!etiquetas.length) {
      const etiqueta=documento.createElement('meta');
      etiqueta.name='theme-color';
      documento.head.append(etiqueta);
      etiquetas=[etiqueta];
    }
    for (const etiqueta of etiquetas) etiqueta.content=papel;
  }
}
export const CLAVE_COLOR_PUBLICO = 'didaxia.portada.colores.v1';
export function leerColoresPublicos() {
  try { return normalizarColores(JSON.parse(globalThis.localStorage?.getItem(CLAVE_COLOR_PUBLICO) ?? 'null')); }
  catch { return {...COLOR_INICIAL}; }
}
export function guardarColoresPublicos(colores) {
  try { globalThis.localStorage?.setItem(CLAVE_COLOR_PUBLICO,JSON.stringify(normalizarColores(colores))); }
  catch {  }
}
