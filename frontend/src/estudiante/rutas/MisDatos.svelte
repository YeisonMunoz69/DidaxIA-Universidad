<!--
Consulta, exportación y derechos del titular · `RU-06` / `RP-19` / `EQ-022`.

Es el canal que la Ley 1581 exige que exista y sea alcanzable, no una pantalla
de cortesía. Por eso se llega a ella **desde todos los estados de bloqueo**
—así lo declara la allowlist de `nucleo/sesion/acceso.js`—: quien rechazó,
revocó o pidió la eliminación es justo quien más necesita entrar aquí.

QUÉ CAMBIÓ EN C1
-----------------
1. **El estado de acceso se integra.** Antes esta pantalla enseñaba los campos
   de la sesión y nada más; quien llegaba bloqueado no sabía por qué. Ahora
   arriba está lo que el servidor calculó y qué autorizaciones lo sostienen.
2. **Revocar vive aquí**, que es el lugar comprensible: al lado de lo que el
   sistema guarda, no dentro del trámite por el que sólo se pasa al principio.
3. **El borrado inmediato se retiró.** `DELETE /api/datos-personales` ejecutaba
   la cascada al recibir la petición y responde 410 desde el hito R2. En su
   lugar está el trámite reversible de `EQ-022`, con su reautenticación, su
   frase, sus 24 horas y su cancelación.



-->
<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { ayudaContextual } from '../../comun/base/ayudaContextual.js';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import Icono from '../../comun/base/Icono.svelte';
  import Degradacion from '../../comun/estado/Degradacion.svelte';
  import BloqueoAutenticacion from '../../comun/estado/BloqueoAutenticacion.svelte';
  import ReportarProblema from '../../comun/rutas/ReportarProblema.svelte';
  import { CORREO_INSTITUCIONAL } from '../../nucleo/configuracion/institucion.js';
  import PanelDeDatosPersonales from '../piezas/PanelDeDatosPersonales.svelte';
  import PanelDeAutorizaciones from '../piezas/datos/PanelDeAutorizaciones.svelte';
  import SolicitudDeSupresion from '../piezas/datos/SolicitudDeSupresion.svelte';
  import * as datos from '../../nucleo/api/datos-personales.js';
  import * as onboarding from '../../nucleo/api/onboarding.js';
  import { describir, clasificar } from '../../nucleo/errores/degradacion.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { navegar } from '../../enrutado/navegar.js';

  let mios = $state(null);
  /** El estado vigente completo. Vive aquí, no en el estado compartido. */
  let estado = $state(null);
  let cargando = $state(true);
  let fallo = $state(null);
  /** `true` cuando el estado no se pudo leer por un 503. `EQ-024`. */
  let enMantenimiento = $state(false);
  /** La portada de la cuenta enseña primero a la persona, no los registros técnicos. */
  let seccion = $state('perfil');
  let fotoPerfil = $state(null);

  /**
   * Vuelve a leerlo todo.
   *
   * ⚠️ `silencioso` NO es cosmética. Tras revocar o cancelar, esta pantalla se
   * recarga; si además volviera al estado «cargando», el `{#if}` desmontaría
   * `PanelDeAutorizaciones` y se llevaría por delante **el recibo que acababa
   * de devolver el servidor** —lo único que prueba el acto—. Se midió montando
   * el componente: la huella aparecía y desaparecía en el mismo cuadro.
   *
   * Sólo la primera carga enseña el indicador, que es cuando de verdad no hay
   * nada que mirar.
   */
  async function cargar({ silencioso = false } = {}) {
    if (!sesion.autenticada) {
      cargando = false;
      return;
    }
    if (!silencioso) cargando = true;
    fallo = null;
    enMantenimiento = false;
    try {
      // `allSettled`: que falle el estado de onboarding no puede impedir
      // consultar y exportar, que son derechos por sí mismos y viven en otra
      // ruta. Y al revés.
      const [datosPersonales, estadoVigente, foto] = await Promise.allSettled([
        datos.consultar(),
        onboarding.estado(),
        datos.consultarFoto()
      ]);

      if (datosPersonales.status === 'fulfilled') mios = datosPersonales.value;
      else fallo = describir(datosPersonales.reason);

      if (estadoVigente.status === 'fulfilled') {
        estado = estadoVigente.value;
        sesion.aplicarAcceso(estado.acceso);
      } else if (clasificar(estadoVigente.reason) === 'mantenimiento') {
        // No se pinta un estado en blanco ni «sin autorizaciones»: se dice que
        // no se pudo comprobar.
        estado = null;
        enMantenimiento = true;
      } else {
        estado = null;
      }

      if (foto.status === 'fulfilled') fotoPerfil = foto.value;
    } finally {
      cargando = false;
    }
  }

  async function llevarme() {
    if (!await confirmarAccion({ tipo:'descarga', titulo:'¿Descargar una copia de tus datos?',
      descripcion:'Se guardará un archivo JSON con los datos de tu cuenta y tu actividad autorizada en este dispositivo. Consérvalo en un lugar privado.', confirmar:'Descargar JSON' })) return;
    fallo = null;
    try {
      datos.descargar(await datos.exportar());
      toast.descarga('Descargando tu copia de datos en JSON.');
    } catch (e) {
      fallo = describir(e);
    }
  }

  async function guardarFoto(archivo) {
    await datos.guardarFoto(archivo);
    fotoPerfil = await datos.consultarFoto();
    globalThis.dispatchEvent?.(new CustomEvent('didaxia:foto-actualizada'));
  }

  async function retirarFoto() {
    await datos.retirarFoto();
    fotoPerfil = null;
    globalThis.dispatchEvent?.(new CustomEvent('didaxia:foto-actualizada'));
  }

  /*
   * ⚠️ `borrar()` Y `seguir()` SE RETIRARON EN C1, CON SU DIÁLOGO Y SU RECIBO.
   *
   * `borrar()` llamaba a `DELETE /api/datos-personales`, que ejecutaba la
   * cascada al recibir la petición y cerraba la sesión; el diálogo decía «se
   * borrará toda la información y no se puede deshacer» y el recibo decía «se
   * borró todo lo registrado». Bajo `EQ-022` las tres afirmaciones son falsas.
   * El trámite vive en `piezas/datos/SolicitudDeSupresion.svelte`.
   */

  $effect(() => {
    sesion.autenticada;
    cargar();
  });

  $effect(() => {
    const actual = fotoPerfil;
    return () => {
      if (actual) URL.revokeObjectURL(actual);
    };
  });
