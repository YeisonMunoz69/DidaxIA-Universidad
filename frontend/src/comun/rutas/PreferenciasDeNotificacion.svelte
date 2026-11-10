<script>
  import CargadorCubo from '../base/CargadorCubo.svelte';
  import { onMount } from 'svelte';
  import * as api from '../../nucleo/api/preferencias-notificacion.js';
  import { describir } from '../../nucleo/errores/degradacion.js';

  let opciones = $state([]);
  let preferencias = $state({});
  let nota = $state('');
  let cargando = $state(true);
  let guardando = $state('');
  let fallo = $state('');
  let confirmacion = $state('');

  function adoptar(respuesta) {
    opciones = respuesta?.opciones ?? [];
    preferencias = { ...(respuesta?.preferencias ?? {}) };
    nota = respuesta?.nota ?? '';
  }

  async function cargar() {
    cargando = true;
    fallo = '';
    try {
      adoptar(await api.consultar());
    } catch (error) {
      fallo = error?.cuerpo?.detalle || describir(error).explicacion;
    } finally {
      cargando = false;
    }
  }

  async function cambiar(categoria, habilitada) {
    const anterior = Boolean(preferencias[categoria]);
    preferencias = { ...preferencias, [categoria]: habilitada };
    guardando = categoria;
    fallo = '';
    confirmacion = '';
    try {
      adoptar(await api.guardar(categoria, habilitada));
      confirmacion = habilitada
        ? 'Los correos de esta categoría quedaron activados.'
        : 'Los correos de esta categoría quedaron desactivados.';
    } catch (error) {
      preferencias = { ...preferencias, [categoria]: anterior };
      fallo = error?.cuerpo?.detalle || describir(error).explicacion;
    } finally {
      guardando = '';
    }
  }

  onMount(cargar);
</script>

<section class="preferencias-correo" aria-labelledby="titulo-preferencias-correo">
  <div class="encabezado">
    <div>
      <h2 id="titulo-preferencias-correo">Notificaciones por correo</h2>
      <p>Elige qué avisos opcionales quieres recibir fuera de la aplicación.</p>
    </div>
    <span class="estado-general">Por defecto: desactivadas</span>
  </div>

  {#if cargando}
    <CargadorCubo mensaje="Consultando tus preferencias…" />
  {:else if opciones.length}
    <div class="opciones">
      {#each opciones as opcion (opcion.codigo)}
        <label class:activa={preferencias[opcion.codigo]}>
          <span class="texto">
            <strong>{opcion.titulo}</strong>
            <small>{opcion.descripcion}</small>
          </span>
          <span class="interruptor">
            <input
              type="checkbox"
              checked={Boolean(preferencias[opcion.codigo])}
              disabled={guardando === opcion.codigo}
              onchange={(evento) => cambiar(opcion.codigo, evento.currentTarget.checked)} />
            <span aria-hidden="true"></span>
          </span>
        </label>
      {/each}
    </div>
    {#if nota}<p class="nota">{nota}</p>{/if}
  {/if}

  {#if fallo}
    <p class="fallo" role="alert">{fallo} <button type="button" onclick={cargar}>Reintentar</button></p>
  {:else if confirmacion}
    <p class="confirmacion" role="status">{confirmacion}</p>
  {/if}
</section>

<style>
  .preferencias-correo {
    display: grid;
    gap: .85rem;
    padding: 1rem 1.1rem;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    background: var(--surface-panel);
  }
  .encabezado { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
  h2, p { margin: 0; }
  h2 { color: var(--ink-primary); font-size: var(--texto-md); }
  p, small { color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.45; }
  .estado-general { flex: none; padding: .25rem .55rem; border-radius: 999px; background: var(--surface-paper); color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .opciones { display: grid; gap: .55rem; }
  label { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: .8rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); cursor: pointer; }
  label.activa { border-color: var(--accent-main); background: var(--accent-surface); }
  .texto { display: grid; gap: .15rem; }
  strong { color: var(--ink-primary); font-size: var(--texto-sm); }
  small { display: block; }
  .interruptor { position: relative; flex: none; inline-size: 2.75rem; block-size: 1.55rem; }
  .interruptor input { position: absolute; inset: 0; z-index: 1; inline-size: 100%; block-size: 100%; margin: 0; opacity: 0; cursor: pointer; }
  .interruptor span { display: block; inline-size: 100%; block-size: 100%; border: 0; border-radius: 999px; background: var(--trazo); transition: var(--transition); }
  .interruptor span::after { content: ''; position: absolute; inset-block-start: .23rem; inset-inline-start: .23rem; inline-size: 1.05rem; block-size: 1.05rem; border-radius: 50%; background: var(--surface-paper); box-shadow: var(--shadow-soft); transition: var(--transition); }
  .interruptor input:checked + span { background: var(--accent-main); }
  .interruptor input:checked + span::after { transform: translateX(1.17rem); }
  .interruptor input:focus-visible + span { outline: 2px solid var(--accent-main); outline-offset: 3px; }
  .interruptor input:disabled { cursor: wait; }
  .nota { padding-block-start: .15rem; font-size: var(--texto-xs); }
  .fallo, .confirmacion { padding: .6rem .7rem; border-radius: var(--radius-sm); }
  .fallo { color: var(--semantic-danger); background: var(--semantic-danger-bg); }
  .confirmacion { color: var(--semantic-success); background: var(--semantic-success-bg); }
  .fallo button { border: 0; background: none; color: inherit; cursor: pointer; font: inherit; font-weight: 700; text-decoration: underline; }
  @media (max-width: 36rem) {
    .encabezado { flex-direction: column; }
    label { align-items: flex-start; }
  }
</style>
