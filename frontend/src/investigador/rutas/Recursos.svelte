<script>
  import { onMount, flushSync } from 'svelte';
  import { sesion } from '../../nucleo/sesion/sesion.svelte.js';
  import { navegar, protegerSalida } from '../../enrutado/navegar.js';
  import { confirmarAccion } from '../../comun/estado/confirmaciones.svelte.js';
  import Dialogo from '../../comun/base/Dialogo.svelte';
  import CargadorCubo from '../../comun/base/CargadorCubo.svelte';
  import EnlacesPublicacion from '../../comun/recursos/EnlacesPublicacion.svelte';
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import Icono from '../../comun/base/Icono.svelte';
  import BotonAyudaTooltip from '../../comun/base/BotonAyudaTooltip.svelte';
  import PestanasSegmentadas from '../../comun/base/PestanasSegmentadas.svelte';
  import Accion from '../../comun/recursos/AccionRecurso.svelte';
  import AccionesBiblioteca from '../../comun/recursos/AccionesBiblioteca.svelte';
  import * as api from '../../nucleo/api/recursos.js';
  import { importarPresentacion } from '../../nucleo/recursos/importarPresentacion.js';
  import SelectorDestinatarios from '../../comun/recursos/SelectorDestinatarios.svelte';
  import GestionDestinatarios from '../../comun/recursos/GestionDestinatarios.svelte';
  import EditorEncuesta from '../../comun/recursos/EditorEncuesta.svelte';
  import EditorDiapositivas from '../../comun/recursos/EditorDiapositivas.svelte';
  import HerramientasPresentacion from '../../comun/recursos/HerramientasPresentacion.svelte';
  import FormularioEncuesta from '../../comun/recursos/FormularioEncuesta.svelte';
  import VisorDiapositivas from '../../comun/recursos/VisorDiapositivas.svelte';
  import MetricasRecursos from '../../comun/recursos/MetricasRecursos.svelte';
  import BibliotecaDiapositivas from '../../comun/recursos/BibliotecaDiapositivas.svelte';
  import '../../comun/recursos/recursos.css';
  import { menuDesplegable } from '../../comun/base/menuDesplegable.js';

  let pantallaPresentacion, presentacionActiva=$state(false), contenidoPresentado=$state(null), tituloPresentado=$state(''), errorPresentacion=$state(''), avisoPantalla=$state('');
  const contenidoEspera={title:'Presentación',slides:[{title:'Preparando presentación',items:[]}]};
  let entroEnPantalla=false, entradaPresentacion='';
  function cerrarPresentacion(retroceder=true){
    const propia=entradaPresentacion&&history.state?.didaxiaPresentacion===entradaPresentacion;entradaPresentacion='';
    if(retroceder&&propia)history.back();
    try{screen.orientation?.unlock?.();}catch{}
    presentacionActiva=false;contenidoPresentado=null;entroEnPantalla=false;
    if(document.fullscreenElement===pantallaPresentacion||document.webkitFullscreenElement===pantallaPresentacion){
      const salir=document.exitFullscreen||document.webkitExitFullscreen;
      Promise.resolve(salir?.call(document)).catch(()=>{});
    }
  }
  async function presentar(r){
    if(presentacionActiva)return;
    entradaPresentacion=crypto.randomUUID();history.pushState({...history.state,didaxiaPresentacion:entradaPresentacion},'',location.href);
    flushSync(()=>{presentacionActiva=true;contenidoPresentado=null;tituloPresentado=r.titulo;errorPresentacion='';avisoPantalla='';});
    pantallaPresentacion.focus();
    const solicitud=entradaPresentacion;
    // Se solicita dentro del clic, antes de consultar el recurso: conserva la activación del usuario.
    const entrar=pantallaPresentacion.requestFullscreen||pantallaPresentacion.webkitRequestFullscreen;
    if(entrar){try{Promise.resolve(entrar.call(pantallaPresentacion)).then(()=>{if(presentacionActiva&&matchMedia('(pointer:coarse)').matches)try{Promise.resolve(screen.orientation?.lock?.('landscape')).catch(()=>{});}catch{}}).catch(()=>{avisoPantalla='El navegador no permitió pantalla completa. La presentación ocupa esta ventana.';});}catch{avisoPantalla='La presentación ocupa esta ventana.';}}
    else avisoPantalla='La presentación ocupa esta ventana; este navegador no ofrece pantalla completa.';
    try{
      const datos=r.contenido?r:await api.consultar(r.id);
      if(presentacionActiva&&entradaPresentacion===solicitud)contenidoPresentado=JSON.parse(JSON.stringify(datos.contenido));
    }catch(e){errorPresentacion=api.mensaje(e);}
  }
  onMount(()=>{
    function cambio(){
      const activa=document.fullscreenElement||document.webkitFullscreenElement;
      if(activa===pantallaPresentacion)entroEnPantalla=true;
      else if(entroEnPantalla)cerrarPresentacion();
    }
    function atras(){if(presentacionActiva&&history.state?.didaxiaPresentacion!==entradaPresentacion)cerrarPresentacion(false);}
    window.addEventListener('popstate',atras);
    document.addEventListener('fullscreenchange',cambio);document.addEventListener('webkitfullscreenchange',cambio);
    return()=>{window.removeEventListener('popstate',atras);document.removeEventListener('fullscreenchange',cambio);document.removeEventListener('webkitfullscreenchange',cambio);cerrarPresentacion(false);};
  });
  let { tipo = '' } = $props();
  let lista = $state([]), cursos = $state([]), plantillas = $state([]);
  let recurso = $state(null), guardado = $state(''), modo = $state('lista');
  let seleccion = $state([]), filtro = $state('todos'), buscar = $state('');
  let error = $state(''), aviso = $state(''), ocupado = $state(false), cargando = $state(true);
  let respuestasPrevia = $state({});
  let controlesEditor = $state(null);
  let mensajeOperacion = $state('Preparando el recurso…'), errorImportacion = $state(''), dialogoErrorImportacion = $state(false);
  let ampliado=$state(false), dialogoPublicacion=$state(false), dialogoInformacion=$state(false), archivoImportado=$state();
  let publicacionLista=$state(null), recursoEnlaces=$state(null), enlacesAbiertos=$state(false);
  let archivoEncuesta=$state();
  function verEnlaces(r){recursoEnlaces=r;enlacesAbiertos=true;}
  let audiencia=$state('estudiantes'), destinatariosDocentes=$state([]), verPlantillas=$state(false);
  let coleccionEncuestas=$state('biblioteca');
  const encuestas=$derived(lista.filter(r=>r.tipo==='encuesta'));
  const seccionesEncuestas=$derived([
    {id:'biblioteca',titulo:`Mis encuestas (${encuestas.filter(r=>r.estado!=='archivado').length})`,icono:'encuesta'},
    {id:'archivadas',titulo:`Archivadas (${encuestas.filter(r=>r.estado==='archivado').length})`,icono:'archivar'}
  ]);
  function elegirColeccionEncuestas(id){coleccionEncuestas=id;filtro='todos';verPlantillas=false;}
  const destinosDisponibles=$derived(audiencia==='docentes'?destinatariosDocentes:audiencia==='individuales'?[]:cursos);
  const destinoPublicacion=$derived(publicacionLista??recurso);
  const investigador = $derived(sesion.rol === 'investigador');
  const nombreSeccion = $derived(tipo === 'encuesta' ? 'Encuestas' : 'Diapositivas');
  const visible = $derived(lista.filter(r => (!tipo || r.tipo === tipo) && (tipo!=='encuesta'||(coleccionEncuestas==='archivadas'?r.estado==='archivado':r.estado!=='archivado')) && (filtro === 'todos' || r.estado === filtro) && r.titulo.toLowerCase().includes(buscar.toLowerCase())));
  const sucio = $derived(!!recurso && recurso.estado === 'borrador' && JSON.stringify(recurso) !== guardado);

  async function ejecutar(accion) {
    if (ocupado) return false;
    ocupado = true; error = ''; aviso = '';
    try { await accion(); return true; } catch (e) { error = api.mensaje(e); return false; } finally { ocupado = false; }
  }
  async function cargar() {
    cargando = true; error = '';
    try {
      [lista, cursos, plantillas, destinatariosDocentes] = await Promise.all([
        api.listar(), api.clases(), investigador?api.plantillas():[], investigador?api.docentes():[]
      ]);
    } catch (e) { error = api.mensaje(e); } finally { cargando = false; }
  }
  async function permitirSalida() {
    if (ocupado) return false;
    if (!sucio) return true;
    const decision = await confirmarAccion({ tipo:'guardar', titulo:'Hay cambios sin guardar',
      descripcion:'Puedes guardar tus cambios antes de salir, seguir editando o salir sin conservarlos.',
      confirmar:'Salir sin guardar', cancelar:'Seguir editando', alternativa:'Salir y guardar' });
    if (decision !== 'alternativa') return decision === true;
    if (!await guardarBorrador()) return false;
    toast.exito('Borrador guardado. Puedes retomarlo desde tu biblioteca.');
    return true;
  }
  onMount(() => {
    cargar();
    return protegerSalida(permitirSalida);
  });
  function editar(r) { recurso = r; guardado = JSON.stringify(r); publicacionLista=null; modo = r.estado === 'borrador' ? 'editor' : 'previa'; ampliado=tipo==='diapositivas'&&modo==='editor'; seleccion = []; audiencia=r.contenido.audiencia_sugerida==='docentes'?'docentes':'estudiantes'; respuestasPrevia = {}; }
  async function salir() {
    if (!await permitirSalida()) return;
    recurso = null; modo = 'lista'; verPlantillas=false; ampliado=false; error = ''; aviso = ''; cargar();
  }
  async function abrir(r) { await ejecutar(async () => editar(await api.consultar(r.id))); }
  async function publicarDesdeLista(r) {
    await ejecutar(async()=>{
      const actual=await api.consultar(r.id);
      if(!['borrador','cerrado'].includes(actual.estado))throw new Error('Cierra la publicación actual antes de crear un nuevo envío.');
      publicacionLista=actual;seleccion=[];audiencia=actual.contenido.audiencia_sugerida==='docentes'?'docentes':'estudiantes';dialogoPublicacion=true;
    });
  }
  function cerrarPublicacion(){dialogoPublicacion=false;publicacionLista=null;seleccion=[];}
  function prepararPublicacion(){seleccion=[];audiencia=recurso.contenido.audiencia_sugerida==='docentes'?'docentes':'estudiantes';dialogoPublicacion=true;}
  async function guardar() {
    if (!await confirmarAccion({ tipo:'guardar', titulo:'¿Guardar este borrador?', descripcion:'Se guardarán las preguntas o diapositivas en tu biblioteca. Puedes seguir editando antes de publicar.', confirmar:'Guardar borrador', cancelar:'Seguir editando' })) return;
    await guardarBorrador();
  }
  async function guardarBorrador() {
    mensajeOperacion = 'Guardando el borrador y sus imágenes…';
    const correcto = await ejecutar(async () => {
      const enviado = JSON.stringify(recurso);
      const resultado = await api.guardar(JSON.parse(enviado));
      // Conserva cualquier edición realizada mientras responde el servidor.
      recurso = JSON.stringify(recurso) === enviado ? resultado : { ...recurso, id:resultado.id, revision:resultado.revision };
      guardado = JSON.stringify(resultado);
      aviso = sucio ? 'Se guardaron los cambios enviados. Hay nuevos cambios por guardar.' : 'Borrador guardado en tu cuenta.';
      lista = await api.listar();
    });
    mensajeOperacion = 'Preparando el recurso…';
    if (!correcto) toast.error(error || 'No se guardó el borrador. Tus cambios siguen en el editor.');
    return correcto && !sucio;
  }
  async function publicar(destino=recurso,desdeLista=false) {
    if (!seleccion.length) return;
    const destinos = audiencia==='individuales'?`${seleccion.length} estudiantes elegidos en el selector`:destinosDisponibles.filter(c => seleccion.includes(c.id)).map(c => c.nombre).join(' · ');
    const repetir=destino.estado!=='borrador';
    if (!await confirmarAccion({ titulo:repetir?`¿Volver a publicar ${destino.tipo==='encuesta'?'esta encuesta':'esta presentación'}?`:`¿Publicar ${destino.tipo === 'encuesta' ? 'esta encuesta' : 'estas diapositivas'}?`,
      descripcion:repetir?`Se creará un nuevo envío para ${destinos}, con sus propias respuestas, aperturas y pendientes. ${audiencia==='docentes'?'Los docentes seleccionados':'Los estudiantes'} recibirán una nueva notificación. Los datos de los envíos anteriores se conservarán.`:`Se guardará el contenido y se enviará a ${seleccion.length} ${audiencia==='docentes'?'docente(s)':audiencia==='individuales'?'estudiante(s)':'curso(s)'}: ${destinos}. ${audiencia==='docentes'?'Los docentes seleccionados':'Los estudiantes'} recibirán una notificación. Para cambiar el contenido después tendrás que crear una copia.`, confirmar:'Confirmar publicación', cancelar:'Revisar destinos' })) { if(desdeLista){publicacionLista=null;seleccion=[];} return; }
    await ejecutar(async () => {
      const borrador=destino.estado==='borrador'?await api.guardar(destino):destino;
      if(desdeLista)publicacionLista=borrador;
      else{recurso=borrador;guardado=JSON.stringify(recurso);}
      const publicado=await api.publicar(borrador, seleccion,audiencia);
      if(!desdeLista){recurso=publicado;guardado=JSON.stringify(recurso);modo='previa';ampliado=false;}
      publicacionLista=null;
      aviso = audiencia==='docentes'?'Publicado únicamente para los docentes seleccionados.':'Publicado. Los estudiantes matriculados lo recibirán en sus notificaciones.'; lista = await api.listar();seleccion=[];
    });
  }
  let encuestaAmpliada=$state(null), ampliarAbierto=$state(false);
  function prepararAmpliacion(r){encuestaAmpliada=r;ampliarAbierto=true;}
  async function importarEncuesta(e){
    const control=e.currentTarget,archivo=control.files?.[0];if(!archivo)return;
    mensajeOperacion='Leyendo la encuesta y comprobando sus imágenes…';
    try{await ejecutar(async()=>{
      if(!archivo.name.toLowerCase().endsWith('.json')||archivo.size>12_000_000)throw new Error('Selecciona una encuesta JSON de hasta 12 MB.');
      let datos;try{datos=JSON.parse(await archivo.text());}catch{throw new Error('El archivo no contiene un JSON válido.');}
      if(!datos||datos.tipo!=='encuesta'||!Array.isArray(datos.contenido?.paginas))throw new Error('El archivo debe contener una encuesta DidaxIa con sus páginas.');
      // El archivo siempre crea un borrador nuevo. Sus IDs/estado/envíos nunca se importan.
      editar(await api.guardar({tipo:'encuesta',titulo:datos.titulo,descripcion:datos.descripcion??'',contenido:datos.contenido}));
      aviso='Encuesta importada como un nuevo borrador. Revisa preguntas e imágenes antes de publicar.';
      toast.exito('Encuesta importada. No se modificó ninguna publicación existente.');
    });}finally{control.value='';mensajeOperacion='Preparando el recurso…';}
  }
  async function importar(e) {
    const control = e.currentTarget, archivo = control.files[0]; if (!archivo) return;
    mensajeOperacion = 'Leyendo y preparando la presentación…';
    try {
      const correcta = await ejecutar(async () => {
        const contenido = await importarPresentacion(archivo);
        mensajeOperacion = `Guardando ${contenido.slides.length} diapositivas en tu biblioteca…`;
        editar(await api.guardar({ tipo:'diapositivas', titulo:contenido.title || archivo.name, descripcion:contenido.caption || '', contenido }, { espera:120000 }));
        aviso = 'Presentación importada como borrador.';
        toast.exito(`${contenido.slides.length} diapositivas importadas. Tu borrador está guardado en la biblioteca.`);
      });
      if (!correcta) { errorImportacion = error; dialogoErrorImportacion = true; }
    } finally { control.value = ''; mensajeOperacion = 'Preparando el recurso…'; }
  }
  async function usarPlantilla(p) { await ejecutar(async () => { editar(await api.guardar(await api.plantilla(p.id))); aviso = 'Copia editable guardada como borrador.'; }); }
  async function duplicar(r) {
    if (!await confirmarAccion({ titulo:'¿Crear una copia editable?', descripcion:`Se creará un nuevo borrador de «${r.titulo}» para preparar otra versión.`, confirmar:'Crear copia' })) return;
    await ejecutar(async () => {editar(await api.duplicar(r.id));aviso='Copia editable creada como borrador.';});
  }
  async function plantillaPersonal(r){
    if(!await confirmarAccion({titulo:'¿Guardar como plantilla?',descripcion:'Se conservará una copia reutilizable. Cada vez que la uses crearás un borrador independiente.',confirmar:'Guardar plantilla'}))return;
    await ejecutar(async()=>{await api.guardarPlantilla(r.id);plantillas=await api.plantillas();aviso='Plantilla guardada. La encontrarás en Plantillas.';});
  }
  async function cambiar(r, estado) {
    const cerrar = estado === 'cerrado';
    if (!await confirmarAccion({ tipo:'eliminar', titulo:cerrar ? '¿Cerrar esta publicación?' : '¿Archivar este recurso?',
      descripcion:cerrar ? 'Quienes tengan el recurso abierto dispondrán de 8 minutos adicionales para terminar. Después se cerrará el material y la encuesta dejará de recibir respuestas. Las respuestas enviadas se conservarán.' : 'El recurso desaparecerá de las notificaciones de sus destinatarios. Sus resultados se conservarán en la biblioteca.', confirmar:cerrar ? 'Cerrar publicación' : 'Archivar recurso' })) return;
    await ejecutar(async () => { await api.cambiarEstado(r.id, estado); await cargar(); aviso=cerrar?'Publicación cerrada. El tiempo adicional ya está disponible para quienes tenían el recurso abierto.':'Recurso archivado. Sus resultados se conservan en la biblioteca.'; });
  }
  async function eliminar(r) {
    const borrador=r.estado==='borrador';
    if (!await confirmarAccion({ tipo:'eliminar', titulo:borrador?'¿Eliminar este borrador?':'¿Eliminar este recurso?', descripcion:`Se eliminará «${r.titulo}», sus publicaciones y el historial de aperturas. ${r.tipo==='encuesta'?'Sólo se permite si nadie ha enviado respuestas en ninguno de sus envíos.':'Sólo se permite si no tiene visitas ni respuestas registradas.'} Esta acción no se puede deshacer.`, confirmar:borrador?'Eliminar borrador':'Eliminar recurso', cancelar:'Conservar recurso' })) return;
    await ejecutar(async () => { await api.eliminar(r.id); await cargar(); toast.exito('Recurso eliminado de tu biblioteca.'); });
  }
