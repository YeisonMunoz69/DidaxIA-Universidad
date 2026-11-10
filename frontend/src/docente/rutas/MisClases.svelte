<!--
DD-12 · Las clases del docente.

Con su código y su lista de estudiantes.

SIN TAREAS, CALIFICACIONES, ENTREGAS, CALENDARIO NI MENSAJERIA. La frontera
está escrita en DD-12 y no se interpreta con generosidad: cualquier añadido
exige modificar la decisión, no ampliarla por conveniencia.

LA LISTA DE INTEGRANTES NO ES UN PANEL DE SEGUIMIENTO. Muestra quién está
matriculado y nada más — ni progreso, ni indicios, ni última conexión. Lo que
el sistema infiere de una persona vive en su ficha, que es otra ruta y tiene su
propia advertencia. Mezclarlo aquí convertiría una lista administrativa en un
tablero de vigilancia sin que nadie lo decidiera.

Dos paneles, no dos secciones apiladas · 2026-08-22
-----------------------------------------------------
Hasta esta fecha, el formulario de creación vivía siempre visible junto a la
lista, y el detalle de la clase seleccionada aparecía DEBAJO de las dos, a
todo el ancho — confirmado con el usuario como el problema real: quería el
detalle AL LADO de la lista, no abajo, y «Crear clase» como una acción, no
como una tarjeta que ocupa sitio aunque no se esté usando.

Ahora «Crear clase» es un botón en la cabecera que abre `Dialogo.svelte`
—reutilizado tal cual, el mismo componente que `Ajustes.svelte` ya usa—, y
el cuerpo es dos paneles con scroll cada uno por su cuenta
(`overflow-y: auto`), sin que la página entera intente desplazarse: mismo
patrón que `estudiante/rutas/Conversacion.svelte` ya usa para «armazón, no
flujo de documento».


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
Origen de esta pieza: OE3-Implementacion/09-Aportes-de-la-Consulta-Docente.md

