
<script>
  import { setContext } from 'svelte';
  import { CONTEXTO_COPIA_FORMULAS } from './copiaDeFormula.js';
  setContext(CONTEXTO_COPIA_FORMULAS, true);
  import { ayudaContextual } from '../base/ayudaContextual.js';
  import Bloque from './Bloque.svelte';
  import SondeoDeDosNiveles from './SondeoDeDosNiveles.svelte';
  import SelloVerificacion from '../estado/SelloVerificacion.svelte';
  import NivelAyuda from '../estado/NivelAyuda.svelte';
  import AvisoDeProcedencia from '../estado/AvisoDeProcedencia.svelte';
  import MaterialDelCurso from '../fuente/MaterialDelCurso.svelte';
  import ReportarProblema from '../rutas/ReportarProblema.svelte';
  import Icono from '../base/Icono.svelte';
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { emitirEvento } from '../../nucleo/api/telemetria.js';
  import { animarEntradaMensaje } from '../../nucleo/animaciones/gsap.js';
  import {
    agruparBloquesDelTurno,
    esPrimeraCitaDeLaFrase,
    esTurnoMalformado,
    textoCopiableDelTurno
  } from '../../nucleo/presentacion/turno.js';

  let materialAbierto = $state(false);
  let copiado = $state(false);

  let {
    turno,
    autor = 'tutor',
    alResponderSondeo = null,
    ocupado = false,
    alAbrirGrafica = null,
    volverA = undefined,
    soloLectura = false,
    rotuloEstudiante = 'Tú',
    rotuloAsistente = 'Asistente'
  } = $props();

  const bloques = $derived(turno?.bloques ?? []);

  const parrafos = $derived(agruparBloquesDelTurno(bloques));

  const malformado = $derived(esTurnoMalformado(turno));

  const materialNavegable = $derived.by(() => {
    const material = turno?.procedencia?.material;
    if (Array.isArray(material) && material.length) return material;
    const vistos = new Set();
    return [...String(turno?.procedencia?.referencia ?? '').matchAll(/F-\d+/gi)]
      .map(([id]) => id.toUpperCase())
      .filter((id) => !vistos.has(id) && vistos.add(id))
      .map((id) => ({ id, titulo: `Abrir fragmento ${id}`, relacion: 'recuperado' }));
  });

  const procedenciaVisible = $derived(turno?.procedencia
    ? { ...turno.procedencia, material: materialNavegable }
    : null);

  const contextoReporte = $derived.by(() => [
    'Origen: respuesta del tutor.',
    turno?.turno ? `Turno: ${turno.turno}` : '',
    sesion.conversacion ? `Conversación: ${sesion.conversacion}` : '',
    turno?.clase ? `Clase: ${turno.clase}` : '',
    (turno?.conceptos?.[0]?.id ?? turno?.citas?.[0]?.id)
      ? `Concepto: ${turno?.conceptos?.[0]?.id ?? turno?.citas?.[0]?.id}`
      : ''
  ].filter(Boolean).join('\n'));

  function referenciasDelTurno(metadatos) {
    const concepto = turno?.conceptos?.[0]?.id ?? turno?.citas?.[0]?.id;
    return {
      clase: turno?.clase,
      conversacion: sesion.conversacion,
      turno: turno?.turno,
      concepto,
      metadatos,
    };
  }

  async function copiarMensaje() {
    const texto = textoCopiableDelTurno(turno);
    if (!texto) return;
    try {
      await navigator.clipboard.writeText(texto);
    } catch {
      const auxiliar = document.createElement('textarea');
      auxiliar.value = texto;
      auxiliar.style.position = 'fixed';
      auxiliar.style.opacity = '0';
      document.body.appendChild(auxiliar);
      auxiliar.select();
      document.execCommand('copy');
      auxiliar.remove();
    }
    copiado = true;
    if (autor !== 'estudiante' && !soloLectura) {
      void emitirEvento(
        'respuesta.copiada',
        referenciasDelTurno({ alcance: 'respuesta' }),
      );
    }
    setTimeout(() => (copiado = false), 1600);
  }

  function abrirFuentes() {
    materialAbierto = true;
    if (!soloLectura) void emitirEvento(
      'fuentes.abiertas',
      referenciasDelTurno({ materiales: materialNavegable.length }),
    );
  }
