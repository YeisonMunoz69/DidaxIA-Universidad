<!--
DD-12 / EQ-033 · El estudiante solicita entrar con el código.

Escribir el código no cambia la matrícula: crea una solicitud que debe aprobar
el docente de la clase destino o un investigador. Sólo puede existir una clase
vigente y, durante un cambio pendiente, la actual se conserva.

EL CÓDIGO NO ES UNA CREDENCIAL, y esta pantalla no puede sugerir lo contrario.
Identifica una agrupación; no autentica a nadie. Por eso aquí no se pide
contraseña, no se habla de «acceso» y el fallo no dice «código incorrecto» como
si fuera un intento de entrar: dice que no hay ninguna clase con ese código, que
es lo que de verdad ocurrió.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
Origen de esta pieza: OE3-Implementacion/09-Aportes-de-la-Consulta-Docente.md

-->
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { onMount } from 'svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import Campo from '../../comun/base/Campo.svelte';
  import Icono from '../../comun/base/Icono.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import BloqueoAutenticacion from '../../comun/estado/BloqueoAutenticacion.svelte';
  import { CORREO_INSTITUCIONAL } from '../../nucleo/configuracion/institucion.js';
  import * as clases from '../../nucleo/api/clases.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { navegar } from '../../enrutado/navegar.js';

  let codigo = $state('');
  let mias = $state([]);
  let solicitudes = $state([]);
  let cargando = $state(true);
  let uniendo = $state(false);
  let fallo = $state(null);
  /** El código no existe. NO es un fallo de red, y no se pinta como tal. */
  let sinClase = $state('');
  let recien = $state(null);
  let aprobada = $state(null);
  let cancelando = $state(false);
  let activa = false, comprobando = false;
  const pendiente = $derived(
    solicitudes.find((solicitud) => solicitud.estado === 'pendiente') ?? null
  );
  const actual = $derived(mias[0] ?? null);

  async function cargar({ silencioso = false } = {}) {
    if (!sesion.autenticada) {
      if (!silencioso) cargando = false;
      return null;
    }
    if (!silencioso) cargando = true;
    if (!silencioso) fallo = null;
    try {
      const [claseActual, peticiones] = await Promise.all([
        clases.mias(), clases.solicitudes()
      ]);
      mias = claseActual ?? [];
      solicitudes = peticiones ?? [];
      return { mias, solicitudes };
    } catch (e) {
      if (!silencioso) fallo = describir(e);
      return null;
    } finally {
      if (!silencioso) cargando = false;
    }
  }

  async function actualizarEstado() {
    if (comprobando || !activa) return;
    comprobando = true;
    try {
      const esperaba = pendiente;
      const estado = await cargar({ silencioso: true });
      if (!activa || !estado || !esperaba) return;

      const siguePendiente = estado.solicitudes.some((solicitud) => solicitud.estado === 'pendiente');
      const claseVigente = estado.mias[0] ?? null;
      if (!siguePendiente && claseVigente?.id === esperaba.clase_destino?.id) {
        aprobada = claseVigente;
        recien = null;
        // La matrícula forma parte del acceso calculado del estudiante. Sin
        // refrescarlo, la pantalla ya enseñaba la clase aprobada pero la guarda
        // global continuaba creyendo que faltaba, hasta una recarga completa.
        await sesion.refrescarAcceso();
        if (activa) navegar('/consentimiento');
      }
    } finally { comprobando = false; }
  }

  async function unirme() {
    if (!codigo.trim()) return;
    uniendo = true;
    fallo = null;
    sinClase = '';
    recien = null;
    aprobada = null;
    try {
      recien = await clases.unirse(codigo.trim().toUpperCase());
      codigo = '';
      await cargar();
    } catch (e) {
      if (e?.estado === 404) {
        sinClase = 'No hay ninguna clase con ese código. Revísalo con tu docente.';
      } else if (e?.estado === 409) {
        sinClase = e?.cuerpo?.detalle || 'Ya tienes una solicitud pendiente. Cancélala antes de pedir otra clase.';
      } else {
        fallo = describir(e);
      }
    } finally {
      uniendo = false;
    }
  }

  async function cancelar() {
    if (!pendiente) return;
    cancelando = true;
    fallo = null;
    try {
      await clases.cancelarSolicitud(pendiente.id);
      recien = null;
      await cargar();
    } catch (e) {
      fallo = describir(e);
    } finally {
      cancelando = false;
    }
  }

  onMount(() => {
    activa = true;
    cargar();

    // La aprobación ocurre en la sesión del docente/investigador. Mientras
    // haya una petición pendiente se consulta cada cuatro segundos y, además,
    // al regresar a la pestaña. No se recarga la página ni se pierden el foco
    // o el texto que la persona estuviera escribiendo.
    const comprobarPendiente = () => {
      if (pendiente) actualizarEstado();
    };
    const alVolver = () => {
      if (!globalThis.document || globalThis.document.visibilityState === 'visible') {
        actualizarEstado();
      }
    };
    const intervalo = globalThis.setInterval?.(comprobarPendiente, 4000);
    globalThis.addEventListener?.('focus', alVolver);
    globalThis.document?.addEventListener?.('visibilitychange', alVolver);

    return () => {
      activa = false;
      if (intervalo !== undefined) globalThis.clearInterval?.(intervalo);
      globalThis.removeEventListener?.('focus', alVolver);
      globalThis.document?.removeEventListener?.('visibilitychange', alVolver);
    };
  });