-->
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { ayudaContextual } from '../../comun/base/ayudaContextual.js';
  import { onMount, tick } from 'svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import CodigoDeClase from '../piezas/CodigoDeClase.svelte';
  import CabeceraDeRuta from '../piezas/CabeceraDeRuta.svelte';
  import EstadoVacio from '../piezas/EstadoVacio.svelte';
  import SolicitudesDeMatricula from '../../comun/clases/SolicitudesDeMatricula.svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Campo from '../../comun/base/Campo.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import * as api from '../../nucleo/api/clases.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { navegar } from '../../enrutado/navegar.js';
  import { CAMINOS } from '../../enrutado/caminos.js';

  let clases = $state([]);
  let cargandoClases = $state(true);
  let solicitudes = $state([]);
  let abierta = $state(null);
  let integrantes = $state([]);
  let nombreNuevo = $state('');
  let fallo = $state(null);
  let creando = $state(false);
  let seccion = $state('estudiantes');
  let editandoNombre = $state(false);
  let nombreEditado = $state('');
  let guardandoNombre = $state(false);
  let campoNombre = $state(null);
  let confirmandoRetiro = $state(false);
  let integranteARetirar = $state(null);
  let motivoRetiro = $state('Ingreso a la clase por error');
  let retirando = $state(false);
  let confirmandoArchivo = $state(false);
  let motivoArchivo = $state('Clase creada para pruebas');
  let archivando = $state(false);

  const pendientes = $derived(
    solicitudes.filter((solicitud) => solicitud.estado === 'pendiente')
  );

  function pendientesDe(clase) {
    return pendientes.filter((solicitud) => solicitud.clase_destino?.id === clase).length;
  }

  async function cargar({ silencioso = false } = {}) {
    if (!silencioso) cargandoClases = true;
    if (!silencioso) fallo = null;
    try {
      const [nuevasClases, nuevasSolicitudes] = await Promise.all([
        api.mias(), api.solicitudes()
      ]);
      clases = nuevasClases ?? [];
      solicitudes = nuevasSolicitudes ?? [];

      // El sondeo no debe dejar el panel abierto con una copia antigua de la
      // clase. Se conserva la selección —que fue explícita— y se actualizan
      // sus contadores y código desde la respuesta más reciente.
      if (abierta) {
        abierta = clases.find((clase) => clase.id === abierta.id) ?? null;
      }
    }
    catch (e) {
      // Una actualización en segundo plano no borra datos que ya se estaban
      // leyendo. El siguiente foco o ciclo volverá a intentarlo; el primer
      // montaje y las acciones explícitas sí muestran el fallo.
      if (!silencioso) fallo = describir(e);
    }
    finally { if (!silencioso) cargandoClases = false; }
  }

  async function abrir(clase) {
    abierta = clase;
    seccion = 'estudiantes';
    integrantes = [];
    try { integrantes = (await api.integrantes(clase.id)) ?? []; }
    catch (e) { fallo = describir(e); }
  }

  async function refrescarIntegrantes() {
    if (!abierta) return;
    try { integrantes = (await api.integrantes(abierta.id)) ?? []; }
    catch (e) { fallo = describir(e); }
  }

  async function refrescarDespuesDeResolver() {
    await Promise.all([
      cargar({ silencioso: true }),
      refrescarIntegrantes()
    ]);
  }

  async function crear() {
    if (!nombreNuevo.trim()) return;
    try {
      // `api.crear()` devuelve la clase con su código — se abre de una vez
      // en el panel derecho en vez de dejarlo vacío hasta un segundo clic
      // en la lista, que es justo el paso siguiente natural tras crearla.
      const nueva = await api.crear(nombreNuevo);
      nombreNuevo = '';
      creando = false;
      if (nueva) await abrir(nueva);
      await cargar();
      toast.exito('Clase creada con éxito.');
    } catch (e) { fallo = describir(e); }
  }

  async function regenerar() {
    if (!abierta) return;
    try {
      const r = await api.regenerarCodigo(abierta.id);
      abierta = { ...abierta, codigo: r?.codigo ?? abierta.codigo };
      await cargar();
    } catch (e) { fallo = describir(e); }
  }

  async function empezarEdicionDeNombre() {
    nombreEditado = abierta?.nombre ?? '';
    editandoNombre = true;
    await tick();
    campoNombre?.focus();
    campoNombre?.select();
  }

  function cancelarEdicionDeNombre() {
    editandoNombre = false;
    nombreEditado = abierta?.nombre ?? '';
  }

  async function guardarNombre() {
    const nombre = nombreEditado.trim();
    if (!abierta || !nombre || nombre === abierta.nombre || guardandoNombre) {
      if (nombre === abierta?.nombre) editandoNombre = false;
      return;
    }
    guardandoNombre = true;
    fallo = null;
    try {
      const actualizada = await api.renombrar(abierta.id, nombre);
      abierta = { ...abierta, ...actualizada };
      clases = clases.map((clase) => clase.id === abierta.id ? { ...clase, ...actualizada } : clase);
      editandoNombre = false;
    } catch (e) {
      fallo = describir(e);
    } finally {
      guardandoNombre = false;
    }
  }

  function alTeclaNombre(evento) {
    if (evento.key === 'Enter') { evento.preventDefault(); guardarNombre(); }
    if (evento.key === 'Escape') cancelarEdicionDeNombre();
  }

  onMount(() => {
    cargar();

    // Las solicitudes llegan desde otra sesión y no existe un evento local
    // que pueda anunciarlas. Se consulta con una cadencia deliberadamente
    // tranquila y también al volver a la pestaña: así la docente recibe la
    // señal sin recargar y sin convertir la pantalla en sondeo agresivo.
    // La bandeja abierta consulta sólo solicitudes cada cinco segundos y
    // comparte su resultado; no duplica aquí la misma consulta ni se sondea
    // una pestaña del navegador oculta.
    const actualizar = () => {
      if (document.visibilityState !== 'visible' || seccion === 'solicitudes') return;
      void cargar({ silencioso: true });
    };
    const alVolver = () => {
      if (!globalThis.document || globalThis.document.visibilityState === 'visible') actualizar();
    };
    const intervalo = globalThis.setInterval?.(actualizar, 10000);
    globalThis.addEventListener?.('focus', alVolver);
    globalThis.document?.addEventListener?.('visibilitychange', alVolver);

    return () => {
      if (intervalo !== undefined) globalThis.clearInterval?.(intervalo);
      globalThis.removeEventListener?.('focus', alVolver);
      globalThis.document?.removeEventListener?.('visibilitychange', alVolver);
    };
  });

  /**
   * A la ficha de un matriculado, con su clase · Fase 7.
   *
   * Los DOS identificadores viajan en la consulta, y no sólo el del estudiante:
   * la autorización del servidor es «esta clase es tuya **y** esta persona está
   * en ella», así que una ficha sin clase no se podría pedir. Además es lo que
   * permite que recargar la página conserve el destino y que Atrás funcione,
   * porque queda en la dirección y no en el estado de este componente.
   *
   * Ni el nombre ni el correo entran en la dirección: `EQ-020` no los usa como
   * clave y una URL con el nombre de alguien acaba en un registro de servidor.
   */
  function abrirFicha(integrante) {
    if (!abierta?.id || !integrante?.identificador) return;
    const consulta = new URLSearchParams({
      clase: abierta.id,
      id: integrante.identificador
    });
    navegar(`${CAMINOS.estudiante}?${consulta}`);
  }

  function prepararRetiro(integrante) {
    integranteARetirar = integrante;
    motivoRetiro = 'Ingreso a la clase por error';
    confirmandoRetiro = true;
  }

  async function retirarIntegrante() {
    if (!abierta?.id || !integranteARetirar?.identificador || motivoRetiro.trim().length < 5) return;
    retirando = true;
    fallo = null;
    try {
      const nombre = integranteARetirar.nombre || 'La persona';
      await api.retirarIntegrante(
        abierta.id, integranteARetirar.identificador, motivoRetiro.trim()
      );
      integrantes = integrantes.filter(
        (item) => item.identificador !== integranteARetirar.identificador
      );
      confirmandoRetiro = false;
      integranteARetirar = null;
      toast.error(`${nombre} fue retirado de ${abierta.nombre}. Su cuenta y su historia se conservaron.`);
      await cargar({ silencioso: true });
    } catch (e) {
      fallo = describir(e);
    } finally {
      retirando = false;
    }
  }

  async function archivarClase() {
    if (!abierta?.id || motivoArchivo.trim().length < 5) return;
    archivando = true;
    fallo = null;
    try {
      const nombre = abierta.nombre;
      await api.archivar(abierta.id, motivoArchivo.trim());
      abierta = null;
      integrantes = [];
      confirmandoArchivo = false;
      toast.error(`${nombre} fue retirada de las vistas y estadísticas. Su historial se conserva.`);
      await cargar();
    } catch (e) { fallo = describir(e); }
    finally { archivando = false; }
  }

  function inicial(nombre) {
    return String(nombre || 'E').trim().charAt(0).toLocaleUpperCase('es');
  }

  function fechaLegible(valor) {
    const fecha = new Date(valor);
    if (Number.isNaN(fecha.getTime())) return 'Fecha no disponible';
    return new Intl.DateTimeFormat('es-CO', {
      day: 'numeric', month: 'long', year: 'numeric'
    }).format(fecha);
  }
