
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import { onMount, tick } from 'svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import Icono from '../../comun/base/Icono.svelte';
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import DirectorioDeDestinatarios from './DirectorioDeDestinatarios.svelte';
  import { PLANTILLAS_COMUNICACION, TONOS_CORREO, parsearDestinatarios, faltantesDeVariables } from './plantillasDeComunicacion.js';
  import * as correos from '../../nucleo/api/correos.js';
  import { describir } from '../../nucleo/errores/degradacion.js';

  let catalogo = $state([]);
  let limites = $state({ destinatarios: 35, adjuntos: 3, adjuntos_bytes: 5 * 1024 * 1024 });
  let canalConfigurado = $state(false);
  let cargando = $state(true);
  let enviando = $state(false);
  let fallo = $state('');
  let resultado = $state(null);
  let plantilla = $state('mensaje-institucional');
  let destinatariosTexto = $state('');
  let asunto = $state('');
  let mensaje = $state('');
  let adjuntos = $state([]);
  let confirmando = $state(false);
  let eligiendoPlantilla = $state(false), directorioAbierto = $state(false);
  let borradorActivo = $state('libre'), correoManual = $state(''), editor = $state(null);
  let variables = $state({ cohorte: '', nodo_didactico: '', fecha_limite: '' });
  let enfasis = $state('oxido'), dispositivo = $state('escritorio');
  let vista = $state(null), falloVista = $state(''), actualizandoVista = $state(false);
  let indiceVista = $state(0), buscandoPlantilla = $state('');
  let rolesDestino = $state({});
  let clasesDestino = $state({});
  let borrador = $derived(PLANTILLAS_COMUNICACION.find((p) => p.id === borradorActivo));
  let faltantes = $derived(faltantesDeVariables(asunto, mensaje, variables));
  let opcionesPlantilla = $derived(PLANTILLAS_COMUNICACION.filter((p) => `${p.nombre} ${p.categoria}`.toLowerCase().includes(buscandoPlantilla.toLowerCase())));

  let seleccionada = $derived(catalogo.find((item) => item.id === plantilla) ?? null);
  let destinatarios = $derived(parsearDestinatarios(destinatariosTexto));
  let bytesAdjuntos = $derived(adjuntos.reduce((total, archivo) => total + archivo.tamano, 0));
  let formularioValido = $derived(
    destinatarios.length > 0 && destinatarios.length <= limites.destinatarios &&
    destinatarios.every((d) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.correo)) &&
    (plantilla !== 'mensaje-institucional' || (asunto.trim() && mensaje.trim() && !faltantes.length)) &&
    adjuntos.length <= limites.adjuntos && bytesAdjuntos <= limites.adjuntos_bytes
  );
  let razonesPendientes = $derived.by(() => {
    const razones = [];
    if (!canalConfigurado) razones.push('El canal de correo no está configurado en este entorno.');
    if (!destinatarios.length) razones.push('Agrega al menos una persona destinataria.');
    if (destinatarios.length > limites.destinatarios) razones.push(`Usa máximo ${limites.destinatarios} destinatarios.`);
    if (destinatarios.some((d) => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.correo))) razones.push('Corrige las direcciones de correo incompletas.');
    if (plantilla === 'mensaje-institucional') {
      if (!asunto.trim()) razones.push('Escribe el asunto.');
      if (!mensaje.trim()) razones.push('Escribe el mensaje.');
      if (faltantes.length) razones.push(`Completa en Datos del mensaje: ${faltantes.map((clave) => ({cohorte:'clase o grupo', nodo_didactico:'nodo didáctico', fecha_limite:'fecha u horario'})[clave]).join(', ')}.`);
    }
    if (adjuntos.length > limites.adjuntos || bytesAdjuntos > limites.adjuntos_bytes) razones.push('Reduce los adjuntos al límite indicado.');
    return razones;
  });

  function serializar(lista) {
    destinatariosTexto = lista.map((d) => d.nombre ? `${d.nombre} <${d.correo}>` : d.correo).join('\n');
  }
  function retirarDestino(correo) { serializar(destinatarios.filter((d) => d.correo.toLowerCase() !== correo.toLowerCase())); }
  function elegirCurso(personas, nombreCurso) {
    const lista = new Map(destinatarios.map((d) => [d.correo.toLowerCase(), d]));
    for (const p of personas) lista.set(p.correo.toLowerCase(), lista.get(p.correo.toLowerCase()) ?? { nombre:p.nombre, correo:p.correo });
    if (lista.size > limites.destinatarios) { fallo = `Máximo ${limites.destinatarios} destinatarios por envío. Divide el curso en dos envíos.`; return; }
    for (const p of personas) {
      rolesDestino[p.correo.toLowerCase()] = 'Estudiante matriculado';
      clasesDestino[p.correo.toLowerCase()] = p.clases ?? [];
    }
    serializar([...lista.values()]);
    if (!variables.cohorte.trim()) variables.cohorte = nombreCurso;
    fallo = '';
  }
  function elegirPersona(p) {
    if (destinatarios.some((d) => d.correo.toLowerCase() === p.correo.toLowerCase())) retirarDestino(p.correo);
    else if (destinatarios.length < limites.destinatarios) {
      const clave = p.correo.toLowerCase();
      rolesDestino[clave] = (p.roles ?? []).length ? p.roles.join(' · ') : p.es_docente ? 'Docente' : 'Estudiante matriculado';
      clasesDestino[clave] = p.clases ?? [];
      serializar([...destinatarios, { nombre:p.nombre, correo:p.correo }]);
      const personasDelDirectorio = [...destinatarios, p];
      const clasesCompartidas = personasDelDirectorio.map((d) => clasesDestino[d.correo.toLowerCase()]);
      if (!variables.cohorte.trim() && clasesCompartidas.every((lista) => lista?.length === 1)
        && clasesCompartidas.every(([c]) => String(c.id) === String(clasesCompartidas[0][0].id))) {
        variables.cohorte = clasesCompartidas[0][0].nombre ?? '';
      }
    }
  }
  function agregarManual() {
    const nuevos = parsearDestinatarios(correoManual);
    const juntos = parsearDestinatarios(`${destinatariosTexto}\n${correoManual}`);
    if (!nuevos.length || nuevos.some((d) => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.correo))) { fallo = 'Revisa la dirección de correo.'; return; }
    if (juntos.length > limites.destinatarios) { fallo = `Máximo ${limites.destinatarios} destinatarios por envío.`; return; }
    serializar(juntos); correoManual = ''; fallo = '';
  }
  function aplicarBorrador(p) {
    plantilla = 'mensaje-institucional'; borradorActivo = p.id;
    asunto = p.asunto; mensaje = p.mensaje; eligiendoPlantilla = false;
  }
  async function insertarVariable(clave) {
    if (!editor) return;
    const desde = editor.selectionStart ?? mensaje.length, hasta = editor.selectionEnd ?? desde;
    const texto = `{${clave}}`;
    mensaje = mensaje.slice(0, desde) + texto + mensaje.slice(hasta);
    await tick(); editor.focus(); editor.setSelectionRange(desde + texto.length, desde + texto.length);
  }

  $effect(() => {
    if (!catalogo.length) return;
    const cuerpo = { plantilla, asunto: asunto.trim() || 'Asunto de la comunicación', mensaje: mensaje.trim() || 'Escribe el mensaje para ver cómo lo recibirá cada persona.',
      variables: { ...variables }, enfasis,
      destinatarios: [destinatarios[indiceVista] ?? destinatarios[0] ?? { nombre:'Persona destinataria', correo:'vista-previa@example.invalid' }] };
    falloVista = ''; actualizandoVista = true;
    const controlador = new AbortController();
    const espera = setTimeout(async () => {
      try { const r = await correos.previsualizar(cuerpo, { señal: controlador.signal }); if (!controlador.signal.aborted) { if(!r.html) throw new Error('Vista previa no disponible.'); vista = r; } }
      catch (e) { if (!controlador.signal.aborted) { vista = null; falloVista = detalleDe(e); } }
      finally { if (!controlador.signal.aborted) actualizandoVista = false; }
    }, 350);
    return () => { clearTimeout(espera); controlador.abort(); };
  });

  function detalleDe(error) {
    return error?.cuerpo?.detalle || describir(error).explicacion;
  }

  async function cargar() {
    cargando = true;
    fallo = '';
    try {
      const respuesta = await correos.listarPlantillas();
      catalogo = respuesta.plantillas ?? [];
      limites = respuesta.limites ?? limites;
      canalConfigurado = respuesta.canal_configurado === true;
    } catch (error) {
      fallo = detalleDe(error);
    } finally {
      cargando = false;
    }
  }

  function leerComoBase64(archivo) {
    return new Promise((resolver, rechazar) => {
      const lector = new FileReader();
      lector.onerror = () => rechazar(new Error('No se pudo leer el archivo.'));
      lector.onload = () => resolver(String(lector.result).split(',', 2)[1] ?? '');
      lector.readAsDataURL(archivo);
    });
  }

  async function elegirArchivos(evento) {
    fallo = '';
    const archivos = [...(evento.currentTarget.files ?? [])];
    evento.currentTarget.value = '';
    if (archivos.length + adjuntos.length > limites.adjuntos) {
      fallo = `Puedes adjuntar máximo ${limites.adjuntos} archivos por envío.`;
      return;
    }
    const total = bytesAdjuntos + archivos.reduce((suma, archivo) => suma + archivo.size, 0);
    if (total > limites.adjuntos_bytes) {
      fallo = `Los adjuntos no pueden superar ${formatearBytes(limites.adjuntos_bytes)} en total.`;
      return;
    }
    try {
      const nuevos = await Promise.all(archivos.map(async (archivo) => ({
        nombre: archivo.name,
        tipo: archivo.type || 'application/octet-stream',
        tamano: archivo.size,
        contenido: await leerComoBase64(archivo)
      })));
      adjuntos = [...adjuntos, ...nuevos];
    } catch (error) {
      fallo = error.message;
    }
  }

  function retirarAdjunto(indice) {
    adjuntos = adjuntos.filter((_, actual) => actual !== indice);
  }

  function formatearBytes(bytes) {
    return bytes >= 1024 * 1024
      ? `${(bytes / (1024 * 1024)).toLocaleString('es-CO', { maximumFractionDigits: 1 })} MB`
      : `${Math.ceil(bytes / 1024)} KB`;
  }

  function prepararEnvio(evento) {
    evento.preventDefault();
    fallo = '';
    resultado = null;
    if (!formularioValido || !canalConfigurado) {
      fallo = razonesPendientes.join(' ');
      toast.error(fallo);
      return;
    }
    confirmando = true;
  }

  async function enviar() {
    enviando = true;
    fallo = '';
    resultado = null;
    try {
      resultado = await correos.enviar({
        plantilla,
        destinatarios,
        asunto: asunto.trim(),
        mensaje: mensaje.trim(),
        adjuntos: adjuntos.map(({ nombre, tipo, contenido }) => ({ nombre, tipo, contenido })),
        confirmado: true,
        ...(plantilla === 'mensaje-institucional' ? { variables: { ...variables }, enfasis } : {})
      });
      confirmando = false;
      if (resultado.enviados === resultado.destinatarios) {
        toast.comunicar(`${resultado.enviados} correo${resultado.enviados === 1 ? '' : 's'} aceptado${resultado.enviados === 1 ? '' : 's'} · auditoría #${resultado.auditoria}`);
        destinatariosTexto = '';
        asunto = '';
        mensaje = '';
        adjuntos = [];
      }
      else { fallo = `${resultado.fallidos} correo${resultado.fallidos === 1 ? '' : 's'} no fue${resultado.fallidos === 1 ? '' : 'ron'} aceptado${resultado.fallidos === 1 ? '' : 's'} por el proveedor. Consulta el registro #${resultado.auditoria} y el panel del canal antes de reintentar.`; toast.error(fallo); }
    } catch (error) {
      fallo = detalleDe(error);
      toast.error(fallo);
    } finally {
      enviando = false;
    }
  }

  onMount(cargar);
