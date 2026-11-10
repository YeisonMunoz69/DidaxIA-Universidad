<!--
La única acción visible del recorrido · `D0` §10.10 / `D1B`.

⚠️ QUÉ SUSTITUYE, Y POR QUÉ NO SE PODÍA CONSERVAR
---------------------------------------------------
`DecisionDeConsentimiento.svelte` pintaba **una dimensión**: se montaba una vez
para el titular y otra para el asentimiento del menor, con dos botones cada una
y una petición cada una. Eso ponía en el navegador una secuencia que `D0` §10.10
descarta: para un menor, entre la primera respuesta y la segunda petición cabía
—y ocurría— el estado que nadie decidió.

Ese componente está **eliminado**, no desactivado. Un componente productivo
muerto es el que alguien vuelve a montar dentro de seis meses.

UNA DECISIÓN BREVE, CON EL DOCUMENTO EXACTO DISPONIBLE
------------------------------------------------------
Privacidad, condiciones, participación en la investigación y medición
conductual forman el paquete versionado del titular (`D0` §10.10), no cuatro
decisiones separadas. La pantalla explica la decisión sin repetir el documento
completo y ofrece el texto exacto, identificado por código y huella, en una
pestaña autenticada aparte. Los enlaces públicos generales permanecen en el pie.

UNA PETICIÓN, Y SE COMPRUEBA
------------------------------
`alDecidir()` se llama **una vez** por decisión. No hay `Promise.all`, no hay
encadenamiento y no hay una segunda llamada para el asentimiento: los actos que
correspondan los escribe el servidor en una transacción. `enviando` cierra la
puerta a un segundo envío mientras la primera vuela.

SIN VERSIÓN PUBLICADA NO SE PUEDE ACEPTAR, Y SE DICE CUÁL FALTA
-----------------------------------------------------------------
Si `GET /api/consentimiento/versiones` devuelve `null` para un alcance requerido,
no existe un texto decidible. Un adulto necesita la del titular; un menor,
la del titular **y** la del asentimiento. Las dos acciones quedan desactivadas y
se nombra lo que falta, en vez de redactar un texto de relleno —que sería la
autorización fabricada que toda la Fase 3 existe para no crear—.

DOS CONDICIONES DISTINTAS, Y NINGUNA SE DEDUCE AQUÍ · `D1B` bis
------------------------------------------------------------------
Para ofrecer una acción hacen falta **dos** cosas, y son independientes:

1. **que exista el documento** — lo dice `versiones`, y sin él no hay nada que
   aceptar;
2. **que la política admita esa decisión** — lo dice `estado.decision`, que el
   servidor resuelve con `dominio/modelo/redecision.py`.

La segunda no se puede deducir mirando banderas desde el navegador, y ése era el
riesgo: con el par otorgado y al día, «No acepto» **no** es una acción —para
retirar lo autorizado está la revocación—, y tras revocar una sola dimensión sí
lo son las dos. Una regla escrita aquí y otra en el servidor habrían acabado
diciendo cosas distintas, y la que la persona vería sería la equivocada.

Por eso `puedeAceptar` y `puedeRechazar` **llegan como props**. Este componente
las combina con la publicación del documento y no las calcula.