</script>

<section class="clases">
  <CabeceraDeRuta titulo="Mis clases" icono="clases" insignia="Comunidad Académica" notaGrande>
    {#snippet accion()}
      <!-- `<span>` envolvente y no `class` en `<Boton>`: comprobado en el
           navegador el 2026-08-22 que `Boton.svelte` pasa `class` por
           `...resto` DESPUÉS de su propio `class="boton {variante}"`, así
           que un `class` aquí lo REEMPLAZA entero en vez de sumarse —el
           botón se quedaba sin ningún estilo de `Boton.svelte`—. El
           selector de abajo apunta al `<svg>` por descendencia en vez de
           necesitar tocar la clase del botón. -->
      <span class="disparador-crear">
        <Boton onclick={() => (creando = true)}>
          <Icono nombre="nueva" medida={14} />
          <span>Crear clase</span>
        </Boton>
      </span>
    {/snippet}
    {#snippet nota()}
      Una clase agrupa estudiantes para acotar lo que ves. <strong>No hay
      tareas, calificaciones, entregas, calendario ni mensajería.</strong>
    {/snippet}
  </CabeceraDeRuta>

  {#if fallo}
    <Degradacion respuesta={fallo} alReintentar={cargar} />
  {/if}

  <div class="paneles">
    <section class="panel-lista" aria-label="Tus clases">
      <div class="cabecera-panel">
        <Icono nombre="grupo" medida={16} />
        <h2>Tus clases</h2>
        {#if pendientes.length}
          <span class="alerta-total" aria-label={`${pendientes.length} solicitudes nuevas`}>
            <Icono nombre="historial" medida={13} />
            {pendientes.length}
          </span>
        {/if}
        <span class="contador-badge">{clases.length}</span>
      </div>

      {#if cargandoClases && !clases.length}
        <CargadorCubo mensaje="Cargando clases…" pantallaCompleta />
      {:else if clases.length}
        <ul class="lista">
          {#each clases as c (c.id)}
            <li>
              <button type="button" class="fila" class:activa={abierta?.id === c.id}
                      aria-current={abierta?.id === c.id ? 'true' : undefined}
                      onclick={() => abrir(c)}>
                <span class="encabezado-fila">
                  <span class="nombre">{c.nombre}</span>
                  {#if pendientesDe(c.id)}
                    <span class="alerta-clase"
                          aria-label={`${pendientesDe(c.id)} solicitudes pendientes`}>
                      <Icono nombre="historial" medida={12} />
                      {pendientesDe(c.id)}
                    </span>
                  {/if}
                </span>
                <span class="cuantos">
                  {c.integrantes ?? 0} {(c.integrantes ?? 0) === 1 ? 'matriculado' : 'matriculados'}
                </span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <div class="estado-vacio">
          <EstadoVacio icono="clases" titulo="Todavía no has creado ninguna"
                       texto="Usa «Crear clase» arriba para conseguir tu primer código."
                       tono="invitacion" />
        </div>
      {/if}
    </section>

    <section class="panel-detalle" aria-live="polite">
      {#if abierta}
        <div class="cabecera-detalle">
          <div class="titulo-detalle">
            <Icono nombre="clase" medida={18} />
            {#if editandoNombre}
              <input class="editar-nombre" aria-label="Nuevo nombre de la clase"
                bind:this={campoNombre} bind:value={nombreEditado} onkeydown={alTeclaNombre}
                maxlength="120" disabled={guardandoNombre} />
              <button type="button" class="accion-nombre" aria-label="Guardar nombre"
                onclick={guardarNombre} disabled={!nombreEditado.trim() || guardandoNombre}>
                <Icono nombre="check" medida={15} />
              </button>
              <button type="button" class="accion-nombre" aria-label="Cancelar edición"
                onclick={cancelarEdicionDeNombre} disabled={guardandoNombre}>
                <Icono nombre="cerrar" medida={15} />
              </button>
            {:else}
              <h2>{abierta.nombre}</h2>
              <button use:ayudaContextual type="button" class="accion-nombre" aria-label="Editar nombre de la clase"
                title="Editar nombre" onclick={empezarEdicionDeNombre}>
                <Icono nombre="lapiz" medida={16} />
              </button>
            {/if}
          </div>
          <CodigoDeClase codigo={abierta.codigo} alRegenerar={regenerar} />
        </div>
        <div class="administrar-clase">
          <button type="button" onclick={() => { motivoArchivo = 'Clase creada para pruebas'; confirmandoArchivo = true; }}>
            Eliminar clase
          </button>
        </div>
        <div class="selector-detalle" role="tablist" aria-label="Contenido de la clase">
          <button type="button" role="tab" aria-selected={seccion === 'estudiantes'}
                  class:activo={seccion === 'estudiantes'} onclick={() => (seccion = 'estudiantes')}>
            <Icono nombre="estudiante" medida={15} /> Estudiantes
          </button>
          <button type="button" role="tab" aria-selected={seccion === 'solicitudes'}
                  class:activo={seccion === 'solicitudes'} onclick={() => (seccion = 'solicitudes')}>
            <Icono nombre="historial" medida={15} /> Solicitudes
            {#if pendientesDe(abierta.id)}
              <span class="alerta-pestana" aria-label={`${pendientesDe(abierta.id)} pendientes`}>
                {pendientesDe(abierta.id)}
              </span>
            {/if}
          </button>
        </div>
        {#if seccion === 'estudiantes'}
        <div class="matriculados" role="tabpanel" aria-labelledby="titulo-matriculados">
          <div class="encabezado-matriculados">
            <div>
              <h3 id="titulo-matriculados">Estudiantes matriculados</h3>
              <p>{integrantes.length} {integrantes.length === 1 ? 'persona' : 'personas'} en {abierta.nombre}</p>
            </div>
          </div>
          {#if integrantes.length}
            <ul class="lista-matriculados">
              <!-- La API vigente entrega `identificador`, pero los hilos
                   creados antes de esa ampliacion del contrato no lo traen.
                   Una lista sin clave conserva ambas filas y evita que dos
                   `undefined` aborten todo el render con each_key_duplicate. -->
              {#each integrantes as integrante}
                <li class="fila-estudiante">
                  <!-- Un `<button>` de verdad y no un `<div>` con `onclick`:
                       llega por tabulación, responde a Intro y Espacio, y el
                       lector de pantalla lo anuncia como acción. Sin
                       `identificador` —hilos anteriores a esa ampliación del
                       contrato— la fila se pinta igual pero no ofrece la
                       ficha, porque el servidor no podría resolverla. -->
                  <button type="button" class="tarjeta-estudiante"
                          disabled={!integrante.identificador}
                          onclick={() => abrirFicha(integrante)}>
                  <span class="avatar-estudiante" aria-hidden="true">
                    <span>{inicial(integrante.nombre)}</span>
                    {#if integrante.tiene_foto && integrante.identificador}
                      <img
                        src={api.fotoDeIntegrante(abierta.id, integrante.identificador)}
                        alt=""
                        onerror={(evento) => evento.currentTarget.remove()}
                      />
                    {/if}
                  </span>
                  <span class="identidad-estudiante">
                    <strong>{integrante.nombre}</strong>
                    {#if integrante.facultad || integrante.programa || integrante.semestre}
                      <span class="datos-academicos">
                        {integrante.facultad || 'Facultad pendiente'}
                        {#if integrante.programa} · {integrante.programa}{/if}
                        {#if integrante.semestre} · semestre {integrante.semestre}{/if}
                      </span>
                    {/if}
                    <span>
                      Se unió el <time datetime={integrante.desde}>{fechaLegible(integrante.desde)}</time>
                    </span>
                  </span>
                  <span class="estado-matricula"><Icono nombre="check" medida={12} /> Matriculado</span>
                  {#if integrante.identificador}
                    <span class="ir-a-ficha" aria-hidden="true"><Icono nombre="flecha-der" medida={14} /></span>
                  {/if}
                  </button>
                  {#if integrante.identificador}
                    <button type="button" class="retirar-estudiante"
                      aria-label={`Retirar a ${integrante.nombre || 'esta persona'} de ${abierta.nombre}`}
                      onclick={() => prepararRetiro(integrante)}>Retirar</button>
                  {/if}
                </li>
              {/each}
            </ul>
          {:else}
            <div class="estado-vacio lista-vacia">
              <EstadoVacio icono="grupo" titulo="Aún no hay estudiantes"
                texto="Comparte el código de la clase para que puedan matricularse." tono="invitacion" />
            </div>
          {/if}
        </div>
        {:else}
          <div role="tabpanel" class="panel-solicitudes">
            <SolicitudesDeMatricula clase={abierta.id} titulo={`Solicitudes para ${abierta.nombre}`}
              alCambiar={refrescarDespuesDeResolver} alActualizar={(nuevas) => solicitudes = nuevas} />
          </div>
        {/if}
      {:else if clases.length}
        <!-- Ninguna clase autoseleccionada a propósito, desde 2026-08-22:
             antes `cargar()` abría la primera de la lista sola, y se pidió
             que el panel empezara vacío hasta un clic explícito. -->
        <div class="estado-vacio">
          <EstadoVacio icono="clase" titulo="Selecciona una clase"
                       texto="Elige una de la lista para ver su código y sus estudiantes matriculados."
                       tono="invitacion" />
        </div>
      {:else}
        <div class="estado-vacio">
          <EstadoVacio icono="clase" titulo="Crea tu primera clase"
                       texto="Usa «Crear clase» arriba a la derecha para conseguir un código y compartirlo."
                       tono="invitacion" />
        </div>
      {/if}
    </section>
  </div>
</section>

<Dialogo bind:abierto={creando} tipo="confirmar" titulo="¿Crear una clase?">
  <!--
    `Dialogo.svelte` pinta `children` y `acciones` en dos contenedores
    HERMANOS, no anidados —`.cuerpo` y `.acciones`—, así que el botón real
    de «Crear clase» no puede ser descendiente de este `<form>`. En vez de
    un botón oculto para que Intro dispare el envío —lo que se intentó
    primero, y chocaba con la regla de accesibilidad de
    `estilos/base.css` que impone 24×24 mínimo a todo botón, así que
    «ocultarlo» a 1px dejaba un cuadro clipeado visible, encontrado en el
    navegador el 2026-08-22—, se usa el atributo `form` de HTML: asocia el
    botón de `acciones` con ESTE formulario por id, sin necesitar ningún
    elemento de más. Intro en el campo y clic en el botón pasan por el
    MISMO evento `submit`.
  -->
  <form id="form-crear-clase" onsubmit={(e) => { e.preventDefault(); crear(); }}>
    <p class="pista-formulario">
      Le da un nombre a un grupo de estudiantes y genera un código para
      que se matriculen.
    </p>
    <Campo etiqueta="Nombre de una clase nueva" bind:valor={nombreNuevo}
           ayuda="Por ejemplo: Cálculo Diferencial · grupo 2." />
  </form>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (creando = false)}>Cancelar</Boton>
    <Boton tipo="submit" form="form-crear-clase" deshabilitado={!nombreNuevo.trim()}>
      Crear clase
    </Boton>
  {/snippet}
</Dialogo>

<Dialogo bind:abierto={confirmandoArchivo} tipo="eliminar" titulo="¿Archivar esta clase?" bloqueado={archivando} ancho="34rem">
  <p class="pista-formulario">
    <strong>{abierta?.nombre || 'Esta clase'}</strong> dejará de aparecer en los paneles y en los KPI.
    Su historial de matrículas, solicitudes y conversaciones seguirá disponible para auditoría.
    Las solicitudes pendientes se cancelarán.
    Las matrículas vigentes se cerrarán y los estudiantes podrán solicitar otra clase.
  </p>
  <label class="motivo-retiro">Motivo
    <textarea bind:value={motivoArchivo} minlength="5" maxlength="240" rows="3"
      placeholder="Por ejemplo: clase creada para pruebas"></textarea>
  </label>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (confirmandoArchivo = false)} deshabilitado={archivando}>Cancelar</Boton>
    <Boton onclick={archivarClase} deshabilitado={archivando || motivoArchivo.trim().length < 5}>
      {archivando ? 'Retirando…' : 'Eliminar de las vistas'}
    </Boton>
  {/snippet}
</Dialogo>

<Dialogo bind:abierto={confirmandoRetiro} tipo="eliminar" titulo="¿Retirar estudiante de la clase?" bloqueado={retirando} ancho="34rem">
  <p class="pista-formulario">
    {integranteARetirar?.nombre || 'Esta persona'} dejará de pertenecer a
    <strong>{abierta?.nombre || 'la clase'}</strong>. No se elimina su cuenta,
    sus conversaciones ni el historial de matrícula.
  </p>
  <label class="motivo-retiro">Motivo del retiro
    <textarea bind:value={motivoRetiro} minlength="5" maxlength="240" rows="3"
      placeholder="Por ejemplo: ingresó a este grupo por error"></textarea>
  </label>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (confirmandoRetiro = false)} deshabilitado={retirando}>Cancelar</Boton>
    <Boton onclick={retirarIntegrante} deshabilitado={retirando || motivoRetiro.trim().length < 5}>
      {retirando ? 'Retirando…' : 'Confirmar retiro'}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  .clases {
    flex: 1;
    min-block-size: 0;
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    padding: var(--espacio-lg) var(--espacio-lg) 0;
    max-inline-size: min(84rem, 100%);
    margin-inline: auto;
    inline-size: 100%;
    overflow: hidden;
    animation: entrarVista 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  }

  @keyframes entrarVista {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* `display: contents`: el `<span>` no debe alterar el `flex` de la fila
     de cabecera que `CabeceraDeRuta.svelte` ya arma —el `<Boton>` de dentro
     sigue actuando como si fuera hijo directo de esa fila, a efectos de
     layout—. Solo existe para poder seleccionar su `<svg>` sin tocar la
     `class` de `Boton.svelte`, que `...resto` reemplazaría entera en vez de
     sumarla. Mismo giro que `comun/armazon/CarrilHistorial.svelte::.nueva`
     al pasar el mouse. */
  .disparador-crear { display: contents; }
  .administrar-clase { display: flex; justify-content: flex-end; margin-block: .35rem .65rem; }
  .administrar-clase button { min-block-size: 2.4rem; padding: .45rem .75rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-secondary); font: inherit; font-weight: 700; cursor: pointer; }
  .administrar-clase button:hover { border-color: var(--accent-main); color: var(--accent-main); }

  .disparador-crear :global(svg) {
    transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .disparador-crear:hover :global(svg) {
    transform: rotate(90deg) scale(1.15);
  }

  /* El área de trabajo: dos paneles con scroll propio, y la página misma
     no se desplaza — `.clases` ya recibe `flex: 1` de `<main>` con
     `overflow: hidden`, y este es el único hijo que se lleva el resto de
     la altura. */
  .paneles {
    flex: 1;
    min-block-size: 0;
    display: flex;
    gap: var(--espacio-lg);
    padding-block-end: var(--espacio-lg);
    overflow: hidden;
  }

  .panel-lista,
  .panel-detalle {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    min-block-size: 0;
    overflow-y: auto;
    padding: var(--espacio-lg);
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
  }

  .panel-lista {
    inline-size: 20rem;
    flex-shrink: 0;
  }

  .panel-detalle { flex: 1; min-inline-size: 0; }

  .cabecera-panel {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--ink-secondary);
  }

  .cabecera-panel h2 {
    margin: 0;
    font-size: var(--texto-md);
    font-weight: 600;
    color: var(--ink-primary);
    flex: 1;
  }

  .contador-badge {
    padding: 2px 8px;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-pill, 9999px);
    font-size: var(--texto-xs);
    font-weight: 700;
    color: var(--ink-primary);
  }

  .alerta-total,
  .alerta-clase,
  .alerta-pestana {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    gap: .25rem;
    min-inline-size: 1.55rem;
    min-block-size: 1.55rem;
    padding-inline: .42rem;
    border: 1px solid var(--accent-main);
    border-radius: var(--radius-pill, 9999px);
    background: var(--accent-surface);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 800;
    line-height: 1;
  }

  .alerta-total { animation: llegadaSolicitud .35s cubic-bezier(.34, 1.56, .64, 1); }
  .alerta-clase { min-inline-size: 1.4rem; min-block-size: 1.4rem; padding-inline: .35rem; }
  .alerta-pestana { min-inline-size: 1.35rem; min-block-size: 1.35rem; padding-inline: .32rem; }

  @keyframes llegadaSolicitud {
    from { opacity: 0; transform: scale(.72); }
    to { opacity: 1; transform: scale(1); }
  }

  .lista { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 0.5rem; }

  .fila {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.15rem;
    inline-size: 100%;
    padding: 0.65em 0.9em;
    background: var(--surface-paper);
    /* Cada fila es un BOTÓN —`font: inherit`, `text-align: start`— y no una
       tarjeta: su borde delimita un control y `1.4.11` le pide 3.0. */
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    color: var(--ink-primary);
    font: inherit;
    text-align: start;
    transition: var(--transition);
  }

  .fila:hover { background: var(--surface-canvas); border-color: var(--trazo); transform: translateX(2px); }

  .fila.activa {
    border: 1.5px solid var(--accent-main);
    color: var(--accent-main);
    font-weight: 600;
    box-shadow: var(--shadow-soft);
  }

  .fila.activa .nombre { color: var(--accent-main); }

  .encabezado-fila {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .55rem;
    inline-size: 100%;
  }

  .nombre { font-size: var(--texto-sm); font-weight: 500; }

  .cuantos { font-size: var(--texto-xs); color: var(--ink-tertiary); white-space: nowrap; }

  .cabecera-detalle {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
  }


  .titulo-detalle { display: flex; align-items: center; gap: 8px; color: var(--ink-secondary); }

  .titulo-detalle h2 { margin: 0; font-size: var(--texto-md); font-weight: 600; color: var(--ink-primary); }
  .editar-nombre { min-inline-size: min(18rem, 45vw); padding: .42rem .55rem; border: 1px solid var(--accent-main); border-radius: var(--radius-xs); background: var(--surface-paper); color: var(--ink-primary); font: inherit; font-weight: 600; }
  .accion-nombre { display: grid; place-items: center; inline-size: 30px; block-size: 30px; padding: 0; border: 1px solid transparent; border-radius: 50%; background: transparent; color: var(--ink-secondary); cursor: pointer; transition: var(--transition-fast); }
  .accion-nombre:hover:not(:disabled), .accion-nombre:focus-visible { border-color: var(--trazo); background: var(--surface-paper); color: var(--accent-main); }

  .selector-detalle {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: .35rem;
    padding: .3rem;
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    background: var(--surface-canvas);
  }

  .selector-detalle button {
    display: inline-flex;
    min-block-size: 40px;
    align-items: center;
    justify-content: center;
    gap: .45rem;
    border: 1px solid transparent;
    border-radius: calc(var(--radius-sm) - 2px);
    background: transparent;
    color: var(--ink-secondary);
    font: inherit;
    font-size: var(--texto-sm);
    font-weight: 600;
  }

  .selector-detalle button:hover { color: var(--ink-primary); }
  .selector-detalle button.activo { border-color: var(--trazo); background: var(--surface-paper); color: var(--accent-main); box-shadow: var(--shadow-soft); }
  .panel-solicitudes { min-block-size: 0; }

  .matriculados { display: flex; flex-direction: column; gap: var(--espacio-md); }
  .encabezado-matriculados { display: flex; align-items: center; justify-content: space-between; border-block-end: 1px solid var(--trazo-suave); padding-block-end: .65rem; }
  .encabezado-matriculados h3 { margin: 0; color: var(--ink-primary); font-size: var(--texto-md); }
  .encabezado-matriculados p { margin: .2rem 0 0; color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .lista-matriculados { display: grid; gap: .65rem; margin: 0; padding: 0; list-style: none; }
  .fila-estudiante { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: .5rem; }
  /* Desde la Fase 7 la tarjeta es un `<button>`: se le quita el aspecto de
     control nativo y se le devuelve el de tarjeta, sin cambiar su composición.
     `text-align: start` y `font: inherit` son los dos que el navegador impone
     y que, sin retirarlos, centrarían el nombre y lo pintarían con la fuente
     del sistema. */
  .tarjeta-estudiante { inline-size: 100%; display: grid; grid-template-columns: 48px minmax(0, 1fr) auto auto; align-items: center; gap: .85rem; min-block-size: 68px; padding: .7rem .85rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); box-shadow: var(--shadow-soft); font: inherit; text-align: start; cursor: pointer; transition: var(--transition-fast); }
  .tarjeta-estudiante:hover:not(:disabled) { border-color: var(--accent-main); background: var(--accent-surface); }
  .tarjeta-estudiante:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 2px; }
  /* Una matrícula sin identificador —hilos anteriores a esa ampliación del
     contrato— se sigue viendo, pero no promete una ficha que el servidor no
     podría resolver. */
  .tarjeta-estudiante:disabled { cursor: default; }
  .ir-a-ficha { display: inline-flex; color: var(--ink-tertiary); transition: var(--transition-fast); }
  .tarjeta-estudiante:hover .ir-a-ficha { color: var(--accent-main); transform: translateX(2px); }
  .avatar-estudiante { position: relative; display: grid; place-items: center; inline-size: 46px; block-size: 46px; overflow: hidden; border: 2px solid var(--accent-main); border-radius: 50%; background: var(--accent-surface); color: var(--accent-main); font-weight: 800; }
  .avatar-estudiante img { position: absolute; inset: 0; inline-size: 100%; block-size: 100%; object-fit: cover; }
  .identidad-estudiante { display: flex; min-inline-size: 0; flex-direction: column; gap: .18rem; }
  .identidad-estudiante strong { overflow: hidden; color: var(--ink-primary); text-overflow: ellipsis; white-space: nowrap; }
  .identidad-estudiante > span { color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .identidad-estudiante .datos-academicos { color: var(--ink-secondary); overflow-wrap: anywhere; }
  .estado-matricula { display: inline-flex; align-items: center; gap: .3rem; padding: .3rem .55rem; border-radius: var(--radius-pill, 9999px); background: var(--semantic-success-bg); color: var(--semantic-success); font-size: var(--texto-xs); font-weight: 700; }
  .retirar-estudiante { min-block-size: 40px; padding: .45rem .65rem; border: 1px solid var(--semantic-error); border-radius: var(--radius-sm); background: transparent; color: var(--semantic-error); font: inherit; font-size: var(--texto-xs); font-weight: 750; cursor: pointer; }
  .retirar-estudiante:hover { background: var(--semantic-error-bg); }
  .retirar-estudiante:focus-visible { outline: 2px solid var(--semantic-error); outline-offset: 2px; }
  .motivo-retiro { display: grid; gap: .35rem; color: var(--ink-primary); font-size: var(--texto-sm); font-weight: 700; }
  .motivo-retiro textarea { inline-size: 100%; padding: .65rem; border: 1px solid var(--trazo); border-radius: var(--radius-sm); background: var(--surface-panel); color: var(--ink-primary); font: inherit; font-weight: 400; resize: vertical; }
  .lista-vacia { min-block-size: 14rem; }

  .pista-formulario {
    margin: 0 0 var(--espacio-md);
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
    line-height: 1.45;
  }

  /* El contenido llamativo —círculo de icono con rebote, tarjeta de acento
     punteada— se extrajo a `docente/piezas/EstadoVacio.svelte` el
     2026-08-22, junto con los mismos estados de `ColaDeSupervision.svelte`
     y `FichaDeEstudiante.svelte` (con otro tono cada uno). Este wrapper
     solo centra `<EstadoVacio>` dentro del panel disponible. */
  .estado-vacio {
    flex: 1;
    min-block-size: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--espacio-xl) var(--espacio-lg);
  }

  /* Por debajo de `--corte-tableta` (48rem) los dos paneles no caben lado a
     lado: se apilan y el hueco entero desplaza junto, en vez de que cada
     panel scrollee por separado — dos barras de scroll finitas en una
     pantalla de teléfono son más difíciles de usar que una sola. */
  @media (max-width: 48rem) {
    .clases { overflow-y: auto; }
    .paneles { flex-direction: column; overflow: visible; }
    .panel-lista { inline-size: 100%; overflow-y: visible; }
    .panel-detalle { overflow-y: visible; }
    .tarjeta-estudiante { grid-template-columns: 44px minmax(0, 1fr); }
    .fila-estudiante { grid-template-columns: 1fr; }
    .retirar-estudiante { justify-self: end; }
    .estado-matricula { grid-column: 2; justify-self: start; }
    /* La tarjeta entera es el área táctil en teléfono; la flecha sólo
       repetiría lo que el toque ya hace y ocuparía una columna que no sobra. */
    .ir-a-ficha { display: none; }
  }

  /* §14 · quien pidió menos movimiento no recibe el desplazamiento de la
     flecha ni el atenuado de la tarjeta. El cambio de color se conserva:
     es la señal de que el control responde, no una animación. */
  @media (prefers-reduced-motion: reduce) {
    .tarjeta-estudiante,
    .ir-a-ficha { transition: none; }
    .tarjeta-estudiante:hover .ir-a-ficha { transform: none; }
    .alerta-total { animation: none; }
  }
</style>
