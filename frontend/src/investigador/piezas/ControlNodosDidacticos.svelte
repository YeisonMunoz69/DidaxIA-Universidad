<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import { onMount } from 'svelte';
  import * as api from '../../nucleo/api/configuracion-sondeos.js';
  import { describir } from '../../nucleo/errores/degradacion.js';

  let configuracion = $state(null);
  let nodos = $derived(Object.entries(configuracion?.nodos ?? {}).map(([codigo, estado]) => ({ codigo, ...estado })));
  let hayPapel = $derived(nodos.some((nodo) => nodo.canal === 'papel'));
  let cargando = $state(true);
  let guardando = $state('');
  let fallo = $state('');
  let confirmacion = $state('');
  const informacion = {
    'L-01': { titulo: 'Hoja presencial: resultado y razón', ayuda: 'Activo: registra que el instrumento en papel está previsto para el aula. Congelado: registra que no está previsto. Este interruptor no administra la hoja física, no crea un sondeo digital ni carga respuestas o métricas. El tutor sigue funcionando.' },
    N05: { titulo: 'Constantes y variable de derivación', ayuda: 'Activo: permite ofrecer un sondeo sobre la derivada de a·x² + k respecto de x, primero el resultado y después su razón. Congelado: impide ofrecer nuevos sondeos N05; el tutor sigue explicando y verificando derivadas, constantes y parámetros. No borra respuestas anteriores ni apaga los factores conductuales.' },
    N08: { titulo: 'Composición y regla de la cadena', ayuda: 'Activo: permite ofrecer un sondeo sobre la derivada de cos³(x), primero el resultado y después su razón. Congelado: impide ofrecer nuevos sondeos N08; el tutor sigue explicando y verificando funciones compuestas y la regla de la cadena. No borra respuestas anteriores ni apaga los factores conductuales.' },
    N14: { titulo: 'Derivadas trigonométricas', ayuda: 'Activo: permite ofrecer un sondeo sobre la derivada de sen(x)·cos(x), primero el resultado y después su razón. Congelado: impide ofrecer nuevos sondeos N14; el tutor sigue explicando y verificando derivadas trigonométricas. No borra respuestas anteriores ni apaga los factores conductuales.' }
  };

  function detalleDe(error) {
    return error?.cuerpo?.detalle || describir(error).explicacion;
  }

  async function cargar() {
    cargando = true;
    fallo = '';
    try {
      configuracion = await api.consultar();
    } catch (error) {
      fallo = detalleDe(error);
    } finally {
      cargando = false;
    }
  }

  async function cambiarNodo(codigo) {
    if (!configuracion || guardando) return;
    guardando = codigo;
    fallo = '';
    confirmacion = '';
    try {
      configuracion = await api.cambiarNodo(codigo, !configuracion.nodos[codigo].habilitado);
      confirmacion = `${codigo} quedó ${configuracion.nodos[codigo].habilitado ? 'activo' : 'congelado'}.`;
    } catch (error) {
      fallo = detalleDe(error);
    } finally {
      guardando = '';
    }
  }

  async function cambiarUmbral(valor) {
    if (!configuracion || guardando || valor === configuracion.umbral_intentos) return;
    guardando = 'umbral';
    fallo = '';
    confirmacion = '';
    try {
      configuracion = await api.cambiarUmbral(valor);
      confirmacion = `El umbral digital quedó en ${valor} ${valor === 1 ? 'intento' : 'intentos'}.`;
    } catch (error) {
      fallo = detalleDe(error);
    } finally {
      guardando = '';
    }
  }

  onMount(cargar);
</script>

