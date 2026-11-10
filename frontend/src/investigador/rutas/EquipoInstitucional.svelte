<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import CabeceraDeRuta from '../../docente/piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../../docente/piezas/PantallaDesplazable.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import { CORREO_INSTITUCIONAL } from '../../nucleo/configuracion/institucion.js';
  import Boton from '../../comun/base/Boton.svelte';
  import * as api from '../../nucleo/api/equipo.js';
  import { FACULTADES_ADMITIDAS } from '../../nucleo/configuracion/programas.js';
  import { describir } from '../../nucleo/errores/degradacion.js';

  let buscar = $state('');
  let pertenencia = $state('todas');
  let claseFiltrada = $state('');
  let clasesDisponibles = $state([]);
  let datos = $state([]);
  let actorPropietario = $state(false);
  let cargando = $state(true);
  let fallo = $state(null);
  let actuando = $state('');
  let aviso = $state('');
  let confirmacion = $state(null);
  let dialogoAbierto = $state(false);
  let invitaciones = $state([]);
  let correoInvitado = $state('');
  let rolInvitado = $state('docente');
  let cargandoInvitaciones = $state(true);
  let temporizador;

  async function cargar() {
    cargando = true;
    fallo = null;
    try {
      const respuesta = await api.listar(buscar, { pertenencia, clase: claseFiltrada });
      datos = respuesta.personas ?? [];
      if (!buscar && pertenencia === 'todas' && !claseFiltrada) {
        const opciones = new Map();
        for (const persona of datos) {
          for (const clase of persona.clases ?? []) opciones.set(clase.id, clase.nombre);
        }
        clasesDisponibles = [...opciones].map(([id, nombre]) => ({ id, nombre }))
          .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
      }
      actorPropietario = Boolean(respuesta.actor_propietario);
    } catch (error) {
      fallo = describir(error);
    } finally {
      cargando = false;
    }
  }

  async function cargarInvitaciones() {
    cargandoInvitaciones = true;
    try {
      const respuesta = await api.listarInvitaciones();
      invitaciones = respuesta.invitaciones ?? [];
    } catch (error) {
      fallo = describir(error);
    } finally {
      cargandoInvitaciones = false;
    }
  }

  $effect(() => {
    void buscar; void pertenencia; void claseFiltrada;
    clearTimeout(temporizador);
    temporizador = setTimeout(cargar, 250);
    return () => clearTimeout(temporizador);
  });

  $effect(() => { void cargarInvitaciones(); });

  async function crearInvitacion(correo, rol) {
    actuando = 'invitacion:nueva';
    aviso = '';
    fallo = null;
    try {
      const respuesta = await api.invitar(correo, rol);
      correoInvitado = '';
      aviso = respuesta.invitacion?.aviso_enviado
        ? 'La invitación quedó registrada y Resend confirmó el envío.'
        : 'La invitación quedó registrada, pero el canal no confirmó el envío. Puedes revocarla y volver a emitirla.';
      (respuesta.invitacion?.aviso_enviado ? toast.exito : toast.alerta)(aviso);
      await cargarInvitaciones();
    } catch (error) {
      fallo = describir(error);
    } finally {
      actuando = '';
    }
  }

  async function retirarInvitacion(invitacion) {
    actuando = `invitacion:${invitacion.id}`;
    aviso = '';
    fallo = null;
    try {
      await api.revocarInvitacion(invitacion.id);
      aviso = 'La invitación quedó revocada antes de usarse.';
      toast.error(aviso);
      await cargarInvitaciones();
    } catch (error) {
      fallo = describir(error);
    } finally {
      actuando = '';
    }
  }

  async function cambiarRol(persona, rol, conceder) {
    const clave = `${persona.identificador}:${rol}`;
    actuando = clave;
    aviso = '';
    fallo = null;
    try {
      conceder
        ? await api.asignarRol(persona.identificador, rol)
        : await api.revocarRol(persona.identificador, rol);
      aviso = 'El cambio quedó registrado. La cuenta verá su nuevo espacio en el próximo inicio de sesión.';
      (conceder ? toast.exito : toast.alerta)(aviso);
      await cargar();
    } catch (error) {
      fallo = describir(error);
    } finally {
      actuando = '';
    }
  }

  async function cambiarFacultad(persona, facultad) {
    actuando = `${persona.identificador}:facultad`;
    aviso = '';
    fallo = null;
    try {
      await api.asignarFacultad(persona.identificador, facultad);
      aviso = 'La facultad del perfil docente quedó actualizada y auditada.';
      toast.exito(aviso);
      await cargar();
    } catch (error) {
      fallo = describir(error);
    } finally {
      actuando = '';
    }
  }

  function tiene(persona, rol) { return persona.roles?.includes(rol); }

  function prepararRol(persona, rol, conceder) {
    confirmacion = { tipo: 'rol', persona, rol, conceder };
    dialogoAbierto = true;
  }

  function prepararFacultad(persona, facultad) {
    if (facultad === persona.facultad) return;
    confirmacion = { tipo: 'facultad', persona, facultad };
    dialogoAbierto = true;
  }

  async function confirmarCambio() {
    const pendiente = confirmacion;
    if (!pendiente) return;
    if (pendiente.tipo === 'rol') {
      await cambiarRol(pendiente.persona, pendiente.rol, pendiente.conceder);
    } else if (pendiente.tipo === 'facultad') {
      await cambiarFacultad(pendiente.persona, pendiente.facultad);
    } else if (pendiente.tipo === 'invitacion') {
      await crearInvitacion(pendiente.correo, pendiente.rol);
    } else {
      await retirarInvitacion(pendiente.invitacion);
    }
    if (!fallo) {
      dialogoAbierto = false;
      confirmacion = null;
    }
  }

  const tituloConfirmacion = $derived.by(() => {
    if (!confirmacion) return 'Confirmar cambio';
    if (confirmacion.tipo === 'invitacion') return '¿Enviar esta invitación?';
    if (confirmacion.tipo === 'revocar-invitacion') return '¿Revocar esta invitación?';
    if (confirmacion.tipo === 'facultad') return '¿Cambiar la facultad docente?';
    const funcion = confirmacion.rol === 'docente' ? 'docente' : 'investigador';
    return confirmacion.conceder ? `¿Asignar el rol de ${funcion}?` : `¿Retirar el rol de ${funcion}?`;
  });

  function prepararInvitacion() {
    const correo = correoInvitado.trim().toLocaleLowerCase('es');
    if (!correo) return;
    confirmacion = { tipo: 'invitacion', correo, rol: rolInvitado };
    dialogoAbierto = true;
  }

  function prepararRevocacion(invitacion) {
    confirmacion = { tipo: 'revocar-invitacion', invitacion };
    dialogoAbierto = true;
  }

  $effect(() => {
    if (!dialogoAbierto && !actuando) confirmacion = null;
  });