</script>

<article
  class="turno {autor}"
  style={`--opacidad-mensaje: ${autor === 'estudiante' ? preferencias.opacidadPregunta : preferencias.opacidadRespuesta}%`}
  use:animarEntradaMensaje
>

  <p class="autor-turno">
    {#if autor !== 'estudiante'}
      <span class="avatar-turno" aria-hidden="true"><Icono nombre="didaxia" medida={15} /></span>
    {/if}
    {autor === 'estudiante' ? rotuloEstudiante : rotuloAsistente}
  </p>
  <div class="burbuja">
    {#if malformado}
      <p class="malformado" role="alert">
        Esta respuesta llegó con una inconsistencia y no se muestra completa.
      </p>
    {:else}
      {#each parrafos as grupo, i (i)}

        {#if grupo.enFrase && grupo.bloques.length > 1}
          <p class="frase">

            {#each grupo.bloques as bloque, j (j)}<Bloque {bloque} sellado={autor !== 'estudiante'} enLinea rotulado={esPrimeraCitaDeLaFrase(grupo.bloques, j)} {alAbrirGrafica} />{/each}{grupo.cierre}
            {#if autor !== 'estudiante'}
              <SelloVerificacion estado={grupo.sello} />
            {/if}
          </p>
        {:else}
          <Bloque bloque={grupo.bloques[0]} sellado={autor !== 'estudiante'} {alAbrirGrafica}
                  cierre={grupo.cierre} />
        {/if}
      {/each}


      {#if turno?.sondeo && alResponderSondeo}
        <SondeoDeDosNiveles
          sondeo={turno.sondeo}
          alResponder={alResponderSondeo}
          {ocupado}
        />
      {/if}

      <footer class="metadatos">
        {#if turno?.nivel}<NivelAyuda nivel={turno.nivel} />{/if}
        {#if procedenciaVisible}
          <AvisoDeProcedencia procedencia={procedenciaVisible} />
        {/if}
      </footer>

      <nav class="acciones-respuesta" aria-label={autor === 'estudiante' ? 'Acciones de tu mensaje' : 'Acciones de la respuesta'}>
          <button use:ayudaContextual type="button" class:confirmado={copiado} onclick={copiarMensaje}
                  aria-label={copiado ? 'Mensaje copiado' : autor === 'estudiante' ? 'Copiar mi mensaje' : 'Copiar respuesta'}
                  title={autor === 'estudiante' ? 'Copiar mi mensaje' : 'Copiar respuesta'}>
            <Icono nombre={copiado ? 'check' : 'copiar'} medida={15} />
            <span>{copiado ? 'Copiado' : 'Copiar'}</span>
          </button>
          {#if autor !== 'estudiante'}
          {#if materialNavegable.length}
            <button type="button" onclick={abrirFuentes}
                    aria-haspopup="dialog" aria-expanded={materialAbierto}>
              <Icono nombre="biblioteca" medida={15} />
              <span>Fuentes</span>
              <em>{materialNavegable.length}</em>
            </button>
          {/if}
          {#if !soloLectura}<ReportarProblema
            compacto
            presentacion="accion"
            etiqueta="Reportar un error"
            etiquetaAria="Reportar un error en esta respuesta"
            categoriaInicial="contenido"
            tituloInicial="Error en una respuesta del tutor"
            contexto={contextoReporte}
          />{/if}
          {/if}
        </nav>
    {/if}
  </div>
</article>

{#if materialNavegable.length && materialAbierto}
  <MaterialDelCurso material={materialNavegable} {volverA} bind:abierto={materialAbierto} />
{/if}

<style>
  .turno {
    position: relative;
    inline-size: min(100%, 54rem);
    margin: 0 auto 1.7rem;
    animation: msgSlideIn 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
  }

  .estudiante {
    inline-size: min(78%, 46rem);
    margin-inline-end: max(0rem, calc((100% - min(100%, 54rem)) / 2));
    margin-inline-start: auto;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }

  .tutor {
    padding-inline-start: 2.65rem;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  @keyframes msgSlideIn {
    from {
      opacity: 0;
      transform: translateY(10px) scale(0.98);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  .autor-turno {
    margin: 0 0 4px;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--ink-tertiary);
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .estudiante .autor-turno {
    color: var(--accent-main);
  }

  .tutor .autor-turno {
    color: var(--color-emerald);
  }

  .avatar-turno {
    display: grid;
    place-items: center;
    position: absolute;
    inset-inline-start: 0;
    inset-block-start: -.25rem;
    inline-size: 1.8rem;
    aspect-ratio: 1;
    border: 1px solid color-mix(in srgb, var(--color-emerald) 42%, var(--trazo-suave));
    border-radius: 50%;
    background: color-mix(in srgb, var(--surface-paper) 84%, transparent);
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--surface-paper) 55%, transparent);
  }

  .tutor::before {
    content: '';
    position: absolute;
    inset-inline-start: .86rem;
    inset-block-start: 1.55rem;
    inset-block-end: -1.75rem;
    inline-size: 1px;
    background: linear-gradient(var(--trazo-suave), transparent);
  }

  .burbuja {
    inline-size: fit-content;
    max-inline-size: 100%;
    padding: 1rem 1.1rem .65rem;
    font-size: 14px;
    line-height: 1.68;
    border-radius: var(--radius-lg);
    transition: var(--transition-fast);
    position: relative;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
  }

  .tutor .burbuja {
    inline-size: 100%;
    background: color-mix(in srgb, var(--surface-elevated) var(--opacidad-mensaje), transparent);
    color: var(--ink-primary);
    border: 1px solid color-mix(in srgb, var(--trazo-suave) 72%, transparent);
    box-shadow: 0 10px 34px color-mix(in srgb, var(--ink-primary) 5%, transparent);
  }

  .tutor .burbuja:hover {
    border-color: var(--ink-tertiary);
    border-color: color-mix(in srgb, var(--accent-main) 38%, var(--trazo-suave));
  }

  .estudiante .burbuja {
    background: color-mix(in srgb, var(--surface-paper) var(--opacidad-mensaje), transparent);
    color: var(--ink-primary);
    border: 1px solid color-mix(in srgb, var(--ink-primary) 16%, transparent);
    border-end-end-radius: .35rem;
    box-shadow: 0 8px 28px color-mix(in srgb, var(--ink-primary) 5%, transparent);
  }

  .estudiante .burbuja:hover {
    border-color: color-mix(in srgb, var(--accent-main) 45%, transparent);
  }

  .metadatos {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-block-start: 0.4rem;
  }

  .acciones-respuesta {
    display: flex;
    align-items: center;
    gap: .25rem;
    margin-block-start: .65rem;
    padding-block-start: .55rem;
    border-block-start: 1px solid color-mix(in srgb, var(--trazo-suave) 62%, transparent);
  }

  .acciones-respuesta button {
    display: inline-flex;
    align-items: center;
    gap: .38rem;
    min-block-size: 2rem;
    padding: .3rem .55rem;
    border: 1px solid transparent;
    border-radius: 999px;
    background: transparent;
    color: var(--ink-tertiary);
    font: inherit;
    font-size: var(--texto-xs);
    cursor: pointer;
  }
  .acciones-respuesta button:hover,
  .acciones-respuesta button:focus-visible {
    border-color: var(--trazo-suave);
    background: color-mix(in srgb, var(--surface-paper) 55%, transparent);
    color: var(--ink-primary);
  }
  .acciones-respuesta button.confirmado { color: var(--semantic-success); }
  .acciones-respuesta em {
    display: grid;
    place-items: center;
    min-inline-size: 1.25rem;
    block-size: 1.25rem;
    padding-inline: .25rem;
    border-radius: 999px;
    background: var(--accent-surface);
    color: var(--accent-main);
    font-size: 9px;
    font-style: normal;
    font-variant-numeric: tabular-nums;
  }

  .frase {
    inline-size: 100%;
    max-inline-size: none;
    margin: 0 0 0.9rem;
    line-height: 1.7;
  }


  .malformado {
    margin: 0;
    color: var(--semantic-error);
    font-size: var(--texto-sm);
  }

  @media (max-width: 48rem) {
    .turno { margin-block-end: 1.25rem; }
    .tutor { padding-inline-start: 2.2rem; }
    .estudiante { inline-size: min(92%, 42rem); }
    .burbuja { padding: .85rem .9rem .55rem; font-size: 13.5px; }
    .avatar-turno { inline-size: 1.55rem; }
    .tutor::before { inset-inline-start: .74rem; }
  }
</style>
