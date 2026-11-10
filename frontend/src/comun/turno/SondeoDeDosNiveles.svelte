<!--
El ítem de dos niveles, dentro de la conversación · `RC-PED-06`.

Va **junto** a la respuesta del tutor y nunca en su lugar: el turno de arriba ya
contestó lo que el estudiante escribió, y esto es una pregunta corta que se
puede contestar o dejar pasar. `RF-GEN-03` prohíbe que la conversación se
convierta en evaluación, así que aquí no hay puntuación, ni marca de acierto, ni
cuenta atrás, ni obligación de responder para seguir.

QUÉ SE ENVÍA, Y ES TODO LO QUE SE PUEDE ENVIAR
------------------------------------------------
`nodo`, `resultado` y `razon`. **Ni `es_correcta`, ni la concepción, ni el
nivel**: quién acertó y qué delata cada razón lo resuelve el servidor contra su
banco. Si el cliente pudiera mandarlos, el estudiante se diagnosticaría a sí
mismo escribiendo un campo — la misma regla por la que `Señales` no viaja desde
el navegador.

Y por eso este componente **no sabe** cuál es la correcta. No la recibe: el
contrato §6.quater emite `{id, texto}` por razón y nada más.

POR QUÉ NO PARECE UN EXAMEN
-----------------------------
Tres decisiones, y las tres se pueden leer en el marcado:

  · **se puede seguir sin contestar.** «Sigo con lo mío» cierra el ítem y no
    manda nada. Ignorarlo tampoco cuesta: el tope de frecuencia del servidor
    aleja el siguiente en vez de acercarlo (`dominio/pedagogia/sondeo.py` §3);
  · **no hay veredicto en pantalla.** Al enviar, la conversación sigue con un
    turno normal del tutor. Nada se pinta en verde ni en rojo;
  · **el texto lo dice.** «Una pregunta corta, para ver por dónde va la duda»,
    no «responde a la siguiente pregunta».

ACCESIBILIDAD
---------------
Las cuatro razones son un `radiogroup` con `<fieldset>` y `<legend>`: se
recorren con las flechas, se anuncian como grupo y el enunciado del turno 1 es
el `legend` de su propio campo. El botón de enviar se deshabilita mientras no
haya razón elegida, y el motivo se dice con texto, no solo con el estado.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

-->
<script>
  let {
    /** { nodo, enunciado, razones: [{id, texto}] } — contrato §6.quater */
    sondeo,
    /**
     * ({nodo, resultado, razon}) => Promise<void> | void
     *
     * 🔴 **Paquete H · ahora se espera su resultado.** Antes se llamaba y el
     * ítem se cerraba en la misma línea, sin mirar si había llegado a algún
     * sitio. Si devuelve una promesa que rechaza, el ítem se queda abierto con
     * lo escrito dentro y se ofrece reintentar.
     */
    alResponder = () => {},
    /** Deshabilita mientras hay un turno en vuelo. */
    ocupado = false
  } = $props();

  let resultado = $state('');
  let razon = $state('');

  /**
   * En qué punto de la operación está este ítem · paquete H.
   *
   * 🔴 **El defecto que esto cierra.** Había un solo `cerrado = true`, puesto
   * **inmediatamente después** de llamar a `alResponder`. El ítem desaparecía
   * de la pantalla antes de que el servidor confirmara nada, así que un fallo
   * de red se llevaba por delante lo que el estudiante había escrito: la
   * respuesta y la razón elegida no existían en ningún otro sitio.
   *
   * Cuatro estados, y los cuatro se pueden ver en el marcado:
   *
   * | Estado | Qué significa | Qué se ve |
   * |---|---|---|
   * | `abierto` | se puede contestar | el formulario |
   * | `enviando` | la operación está en vuelo | el formulario, bloqueado, y un aviso |
   * | `confirmado` | el servidor lo recibió | nada: el ítem se cierra |
   * | `error` | no llegó | el formulario **con lo escrito** y un botón de reintentar |
   */
  let estado = $state('abierto');

  const razones = $derived(sondeo?.razones ?? []);
  const completo = $derived(resultado.trim() !== '' && razon !== '');
  const bloqueado = $derived(ocupado || estado === 'enviando');

  /**
   * El payload completo, conservado hasta la confirmación.
   *
   * Se construye una vez y se reusa en el reintento **tal cual**: reintentar
   * tiene que ser la misma operación, no una parecida armada otra vez con lo
   * que quede en pantalla.
   */
  let enviado = $state(null);

  async function entregar(payload) {
    estado = 'enviando';
    try {
      await alResponder(payload);
      estado = 'confirmado';
    } catch {
      // No se limpia nada: `resultado`, `razon` y `enviado` siguen donde
      // estaban, que es lo que permite reintentar sin volver a escribir.
      estado = 'error';
    }
  }

  function responder(evento) {
    evento.preventDefault();
    // El doble clic no pasa de aquí: mientras hay una operación en vuelo no se
    // abre otra, y `bloqueado` deshabilita además el botón.
    if (!completo || bloqueado) return;
    // Los tres campos del contrato y ni uno más. Ver la cabecera.
    enviado = { nodo: sondeo.nodo, resultado: resultado.trim(), razon };
    return entregar(enviado);
  }

  function reintentar() {
    if (bloqueado || !enviado) return;
    return entregar(enviado);
  }
