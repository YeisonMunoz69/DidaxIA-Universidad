
<script>
  import { ayudaContextual } from '../../comun/base/ayudaContextual.js';
  import Icono from '../../comun/base/Icono.svelte';

  let {
    mios,
    perfil = null,
    foto = null,
    modoProfesional = false,
    alGuardarFoto = async () => {},
    alRetirarFoto = async () => {}
  } = $props();

  let selectorFoto;
  let guardandoFoto = $state(false);
  let errorFoto = $state('');

  const nombreVisible = $derived(mios?.nombre || (modoProfesional ? 'Cuenta de DidaxIa' : 'Estudiante de DidaxIa'));
  const inicial = $derived(nombreVisible.trim().charAt(0).toUpperCase() || 'D');

  async function seleccionarFoto(evento) {
    const archivo = evento.currentTarget.files?.[0];
    evento.currentTarget.value = '';
    if (!archivo) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(archivo.type)) {
      errorFoto = 'Selecciona una imagen JPEG, PNG o WebP.';
      return;
    }
    if (archivo.size > 4 * 1024 * 1024) {
      errorFoto = 'La imagen no puede superar 4 MB.';
      return;
    }
    guardandoFoto = true;
    errorFoto = '';
    try {
      await alGuardarFoto(archivo);
    } catch (error) {
      errorFoto = error?.detalle || 'No se pudo guardar la foto. Inténtalo de nuevo.';
    } finally {
      guardandoFoto = false;
    }
  }

  async function retirarFoto() {
    guardandoFoto = true;
    errorFoto = '';
    try {
      await alRetirarFoto();
    } catch (error) {
      errorFoto = error?.detalle || 'No se pudo retirar la foto. Inténtalo de nuevo.';
    } finally {
      guardandoFoto = false;
    }
  }
</script>

