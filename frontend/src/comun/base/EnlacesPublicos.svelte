<!--
Los enlaces a los tres documentos públicos. **Los usan las dos superficies.**

Vive en `comun/base/` y no bajo `presencia/` porque no es de la portada: lo
pinta el pie de la superficie pública Y el recorrido de consentimiento de la
aplicación, que tiene que ofrecer privacidad, condiciones e investigación
antes de que nadie decida nada. Puesto en `presencia/`, el árbol privado
dependería de la carpeta pública para citar tres enlaces; escrito dos veces,
la segunda copia se habría quedado con dos de los tres el día que se añada
un documento.

`absolutos` ES LA ÚNICA DIFERENCIA REAL ENTRE LOS DOS USOS
------------------------------------------------------------
Dentro de la superficie pública el enlace es relativo —`/privacidad`— porque
ya se está en `didaxia.pro`. Desde la aplicación tiene que llevar el origen
delante: un `/privacidad` relativo apuntaría a `app.didaxia.pro/privacidad`,
que no existe. El origen sale de `nucleo/configuracion/origenes.js`, que es
la única copia de las dos direcciones.

`<nav>` CON NOMBRE, Y NO UN ENCABEZADO
----------------------------------------
Se nombra con `aria-label` en vez de con un `<h2>` porque los dos sitios
donde se monta ya tienen su propia jerarquía de encabezados: en el pie
público añadiría un nivel suelto, y en el recorrido de consentimiento
—donde `T-09`-`T-11` fijan un `<h1>` por vista y `<h2>` por paso— habría
metido un `<h2>` que no es un paso.



-->
<script>
  import { DOCUMENTOS_PUBLICOS, enlacePublico } from '../../nucleo/configuracion/origenes.js';

  let {
    /** Con el origen público delante. `true` desde la aplicación. */
    absolutos = false,
    /** Nombre accesible del `<nav>`. Cambia según dónde se monte. */
    rotulo = 'Documentos públicos del proyecto',
    /** `en-linea` para una fila que envuelve · `apilada` para una columna. */
    variante = 'en-linea',
    /** Muestra la frase de cada documento. El pie público la quiere; el
        recorrido de consentimiento no, que ya va cargado de texto. */
    conResumen = false
  } = $props();

  const enlaces = $derived(
    DOCUMENTOS_PUBLICOS.map((p) => ({
      ...p,
      href: absolutos ? enlacePublico(p.camino) : p.camino
    }))
  );
</script>

<nav class="enlaces {variante}" aria-label={rotulo}>
  <ul>
    {#each enlaces as enlace (enlace.camino)}
      <li>
        <a href={enlace.href}>{enlace.titulo}</a>
        {#if conResumen}
          <span class="resumen">{enlace.resumen}</span>
        {/if}
      </li>
    {/each}
  </ul>
</nav>

<style>
  .enlaces ul {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    gap: var(--espacio-md) var(--espacio-lg);
  }

  .en-linea ul { flex-wrap: wrap; align-items: baseline; }

  .apilada ul { flex-direction: column; }

  li {
    max-inline-size: none;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  /* `2.5.8` deja fuera al enlace que va dentro de una frase, y estos no lo
     están: son navegación. `base.css` no les pone mínimo a propósito, así
     que lo declara quien los estiliza — misma regla que los enlaces de
     `CabeceraGlobal.svelte`. */
  a {
    display: inline-flex;
    align-items: center;
    min-block-size: 24px;
    font-size: var(--texto-sm);
    font-weight: 500;
  }

  .resumen {
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
    line-height: 1.4;
  }
</style>
