
<script>
  import { menuDesplegable } from '../../../comun/base/menuDesplegable.js';
  import Campo from '../../../comun/base/Campo.svelte';
  import Boton from '../../../comun/base/Boton.svelte';
  import Icono from '../../../comun/base/Icono.svelte';
  import Dialogo from '../../../comun/base/Dialogo.svelte';
  import { navegar } from '../../../enrutado/navegar.js';
  import {
    FACULTADES_ADMITIDAS,
    facultadAdmitida,
    programaAdmitido,
    programasDe
  } from '../../../nucleo/configuracion/programas.js';
  import { untrack } from 'svelte';

  let {
    perfil,
    identidad = null,
    alGuardar,
    errorDelServidor = ''
  } = $props();

  let edad = $state(untrack(() => (perfil?.edad != null ? String(perfil.edad) : '')));
  let facultad = $state(untrack(() => facultadAdmitida(perfil?.facultad) ? perfil.facultad : ''));
  let programa = $state(untrack(() => programaAdmitido(perfil?.programa, perfil?.facultad) ? perfil.programa : ''));
  let semestre = $state(untrack(() => (perfil?.semestre != null ? String(perfil.semestre) : '')));
  let motivo = $state('');
  let editando = $state(false);

  let enviando = $state(false);
  let confirmando = $state(false);
  let intentado = $state(false);
  let continuarAClase = $state(false);

  const claseVinculada = $derived(Boolean(perfil?.clase_vinculada));

  const datosPersonalesGuardados = $derived(
    typeof perfil?.edad === 'number' &&
      Boolean(String(perfil?.facultad ?? '').trim()) &&
      Boolean(String(perfil?.programa ?? '').trim()) &&
      typeof perfil?.semestre === 'number'
  );

  const valores = $derived({
    edad: String(edad ?? '').trim(),
    facultad: String(facultad ?? '').trim(),
    programa: String(programa ?? '').trim(),
    semestre: String(semestre ?? '').trim()
  });

  const errores = $derived({
    edad: !valores.edad
      ? 'Escribe tu edad exacta.'
      : !/^\d{1,3}$/.test(valores.edad) || Number(valores.edad) < 1 || Number(valores.edad) > 120
        ? 'Escribe una edad entre 1 y 120.'
        : '',
    facultad: !facultadAdmitida(valores.facultad) ? 'Selecciona tu facultad.' : '',
    programa: !programaAdmitido(valores.programa, valores.facultad) ? 'Selecciona un programa de tu facultad.' : '',
    semestre: !valores.semestre
      ? 'Escribe el semestre que cursas.'
      : !/^\d{1,2}$/.test(valores.semestre) || Number(valores.semestre) < 1
        ? 'Escribe el semestre como un número.'
        : '',
    motivo: editando && (motivo.trim().length < 8 || motivo.trim().length > 500)
      ? 'Explica el motivo en 8 a 500 caracteres.'
      : ''
  });

  const completo = $derived(
    !errores.edad && !errores.facultad && !errores.programa &&
      !errores.semestre && !errores.motivo
  );

  $effect(() => {
    const opciones = programasDe(facultad);
    if (programa && !opciones.includes(programa)) programa = '';
  });

  const declaraMinoria = $derived(
    Boolean(valores.edad) && !errores.edad && Number(valores.edad) < 18
  );

  function pedirConfirmacion() {
    continuarAClase = false;
    intentado = true;
    if (!completo) return;
    confirmando = true;
  }

  function irAClase() {
    if (enviando) return;
    if (datosPersonalesGuardados && !editando) {
      navegar('/unirse');
      return;
    }
    intentado = true;
    if (!completo) return;
    continuarAClase = true;
    confirmando = true;
  }

  async function confirmar() {
    if (enviando) return;
    enviando = true;
    try {
      await alGuardar({
        ...valores,
        ...(editando ? { motivo: motivo.trim() } : {})
      });
      confirmando = false;
      editando = false;
      motivo = '';
      if (continuarAClase) navegar('/unirse');
    } catch {
      confirmando = false;
    } finally {
      enviando = false;
    }
  }

  function cancelarEdicion() {
    edad = perfil?.edad != null ? String(perfil.edad) : '';
    facultad = facultadAdmitida(perfil?.facultad) ? perfil.facultad : '';
    programa = programaAdmitido(perfil?.programa, perfil?.facultad) ? perfil.programa : '';
    semestre = perfil?.semestre != null ? String(perfil.semestre) : '';
    motivo = '';
    intentado = false;
    editando = false;
  }
