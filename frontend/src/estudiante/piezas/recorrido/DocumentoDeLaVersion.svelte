<!--
DocumentoDeLaVersion.svelte — El texto exacto que se está aceptando · `§8`

Lo que este componente existe para arreglar
-------------------------------------------------
`DecisionConjunta.svelte` afirma que «la huella identifica el texto exacto que
estás leyendo». Hasta la revisión R2 esa frase era falsa: lo único que la
pantalla ofrecía abrir eran cuatro enlaces a las páginas públicas del sitio
—genéricas, editables, sin relación con la huella—, y el documento hasheado no
se podía leer desde la aplicación. La huella identificaba un artefacto que la
persona nunca veía.

Esto trae ese artefacto: pide `GET /api/consentimiento/version/{codigo}/texto`,
que el servidor sólo responde después de recalcular el SHA-256 y comprobar que
coincide con la huella publicada.

Cuándo se pide
--------------
En el resumen compacto se carga cuando la persona pide leerlo. En la página
dedicada (`pagina`) se carga al montar porque esa ruta existe exclusivamente
para mostrar el texto exacto en una pestaña autenticada aparte.

Qué hace si falla · **fallo cerrado, y visible**
-----------------------------------------------------
No se inventa un texto de relleno y no se esconde el error. Si el servidor
responde `409` —el documento almacenado no corresponde a la huella— eso se dice
con esas palabras: es exactamente la situación que invalidaría la decisión, y
callarla sería peor que no ofrecer el documento.



-->
<script>
  import CargadorCubo from '../../../comun/base/CargadorCubo.svelte';
  import Boton from '../../../comun/base/Boton.svelte';
  import MarkdownSeguro from '../../../comun/base/MarkdownSeguro.svelte';
  import { textoDeVersion } from '../../../nucleo/api/consentimiento.js';

  let {
    /** El código de la versión cuyo documento se ofrece. */
    codigo = '',
    /** Cómo se nombra este documento en pantalla. */
    rotulo = 'documento',
    /**
     * `(codigo, motivo) => void` · se llama cuando el documento NO se pudo
     * mostrar · `C1-A`.
     *
     * Sirve para que la pantalla que contiene esto pueda fallar cerrada. **No
     * es la barrera**: quien impide aceptar sin documento es el servidor —desde
     * la migración 14 una versión sin instantánea válida no es la requerida y
     * el disparador rechaza el acto—. Esto evita que la persona pulse un botón
     * que va a ser rechazado y no entienda por qué.
     */
    alFallarElDocumento = () => {},
    /** Vista independiente, autenticada, abierta desde la decisión. */
    pagina = false
  } = $props();

  let abierto = $state(false);
  let cargando = $state(false);
  let documento = $state(null);
  let error = $state('');

  /**
   * Trae el documento la primera vez que se abre.
   *
   * No se reintenta solo: un fallo aquí puede ser el `409` de huella que no
   * corresponde, y reintentarlo en bucle escondería justo lo que hay que ver.
   */
  async function abrir() {
    abierto = true;
    if (documento || cargando) return;
    cargando = true;
    error = '';
    try {
      documento = await textoDeVersion(codigo);
    } catch (fallo) {
      error =
        fallo?.datos?.detalle ||
        'No se pudo cargar el documento. No aceptes nada que no hayas podido leer.';
      alFallarElDocumento(codigo, error);
    } finally {
      cargando = false;
    }
  }

  $effect(() => {
    if (pagina && codigo) abrir();
  });
</script>

{#if codigo}
  <div class="documento-version" class:pagina>
    {#if !abierto && !pagina}
      <Boton variante="secundario" onclick={abrir}>Leer el {rotulo} completo</Boton>
    {:else}
      <div class="marco">
        {#if cargando}
          <CargadorCubo mensaje="Cargando el documento…" pantallaCompleta />
        {:else if error}
          <!--
            El error se enseña tal cual lo dijo el servidor. Un `409` significa
            que lo guardado no corresponde a la huella publicada, y esa frase
            es la que hace falta para que nadie acepte a ciegas.
          -->
          <p class="estado error" role="alert">{error}</p>
        {:else if documento && pagina}
          <MarkdownSeguro texto={documento.cuerpo} />
          <p class="pie">
            <span class="etiqueta">Huella SHA-256 de este texto</span>
            <span class="monoespaciado huella">{documento.huella_contenido}</span>
          </p>
        {:else if documento}
          <!--
            `M5` · el punto de referencia y el foco viven en el elemento que
            DESPLAZA, no en el marco de fuera.

            Antes `role="region"` estaba en `.marco` y el `<pre>` —que es el que
            tiene `max-height` y `overflow-y: auto`— no era enfocable. Con sólo
            teclado no había forma de desplazar el texto: se podía abrir el
            documento y no se podía leer entero. En la pantalla donde alguien
            **debe poder leer antes de consentir**, eso no es cosmético.

            Un `tabindex="0"` en el marco no habría servido: el navegador
            desplaza el elemento con overflow que tiene el foco, y el marco no
            desplaza nada. Y añadir aquí una segunda `region` anidada habría
            duplicado el punto de referencia, así que la etiqueta se mueve con
            el papel en vez de repetirse.
          -->
          <!-- svelte-ignore a11y_no_noninteractive_tabindex
               El aviso es correcto como regla general y falso aquí, por el
               mismo motivo que en `comun/base/Tabla.svelte`: una región que se
               desplaza TIENE que poder recibir foco, o quien navega por teclado
               no puede desplazarla —WCAG 2.1.1 lo exige—. La pauta de la WAI
               para regiones desplazables es exactamente ésta: role, nombre
               accesible y tabindex 0. -->
          <pre
            class="cuerpo"
            tabindex="0"
            role="region"
            aria-label={`Texto completo del ${rotulo}`}>{documento.cuerpo}</pre>
          <p class="pie">
            <span class="etiqueta">Huella de este texto</span>
            <span class="monoespaciado huella">{documento.huella_contenido}</span>
          </p>
          <p class="nota">
            Es el SHA-256 del documento que acabas de leer. Puedes copiarlo y
            comprobarlo por tu cuenta; queda guardado con tu decisión.
          </p>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .documento-version {
    margin-top: 8px;
  }

  .marco {
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    background: var(--surface-paper);
  }

  .documento-version.pagina .marco { padding: clamp(1rem, 3vw, 2.5rem); }

  .cuerpo {
    /* El documento se enseña tal cual llegó: sin reformatear, porque lo que se
       lee tiene que ser lo que se hasheó. */
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    max-height: 24rem;
    overflow-y: auto;
    margin: 0;
    font-family: inherit;
    font-size: var(--texto-sm);
    line-height: 1.55;
  }

  /* `M5` · aquí NO se estiliza el foco a propósito. `estilos/base.css` ya da
     a todo `:focus-visible` un contorno de `--accent-main` y a todo
     `[tabindex]` un `scroll-margin-block`, y ese archivo dice por qué se
     aplica al elemento nativo: para no tener que recordarlo en cada
     componente. Repetirlo aquí crearía un segundo sitio donde el aro de foco
     puede divergir del resto de la aplicación. */

  .estado {
    margin: 0;
    font-size: var(--texto-sm);
  }

  .error {
    color: var(--semantic-error);
  }

  .pie {
    margin: 10px 0 0;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .etiqueta {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  .huella {
    font-size: var(--texto-xs);
    overflow-wrap: anywhere;
    user-select: all;
  }

  .nota {
    margin: 8px 0 0;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }
</style>