</script>

{#if sondeo && estado !== 'confirmado'}
  <section class="sondeo" aria-label="Pregunta corta de diagnóstico">
    <p class="presentacion">
      Una pregunta corta, para ver por dónde va la duda. Puedes contestarla o
      seguir con lo tuyo.
    </p>

    <form onsubmit={responder}>
      <label class="calculo">
        <span class="enunciado">{sondeo.enunciado}</span>
        <input
          type="text"
          bind:value={resultado}
          disabled={bloqueado}
          autocomplete="off"
          spellcheck="false"
          placeholder="Escribe solo el resultado"
        />
      </label>

      <fieldset>
        <legend>¿Por qué ese resultado?</legend>
        {#each razones as opcion (opcion.id)}
          <label class="razon">
            <input
              type="radio"
              name="razon-{sondeo.nodo}"
              value={opcion.id}
              bind:group={razon}
              disabled={bloqueado}
            />
            <span>{opcion.texto}</span>
          </label>
        {/each}
      </fieldset>

      <div class="acciones">
        <button type="submit" disabled={!completo || bloqueado}>Responder</button>
        {#if estado === 'error'}
          <!-- Reintenta LA MISMA operación con el payload conservado, no una
               nueva armada con lo que quede en pantalla. -->
          <button type="button" class="reintentar" onclick={reintentar}>
            Reintentar
          </button>
        {/if}
        <button type="button" class="omitir" onclick={() => (estado = 'confirmado')}>
          Sigo con lo mío
        </button>
      </div>

      <!-- El estado de la operación se anuncia con texto y con `aria-live`, no
           sólo deshabilitando controles: quien no ve el botón atenuado tiene
           que enterarse igual de que su respuesta está en vuelo o no llegó. -->
      <p class="pista" aria-live="polite">
        {#if estado === 'enviando'}
          Enviando tu respuesta…
        {:else if estado === 'error'}
          No se pudo enviar. Tu respuesta sigue aquí: puedes reintentarlo.
        {:else if !completo}
          Escribe el resultado y elige una razón para poder enviarlo.
        {/if}
      </p>
    </form>
  </section>
{/if}

<style>
  /*
    NO ES UN EXAMEN, Y LA FORMA TAMBIÉN LO DICE.

    Papel apoyado del mismo material que el resto de la conversación, con el
    radio trazado del lenguaje y sin ningún color de estado: nada de verde, de
    rojo ni de iconografía de evaluación. `--trazo-suave` es el token del canto
    de una REGIÓN —lo que esto es—; los controles de dentro llevan `--trazo`,
    que es el que `WCAG 2.2 · 1.4.11` mide.

    Ningún literal de color: `tokens.css` es el único sitio donde uno es
    legítimo, y `pruebas/accesibilidad/contraste.prueba.js` lo comprueba.
  */
  .sondeo {
    margin-block-start: var(--espacio-sm);
    padding: var(--espacio-md);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-trazado);
    background: var(--surface-panel);
  }

  .presentacion {
    margin: 0 0 var(--espacio-sm);
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
  }

  .calculo {
    display: block;
    margin-block-end: var(--espacio-md);
  }

  .enunciado {
    display: block;
    margin-block-end: 0.35rem;
    font-weight: 600;
  }

  .calculo input {
    inline-size: 100%;
    min-block-size: 44px;
    padding: 0.4em 0.7em;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-trazado);
    background: var(--surface-paper);
    font: inherit;
  }

  fieldset {
    margin: 0 0 var(--espacio-md);
    padding: 0;
    border: 0;
  }

  legend {
    padding: 0;
    margin-block-end: 0.35rem;
    font-weight: 600;
    font-size: var(--texto-sm);
  }

  .razon {
    display: flex;
    gap: 0.5rem;
    align-items: flex-start;
    padding: 0.35rem 0;
    font-size: var(--texto-sm);
    cursor: pointer;
  }

  .acciones {
    display: flex;
    gap: var(--espacio-sm);
    flex-wrap: wrap;
  }

  button {
    min-block-size: 44px;
    padding: 0.4em 0.9em;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-trazado);
    background: var(--surface-paper);
    font-size: var(--texto-sm);
    transition: var(--transition-fast);
  }

  button:hover:not([disabled]) {
    border-color: var(--accent-main);
    color: var(--accent-main);
  }

  button[disabled] {
    color: var(--ink-tertiary);
    cursor: not-allowed;
  }

  .pista {
    margin: var(--espacio-sm) 0 0;
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
    /* La región viva se reserva su alto para que aparecer un aviso no
       desplace el formulario bajo el dedo de quien está contestando. */
    min-block-size: 1.5em;
  }
</style>
