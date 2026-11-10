<script>
  import { onMount } from 'svelte';
  let { temaOscuro = false, colores } = $props();
  import HeroDePortada from '../piezas/HeroDePortada.svelte';
  import DemostracionPublica from '../piezas/DemostracionPublica.svelte';
  import ImagenAmpliable from '../piezas/ImagenAmpliable.svelte';
  import PerfilesPublicos from '../piezas/PerfilesPublicos.svelte';
  import { AUTORES_CON_LINKEDIN, INSTITUCION, MARCA, MATERIALES_ESTUDIO } from '../contenido/proyecto.js';

  const RESULTADOS_PILOTO = Object.freeze([
    Object.freeze({ valor: '113', descripcion: 'personas con al menos un par completo incluido en el análisis' }),
    Object.freeze({ valor: '251', descripcion: 'conversaciones analizadas' }),
    Object.freeze({ valor: '1.473', descripcion: 'pares completos estudiante–tutor' }),
    Object.freeze({ valor: '62 de 82', descripcion: 'respuestas numéricas favorables en satisfacción' })
  ]);

  const ETAPAS = Object.freeze([
    Object.freeze({ numero: '01', titulo: 'Pregunta', texto: 'Plantea una duda, una expresión o el paso en que te detuviste.' }),
    Object.freeze({ numero: '02', titulo: 'Trabaja la idea', texto: 'Pide una explicación o ejemplo y comparte tu propio intento.' }),
    Object.freeze({ numero: '03', titulo: 'Conecta', texto: 'Consulta la gráfica, los recursos y la comprobación disponible.' })
  ]);

  onMount(() => {
    document.querySelector('meta[name="description"]')?.setAttribute(
      'content',
      'Conoce DidaxIa, un tutor conversacional de apoyo al cálculo diferencial. Explora una presentación abierta por roles, capturas del sistema y resultados de su evaluación formativa.'
    );
  });
</script>

<svelte:head><title>{MARCA} · Tutor de cálculo diferencial</title></svelte:head>

<HeroDePortada {temaOscuro} {colores} />
<DemostracionPublica {temaOscuro} {colores} />