<section class="gobierno" aria-labelledby="titulo-gobierno">
  <header class="cabecera">
    <div>
      <span class="sobretitulo">Gobernanza pedagógica</span>
      <h2 id="titulo-gobierno">Nodos didácticos</h2>
      <p>Permite o congela sondeos de resultado y razón. Estos ajustes se aplican a todo el sistema, no a una clase particular.</p>
    </div>
    <span class="sello">Corte curricular del aula</span>
  </header>

  {#if fallo}<p class="fallo" role="alert">{fallo} <button type="button" onclick={cargar}>Reintentar</button></p>{/if}
  {#if confirmacion}<p class="confirmacion" role="status">{confirmacion}</p>{/if}
  {#if cargando}<CargadorCubo mensaje="Consultando los ajustes pedagógicos…" />{/if}

  {#if configuracion}
    <p class="nota">Sólo aparecen los nodos que tienen un instrumento configurable. Los demás temas siguen disponibles en el tutor. Activar un sondeo permite ofrecerlo cuando corresponda; no obliga a mostrarlo en cada respuesta.</p>
    <div class="rejilla">
      {#each nodos as nodo (nodo.codigo)}
        {@const activo = nodo.habilitado === true}
        {@const esPapel = nodo.canal === 'papel'}
        <article class="tarjeta" class:activa={activo}>
          <div class="linea-superior">
            <span class="codigo">{nodo.codigo}</span>
            <span class="canal">{esPapel ? 'Hoja de aula' : 'Sondeo digital'}</span>
          </div>
          <div class="contenido-tarjeta">
            <div class="titulo-con-ayuda"><h3>{informacion[nodo.codigo]?.titulo ?? `Sondeo ${nodo.codigo}`}</h3>
              <BotonAyudaTooltip tamano="sm" ariaLabel={`Qué cambia al activar o congelar ${nodo.codigo}`} texto={informacion[nodo.codigo]?.ayuda ?? 'Control de oferta del sondeo de este nodo.'} />
            </div>
            <p class="contexto">{esPapel ? 'Aplicación presencial' : 'Oferta en el tutor'}</p>
            <p id={`descripcion-${nodo.codigo}`} class="detalle">
              {esPapel
                ? 'Resultado y razón se registran en la hoja física; este control no crea un sondeo digital.'
                : 'La oferta digital depende del contenido trabajado, el umbral de intentos y el estado de este nodo.'}
            </p>
          </div>
          <div class="control">
            <span class:encendido={activo} class="estado">{activo ? (esPapel ? 'Activo en aula' : 'Activo en tutor') : 'Congelado'}</span>
            <button
              type="button"
              class="interruptor"
              role="switch"
              aria-label={`${nodo.codigo}: sondeo ${esPapel ? 'en papel' : 'digital'}`}
              aria-describedby={`descripcion-${nodo.codigo}`}
              aria-checked={activo}
              disabled={Boolean(guardando)}
              onclick={() => cambiarNodo(nodo.codigo)}>
              <span aria-hidden="true"></span>
            </button>
          </div>
        </article>
      {/each}
    </div>

    <section class="umbral" aria-labelledby="titulo-umbral">
      <div>
        <span class="sobretitulo">Oferta automática</span>
        <div class="titulo-con-ayuda"><h3 id="titulo-umbral">Umbral de intentos</h3>
          <BotonAyudaTooltip tamano="sm" ariaLabel="Cómo se cuentan los intentos del sondeo"
            texto="Cuenta propuestas distintas sobre el mismo problema, no sólo mensajes enviados. Repetir el mismo resultado no suma otro intento. Elegir 1 permite ofrecer el sondeo antes; elegir 2 espera más evidencia. También deben cumplirse las condiciones del tema y haber al menos tres turnos desde el último sondeo. El ajuste es global y no cambia por sí solo la explicación del tutor." />
        </div>
        <p>Se aplica solo a los sondeos digitales habilitados. Además debe haber una expresión matemática, un nodo pertinente y espacio entre sondeos.</p>
      </div>
      <div class="opciones-umbral" role="group" aria-label="Intentos requeridos en el problema">
        <button type="button" class:elegido={configuracion.umbral_intentos === 1}
          aria-pressed={configuracion.umbral_intentos === 1}
          disabled={Boolean(guardando)} onclick={() => cambiarUmbral(1)}>1 intento</button>
        <button type="button" class:elegido={configuracion.umbral_intentos === 2}
          aria-pressed={configuracion.umbral_intentos === 2}
          disabled={Boolean(guardando)} onclick={() => cambiarUmbral(2)}>2 intentos</button>
      </div>
    </section>
    {#if hayPapel}<p class="nota">Las hojas físicas se codificarán tras la visita. Sus respuestas y estados E1–E4 no se incorporan automáticamente a los KPI del servidor.</p>{/if}
  {/if}
</section>

<style>
  .gobierno { display: grid; gap: 1.2rem; }
  .cabecera { display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; }
  .sobretitulo { color: var(--accent-main); font-size: var(--texto-xs); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
  h2, h3, p { margin: 0; }
  h2 { color: var(--ink-primary); font-size: var(--texto-xl); }
  h3 { color: var(--ink-primary); font-size: var(--texto-md); }
  p { color: var(--ink-secondary); font-size: var(--texto-sm); line-height: 1.5; }
  .cabecera p { margin-block-start: .3rem; }
  .sello { flex: none; padding: .45rem .75rem; border-radius: var(--radius-pill); background: var(--accent-surface); color: var(--accent-main); font-size: var(--texto-xs); font-weight: 750; }
  .rejilla { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
  .tarjeta { display: flex; flex-direction: column; gap: 1rem; min-inline-size: 0; padding: 1.25rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-lg); background: var(--surface-panel); box-shadow: var(--shadow-soft); transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease; }
  .tarjeta:hover { transform: translateY(-2px); box-shadow: var(--shadow-card-hover); }
  .tarjeta.activa { border-color: var(--accent-main); background: var(--surface-paper); }
  .linea-superior, .control { display: flex; justify-content: space-between; align-items: center; gap: .75rem; }
  .codigo { display: inline-flex; align-items: center; justify-content: center; min-inline-size: 3rem; padding: .35rem .6rem; border-radius: var(--radius-sm); background: var(--surface-canvas); color: var(--ink-primary); font-size: var(--texto-xs); font-weight: 800; letter-spacing: .04em; }
  .canal { color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .contenido-tarjeta { display: grid; gap: .25rem; flex: 1; }
  .titulo-con-ayuda { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
  .contexto { color: var(--accent-main); font-weight: 700; }
  .detalle { margin-block-start: .3rem; }
  .control { padding-block-start: .85rem; border-top: 1px solid var(--trazo-suave); }
  .estado { color: var(--ink-secondary); font-size: var(--texto-sm); font-weight: 700; }
  .estado.encendido { color: var(--semantic-success); }
  .interruptor { position: relative; inline-size: 3rem; block-size: 1.7rem; flex: 0 0 3rem; border: 0; border-radius: var(--radius-pill); background: var(--trazo); cursor: pointer; transition: background-color 180ms ease; }
  .interruptor[aria-checked="true"] { background: var(--semantic-success); }
  .interruptor span { position: absolute; inset-block-start: .17rem; inset-inline-start: .18rem; inline-size: 1.23rem; block-size: 1.23rem; border-radius: 50%; background: var(--surface-paper); box-shadow: var(--shadow-soft); transition: transform 180ms ease; }
  .interruptor[aria-checked="true"] span { transform: translateX(1.28rem); }
  .interruptor:focus-visible, .opciones-umbral button:focus-visible, .fallo button:focus-visible { outline: 3px solid var(--accent-main); outline-offset: 3px; }
  button:disabled { opacity: .65; cursor: wait; }
  .umbral { display: flex; justify-content: space-between; align-items: center; gap: 1.25rem; padding: 1.2rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-lg); background: var(--surface-panel); box-shadow: var(--shadow-soft); }
  .umbral p { max-inline-size: 39rem; margin-block-start: .35rem; }
  .opciones-umbral { display: flex; flex: none; gap: .3rem; padding: .3rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-pill); background: var(--surface-canvas); }
  .opciones-umbral button { min-block-size: 2.65rem; padding: .55rem .8rem; border: 0; border-radius: var(--radius-pill); background: transparent; color: var(--ink-secondary); font: inherit; font-size: var(--texto-sm); font-weight: 700; cursor: pointer; transition: background-color 160ms ease, box-shadow 160ms ease; }
  .opciones-umbral button.elegido { background: var(--surface-paper); color: var(--ink-primary); box-shadow: var(--shadow-soft); }
  .nota { padding: .75rem 1rem; border-inline-start: 3px solid var(--accent-main); border-radius: var(--radius-sm); background: var(--accent-surface); }
  .fallo, .confirmacion { padding: .8rem 1rem; border-radius: var(--radius-sm); }
  .fallo { color: var(--semantic-error); background: var(--semantic-error-bg); }
  .confirmacion { color: var(--semantic-success); background: var(--semantic-success-bg); }
  .fallo button { border: 0; background: none; color: inherit; font: inherit; font-weight: 700; text-decoration: underline; cursor: pointer; }
  @media (max-width: 52rem) { .rejilla { grid-template-columns: 1fr; } .umbral { align-items: stretch; flex-direction: column; } }
  @media (max-width: 36rem) { .cabecera { align-items: flex-start; flex-direction: column; } .sello { align-self: flex-start; } .opciones-umbral { flex-wrap: wrap; } .opciones-umbral button { flex: 1; } }
  @media (prefers-reduced-motion: reduce) { .tarjeta, .interruptor, .interruptor span, .opciones-umbral button { transition: none; } .tarjeta:hover { transform: none; } }
</style>