</script>

<div class="unirse-desplazable">
<div class="vista-unirse">
  <header class="cabecera-unirse">
    <div class="insignia-modulo">
      <Icono nombre="clase" medida={15} />
      <span>Comunidad Académica</span>
    </div>
    <h1>Mi clase de Cálculo</h1>
    <p class="descripcion-intro">
      Puedes tener una sola clase vigente. Tu docente te dará el código y la
      clase destino deberá aprobar tu ingreso o cambio.
    </p>
  </header>

  {#if fallo}
    <Degradacion respuesta={fallo} alReintentar={cargar} />
  {/if}

  {#if !sesion.autenticada}
    <BloqueoAutenticacion icono="clase" titulo="Únete a tu grupo de clase">
      <p>
        Inicia sesión con tu cuenta institucional de <strong>{CORREO_INSTITUCIONAL}</strong> desde el botón del menú lateral para vincular tus tutorías con el grupo de tu docente.
      </p>
    </BloqueoAutenticacion>
  {:else}
  <div class="grid-principal">

    <!-- Tarjeta del formulario para unirse -->
    <section class="tarjeta-formulario">
      <div class="cabecera-tarjeta">
        <Icono nombre="ancla" medida={18} />
        <h2>{actual ? 'Solicitar cambio de clase' : 'Solicitar ingreso'}</h2>
      </div>

      <p class="pista-formulario">
        El código identifica el grupo, pero <strong>no te matricula de inmediato</strong>.
        Mientras esperas una aprobación conservarás tu clase actual, si ya tienes una.
      </p>

      <form class="formulario" onsubmit={(e) => { e.preventDefault(); unirme(); }}>
        <div class="campo-contenedor">
          <Campo
            etiqueta="Código alfanumérico"
            bind:valor={codigo}
            error={sinClase}
            ayuda="Ejemplo: K3PXQ7 (no distingue mayúsculas o minúsculas)"
            autocomplete="off"
            maxlength="6" />
        </div>

        <div class="fila-boton">
          <!-- Sin icono: el texto ya dice lo que hace en los dos estados,
               y el «check» en reposo se leía como un adorno suelto —«el
               churito»— más que como parte del botón. Mismo criterio que
               `docente/rutas/ContextoCurricular.svelte` y el modal de
               `MisClases.svelte`. -->
          <Boton tipo="submit" deshabilitado={uniendo || !codigo.trim() || Boolean(pendiente)}>
            {uniendo ? 'Enviando…' : actual ? 'Solicitar cambio' : 'Solicitar ingreso'}
          </Boton>
        </div>
      </form>

      {#if recien}
        <div class="aviso-exito" role="status">
          <Icono nombre="check" medida={16} />
          <div>
            <strong>Solicitud enviada</strong>
            <span><em>{recien.clase_destino?.nombre}</em> debe aprobarla antes de que cambie tu matrícula.</span>
          </div>
        </div>
      {/if}

      {#if aprobada}
        <div class="aviso-exito" role="status" aria-live="polite">
          <Icono nombre="check" medida={16} />
          <div>
            <strong>Ingreso aprobado</strong>
            <span>Ya perteneces a <em>{aprobada.nombre}</em>. Puedes continuar tu registro y usar el tutor cuando tus autorizaciones estén al día.</span>
          </div>
        </div>
      {/if}

      {#if pendiente}
        <div class="solicitud-pendiente" aria-live="polite">
          <div class="marca-pendiente" aria-hidden="true"><Icono nombre="historial" medida={18} /></div>
          <div class="detalle-pendiente">
            <strong>Esperando aprobación</strong>
            <span>{pendiente.clase_destino?.nombre}</span>
            {#if pendiente.clase_origen}
              <small>Sigues en {pendiente.clase_origen.nombre} hasta que se apruebe el cambio.</small>
            {:else}
              <small>Podrás continuar el registro cuando aprueben tu ingreso.</small>
            {/if}
          </div>
          <Boton variante="secundario" onclick={cancelar} deshabilitado={cancelando}>
            {cancelando ? 'Cancelando…' : 'Cancelar solicitud'}
          </Boton>
        </div>
      {/if}
    </section>

    <!-- Tarjeta de clases en las que está inscrito -->
    <section class="tarjeta-clases">
      <div class="cabecera-tarjeta">
        <Icono nombre="grupo" medida={18} />
        <h2>Clase vigente</h2>
        <span class="contador-badge">{actual ? '1' : '0'}</span>
      </div>

      {#if cargando}
        <CargadorCubo mensaje="Cargando tus clases inscritas…" />
      {:else if actual}
        <ul class="lista-clases">
            <li class="item-clase">
              <div class="icono-clase">
                <Icono nombre="clase" medida={18} />
              </div>
              <div class="info-clase">
                <span class="nombre-clase">{actual.nombre}</span>
                <span class="detalles-clase">
                  <Icono nombre="estudiante" medida={12} />
                  <span>Tu grupo actual de Cálculo</span>
                </span>
              </div>
              <span class="etiqueta-activa">Inscrito</span>
            </li>
        </ul>
        <div class="continuar-registro">
          <Boton variante="secundario" onclick={() => navegar('/consentimiento')}>
            Continuar mi registro
          </Boton>
        </div>
      {:else}
        <div class="estado-vacio">
          <div class="circulo-icono-vacio">
            <Icono nombre="clase" medida={24} />
          </div>
          <h3>Aún no perteneces a ninguna clase</h3>
          <p>
            {pendiente
              ? 'Tu solicitud está en revisión. Aquí aparecerá la clase cuando sea aprobada.'
              : 'Para completar el registro y usar el tutor necesitas enviar el código que genera tu docente.'}
          </p>
        </div>
      {/if}
    </section>

  </div>
  {/if}
</div>
</div>

<style>
  /* La tarjeta «inicia sesión para…» vive en `comun/estado/
     BloqueoAutenticacion.svelte` desde el 2026-08-22 — este archivo era
     una de las tres copias que la motivaron. */

  /*
    Bug real, mismo patrón que ya se encontró y corrigió en el árbol de
    docente (`ColaDeSupervision.svelte` y hermanas, 2026-08-22): esta
    sección nunca puso `overflow-y: auto` en ningún nivel, así que con
    veinte clases inscritas la lista se cortaba a media tarjeta —sin
    ninguna barra de scroll que lo delatara— dentro de `<main
    id="contenido">`, que trae `overflow: hidden` de `Aplicacion.svelte`.
    Confirmado en el navegador el 2026-08-22 con `getBoundingClientRect`.

    El scroll vive en `.unirse-desplazable`, a ancho completo, y no en
    `.vista-unirse`: mismo arreglo que
    `docente/rutas/ColaDeSupervision.svelte::.cola-desplazable` —ver su
    comentario— para que la barra de scroll quede pegada al borde real de
    la ventana.
  */
  .unirse-desplazable {
    flex: 1;
    min-block-size: 0;
    overflow-y: auto;
    inline-size: 100%;
  }

  .vista-unirse {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-lg);
    padding: var(--espacio-xl) var(--espacio-lg);
    /* `68rem` y no `52rem`: reportado que las tarjetas de esta pantalla
       «no ocupan mucho» espacio y que una lista de clases más larga no
       tendría mucho margen antes del scroll. El carril de estudiante
       sigue existiendo aquí —a diferencia del árbol de docente, no se
       quitó—, así que el ancho disponible es menor y el aumento es más
       moderado que en las pantallas de docente (52 → 68rem, no → 78rem). */
    max-inline-size: min(68rem, 100%);
    margin-inline: auto;
    animation: entrarVista 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  }

  @keyframes entrarVista {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .cabecera-unirse {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .insignia-modulo {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: var(--radius-pill, 9999px);
    background: var(--accent-surface);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 600;
    align-self: flex-start;
    border: 1px solid var(--accent-main);
  }

  h1 {
    margin: 0;
    font-size: var(--texto-xl);
    font-weight: 700;
    color: var(--ink-primary);
    line-height: 1.2;
  }

  .descripcion-intro {
    margin: 0;
    font-size: var(--texto-base);
    color: var(--ink-secondary);
    line-height: 1.5;
  }

  .grid-principal {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--espacio-lg);
  }

  @media (min-width: 48rem) {
    .grid-principal {
      grid-template-columns: 1fr 1fr;
      align-items: start;
    }
  }

  /* Tarjetas base con diseño papel y elevación suave */
  .tarjeta-formulario,
  .tarjeta-clases {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
    padding: var(--espacio-lg);
    background: var(--surface-panel);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-soft);
    transition: var(--transition);
  }

  .tarjeta-formulario:hover,
  .tarjeta-clases:hover {
    border-color: var(--trazo);
  }

  .cabecera-tarjeta {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--ink-secondary);
  }

  .cabecera-tarjeta h2 {
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

  .pista-formulario {
    margin: 0;
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
    line-height: 1.45;
  }

  .formulario {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-md);
  }

  .campo-contenedor {
    display: flex;
    flex-direction: column;
  }

  .fila-boton {
    display: flex;
    justify-content: flex-start;
  }

  .aviso-exito {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: var(--espacio-sm) var(--espacio-md);
    background: var(--semantic-success-bg);
    border: 1px solid var(--semantic-success);
    border-radius: var(--radius-sm);
    color: var(--semantic-success);
    font-size: var(--texto-xs);
    line-height: 1.4;
  }

  .aviso-exito strong {
    display: block;
    font-weight: 600;
  }

  .solicitud-pendiente {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: var(--espacio-sm);
    padding: var(--espacio-md);
    border: 1px solid var(--accent-main);
    border-radius: var(--radius-sm);
    background: var(--accent-surface);
  }

  .marca-pendiente {
    display: grid;
    place-items: center;
    inline-size: 38px;
    block-size: 38px;
    border-radius: 50%;
    background: var(--surface-paper);
    color: var(--accent-main);
  }

  .detalle-pendiente {
    display: flex;
    min-inline-size: 0;
    flex-direction: column;
    gap: 2px;
  }

  .detalle-pendiente strong,
  .detalle-pendiente span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .detalle-pendiente strong { color: var(--ink-primary); font-size: var(--texto-sm); }
  .detalle-pendiente span { color: var(--accent-main); font-size: var(--texto-sm); font-weight: 600; }
  .detalle-pendiente small { color: var(--ink-secondary); line-height: 1.35; }

  .continuar-registro { display: flex; justify-content: flex-end; }

  /*
    Lista de clases matriculadas · con tope y scroll propio.

    Sin esto, la lista crecía con el número de clases hasta empujar toda la
    tarjeta —y con ella la página entera, vía `.unirse-desplazable`— cada
    vez más abajo: reportado tras sembrar una cuenta con varias clases
    reales. `18rem` es lo que ocupan cuatro o cinco `.item-clase` —mismo
    criterio de tope que ya usa `estudiante/rutas/Conceptos.svelte::
    .lista-conceptos`—, y de ahí en adelante scrollea sola sin arrastrar el
    resto de la pantalla.
  */
  .lista-clases {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-xs);
    margin: 0;
    padding: 0;
    padding-inline-end: 2px;
    list-style: none;
    max-block-size: 18rem;
    overflow-y: auto;
  }

  .item-clase {
    display: flex;
    align-items: center;
    gap: var(--espacio-sm);
    padding: var(--espacio-sm) var(--espacio-md);
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-sm);
    transition: var(--transition);
  }

  .item-clase:hover {
    border-color: var(--accent-main);
    box-shadow: var(--shadow-soft);
    transform: translateY(-1px);
  }

  .icono-clase {
    display: flex;
    align-items: center;
    justify-content: center;
    inline-size: 34px;
    block-size: 34px;
    border-radius: var(--radius-xs);
    background: var(--accent-surface);
    color: var(--accent-main);
    flex-shrink: 0;
  }

  .info-clase {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    min-inline-size: 0;
  }

  .nombre-clase {
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .detalles-clase {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  .etiqueta-activa {
    padding: 2px 7px;
    border-radius: var(--radius-xs);
    background: var(--semantic-success-bg);
    color: var(--semantic-success);
    font-size: var(--texto-xs);
    font-weight: 600;
  }

  /* Estados de carga y vacío */

  .estado-vacio {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 8px;
    padding: var(--espacio-xl) var(--espacio-md);
  }

  .circulo-icono-vacio {
    display: flex;
    align-items: center;
    justify-content: center;
    inline-size: 48px;
    block-size: 48px;
    border-radius: 50%;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    color: var(--ink-tertiary);
    margin-block-end: 4px;
  }

  .estado-vacio h3 {
    margin: 0;
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-primary);
  }

  .estado-vacio p {
    margin: 0;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    line-height: 1.4;
    max-inline-size: 18rem;
  }

  @media (max-width: 38rem) {
    .solicitud-pendiente { grid-template-columns: auto minmax(0, 1fr); }
    .solicitud-pendiente :global(.boton) { grid-column: 1 / -1; inline-size: 100%; }
  }
</style>
