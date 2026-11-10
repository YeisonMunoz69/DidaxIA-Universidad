<!--
La cabecera de una ruta de docente · extraída el 2026-08-22.

`<h1>` + insignia-píldora en la misma línea, con una nota opcional debajo y
un hueco opcional a la derecha para una acción (un botón, un contador) — el
mismo bloque, con el mismo CSS, vivía copiado en las cinco rutas de docente
(`ColaDeSupervision`, `MisClases`, `VistaDelGrupo`, `FichaDeEstudiante`,
`ContextoCurricular`). Cada copia llevaba un comentario apuntando a las
otras cuatro («mismo arreglo que MisClases.svelte::.titulo-y-insignia, ver
su comentario») — la propia duplicación ya se sabía a sí misma duplicación.

QUÉ CAMBIA DE VERDAD, Y POR QUÉ ES SEGURO
--------------------------------------------
En `MisClases.svelte`, el botón «Crear clase» centraba antes contra el
bloque título+insignia+nota completo (dos líneas); aquí `accion` se pinta
junto al título y la nota queda DEBAJO de esa fila, como ya hacía
`ColaDeSupervision.svelte`. El botón queda centrado contra una fila más
baja —un cambio de posición de unos pocos píxeles, no de comportamiento—,
y unifica el mismo gesto que las dos pantallas con acción ya compartían por
separado.



-->
<script>
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import Icono from '../../comun/base/Icono.svelte';

  let {
    /** Texto del `<h1>`. Puede ser dinámico —`FichaDeEstudiante.svelte` le
        pasa el nombre del estudiante cuando lo tiene. */
    titulo,
    ayuda = '',
    /** Nombre del icono de `Icono.svelte` para la insignia-píldora. */
    icono,
    /** Texto de la insignia-píldora. */
    insignia,
    /** Contenido opcional a la derecha de título+insignia — un botón, un
        contador. Sin esto, el título ocupa la fila entera. */
    accion,
    /** Párrafo opcional debajo de la fila de título — puede traer
        `<strong>`. Sin esto, la cabecera es solo título+insignia. */
    nota,
    /** `MisClases.svelte::.frontera` es la única nota que se lee más grande
        y menos apagada que las demás —`--texto-base`/`--ink-secondary` en
        vez de `--texto-sm`/`--ink-tertiary`—, a propósito: es la única
        pantalla de docente donde ese párrafo hace de subtítulo explicativo
        y no de nota al margen. No es una talla nueva inventada al
        extraer este componente, es la que ya tenía antes. */
    notaGrande = false
  } = $props();
</script>

<header class="cabecera-de-ruta">
  <div class="fila-titulo">
    <div class="titulo-y-insignia">
      <h1>{titulo}</h1>
      <span class="insignia-modulo">
        <Icono nombre={icono} medida={13} />
        <span>{insignia}</span>
      </span>
      {#if ayuda}<BotonAyudaTooltip texto={ayuda} ariaLabel={`Ayuda sobre ${titulo}`} />{/if}
    </div>
    {#if accion}
      {@render accion()}
    {/if}
  </div>
  {#if nota}
    <p class="nota" class:grande={notaGrande}>{@render nota()}</p>
  {/if}
</header>

<style>
  .cabecera-de-ruta {
    /* `flex-shrink: 0`: preserva la garantía que `MisClases.svelte::
       .cabecera-clases` ya tenía —es la única pantalla de docente sin su
       propio scroll de página (`.clases { overflow: hidden }`, dos paneles
       con scroll propio en vez de uno)—, así que su cabecera es la única
       que de verdad podría comprimirse si el contenedor se queda corto de
       alto. Inocuo para las otras cuatro rutas, que viven dentro de un
       envoltorio que scrollea entero y nunca fuerzan a su cabecera a
       encogerse. */
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .fila-titulo {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--espacio-lg);
  }

  .titulo-y-insignia {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.6rem;
  }

  .insignia-modulo {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: var(--radius-pill, 9999px);
    background: var(--accent-surface);
    color: var(--accent-main);
    font-size: var(--texto-xs);
    font-weight: 600;
    border: 1px solid var(--accent-main);
  }

  h1 {
    margin: 0;
    font-size: var(--texto-xl);
    font-weight: 700;
    color: var(--ink-primary);
    line-height: 1.2;
  }

  /* `max-inline-size: none`: `estilos/tipografia.css` trae `:where(p, li) {
     max-inline-size: var(--ancho-lectura) }` global, con especificidad
     cero a propósito para que cualquier regla de componente la pise —sin
     declarar esta propiedad aquí, esa regla global sigue aplicando aunque
     este archivo no diga nada al respecto—. */
  .nota {
    margin: 0;
    max-inline-size: none;
    font-size: var(--texto-sm);
    color: var(--ink-tertiary);
    line-height: 1.5;
  }

  .nota.grande {
    font-size: var(--texto-base);
    color: var(--ink-secondary);
  }
</style>
