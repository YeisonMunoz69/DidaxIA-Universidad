<script>
  import Dialogo from './Dialogo.svelte';
  import Boton from './Boton.svelte';
  import ColumnaTambor from './ColumnaTambor.svelte';
  import { fechaBogota, descomponerFecha, diasDelMes } from '../../nucleo/formato/selectorFecha.js';
  let { value = $bindable(''), etiqueta = 'Fecha', conHora = false, minimo = '', maximo = '', exclusivo = false, limpiable = false, alCambiar = () => {} } = $props();
  const hoy = fechaBogota();
  let abierto = $state(false), fase = $state('fecha'), partes = $state(descomponerFecha(hoy));
  const fecha = $derived(`${partes.ano}-${partes.mes}-${partes.dia}`);
  const borrador = $derived(conHora ? `${fecha}T${partes.hora}:${partes.minuto}:${partes.segundo}` : fecha);
  const inferior = $derived(exclusivo && !conHora && minimo ? new Date(Date.parse(`${minimo.slice(0,10)}T12:00:00Z`) + 86400000).toISOString().slice(0,10) : minimo);
  const superior = $derived(maximo || (conHora ? `${hoy}T23:59:59` : hoy));
  const valido = $derived((!inferior || (exclusivo && conHora ? borrador > inferior : borrador >= inferior)) && borrador <= superior);
  const legible = $derived(value ? new Intl.DateTimeFormat('es-CO', {year:'numeric',month:'short',day:'numeric',timeZone:'UTC'}).format(new Date(`${value.slice(0,10)}T12:00:00Z`)) + (conHora ? ` · ${value.slice(11)}` : '') : 'Elegir fecha');
  const anos = $derived(Array.from({length: Math.max(1, Number(superior.slice(0,4)) - Number(inferior?.slice(0,4) || '1900') + 1)}, (_, i) => {const ano=String(i + Number(inferior?.slice(0,4) || '1900'));return {valor:ano,texto:ano};}));
  const numeros = (cantidad, inicio=0) => Array.from({length:cantidad},(_,i)=>({valor:String(i+inicio).padStart(2,'0'),texto:String(i+inicio).padStart(2,'0')}));
  const meses = numeros(12,1).map((opcion,i)=>({...opcion,texto:new Intl.DateTimeFormat('es-CO',{month:'short',timeZone:'UTC'}).format(new Date(Date.UTC(2026,i,1)))}));
  const dias = $derived(numeros(diasDelMes(partes.ano,partes.mes),1));
  function permitidaFecha(fecha){return (!inferior || fecha >= inferior.slice(0,10)) && fecha <= superior.slice(0,10);}
  function ajustarDia(){partes.dia=String(Math.min(Number(partes.dia),diasDelMes(partes.ano,partes.mes))).padStart(2,'0');}
  function abrir(){partes=descomponerFecha(value || hoy,conHora);fase='fecha';abierto=true;}
  function confirmar(nuevo=borrador){value=nuevo;alCambiar(nuevo);abierto=false;}
