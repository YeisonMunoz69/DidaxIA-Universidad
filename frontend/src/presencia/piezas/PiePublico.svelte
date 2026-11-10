<!--
El pie de la superficie pública.

Autores, relación con la Institución, los tres documentos y el enlace al
tutor. Es lo último que se lee en cualquiera de las cuatro páginas, así que
es donde tiene que estar lo que no debe depender de haber leído la portada.

⚠️ **NI ESCUDO NI LOGOTIPO INSTITUCIONAL** (`ESTADO-ACTUAL.md` §10.1). La
relación con la Institución se explica en texto y **no se afirma ningún aval**:
la solicitud está en trámite y §10.9 la lista como pendiente humano.

Autores, institución y los caminos de los documentos salen de
`contenido/proyecto.js` y de `nucleo/configuracion/origenes.js`. Este archivo
no escribe ninguno de esos datos.



-->
<script>
  import EnlacesPublicos from "../../comun/base/EnlacesPublicos.svelte";
  import { ENLACE_AL_TUTOR } from "../../nucleo/configuracion/origenes.js";
  import { AUTORES_CON_LINKEDIN, MARCA } from "../contenido/proyecto.js";
  import PerfilesPublicos from './PerfilesPublicos.svelte';
</script>

<footer class="pie">
  <div class="columnas">
    <div class="columna">
      <p class="rotulo">Quién lo hace</p>
      <ul class="autores">
        {#each AUTORES_CON_LINKEDIN as autor (autor.nombre)}
          <li>
            <span class="nombre-autor">{autor.nombre}{autor.cargo ? ` · ${autor.cargo}` : ''}</span>
            <PerfilesPublicos perfil={autor} />
          </li>
        {/each}
      </ul>
    </div>

    <div class="columna">
      <p class="rotulo">Documentos</p>
      <EnlacesPublicos rotulo="Documentos públicos" variante="apilada" />
    </div>

    <div class="columna">
      <p class="rotulo">El tutor</p>
      <p class="nota">
        La aplicación vive en una dirección propia y pide cuenta institucional.
      </p>
      <a class="tutor entrada-tutor" href={ENLACE_AL_TUTOR}>Entrar al tutor</a>
    </div>
  </div>

  <p class="cierre">
    <span class="marca-cierre">{MARCA}</span> · Trabajo de grado en curso. Sistema
    de apoyo al estudio; no sustituye al docente.
  </p>
</footer>

<style>
  .pie {
    display: flex;
    flex-direction: column;
    gap: var(--espacio-lg);
    padding: var(--espacio-xl) var(--espacio-lg);
    background: var(--surface-panel);
    border-block-start: 1px solid var(--trazo-suave);
  }

  .columnas {
    display: flex;
    flex-wrap: wrap;
    gap: var(--espacio-xl);
    inline-size: 100%;
    max-inline-size: min(78rem, 100%);
    margin-inline: auto;
  }

  .columna {
    flex: 1 1 15rem;
    min-inline-size: 0;
    display: flex;
    flex-direction: column;
    gap: var(--espacio-sm);
  }

  .rotulo {
    margin: 0;
    max-inline-size: none;
    font-size: var(--texto-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-tertiary);
  }

  .autores {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .autores li {
    max-inline-size: none;
  }

  .nombre-autor {
    color: var(--ink-primary);
    font-size: var(--texto-sm);
    font-weight: 500;
  }

  .nota {
    margin: 0;
    max-inline-size: none;
    font-size: var(--texto-xs);
    line-height: 1.5;
    color: var(--ink-tertiary);
  }

  /* Enlace de navegación, no de frase: declara su propio objetivo mínimo. */
  .tutor {
    display: inline-flex;
    align-items: center;
    inline-size: fit-content;
    min-block-size: 24px;
    font-size: var(--texto-sm);
    font-weight: 600;
  }

  .cierre {
    margin: 0;
    inline-size: 100%;
    max-inline-size: min(78rem, 100%);
    margin-inline: auto;
    padding-block-start: var(--espacio-md);
    border-block-start: 1px solid var(--ink-ghost);
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  .marca-cierre {
    font-family: var(--fuente-manuscrita);
    font-size: 1.25em;
    font-weight: 700;
    color: var(--ink-primary);
  }
</style>
