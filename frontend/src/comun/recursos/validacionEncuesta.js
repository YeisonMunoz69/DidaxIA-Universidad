import { CORREO_INSTITUCIONAL } from '../../nucleo/configuracion/institucion.js';
export function problemaPregunta(p, valor) {
 const vacio=valor===undefined||valor===null||(typeof valor==='string'&&!valor.trim())||(Array.isArray(valor)&&!valor.length);
 if(vacio)return p.obligatoria?'Esta pregunta es obligatoria. Completa tu respuesta para continuar.':'';
 if(p.tipo==='correo'&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(valor).trim()))return `Escribe un correo completo, por ejemplo nombre${CORREO_INSTITUCIONAL}.`;
 if(p.tipo==='numero'&&(!Number.isFinite(Number(valor))||Math.abs(Number(valor))>1e12))return 'Escribe un número válido. Puedes usar un punto para los decimales.';
 if(p.tipo==='fecha'&&(!/^\d{4}-\d{2}-\d{2}$/.test(valor)||Number.isNaN(Date.parse(valor))||new Date(valor+'T12:00:00Z').toISOString().slice(0,10)!==valor))return 'Selecciona una fecha válida en el calendario.';
 if(['unica','desplegable'].includes(p.tipo)&&!p.opciones.includes(valor))return 'Selecciona una de las opciones disponibles.';
 if(p.tipo==='multiple'&&(!Array.isArray(valor)||valor.some(v=>!p.opciones.includes(v))))return 'Selecciona una o varias opciones de esta pregunta.';
 if(p.tipo==='multiple'&&valor.length>1&&valor.some(v=>p.exclusivas?.includes(v)))return 'La opción excluyente debe marcarse sola. Revisa las actividades seleccionadas.';
 if(p.tipo==='escala'&&(!Number.isInteger(Number(valor))||Number(valor)<p.minimo||Number(valor)>p.maximo))return `Selecciona un valor entre ${p.minimo} y ${p.maximo}.`;
 if(['texto','correo','parrafo'].includes(p.tipo)&&String(valor).length>(p.tipo==='parrafo'?10000:1000))return 'Reduce la longitud de tu respuesta.';
 return '';
}
export function contestada(p,valor){return valor!==undefined&&valor!==null&&String(valor).trim()!==''&&(!Array.isArray(valor)||valor.length>0)&&!problemaPregunta(p,valor);}
export function prepararRespuestas(preguntas,respuestas){
 return Object.fromEntries(preguntas.filter(p=>contestada(p,respuestas[p.id])).map(p=>[p.id,['numero','escala'].includes(p.tipo)?Number(respuestas[p.id]):typeof respuestas[p.id]==='string'?respuestas[p.id].trim():respuestas[p.id]]));
}