<div class="portada">
  <section class="seccion-proyecto" aria-labelledby="titulo-proyecto">
    <div class="texto-proyecto">
      <p class="sobrelinea">Un trabajo académico aplicado</p>
      <h2 id="titulo-proyecto">Diseñado para estudiar, explicar y revisar.</h2>
      <p>
        {MARCA} es un trabajo de grado desarrollado en la {INSTITUCION} a partir de
        una revisión sistemática sobre tutores inteligentes. Apoya el estudio del
        cálculo diferencial con conversación en español, consulta de material y
        herramientas para explorar expresiones y gráficas.
      </p>
      <p>
        Se evaluó de manera formativa en actividades universitarias voluntarias.
        La experiencia describe uso y percepción; no demuestra por sí sola un
        efecto causal sobre el aprendizaje. El tutor puede equivocarse: comprueba
        los resultados y consulta a tu docente cuando lo necesites.
      </p>
    </div>

    <ol class="etapas" aria-label="Tres pasos de uso de DidaxIa">
      {#each ETAPAS as etapa (etapa.numero)}
        <li>
          <span class="numero-etapa">{etapa.numero}</span>
          <div><h3>{etapa.titulo}</h3><p>{etapa.texto}</p></div>
        </li>
      {/each}
    </ol>
  </section>

  <section class="resultados" aria-labelledby="titulo-resultados">
    <div class="encabezado-resultados">
      <p class="sobrelinea">Evaluación formativa · 16 sep — 9 oct 2026</p>
      <h2 id="titulo-resultados">Qué se observó en el piloto.</h2>
      <p>
        Cifras de la evaluación del proyecto, presentadas por separado de los datos
        ficticios que aparecen en las pantallas de demostración.
      </p>
    </div>

    <div class="cifras-piloto">
      {#each RESULTADOS_PILOTO as resultado (resultado.valor)}
        <div class="cifra-piloto">
          <strong>{resultado.valor}</strong>
          <span>{resultado.descripcion}</span>
          {#if resultado.valor === '62 de 82'}<small>75,61% de las respuestas numéricas</small>{/if}
        </div>
      {/each}
    </div>

    <p class="limite-resultados">
      La muestra fue voluntaria y de conveniencia. La satisfacción corresponde a 82
      respuestas numéricas de un ítem; hubo una respuesta no numérica entre 83 formularios
      posteriores. De 1.602 registros brutos se obtuvieron 1.474 elegibles y 1.473 pares
      completos; cada par contiene un mensaje del estudiante y la respuesta registrada del tutor.
      Las 117 personas corresponden a quienes tuvieron conversación o encuesta elegible.
      Estas cifras no miden aprendizaje ni prueban
      causalidad.
    </p>
    <a class="enlace-investigacion" href="/investigacion">Método, alcance y limitaciones <span aria-hidden="true">↗</span></a>
    <p class="limite-resultados">La comprobación simbólica de expresiones es una función implementada; las verificaciones de desarrollo son evidencia técnica. El estudio recoge, entre otros resultados, los juicios de dos docentes sobre funciones seleccionadas.</p>
    <div class="materiales-estudio">
      <h3>Materiales del estudio</h3>
      <p>Consulta las tablas agregadas de la evaluación formativa y el script que permite recalcular cifras seleccionadas del estudio.</p>
      <a class="enlace-investigacion" href={MATERIALES_ESTUDIO} target="_blank" rel="noopener noreferrer">Ver materiales del estudio <span aria-hidden="true">↗</span></a>
    </div>
  </section>

  <section class="equipo" id="equipo" aria-labelledby="titulo-equipo">
    <div class="encabezado-equipo">
      <p class="sobrelinea">Personas detrás del proyecto</p>
      <h2 id="titulo-equipo">Equipo DidaxIa</h2>
      <p>Las personas que hicieron posible DidaxIa.</p>
    </div>

    <div class="galeria-equipo">
      <ImagenAmpliable
        src="/imagenes/equipo/equipo-didaxia.webp"
        alt="Los tres integrantes del equipo DidaxIa posan juntos con sus camisetas institucionales y del semillero de investigación."
        descripcion="Equipo Didaxia: Yeison Muñoz, Juan Caiza, Fabian Hoyos"
        clase="foto-equipo"
        width={6102}
        height={3901}
      />
    </div>

    <div class="autoria">
      <h3>Integrantes del equipo</h3>
      <div class="lista-autores">
        {#each AUTORES_CON_LINKEDIN as autor (autor.nombre)}
          <div class="autor">
            <span>{autor.nombre}{autor.cargo ? ` · ${autor.cargo}` : ''}</span>
            <PerfilesPublicos perfil={autor} />
          </div>
        {/each}
      </div>
    </div>
  </section>

</div>

<style>
  .materiales-estudio { margin-block-start: var(--espacio-lg); }
  .materiales-estudio h3 { margin: 0 0 var(--espacio-xs); font-size: var(--texto-md); }
  .materiales-estudio p { margin: 0 0 var(--espacio-sm); color: var(--ink-secondary); }
  .portada {
    display: grid;
    gap: clamp(var(--espacio-2xl), 7vw, 6rem);
    inline-size: min(calc(100% - 2 * var(--espacio-lg)), 82rem);
    margin: 0 auto;
    padding-block: clamp(var(--espacio-2xl), 6vw, 5rem);
  }

  .sobrelinea {
    margin: 0 0 var(--espacio-sm);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 750;
    letter-spacing: 0.065em;
    text-transform: uppercase;
  }

  h2 {
    max-inline-size: 24ch;
    margin: 0;
    color: var(--ink-primary);
    font-size: clamp(var(--texto-2xl), 3.4vw, 3.1rem);
    font-weight: 720;
    line-height: 1.06;
    letter-spacing: -0.04em;
    text-wrap: balance;
  }

  .seccion-proyecto {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 0.9fr);
    gap: clamp(var(--espacio-xl), 6vw, 5rem);
    align-items: start;
  }

  .texto-proyecto { max-inline-size: 50rem; }
  .texto-proyecto > p:not(.sobrelinea) { margin: var(--espacio-md) 0 0; color: var(--ink-secondary); font-size: var(--texto-base); line-height: var(--interlinea-comoda); }

  .etapas {
    display: grid;
    gap: 0;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .etapas li {
    display: grid;
    grid-template-columns: 2.7rem minmax(0, 1fr);
    gap: var(--espacio-md);
    padding-block: var(--espacio-md);
    border-block-start: 1px solid var(--trazo-suave);
  }

  .numero-etapa { padding-block-start: 0.1rem; color: var(--accent-main); font-size: var(--texto-xs); font-weight: 750; }
  .etapas h3 { margin: 0; color: var(--ink-primary); font-size: var(--texto-lg); }
  .etapas p { max-inline-size: 34rem; margin: var(--espacio-xs) 0 0; color: var(--ink-secondary); font-size: var(--texto-sm); line-height: var(--interlinea-normal); }

  .resultados {
    position: relative;
    padding: clamp(var(--espacio-xl), 4vw, 3rem) 0;
    border-block: 1px solid var(--trazo-suave);
  }

  .encabezado-resultados { max-inline-size: 53rem; }
  .encabezado-resultados > p:last-child { margin: var(--espacio-md) 0 0; color: var(--ink-secondary); line-height: var(--interlinea-comoda); }

  .cifras-piloto {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--espacio-lg);
    margin-block: var(--espacio-2xl) var(--espacio-lg);
  }

  .cifra-piloto {
    display: flex;
    min-inline-size: 0;
    flex-direction: column;
    align-items: start;
    gap: var(--espacio-xs);
    padding-inline-start: var(--espacio-md);
    border-inline-start: 2px solid var(--accent-main);
  }

  .cifra-piloto strong { color: var(--ink-primary); font-size: clamp(var(--texto-xl), 2.2vw, var(--texto-2xl)); line-height: 1.1; letter-spacing: -0.03em; }
  .cifra-piloto span { color: var(--ink-secondary); font-size: var(--texto-sm); line-height: var(--interlinea-normal); }
  .cifra-piloto small { color: var(--ink-tertiary); font-size: var(--texto-xs); }

  .limite-resultados {
    max-inline-size: 76rem;
    margin: 0;
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
    line-height: var(--interlinea-comoda);
  }

  .enlace-investigacion {
    display: inline-flex;
    align-items: center;
    gap: var(--espacio-xs);
    min-block-size: 44px;
    margin-block-start: var(--espacio-sm);
    color: var(--accent-main);
    font-size: var(--texto-sm);
    font-weight: 650;
    text-decoration: underline;
    text-underline-offset: 0.22em;
  }

  .enlace-investigacion:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 3px; }

  .encabezado-equipo { margin-block-end: var(--espacio-lg); }
  .encabezado-equipo > p:last-child { margin: var(--espacio-sm) 0 0; color: var(--ink-secondary); line-height: var(--interlinea-comoda); }

  .galeria-equipo {
    inline-size: min(100%, 66rem);
    margin-inline: auto;
  }

  .galeria-equipo :global(.foto-equipo .abrir-imagen) { aspect-ratio: 6102 / 3901; }
  .galeria-equipo :global(.foto-equipo .abrir-imagen img) { object-fit: contain; }
  .galeria-equipo :global(.foto-equipo .abrir-imagen:hover img) { transform: none; }

  .autoria { margin-block-start: var(--espacio-xl); }
  .autoria h3 { margin: 0 0 var(--espacio-sm); color: var(--ink-tertiary); font-size: var(--texto-xs); font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; }

  .lista-autores {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--espacio-lg);
  }

  .autor {
    display: flex;
    min-inline-size: 0;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--espacio-xs);
    padding-block: var(--espacio-md);
    border-block-start: 1px solid var(--trazo-suave);
  }

  .autor > span { color: var(--ink-primary); font-size: var(--texto-base); font-weight: 650; overflow-wrap: anywhere; }

  @media (max-width: 75rem) {
    .seccion-proyecto { grid-template-columns: minmax(0, 1fr); gap: var(--espacio-xl); }
    .etapas { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--espacio-md); }
    .etapas li { grid-template-columns: 1fr; gap: var(--espacio-xs); }
    .cifras-piloto { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }

  @media (max-width: 48rem) {
    .portada { inline-size: min(calc(100% - 2 * var(--espacio-md)), 82rem); gap: var(--espacio-2xl); padding-block: var(--espacio-xl); }
    .etapas { grid-template-columns: minmax(0, 1fr); }
    .etapas li { grid-template-columns: 2rem minmax(0, 1fr); gap: var(--espacio-sm); }
    .resultados { padding-block: var(--espacio-xl); }
    .cifras-piloto { gap: var(--espacio-lg) var(--espacio-md); margin-block: var(--espacio-xl); }
    .cifra-piloto { padding-inline-start: var(--espacio-sm); }
    .cifra-piloto strong { font-size: var(--texto-xl); }
    .lista-autores { grid-template-columns: minmax(0, 1fr); gap: 0; }
  }
</style>