</script>

<section class="mis-datos-contenedor">
  <div class="mis-datos-tarjeta">

    <div class="fila-superior">
      <button use:ayudaContextual type="button" class="btn-volver-tutor" onclick={() => navegar('/')} title="Regresar a la conversación">
        <Icono nombre="volver" medida={15} />
        <span>Volver</span>
      </button>

      <a use:ayudaContextual
        class="insignia-seguridad"
        href="https://www.unimayor.edu.co/files/documentos/2025/planeacion-estrategica-politica-2025-politica-de-seguridad-y-privacidad-de-la-informacion-20260703152358.pdf"
        target="_blank"
        rel="noopener noreferrer"
        title="Abrir la Política de Tratamiento y Protección de Datos Personales de UNIMAYOR en otra pestaña">
        <Icono nombre="escudo" medida={14} />
        <span>DidaxIa · Ley 1581 y Control de Datos</span>
      </a>
    </div>

    <header class="encabezado">
      <h1>Mi cuenta</h1>
      <p class="subtitulo">
        Tu perfil, tus decisiones y el control de tu información en un solo lugar.
      </p>
    </header>

    {#if !sesion.autenticada}
      <BloqueoAutenticacion icono="datos" titulo="Gestión de Datos Personales">
        <p>
          Inicia sesión con tu cuenta institucional de <strong>{CORREO_INSTITUCIONAL}</strong>
          para consultar la información registrada, descargar copias y ejercer
          tus derechos de la Ley 1581.
        </p>
      </BloqueoAutenticacion>

    {:else if cargando}
      <CargadorCubo mensaje="Consultando tus datos registrados…" />

    {:else}
      {#if fallo}
        <Degradacion respuesta={fallo} alReintentar={cargar} />
      {/if}

      {#if enMantenimiento}
        <p class="mantenimiento" role="status">
          No se pudo comprobar el estado de tus autorizaciones ahora mismo.
          <strong>Esto no significa que falte ninguna</strong>: el servicio está
          en mantenimiento y lo que veas abajo puede estar incompleto.
        </p>
      {/if}

      <nav class="subcategorias" aria-label="Secciones de mi cuenta">
        <button class:activa={seccion === 'perfil'} aria-current={seccion === 'perfil' ? 'page' : undefined} onclick={() => (seccion = 'perfil')}>
          <Icono nombre="datos" medida={15} /> Perfil
        </button>
        <button class:activa={seccion === 'autorizaciones'} aria-current={seccion === 'autorizaciones' ? 'page' : undefined} onclick={() => (seccion = 'autorizaciones')}>
          <Icono nombre="escudo" medida={15} /> Autorizaciones
        </button>
        <button class:activa={seccion === 'privacidad'} aria-current={seccion === 'privacidad' ? 'page' : undefined} onclick={() => (seccion = 'privacidad')}>
          <Icono nombre="candado" medida={15} /> Privacidad
        </button>
      </nav>

      <div class="panel-seccion" hidden={seccion !== 'perfil'}>
        {#if mios}
          <PanelDeDatosPersonales
            {mios}
            perfil={estado?.perfil ?? null}
            foto={fotoPerfil}
            alGuardarFoto={guardarFoto}
            alRetirarFoto={retirarFoto} />
        {/if}
        <ReportarProblema />
      </div>

      <div class="panel-seccion" hidden={seccion !== 'autorizaciones'}>
        {#if estado}
          <PanelDeAutorizaciones {estado} alCambiar={() => cargar({ silencioso: true })} />
        {:else}
          <p class="sin-datos">No se pudo consultar el estado de tus autorizaciones ahora mismo.</p>
        {/if}
      </div>

      <div class="panel-seccion privacidad" hidden={seccion !== 'privacidad'}>
        <section class="panel-privacidad" aria-labelledby="titulo-privacidad">
          <div>
            <h2 id="titulo-privacidad">Tu información, bajo tu control</h2>
            <p>Descarga una copia legible por máquina o inicia el trámite de eliminación cuando lo necesites.</p>
          </div>
          <button type="button" class="descargar" onclick={llevarme}>
            <Icono nombre="descarga" medida={16} /> Descargar copia de mis datos (JSON)
          </button>
        </section>
        <SolicitudDeSupresion alCambiar={() => cargar({ silencioso: true })} />
      </div>
    {/if}

  </div>
</section>

<style>
  .mis-datos-contenedor {
    flex: 1;
    min-block-size: 0;
    overflow-y: auto;
    scrollbar-gutter: stable;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 16px 18px;
  }

  .mis-datos-tarjeta {
    max-inline-size: 860px;
    inline-size: 100%;
    background: var(--surface-paper);
    border: 1.5px solid var(--ink-ghost);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-float);
    padding: 18px 26px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-sizing: border-box;
  }

  .fila-superior {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .btn-volver-tutor {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12.5px;
    font-weight: 600;
    color: var(--ink-secondary);
    background: var(--surface-paper);
    border: 1.5px solid var(--trazo);
    border-radius: var(--radius-pill);
    padding: 4px 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: var(--shadow-soft);
  }

  .btn-volver-tutor:hover {
    color: var(--ink-primary);
    border-color: var(--ink-primary);
    background: var(--surface-canvas);
    transform: translateY(-1px);
    box-shadow: var(--shadow-card-hover);
  }

  .insignia-seguridad {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--accent-main);
    background: var(--accent-surface);
    padding: 3px 10px;
    border-radius: var(--radius-pill);
    text-decoration: none;
  }

  .encabezado {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  h1 {
    margin: 0;
    font-size: 21px;
    font-weight: 700;
    color: var(--ink-primary);
    letter-spacing: -0.02em;
    line-height: 1.2;
  }

  .subtitulo {
    margin: 0;
    font-size: 13px;
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  .mantenimiento {
    margin: 0;
    padding: 8px 10px;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--ink-primary);
    background: var(--surface-canvas);
    border-inline-start: 3px solid var(--ink-tertiary);
    border-radius: var(--radius-xs);
  }

  .subcategorias {
    display: flex;
    gap: 5px;
    padding: 4px;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-pill);
    background: var(--surface-canvas);
    inline-size: fit-content;
    max-inline-size: 100%;
  }

  .subcategorias button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    min-block-size: 36px;
    padding: 6px 13px;
    border: 0;
    border-radius: var(--radius-pill);
    background: transparent;
    color: var(--ink-secondary);
    font: inherit;
    font-size: var(--texto-sm);
    font-weight: 600;
    cursor: pointer;
  }

  .subcategorias button.activa {
    background: var(--surface-paper);
    color: var(--accent-main);
    box-shadow: var(--shadow-soft);
  }

  .panel-privacidad {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 18px;
    padding: 18px;
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-lg);
    background: var(--surface-panel);
  }

  .panel-seccion.privacidad { display: flex; flex-direction: column; gap: 12px; }
  .panel-seccion[hidden] { display: none; }

  .panel-privacidad h2 { margin: 0; font-size: 1rem; color: var(--ink-primary); }
  .panel-privacidad p,
  .sin-datos { margin: 4px 0 0; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.45; }

  .descargar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    flex-shrink: 0;
    padding: 9px 14px;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-pill);
    background: var(--surface-paper);
    color: var(--ink-primary);
    font: inherit;
    font-size: var(--texto-sm);
    font-weight: 700;
    cursor: pointer;
  }

  /* Los registros y los derechos viven en `../piezas/PanelDeDatosPersonales
     .svelte`; las autorizaciones y el trámite, en `../piezas/datos/`. Esta
     ruta sólo decide qué se monta. */

  /* La tarjeta «inicia sesión para…» vive en `comun/estado/
     BloqueoAutenticacion.svelte` desde el 2026-08-22. */

  @media (max-width: 75rem) {
    .mis-datos-contenedor {
      padding: 12px 8px;
    }

    .mis-datos-tarjeta {
      padding: 16px 14px;
      max-inline-size: 520px;
    }
  }

  @media (max-width: 48rem) {
    .subcategorias {
      inline-size: 100%;
      overflow-x: auto;
      border-radius: var(--radius-md);
      box-sizing: border-box;
    }

    .subcategorias button { flex: 1 0 auto; }
    .panel-privacidad { align-items: stretch; flex-direction: column; }
  }
</style>
