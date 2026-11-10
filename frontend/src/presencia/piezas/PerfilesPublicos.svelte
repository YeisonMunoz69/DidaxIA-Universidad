<script>
  let { perfil } = $props();
  const plataformas = [
    { clave: 'linkedin', nombre: 'LinkedIn', icono: 'linkedin.svg' },
    { clave: 'github', nombre: 'GitHub', icono: 'github_light.svg' },
    { clave: 'cvlac', nombre: 'CvLAC', icono: '' },
    { clave: 'orcid', nombre: 'ORCID', icono: 'orcid.svg' },
    { clave: 'correo', nombre: 'Correo', icono: 'gmail.svg' }
  ];
</script>

<div class="perfiles" role="group" aria-label={`Perfiles de ${perfil.nombre}`}>
  {#each plataformas as plataforma (plataforma.clave)}
    {#if perfil[plataforma.clave]}
      <a href={plataforma.clave === 'correo' ? `mailto:${perfil.correo}` : perfil[plataforma.clave]}
         target={plataforma.clave === 'correo' ? undefined : '_blank'}
         rel={plataforma.clave === 'correo' ? undefined : 'noopener noreferrer'}
         aria-label={`${plataforma.nombre} de ${perfil.nombre}`} title={`${plataforma.nombre} de ${perfil.nombre}`}>
        {#if plataforma.icono}<img class:github={plataforma.clave === 'github'} src={`/imagenes/iconos/${plataforma.icono}`} alt="" />{:else}<span class="cvlac" aria-hidden="true">Cv</span>{/if}
      </a>
    {:else}
      <span class="pendiente" role="img" aria-label={`${plataforma.nombre} de ${perfil.nombre}: enlace pendiente`} title={`${plataforma.nombre}: enlace pendiente`}>
        {#if plataforma.icono}<img class:github={plataforma.clave === 'github'} src={`/imagenes/iconos/${plataforma.icono}`} alt="" />{:else}<span class="cvlac" aria-hidden="true">Cv</span>{/if}
      </span>
    {/if}
  {/each}
</div>

<style>
  .perfiles { display: flex; flex-wrap: wrap; align-items: center; gap: var(--espacio-xs); }
  a, .pendiente { display: inline-grid; place-items: center; inline-size: 44px; block-size: 44px; border-radius: var(--radius-sm); }
  a:hover { background: var(--accent-surface); }
  a:focus-visible { outline: 2px solid var(--accent-main); outline-offset: 2px; }
  .pendiente { opacity: .34; }
  img { inline-size: 19px; block-size: 19px; object-fit: contain; }
  :global(.dark-theme) img.github { filter: invert(1); }
  .cvlac { font-size: var(--texto-xs); font-weight: 800; color: var(--ink-primary); }
</style>
