<script>
  import { toast } from '../estado/toasts.svelte.js';
  import { menuDesplegable } from '../base/menuDesplegable.js';
  import Boton from '../base/Boton.svelte';
  import Dialogo from '../base/Dialogo.svelte';
  import Icono from '../base/Icono.svelte';
  import * as api from '../../nucleo/api/reportes.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { onMount } from 'svelte';

  let {
    compacto = false,
    etiqueta = 'Reportar un problema',
    etiquetaAria = '',
    presentacion = 'normal',
    categoriaInicial = 'funcional',
    tituloInicial = '',
    contexto = ''
  } = $props();
  let abierto = $state(false);
  let confirmando = $state(false);
  let enviando = $state(false);
  let categoria = $state('funcional');
  let titulo = $state('');
  let descripcion = $state('');
  let pasos = $state('');
  let archivo = $state(null);
  let fallo = $state('');
  let recibo = $state(null);
  let ruta = $state('/');
  let anteriores = $state([]);
  let falloDeConsulta = $state('');
  let preparado = false;

  async function cargarAnteriores() {
    try {
      anteriores = (await api.mios()).reportes ?? [];
      falloDeConsulta = '';
    } catch (error) {
      falloDeConsulta = error?.cuerpo?.detalle || describir(error).explicacion;
    }
  }

  onMount(() => { if (!compacto) cargarAnteriores(); });

  function abrir() {
    if (!preparado) {
      categoria = categoriaInicial;
      titulo = tituloInicial;
      preparado = true;
    }
    ruta = globalThis.location?.pathname || '/';
    fallo = '';
    abierto = true;
  }

  function pasosConContexto() {
    const automatico = String(contexto ?? '').trim();
    const indicados = pasos.trim();
    return [
      automatico ? `Contexto automático (sin contenido de la conversación):\n${automatico}` : '',
      indicados ? `Pasos indicados por la persona:\n${indicados}` : ''
    ].filter(Boolean).join('\n\n');
  }

  function seleccionar(evento) {
    const candidato = evento.currentTarget.files?.[0] ?? null;
    evento.currentTarget.value = '';
    validarCaptura(candidato);
  }

  function validarCaptura(candidato, { pegada = false } = {}) {
    if (!candidato) return false;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(candidato.type)) {
      fallo = 'La captura debe ser PNG, JPEG o WebP.';
      return false;
    }
    if (candidato.size > 5 * 1024 * 1024 || candidato.size === 0) {
      fallo = 'La captura debe pesar entre 1 byte y 5 MB.';
      return false;
    }
    archivo = candidato;
    fallo = '';
    if (pegada) {
      const extension = { 'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp' }[candidato.type];
      archivo = new File(
        [candidato],
        `captura-pegada.${extension}`,
        { type: candidato.type, lastModified: candidato.lastModified || Date.now() }
      );
    }
    return true;
  }

  function pegarCaptura(evento) {
    const imagen = [...(evento.clipboardData?.items ?? [])]
      .find((item) => item.kind === 'file' && item.type.startsWith('image/'));
    if (!imagen) return;
    evento.preventDefault();
    validarCaptura(imagen.getAsFile(), { pegada: true });
  }

  function leerBase64(candidato) {
    return new Promise((resolver, rechazar) => {
      const lector = new FileReader();
      lector.onerror = () => rechazar(new Error('No se pudo leer la captura.'));
      lector.onload = () => resolver(String(lector.result).split(',', 2)[1] ?? '');
      lector.readAsDataURL(candidato);
    });
  }

  function revisar(evento) {
    evento.preventDefault();
    fallo = '';
    if (titulo.trim().length < 5 || descripcion.trim().length < 10) {
      fallo = 'Describe el problema con un título y al menos diez caracteres.';
      return;
    }
    if (pasosConContexto().length > 3000) {
      fallo = 'El contexto y los pasos no pueden superar 3.000 caracteres.';
      return;
    }
    confirmando = true;
  }

  async function enviar() {
    enviando = true;
    fallo = '';
    try {
      const captura = archivo
        ? { tipo: archivo.type, contenido: await leerBase64(archivo) }
        : null;
      const respuesta = await api.crear({
        categoria, titulo: titulo.trim(), descripcion: descripcion.trim(),
        pasos: pasosConContexto(), ruta, captura, confirmado: true
      });
      recibo = respuesta.reporte;
      toast.exito(`Reporte #${recibo.id} registrado. Puedes seguirlo desde soporte.`);
      confirmando = false;
      abierto = false;
      categoria = categoriaInicial;
      titulo = tituloInicial;
      descripcion = '';
      pasos = '';
      archivo = null;
      if (!compacto) await cargarAnteriores();
    } catch (error) {
      fallo = error?.cuerpo?.detalle || describir(error).explicacion;
      confirmando = false;
    } finally {
      enviando = false;
    }
  }
