<script>
  import { onMount } from 'svelte';
  import { ARCHIVO_DISPONIBLE } from '../../nucleo/descargas/archivo.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import Dialogo from '../base/Dialogo.svelte';
  import Accion from '../recursos/AccionRecurso.svelte';

  let archivo = $state(null);
  let direccion = $state('');
  let puedeCompartir = $state(false);
  let mensaje = $state('');
  let opcionesAbiertas = $state(false);
  let propietario;
  function cerrar() {
    if (direccion) URL.revokeObjectURL(direccion);
    direccion = '';
    archivo = null;
    mensaje = '';
    opcionesAbiertas = false;
  }
  $effect(() => {
    const actual = sesion.conversacion;
    if (!sesion.autenticada || (propietario && actual !== propietario)) cerrar();
    propietario = actual;
  });
  onMount(() => {
    const recibir = (evento) => {
      const {blob,nombre,compartirRequerido} = evento.detail ?? {};
      if (!['application/pdf','image/png','image/jpeg'].includes(blob?.type)) return;
      cerrar();
      archivo = new File([blob],nombre,{type:blob.type});
      direccion = URL.createObjectURL(blob);
      try { puedeCompartir = Boolean(navigator.share && navigator.canShare?.({files:[archivo]})); }
      catch { puedeCompartir = false; }
      opcionesAbiertas = Boolean(compartirRequerido);
    };
    window.addEventListener(ARCHIVO_DISPONIBLE,recibir);
    return () => { window.removeEventListener(ARCHIVO_DISPONIBLE,recibir); cerrar(); };
  });
  async function compartir() {
    try {
      await navigator.share({files:[archivo],title:'Archivo de DidaxIa'});
      mensaje = 'Archivo compartido.';
    } catch (error) {
      if (error.name !== 'AbortError') mensaje = 'No se pudo compartir. Puedes abrir el archivo y guardarlo desde el visor.';
    }
  }
</script>

{#if archivo}
  {#if !opcionesAbiertas}<aside class="archivo-preparado" aria-label="Archivo preparado">
    <Accion icono="descargar" aria-expanded="false" onclick={() => (opcionesAbiertas = true)}>Archivo listo · Abrir/guardar</Accion>
    <Accion icono="cerrar" onclick={cerrar} aria-label="Cerrar archivo preparado" />
  </aside>{/if}
  <Dialogo bind:abierto={opcionesAbiertas} titulo="Archivo preparado" tipo="descarga">
    <p class="nombre-archivo">{archivo.name}</p>
    <p>Guarda el archivo desde el menú de compartir o descárgalo directamente.</p>
    <nav aria-label="Guardar el archivo">
      <Accion icono="descargar" href={direccion} download={archivo.name} class="primario">{archivo.type === 'application/pdf' ? 'Guardar PDF' : 'Guardar imagen'}</Accion>
      <Accion icono="visible" href={direccion} target="_blank" rel="noopener noreferrer">{archivo.type === 'application/pdf' ? 'Abrir PDF' : 'Abrir imagen'}</Accion>
      {#if puedeCompartir}<Accion icono="compartir" onclick={compartir}>Compartir / guardar</Accion>{/if}
    </nav>
    {#if mensaje}<p role="status">{mensaje}</p>{/if}
    <div class="cierre-archivo"><Accion icono="check" onclick={cerrar} aria-label="Cerrar archivo preparado">Listo</Accion></div>
  </Dialogo>
{/if}

<style>
  .archivo-preparado { position:fixed;z-index:160;inset:auto max(1rem,env(safe-area-inset-right)) max(1rem,env(safe-area-inset-bottom)) auto;display:flex;align-items:center;max-width:calc(100vw - 2rem);padding:.2rem;background:var(--surface-panel);border:1px solid var(--trazo);border-radius:var(--radius-sm);box-shadow:var(--shadow-soft);box-sizing:border-box; }
  p { color:var(--ink-secondary); }
  .nombre-archivo { overflow-wrap:anywhere;font-weight:600;color:var(--ink-primary); }
  nav { display: flex; flex-wrap: wrap; gap: .5rem; }
  .cierre-archivo { display:flex;justify-content:flex-end;margin-top:1rem; }
</style>
