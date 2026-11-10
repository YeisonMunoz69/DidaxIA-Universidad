<script>
  import { CANALES_PUBLICOS as canales } from '../../nucleo/configuracion/contacto.js';
  const gmail = correo => `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(correo)}&su=${encodeURIComponent('Consulta sobre DidaxIa')}`;
</script>

<section class="canal" aria-labelledby="canal-titulo">
  <div class="introduccion">
    <h2 id="canal-titulo">Cómo preguntar o ejercer un derecho</h2>
    <p>Escríbenos para consultar sobre el tratamiento de tus datos o solicitar el ejercicio de tus derechos. También puedes consultar tus datos y solicitar su eliminación desde la aplicación.</p>
  </div>
  <div class="canales">
    {#each canales as canal (canal.correo)}
      <div class="contacto">
        <div><strong>{canal.nombre}</strong><a class="direccion" href={`mailto:${canal.correo}`}>{canal.correo}</a></div>
        <a class="gmail" href={gmail(canal.correo)} target="_blank" rel="noopener noreferrer" aria-label={`Escribir a ${canal.correo} en Gmail; abre otra pestaña`}>
          <img src="/imagenes/iconos/gmail.svg" alt="" /> Abrir Gmail <span aria-hidden="true">↗</span>
        </a>
      </div>
    {/each}
  </div>
</section>

<style>
  .canal { display: grid; gap: var(--espacio-lg); padding: clamp(var(--espacio-lg), 3vw, var(--espacio-2xl)); background: var(--surface-panel); border: 1px solid var(--trazo-suave); border-radius: var(--radius-lg); }
  .introduccion { max-inline-size: 65rem; }
  h2 { margin: 0 0 var(--espacio-sm); font-size: var(--texto-lg); color: var(--ink-primary); }
  p { max-inline-size: none; margin: 0; color: var(--ink-secondary); line-height: var(--interlinea-comoda); }
  .canales { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--espacio-md); }
  .contacto { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: var(--espacio-sm); padding: var(--espacio-md); background: var(--surface-paper); border-radius: var(--radius-md); }
  .contacto div { display: grid; gap: var(--espacio-xs); min-inline-size: 0; }
  strong { color: var(--ink-primary); font-size: var(--texto-sm); }
  .direccion { color: var(--ink-secondary); font-size: var(--texto-sm); overflow-wrap: anywhere; }
  .gmail { display: inline-flex; align-items: center; gap: .45rem; min-block-size: 44px; color: var(--accent-main); font-size: var(--texto-sm); font-weight: 650; text-decoration: none; }
  .gmail img { width: 20px; height: 20px; }
  a:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 3px; }
  @media (max-width: 48rem) { .canales { grid-template-columns: minmax(0, 1fr); } }
</style>
