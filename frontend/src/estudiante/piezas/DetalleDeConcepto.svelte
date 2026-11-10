<!-- Jerarquía editorial del contenido docente, sin añadir afirmaciones nuevas. -->
<script>
  import EnlaceAConcepto from '../../comun/concepto/EnlaceAConcepto.svelte';
  import TextoDeConcepto from '../../comun/concepto/TextoDeConcepto.svelte';
  import Notacion from '../../comun/turno/Notacion.svelte';
  import { formulasDelConcepto, temaDeConcepto } from '../../nucleo/lectura/conceptos.js';
  let { ficha, alAbrir = null, parte = 'completa' } = $props();
  const secciones = $derived(ficha?.secciones ?? []), previos = $derived(ficha?.previos ?? []);
  const formulas = $derived(formulasDelConcepto(secciones));
  const revisada = $derived(!/borrador|pendiente/i.test(ficha?.estado ?? ''));
  const central = titulo => /qué es|que es|idea central|definici[oó]n/i.test(titulo);
  const intuicion = titulo => /explicaci[oó]n|intuici[oó]n|simulaci[oó]n/i.test(titulo);
</script>
<article class="detalle-concepto">
  {#if parte!=='contenido'}
    <header class="cabecera-detalle">
      <div class="sobre-titulo"><span class="rotulo-libro">Libro de conceptos</span><span>{temaDeConcepto(ficha??{})}</span></div>
      <h2>{ficha?.nombre??'Concepto'}</h2>
      <div class="datos-editoriales"><span class="clave-concepto">Identificador: <code>{ficha?.id}</code></span>{#if ficha?.estado}<span class="estado" class:sin-revisar={!revisada}>{revisada?'✓':'◇'} {ficha.estado}</span>{/if}</div>
    </header>
  {/if}
  <div class="cuerpo-detalle">
    {#if parte!=='portada'}
      {#each secciones as s,i (s.titulo)}
        <section class="seccion-bloque" class:definicion-central={central(s.titulo)} class:intuicion={intuicion(s.titulo)}>
          <h3 class="titulo-seccion"><span aria-hidden="true">{String(i+1).padStart(2,'0')}</span>{s.titulo}</h3>
          {#if intuicion(s.titulo)}<div class="mapa-intuicion" aria-hidden="true"><i></i><span>Idea</span><b>→</b><span>Representación</span><b>→</b><span>Aplicación</span></div>{/if}
          <div class="contenido-seccion"><TextoDeConcepto texto={s.texto} /></div>
        </section>
      {/each}
      {#if formulas.length}<section class="formulas-concepto"><h3>Notación del concepto</h3><div>{#each formulas as formula}<div class="tarjeta-formula"><Notacion expresion={formula} bloque /></div>{/each}</div></section>{/if}
    {/if}
    {#if parte!=='contenido'&&previos.length}
      <section class="franja-prerrequisitos"><h3>Conecta con lo que ya sabes</h3><div class="lista-prerrequisitos">
        {#each previos as p (p.id)}<article class="item-prerrequisito"><EnlaceAConcepto concepto={{id:p.id,nombre:p.nombre??'Concepto relacionado'}} {alAbrir} />{#if p.motivo}<div class="motivo-prerrequisito"><TextoDeConcepto texto={p.motivo} /></div>{:else}<p>Concepto previo de esta ficha.</p>{/if}</article>{/each}
      </div></section>
    {/if}
    {#if parte==='portada'&&!previos.length}<p>Este concepto puede leerse directamente.</p>{/if}
  </div>
</article>
<style>
  .detalle-concepto {
    display:flex;
    flex-direction:column;
    inline-size:100%;
    block-size:auto;
    min-block-size:100%;
    margin:0;
    background:var(--book-paper);
    color:var(--ink-primary);
    box-sizing:border-box;
  }
  .cabecera-detalle {
    padding:clamp(1.4rem,3vw,2.6rem) clamp(1.2rem,3vw,2.6rem) 1rem;
  }
  .sobre-titulo {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:1rem;
    color:var(--accent-main);
    font:700 .65rem/1.4 var(--fuente-mono);
    letter-spacing:.08em;
    text-transform:uppercase;
  }
  h2 {
    margin:.85rem 0 .8rem;
    max-width:28ch;
    font:600 clamp(1.7rem,3.2vw,2.6rem)/1.12 Georgia,serif;
    letter-spacing:-.035em;
  }
  .datos-editoriales {
    display:flex;
    flex-wrap:wrap;
    gap:.6rem 1rem;
    align-items:center;
    color:var(--ink-tertiary);
    font-size:.7rem;
  }
  code {
    font-family:var(--fuente-mono);
    color:var(--accent-main);
  }
  .estado {
    font-size:.7rem;
  }
  .sin-revisar {
    color:var(--ink-secondary);
  }
  .cuerpo-detalle {
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:1.3rem;
    padding:1rem clamp(1.2rem,3vw,2.6rem) 2.4rem;
  }
  .seccion-bloque {
    min-width:0;
    border-top:1px solid var(--trazo-suave);
    padding:1rem 0;
  }
  .definicion-central,.intuicion,.franja-prerrequisitos,.formulas-concepto {
    grid-column:1/-1;
  }
  .definicion-central {
    padding:1.25rem 1.4rem;
    border:1px solid color-mix(in srgb,var(--accent-main) 25%,var(--trazo-suave));
    border-left:3px solid var(--accent-main);
    border-radius:.75rem;
    background:color-mix(in srgb,var(--accent-surface) 40%,var(--book-paper));
  }
  h3 {
    margin:0 0 .75rem;
    font:600 1.1rem/1.3 Georgia,serif;
    color:var(--ink-primary);
  }
  .titulo-seccion {
    display:flex;
    gap:.65rem;
    align-items:baseline;
  }
  .titulo-seccion span {
    font:600 .65rem/1 var(--fuente-mono);
    color:var(--accent-main);
  }
  .contenido-seccion {
    font:400 1rem/1.75 Georgia,serif;
    color:var(--ink-secondary);
  }
  .contenido-seccion :global(.texto) {
    font:inherit;
    line-height:inherit;
  }
  .mapa-intuicion {
    display:flex;
    align-items:center;
    gap:.7rem;
    padding:.65rem 0;
    margin-bottom:.45rem;
    font:.65rem/1.5 var(--fuente-mono);
    color:var(--ink-tertiary);
  }
  .mapa-intuicion i {
    width:8px;
    height:8px;
    border-radius:50%;
    background:var(--accent-main);
  }
  .mapa-intuicion b {
    color:var(--accent-main);
  }
  .formulas-concepto>div,.lista-prerrequisitos {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(min(100%,14rem),1fr));
    gap:.75rem;
  }
  .tarjeta-formula {
    display:grid;
    align-items:center;
    min-width:0;
    min-height:5rem;
    padding:1rem;
    background:var(--surface-paper);
    border:1px solid var(--trazo-suave);
    border-radius:.75rem;
    overflow-x:auto;
  }
  .tarjeta-formula :global(.notacion.bloque) {
    margin:0;
    padding:.25rem;
    background:transparent;
    border:0;
    border-radius:0;
    box-shadow:none;
    max-inline-size:100%;
  }
  .item-prerrequisito :global(.enlace) {
    min-height:44px;
    padding:0;
    background:transparent;
    border:0;
    box-shadow:none;
    color:var(--accent-main);
    font:600 1rem/1.4 Georgia,serif;
  }
  .item-prerrequisito :global(.enlace:hover) { box-shadow:none; }
  .item-prerrequisito :global(.enlace:focus-visible) {
    outline:2px solid var(--accent-main);
    outline-offset:3px;
  }
  .item-prerrequisito {
    min-width:0;
    padding:1rem;
    background:var(--surface-paper);
    border:1px solid var(--trazo-suave);
    border-radius:.75rem;
  }
  .item-prerrequisito :global(.enlace) {
    min-height:44px;
    width:100%;
    justify-content:flex-start;
    text-align:left;
    white-space:normal;
  }
  .motivo-prerrequisito,p {
    font-size:.8rem;
    line-height:1.55;
    color:var(--ink-secondary);
  }
  @media(max-width:70rem) {
    .cuerpo-detalle {
      grid-template-columns:1fr;
    }
  }
  @media(max-width:47.999rem) {
    .cabecera-detalle {
      padding:1.3rem 1rem .5rem;
    }
    h2 {
      font-size:1.8rem;
    }
    .cuerpo-detalle {
      padding:.7rem 1rem 2rem;
      gap:1rem;
    }
    .definicion-central {
      padding:1rem;
    }
    .sobre-titulo {
      font-size:.6rem;
    }
    .mapa-intuicion {
      gap:.4rem;
      font-size:.58rem;
    }
  }
</style>
