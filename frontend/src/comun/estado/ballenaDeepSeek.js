import { TRAZO_DEEPSEEK } from './trazoDeepSeek.js';
import { mezclar } from '../../nucleo/preferencias/colores.js';

const SIMBOLOS = ['∫', '∑', "f′(x)", 'lim', 'dx', 'π', '∞', 'λ', '∂', '√x'];
const BANDAS = 64;
export const AZUL_DEEPSEEK = '#4D6BFE';
const RITMO = 1.7;
const COLORES_MAR = [
  ['#082256','#020b1c','rgba(92,225,230,0.25)'],
  ['#0b3280','#03102b','rgba(255,255,255,0.40)'],
  ['rgba(14,75,195,0.86)','#020c24','rgba(92,225,230,0.85)'],
  ['#0c41ac','#010817','#FFFFFF']
];

export function crearOceano(canvas, contenedor) {
  const win = canvas.ownerDocument.defaultView;
  const doc = canvas.ownerDocument;
  if (!win?.Path2D) return null;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  const textura = doc.createElement('canvas');
  textura.width = textura.height = 512;
  const pintura = textura.getContext('2d');
  if (!pintura) return null;
  pintura.scale(512 / 24, 512 / 24);
  const azul = pintura.createLinearGradient(2,2,22,22);
  azul.addColorStop(0,'#6898FF'); azul.addColorStop(.5,AZUL_DEEPSEEK); azul.addColorStop(1,'#1D3DC4');
  pintura.fillStyle=azul; pintura.fill(new win.Path2D(TRAZO_DEEPSEEK));
  let ancho = 0, alto = 0, dpr = 1, t = 0, anterior = 0, raf = 0;
  let modo = 'normal', pausa = false, reducido = false, visible = true, destruido = false;
  let siguienteFuente = 1.6, siguienteRadar = 0.2;
  let fondo, luna, halo, aura, mares, contraste, vineta;
  let siguienteEstela = 0;
  const particulas = [], pulsos = [], estelas = [];
  const estrellas = Array.from({length:60}, (_, i) => ({x:((i * 37 + 11) % 101) / 101, y:((i * 19 + 7) % 47) / 100}));

  function paleta() {
    const estilo = win.getComputedStyle(contenedor);
    const acento = estilo.getPropertyValue('--accent-main').trim() || AZUL_DEEPSEEK;
    const segundo = estilo.getPropertyValue('--decorative-contrast').trim() || '#5CE1E6';
    contraste=mezclar('#dcf5ff',segundo,.45);
    const brillo = estilo.getPropertyValue('--accent-glow').trim() || 'rgba(77,107,254,0.25)';
    const papel = estilo.getPropertyValue('--surface-paper').trim() || '#141923';
    fondo = ctx.createLinearGradient(0, 0, 0, alto);
    fondo.addColorStop(0,mezclar(mezclar('#020713',papel,.025),acento,.08));
    fondo.addColorStop(.6,mezclar('#061638',acento,.18));
    fondo.addColorStop(1,mezclar('#0c2d68',acento,.32));
    luna = mezclar('#f0faff',segundo,.12);
    halo = ctx.createRadialGradient(ancho*.82, alto*.18, 1, ancho*.82, alto*.18, alto*.18);
    halo.addColorStop(0, brillo); halo.addColorStop(1, 'transparent');
    const tamano = medidaBallena();
    aura = ctx.createRadialGradient(0, 0, 1, 0, 0, tamano*.7);
    aura.addColorStop(0, brillo); aura.addColorStop(1, 'transparent');
    mares = [0.48, 0.56, 0.66, 0.81].map((base, i) => {
      const mar = ctx.createLinearGradient(0, alto*base - 20, 0, alto);
      mar.addColorStop(0, COLORES_MAR[i][0]); mar.addColorStop(1, COLORES_MAR[i][1]);
      return mar;
    });
    vineta=ctx.createRadialGradient(ancho*.5,alto*.5,alto*.4,ancho*.5,alto*.5,Math.max(ancho,alto)*.65);
    vineta.addColorStop(0,'transparent');vineta.addColorStop(1,'rgba(2,6,16,0.4)');
  }
  function medidaBallena() { return Math.min(ancho*.42, Math.max(110, Math.min(ancho, alto)*.66), 190); }
  function ola(x, base, amp, ritmo, frecuencia) {
    return alto*base + Math.sin(x*frecuencia+t*ritmo)*amp + Math.cos(x*frecuencia*.55-t*ritmo*.75)*amp*.35;
  }
  function capa(base, amp, ritmo, frecuencia, indice) {
    ctx.globalAlpha = 1;
    ctx.beginPath(); ctx.moveTo(-20, alto);
    let px=-20, py=ola(px,base,amp,ritmo,frecuencia);
    ctx.lineTo(px,py);
    for (let x=0; x<=ancho+20; x+=20) {
      const y=ola(x,base,amp,ritmo,frecuencia);
      ctx.quadraticCurveTo(px,py,(px+x)/2,(py+y)/2);px=x;py=y;
    }
    ctx.lineTo(ancho+20, alto); ctx.closePath(); ctx.fillStyle=mares[indice]; ctx.fill();
    ctx.beginPath(); px=-20;py=ola(px,base,amp,ritmo,frecuencia);ctx.moveTo(px,py);
    for (let x=0; x<=ancho+20; x+=20) {
      const y=ola(x,base,amp,ritmo,frecuencia);
      ctx.quadraticCurveTo(px,py,(px+x)/2,(py+y)/2);px=x;py=y;
    }
    ctx.strokeStyle=COLORES_MAR[indice][2]; ctx.lineWidth=2; ctx.stroke();
    if(indice) {
      ctx.fillStyle=COLORES_MAR[indice][2];
      for(let x=0; x<ancho; x+=60) {
        const y=ola(x,base,amp,ritmo,frecuencia);
        if(y<alto*base-amp*.2) {ctx.beginPath();ctx.arc(x,y-1.2,Math.max(.6,1.3+Math.sin(t*4+x)*.7),0,Math.PI*2);ctx.fill();}
      }
    }
  }
  function posicion() {
    const tamano=medidaBallena(), oleaje=Math.sin(t*1.3), nado=Math.sin(t*3.6);
    const x=ancho*.5+Math.cos(t*3.6)*16+Math.sin(t*.45)*ancho*.08;
    return {x, y:ola(x,.56,alto*.07,1.7,.008)-14+oleaje*alto*.09+nado*6,
      tamano, inclinacion:-oleaje*.16+nado*.07};
  }
  function fuente(x, y, cantidad=20) {
    for (let i=0; i<cantidad && particulas.length<96; i++) {
      const angulo=-Math.PI/2+(Math.random()-.5)*.8;
      const velocidad=90+Math.random()*100;
      particulas.push({x:x+(Math.random()-.5)*20,y:y-Math.random()*12,vx:Math.cos(angulo)*velocidad,vy:Math.sin(angulo)*velocidad,
        vida:1.6+Math.random()*.5, simbolo:i%3===0 ? SIMBOLOS[(i/3)%SIMBOLOS.length] : '·', tamano:i%3===0 ? 12+Math.random()*5 : 7});
    }
  }
  function radar(x,y) { if (pulsos.length<6) pulsos.push({x,y,vida:2}); }
  function dibujar(dt=0) {
    if (!ancho || !alto || destruido) return;
    ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.globalAlpha=1; ctx.fillStyle=fondo; ctx.fillRect(0,0,ancho,alto);
    ctx.fillStyle=contraste;
    estrellas.forEach((s,i)=>{ctx.globalAlpha=.25+.3*(1+Math.sin(t*1.8+i)); ctx.beginPath(); ctx.arc(s.x*ancho,s.y*alto,1,0,Math.PI*2); ctx.fill();});
    ctx.globalAlpha=1; ctx.fillStyle=halo; ctx.fillRect(ancho*.64,0,ancho*.36,alto*.38);
    ctx.fillStyle=luna; ctx.beginPath(); ctx.arc(ancho*.82,alto*.18,alto*.055,0,Math.PI*2); ctx.fill();
    capa(.48,alto*.055,1.2,.006,0); capa(.56,alto*.07,1.7,.008,1);
    const p=posicion();
    ctx.save(); ctx.translate(p.x,p.y); ctx.rotate(p.inclinacion);
    ctx.fillStyle=aura; ctx.fillRect(-p.tamano*.7,-p.tamano*.7,p.tamano*1.4,p.tamano*1.4);
    ctx.translate(-p.tamano/2,-p.tamano/2);
    for (let i=0; i<BANDAS; i++) {
      const frac=i/(BANDAS-1), fase=t*3.6-frac*Math.PI*1.5;
      const onda=(Math.sin(fase)+.15*Math.sin(fase*2))*p.tamano*.11*Math.pow(frac,1.85);
      ctx.drawImage(textura,i*8,0,8,512,i*p.tamano/BANDAS,onda,p.tamano/BANDAS+.25,p.tamano);
    }
    ctx.restore();
    if (dt && t>=siguienteFuente && Math.sin(t*1.3)<-.55 && modo!=='offline') {
      fuente(p.x-p.tamano*.12,p.y-p.tamano*.32); siguienteFuente=t+3.8;
    }
    if (dt && modo==='offline' && t>=siguienteRadar) {
      radar(p.x-p.tamano*.12,p.y-p.tamano*.32); siguienteRadar=t+1.9;
    }
    if(dt && t>=siguienteEstela && Math.abs(Math.sin(t*3.6))>.92) {
      if(estelas.length<8) estelas.push({x:p.x+p.tamano*.45,y:p.y+6,vida:1});
      siguienteEstela=t+.2;
    }
    capa(.66,alto*.085,2.2,.01,2);
    for(let i=estelas.length-1;i>=0;i--) {
      const a=estelas[i];a.vida-=dt;
      if(a.vida<=0) {estelas.splice(i,1);continue;}
      ctx.globalAlpha=a.vida*.65;ctx.strokeStyle='#5ce1e6';ctx.lineWidth=1.4;
      ctx.beginPath();ctx.ellipse(a.x,a.y,4+(1-a.vida)*44,2+(1-a.vida)*10,0,0,Math.PI*2);ctx.stroke();
    }
    for (let i=particulas.length-1; i>=0; i--) {
      const a=particulas[i]; a.vida-=dt; a.x+=a.vx*dt; a.y+=a.vy*dt; a.vy+=110*dt;
      if (a.vida<=0) {particulas.splice(i,1); continue;}
      ctx.globalAlpha=Math.min(1,a.vida); ctx.fillStyle=contraste;
      ctx.font=`600 ${a.tamano}px monospace`; ctx.fillText(a.simbolo,a.x,a.y);
    }
    for (let i=pulsos.length-1; i>=0; i--) {
      const a=pulsos[i]; a.vida-=dt;
      if (a.vida<=0) {pulsos.splice(i,1); continue;}
      ctx.globalAlpha=a.vida/2; ctx.strokeStyle=contraste; ctx.lineWidth=2;
      for (const radio of [1,.65,.32]) {ctx.beginPath();ctx.arc(a.x,a.y,(10+(2-a.vida)*65)*radio,-Math.PI*.85,-Math.PI*.15);ctx.stroke();}
    }
    ctx.globalAlpha=1; capa(.78,alto*.07,2.8,.013,3);
    ctx.fillStyle=vineta;ctx.fillRect(0,0,ancho,alto);
  }
  function activo() { return !destruido && !pausa && !reducido && visible && !doc.hidden && ancho>0 && alto>0; }
  function parar() { if (raf) win.cancelAnimationFrame(raf); raf=0; anterior=0; }
  function fotograma(ahora) {
    raf=0;
    if (!activo()) return;
    const dt=anterior ? Math.min((ahora-anterior)/1000,.05) : 0;
    anterior=ahora; t+=dt*RITMO; dibujar(dt*RITMO); raf=win.requestAnimationFrame(fotograma);
  }
  function sincronizar() { parar(); if (activo()) raf=win.requestAnimationFrame(fotograma); }
  function redimensionar() {
    const caja=contenedor.getBoundingClientRect();
    ancho=Math.max(0,caja.width); alto=Math.max(0,caja.height);
    dpr=Math.min(win.devicePixelRatio || 1,2);
    canvas.width=Math.round(ancho*dpr); canvas.height=Math.round(alto*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    paleta(); dibujar(); sincronizar();
  }
  const observadorTamano = new win.ResizeObserver(redimensionar);
  observadorTamano.observe(contenedor);
  const observadorTema = new win.MutationObserver(()=>{paleta();dibujar();});
  for (let nodo=contenedor; nodo; nodo=nodo.parentElement) observadorTema.observe(nodo,{attributes:true,attributeFilter:['class','style','data-theme']});
  const observadorVista = win.IntersectionObserver ? new win.IntersectionObserver(([entrada])=>{visible=entrada.isIntersecting;sincronizar();}) : null;
  observadorVista?.observe(contenedor);
  doc.addEventListener('visibilitychange',sincronizar);
  win.addEventListener('resize',redimensionar);
  redimensionar();
  return {
    configurar(opciones) {
      const cambiado=modo!==opciones.modo;
      modo=opciones.modo; pausa=opciones.pausa; reducido=opciones.reducido;
      if (cambiado) {particulas.length=0;pulsos.length=0;estelas.length=0;siguienteRadar=t+.2;siguienteFuente=t+1;}
      dibujar(); sincronizar();
    },
    salpicar(x, y) {
      if (destruido || !ancho || !alto) return;
      fuente(x??ancho*.5,y??alto*.58,28);
      if (modo==='offline') radar(x??ancho*.5,y??alto*.58);
      dibujar();
    },
    destruir() {
      destruido=true; parar(); observadorTamano.disconnect(); observadorTema.disconnect(); observadorVista?.disconnect();
      doc.removeEventListener('visibilitychange',sincronizar); win.removeEventListener('resize',redimensionar);
      particulas.length=0; pulsos.length=0; estelas.length=0;
      textura.width=textura.height=0;
      canvas.width=canvas.height=0;
    }
  };
}