</script>

<section class="compositor" aria-labelledby="titulo-correos">
  <header><div class="titulo"><Icono nombre="correo" medida={22} /><h2 id="titulo-correos">Correo institucional</h2>
    <BotonAyudaTooltip ariaLabel="Ayuda sobre el envío institucional" texto={`Máximo ${limites.destinatarios} destinatarios y ${limites.adjuntos} adjuntos por acción. Cada persona recibe una copia individual. Revisa el contenido antes de confirmar; el envío se audita sin guardar el texto ni las direcciones.`} /></div>
    <span class="estado-canal" class:disponible={canalConfigurado}>{canalConfigurado ? 'Canal configurado' : 'Canal no configurado'}</span>
  </header>
  {#if cargando}<CargadorCubo mensaje="Consultando las plantillas…" />{:else if catalogo.length}
    <div class="plantilla-activa"><span class="categoria">{plantilla === 'mensaje-institucional' ? borrador?.categoria : 'Ensayo visual'}</span>
      <strong>{plantilla === 'mensaje-institucional' ? borrador?.nombre : seleccionada?.nombre}</strong>
      <button type="button" onclick={() => eligiendoPlantilla = true}><Icono nombre="biblioteca" medida={16} /> Cambiar plantilla <span aria-hidden="true">⌄</span></button>
    </div>
    <form onsubmit={prepararEnvio}>
      <div class="campos">
        <div class="bloque-destinatarios">
          <div class="linea-titulo"><h3>Destinatarios</h3><span class="contador">{destinatarios.length}/{limites.destinatarios}</span></div>
          {#if destinatarios.length}<ul class="chips">{#each destinatarios as d (d.correo)}<li><span><strong>{d.nombre || d.correo}</strong>{#if d.nombre}<small>{d.correo}</small>{/if}{#if rolesDestino[d.correo.toLowerCase()]}<small>{rolesDestino[d.correo.toLowerCase()]}</small>{/if}</span><button type="button" onclick={() => retirarDestino(d.correo)} aria-label={`Retirar destinatario ${d.correo}`}>×</button></li>{/each}</ul>{/if}
          <button class="directorio-boton" type="button" onclick={() => directorioAbierto = true}><Icono nombre="equipo-institucional" medida={18} /> Directorio institucional</button>
          <div class="entrada-manual"><label>Correo externo o institucional<input type="text" bind:value={correoManual} placeholder="nombre@institucion.edu.co" onkeydown={(e) => { if(e.key === 'Enter') { e.preventDefault(); agregarManual(); } }} /></label><button type="button" onclick={agregarManual} aria-label="Añadir correo escrito">+</button></div>
          <details><summary>Pegar varias direcciones</summary><label>Destinatarios<textarea bind:value={destinatariosTexto} rows="3" placeholder={'Ana Pérez <ana@example.com>\nexterno@example.com'}></textarea></label></details>
          <p class="ayuda-variables">Para escribir a un curso, abre el Directorio institucional, elige la clase y añade sus estudiantes.</p>
        </div>
        {#if plantilla === 'mensaje-institucional'}
          <label>Asunto<input bind:value={asunto} maxlength="160" placeholder="Asunto de la comunicación" /></label>
          <div class="mensaje-editor"><div class="linea-titulo"><label for="mensaje-correo">Mensaje</label><span class="contador">{mensaje.length}/8000</span></div>
            <div class="variables-rapidas" aria-label="Insertar variable en el mensaje">{#each ['nombre','cohorte','nodo_didactico','fecha_limite'] as clave}<button type="button" onpointerdown={(e) => e.preventDefault()} onclick={() => insertarVariable(clave)}>{`{${clave}}`}</button>{/each}<BotonAyudaTooltip tamano="sm" texto="Inserta la variable en la posición del cursor. El nombre se resuelve para cada destinatario; los demás valores se completan en Datos del mensaje." /></div>
            <textarea id="mensaje-correo" bind:this={editor} bind:value={mensaje} rows="9" maxlength="8000" placeholder="Escribe el mensaje que recibirá cada persona."></textarea>
          </div>
          <details open={faltantes.length > 0}><summary>Datos del mensaje {#if faltantes.length}<span class="pendiente">· {faltantes.length} por completar</span>{/if}</summary>
            <p class="ayuda-variables">Si usas una etiqueta, se reemplaza en el asunto o mensaje. Los datos escritos sin etiqueta se añaden al final del correo. La clase se propone desde el directorio cuando todos los destinatarios comparten una misma.</p>
            <div class="datos-mensaje"><label>Clase o grupo<input bind:value={variables.cohorte} maxlength="200" placeholder="Nombre del grupo" /></label><label>Nodo didáctico<input bind:value={variables.nodo_didactico} maxlength="200" placeholder="Contenido trabajado" /></label><label>Fecha u horario acordado<input bind:value={variables.fecha_limite} maxlength="200" placeholder="Fecha y horario confirmados" /></label></div>
          </details>
        {:else}<p class="aviso-prueba" role="note">Esta plantilla recrea un aviso automático y saldrá marcada como <strong>Prueba</strong>; no crea el evento real que describe.</p>{/if}
        <details class="adjuntos"><summary>Adjuntos <span class="contador">{adjuntos.length}/{limites.adjuntos}</span></summary>
          <small>PDF, imágenes, texto, CSV y Office · hasta {formatearBytes(limites.adjuntos_bytes)} en total.</small>
          <label class="boton-archivo">Elegir archivos<input class="solo-lectura-asistida" type="file" multiple onchange={elegirArchivos} accept=".pdf,.png,.jpg,.jpeg,.txt,.csv,.docx,.xlsx,.pptx" /></label>
          <ul class="lista-archivos">{#each adjuntos as archivo, indice}<li><span>{archivo.nombre} · {formatearBytes(archivo.tamano)}</span><button type="button" onclick={() => retirarAdjunto(indice)} aria-label={`Retirar ${archivo.nombre}`}>×</button></li>{/each}</ul>
        </details>
        <div class="accion-principal"><Boton tipo="submit" deshabilitado={enviando}>Revisar y enviar</Boton></div>
        {#if razonesPendientes.length}<p class="estado-preparacion" role="status">Para enviar: {razonesPendientes.join(' ')}</p>{/if}
      </div>
      <aside class="vista-previa" aria-labelledby="titulo-vista-previa">
        <div class="linea-titulo"><h3 id="titulo-vista-previa">Render en vivo</h3><BotonAyudaTooltip texto="El servidor genera esta vista con el mismo armazón, contenido escapado y personalización del envío. No se envía ningún correo al previsualizar. La fuente manuscrita y las imágenes pueden variar según el cliente de correo." /></div>
        <div class="barra-render">
          <div class="tonos" role="group" aria-label="Color del correo">{#each TONOS_CORREO as tono}<button type="button" style={`--tono:var(${tono.token})`} aria-label={tono.nombre} aria-pressed={enfasis === tono.id} disabled={plantilla !== 'mensaje-institucional'} onclick={() => enfasis = tono.id}><span aria-hidden="true">{enfasis === tono.id ? '✓' : ''}</span></button>{/each}</div>
          <div class="dispositivo" role="group" aria-label="Dispositivo de vista previa"><button type="button" aria-pressed={dispositivo === 'escritorio'} onclick={() => dispositivo = 'escritorio'}>Escritorio</button><button type="button" aria-pressed={dispositivo === 'movil'} onclick={() => dispositivo = 'movil'}>Móvil</button></div>
        </div>
        {#if destinatarios.length > 1}<label>Vista para<select use:menuDesplegable={indiceVista} bind:value={indiceVista}>{#each destinatarios as d, i}<option value={i}>{d.nombre || d.correo}</option>{/each}</select></label>{/if}
        <div class="estado-render" aria-live="polite">{#if actualizandoVista}Actualizando vista previa…{:else if falloVista}<span class="pendiente">{falloVista}</span>{:else}{vista?.asunto || seleccionada?.asunto_ejemplo}{/if}</div>
        <div class="lienzo" class:movil={dispositivo === 'movil'}><iframe title={`Vista previa de ${plantilla === 'mensaje-institucional' ? borrador?.nombre : seleccionada?.nombre}`} sandbox referrerpolicy="no-referrer" srcdoc={vista?.html ?? ''}></iframe></div>
      </aside>
    </form>
  {/if}
  {#if fallo}<p class="fallo" role="alert">{fallo}</p>{/if}
  {#if resultado?.fallidos}<p class="resultado parcial" role="alert">{resultado.enviados} de {resultado.destinatarios} correos aceptados. Registro de auditoría #{resultado.auditoria}.</p>{/if}
</section>

{#if eligiendoPlantilla}<Dialogo bind:abierto={eligiendoPlantilla} titulo="Elegir plantilla de comunicación" ancho="45rem">
  <label>Buscar plantilla<input type="search" bind:value={buscandoPlantilla} placeholder="Nombre o categoría" /></label>
  <div class="catalogo">{#each opcionesPlantilla as p (p.id)}<button type="button" class:seleccionado={borradorActivo === p.id && plantilla === 'mensaje-institucional'} onclick={() => aplicarBorrador(p)}><small>{p.categoria}</small><strong>{p.nombre}</strong><span>Usar borrador <span aria-hidden="true">↗</span></span></button>{:else}<p>No hay plantillas con ese nombre.</p>{/each}</div>
  <details><summary>Ensayos de avisos automáticos</summary><div class="catalogo">{#each catalogo.filter((p) => p.solo_prueba) as p (p.id)}<button type="button" onclick={() => { plantilla = p.id; eligiendoPlantilla = false; }}><small>Prueba visible</small><strong>{p.nombre}</strong></button>{/each}</div></details>
</Dialogo>{/if}
{#if directorioAbierto}<Dialogo bind:abierto={directorioAbierto} titulo="Directorio institucional" ancho="40rem"><DirectorioDeDestinatarios elegidos={destinatarios} limite={limites.destinatarios} alElegir={elegirPersona} alElegirCurso={elegirCurso} />{#snippet acciones()}<Boton onclick={() => directorioAbierto = false}>Listo</Boton>{/snippet}</Dialogo>{/if}
{#if confirmando}<Dialogo bind:abierto={confirmando} tipo="comunicar" titulo="Confirmar envío institucional" bloqueado={enviando} ancho="34rem">
  <div class="resumen"><p>Vas a enviar <strong>{plantilla === 'mensaje-institucional' ? borrador?.nombre : seleccionada?.nombre}</strong> a <strong>{destinatarios.length} destinatario{destinatarios.length === 1 ? '' : 's'}</strong>.</p>
    <ul class="lista-confirmacion">{#each destinatarios as d (d.correo)}<li>{d.nombre ? `${d.nombre} · ` : ''}{d.correo}</li>{/each}</ul>
    <dl><div><dt>Modo</dt><dd>{seleccionada?.solo_prueba ? 'Prueba visible' : 'Comunicación real'}</dd></div><div><dt>Adjuntos</dt><dd>{adjuntos.length} · {formatearBytes(bytesAdjuntos)}</dd></div><div><dt>Privacidad</dt><dd>Un correo individual por persona</dd></div></dl>
    <p>El envío quedará auditado antes de contactar al proveedor. Revisa los destinatarios y el contenido.</p>
    {#if enviando}<p role="status">Enviando {destinatarios.length} copias individuales. Mantén esta ventana abierta hasta recibir el resultado.</p>{/if}
    {#if fallo}<p class="fallo" role="alert">{fallo}</p>{/if}
  </div>
  {#snippet acciones()}<Boton variante="secundario" onclick={() => confirmando = false} deshabilitado={enviando}>Cancelar</Boton><Boton onclick={enviar} deshabilitado={enviando}>{enviando ? 'Enviando…' : 'Confirmar y enviar'}</Boton>{/snippet}
</Dialogo>{/if}

<style>
  .compositor { display:grid; gap:1rem; padding:1rem; min-inline-size:0; border:1px solid var(--trazo-suave); border-radius:var(--radius-lg); background:var(--surface-paper); box-shadow:var(--shadow-soft); }
  header,.titulo,.linea-titulo,.barra-render { display:flex; align-items:center; gap:.6rem; } header,.linea-titulo,.barra-render { justify-content:space-between; flex-wrap:wrap; }
  .titulo { color:var(--accent-main); } h2,h3,p { margin:0; } h2 { font-size:var(--texto-md); color:var(--ink-primary); } h3 { font-size:var(--texto-sm); }
  .estado-canal { padding:.3rem .5rem; border-radius:var(--radius-pill); font-size:var(--texto-xs); color:var(--semantic-danger); background:var(--semantic-danger-bg); } .estado-canal.disponible { color:var(--semantic-success); background:var(--semantic-success-bg); }
  .plantilla-activa { display:flex; align-items:center; gap:.6rem; padding:.65rem .8rem; border:1px solid var(--trazo-suave); border-radius:var(--radius-md); background:var(--surface-panel); min-inline-size:0; flex-wrap:wrap; }
  .plantilla-activa strong { flex:1; min-inline-size:0; font-size:var(--texto-sm); overflow-wrap:anywhere; } .categoria { font-size:var(--texto-xs); color:var(--accent-main); }
  button { cursor:pointer; font:inherit; color:var(--ink-primary); background:var(--surface-paper); border:1px solid var(--trazo); border-radius:var(--radius-sm); min-block-size:2.5rem; padding:.4rem .65rem; }
  button:focus-visible { outline:2px solid var(--accent-main); outline-offset:2px; } button:hover { background:var(--accent-surface); } button:disabled { opacity:.5; cursor:default; }
  .plantilla-activa button,.directorio-boton { display:inline-flex; gap:.4rem; align-items:center; font-size:var(--texto-sm); }
  form { display:grid; grid-template-columns:minmax(0,1fr) minmax(380px,.95fr); gap:1.2rem; align-items:start; } .campos { display:grid; gap:1rem; min-inline-size:0; }
  .bloque-destinatarios { display:grid; gap:.6rem; } .contador,small { color:var(--ink-tertiary); font-size:var(--texto-xs); font-weight:400; } .contador { white-space:nowrap; }
  label { display:grid; gap:.35rem; color:var(--ink-secondary); font-size:var(--texto-sm); font-weight:650; min-inline-size:0; }
  input,select,textarea { inline-size:100%; min-inline-size:0; padding:.6rem .7rem; min-block-size:2.6rem; border:1px solid var(--trazo); border-radius:var(--radius-sm); background:var(--surface-panel); color:var(--ink-primary); font:inherit; font-weight:400; } textarea { resize:vertical; line-height:1.6; }
  .entrada-manual { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:end; gap:.4rem; } .entrada-manual button { inline-size:2.8rem; }
  .chips { display:flex; flex-wrap:wrap; gap:.4rem; } ul { list-style:none; margin:0; padding:0; }
  .chips li { display:flex; gap:.3rem; align-items:center; min-inline-size:0; max-inline-size:100%; padding:.3rem .5rem; background:var(--semantic-info-bg); border-radius:var(--radius-sm); }
  .chips span { display:grid; min-inline-size:0; } .chips strong { font-size:var(--texto-xs); } .chips button,.lista-archivos button { border:0; background:transparent; flex:none; }
  .chips strong,small,.lista-archivos span,.lista-confirmacion li { overflow-wrap:anywhere; }
  details { border:1px solid var(--trazo-suave); padding:.6rem .7rem; border-radius:var(--radius-sm); min-inline-size:0; } summary { cursor:pointer; color:var(--ink-secondary); font-size:var(--texto-sm); } details[open]>summary { margin-block-end:.7rem; }
  .mensaje-editor { display:grid; gap:.4rem; } .variables-rapidas { display:flex; flex-wrap:wrap; gap:.3rem; align-items:center; } .variables-rapidas button { font-family:var(--fuente-mono); font-size:var(--texto-xs); min-block-size:2rem; padding:.3rem .4rem; border-color:var(--trazo-suave); }
  .datos-mensaje { display:grid; gap:.6rem; } .pendiente { color:var(--semantic-warning); } .aviso-prueba { padding:.8rem; background:var(--semantic-warning-bg); color:var(--semantic-warning); font-size:var(--texto-sm); }
  .ayuda-variables,.estado-preparacion { color:var(--ink-secondary); font-size:var(--texto-xs); line-height:1.5; }
  .adjuntos small { display:block; margin-block-end:.5rem; } .boton-archivo { display:inline-flex; position:relative; padding:.5rem .7rem; border:1px solid var(--trazo); border-radius:var(--radius-sm); cursor:pointer; }
  .lista-archivos { display:grid; gap:.4rem; } .lista-archivos li { display:flex; align-items:center; justify-content:space-between; gap:.4rem; font-size:var(--texto-xs); }
  .accion-principal { display:flex; justify-content:flex-end; } .vista-previa { display:grid; gap:.75rem; min-inline-size:0; padding:1rem; background:var(--surface-panel); border:1px solid var(--trazo-suave); border-radius:var(--radius-lg); position:sticky; inset-block-start:1rem; }
  .tonos,.dispositivo { display:flex; gap:.35rem; align-items:center; flex-wrap:wrap; } .tonos button { border-radius:var(--radius-pill); inline-size:2.5rem; block-size:2.5rem; padding:.35rem; } .tonos span { display:grid; place-items:center; border-radius:var(--radius-pill); block-size:100%; background:var(--tono); color:var(--surface-paper); }
  button[aria-pressed=true] { border-color:var(--accent-main); box-shadow:var(--shadow-soft); } .dispositivo button { font-size:var(--texto-xs); }
  .estado-render { min-block-size:2rem; font-size:var(--texto-xs); color:var(--ink-secondary); overflow-wrap:anywhere; } .lienzo { inline-size:100%; min-inline-size:0; margin-inline:auto; } .lienzo.movil { max-inline-size:350px; border:4px solid var(--trazo); border-radius:var(--radius-xl); overflow:hidden; }
  iframe { display:block; inline-size:100%; block-size:36rem; border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); background:var(--surface-paper); }
  .catalogo { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.6rem; margin-block:1rem; } .catalogo button { display:grid; gap:.4rem; text-align:start; padding:.85rem; border-color:var(--trazo-suave); } .catalogo button.seleccionado { border-color:var(--accent-main); background:var(--accent-surface); } .catalogo strong { overflow-wrap:anywhere; } .catalogo span { color:var(--accent-main); font-size:var(--texto-xs); }
  .resumen { display:grid; gap:.8rem; } dl { display:grid; gap:.4rem; margin:0; } dl div { display:grid; grid-template-columns:5rem minmax(0,1fr); gap:.6rem; } dd { margin:0; } dt,.resumen p { color:var(--ink-secondary); } .lista-confirmacion { display:grid; gap:.3rem; }
  .fallo,.resultado { padding:.8rem; border-radius:var(--radius-sm); overflow-wrap:anywhere; } .fallo,.resultado.parcial { background:var(--semantic-danger-bg); color:var(--semantic-danger); } .resultado { background:var(--semantic-success-bg); color:var(--semantic-success); }
  @media(max-width:60rem) { form { grid-template-columns:minmax(0,1fr); } .vista-previa { position:static; } }
  @media(max-width:36rem) { .compositor,.vista-previa { padding:.75rem; } .plantilla-activa button { inline-size:100%; justify-content:center; } .catalogo { grid-template-columns:minmax(0,1fr); } iframe { block-size:30rem; } }
</style>