</script>
<div class="selector"><span class="etiqueta">{etiqueta}</span><button type="button" class="disparador" aria-label={`${etiqueta}: elegir fecha`} aria-expanded={abierto} onclick={abrir}><span aria-hidden="true">▦</span><span>{legible}</span><span aria-hidden="true">⌄</span></button></div>
{#if abierto}
<Dialogo bind:abierto titulo={`${etiqueta}: calendario`} ancho="25rem">
  <div class="paso"><strong>{conHora ? fase==='fecha' ? '1 · Fecha' : '2 · Hora' : 'Fecha'}</strong><output>{borrador.replace('T',' · ')}</output></div>
  <div class="ruedas"><div class="seleccion" aria-hidden="true"></div>
    {#if fase==='fecha'}
      <ColumnaTambor etiqueta="Año" opciones={anos} bind:value={partes.ano} alCambiar={ajustarDia}/>
      <ColumnaTambor etiqueta="Mes" opciones={meses} bind:value={partes.mes} alCambiar={ajustarDia}/>
      <ColumnaTambor etiqueta="Día" opciones={dias} bind:value={partes.dia}/>
    {:else}
      <ColumnaTambor etiqueta="Hora" opciones={numeros(24)} bind:value={partes.hora}/>
      <ColumnaTambor etiqueta="Minuto" opciones={numeros(60)} bind:value={partes.minuto}/>
      <ColumnaTambor etiqueta="Segundo" opciones={numeros(60)} bind:value={partes.segundo}/>
    {/if}
  </div>
  <div class="atajos">
    <button type="button" disabled={!permitidaFecha(hoy)} onclick={()=>partes=descomponerFecha(hoy,conHora)}>Hoy</button>
    <button type="button" disabled={!permitidaFecha(fechaBogota(-7))} onclick={()=>partes=descomponerFecha(fechaBogota(-7),conHora)}>Hace 7 días</button>
    {#if exclusivo && !conHora}<button type="button" disabled={!permitidaFecha(fechaBogota(1))} onclick={()=>partes=descomponerFecha(fechaBogota(1))}>Incluir hoy</button>{/if}
    {#if limpiable}<button type="button" onclick={()=>confirmar('')}>Borrar</button>{/if}
  </div>
  {#if !valido}<p role="alert">Elige un valor entre {inferior || 'el inicio del registro'} y {superior}.</p>{/if}
  {#if exclusivo}<p class="nota">«Hasta» se excluye del período consultado.</p>{/if}
  {#if conHora}<p class="nota">Hora civil de America/Bogota (UTC−5).</p>{/if}
  {#snippet acciones()}
    {#if fase==='hora'}<Boton variante="secundario" onclick={()=>fase='fecha'}>Volver a fecha</Boton>{:else}<Boton variante="secundario" onclick={()=>abierto=false}>Cancelar</Boton>{/if}
    {#if conHora && fase==='fecha'}<Boton onclick={()=>fase='hora'}>Continuar a la hora</Boton>{:else}<Boton deshabilitado={!valido} onclick={()=>confirmar()}>Confirmar {conHora?'fecha y hora':'fecha'}</Boton>{/if}
  {/snippet}
</Dialogo>
{/if}
<style>
  .selector{min-width:0}.etiqueta{display:block;margin-bottom:.3rem;font-size:var(--texto-xs);color:var(--ink-secondary);font-weight:750}.disparador{display:flex;align-items:center;justify-content:space-between;gap:.5rem;width:100%;min-height:44px;padding:.5rem .7rem;border:1px solid var(--trazo);border-radius:var(--radius-sm);color:var(--ink-primary);background:var(--surface-paper);box-shadow:var(--shadow-soft);font:inherit;font-size:var(--texto-sm);cursor:pointer}.disparador span:nth-child(2){min-width:0;overflow:hidden;text-overflow:ellipsis}.disparador span:first-child{color:var(--accent-main)}.disparador:focus-visible{outline:2px solid var(--help-color);outline-offset:2px}.paso{display:flex;justify-content:space-between;gap:.5rem;flex-wrap:wrap;font-size:var(--texto-xs);color:var(--ink-secondary);margin-bottom:.5rem}.ruedas{position:relative;display:flex;background:var(--surface-panel);border-radius:var(--radius-md);overflow:hidden}.seleccion{position:absolute;inset-inline:0;top:calc(50% + 15px);height:44px;transform:translateY(-50%);background:var(--accent-surface);border-block:1px solid var(--accent-main);pointer-events:none}.ruedas :global(.grupo){position:relative}.atajos{display:flex;gap:.4rem;margin-top:.7rem;flex-wrap:wrap}.atajos button{min-height:44px;border:1px solid var(--trazo-suave);border-radius:var(--radius-sm);background:var(--surface-paper);color:var(--ink-primary);padding:.4rem .6rem;font:inherit;cursor:pointer}.atajos button:disabled{opacity:.4}.nota{font-size:var(--texto-xs);color:var(--ink-secondary)}p[role=alert]{color:var(--semantic-error);font-size:var(--texto-xs)}
</style>
