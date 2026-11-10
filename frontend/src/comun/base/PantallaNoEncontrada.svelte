
<script>
  import { onMount } from 'svelte';

  let { camino = '/', inicio = '/', alInicio = null, alVolver = null } = $props();
  let canal = $state(0);
  let sonido = $state(false);
  let perilla = $state(0);
  let chispas = $state(0);
  let lienzo = $state(null);
  let audio = null;
  let ruido = null;
  let ganancia = null;
  let visible = true;
  let movimientoReducido = false;
  const canales = [
    { nombre: 'Estática analógica', badge: 'NOT FOUND', estado: '404_NO_CONVERGE' },
    { nombre: 'Osciloscopio', badge: 'x ∉ Dom(f)', estado: 'SIN DOMINIO' },
    { nombre: 'Calibración', badge: 'DIDAXIA TV', estado: 'TRANSMISIÓN INTERRUMPIDA' },
    { nombre: 'Radar matemático', badge: 'SIN SEÑAL', estado: 'BUSCANDO RUTA' }
  ];

  function tinta(nombre) {
    return globalThis.getComputedStyle(globalThis.document.documentElement).getPropertyValue(nombre).trim();
  }

  function dibujar(tiempo = 0) {
    const ctx = lienzo?.getContext?.('2d');
    if (!ctx) return;
    const w = lienzo.width, h = lienzo.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = tinta('--crt-screen'); ctx.fillRect(0, 0, w, h);
    if (canal === 0) {
      const pixeles = ctx.createImageData(w, h);
      for (let n = 0; n < pixeles.data.length; n += 4) {
        const valor = 27 + Math.random() * 145;
        pixeles.data[n] = valor; pixeles.data[n + 1] = valor;
        pixeles.data[n + 2] = valor * .91; pixeles.data[n + 3] = 255;
      }
      ctx.putImageData(pixeles, 0, 0);
    } else if (canal === 1) {
      ctx.strokeStyle = tinta('--crt-grid'); ctx.lineWidth = .5;
      for (let x = 0; x < w; x += 16) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
      for (let y = 0; y < h; y += 16) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
      ctx.strokeStyle = tinta('--crt-phosphor'); ctx.lineWidth = 2; ctx.beginPath();
      for (let x = 0; x < w; x++) {
        if (x >= w * .46 && x <= w * .53) continue;
        const y = h / 2 + Math.sin(x / 13 - tiempo / 300) * 20;
        if (x === 0 || x === Math.ceil(w * .53)) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.strokeStyle = tinta('--crt-phosphor'); ctx.beginPath(); ctx.arc(w * .46, h / 2 + Math.sin(w * .46 / 13 - tiempo / 300) * 20, 4, 0, Math.PI * 2); ctx.stroke();
    } else if (canal === 2) {
      for (let n = 0; n < 7; n++) { ctx.fillStyle = tinta(`--crt-calibration-${n + 1}`); ctx.fillRect(n * w / 7, 0, Math.ceil(w / 7), h * .72); }
      ctx.fillStyle = tinta('--crt-calibration-dark'); ctx.fillRect(0, h * .72, w, h * .28);
      for (let n = 0; n < 7; n++) { ctx.fillStyle = tinta(n % 2 ? '--crt-calibration-mid' : '--crt-calibration-light'); ctx.fillRect(n * w / 7, h * .78, w / 7, h * .12); }
    } else {
      const cx = w / 2, cy = h / 2;
      ctx.strokeStyle = tinta('--crt-radar'); ctx.lineWidth = 1;
      for (const radio of [19, 38, 57]) { ctx.beginPath(); ctx.arc(cx, cy, radio, 0, Math.PI * 2); ctx.stroke(); }
      ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, h); ctx.moveTo(0, cy); ctx.lineTo(w, cy); ctx.stroke();
      ctx.fillStyle = tinta('--crt-radar'); ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, 57, -Math.PI / 2 + tiempo / 500, -Math.PI / 2 + tiempo / 500 + .5); ctx.fill();
    }
  }

  function cambiarCanal() {
    canal = (canal + 1) % canales.length;
    perilla += 45;
    chispas += 1;
    dibujar();
    clicAnalogico();
  }

  function clicAnalogico() {
    if (!sonido || !audio) return;
    const osc = audio.createOscillator(), vol = audio.createGain();
    osc.type = 'triangle'; osc.frequency.setValueAtTime(180, audio.currentTime);
    osc.frequency.exponentialRampToValueAtTime(65, audio.currentTime + .07);
    vol.gain.setValueAtTime(.025, audio.currentTime);
    vol.gain.exponentialRampToValueAtTime(.001, audio.currentTime + .08);
    osc.connect(vol).connect(audio.destination); osc.start(); osc.stop(audio.currentTime + .08);
  }

  async function alternarSonido() {
    if (sonido) { sonido = false; ganancia && (ganancia.gain.value = 0); return; }
    const Constructor = globalThis.AudioContext || globalThis.webkitAudioContext;
    if (!Constructor) return;
    try {
      audio ??= new Constructor();
      await audio.resume();
      if (!ruido) {
        const buffer = audio.createBuffer(1, audio.sampleRate, audio.sampleRate);
        const datos = buffer.getChannelData(0);
        for (let n = 0; n < datos.length; n++) datos[n] = (Math.random() * 2 - 1) * .35;
        ruido = audio.createBufferSource(); ruido.buffer = buffer; ruido.loop = true;
        ganancia = audio.createGain(); ganancia.gain.value = 0;
        ruido.connect(ganancia).connect(audio.destination); ruido.start();
      }
      ganancia.gain.value = .025; sonido = true; clicAnalogico();
    } catch { sonido = false; }
  }

  function irInicio() { if (alInicio) alInicio(inicio); else globalThis.location?.assign(inicio); }
  function volver() {
    if (alVolver) { alVolver(); return; }
    try {
      const anterior = globalThis.document?.referrer;
      if (anterior && new URL(anterior).origin === globalThis.location?.origin && globalThis.history?.length > 1) {
        globalThis.history.back(); return;
      }
    } catch {  }
    irInicio();
  }

  onMount(() => {
    globalThis.document?.querySelector('meta[name="description"]')?.setAttribute('content',
      'La dirección solicitada no existe en DidaxIa. Vuelve al inicio o revisa la URL.');
    movimientoReducido = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    dibujar();
    const observador = typeof IntersectionObserver === 'function'
      ? new IntersectionObserver(([entrada]) => { visible = Boolean(entrada?.isIntersecting); }) : null;
    if (observador && lienzo) observador.observe(lienzo);
    const intervalo = globalThis.setInterval?.(() => {
      if (visible && !movimientoReducido) dibujar(performance.now());
    }, 100);
    return () => {
      observador?.disconnect(); globalThis.clearInterval?.(intervalo);
      ruido?.stop(); audio?.close();
    };
  });
