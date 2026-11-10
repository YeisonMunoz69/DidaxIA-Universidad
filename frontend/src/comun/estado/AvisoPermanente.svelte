<!--
Las inferencias son probabilísticas.

`RP-18` lo exige persistente y NO DESCARTABLE. Por eso este componente no lleva
botón de cerrar, y eso es intencionado: si se pudiera descartar, dejaría de
cumplir su función el segundo día de uso.

`RP-20` es inusualmente específico sobre la REDACCION, y su criterio de
aceptación lo dice con estas palabras:

    el aviso emplea formulaciones del tipo «indicios» y NUNCA del tipo
    «tienes ansiedad matemática».

De ahí que el texto por defecto hable de indicios y de apoyo, y nunca nombre un
estado del estudiante. Si alguien lo reescribe, esa es la línea que no se cruza.

El texto vive AQUI y no viaja en cada turno, para que ninguna respuesta pueda
alterarlo.



-->
<script>
  let {
    texto = 'Este es un sistema automatizado. Lo que observa son indicios ' +
            'a partir de cómo escribes, no un diagnóstico, y puede ' +
            'equivocarse. Sirve para orientar el apoyo, no para evaluarte.'
  } = $props();
</script>

<aside class="aviso" role="note">
  <span class="signo" aria-hidden="true">i</span>
  <p>{texto}</p>
</aside>

<style>
  .aviso {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 8px 14px;
    background: var(--semantic-info-bg);
    border: 1px solid var(--semantic-info);
    border-radius: var(--radius-sm);
    margin-block-end: 1rem;
    max-inline-size: 100%;
  }

  .signo {
    flex: 0 0 1rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    block-size: 1rem;
    border-radius: 50%;
    background: var(--semantic-info);
    color: var(--surface-paper);
    font-size: 11px;
    font-weight: 700;
  }

  p {
    margin: 0;
    font-size: 12px;
    line-height: 1.4;
    color: var(--ink-secondary);
    max-inline-size: 100%;
  }
</style>
