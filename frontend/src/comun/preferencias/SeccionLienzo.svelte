<script>
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import AlternarFondo from './AlternarFondo.svelte';
</script>

<div class="lienzo">
  <AlternarFondo />
  <section class="transparencia" aria-labelledby="titulo-transparencia">
    <div class="cabecera">
      <div>
        <h3 id="titulo-transparencia">Transparencia de los mensajes</h3>
        <p>Calibra la lectura sobre el fondo antes de guardar.</p>
      </div>
    </div>
    <div class="contenido">
      <div class="controles">
        <label>
          <span class="rotulo"><strong>Tus preguntas</strong><output>{preferencias.opacidadPregunta}%</output></span>
          <input type="range" min="0" max="100" step="1" value={preferencias.opacidadPregunta}
            aria-label="Opacidad de tus preguntas"
            oninput={(evento) => preferencias.elegirOpacidadPregunta(evento.currentTarget.value)} />
          <span class="extremos"><span>Transparente</span><span>Sólido</span></span>
        </label>
        <label>
          <span class="rotulo"><strong>Respuestas del tutor</strong><output>{preferencias.opacidadRespuesta}%</output></span>
          <input type="range" min="0" max="100" step="1" value={preferencias.opacidadRespuesta}
            aria-label="Opacidad de las respuestas"
            oninput={(evento) => preferencias.elegirOpacidadRespuesta(evento.currentTarget.value)} />
          <span class="extremos"><span>Transparente</span><span>Sólido</span></span>
        </label>
      </div>
      <div class="vista" aria-label="Previsualización del chat"
        style={`--muestra-pregunta: ${preferencias.opacidadPregunta}%; --muestra-respuesta: ${preferencias.opacidadRespuesta}%; --muestra-ambiente: ${(preferencias.fondoDuranteConversacion ? preferencias.intensidadFondoConversacion : 100) / 100};`}>
        <span class="vista-titulo">Vista previa</span>
        <div class="burbuja pregunta"><small>Estudiante</small><span>¿Cómo se aproxima f(x) al límite?</span></div>
        <div class="burbuja respuesta"><small>Tutor</small><span>Observa la curva cerca del punto.</span></div>
      </div>
    </div>
  </section>
</div>

<style>
  .lienzo { display:grid; gap:1.25rem; min-inline-size:0; }
  .transparencia { display:grid; gap:1rem; padding:1rem; min-inline-size:0; border:1px solid var(--trazo-suave); border-radius:var(--radius-md); background:var(--surface-panel); }
  h3 { margin:0; color:var(--ink-primary); font-size:var(--texto-md); }
  p { margin:.25rem 0 0; color:var(--ink-tertiary); font-size:var(--texto-xs); line-height:1.45; }
  .contenido { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:1.25rem; min-inline-size:0; }
  .controles { display:grid; align-content:center; gap:1.25rem; min-inline-size:0; }
  .controles label { display:grid; gap:.5rem; min-inline-size:0; }
  .rotulo, .extremos { display:flex; align-items:center; justify-content:space-between; gap:.5rem; }
  .rotulo { color:var(--ink-secondary); font-size:var(--texto-sm); }
  output { padding:.15rem .45rem; border-radius:var(--radius-pill); background:var(--accent-surface); color:var(--accent-main); font-size:var(--texto-xs); font-variant-numeric:tabular-nums; }
  input { inline-size:100%; accent-color:var(--accent-main); cursor:pointer; }
  .extremos { color:var(--ink-tertiary); font-size:var(--texto-xs); }
  .vista { position:relative; display:grid; align-content:center; gap:.6rem; min-block-size:11rem; padding:.75rem; overflow:hidden; border:1px solid var(--trazo-suave); border-radius:var(--radius-md); background-color:var(--surface-paper); background-image:linear-gradient(to right,var(--trazo-suave) 1px,transparent 1px),linear-gradient(to bottom,var(--trazo-suave) 1px,transparent 1px); background-size:1.35rem 1.35rem; }
  .vista::before { position:absolute; inset:0; content:''; background:var(--surface-paper); opacity:calc(1 - var(--muestra-ambiente)); pointer-events:none; }
  .vista > * { position:relative; }
  .vista-titulo { color:var(--ink-secondary); font-size:var(--texto-xs); font-weight:700; }
  .burbuja { display:grid; gap:.2rem; max-inline-size:88%; padding:.5rem .65rem; border:1px solid var(--trazo-suave); border-radius:var(--radius-md); color:var(--ink-primary); font-size:var(--texto-xs); line-height:1.4; }
  .burbuja small { color:var(--ink-secondary); font-size:var(--texto-xs); font-weight:700; }
  .pregunta { justify-self:end; background:color-mix(in srgb,var(--surface-paper) var(--muestra-pregunta),transparent); }
  .respuesta { justify-self:start; background:color-mix(in srgb,var(--surface-paper) var(--muestra-respuesta),transparent); }
  @media (max-width:48rem) { .contenido { grid-template-columns:1fr; } .vista { min-block-size:10rem; } }
</style>