</script>

<svelte:head><title>404 · Señal didáctica perdida · DidaxIa</title><meta name="robots" content="noindex, nofollow" /></svelte:head>

<section class="no-encontrada" aria-labelledby="titulo-404">
  <button class="sonido" type="button" aria-label={sonido ? 'Silenciar sonido CRT' : 'Activar sonido CRT'} aria-pressed={sonido} onclick={alternarSonido}>
    {sonido ? '◖)) Sonido CRT' : '◖) Sonido CRT'}
  </button>
  <div class="escenario">
    <span class="cifra" aria-hidden="true">404</span>
    <div class="televisor" aria-label={`Televisor retro. Canal ${canal + 1}: ${canales[canal].nombre}`}>
      {#if chispas}
        {#key chispas}<span class="chispa" aria-hidden="true">✧</span>{/key}
      {/if}
      <div class="cupula" aria-hidden="true"><i class="antena antena-a"></i><i class="antena antena-b"></i></div>
      <div class="carcasa">
        <div class="pantalla" role="img" aria-label={canales[canal].estado}>
          <canvas bind:this={lienzo} width="160" height="105" aria-hidden="true"></canvas>
          <div class="barrido" aria-hidden="true"></div>
          <div class="reflejo" aria-hidden="true"></div>
          <span class="cartel" class:glitch={canal === 0}>{canales[canal].badge}</span>
        </div>
        <div class="controles">
          <button type="button" class="perilla perilla-1" style:--giro={`${perilla}deg`} aria-label="Cambiar de canal con la perilla izquierda" onclick={cambiarCanal}><span></span></button>
          <button type="button" class="perilla perilla-2" style:--giro={`${perilla}deg`} aria-label="Cambiar de canal con la perilla derecha" onclick={cambiarCanal}><span></span></button>
          <div class="parlante" aria-hidden="true"></div>
        </div>
      </div>
      <div class="patas" aria-hidden="true"><i></i><i></i></div>
    </div>
  </div>
  <div class="tarjeta">
    <span class="senal">Canal {canal + 1} / 4 · {canales[canal].estado}</span>
    <h1 id="titulo-404">Esta dirección no existe</h1>
    <p>La señal didáctica se perdió. Comprueba la dirección o vuelve a una página conocida.</p>
    <p class="formula"><span>lim f(x) = ∄</span><small>x → {camino}</small></p>
    <p class="matiz">Esta es una metáfora de una ruta ausente, no el resultado matemático de un ejercicio.</p>
    <div class="acciones">
      <button type="button" class="principal" onclick={irInicio}>Sintonizar inicio</button>
      <button type="button" class="secundario" onclick={volver}>Retornar un paso</button>
    </div>
  </div>
</section>

<style>
  .no-encontrada { position: relative; isolation: isolate; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; inline-size: 100%; min-inline-size: 0; min-block-size: 100%; padding: 1.5rem 1rem 2.5rem; box-sizing: border-box; overflow: hidden; color: var(--ink-primary); }
  .sonido { align-self: flex-end; min-block-size: 44px; padding: .45rem .8rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-pill); background: var(--surface-paper); color: var(--ink-secondary); font: inherit; cursor: pointer; }
  .sonido[aria-pressed='true'] { border-color: var(--accent-main); color: var(--accent-main); }
  .escenario { position: relative; display: grid; place-items: center; inline-size: min(100%, 36rem); min-block-size: clamp(20rem, 35vw, 24rem); }
  .cifra { position: absolute; z-index: 0; inset: 0; display: grid; place-items: start center; font: 900 clamp(10rem, 32vw, 19rem)/1 var(--fuente-mono); letter-spacing: -.1em; color: var(--accent-main); opacity: .11; animation: levitar 5s ease-in-out infinite; }
  .televisor { position: relative; z-index: 1; inline-size: min(20rem, 78vw); margin-block-start: 5rem; transform: rotate(-2deg); filter: drop-shadow(0 1rem 1.2rem color-mix(in srgb, var(--ink-primary) 20%, transparent)); }
  .chispa { position: absolute; z-index: 3; inset-block-start: 1rem; inset-inline-end: .4rem; color: var(--accent-main); font-size: 1.8rem; animation: chispa .4s ease-out both; pointer-events: none; }
  .cupula { position: relative; margin-inline: auto; inline-size: 5rem; block-size: 2.2rem; border: .28rem solid var(--crt-outline); border-radius: 100% 100% 20% 20%; background: var(--accent-main); }
  .antena { position: absolute; inset-block-end: 1.1rem; inline-size: .28rem; block-size: 4rem; border-radius: 1rem; background: var(--ink-primary); transform-origin: bottom center; }
  .antena::after { content: ''; position: absolute; inset-block-start: -.3rem; inset-inline-start: -.16rem; inline-size: .6rem; block-size: .6rem; border-radius: 50%; background: var(--accent-main); }
  .antena-a { inset-inline-start: 1.4rem; transform: rotate(-37deg); animation: antena-a 4s ease-in-out infinite; }
  .antena-b { inset-inline-end: 1.4rem; transform: rotate(37deg); animation: antena-b 4s ease-in-out infinite; }
  .carcasa { position: relative; z-index: 1; display: grid; grid-template-columns: minmax(0, 1fr) 3.5rem; gap: .55rem; align-items: center; padding: .85rem; border: .25rem solid var(--crt-outline); border-radius: 1.6rem; background: var(--accent-main); box-shadow: inset .3rem .3rem color-mix(in srgb, var(--surface-paper) 35%, var(--accent-main)), inset -.35rem -.4rem color-mix(in srgb, var(--crt-outline) 22%, var(--accent-main)); }
  .pantalla { position: relative; display: grid; place-items: center; aspect-ratio: 1.52; min-inline-size: 0; overflow: hidden; border: .45rem solid var(--crt-calibration-light); border-radius: 38% / 13%; background: var(--theme-night-start); box-shadow: inset 0 0 1.2rem var(--crt-outline); }
  canvas { position: absolute; inline-size: 100%; block-size: 100%; image-rendering: pixelated; }
  .barrido { position: absolute; inset: 0; pointer-events: none; background: repeating-linear-gradient(to bottom, transparent 0 3px, color-mix(in srgb, var(--ink-primary) 25%, transparent) 4px 5px); }
  .reflejo { position: absolute; inset: 0; pointer-events: none; border-radius: inherit; background: radial-gradient(ellipse at 25% 10%, color-mix(in srgb, var(--surface-paper) 27%, transparent), transparent 48%); }
  .cartel { position: relative; padding: .25rem .45rem; border: 1px solid var(--theme-star); border-radius: .25rem; background: var(--theme-night-start); color: var(--theme-star); font: 800 clamp(.7rem, 3vw, 1rem)/1.2 var(--fuente-mono); letter-spacing: .08em; text-align: center; }
  .cartel.glitch { animation: glitch 2.4s steps(2, end) infinite; }
  .controles { display: flex; flex-direction: column; align-items: center; gap: .55rem; }
  .perilla { display: grid; place-items: center; inline-size: 2.75rem; block-size: 2.75rem; min-inline-size: 44px; min-block-size: 44px; padding: 0; border: .2rem solid var(--ink-primary); border-radius: 50%; background: var(--accent-surface); cursor: pointer; }
  .perilla span { display: block; inline-size: .22rem; block-size: 1.65rem; border-radius: 1rem; background: var(--ink-primary); transform: rotate(var(--giro)); transition: transform .25s ease; }
  .perilla-2 span { block-size: 1.35rem; }
  .parlante { inline-size: 2.5rem; block-size: 1.8rem; border-radius: .35rem; background: repeating-linear-gradient(to bottom, var(--ink-primary) 0 2px, transparent 2px 5px); }
  .patas { display: flex; justify-content: space-around; margin-inline: 3rem; }
  .patas i { inline-size: 2rem; block-size: 1rem; border: .2rem solid var(--crt-outline); border-radius: 0 0 .3rem .3rem; background: var(--accent-main); }
  .tarjeta { inline-size: min(100%, 34rem); padding: 1.25rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-xl); background: var(--surface-paper); box-shadow: var(--shadow-soft); text-align: center; }
  .senal { display: inline-block; max-inline-size: 100%; padding: .3rem .65rem; border-radius: var(--radius-pill); background: var(--accent-surface); color: var(--accent-main); font: 700 var(--texto-xs) var(--fuente-mono); overflow-wrap: anywhere; }
  h1 { margin: .75rem 0; color: var(--ink-primary); font-size: clamp(1.35rem, 5vw, 2rem); }
  p { margin: .5rem 0; color: var(--ink-secondary); line-height: 1.5; }
  .formula { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: center; gap: .35rem; margin-block: 1rem .25rem; padding: .7rem; border-radius: var(--radius-md); background: var(--surface-canvas); color: var(--ink-primary); font-family: var(--fuente-mono); }
  .formula small { min-inline-size: 0; overflow-wrap: anywhere; }
  .matiz { font-size: var(--texto-xs); }
  .acciones { display: flex; flex-wrap: wrap; justify-content: center; gap: .65rem; margin-block-start: 1.25rem; }
  .acciones button { min-block-size: 44px; padding: .6rem 1rem; border: 1px solid var(--accent-main); border-radius: var(--radius-sm); font-family: inherit; font-size: var(--texto-sm); font-weight: 700; cursor: pointer; box-shadow: .2rem .2rem 0 var(--ink-primary); }
  .principal { background: var(--accent-main); color: var(--surface-paper); }
  .secundario { background: var(--surface-paper); color: var(--accent-main); }
  button:focus-visible { outline: 3px solid var(--accent-main); outline-offset: 3px; }
  @keyframes levitar { 50% { transform: translateY(-.6rem); } }
  @keyframes antena-a { 50% { transform: rotate(-31deg); } }
  @keyframes antena-b { 50% { transform: rotate(31deg); } }
  @keyframes glitch { 8% { transform: translateX(2px); opacity: .7; } 10%, 100% { transform: none; opacity: 1; } }
  @keyframes chispa { from { opacity: 1; transform: scale(.4) rotate(0); } to { opacity: 0; transform: scale(1.5) rotate(45deg); } }
  @media (max-width: 26rem) { .carcasa { grid-template-columns: minmax(0, 1fr) 2.8rem; gap: .3rem; padding: .6rem; } .parlante { inline-size: 2rem; } .tarjeta { padding: 1rem; } }
  @media (prefers-reduced-motion: reduce) { .cifra, .antena, .cartel, .chispa { animation: none; } .chispa { display: none; } .perilla span { transition: none; } }
</style>