</script>

<svelte:window onkeydown={e=>{if(presentacionActiva&&e.key==='Escape')cerrarPresentacion();}} onbeforeunload={(e) => { if (sucio) { e.preventDefault(); e.returnValue = ''; } }} />
<section class="recursos-pantalla" class:espacio-diapositivas={tipo==='diapositivas'} class:espacio-encuestas={tipo==='encuesta'} class:ampliado={ampliado}>
 {#if ocupado}<div class="carga-operacion"><CargadorCubo compacto mensaje={mensajeOperacion} /></div>{/if}
 {#if tipo==='diapositivas'}
  <div class="cabecera-escritorio" class:editando={modo!=='lista'}>
   <Accion icono="volver" class="retorno-escritorio" disabled={ocupado} onclick={()=>modo==='lista'?navegar('/recursos'):salir()}><span class="rotulo-retorno">{modo==='lista'?'Volver a recursos':'Volver a diapositivas'}</span></Accion>
   <div class="titulo-escritorio"><Icono nombre="diapositivas" medida={24} /><div><h1>{modo==='lista'?'Diapositivas':recurso?.titulo}</h1><span>{modo==='lista'?'Biblioteca de investigación':modo==='metricas'?'Participación de tus cursos':sucio?'Cambios sin guardar':recurso?.estado==='borrador'?'Borrador guardado':`Publicación ${recurso?.estado}`}</span></div></div>
   <div class="acciones-escritorio">
    {#if modo==='lista'&&investigador}<Accion icono="importar" disabled={ocupado} onclick={()=>archivoImportado.click()}>Importar HTML o JSON</Accion><input bind:this={archivoImportado} type="file" accept=".html,.json" hidden onchange={importar} /><Accion icono="nueva" class="primario" disabled={ocupado} onclick={()=>usarPlantilla({id:'base'})}>Crear diapositivas desde la base</Accion>
    {:else if modo!=='lista'}<Accion icono={ampliado?'reducir':'ampliar'} onclick={()=>ampliado=!ampliado}>{ampliado?'Restaurar espacio':modo==='editor'?'Ampliar editor':'Ampliar panel'}</Accion>
      {#if investigador&&recurso?.estado==='borrador'}<Accion icono="guardar" disabled={ocupado} onclick={guardar}>Guardar borrador</Accion>{/if}
      {#if investigador&&['borrador','cerrado'].includes(recurso?.estado)}<Accion icono="publicar" class="primario" disabled={ocupado} onclick={prepararPublicacion}>{recurso?.estado==='borrador'?'Publicar':'Volver a publicar'}</Accion>{/if}
    {/if}
   </div>
  </div>
 {:else}
  {#if tipo && modo === 'lista'}<Accion icono="volver" class="volver-recurso" onclick={() => navegar('/recursos')}><span class="rotulo-retorno">Volver a recursos</span></Accion>{/if}
  <div class="cabecera-recursos">
    <span class="emblema-recurso"><Icono nombre={tipo || 'recursos'} medida={30} /></span>
    <div><p class="eyebrow">{investigador ? 'Investigación' : 'Mis cursos'} · Recursos</p>
      <h1>{modo === 'lista' ? (tipo ? nombreSeccion : 'Recursos y encuestas') : recurso?.titulo}</h1>
      <p class="muted">{modo !== 'lista' ? (sucio ? 'Hay cambios sin guardar' : 'Contenido guardado') : tipo === 'encuesta' ? 'Diseña preguntas, escucha a tus cursos y explora sus respuestas.' : tipo === 'diapositivas' ? 'Prepara tus sesiones, presenta materiales y compártelos con tus cursos.' : 'Un espacio para preparar y compartir los materiales de investigación.'}</p>
    </div>
  </div>
 {/if}
  {#if error}<p class="aviso error" role="alert">{error}</p>{/if}
  {#if aviso}<p class="aviso" role="status"><Icono nombre="check" />{aviso}</p>{/if}
  {#if tipo==='diapositivas'&&modo==='lista'}
      <BibliotecaDiapositivas {lista} plantillas={plantillas.filter(p=>p.tipo!=='encuesta')} {cargando} {ocupado} {investigador} bind:buscar bind:filtro
     alCrear={()=>usarPlantilla({id:'base'})} alAbrir={abrir} alPresentar={presentar} alDuplicar={duplicar} alPublicar={publicarDesdeLista}
     alMetricas={(r)=>{recurso=r;guardado=JSON.stringify(r);modo='metricas';}}
     alEnlaces={verEnlaces} alCambiar={cambiar} alEliminar={eliminar} alPlantilla={usarPlantilla} alGuardarPlantilla={plantillaPersonal} />
  {:else if tipo==='diapositivas'&&recurso}
   <div class="herramientas-escritorio">
    <div class="pestanas-recurso" aria-label="Vistas del recurso">
     {#if investigador&&recurso.contenido}
      {#if recurso.estado==='borrador'}<Accion icono="editar" aria-pressed={modo==='editor'} onclick={()=>{modo='editor';ampliado=true;}}>Editar</Accion>{/if}
      <Accion icono="diapositivas" aria-pressed={modo==='previa'} onclick={()=>presentar(recurso)}>Presentar</Accion>
     {/if}
     {#if recurso.id}<Accion icono="analitica" aria-pressed={modo==='metricas'} onclick={()=>modo='metricas'}>Métricas</Accion>{/if}
    </div>
    {#if modo==='editor'}<HerramientasPresentacion controles={controlesEditor} />{/if}
    <Accion icono="ajustes" onclick={()=>dialogoInformacion=true}>Información</Accion>
   </div>
   <div class="area-editor-escritorio" class:con-lienzo={modo==='editor'}>
    {#if modo==='editor'}<EditorDiapositivas bind:recurso espacioTrabajo alControles={c=>controlesEditor=c} />
    {:else if modo==='previa'}<VisorDiapositivas contenido={recurso.contenido} titulo={recurso.titulo} />
    {:else if modo==='metricas'}{#key recurso.id}<MetricasRecursos {recurso} />{/key}{/if}
   </div>
   <Dialogo bind:abierto={dialogoInformacion} titulo="Información del recurso" tipo="comunicar" ancho="42rem">

    <label>Nombre en la biblioteca<input maxlength="250" bind:value={recurso.titulo} disabled={recurso.estado!=='borrador'} /></label><label>Descripción<textarea rows="4" maxlength="5000" bind:value={recurso.descripcion} disabled={recurso.estado!=='borrador'}></textarea></label>
    <p class="muted">{recurso.contenido?.slides?.length??0} diapositivas · {recurso.estado} · {recurso.id?'Guardada en tu biblioteca':'Nueva presentación'}</p>
    <div class="acciones"><Accion icono="check" class="primario" onclick={()=>dialogoInformacion=false}>Listo</Accion></div>
   </Dialogo>
  {:else if modo === 'lista' && !tipo}
    <div class="secciones-recursos">
      {#each [{tipo:'encuesta',nombre:'Encuestas',camino:'/recursos/encuestas',detalle:'Borradores, formularios por páginas y resultados de tus cursos.',accion:'Gestionar encuestas'}, {tipo:'diapositivas',nombre:'Diapositivas',camino:'/recursos/diapositivas',detalle:'Presentaciones existentes, plantilla base y materiales para tus sesiones.',accion:'Gestionar diapositivas'}] as seccion}
        <article class="entrada-recurso">
          <span class="emblema-recurso"><Icono nombre={seccion.tipo} medida={35} /></span>
          <h2>{seccion.nombre}</h2><p>{seccion.detalle}</p>
          <div class="resumen-recurso"><span>{lista.filter(r => r.tipo === seccion.tipo).length} en biblioteca</span><span>{lista.filter(r => r.tipo === seccion.tipo && r.estado === 'publicado').length} publicados</span></div>
          <Accion class="primario" icono="flecha-der" onclick={() => navegar(seccion.camino)}>{seccion.accion}</Accion>
        </article>
      {/each}
    </div>
  {:else if modo === 'lista'}
    {#if tipo==='encuesta'}
      <PestanasSegmentadas opciones={seccionesEncuestas} activa={coleccionEncuestas} alElegir={elegirColeccionEncuestas} etiqueta="Biblioteca de encuestas" prefijo="biblioteca-encuestas" />
      <p class="muted">{coleccionEncuestas==='archivadas'?'Aquí se conservan las encuestas archivadas y sus resultados. Puedes eliminarlas únicamente si no recibieron respuestas.':'Gestiona tus borradores y publicaciones. Archiva las encuestas que quieras retirar de este listado.'}</p>
    {/if}
    <div role="tabpanel" id={`biblioteca-encuestas-panel-${coleccionEncuestas}`} aria-labelledby={`biblioteca-encuestas-pestana-${coleccionEncuestas}`}>
    <div class="barra-recursos">
      {#if investigador}
        {#if tipo === 'encuesta'}<Accion icono="nueva" class="primario" disabled={ocupado} onclick={() => editar(api.encuestaNueva())}>Crear encuesta</Accion><Accion icono="importar" disabled={ocupado} onclick={()=>archivoEncuesta.click()}>Importar encuesta JSON</Accion><input bind:this={archivoEncuesta} type="file" accept=".json,application/json" aria-label="Archivo de encuesta JSON" hidden onchange={importarEncuesta} /><Accion icono="duplicar" aria-pressed={verPlantillas} class={verPlantillas?'plantillas-activas':''} onclick={()=>{verPlantillas=!verPlantillas;buscar='';}}>Plantillas de encuestas</Accion>
        {:else}<Accion icono="diapositivas" class="primario" disabled={ocupado} onclick={() => usarPlantilla({id:'base'})}>Crear diapositivas desde la base</Accion>
          <label class="importar-recurso"><Icono nombre="importar" />Importar diapositivas DidaxIa<input type="file" accept=".html,.json" disabled={ocupado} onchange={importar} /></label>
        {/if}
      {/if}
      <div class="filtros-recursos"><label><span><Icono nombre="buscar" />Buscar recurso</span><input type="search" bind:value={buscar} placeholder={`Buscar ${nombreSeccion.toLowerCase()}…`} /></label>
        {#if tipo!=='encuesta'||coleccionEncuestas!=='archivadas'}<label>Estado<select use:menuDesplegable aria-label="Mostrar" bind:value={filtro}><option value="todos">Todos los estados</option><option value="borrador">Borradores</option><option value="publicado">Publicados</option><option value="cerrado">Cerrados</option>{#if tipo!=='encuesta'}<option value="archivado">Archivados</option>{/if}</select></label>{/if}</div>
    </div>
    {#if investigador&&tipo==='encuesta'&&verPlantillas}<section class="bloque pantalla-plantillas"><Accion icono="volver" onclick={()=>verPlantillas=false}>Volver a mis encuestas</Accion><h2><Icono nombre="duplicar" />Plantillas de encuestas</h2><p>Empieza con una estructura lista o reutiliza una plantilla guardada por tu equipo.</p><div class="tarjetas">{#each plantillas.filter(p=>p.tipo==='encuesta') as p}<article class="tarjeta plantilla"><div class="titulo-plantilla"><h3>{p.titulo}</h3>{#if p.descripcion}<BotonAyudaTooltip texto={p.descripcion} icono="conversacion" tamano="lg" ariaLabel={`Información de la plantilla ${p.titulo}`} />{/if}</div><div class="pie-plantilla"><span class="muted">{p.personalizada?'Personalizada':'Plantilla del sistema'}</span><Accion icono="nueva" onclick={()=>usarPlantilla(p)} disabled={ocupado}>Usar plantilla</Accion></div></article>{/each}</div></section>
    {/if}
    {#if !verPlantillas&&cargando}<CargadorCubo mensaje="Cargando recursos…" />{:else if !verPlantillas&&!visible.length}<div class="vacio-recurso"><Icono nombre={tipo==='encuesta'&&coleccionEncuestas==='archivadas'?'archivar':tipo} medida={38} /><h2>{tipo==='encuesta'&&coleccionEncuestas==='archivadas'?'Encuestas archivadas':`Tu biblioteca de ${nombreSeccion.toLowerCase()}`}</h2><p>{coleccionEncuestas==='archivadas'?'No hay encuestas archivadas que coincidan con tu búsqueda. Al archivar una encuesta aparecerá aquí con sus resultados.':'No hay recursos que coincidan con este filtro. Crea un borrador o revisa los filtros para comenzar.'}</p></div>{/if}
    <div class="tarjetas">{#each (verPlantillas?[]:visible) as r (r.id)}<article class="tarjeta tarjeta-gestion">
      <div class="cabecera-tarjeta"><Icono nombre={r.tipo} medida={27} /><div class="indicadores-tarjeta"><span class="estado" class:publicado={r.estado==='publicado'}>{r.estado}</span><BotonAyudaTooltip texto={r.descripcion || 'Añade una descripción al preparar el recurso.'} icono="conversacion" tamano="lg" ariaLabel={`Descripción de ${r.titulo || 'Borrador sin título'}`} /></div></div>
      <h2 class="nombre-encuesta">{r.titulo || 'Borrador sin título'}</h2>
      <p class="muted datos-tarjeta"><span>{r.cursos} destinatarios · {r.envios} envíos</span><span>Actualizado {new Date(r.actualizado_en).toLocaleDateString()}</span></p>
      <AccionesBiblioteca titulo={r.titulo || 'Borrador sin título'} esquina>
        {#if investigador}<Accion icono={r.estado === 'borrador' ? 'editar' : 'visible'} disabled={ocupado} onclick={() => abrir(r)}>{r.estado === 'borrador' ? 'Editar' : 'Ver / presentar'}</Accion>{#if ['borrador','cerrado'].includes(r.estado)}<Accion icono="publicar" class="primario" disabled={ocupado} onclick={()=>publicarDesdeLista(r)}>{r.estado==='borrador'?'Publicar':'Volver a publicar'}</Accion>{/if}{/if}
        <Accion icono="analitica" disabled={ocupado} onclick={() => {recurso=r;guardado=JSON.stringify(r);modo='metricas';}}>Métricas</Accion>
        {#if r.envios>0}<Accion icono="copiar" disabled={ocupado} onclick={()=>verEnlaces(r)}>Enlaces</Accion>{/if}
        {#if investigador}
          <Accion icono="duplicar" disabled={ocupado} onclick={() => duplicar(r)}>Duplicar</Accion><Accion icono="guardar" disabled={ocupado} onclick={()=>plantillaPersonal(r)}>Guardar como plantilla</Accion>
          {#if r.tipo==='encuesta' && r.estado==='publicado'}<Accion icono="clase" disabled={ocupado} onclick={()=>prepararAmpliacion(r)}>Gestionar destinatarios</Accion>{/if}
          {#if r.estado === 'publicado'}<Accion icono="candado" disabled={ocupado} onclick={() => cambiar(r,'cerrado')}>Cerrar publicación</Accion>{/if}
          {#if r.puede_eliminar}<Accion icono="eliminar" disabled={ocupado} onclick={() => eliminar(r)}>{r.estado==='borrador'?'Eliminar borrador':'Eliminar encuesta'}</Accion>{/if}
          {#if r.estado !== 'archivado'}<Accion icono="archivar" disabled={ocupado} onclick={() => cambiar(r,'archivado')}>Archivar</Accion>{/if}
        {/if}
      </AccionesBiblioteca>
    </article>{/each}</div>
    </div>
    {#if investigador && tipo === 'diapositivas' && plantillas.length}
      <div class="titulo-coleccion"><Icono nombre="diapositivas" medida={25} /><div><h2>Materiales del piloto y plantilla base</h2><p>Crea una copia para editarla, presentarla o publicarla.</p></div></div>
      <div class="tarjetas">{#each plantillas as p}<article class="tarjeta plantilla"><span class="emblema-recurso"><Icono nombre="diapositivas" medida={25} /></span><h3>{p.titulo}</h3><p>{p.diapositivas} diapositivas</p><Accion icono="duplicar" disabled={ocupado} onclick={() => usarPlantilla(p)}>Añadir a mi biblioteca</Accion></article>{/each}</div>
    {/if}
  {:else if recurso}
    <div class="barra-editor">
      <div class="acciones-editor-izquierda"><Accion icono="volver" disabled={ocupado} onclick={salir}>Volver a {nombreSeccion.toLowerCase()}</Accion>{#if investigador&&recurso.estado==='borrador'}<Accion icono="guardar" disabled={ocupado} onclick={guardar}>Guardar borrador</Accion><Accion icono="publicar" class="primario" disabled={ocupado} onclick={prepararPublicacion}>Publicar</Accion>{/if}</div>
      <div class="pestanas-recurso" aria-label="Vistas del recurso">
        {#if investigador && recurso.contenido}
          {#if recurso.estado === 'borrador'}<Accion icono="editar" onclick={() => modo='editor'} aria-pressed={modo==='editor'}>Editar</Accion>{/if}
          <Accion icono={recurso.tipo==='encuesta'?'visible':'diapositivas'} onclick={() => {if(recurso.tipo==='diapositivas')presentar(recurso);else{modo='previa';respuestasPrevia={};}}} aria-pressed={modo==='previa'}>{recurso.tipo==='encuesta'?'Vista previa':'Presentar'}</Accion>
        {/if}
        {#if recurso.id}<Accion icono="analitica" onclick={() => modo='metricas'} aria-pressed={modo==='metricas'}>Métricas</Accion>{/if}
        {#if investigador&&recurso.estado==='cerrado'}<Accion icono="publicar" disabled={ocupado} onclick={prepararPublicacion}>Volver a publicar</Accion>{/if}
      </div>
    </div>
    {#if modo === 'editor'}
      <div class="bloque identidad-recurso"><h2><Icono nombre={recurso.tipo} medida={23} />Información de {recurso.tipo==='encuesta'?'la encuesta':'la presentación'}</h2>
        <label>Título del recurso<input maxlength="250" bind:value={recurso.titulo} /></label><label>Descripción<textarea maxlength="5000" bind:value={recurso.descripcion}></textarea></label>
      </div>
      {#if recurso.tipo === 'encuesta'}<EditorEncuesta bind:recurso />{:else}<EditorDiapositivas bind:recurso />{/if}
    {:else if modo === 'previa'}
      {#if recurso.tipo === 'encuesta'}<FormularioEncuesta {recurso} previa bind:respuestas={respuestasPrevia} />{:else}<VisorDiapositivas contenido={recurso.contenido} titulo={recurso.titulo} />{/if}
    {:else if modo === 'metricas'}{#key recurso.id}<MetricasRecursos {recurso} />{/key}{/if}
  {/if}
 {#if encuestaAmpliada&&ampliarAbierto}<GestionDestinatarios recurso={encuestaAmpliada} bind:abierto={ampliarAbierto} alCambiar={cargar} />{/if}
 {#if investigador&&destinoPublicacion&&['borrador','cerrado'].includes(destinoPublicacion.estado)}<Dialogo bind:abierto={dialogoPublicacion} titulo={`${destinoPublicacion.estado==='borrador'?'Publicar':'Volver a publicar'} ${destinoPublicacion.tipo==='encuesta'?'encuesta':'presentación'}`} tipo="confirmar" ancho="42rem">
  <p><strong>{destinoPublicacion.titulo}</strong></p><p>Selecciona quién recibirá este recurso en sus notificaciones.</p>
  <SelectorDestinatarios bind:audiencia bind:seleccion {cursos} docentes={destinatariosDocentes} />
  {#if destinoPublicacion.estado!=='borrador'}<p>Este envío tendrá métricas independientes. Se conservarán los datos de los envíos anteriores.</p>{/if}
  <div class="acciones"><Accion icono="volver" onclick={cerrarPublicacion}>{publicacionLista?'Volver a la biblioteca':'Seguir editando'}</Accion><Accion icono="publicar" class="primario" disabled={ocupado||!seleccion.length} onclick={()=>{dialogoPublicacion=false;publicar(destinoPublicacion,!!publicacionLista);}}>{audiencia==='docentes'?'Publicar para docentes seleccionados':audiencia==='individuales'?'Publicar para estudiantes seleccionados':'Publicar en cursos seleccionados'}</Accion></div>
 </Dialogo>{/if}
</section>
<Dialogo bind:abierto={dialogoErrorImportacion} titulo="No se pudo importar la presentación" tipo="comunicar">
  <p>{errorImportacion}</p>
  <p>Puedes seleccionar otra vez el archivo HTML o JSON. Si la conexión se interrumpió durante el guardado, revisa primero tu biblioteca.</p>
</Dialogo>
{#if enlacesAbiertos&&recursoEnlaces}<EnlacesPublicacion recurso={recursoEnlaces} bind:abierto={enlacesAbiertos} />{/if}

<div bind:this={pantallaPresentacion} tabindex="-1" role="region" aria-label="Presentación a pantalla completa" class="pantalla-presentacion" class:oculta={!presentacionActiva}>
 {#if presentacionActiva}
  {#if avisoPantalla}<p class="aviso-pantalla" role="status">{avisoPantalla}</p>{/if}
  {#if errorPresentacion}<p class="estado-presentacion" role="alert">{errorPresentacion}</p>{:else if !contenidoPresentado}<div class="estado-presentacion"><CargadorCubo mensaje="Preparando presentación…" /></div>{/if}
 {/if}
 {#if tipo==='diapositivas'||recurso?.tipo==='diapositivas'}<VisorDiapositivas contenido={contenidoPresentado??contenidoEspera} titulo={tituloPresentado} pantallaCompleta alCerrarPresentacion={()=>cerrarPresentacion()} />{/if}
</div>
<style>
 .pantalla-presentacion{position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;background:var(--surface-canvas);color:var(--ink-primary);width:100%;height:100dvh;overflow:hidden}
 .pantalla-presentacion.oculta{display:none}
 .estado-presentacion{position:absolute;inset:0;z-index:4;display:grid;place-items:center;background:var(--surface-canvas)}
 .aviso-pantalla{position:absolute;top:10px;left:10px;z-index:5;max-width:70%;background:var(--surface-paper);padding:8px;font-size:.8rem}
 @media(orientation:portrait) and (max-width:700px){.pantalla-presentacion :global(.pantalla-completa){position:absolute;left:50%;top:50%;flex:none;width:100dvh;height:100dvw;transform:translate(-50%,-50%) rotate(90deg)}}
</style>
