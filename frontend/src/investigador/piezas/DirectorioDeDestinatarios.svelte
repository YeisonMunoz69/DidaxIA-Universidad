<script>
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import { onMount } from 'svelte';
  import Boton from '../../comun/base/Boton.svelte';
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';
  import * as equipo from '../../nucleo/api/equipo.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  let { elegidos = [], limite = 35, alElegir, alElegirCurso } = $props();
  let personas = $state([]), buscando = $state(''), rol = $state(''), clase = $state('');
  let cargando = $state(true), fallo = $state('');
  let clases = $derived([...new Map(personas.flatMap((p) => p.clases ?? []).map((c) => [c.id, c])).values()]);
  function esProfesional(p) {
    return (p.roles ?? []).some((r) => r.startsWith('docente') || r.startsWith('investigador')) || p.es_docente;
  }
  const estudiantesDelCurso = $derived(personas.filter((p) => !p.es_cuenta_prueba && p.correo
    && !esProfesional(p) && clase && p.clases?.some((c) => String(c.id) === String(clase))));
  const nuevosDelCurso = $derived([...new Map(estudiantesDelCurso
    .filter((p) => !seleccionado(p)).map((p) => [p.correo.toLowerCase(), p])).values()]);
  const cursoCabe = $derived(elegidos.length + nuevosDelCurso.length <= limite);
  let visibles = $derived(personas.filter((p) => {
    const roles = p.roles ?? [];
    const termino = buscando.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const texto = `${p.nombre} ${p.correo}`.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    // La matrícula, no rol_asignacion, identifica al estudiante. En la base real
    // las cuentas estudiantiles normalmente tienen roles=[]; "estudiante" es
    // el rol de sesión, no una asignación profesional del directorio.
    const matriculada = (p.clases?.length ?? 0) > 0;
    const profesional = esProfesional(p);
    const coincideRol = !rol || (rol === 'estudiante' ? matriculada && !profesional : roles.some((r) => r.startsWith(rol)) || (rol === 'docente' && p.es_docente));
    return !p.es_cuenta_prueba && p.correo && (matriculada || profesional)
      && coincideRol && (!clase || p.clases?.some((c) => String(c.id) === String(clase))) && texto.includes(termino);
  }));
  function seleccionado(p) { return elegidos.some((d) => d.correo.toLowerCase() === p.correo.toLowerCase()); }
  async function cargar() {
    cargando = true; fallo = '';
    try { personas = (await equipo.listar()).personas ?? []; }
    catch (e) { fallo = e?.cuerpo?.detalle || describir(e).explicacion; }
    finally { cargando = false; }
  }
  onMount(cargar);
</script>
<div class="directorio">
  <div class="resumen"><span>{elegidos.length}/{limite} destinatarios</span><BotonAyudaTooltip texto="Se muestran estudiantes con matrícula vigente y cuentas profesionales autorizadas. Se excluyen cuentas de prueba. El directorio no concede permisos ni define una cohorte de investigación." /></div>
  <label>Buscar nombre o correo<input type="search" bind:value={buscando} placeholder="Nombre o correo institucional" /></label>
  <div class="filtros">
    <label>Rol<select use:menuDesplegable={rol} bind:value={rol}><option value="">Todos</option><option value="estudiante">Estudiantes</option><option value="docente">Docentes</option><option value="investigador">Investigadores</option></select></label>
    <label>Clase<select use:menuDesplegable={clase} bind:value={clase}><option value="">Todas</option>{#each clases as c (c.id)}<option value={c.id}>{c.nombre}</option>{/each}</select></label>
  </div>
  {#if clase && alElegirCurso && !cargando && !fallo}
    <div class="seleccion-curso">
      <Boton variante="secundario" deshabilitado={!nuevosDelCurso.length || !cursoCabe}
        onclick={() => alElegirCurso(estudiantesDelCurso, clases.find((c) => String(c.id) === String(clase))?.nombre ?? '')}>
        Añadir estudiantes del curso
      </Boton>
      <p>{estudiantesDelCurso.length} estudiantes con correo en este curso; {nuevosDelCurso.length} por añadir. Se incluyen todos, aunque uses búsqueda o filtro de rol.</p>
      {#if !cursoCabe}<p role="alert">La selección completa superaría {limite} destinatarios. Retira personas o divide el envío; no se recortará el curso.</p>{/if}
    </div>
  {/if}
  {#if cargando}<CargadorCubo mensaje="Consultando el directorio…" compacto />{:else if fallo}<p role="alert">{fallo}</p><Boton onclick={cargar}>Reintentar</Boton>{:else}
    <div class="personas">
      {#each visibles as p (p.correo)}
        <button type="button" class:elegido={seleccionado(p)} aria-pressed={seleccionado(p)} disabled={!seleccionado(p) && elegidos.length >= limite} onclick={() => alElegir(p)}>
          <span class="avatar" aria-hidden="true">{p.nombre?.[0] ?? '?'}</span>
          <span class="identidad"><strong>{p.nombre || p.correo}</strong><small>{p.correo}</small><small>{(p.roles ?? []).length ? p.roles.join(' · ') : p.es_docente ? 'Docente' : 'Estudiante matriculado'}</small></span>
          <span aria-hidden="true">{seleccionado(p) ? '✓' : '+'}</span>
        </button>
      {:else}<p>No hay cuentas que coincidan con estos filtros.</p>{/each}
    </div>
  {/if}
</div>
<style>
  .directorio { display:grid; gap:.8rem; min-inline-size:0; }
  .resumen { display:flex; align-items:center; justify-content:space-between; color:var(--ink-secondary); font-size:var(--texto-sm); }
  .filtros { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.6rem; }
  .seleccion-curso { display:grid; gap:.4rem; padding:.75rem; border:1px solid var(--trazo-suave); border-radius:var(--radius-sm); background:var(--surface-panel); }
  .seleccion-curso p { margin:0; color:var(--ink-secondary); font-size:var(--texto-sm); }
  .seleccion-curso p[role='alert'] { color:var(--semantic-error); }
  label { display:grid; gap:.3rem; min-inline-size:0; font-size:var(--texto-sm); }
  input,select { inline-size:100%; min-inline-size:0; padding:.6rem; border:1px solid var(--trazo); border-radius:var(--radius-sm); color:var(--ink-primary); background:var(--surface-paper); font:inherit; }
  .personas { display:flex; flex-direction:column; gap:.4rem; max-block-size:23rem; overflow-y:auto; min-block-size:0; }
  button { display:flex; flex:none; inline-size:100%; min-block-size:4.25rem; gap:.7rem; align-items:center; padding:.7rem; text-align:start; border:1px solid var(--trazo-suave); border-radius:var(--radius-md); background:var(--surface-panel); color:var(--ink-primary); cursor:pointer; font:inherit; }
  button.elegido { border-color:var(--accent-main); background:var(--accent-surface); }
  button:disabled { opacity:.6; cursor:default; } button:focus-visible { outline:2px solid var(--accent-main); outline-offset:2px; }
  .avatar { flex:none; display:grid; place-items:center; inline-size:2.4rem; block-size:2.4rem; border-radius:var(--radius-pill); background:var(--accent-surface); color:var(--accent-main); }
  .identidad { flex:1; min-inline-size:0; display:grid; gap:.15rem; line-height:1.3; } strong,small,p { overflow-wrap:anywhere; } small { color:var(--ink-secondary); font-size:var(--texto-xs); }
</style>