</script>

<div class="perfil">
  {#if identidad?.correo || identidad?.nombre}
    <div class="identidad">
      <div class="identidad-rotulo">
        <Icono nombre="google" medida={13} />
        <span>Tu cuenta institucional</span>
      </div>
      <p class="identidad-valor">
        {#if identidad.nombre}<strong>{identidad.nombre}</strong>{/if}
        {#if identidad.correo}<span class="correo">{identidad.correo}</span>{/if}
      </p>
      <p class="identidad-nota">
        Vienen de Google y no se editan aquí.
      </p>
    </div>
  {/if}

  <p class="explica">
    Confirma estos datos antes de empezar. Se guardan en el sistema, no en tu
    navegador, y puedes consultarlos siempre desde «Mis datos».
  </p>

  {#if datosPersonalesGuardados}
    <div class="aviso-guardado" role="status">
      <Icono nombre="check" medida={16} />
      <div>
        <strong>Tus datos personales ya quedaron guardados.</strong>
        {#if !claseVinculada}
          <span>Ahora falta el código de una clase creada por tu docente.</span>
        {:else}
          <span>También estás vinculado a una clase.</span>
        {/if}
      </div>
      {#if !claseVinculada && !editando}
        <Boton variante="secundario" onclick={() => (editando = true)}>
          Editar mis datos
        </Boton>
      {/if}
    </div>
  {/if}

  {#if !datosPersonalesGuardados || editando}
    <div class="campos">
      <Campo
        etiqueta="Tu edad exacta"
        tipo="number"
        inputmode="numeric"
        min="1"
        max="120"
        requerido
        bind:valor={edad}
        ayuda="Determina qué autorizaciones necesitas."
        error={intentado ? errores.edad : ''}
      />

      <div class="campo-programa">
        <label for="facultad-onboarding">
          Facultad <span aria-hidden="true">*</span>
          <span class="solo-lectura-asistida">obligatoria</span>
        </label>
        <select use:menuDesplegable={facultad} id="facultad-onboarding" bind:value={facultad} required
                aria-invalid={intentado && errores.facultad ? 'true' : undefined}>
          <option value="" disabled>Selecciona tu facultad</option>
          {#each FACULTADES_ADMITIDAS as opcion}
            <option value={opcion}>{opcion}</option>
          {/each}
        </select>
        <p class="ayuda-programa">La unidad académica a la que pertenece tu programa.</p>
        {#if intentado && errores.facultad}<p class="error-programa">{errores.facultad}</p>{/if}
      </div>

      <div class="campo-programa">
        <label for="programa-onboarding">
          Programa <span aria-hidden="true">*</span>
          <span class="solo-lectura-asistida">obligatorio</span>
        </label>
        <select use:menuDesplegable={programa}
          id="programa-onboarding"
          bind:value={programa}
          required
          aria-describedby="programa-onboarding-ayuda"
          aria-errormessage={intentado && errores.programa ? 'programa-onboarding-error' : undefined}
          aria-invalid={intentado && errores.programa ? 'true' : undefined}>
          <option value="" disabled>{facultad ? 'Selecciona tu programa' : 'Primero selecciona tu facultad'}</option>
          {#each programasDe(facultad) as opcion}
            <option value={opcion}>{opcion}</option>
          {/each}
        </select>
        <p class="ayuda-programa" id="programa-onboarding-ayuda">El programa académico en el que estás matriculado.</p>
        {#if intentado && errores.programa}
          <p class="error-programa" id="programa-onboarding-error">{errores.programa}</p>
        {/if}
      </div>

      <Campo
        etiqueta="Semestre"
        tipo="number"
        inputmode="numeric"
        min="1"
        max="20"
        requerido
        bind:valor={semestre}
        error={intentado ? errores.semestre : ''}
      />

      {#if editando}
        <div class="campo-programa">
          <label for="motivo-correccion">
            Motivo de la corrección <span aria-hidden="true">*</span>
          </label>
          <textarea
            id="motivo-correccion"
            bind:value={motivo}
            rows="3"
            maxlength="500"
            required
            aria-invalid={intentado && errores.motivo ? 'true' : undefined}
            aria-describedby="motivo-correccion-ayuda"
          ></textarea>
          <p class="ayuda-programa" id="motivo-correccion-ayuda">
            La corrección y su motivo quedan registrados. Si cambia tu categoría
            de edad, el sistema volverá a calcular las autorizaciones necesarias.
          </p>
          {#if intentado && errores.motivo}<p class="error-programa">{errores.motivo}</p>{/if}
        </div>
      {/if}
    </div>
  {/if}


  <div class="clase" class:resuelta={claseVinculada}>
    <div class="clase-texto">
      <span class="clase-icono"><Icono nombre="clase" medida={15} /></span>
      <div>
        <p class="clase-titulo">
          {claseVinculada ? 'Ya estás vinculado a una clase' : 'Falta vincularte a una clase'}
        </p>
        <p class="clase-nota">
          {claseVinculada
            ? 'Puedes cambiarla desde «Unirme a una clase» cuando lo necesites.'
            : 'Tu docente te da un código. Se hace desde la pantalla de siempre.'}
        </p>
      </div>
    </div>
    {#if !claseVinculada}
      <Boton variante="secundario" onclick={irAClase} deshabilitado={enviando}>
        Unirme a una clase
      </Boton>
    {/if}
  </div>

  {#if errorDelServidor}
    <p class="error-servidor" role="alert">{errorDelServidor}</p>
  {/if}

  {#if !datosPersonalesGuardados || editando}
    <div class="acciones">
      {#if editando}
        <Boton variante="secundario" onclick={cancelarEdicion} deshabilitado={enviando}>
          Cancelar
        </Boton>
      {/if}
      <Boton onclick={pedirConfirmacion} deshabilitado={enviando}>
        <Icono nombre="check" medida={15} />
        {enviando ? 'Guardando…' : editando ? 'Guardar corrección' : 'Guardar mis datos'}
      </Boton>
    </div>
  {/if}
</div>

<Dialogo bind:abierto={confirmando} titulo="¿Guardar estos datos?">
  <p>
    Vas a registrar que tienes <strong>{valores.edad} años</strong>, que estudias
    en la <strong>{valores.facultad}</strong>, el programa
    <strong>{valores.programa}</strong>, y que cursas el semestre
    <strong>{valores.semestre}</strong>.
  </p>
  {#if editando}
    <p>
      Motivo registrado: <strong>{motivo.trim()}</strong>. El historial anterior
      se conserva y la vinculación pendiente se reevaluará con los nuevos datos.
    </p>
  {/if}
  {#if declaraMinoria}
    <p>
      Al declarar que eres menor de 18 años, el sistema te pedirá además tu
      propio asentimiento y la autorización firmada de tu representante, y
      empezará a contar el plazo para entregarla. Hasta que esa autorización se
      apruebe no podrás usar el tutor.
    </p>
  {/if}
  <p class="consecuencia">
    Tu edad determina qué autorizaciones necesitas, así que revísala antes de
    continuar.
  </p>
  {#snippet acciones()}
    <Boton variante="secundario" onclick={() => (confirmando = false)} deshabilitado={enviando}>
      Volver a revisar
    </Boton>
    <Boton onclick={confirmar} deshabilitado={enviando}>
      {enviando ? 'Guardando…' : continuarAClase ? 'Guardar y continuar a la clase' : 'Sí, guardar'}
    </Boton>
  {/snippet}
</Dialogo>

<style>
  .perfil { display: flex; flex-direction: column; gap: 12px; }

  .identidad {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 10px 12px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-radius: var(--radius-sm);
  }

  .identidad-rotulo {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: var(--texto-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-tertiary);
  }

  .identidad-valor {
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 4px 10px;
    align-items: baseline;
    font-size: var(--texto-sm);
    color: var(--ink-primary);
  }

  .correo { color: var(--ink-secondary); overflow-wrap: anywhere; }

  .identidad-nota {
    margin: 0;
    font-size: var(--texto-xs);
    color: var(--ink-tertiary);
  }

  .explica {
    margin: 0;
    font-size: var(--texto-sm);
    line-height: 1.45;
    color: var(--ink-secondary);
  }

  .aviso-guardado {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: var(--espacio-sm) var(--espacio-md);
    background: var(--semantic-success-bg);
    border: 1px solid var(--semantic-success);
    border-radius: var(--radius-sm);
    color: var(--semantic-success);
    font-size: var(--texto-xs);
    line-height: 1.45;
  }

  .aviso-guardado div {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .aviso-guardado :global(.boton) { margin-inline-start: auto; flex: 0 0 auto; }

  .aviso-guardado strong { font-weight: 700; }

  .campos { display: flex; flex-direction: column; gap: 10px; }
  .campo-programa { display: flex; flex-direction: column; gap: 0.35em; }
  .campo-programa label { font-size: var(--texto-sm); font-weight: 500; }
  .campo-programa select {
    min-block-size: 2.5rem;
    padding: 0.55em 2.25em 0.55em 0.75em;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-trazado);
    background: var(--surface-paper);
    color: var(--ink-primary);
    font: inherit;
  }
  .campo-programa textarea {
    min-block-size: 5.5rem;
    padding: 0.65em 0.75em;
    resize: vertical;
    border: 1px solid var(--trazo);
    border-radius: var(--radius-trazado);
    background: var(--surface-paper);
    color: var(--ink-primary);
    font: inherit;
  }
  .campo-programa textarea:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 2px; }
  .campo-programa select:hover { border-color: var(--ink-tertiary); }
  .campo-programa select:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 2px; }
  .campo-programa select[aria-invalid='true'] { border-color: var(--semantic-error); }
  .ayuda-programa, .error-programa { margin: 0; font-size: var(--texto-sm); }
  .ayuda-programa { color: var(--ink-tertiary); }
  .error-programa { color: var(--semantic-error); }
  .error-programa::before { content: '⚠ '; }

  .clase {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 12px;
    background: var(--surface-paper);
    border: 1px solid var(--ink-ghost);
    border-inline-start: 3px solid var(--semantic-error);
    border-radius: var(--radius-sm);
  }

  .clase.resuelta { border-inline-start-color: var(--accent-main); }

  .clase-texto { display: flex; gap: 8px; align-items: flex-start; min-inline-size: 0; }

  .clase-icono { color: var(--ink-secondary); margin-block-start: 2px; flex-shrink: 0; }

  .clase-titulo {
    margin: 0;
    font-size: var(--texto-sm);
    font-weight: 600;
    color: var(--ink-primary);
  }

  .clase-nota {
    margin: 2px 0 0;
    font-size: var(--texto-xs);
    line-height: 1.4;
    color: var(--ink-secondary);
  }

  .error-servidor {
    margin: 0;
    padding: 8px 10px;
    font-size: var(--texto-sm);
    line-height: 1.4;
    color: var(--semantic-error);
    background: var(--surface-paper);
    border: 1px solid var(--semantic-error);
    border-radius: var(--radius-xs);
  }

  .error-servidor::before { content: '⚠ '; }

  .acciones { display: flex; justify-content: flex-end; gap: .6rem; flex-wrap: wrap; }

  .consecuencia { color: var(--ink-secondary); }

  @media (max-width: 30rem) {
    .clase { flex-direction: column; align-items: stretch; }
    .aviso-guardado { flex-wrap: wrap; }
    .aviso-guardado :global(.boton) { inline-size: 100%; margin-inline-start: 0; }
    .acciones :global(.boton) { inline-size: 100%; }
  }
</style>
