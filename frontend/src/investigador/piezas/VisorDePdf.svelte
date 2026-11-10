<!--
El visor del documento · `EQ-021` / C2B.

Recibe un `Blob` y lo pinta. **Es el único sitio de la aplicación que crea una
Object URL**, y por eso es el único que puede prometer que la revoca.

POR QUÉ LA OBJECT URL VIVE AQUÍ Y NO EN EL MÓDULO DE API
---------------------------------------------------------
Una `URL.createObjectURL()` no se recoge sola: vive hasta que alguien la revoca
o hasta que se cierra la pestaña, con el documento entero retenido en memoria y
alcanzable por cualquiera que sepa la dirección `blob:`. Lo que aquí se retiene
es la autorización firmada por el representante legal de un menor de edad.

`nucleo/api/evidencias.js` devuelve el `Blob` y no crea ninguna dirección a
propósito: no tiene ciclo de vida en el que revocarla. Este componente sí, y el
`$effect` de abajo lo usa entero — la función que devuelve se ejecuta **las dos
veces que hacen falta**: cuando cambia el documento (se pasa a otra evidencia) y
cuando el componente se desmonta (se cierra el detalle o se sale de la
pantalla). Sin él, revisar quince evidencias dejaría quince documentos vivos.

No se guarda en ningún almacén global, ni en `localStorage`, ni en la dirección
de navegación. La única referencia es la variable de este componente.

`<object>` Y NO `<iframe>` NI UNA BIBLIOTECA
----------------------------------------------
`DD-05` decidió HTML nativo primero, y para un PDF eso es `<object>`: el
navegador usa su propio visor, con su búsqueda, su zoom y su accesibilidad. Una
biblioteca de renderizado en JavaScript habría añadido megabytes y una superficie
nueva sobre un documento que `EQ-021` quiere custodiado, no procesado.

`<object>` pinta su contenido alternativo cuando no puede incrustar —es lo que
hace un navegador móvil que no trae visor—, y ahí va el enlace de apertura. No
lleva `download` con ningún nombre de persona: `evidencia-{id}.pdf` y nada más.



-->
<script>
  let {
    /** El `Blob` del PDF, o `null` mientras no se haya recuperado. */
    documento = null,
    /** Para el nombre del archivo. Nunca el sujeto ni el nombre de nadie. */
    evidencia = 0,
    /** Alto del visor. Prop para que el detalle decida, no este componente. */
    alto = '32rem'
  } = $props();

  let direccion = $state('');

  /**
   * La Object URL, creada y revocada por el mismo efecto.
   *
   * La lectura de `documento` es lo que hace que el efecto vuelva a correr al
   * cambiar de evidencia, y el `return` es lo que revoca la anterior antes de
   * crear la siguiente. Las dos mitades tienen que estar en el mismo efecto: si
   * la revocación viviera en un `onDestroy`, cambiar de evidencia sin desmontar
   * —que es el gesto normal de esta pantalla— no revocaría nada.
   */
  $effect(() => {
    if (!documento) {
      direccion = '';
      return;
    }
    const url = URL.createObjectURL(documento);
    direccion = url;
    return () => {
      URL.revokeObjectURL(url);
      // Se limpia también la variable: una dirección ya revocada en el marcado
      // es un `<object>` apuntando a nada, que el navegador pinta como error.
      direccion = '';
    };
  });

  const nombre = $derived(`evidencia-${Number(evidencia)}.pdf`);
</script>

{#if direccion}
  <object
    class="visor"
    data={direccion}
    type="application/pdf"
    style:block-size={alto}
    aria-label="Autorización del representante, evidencia {evidencia}"
  >
    <!-- Contenido alternativo: lo pinta el navegador que no puede incrustar. -->
    <div class="sin-visor">
      <p>Este navegador no puede mostrar el documento aquí dentro.</p>
      <a href={direccion} target="_blank" rel="noopener noreferrer" download={nombre}>
        Abrir la autorización en otra pestaña
      </a>
    </div>
  </object>
{/if}

<style>
  .visor {
    inline-size: 100%;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-md);
    background: var(--surface-panel);
  }

  .sin-visor {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--espacio-sm);
    padding: var(--espacio-xl);
    text-align: center;
  }

  .sin-visor p {
    margin: 0;
    font-size: var(--texto-sm);
    color: var(--ink-tertiary);
  }

  .sin-visor a {
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--accent-main);
  }
</style>
