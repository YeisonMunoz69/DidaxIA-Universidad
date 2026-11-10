<script>
  import ImagenAmpliable from './ImagenAmpliable.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  let { temaOscuro = false, colores = { paleta: 'ambar' } } = $props();

  const PERFILES = Object.freeze([
    Object.freeze({
      id: 'estudiante',
      nombre: 'Estudiante',
      lema: 'Pregunta, comprende y prueba.',
      quien: 'Un tutor conversacional para explorar cálculo diferencial paso a paso.',
      objetivo: 'Relacionar una duda en español con notación matemática, comprobaciones simbólicas y recursos de apoyo.',
      pasos: Object.freeze([
        'Plantea una pregunta o escribe una función.',
        'Revisa la explicación y la derivada propuesta.',
        'Comprueba qué expresión fue validada simbólicamente.',
        'Continúa con tus propias preguntas desde la conversación.'
      ]),
      resultado: 'Un hilo de trabajo con explicación, notación matemática y espacio para continuar.'
    }),
    Object.freeze({
      id: 'docente',
      nombre: 'Docente',
      lema: 'Consulta el pulso de una clase.',
      quien: 'Indicadores de grupo para acompañar la actividad de cálculo diferencial.',
      objetivo: 'Elegir una clase y un periodo, y leer sus valores junto a la población, muestra y reglas de calidad.',
      pasos: Object.freeze([
        'Selecciona una de tus clases.',
        'Define el periodo que quieres consultar.',
        'Revisa las proporciones y los conteos disponibles.',
        'Abre la explicación de cada indicador para ver sus límites.'
      ]),
      resultado: 'Un resumen del grupo con filtros, denominadores y datos de cobertura.'
    }),
    Object.freeze({
      id: 'investigador',
      nombre: 'Investigador',
      lema: 'Explora la actividad con contexto.',
      quien: 'Analítica institucional con filtros y recorrido por niveles autorizados.',
      objetivo: 'Consultar indicadores agregados, conocer su población y recorrer la jerarquía hasta una ficha institucional.',
      pasos: Object.freeze([
        'Filtra por periodo, facultad, programa, docente o clase.',
        'Explora el nivel institucional y el detalle disponible.',
        'Compara métricas con sus muestras y denominadores.',
        'Consulta la calidad y las limitaciones de lectura.'
      ]),
      resultado: 'Un tablero agregado que conserva el contexto de cada indicador y el alcance del análisis.'
    })
  ]);

  const DISPOSITIVOS = Object.freeze({
    computador: Object.freeze({ etiqueta: 'Computador', ancho: 1600, alto: 900 }),
    telefono: Object.freeze({ etiqueta: 'Teléfono', ancho: 390, alto: 844 })
  });

  const VISTAS = {
    estudiante: [
      { id: 'inicio', nombre: 'Inicio del tutor', detalle: 'Comienza con una pregunta o el tema que quieres comprender.' },
      { id: 'pregunta', nombre: 'Pregunta y símbolos', detalle: 'Escribe una pregunta compleja y usa el teclado de notación matemática.' },
      { id: 'conversacion', nombre: 'Conversación', detalle: 'Recibe una explicación y revisa la comprobación matemática.' },
      { id: 'fuentes', nombre: 'Fuentes en la charla', detalle: 'Consulta el material asociado a una respuesta del tutor.' },
      { id: 'lectura', nombre: 'Lectura del libro', detalle: 'Abre una obra del curso y lee su contenido.' },
      { id: 'pasopagina', nombre: 'Pasar página', detalle: 'Avanza entre secciones del libro interactivo.' },
      { id: 'encuesta', nombre: 'Responder formulario', detalle: 'Responde una actividad publicada para tu curso.' },
      { id: 'diapositivas', nombre: 'Ver diapositivas', detalle: 'Consulta una presentación compartida para tu clase.' },
      { id: 'grafica', nombre: 'Graficadora', detalle: 'Explora una función en el plano y ajusta sus opciones.' },
      { id: 'tabla', nombre: 'Tabla de valores', detalle: 'Consulta los valores de la función junto a su gráfica.' },
      { id: 'teclado', nombre: 'Teclado matemático', detalle: 'Introduce expresiones con el teclado de notación.' },
      { id: 'conceptos', nombre: 'Conceptos', detalle: 'Consulta una ficha y relaciona ideas de cálculo.' },
      { id: 'biblioteca', nombre: 'Biblioteca', detalle: 'Explora el catálogo y los fragmentos disponibles de una obra.' }
    ],
    docente: [
      { id: 'docente', nombre: 'Indicadores', detalle: 'Revisa indicadores y cobertura de una clase.' },
      { id: 'docenteclases', nombre: 'Mis clases', detalle: 'Organiza y consulta tus clases.' },
      { id: 'docentecrear', nombre: 'Crear clase', detalle: 'Prepara una clase y su acceso para estudiantes.' }
    ],
    investigador: [
      { id: 'investigador', nombre: 'Analítica', detalle: 'Explora indicadores institucionales y sus filtros.' },
      { id: 'investigadorcorreo', nombre: 'Comunicaciones', detalle: 'Prepara comunicaciones desde la aplicación.' },
      { id: 'investigadorrecursos', nombre: 'Recursos', detalle: 'Gestiona encuestas y presentaciones del proyecto.' }
    ]
  };
  let rol = $state('estudiante');
  let vista = $state('inicio');
  const vistaActual = $derived(VISTAS[rol].find(item => item.id === vista) ?? VISTAS[rol][0]);
  const PASOS = {
    inicio: ['Abre una conversación nueva.', 'Escribe el tema que quieres comprender.', 'Continúa con una duda, una función o tu propio intento.'],
    pregunta: ['Redacta una pregunta de cálculo.', 'Abre el teclado de símbolos.', 'Combina texto y notación matemática en el mismo mensaje.'],
    fuentes: ['Abre las fuentes de una respuesta.', 'Elige un fragmento del material consultado.', 'Regresa a la conversación para continuar.'],
    lectura: ['Selecciona una obra disponible.', 'Lee el contenido y sus fórmulas.', 'Utiliza el índice para explorar otras partes.'],
    pasopagina: ['Abre una sección del libro.', 'Avanza con las flechas o el gesto de página.', 'Continúa leyendo la siguiente sección.'],
    encuesta: ['Abre el formulario de tu curso.', 'Elige tus respuestas y completa las preguntas.', 'Revisa tus respuestas antes de enviarlas.'],
    diapositivas: ['Abre el material compartido.', 'Recorre las diapositivas.', 'Consulta los recursos asociados a la presentación.'],
    grafica: ['Escribe una función.', 'Observa su representación en el plano.', 'Explora las opciones de la gráfica.'],
    tabla: ['Abre una función en la graficadora.', 'Selecciona la tabla de valores.', 'Relaciona cada valor con la curva.'],
    teclado: ['Abre el panel de funciones.', 'Elige una categoría de símbolos.', 'Escribe la expresión que quieres graficar.'],
    conceptos: ['Busca una idea de cálculo.', 'Abre la ficha del concepto.', 'Consulta la explicación y su notación.'],
    biblioteca: ['Explora las obras del curso.', 'Selecciona un libro.', 'Abre una sección o un fragmento disponible.'],
    docenteclases: ['Selecciona una de tus clases.', 'Consulta su código y sus integrantes.', 'Revisa las solicitudes de matrícula disponibles.'],
    docentecrear: ['Abre la creación de una clase.', 'Escribe un nombre para el grupo.', 'Crea el grupo para compartir su código.'],
    investigadorcorreo: ['Abre Comunicaciones en tu perfil.', 'Prepara el destinatario, asunto y mensaje.', 'Revisa la vista previa antes del envío.'],
    investigadorrecursos: ['Abre el espacio de recursos.', 'Elige encuestas o diapositivas.', 'Prepara y comparte el material autorizado.']
  };
  function elegirRol(id) { rol = id; vista = VISTAS[id][0].id; }
  let dispositivo = $state(
    globalThis.matchMedia?.('(max-width: 48rem)').matches
      ? 'telefono'
      : 'computador'
  );

  const perfilActual = $derived(PERFILES.find((perfil) => perfil.id === rol));
  const pasosActuales = $derived(PASOS[vistaActual.id] ?? perfilActual.pasos);
  const dispositivoActual = $derived(DISPOSITIVOS[dispositivo]);
  const imagenCaptura = $derived(`/imagenes/demostracion/variantes/${vistaActual.id}-${dispositivo}-${temaOscuro ? 'oscuro' : 'claro'}-${colores.paleta}.webp`);
  const textoCaptura = $derived(
    `Interfaz de DidaxIa para ${perfilActual.nombre.toLocaleLowerCase('es')}, vista en ${dispositivoActual.etiqueta.toLocaleLowerCase('es')}.`
  );
  const altCaptura = $derived(`Captura de ${vistaActual.nombre} de DidaxIa en ${dispositivoActual.etiqueta.toLocaleLowerCase('es')}. ${vistaActual.detalle}`);

  function moverPestana(evento, indice) {
    const paso = evento.key === 'ArrowRight' ? 1
      : evento.key === 'ArrowLeft' ? -1
        : evento.key === 'Home' ? -indice
          : evento.key === 'End' ? PERFILES.length - 1 - indice
            : 0;

    if (!paso) return;
    evento.preventDefault();
    const siguiente = (indice + paso + PERFILES.length) % PERFILES.length;
    elegirRol(PERFILES[siguiente].id);
    evento.currentTarget.parentElement
      ?.querySelectorAll('[role="tab"]')?.[siguiente]
      ?.focus();
  }