-->
<script>
  import CargadorCubo from '../../../comun/base/CargadorCubo.svelte';
  import Boton from '../../../comun/base/Boton.svelte';
  import Icono from '../../../comun/base/Icono.svelte';
  import Dialogo from '../../../comun/base/Dialogo.svelte';
  import { hayVersion, textoDeVersion } from '../../../nucleo/api/consentimiento.js';

  let {
    /** Si esta persona es menor de edad, según la edad PERSISTIDA. */
    esMenor = false,
    /** La versión requerida del paquete del titular, o `null`. */
    versionTitular = null,
    /** La versión requerida del asentimiento, o `null`. Sólo aplica al menor. */
    versionAsentimiento = null,
    /** `async (decision) => void`. `decision` es `otorgado` o `rechazado`. */
    alDecidir,
    /** Lo que dijo el servidor si rechazó la última decisión. */
    errorDelServidor = '',
    /** Si el servidor dijo que falta alguna versión al intentar registrar. */
    sinVersion = false,
    /** Qué alcances nombró el servidor como faltantes. Lista cerrada. */
    alcancesFaltantes = [],
    /**
     * Si la política del servidor admite aceptar ahora. **No se calcula aquí.**
     * Por defecto `true` para que un estado sin el campo —una respuesta vieja—
     * no bloquee el recorrido: la autoridad real sigue siendo el servidor, que
     * responde 409 si no lo admite.
     */
    puedeAceptar = true,
    /** Lo mismo para «No acepto». Ver la cabecera. */
    puedeRechazar = true,
    /** Lo que el servidor dijo cuando negó la última decisión por política. */
    motivoDeLaPolitica = ''
  } = $props();

  /**
   * Qué alcances necesita ESTA persona, con cómo se nombra cada uno.
   *
   * `rotulo` encabeza la fila del documento; `nombre` es cómo se lee dentro de
   * una frase —«falta que se publique el texto de …»—. Son dos porque un rótulo
   * de tabla y un sintagma en mitad de una oración no se escriben igual, y usar
   * uno para las dos cosas dejaba frases que no se pueden leer.
   *
   * La edad la decide el servidor: aquí sólo se recibe si es menor.
   */
  const requeridas = $derived(
    esMenor
      ? [
          {
            alcance: 'titular',
            rotulo: 'Documento que autorizas',
            nombre: 'la autorización del tratamiento',
            version: versionTitular
          },
          {
            alcance: 'asentimiento',
            rotulo: 'Tu propio acuerdo',
            nombre: 'tu propio acuerdo como menor de edad',
            version: versionAsentimiento
          }
        ]
      : [
          {
            alcance: 'titular',
            rotulo: 'Documento que autorizas',
            nombre: 'la autorización del tratamiento',
            version: versionTitular
          }
        ]
  );

  /** Las que faltan por publicar. Vacío significa que hay documento. */
  const faltantes = $derived(requeridas.filter((r) => !hayVersion(r.version)));
  const publicadas = $derived(faltantes.length === 0);

  /**
   * Los documentos que esta pantalla intentó mostrar y no pudo · `C1-A`.
   *
   * ⚠️ **Esto NO es lo que impide aceptar sin documento.** Lo impide el
   * servidor: desde la migración 14 una versión sin instantánea válida no es la
   * requerida —así que ni siquiera llega aquí— y el disparador de la base
   * rechaza cualquier acto contra ella, venga de donde venga.
   *
   * Lo que esto aporta es que la persona no pulse un botón que va a ser
   * rechazado sin entender por qué. Si el documento no se pudo leer, no se
   * ofrece decidir sobre él.
   */
  let documentosRotos = $state({});
  let documentosComprobados = $state(false);
  const hayDocumentoRoto = $derived(Object.keys(documentosRotos).length > 0);

  /*
   * La pantalla queda breve, pero no pierde el fallo cerrado de C1-A. Se pide
   * el documento en segundo plano y se contrasta con la huella publicada antes
   * de habilitar las acciones. La lectura visible ocurre en otra pestaña.
   */
  $effect(() => {
    const documentos = publicadas
      ? requeridas.map((r) => ({ codigo: r.version.codigo, huella: r.version.huella_contenido }))
      : [];
    let vigente = true;
    documentosRotos = {};
    documentosComprobados = false;
    if (!documentos.length) return;

    Promise.allSettled(documentos.map(async ({ codigo, huella }) => {
      const recibido = await textoDeVersion(codigo);
      if (!recibido?.cuerpo || recibido.huella_contenido !== huella) {
        throw new Error('el documento no corresponde a la huella publicada');
      }
      return codigo;
    })).then((resultados) => {
      if (!vigente) return;
      const rotos = {};
      resultados.forEach((resultado, i) => {
        if (resultado.status === 'rejected') {
          rotos[documentos[i].codigo] = resultado.reason?.message || 'no se pudo cargar';
        }
      });
      documentosRotos = rotos;
      documentosComprobados = true;
    });

    return () => { vigente = false; };
  });

  /**
   * Cada acción, con sus DOS condiciones: documento publicado y política.
   *
   * Separadas a propósito: la persona necesita saber cuál de las dos falta.
   * «Todavía no hay texto» y «esto ya está registrado» se arreglan de formas
   * distintas, y fundirlas en un botón gris sin explicación deja a quien lo mira
   * sin saber qué hacer.
   */
  const aceptarDisponible = $derived(
    publicadas && documentosComprobados && !hayDocumentoRoto && puedeAceptar && !enviando
  );
  const rechazarDisponible = $derived(
    publicadas && documentosComprobados && !hayDocumentoRoto && puedeRechazar && !enviando
  );

  let enviando = $state(false);
  /** `''`, `otorgado` o `rechazado`: qué confirmación está abierta. */
  let confirmando = $state('');

  function pedir(decision) {
    const disponible = decision === 'otorgado' ? aceptarDisponible : rechazarDisponible;
    if (!disponible) return;
    confirmando = decision;
  }

  async function confirmar() {
    // Un segundo clic mientras la primera petición vuela crearía OTRO juego de
    // actos: el servidor recibiría dos decisiones del mismo sujeto y la segunda
    // llegaría sobre un estado que ya cambió. Se cierra la puerta aquí, y el
    // servidor la vuelve a cerrar con su cerrojo por titular.
    if (enviando) return;
    const decision = confirmando;
    enviando = true;
    try {
      await alDecidir(decision);
      confirmando = '';
    } catch {
      // Lo redacta la composición con el motivo del servidor. Se cierra el
      // diálogo para que el mensaje quede a la vista.
      confirmando = '';
    } finally {
      enviando = false;
    }
  }

  /** Cómo se nombra cada alcance faltante delante de una persona. */
  const NOMBRE_DE_ALCANCE = {
    titular: 'la autorización del tratamiento',
    asentimiento: 'tu propio acuerdo como menor de edad',
    representante: 'la autorización de tu representante'
  };

  const faltantesDelServidor = $derived(
    alcancesFaltantes.map((a) => NOMBRE_DE_ALCANCE[a] ?? a).join(' y ')
  );