<section class="perfil-social" aria-labelledby="titulo-perfil-personal">
  <div class="portada" aria-hidden="true">
    <span class="trazo trazo-uno"></span>
    <span class="trazo trazo-dos"></span>
    <span class="trazo trazo-tres"></span>
  </div>

  <div class="identidad">
    <div class="avatar-contenedor">
      <div class="avatar" class:con-foto={foto} aria-hidden={!foto}>
        {#if foto}
          <img src={foto} alt={`Foto de perfil de ${nombreVisible}`} />
        {:else}
          <span aria-hidden="true">{inicial}</span>
        {/if}
      </div>
      <button use:ayudaContextual
        type="button"
        class="cambiar-foto"
        title="Cambiar foto de perfil"
        disabled={guardandoFoto}
        onclick={() => selectorFoto?.click()}>
        <Icono nombre="editar" medida={12} />
        <span class="solo-lectura-asistida">Cambiar foto de perfil</span>
      </button>
      <input
        bind:this={selectorFoto}
        class="selector-foto solo-lectura-asistida"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onchange={seleccionarFoto} />
    </div>
    <div class="quien">
      <h2 id="titulo-perfil-personal">{nombreVisible}</h2>
      <p>{mios?.correo || 'Correo institucional no disponible'}</p>
    </div>
    <span class="cuenta-institucional"><Icono nombre="check" medida={12} /> Cuenta institucional</span>
  </div>

  <div class="acciones-foto">
    <button type="button" onclick={() => selectorFoto?.click()} disabled={guardandoFoto}>
      {guardandoFoto ? 'Procesando foto…' : foto ? 'Cambiar foto' : 'Añadir foto'}
    </button>
    {#if foto}
      <button type="button" class="retirar-foto" onclick={retirarFoto} disabled={guardandoFoto}>Retirar foto</button>
    {/if}
    <span>JPEG, PNG o WebP · máximo 4 MB</span>
  </div>
  {#if errorFoto}<p class="error-foto" role="alert">{errorFoto}</p>{/if}

  <div class="datos-clave">
    {#if !modoProfesional}
      <article>
        <span class="etiqueta">Edad</span>
        <strong>{mios?.edad == null ? 'Sin declarar' : `${mios.edad} años`}</strong>
      </article>
    {/if}
    {#if !modoProfesional || mios?.rol === 'docente'}
      <article>
        <span class="etiqueta">Facultad</span>
        <strong>{perfil?.facultad || 'Pendiente de asignación'}</strong>
      </article>
    {/if}
    {#if !modoProfesional}
      <article>
        <span class="etiqueta">Programa</span>
        <strong>{perfil?.programa || 'Sin registrar'}</strong>
      </article>
      <article>
        <span class="etiqueta">Semestre</span>
        <strong>{perfil?.semestre == null ? 'Sin registrar' : perfil.semestre}</strong>
      </article>
    {/if}
    <article>
      <span class="etiqueta">Rol</span>
      <strong>{mios?.rol || 'Estudiante'}</strong>
    </article>
  </div>

  <div class="nota-perfil">
    <Icono nombre="candado" medida={14} />
    <p>{modoProfesional
      ? 'Tu nombre y correo provienen de Google. La fotografía la controlas aquí; la facultad docente la administra el equipo institucional.'
      : 'Estos son tus datos personales visibles. Los identificadores técnicos y registros del tutor están disponibles en tu copia de datos.'}</p>
  </div>
</section>

<style>
  h2 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--ink-primary);
  }

  .perfil-social { overflow: hidden; border: 1px solid var(--ink-ghost); border-radius: var(--radius-lg); background: var(--surface-panel); }
  .portada { position: relative; block-size: 112px; overflow: hidden; background: linear-gradient(135deg, var(--accent-surface), var(--surface-canvas)); }
  .trazo { position: absolute; border-radius: 50%; border: 2px solid color-mix(in srgb, var(--accent-main) 25%, transparent); }
  .trazo-uno { inline-size: 220px; block-size: 220px; inset: -120px auto auto -40px; }
  .trazo-dos { inline-size: 170px; block-size: 170px; inset: -70px 12% auto auto; }
  .trazo-tres { inline-size: 8px; block-size: 8px; inset: 30px 26% auto auto; background: var(--accent-main); border: 0; box-shadow: 40px 35px 0 var(--accent-main), -85px 45px 0 var(--accent-main); }
  .identidad { position: relative; display: flex; align-items: center; gap: 14px; padding: 0 22px 18px; }
  .avatar-contenedor { position: relative; margin-block-start: -36px; inline-size: 78px; block-size: 78px; flex: 0 0 78px; }
  .avatar { display: grid; place-items: center; inline-size: 78px; block-size: 78px; overflow: hidden; border: 5px solid var(--surface-panel); border-radius: 50%; background: var(--accent-main); color: var(--surface-paper); font-size: 1.7rem; font-weight: 800; box-shadow: var(--shadow-card); box-sizing: border-box; }
  .avatar img { inline-size: 100%; block-size: 100%; object-fit: cover; }
  .cambiar-foto { position: absolute; inset: auto -4px -4px auto; display: grid; place-items: center; inline-size: 28px; block-size: 28px; padding: 0; border: 2px solid var(--surface-panel); border-radius: 50%; background: var(--ink-primary); color: var(--surface-paper); cursor: pointer; }
  .selector-foto { inset: 0 auto auto 0; }
  .acciones-foto { display: flex; align-items: center; gap: 10px; margin: -8px 22px 16px 114px; flex-wrap: wrap; }
  .acciones-foto button { border: 0; padding: 0; background: transparent; color: var(--accent-main); font: inherit; font-size: var(--texto-xs); font-weight: 700; cursor: pointer; }
  .acciones-foto button:disabled { opacity: .55; cursor: wait; }
  .acciones-foto .retirar-foto { color: var(--ink-secondary); }
  .acciones-foto span { color: var(--ink-tertiary); font-size: var(--texto-xs); }
  .error-foto { margin: -10px 22px 15px 114px; color: var(--semantic-error); font-size: var(--texto-xs); }
  .quien { min-inline-size: 0; flex: 1; padding-block-start: 12px; }
  .quien h2 { font-size: 1.15rem; }
  .quien p { margin: 3px 0 0; overflow: hidden; text-overflow: ellipsis; color: var(--ink-secondary); font-size: var(--texto-sm); }
  .cuenta-institucional { display: inline-flex; align-items: center; gap: 5px; padding: 5px 9px; border-radius: var(--radius-pill); color: var(--accent-main); background: var(--accent-surface); font-size: var(--texto-xs); font-weight: 700; }
  .datos-clave { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: 10px; padding: 0 22px 20px; }
  .datos-clave article { position: relative; min-block-size: 82px; display: flex; flex-direction: column; gap: 5px; padding: 13px; border: 1px solid var(--ink-ghost); border-radius: var(--radius-md); background: var(--surface-paper); }
  .etiqueta { color: var(--ink-tertiary); font-size: var(--texto-xs); text-transform: uppercase; letter-spacing: .04em; }
  .datos-clave strong { color: var(--ink-primary); font-size: var(--texto-sm); overflow-wrap: anywhere; }
  .nota-perfil { display: flex; gap: 8px; align-items: flex-start; margin: 0 22px 22px; padding: 10px 12px; border-radius: var(--radius-sm); background: var(--surface-canvas); color: var(--ink-secondary); }
  .nota-perfil p { margin: 0; font-size: var(--texto-xs); line-height: 1.45; }
  @media (max-width: 48rem) {
    .identidad { align-items: flex-start; flex-wrap: wrap; padding-inline: 16px; }
    .cuenta-institucional { margin-inline-start: 92px; margin-block-start: -10px; }
    .datos-clave { grid-template-columns: repeat(2, minmax(0, 1fr)); padding-inline: 16px; }
    .nota-perfil { margin-inline: 16px; }
    .acciones-foto, .error-foto { margin-inline: 16px; margin-block-start: 0; }
  }
</style>