</script>

<PantallaDesplazable anchoMaximo="min(78rem, 100%)">
  <CabeceraDeRuta titulo="Equipo institucional" icono="equipo-institucional" insignia="Gobierno de accesos" ayuda="Sólo las cuentas propietarias pueden incorporar o retirar investigadores y no pueden retirarse desde esta interfaz. Cualquier investigador vigente puede administrar docentes y facultades. Cada cambio queda auditado.">
    {#snippet nota()}
      Asigna funciones profesionales a cuentas que ya iniciaron sesión una vez. Cada alta, baja y facultad queda auditada.
    {/snippet}
    {#snippet accion()}
      <label class="buscar"><span>Buscar por nombre o correo</span><input bind:value={buscar} placeholder="Nombre o correo institucional" /></label>
    {/snippet}
  </CabeceraDeRuta>


  <div class="filtros-pertenencia" aria-label="Filtrar cuentas por matrícula">
    <label><span>Vínculo con una clase</span>
      <select use:menuDesplegable={pertenencia} bind:value={pertenencia} onchange={() => { if (pertenencia === 'sin_clase') claseFiltrada = ''; }}>
        <option value="todas">Todas las cuentas</option>
        <option value="con_clase">Con matrícula vigente</option>
        <option value="sin_clase">Sin matrícula vigente</option>
        <option value="solicitud_pendiente">Con solicitud pendiente</option>
      </select>
    </label>
    <label><span>Clase concreta</span>
      <select use:menuDesplegable={claseFiltrada} bind:value={claseFiltrada} disabled={pertenencia === 'sin_clase'}
        onchange={() => { if (claseFiltrada) pertenencia = 'con_clase'; }}>
        <option value="">Todas las clases</option>
        {#each clasesDisponibles as clase (clase.id)}<option value={clase.id}>{clase.nombre}</option>{/each}
      </select>
    </label>
    <span class="total-filtrado" role="status">{datos.length} cuenta{datos.length === 1 ? '' : 's'} en esta vista</span>
  </div>

  {#if fallo}<Degradacion respuesta={fallo} alReintentar={cargar} />
  {:else if cargando && !datos.length}<CargadorCubo mensaje="Consultando el directorio…" />
  {:else}
    <section class="invitaciones" aria-labelledby="titulo-invitaciones">
      <div class="encabezado-invitaciones">
        <div><h2 id="titulo-invitaciones">Invitaciones previas <BotonAyudaTooltip texto="La persona acepta al iniciar sesión desde el enlace con la misma cuenta institucional. Las invitaciones vencen en siete días." /></h2></div>
        <form onsubmit={(evento) => { evento.preventDefault(); prepararInvitacion(); }}>
          <label><span>Correo institucional</span><input type="email" required bind:value={correoInvitado} placeholder={`nombre${CORREO_INSTITUCIONAL}`} /></label>
          <label><span>Función</span><select use:menuDesplegable={rolInvitado} bind:value={rolInvitado}><option value="docente">Docente</option>{#if actorPropietario}<option value="investigador_administrador">Investigador delegado</option>{/if}</select></label>
          <Boton tipo="submit" deshabilitado={Boolean(actuando)}>Preparar invitación</Boton>
        </form>
      </div>
      {#if cargandoInvitaciones}<CargadorCubo mensaje="Consultando invitaciones…" compacto />
      {:else if invitaciones.length}
        <div class="tabla-invitaciones">
          <table><thead><tr><th>Correo</th><th>Función</th><th>Estado</th><th>Vence</th><th><span class="status-sr">Acción</span></th></tr></thead>
            <tbody>{#each invitaciones as invitacion (invitacion.id)}<tr><td>{invitacion.correo}</td><td>{invitacion.rol === 'docente' ? 'Docente' : 'Investigador delegado'}</td><td><span class={`estado estado-${invitacion.estado}`}>{invitacion.estado}</span></td><td>{new Date(invitacion.expira_en).toLocaleString('es-CO')}</td><td>{#if invitacion.estado === 'pendiente'}<button type="button" disabled={Boolean(actuando) || (invitacion.rol !== 'docente' && !actorPropietario)} onclick={() => prepararRevocacion(invitacion)}>Revocar</button>{/if}</td></tr>{/each}</tbody>
          </table>
        </div>
      {:else}<p class="vacio">Todavía no hay invitaciones.</p>{/if}
    </section>
    <section class="directorio" aria-label="Cuentas institucionales registradas">
      {#each datos as persona (persona.identificador)}
        <article>
          <div class="identidad">
            <span class="avatar">
              <span aria-hidden="true">{persona.nombre?.charAt(0)?.toLocaleUpperCase('es') || 'U'}</span>
              {#if persona.tiene_foto}
                <img src={api.fotoDePersona(persona.identificador)} alt={`Foto de perfil de ${persona.nombre}`}
                     onerror={(evento) => (evento.currentTarget.hidden = true)} />
              {/if}
            </span>
            <div><h2>{persona.nombre}</h2><p>{persona.correo}</p></div>
            {#if persona.propietario}<span class="propietario">Propietario</span>{/if}
            {#if persona.es_cuenta_prueba}<span class="propietario">Cuenta de prueba</span>{/if}
          </div>
          <div class="funciones">
            <div>
              <span class="rotulo">Docencia</span>
              <button type="button" class:activo={tiene(persona, 'docente') || persona.es_docente}
                disabled={actuando || (persona.es_docente && !tiene(persona, 'docente'))}
                onclick={() => prepararRol(persona, 'docente', !tiene(persona, 'docente'))}>
                {tiene(persona, 'docente') ? 'Retirar rol' : persona.es_docente ? 'Docente por registro previo' : 'Asignar docente'}
              </button>
            </div>
            <div>
              <span class="rotulo">Investigación</span>
              <button type="button" class:activo={tiene(persona, 'investigador_administrador')}
                disabled={actuando || persona.propietario || !actorPropietario}
                onclick={() => prepararRol(persona, 'investigador_administrador', !tiene(persona, 'investigador_administrador'))}>
                {persona.propietario ? 'Inamovible' : !actorPropietario ? 'Reservado a propietarios' : tiene(persona, 'investigador_administrador') ? 'Retirar investigador' : 'Asignar investigador'}
              </button>
            </div>
            <label class="facultad"><span class="rotulo">Facultad docente</span>
              <select use:menuDesplegable={persona.facultad} value={persona.facultad} disabled={actuando || !persona.es_docente}
                onchange={(evento) => {
                  const nueva = evento.currentTarget.value;
                  evento.currentTarget.value = persona.facultad;
                  prepararFacultad(persona, nueva);
                }}>
                <option value="">Sin asignar</option>
                {#each FACULTADES_ADMITIDAS as opcion}<option value={opcion}>{opcion}</option>{/each}
              </select>
            </label>
          </div>
          <footer>
            {#if persona.clases?.length}
              <strong>Matriculado en:</strong> {persona.clases.map((clase) => clase.nombre).join(', ')}
            {:else}
              Sin matrícula vigente
            {/if}
            {#if persona.solicitudes_pendientes}
              <span> · {persona.solicitudes_pendientes} solicitud{persona.solicitudes_pendientes === 1 ? '' : 'es'} pendiente{persona.solicitudes_pendientes === 1 ? '' : 's'}</span>
            {/if}
            {#if persona.cursos}<span> · {persona.cursos} curso{persona.cursos === 1 ? '' : 's'} creado{persona.cursos === 1 ? '' : 's'}</span>{/if}
          </footer>
        </article>
      {:else}
        <p class="vacio">No hay cuentas que coincidan con la búsqueda. La persona debe iniciar sesión una vez antes de recibir un rol.</p>
      {/each}
    </section>
  {/if}
</PantallaDesplazable>

<Dialogo bind:abierto={dialogoAbierto} tipo={confirmacion?.tipo === 'revocar-invitacion' || (confirmacion?.tipo === 'rol' && !confirmacion?.conceder) ? 'eliminar' : 'confirmar'} titulo={tituloConfirmacion} bloqueado={Boolean(actuando)}>
  {#if confirmacion}
    {#if confirmacion.persona}
      <div class="resumen-confirmacion">
        <span class="avatar confirmacion-avatar">
          <span aria-hidden="true">{confirmacion.persona.nombre?.charAt(0)?.toLocaleUpperCase('es') || 'U'}</span>
          {#if confirmacion.persona.tiene_foto}
            <img src={api.fotoDePersona(confirmacion.persona.identificador)} alt=""
                 onerror={(evento) => (evento.currentTarget.hidden = true)} />
          {/if}
        </span>
        <div>
          <strong>{confirmacion.persona.nombre}</strong>
          <span>{confirmacion.persona.correo}</span>
        </div>
      </div>
    {:else if confirmacion.tipo === 'invitacion'}
      <div class="resumen-confirmacion">
        <span class="avatar confirmacion-avatar" aria-hidden="true">@</span>
        <div><strong>{confirmacion.correo}</strong><span>Invitación institucional previa</span></div>
      </div>
    {:else if confirmacion.tipo === 'revocar-invitacion'}
      <div class="resumen-confirmacion">
        <span class="avatar confirmacion-avatar" aria-hidden="true">×</span>
        <div><strong>{confirmacion.invitacion.correo}</strong><span>Enlace pendiente</span></div>
      </div>
    {/if}
    <p class="detalle-confirmacion">
      {#if confirmacion.tipo === 'invitacion'}
        Se registrará una invitación para <strong>{confirmacion.correo}</strong> como <strong>{confirmacion.rol === 'docente' ? 'docente' : 'investigador delegado'}</strong>. El correo incluirá un enlace de un solo uso y la operación quedará auditada.
      {:else if confirmacion.tipo === 'revocar-invitacion'}
        Se invalidará el enlace pendiente enviado a <strong>{confirmacion.invitacion.correo}</strong>. La invitación conservará su historia y no podrá aceptarse después.
      {:else if confirmacion.tipo === 'facultad'}
        La facultad cambiará de <strong>{confirmacion.persona.facultad || 'sin asignar'}</strong>
        a <strong>{confirmacion.facultad}</strong>.
      {:else if confirmacion.conceder}
        Esta cuenta recibirá acceso como <strong>{confirmacion.rol === 'docente' ? 'docente' : 'investigador'}</strong>
        a partir de su próximo inicio de sesión.
      {:else}
        Esta cuenta perderá su acceso como <strong>{confirmacion.rol === 'docente' ? 'docente' : 'investigador'}</strong>
        a partir de su próximo inicio de sesión.
      {/if}
    </p>
  {/if}
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (dialogoAbierto = false)} deshabilitado={Boolean(actuando)}>Cancelar</Boton>
    <Boton onclick={confirmarCambio} deshabilitado={Boolean(actuando)}>
      {actuando ? 'Aplicando…' : 'Confirmar cambio'}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  .buscar { display: grid; gap: .25rem; color: var(--ink-tertiary); font-size: var(--texto-xs); font-weight: 700; }
  .buscar input { min-inline-size: min(20rem, 70vw); min-block-size: 2.35rem; padding: .45rem .7rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); font: inherit; }
  .filtros-pertenencia { display: flex; flex-wrap: wrap; align-items: end; gap: .7rem; padding: .8rem 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); }
  .filtros-pertenencia label { display: grid; gap: .3rem; min-inline-size: min(100%, 13rem); color: var(--ink-tertiary); font-size: var(--texto-xs); font-weight: 700; }
  .filtros-pertenencia select { inline-size: 100%; min-block-size: 2.5rem; }
  .total-filtrado { margin-inline-start: auto; color: var(--ink-secondary); font-size: var(--texto-xs); font-weight: 700; }
  .aviso { margin: 0; padding: .7rem .9rem; border-radius: var(--radius-sm); background: var(--semantic-success-bg); color: var(--semantic-success); font-size: var(--texto-sm); }
  .cargando, .vacio { padding: 2rem; color: var(--ink-tertiary); text-align: center; }
  .directorio { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 29rem), 1fr)); gap: .8rem; }
  .invitaciones { display: grid; gap: .85rem; padding: 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); }
  .encabezado-invitaciones { display: grid; grid-template-columns: minmax(15rem, 1fr) minmax(22rem, 1.4fr); gap: 1rem; align-items: end; }
  .encabezado-invitaciones h2 { margin: 0; }
  .encabezado-invitaciones form { display: grid; grid-template-columns: 1.5fr 1fr auto; gap: .55rem; align-items: end; }
  .encabezado-invitaciones label { display: grid; gap: .25rem; color: var(--ink-tertiary); font-size: var(--texto-xs); font-weight: 700; }
  .encabezado-invitaciones input { min-block-size: 2.35rem; padding: .4rem .65rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-panel); color: var(--ink-primary); font: inherit; }
  .tabla-invitaciones { max-inline-size: 100%; overflow-x: auto; }
  table { inline-size: 100%; border-collapse: collapse; font-size: var(--texto-xs); }
  th, td { padding: .55rem; border-block-start: 1px solid var(--trazo-suave); text-align: start; vertical-align: middle; }
  th { color: var(--ink-tertiary); }
  .estado { display: inline-block; padding: .2rem .4rem; border-radius: 999px; background: var(--surface-panel); font-weight: 750; }
  .estado-aceptada { background: var(--semantic-success-bg); color: var(--semantic-success); }
  article { display: grid; gap: .9rem; padding: 1rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-md); background: var(--surface-paper); box-shadow: var(--shadow-soft); }
  .identidad { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: .7rem; min-inline-size: 0; }
  .avatar { position: relative; display: grid; place-items: center; inline-size: 2.6rem; block-size: 2.6rem; overflow: hidden; border: 1px solid var(--trazo-suave); border-radius: 50%; background: var(--accent-surface); color: var(--accent-main); font-weight: 800; }
  .avatar img { position: absolute; inset: 0; inline-size: 100%; block-size: 100%; object-fit: cover; }
  h2 { margin: 0; color: var(--ink-primary); font-size: var(--texto-md); }
  .identidad p { margin: .15rem 0 0; color: var(--ink-tertiary); font-size: var(--texto-xs); overflow-wrap: anywhere; }
  .propietario { padding: .25rem .45rem; border-radius: 999px; background: var(--accent-surface); color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; }
  .funciones { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .65rem; }
  .funciones > div, .facultad { display: grid; gap: .3rem; }
  .facultad { grid-column: 1 / -1; }
  .rotulo { color: var(--ink-tertiary); font-size: var(--texto-xs); font-weight: 750; }
  button, select { min-block-size: 2.35rem; padding: .4rem .65rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-panel); color: var(--ink-secondary); font: inherit; font-size: var(--texto-xs); }
  button { cursor: pointer; font-weight: 750; }
  button.activo { border-color: var(--accent-main); background: var(--accent-surface); color: var(--accent-main); }
  button:disabled, select:disabled { cursor: not-allowed; opacity: .6; }
  footer { padding-block-start: .65rem; border-block-start: 1px solid var(--trazo-suave); color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .resumen-confirmacion { display: flex; align-items: center; gap: .75rem; padding: .8rem; border-radius: var(--radius-md); background: var(--surface-panel); }
  .confirmacion-avatar { inline-size: 3rem; block-size: 3rem; flex: 0 0 3rem; }
  .resumen-confirmacion div { display: grid; min-inline-size: 0; }
  .resumen-confirmacion strong { color: var(--ink-primary); }
  .resumen-confirmacion div span { color: var(--ink-tertiary); font-size: var(--texto-xs); overflow-wrap: anywhere; }
  .detalle-confirmacion { margin: 1rem 0 0; max-inline-size: none; color: var(--ink-secondary); line-height: 1.55; }
  @media (max-width: 54rem) { .encabezado-invitaciones, .encabezado-invitaciones form { grid-template-columns: 1fr; } }
  @media (max-width: 34rem) { .funciones { grid-template-columns: 1fr; } .facultad { grid-column: auto; } .identidad { grid-template-columns: auto 1fr; } .propietario { grid-column: 2; justify-self: start; } }
</style>