</script>

<section class="decision" aria-labelledby="titulo-decision">
  <h2 id="titulo-decision">Lo que vas a aceptar</h2>
  <p class="intro">
    Para usar el tutor debes decidir sobre el tratamiento de tus datos y la
    participación descrita en el documento vigente. No hay nada marcado de antemano.
  </p>

  {#if publicadas}
    <div class="documento">
      {#each requeridas as requerida (requerida.alcance)}
        <a
          class="leer-documento"
          href={`/consentimiento?documento=${encodeURIComponent(requerida.version.codigo)}`}
          target="_blank"
          rel="noopener">
          Leer {requerida.nombre} completo en otra pestaña
        </a>
        <details class="datos-version">
          <summary>Ver código y huella de la versión</summary>
          <p><span class="etiqueta">Versión</span> <span class="monoespaciado">{requerida.version.codigo}</span></p>
          <p><span class="etiqueta">SHA-256</span> <span class="monoespaciado huella">{requerida.version.huella_contenido}</span></p>
        </details>
      {/each}
      {#if !documentosComprobados}
        <CargadorCubo mensaje="Comprobando el documento publicado…" compacto />
      {/if}
      {#if hayDocumentoRoto}
        <!--
          `C1-A` · falla cerrado y lo dice. No se esconden los botones: se
          explican, porque quien no entiende por qué no puede decidir vuelve a
          intentarlo en vez de avisar de que algo va mal.
        -->
        <p class="documento-roto" role="alert">
          No se pudo mostrar el documento completo, o no coincide con su huella.
          <strong>No puedes aceptar ni rechazar</strong> algo que no has podido
          leer. Vuelve a cargar la página; si sigue igual, avisa al equipo.
        </p>
      {/if}
    </div>
  {:else}
    <!--
      El caso REAL de este árbol: no hay ningún texto aprobado. No es un error
      del cliente ni algo que reintentar, y no se rellena con un texto de
      relleno: no existe todavía un documento sobre el que decidir.
    -->
    <div class="sin-version" role="note">
      <div class="sin-version-titulo">
        <Icono nombre="candado" medida={14} />
        <strong>Todavía no puedes decidir</strong>
      </div>
      <p>
        Falta que se publique el texto de
        {#each faltantes as falta, i (falta.alcance)}{i > 0 ? ' y de ' : ''}<strong>{falta.nombre}</strong>{/each}.
        Sin ese texto no se puede aceptar ni rechazar nada, porque no existe
        todavía aquello sobre lo que decidirías.
      </p>
      <p>
        No es un fallo del sistema ni algo que puedas resolver tú. Cuando esté
        publicado, aquí aparecerá su código, su huella y esta misma decisión.
      </p>
    </div>
  {/if}

  {#if sinVersion}
    <p class="error-servidor" role="alert">
      No se registró tu decisión porque falta publicar
      {faltantesDelServidor || 'alguno de los documentos necesarios'}.
      <strong>No se guardó nada.</strong>
    </p>
  {:else if motivoDeLaPolitica}
    <p class="error-servidor" role="alert">
      {motivoDeLaPolitica} <strong>No se guardó nada.</strong>
    </p>
  {:else if errorDelServidor}
    <p class="error-servidor" role="alert">{errorDelServidor}</p>
  {/if}

  <div class="acciones">
    <Boton onclick={() => pedir('otorgado')} deshabilitado={!aceptarDisponible}>
      <Icono nombre="check" medida={15} />
      Acepto y continuar
    </Boton>
    <Boton
      variante="secundario"
      onclick={() => pedir('rechazado')}
      deshabilitado={!rechazarDisponible}
    >
      No acepto
    </Boton>
  </div>

  {#if !publicadas}
    <p class="motivo-desactivado">
      Las dos opciones están desactivadas mientras falte un documento por publicar.
    </p>
  {:else if !puedeAceptar && !puedeRechazar}
    <p class="motivo-desactivado">
      Tu decisión ya está registrada sobre los documentos que rigen ahora. Para
      retirarla, usa «Mis datos»: retirar una autorización es un acto distinto
      de decidir, y tiene su propio trámite.
    </p>
  {:else if !puedeRechazar}
    <p class="motivo-desactivado">
      «No acepto» no está disponible porque no hay ninguna autorización nueva
      pendiente. Lo que ya autorizaste se retira desde «Mis datos».
    </p>
  {/if}
</section>

<Dialogo
  abierto={Boolean(confirmando)}
  titulo={confirmando === 'otorgado' ? '¿Confirmas que aceptas?' : '¿Confirmas que no aceptas?'}
>
  {#if confirmando === 'otorgado'}
    <p>
      Quedará registrado que aceptaste las cuatro partes: privacidad,
      condiciones, participación en la investigación y la medición que
      personaliza el tutor.
      {#if esMenor}
        Como eres menor de 18 años se registran <strong>dos constancias</strong>:
        la autorización del tratamiento y tu propio acuerdo. Aun así seguirá
        faltando la autorización firmada de tu representante.
      {/if}
      Podrás retirarlo cuando quieras desde «Mis datos».
    </p>
  {:else}
    <p>
      Sin esta autorización el tutor no puede funcionar y quedará bloqueado.
      Conservarás únicamente las páginas públicas y podrás volver a decidir más
      adelante.
      {#if esMenor}
        Se registrará tu negativa en las dos dimensiones que te aplican.
      {/if}
      Tu decisión se registra y no se borra nada de lo que ya exista.
    </p>
  {/if}
  {#if publicadas}
    <p class="version-en-dialogo">
      Se registrará sobre
      {#each requeridas as requerida, i (requerida.alcance)}{i > 0 ? ' y ' : ' '}<strong>{requerida.version.codigo}</strong>{/each},
      que {requeridas.length === 1 ? 'es la versión que rige' : 'son las versiones que rigen'}
      ahora. Las elige el servidor, no esta pantalla.
    </p>
  {/if}
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (confirmando = '')} deshabilitado={enviando}>
      Volver
    </Boton>
    <Boton onclick={confirmar} deshabilitado={enviando}>
      {enviando ? 'Registrando…' : 'Sí, confirmar'}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  .decision { display: flex; flex-direction: column; gap: 10px; }

  h2 {
    margin: 0;
    font-size: var(--texto-lg);
    font-weight: 700;
    color: var(--ink-primary);
    line-height: 1.25;
  }

  .intro {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.5;
    color: var(--ink-secondary);
  }

  .documento {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px 12px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
  }

  .leer-documento {
    align-self: flex-start;
    color: var(--accent-main);
    font-size: var(--texto-sm);
    font-weight: 650;
  }

  .datos-version {
    font-size: var(--texto-xs);
    color: var(--ink-secondary);
  }

  .datos-version summary { cursor: pointer; }
  .datos-version p { margin: 6px 0 0; }

  .etiqueta {
    font-size: var(--texto-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-tertiary);
  }

  .monoespaciado {
    font-family: var(--fuente-mono, ui-monospace, monospace);
    font-size: var(--texto-sm);
    color: var(--ink-primary);
  }

  .huella { font-size: var(--texto-xs); overflow-wrap: anywhere; user-select: all; }

  .documento-roto {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--semantic-error);
  }

  .sin-version {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-inline-start: 3px solid var(--ink-tertiary);
    border-radius: var(--radius-sm);
  }

  .sin-version-titulo {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: var(--texto-sm);
    color: var(--ink-primary);
  }

  .sin-version p {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  .error-servidor {
    margin: 0;
    padding: 8px 10px;
    font-size: var(--texto-sm);
    line-height: 1.4;
    color: var(--semantic-error);
    background: var(--surface-paper);
    border: 1px solid var(--semantic-error);
    border-radius: var(--radius-xs);
  }

  .error-servidor::before { content: '⚠ '; }

  .acciones { display: flex; flex-wrap: wrap; gap: 8px; }

  .motivo-desactivado {
    margin: 0;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  .version-en-dialogo { color: var(--ink-secondary); font-size: var(--texto-sm); }

  @media (max-width: 30rem) {
    .acciones { flex-direction: column; }
    .acciones :global(.boton) { inline-size: 100%; }
  }
</style>