</script>

{#if compacto}
  <button class={`boton-compacto ${presentacion}`} type="button" onclick={abrir}
          aria-label={etiquetaAria || etiqueta}>
    <Icono nombre="evidencias" medida={17} /> {etiqueta}
  </button>
{:else}
  <section class="invitacion" aria-labelledby="titulo-reportar">
    <div>
      <h2 id="titulo-reportar">¿Encontraste un problema?</h2>
      <p>Canal exclusivo de soporte técnico. Puedes adjuntar una captura revisada por ti; un investigador responderá o resolverá la incidencia en un máximo de 15 días calendario.</p>
    </div>
    <Boton variante="secundario" onclick={abrir}>Reportar un problema</Boton>
  </section>
{/if}

{#if !compacto}
  <section class="mis-reportes" aria-label="Seguimiento de mis reportes">
    <div class="titulo-seguimiento"><h2>Mis reportes recientes (hasta 50)</h2><button type="button" onclick={cargarAnteriores}>Actualizar</button></div>
    {#if falloDeConsulta}<p class="fallo" role="alert">{falloDeConsulta}</p>{/if}
    {#each anteriores as anterior (anterior.id)}
      <article><strong>#{anterior.id} · {anterior.titulo}</strong><span>{anterior.estado.replaceAll('_', ' ')}</span>
        {#if anterior.respuesta}<p>Respuesta del equipo: {anterior.respuesta}</p>{/if}
      </article>
    {/each}
  </section>
{/if}
{#if fallo && !abierto}<p class="fallo" role="alert">{fallo}</p>{/if}

{#if abierto}
<Dialogo bind:abierto titulo="Reportar un problema" ancho="min(38rem, 100%)" bloqueado={enviando}>
  <form id="formulario-reporte" onsubmit={revisar} onpaste={pegarCaptura}>
    <p>Este canal se usa únicamente para corregir fallas del software durante los pilotos. Lo atienden personas con rol investigador y recibirás respuesta o solución en un máximo de 15 días calendario.</p>
    <p>La descripción y la captura pueden contener datos personales. Evita nombres, correos o conversaciones ajenas; recorta o tapa lo que no haga falta antes de adjuntar.</p>
    {#if String(contexto ?? '').trim()}
      <aside class="contexto-reporte">
        <strong>Ubicación identificada automáticamente</strong>
        <span>{contexto}</span>
        <small>No se adjunta el texto de la conversación. Puedes completar los pasos si hace falta.</small>
      </aside>
    {/if}
    <label>Categoría
      <select use:menuDesplegable={categoria} bind:value={categoria}>
        <option value="funcional">No funciona como esperaba</option>
        <option value="visual">Se ve mal</option>
        <option value="accesibilidad">No puedo usarlo con mi dispositivo o teclado</option>
        <option value="rendimiento">Lentitud o carga</option>
        <option value="contenido">Contenido o respuesta</option>
        <option value="otro">Otro</option>
      </select>
    </label>
    <label>Título
      <input bind:value={titulo} minlength="5" maxlength="120" required placeholder="No puedo abrir la segunda gráfica" />
    </label>
    <label>¿Qué sucedió?
      <textarea bind:value={descripcion} minlength="10" maxlength="4000" rows="5" required placeholder="Describe lo que observaste y qué esperabas ver."></textarea>
    </label>
    <label>¿Cómo podemos repetirlo? (opcional)
      <textarea bind:value={pasos} maxlength="3000" rows="3" placeholder="1. Abrí… 2. Pulsé…"></textarea>
    </label>
    <label>Captura (opcional; PNG, JPEG o WebP; máximo 5 MB)
      <input type="file" accept=".png,.jpg,.jpeg,.webp" onchange={seleccionar} />
    </label>
    <button class="zona-pegado" type="button" aria-label="Pegar una captura desde el portapapeles">
      <Icono nombre="evidencias-institucionales" medida={22} />
      <span><strong>También puedes pegar una captura</strong><small>Haz clic aquí y pulsa Ctrl+V. También funciona mientras escribes en este formulario.</small></span>
    </button>
    {#if archivo}
      <p class="adjunto">{archivo.name} · {Math.ceil(archivo.size / 1024)} KB
        <button type="button" onclick={() => (archivo = null)}>Retirar</button>
      </p>
    {/if}
    <p class="ruta">Pantalla: {ruta}. No se incluye la dirección completa ni parámetros de búsqueda.</p>
    {#if fallo}<p class="fallo" role="alert">{fallo}</p>{/if}
  </form>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (abierto = false)} deshabilitado={enviando}>Cancelar</Boton>
    <Boton tipo="submit" form="formulario-reporte" deshabilitado={enviando}>Revisar reporte</Boton>
  {/snippet}
</Dialogo>
{/if}

{#if confirmando}
<Dialogo bind:abierto={confirmando} tipo="confirmar" titulo="Confirmar reporte" bloqueado={enviando} ancho="32rem">
  <p>Enviarás «{titulo.trim()}» desde {ruta}{archivo ? ' con una captura' : ' sin captura'}. La descripción será visible para el equipo investigador. ¿Revisaste que no incluya información ajena innecesaria?</p>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (confirmando = false)} deshabilitado={enviando}>Volver a revisar</Boton>
    <Boton onclick={enviar} deshabilitado={enviando}>{enviando ? 'Guardando…' : 'Confirmar y enviar'}</Boton>
  {/snippet}
</Dialogo>
{/if}

<style>
  .invitacion { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-panel); }
  h2, p { margin: 0; }
  h2 { font-size: var(--texto-md); }
  p { color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.5; }
  .boton-compacto { display: inline-flex; align-items: center; gap: .4rem; border: 1px solid var(--trazo-suave); background: var(--surface-paper); border-radius: var(--radius-sm); color: var(--accent-main); padding: .55rem .7rem; cursor: pointer; font: inherit; font-size: var(--texto-sm); }
  .boton-compacto.accion { min-block-size: 2rem; padding: .3rem .55rem; border-color: transparent; border-radius: 999px; background: transparent; color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .boton-compacto.accion:hover, .boton-compacto.accion:focus-visible { border-color: var(--trazo-suave); background: color-mix(in srgb, var(--surface-paper) 55%, transparent); color: var(--ink-primary); }
  .boton-compacto.grafica { min-block-size: 27px; flex: 0 0 auto; padding: 3px 7px; border-radius: var(--radius-xs); color: var(--ink-secondary); font-size: 10.5px; white-space: nowrap; }
  .boton-compacto.previa { padding: .35rem .5rem; border-color: transparent; background: transparent; color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .boton-compacto.previa:hover, .boton-compacto.previa:focus-visible { border-color: var(--trazo-suave); color: var(--accent-main); }
  form { display: grid; gap: .8rem; }
  .contexto-reporte { display: grid; gap: .25rem; padding: .65rem .75rem; border-inline-start: 3px solid var(--accent-main); border-radius: var(--radius-xs); background: var(--accent-surface); color: var(--ink-primary); font-size: var(--texto-sm); }
  .contexto-reporte span { white-space: pre-line; color: var(--ink-secondary); }
  .contexto-reporte small { color: var(--ink-tertiary); }
  label { display: grid; gap: .25rem; color: var(--ink-primary); font-size: var(--texto-sm); font-weight: 650; }
  input, select, textarea { inline-size: 100%; padding: .6rem; border: 1px solid var(--trazo); border-radius: var(--radius-sm); background: var(--surface-panel); color: var(--ink-primary); font: inherit; font-weight: 400; }
  textarea { resize: vertical; }
  .adjunto { padding: .65rem; background: var(--semantic-success-bg); border-radius: var(--radius-sm); }
  .adjunto button { margin-inline-start: .5rem; }
  .zona-pegado { display: flex; inline-size: 100%; align-items: center; gap: .65rem; padding: .7rem; border: 1px dashed var(--accent-main); border-radius: var(--radius-sm); background: var(--accent-surface); color: var(--accent-main); cursor: text; font: inherit; text-align: start; }
  .zona-pegado span { display: grid; gap: .1rem; }
  .zona-pegado small { color: var(--ink-secondary); font-weight: 400; }
  .zona-pegado:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 2px; }
  .fallo { padding: .6rem; background: var(--semantic-danger-bg); color: var(--semantic-danger); border-radius: var(--radius-sm); }
  .ruta { font-size: var(--texto-xs); }
  .mis-reportes { display: grid; gap: .5rem; padding: 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); }
  .titulo-seguimiento { display: flex; justify-content: space-between; gap: 1rem; }
  .titulo-seguimiento button { border: 0; background: none; color: var(--accent-main); cursor: pointer; }
  article { display: flex; flex-wrap: wrap; gap: .3rem .7rem; font-size: var(--texto-sm); }
  article span { color: var(--ink-secondary); }
  article p { inline-size: 100%; }
  @media (max-width: 36rem) { .invitacion { align-items: stretch; flex-direction: column; } }
</style>