</script>

<section class="recorrido" id="recorrido" aria-labelledby="titulo-recorrido">
  <div class="encabezado-recorrido">
    <p class="sobrelinea">Conoce la aplicación</p>
    <h2 id="titulo-recorrido">Un sistema, tres perspectivas.</h2>
    <p class="intro-recorrido">
      Explora capturas de la aplicación en computador y teléfono. Cambia de perfil
      para conocer el tutor, los indicadores del grupo y la analítica institucional.
    </p>
  </div>

  <div class="pestanas-roles" id="pestanas-roles" role="tablist" aria-label="Vistas de DidaxIa por perfil">
    {#each PERFILES as perfil, indice (perfil.id)}
      <button
        id={`pestana-${perfil.id}`}
        type="button"
        role="tab"
        aria-selected={rol === perfil.id}
        aria-controls="panel-recorrido"
        tabindex={rol === perfil.id ? 0 : -1}
        class:activa={rol === perfil.id}
        onclick={() => elegirRol(perfil.id)}
        onkeydown={(evento) => moverPestana(evento, indice)}
      >{perfil.nombre}</button>
    {/each}
  </div>

  <div
    id="panel-recorrido"
    class="panel-recorrido"
    role="tabpanel"
    aria-labelledby={`pestana-${rol}`}
    tabindex="0"
  >
    <div class="detalle-perfil">
      <p class="sobrelinea">{perfilActual.nombre} · {perfilActual.lema}</p>
      <h3>{vistaActual.id === VISTAS[rol][0].id ? perfilActual.quien : vistaActual.nombre}</h3>
      <p class="objetivo">{vistaActual.id === VISTAS[rol][0].id ? perfilActual.objetivo : vistaActual.detalle}</p>

      <div class="pasos-perfil">
        <h4>Recorrido</h4>
        <ol>
          {#each pasosActuales as paso, indice (paso)}
            <li><span class="numero-paso">{indice + 1}</span><span>{paso}</span></li>
          {/each}
        </ol>
      </div>

      <div class="resultado-perfil">
        <span class="etiqueta-resultado">Qué muestra</span>
        <p>{PASOS[vistaActual.id] ? vistaActual.detalle : perfilActual.resultado}</p>
      </div>
    </div>

    <div class="muestra-perfil">
      <div class="controles-muestra">
        <div class="selector-dispositivo" role="group" aria-label="Formato de captura">
          {#each Object.entries(DISPOSITIVOS) as [id, opcion] (id)}
            <button
              type="button"
              aria-pressed={dispositivo === id}
              class:seleccionado={dispositivo === id}
              onclick={() => { dispositivo = id; }}
            >{opcion.etiqueta}</button>
          {/each}
        </div>
      </div>

      <div class="vistas-estudiante" aria-label={`Vistas de ${perfilActual.nombre}`}>
          <label for="vista-del-perfil">Explora una vista</label>
          <select id="vista-del-perfil" use:menuDesplegable={vista} bind:value={vista}>
            {#each VISTAS[rol] as opcion (opcion.id)}
              <option value={opcion.id}>{opcion.nombre}</option>
            {/each}
          </select>
          <p>{vistaActual.detalle}</p>
        </div>
      {#if (rol === 'estudiante' && (vista === 'encuesta' || vista === 'diapositivas')) || rol === 'docente'}
        <p class="nota-futura">Se espera ampliar estas herramientas para que el docente dirija sus clases y cree cuestionarios de distintos tipos, integrados en DidaxIa.</p>
      {/if}

      <div class="captura" class:formato-telefono={dispositivo === 'telefono'}>
        {#if dispositivo === 'computador'}
          <div class="marco-computador">
            <div class="bisel-computador">
              <div class="barra-navegador" aria-hidden="true">
                <span class="controles-navegador"><i></i><i></i><i></i></span>
                <span class="ruta-navegador">DidaxIa · aplicación</span>
                <span class="acciones-navegador">•••</span>
              </div>
              <ImagenAmpliable
                src={imagenCaptura}
                alt={altCaptura}
                descripcion={textoCaptura}
                clase="captura-sistema"
                width={dispositivoActual.ancho}
                height={dispositivoActual.alto}
              />
            </div>
            <div class="soporte-computador" aria-hidden="true"><span></span></div>
          </div>
        {:else}
          <div class="marco-telefono">
            <div class="pantalla-telefono">
              <div class="bisel-superior" aria-hidden="true"><span></span></div>
              <ImagenAmpliable
                src={imagenCaptura}
                alt={altCaptura}
                descripcion={textoCaptura}
                clase="captura-sistema"
                width={dispositivoActual.ancho}
                height={dispositivoActual.alto}
              />
              <div class="bisel-inferior" aria-hidden="true"><span></span></div>
            </div>
          </div>
        {/if}
      </div>

      <p class="procedencia">
        Vista de demostración con datos ilustrativos.
      </p>
    </div>
  </div>

  <p class="nota-alcance">
    La demostración no requiere una cuenta. Los controles de perfil y dispositivo cambian
    la vista presentada; no abren el tutor ni consultan datos personales.
  </p>
</section>

<style>
  .recorrido {
    inline-size: min(calc(100% - 2 * var(--espacio-lg)), 82rem);
    margin: 0 auto;
    padding-block: clamp(var(--espacio-2xl), 6vw, 5rem);
    scroll-margin-top: 7rem;
  }

  .encabezado-recorrido { max-inline-size: 56rem; }

  .sobrelinea {
    margin: 0 0 var(--espacio-sm);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 750;
    letter-spacing: 0.065em;
    text-transform: uppercase;
  }

  h2 {
    margin: 0;
    color: var(--ink-primary);
    font-size: clamp(var(--texto-2xl), 4vw, 3.5rem);
    font-weight: 720;
    line-height: 1.03;
    letter-spacing: -0.04em;
    text-wrap: balance;
  }

  .intro-recorrido {
    max-inline-size: 50rem;
    margin: var(--espacio-md) 0 0;
    color: var(--ink-secondary);
    font-size: var(--texto-base);
    line-height: var(--interlinea-comoda);
  }

  .pestanas-roles {
    display: flex;
    align-items: center;
    gap: var(--espacio-lg);
    margin-block-start: var(--espacio-2xl);
    border-block-end: 1px solid var(--trazo-suave);
  }

  .pestanas-roles button {
    position: relative;
    min-block-size: 52px;
    padding: 0.6rem 0.1rem;
    border: 0;
    color: var(--ink-secondary);
    background: transparent;
    font: inherit;
    font-size: var(--texto-base);
    font-weight: 620;
    cursor: pointer;
  }

  .pestanas-roles button::after {
    position: absolute;
    inset-inline: 0;
    inset-block-end: -1px;
    block-size: 2px;
    background: transparent;
    content: '';
    transition: background-color 180ms ease;
  }

  .pestanas-roles button:hover { color: var(--ink-primary); }
  .pestanas-roles button.activa { color: var(--accent-main); }
  .pestanas-roles button.activa::after { background: var(--accent-main); }
  .pestanas-roles button:focus-visible,
  .selector-dispositivo button:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 3px; }

  .panel-recorrido {
    display: grid;
    grid-template-columns: minmax(17rem, 0.72fr) minmax(0, 1.28fr);
    gap: clamp(var(--espacio-xl), 4vw, 3.5rem);
    align-items: start;
    padding-block: clamp(var(--espacio-xl), 4vw, 3rem);
  }

  .panel-recorrido:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 4px; }
  .detalle-perfil { min-inline-size: 0; }

  .detalle-perfil h3 {
    max-inline-size: 25ch;
    margin: 0;
    color: var(--ink-primary);
    font-size: clamp(var(--texto-xl), 2.25vw, var(--texto-2xl));
    line-height: 1.13;
    letter-spacing: -0.026em;
    text-wrap: balance;
  }

  .objetivo {
    margin: var(--espacio-md) 0 0;
    color: var(--ink-secondary);
    line-height: var(--interlinea-comoda);
  }

  .pasos-perfil { margin-block-start: var(--espacio-xl); }
  .pasos-perfil h4 { margin: 0 0 var(--espacio-sm); color: var(--ink-primary); font-size: var(--texto-sm); }
  .pasos-perfil ol { display: grid; gap: var(--espacio-sm); margin: 0; padding: 0; list-style: none; }

  .pasos-perfil li {
    display: grid;
    grid-template-columns: 1.65rem minmax(0, 1fr);
    align-items: start;
    gap: var(--espacio-sm);
    color: var(--ink-secondary);
    font-size: var(--texto-sm);
    line-height: var(--interlinea-normal);
  }

  .numero-paso {
    display: grid;
    place-items: center;
    inline-size: 1.5rem;
    block-size: 1.5rem;
    border-radius: 50%;
    color: var(--accent-main);
    background: var(--accent-surface);
    font-size: var(--texto-xs);
    font-weight: 700;
  }

  .resultado-perfil {
    margin-block-start: var(--espacio-xl);
    padding-inline-start: var(--espacio-md);
    border-inline-start: 2px solid var(--accent-main);
  }

  .etiqueta-resultado { color: var(--ink-tertiary); font-size: var(--texto-xs); font-weight: 700; }
  .resultado-perfil p { margin: var(--espacio-xs) 0 0; color: var(--ink-primary); font-size: var(--texto-sm); line-height: var(--interlinea-normal); }

  .muestra-perfil {
    min-inline-size: 0;
    align-self: start;
    padding: var(--espacio-md);
    border-radius: var(--radius-xl);
    background: var(--surface-panel);
  }

  .controles-muestra {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--espacio-sm);
    margin-block-end: var(--espacio-md);
  }

  .selector-dispositivo {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: 3px;
    border-radius: var(--radius-trazado);
    background: var(--surface-canvas);
  }

  .selector-dispositivo button {
    min-block-size: 38px;
    padding: 0.35rem 0.7rem;
    border: 0;
    border-radius: var(--radius-trazado);
    color: var(--ink-tertiary);
    background: transparent;
    font: inherit;
    font-size: var(--texto-xs);
    font-weight: 620;
    cursor: pointer;
    transition: color 160ms ease, background-color 160ms ease;
  }

  .selector-dispositivo button.seleccionado {
    color: var(--ink-primary);
    background: var(--surface-paper);
    box-shadow: var(--shadow-soft);
  }

  .vistas-estudiante { margin: 0 0 var(--espacio-md); }
  .nota-futura { max-inline-size: none; margin: 0 0 var(--espacio-md); color: var(--ink-secondary); font-size: var(--texto-xs); line-height: var(--interlinea-normal); }
  .vistas-estudiante label { display: block; margin-bottom: .45rem; color: var(--ink-tertiary); font-size: var(--texto-xs); font-weight: 700; }
  .vistas-estudiante select { inline-size: 100%; min-height: 44px; padding: .55rem .8rem; border: 1px solid var(--trazo-suave); border-radius: var(--radius-sm); background: var(--surface-paper); color: var(--ink-primary); font: inherit; font-size: var(--texto-sm); cursor: pointer; }
  .vistas-estudiante select:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 2px; }
  .vistas-estudiante p { margin: .6rem 0 0; max-inline-size: none; color: var(--ink-secondary); font-size: var(--texto-xs); line-height: var(--interlinea-normal); }

  .captura { display: grid; place-items: center; min-inline-size: 0; }
  .captura :global(.captura-sistema) { inline-size: 100%; margin: 0; }
  .captura :global(.captura-sistema figcaption) { display: none; }

  .marco-computador {
    inline-size: 100%;
    padding: 0.65rem 0.65rem 0;
    border: 1px solid color-mix(in srgb, var(--trazo) 62%, transparent);
    border-block-end: 0;
    border-radius: 1.25rem 1.25rem 0 0;
    background: linear-gradient(150deg,
      color-mix(in srgb, var(--surface-paper) 84%, white),
      color-mix(in srgb, var(--surface-panel) 88%, var(--ink-primary)));
    box-shadow: 0 20px 42px color-mix(in srgb, var(--ink-primary) 16%, transparent);
    transition: transform 220ms ease, box-shadow 220ms ease;
  }

  .muestra-perfil:hover .marco-computador {
    transform: translateY(-2px);
    box-shadow: 0 26px 48px color-mix(in srgb, var(--ink-primary) 19%, transparent);
  }

  .bisel-computador { overflow: hidden; border-radius: 0.8rem 0.8rem 0 0; background: var(--surface-canvas); }
  .barra-navegador {
    display: grid;
    grid-template-columns: 3.5rem minmax(0, 1fr) 3.5rem;
    align-items: center;
    min-block-size: 2rem;
    padding-inline: 0.65rem;
    background: color-mix(in srgb, var(--surface-paper) 82%, var(--surface-panel));
  }

  .controles-navegador { display: flex; align-items: center; gap: 0.32rem; }
  .controles-navegador i { inline-size: 0.5rem; block-size: 0.5rem; border-radius: 50%; background: var(--ink-ghost); }
  .controles-navegador i:first-child { background: var(--color-rose-light); }
  .controles-navegador i:nth-child(2) { background: var(--color-amber-chart); }
  .controles-navegador i:last-child { background: var(--color-emerald-light); }
  .ruta-navegador { justify-self: center; max-inline-size: 100%; overflow: hidden; color: var(--ink-tertiary); font-size: 0.65rem; text-overflow: ellipsis; white-space: nowrap; }
  .acciones-navegador { justify-self: end; color: var(--ink-ghost); font-size: 0.7rem; letter-spacing: 0.08em; }
  .marco-computador :global(.captura-sistema .abrir-imagen) { aspect-ratio: 16 / 9; border-radius: 0; }
  .marco-computador :global(.captura-sistema .abrir-imagen img) { object-fit: contain; background: var(--surface-canvas); }

  .soporte-computador { display: grid; justify-items: center; block-size: 1.15rem; }
  .soporte-computador::before { inline-size: 16%; block-size: 0.86rem; background: linear-gradient(90deg, var(--surface-panel), var(--surface-paper), var(--surface-panel)); content: ''; clip-path: polygon(18% 0, 82% 0, 100% 100%, 0 100%); }
  .soporte-computador span { inline-size: 29%; block-size: 0.22rem; margin-block-start: -0.08rem; border-radius: 999px 999px 0.35rem 0.35rem; background: color-mix(in srgb, var(--surface-panel) 84%, var(--ink-primary)); }

  .marco-telefono {
    inline-size: min(100%, 20rem);
    padding: 0.42rem;
    border: 1px solid color-mix(in srgb, var(--trazo) 70%, transparent);
    border-radius: 2.65rem;
    background: linear-gradient(145deg,
      color-mix(in srgb, var(--surface-paper) 58%, white),
      color-mix(in srgb, var(--surface-panel) 78%, var(--ink-primary)) 30%,
      color-mix(in srgb, var(--surface-paper) 55%, var(--ink-primary)));
    box-shadow: 0 22px 44px color-mix(in srgb, var(--ink-primary) 20%, transparent),
      inset 0 0 0 1px color-mix(in srgb, white 28%, transparent);
    transition: transform 220ms ease, box-shadow 220ms ease;
  }

  .muestra-perfil:hover .marco-telefono {
    transform: translateY(-2px) rotate(0.35deg);
    box-shadow: 0 28px 52px color-mix(in srgb, var(--ink-primary) 24%, transparent),
      inset 0 0 0 1px color-mix(in srgb, white 28%, transparent);
  }

  .pantalla-telefono { overflow: hidden; border-radius: 2.25rem; background: var(--surface-zen); }
  .bisel-superior, .bisel-inferior { display: grid; place-items: center; background: var(--surface-zen); }
  .bisel-superior { block-size: 1.1rem; }
  .bisel-superior span { inline-size: 4.2rem; block-size: 0.62rem; border-radius: 999px; background: var(--surface-zen); box-shadow: inset 0 1px 2px var(--book-cover-thread); }
  .bisel-inferior { block-size: 0.9rem; }
  .bisel-inferior span { inline-size: 4.6rem; block-size: 0.18rem; border-radius: 999px; background: var(--cuenta-peligro-tinta); }
  .marco-telefono :global(.captura-sistema .abrir-imagen) { aspect-ratio: 390 / 844; border-radius: 0; }
  .marco-telefono :global(.captura-sistema .abrir-imagen img) { object-fit: contain; background: var(--surface-canvas); }

  .captura.formato-telefono .marco-telefono { inline-size: min(100%, 18rem); }
  .procedencia { margin: var(--espacio-sm) 0 0; color: var(--ink-tertiary); font-size: var(--texto-xs); line-height: var(--interlinea-normal); }

  .nota-alcance {
    margin: 0;
    padding-block-start: var(--espacio-md);
    border-block-start: 1px solid var(--trazo-suave);
    color: var(--ink-tertiary);
    font-size: var(--texto-xs);
    line-height: var(--interlinea-normal);
  }

  @media (max-width: 75rem) {
    .panel-recorrido { grid-template-columns: minmax(0, 1fr); gap: var(--espacio-xl); }
    .detalle-perfil { display: block; }
    .detalle-perfil h3 { max-inline-size: 48ch; }
    .resultado-perfil { margin-block-start: var(--espacio-lg); }
  }

  @media (max-width: 48rem) {
    .recorrido { inline-size: min(calc(100% - 2 * var(--espacio-md)), 82rem); padding-block: var(--espacio-2xl); }
    .pestanas-roles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--espacio-sm); margin-block-start: var(--espacio-xl); }
    .pestanas-roles button { min-inline-size: 0; min-block-size: 50px; font-size: var(--texto-sm); text-align: center; }
    .panel-recorrido { gap: var(--espacio-lg); padding-block: var(--espacio-lg); }
    .detalle-perfil { display: block; }
    .detalle-perfil h3 { max-inline-size: 24ch; font-size: var(--texto-xl); }
    .pasos-perfil { margin-block-start: var(--espacio-lg); }
    .resultado-perfil { margin-block-start: var(--espacio-lg); }
    .muestra-perfil { padding: var(--espacio-sm); border-radius: var(--radius-lg); }
    .controles-muestra { align-items: start; }
    .selector-dispositivo button { padding-inline: 0.5rem; }
    .marco-computador { padding: 0.42rem 0.42rem 0; border-radius: 0.95rem 0.95rem 0 0; }
    .bisel-computador { border-radius: 0.58rem 0.58rem 0 0; }
    .barra-navegador { min-block-size: 1.65rem; grid-template-columns: 2.6rem minmax(0, 1fr) 2.6rem; padding-inline: 0.45rem; }
    .soporte-computador { block-size: 0.9rem; }
    .soporte-computador::before { block-size: 0.65rem; }
    .marco-telefono { padding: 0.34rem; border-radius: 2.35rem; }
    .pantalla-telefono { border-radius: 1.98rem; }
    .marco-telefono :global(.captura-sistema) { inline-size: 100%; }
  }

  @media (prefers-reduced-motion: reduce) {
    .pestanas-roles button::after,
    .selector-dispositivo button,
    .marco-computador,
    .marco-telefono { transition: none; }
  }
</style>
