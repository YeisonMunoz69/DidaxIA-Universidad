<!--
El envoltorio de scroll de una pantalla de docente · extraído el 2026-08-22.

Bug real, no solo estética — confirmado en el navegador antes de que
existiera este arreglo: `<main id="contenido">` (`Aplicacion.svelte`) trae
`overflow: hidden`, y ninguna de las rutas de docente ponía `overflow-y:
auto` en su elemento raíz. A 1440×700 con veinte ítems en la cola de
supervisión, el contenido medía 6037px dentro de una caja de 645px de
alto — sin barra de scroll en NINGÚN nivel, así que ~5400px quedaban
inalcanzables sin que nada en pantalla lo delatara.

DOS CAPAS, Y LAS DOS IMPORTAN
--------------------------------
`.desplazable` es quien scrollea, A ANCHO COMPLETO. `.contenido` solo centra
y acolcha. Si las dos cosas —`overflow-y: auto` y `max-inline-size`— vivieran
en el MISMO elemento, la barra de scroll aparecería en el borde de la
columna centrada y no en el borde real de la ventana — reportado como «la
barra de scroll no quedó pegada al borde» la primera vez que se escribió
esto, antes de partirlo en dos capas.

ESTE ARCHIVO REEMPLAZA CUATRO COPIAS CASI IDÉNTICAS, no una decisión nueva:
`ColaDeSupervision.svelte`, `VistaDelGrupo.svelte`, `FichaDeEstudiante.svelte`
y `ContextoCurricular.svelte` tenían cada una su propio `.X-desplazable` +
`.X` con el mismo CSS, byte a byte salvo el ancho máximo, el relleno y el
espaciado entre hijos — que es justo lo que `anchoMaximo`/`relleno`/`espacio`
parametrizan. `MisClases.svelte` NO usa esto: es la única pantalla de
docente con dos paneles de scroll independiente en vez de una columna
entera que se desplaza, y forzarla a este molde sería inventarle una
estructura que no tiene.



-->
<script>
  let {
    /** `max-inline-size` de la columna centrada, ya envuelto en `min(...)`
        si hace falta. 78rem es lo que ya usan tres de las cuatro pantallas
        que usan este envoltorio. */
    anchoMaximo = 'min(78rem, 100%)',
    /** `padding` del contenido, shorthand de CSS tal cual. */
    relleno = 'var(--espacio-xl) var(--espacio-lg)',
    /** `gap` entre los hijos directos del contenido. */
    espacio = 'var(--espacio-lg)',
    children
  } = $props();
</script>

<div class="desplazable">
  <section
    class="contenido"
    style:max-inline-size={anchoMaximo}
    style:padding={relleno}
    style:gap={espacio}
  >
    {@render children()}
  </section>
</div>

<style>
  .desplazable {
    flex: 1;
    min-block-size: 0;
    overflow-y: auto;
    inline-size: 100%;
  }

  .contenido {
    display: flex;
    flex-direction: column;
    margin-inline: auto;
    animation: entrarVista 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  }

  /* La espera ocupa también el espacio restante bajo cabecera/filtros.
     Sólo durante la carga: no cambia la altura de las tarjetas ya resueltas. */
  .contenido:has(> :global(.cargador-cubo.pantalla-completa)) {
    min-block-size: 100%;
    box-sizing: border-box;
  }

  @keyframes entrarVista {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @media (prefers-reduced-motion: reduce) {
    .contenido { animation: none; }
  }
</style>
