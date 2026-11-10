
<script>
  import { ayudaContextual } from '../base/ayudaContextual.js';
  let { oscuro = false, alCambiar = () => {} } = $props();

  function cambiar(evento) {
    alCambiar(evento.currentTarget.checked ? 'oscuro' : 'claro', evento);
  }
</script>

<label use:ayudaContextual class="tema" title={oscuro ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}>
  <span class="solo-lectura-asistida">{oscuro ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}</span>
  <input type="checkbox" checked={oscuro} onchange={cambiar} />
  <span class="cielo" aria-hidden="true">
    <span class="estrellas">✦ · ✧</span>
    <span class="nubes"><i></i><i></i><i></i></span>
    <span class="astro"><i></i><i></i><i></i></span>
  </span>
</label>

<style>
  .tema { position: relative; display: inline-grid; flex: 0 0 auto; cursor: pointer; -webkit-tap-highlight-color: transparent; }
  input { position: absolute; z-index: 5; inset: 0; inline-size: 100%; block-size: 100%; margin: 0; opacity: 0; cursor: pointer; }
  .cielo {
    position: relative;
    display: block;
    inline-size: 50px;
    block-size: 27px;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--theme-day-border) 65%, var(--trazo));
    border-radius: 999px;
    background: linear-gradient(145deg, var(--theme-day-start), var(--theme-day-end));
    box-shadow: inset 0 1px 2px var(--theme-day-shine), var(--shadow-soft);
    transition: background .38s ease, border-color .38s ease, box-shadow .38s ease;
  }
  input:focus-visible + .cielo { outline: 3px solid var(--accent-focus, var(--accent-main)); outline-offset: 3px; }
  .astro {
    position: absolute;
    z-index: 3;
    inset: 3px auto auto 3px;
    inline-size: 19px;
    block-size: 19px;
    border-radius: 50%;
    background: var(--theme-sun);
    box-shadow: inset 1px 1px 1px var(--theme-sun-shine), 0 1px 4px var(--theme-sun-shadow);
    transition: transform .42s cubic-bezier(.68,-.3,.32,1.28), background .35s ease, box-shadow .35s ease;
  }
  .astro i { position: absolute; border-radius: 50%; background: var(--theme-crater); opacity: 0; transition: opacity .2s ease .08s; }
  .astro i:nth-child(1) { inline-size: 5px; block-size: 5px; inset: 4px auto auto 4px; }
  .astro i:nth-child(2) { inline-size: 3px; block-size: 3px; inset: 10px auto auto 10px; }
  .astro i:nth-child(3) { inline-size: 2px; block-size: 2px; inset: 5px auto auto 12px; }
  .estrellas { position: absolute; inset: 4px auto auto 6px; color: var(--theme-star); background: var(--theme-night-start); border-radius: 999px; font: 700 9px/1 serif; letter-spacing: 1px; opacity: 0; transform: translateX(-3px); transition: opacity .25s ease, transform .35s ease; }
  .nubes { position: absolute; inset: auto 3px 3px auto; inline-size: 25px; block-size: 11px; transition: transform .4s ease, opacity .25s ease; }
  .nubes i { position: absolute; inset-block-end: 0; border-radius: 50%; background: var(--theme-cloud); }
  .nubes i:nth-child(1) { inline-size: 18px; block-size: 7px; inset-inline-end: 0; }
  .nubes i:nth-child(2) { inline-size: 10px; block-size: 10px; inset-inline-end: 4px; }
  .nubes i:nth-child(3) { inline-size: 8px; block-size: 8px; inset-inline-end: 14px; }
  input:checked + .cielo { border-color: var(--theme-night-border); background: linear-gradient(145deg, var(--theme-night-start), var(--theme-night-end)); box-shadow: inset 0 1px 2px var(--theme-night-shine), var(--shadow-soft); }
  input:checked + .cielo .astro { transform: translateX(23px) rotate(25deg); background: var(--theme-moon); box-shadow: inset 2px -1px 2px var(--theme-moon-depth), 0 1px 5px var(--theme-night-shadow); }
  input:checked + .cielo .astro i { opacity: 1; }
  input:checked + .cielo .estrellas { opacity: .9; transform: translateX(0); }
  input:checked + .cielo .nubes { opacity: 0; transform: translate(8px, 7px); }
  @media (prefers-reduced-motion: reduce) {
    .cielo, .astro, .astro i, .estrellas, .nubes { transition: none; }
  }
</style>
