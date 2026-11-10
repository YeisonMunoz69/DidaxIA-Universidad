<!--
Envuelve <table>.

DD-05 decidió HTML nativo primero. Con encabezados y ámbito declarados.

`scope` en cada <th> es lo que permite a un lector de pantalla anunciar «fila
3, Estado: pendiente» en vez de leer celdas sueltas sin contexto. Es un
atributo y resuelve el problema entero.

El <caption> no es decorativo: es el nombre accesible de la tabla. Puede
ocultarse visualmente, pero no debe faltar.

El desbordamiento va en un contenedor con tabindex, para que quien navega por
teclado pueda desplazar una tabla ancha. Un contenedor con scroll que no
recibe foco es inalcanzable sin ratón.



-->
<script>
  let {
    titulo,
    tituloVisible = false,
    columnas = [],      // [{ clave, etiqueta, numerica }]
    filas = [],
    ...resto
  } = $props();
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex
     El aviso es correcto como regla general y falso aquí. Una región que se
     desplaza horizontalmente TIENE que poder recibir foco, o quien navega por
     teclado no puede desplazarla: WCAG 2.1.1 lo exige. La pauta de la WAI para
     regiones desplazables es exactamente esta —role, nombre accesible y
     tabindex 0— y por eso se conserva. -->
<div class="marco" tabindex="0" role="region" aria-label={titulo}>
  <table {...resto}>
    <caption class={tituloVisible ? '' : 'solo-lectura-asistida'}>{titulo}</caption>
    <thead>
      <tr>
        {#each columnas as c}
          <th scope="col" class={c.numerica ? 'num' : ''}>{c.etiqueta}</th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each filas as fila}
        <tr>
          {#each columnas as c, i}
            {#if i === 0}
              <th scope="row">{fila[c.clave]}</th>
            {:else}
              <td class={c.numerica ? 'num' : ''}>{fila[c.clave]}</td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .marco { overflow-x: auto; }

  table { border-collapse: collapse; inline-size: 100%; }

  caption {
    text-align: start;
    font-weight: 500;
    margin-block-end: 0.5em;
  }

  /*
    POCAS LÍNEAS Y MUCHO AIRE. El lenguaje pide separación clara entre filas y
    «nunca demasiadas líneas»: se conserva UNA línea por fila y ninguna
    vertical, y la separación la da el relleno, que subió de 0.5em a 0.7em.

    La línea de fila sí es decoración —separa, no delimita un control— y por
    eso se queda en `--ink-ghost`. La de la cabecera pasa a `--trazo-suave`
    porque es la que estructura la tabla, como el subrayado de un encabezado
    escrito a mano.
  */
  th, td {
    padding: 0.7em 0.85em;
    text-align: start;
    border-block-end: 1px solid var(--ink-ghost);
  }

  thead th {
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
    border-block-end: 2px solid var(--trazo-suave);
  }

  tbody tr:last-child :where(th, td) { border-block-end: none; }

  .num { text-align: end; font-variant-numeric: tabular-nums; }
</style>
