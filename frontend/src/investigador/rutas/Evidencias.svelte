<!--
Autorizaciones de representantes · la consola del investigador · `EQ-023` / C2B.

Maestro y detalle. La ruta orquesta —qué se pide, en qué orden, qué se enseña— y
las piezas pintan. Ninguna pieza llama al servidor: si lo hicieran, dos de ellas
podrían pedir la misma evidencia a la vez y el orden de las respuestas decidiría
qué se ve.

EL ORDEN DE LAS DOS PETICIONES AL SELECCIONAR ES EL CONTRATO
--------------------------------------------------------------
Primero el **detalle**, después el **archivo**. Nunca a la vez.

Si el archivo no se puede recuperar —una reserva sin confirmar, el almacén
caído— la pantalla todavía tiene qué enseñar y qué explicar: los metadatos, el
estado, el motivo histórico si lo hay, y el aviso de por qué no se puede
decidir. En paralelo, un fallo del archivo llegaría antes que el detalle y
dejaría un panel vacío con un error encima, que no dice nada de la evidencia.

NO SE DECIDE SOBRE LO QUE NO SE HA VISTO
------------------------------------------
`DetalleDeEvidencia.svelte` cierra los botones hasta que hay `Blob`. Aquí se
sostiene la otra mitad: al cambiar de evidencia, `documento` vuelve a `null`
**antes** de pedir nada, así que no queda ni un instante en el que los botones
estén abiertos con el PDF de la evidencia anterior en pantalla.

⚠️ Y no se registra ningún «leído». Que los bytes llegaran no demuestra que
alguien los mirara; el sistema no finge lo contrario.

SÓLO LA GENERACIÓN VIGENTE ESCRIBE
------------------------------------
Elegir una evidencia dispara dos peticiones y elegir otra las deja vencidas.
Sin gobernar ese orden, seleccionar A y después B deja la pantalla diciendo B
mientras enseña el detalle o el PDF de A — y los diálogos resolverían B con el
documento de A a la vista. La red no promete orden y por eso no se le pide.

Cada arranque estrena **generación** —un contador— y guarda su
`AbortController`. La generación se comprueba **después de cada `await` y
también en el `catch` y en el `finally`**; la que ya no es la vigente no
escribe nada, ni siquiera para apagar un indicador de carga.

⚠️ **Cancelar no basta y por eso hay las dos cosas.** Una promesa ya resuelta
se entrega aunque su controlador se aborte un instante después, y un doble de
prueba puede ignorar la señal entera. El `AbortController` ahorra red; la
generación es la que decide qué se pinta.

Y no se resuelve bloqueando la navegación: quien revisa puede cambiar de
evidencia o de filtro cuando quiera. Lo que se descarta es el trabajo vencido,
no el gesto.

LA IDENTIDAD VIAJA CON EL DATO
-------------------------------
`detalleDe` y `documentoDe` dicen **de qué evidencia** es cada cosa que hay en
memoria. `Boolean(documento)` sólo dice que llegó un PDF, no de cuál es, y ésa
es exactamente la pregunta que decide si se puede aprobar. Los diálogos, además,
capturan el identificador **al abrirse** (`decidiendoSobre`) y `resolver()`
comprueba que los cuatro —capturado, seleccionado, el del detalle y el del
PDF— sean el mismo antes de escribir en el expediente de nadie.

EL DOBLE ENVÍO SE CIERRA EN DOS SITIOS
----------------------------------------
El botón se deshabilita mientras `resolviendo` está puesto, y `resolver()`
comprueba la misma bandera antes de hacer nada. Con lo primero solo, un doble
clic rapidísimo o un `Enter` mantenido pueden colar la segunda llamada antes de
que Svelte repinte; con lo segundo solo, el botón parecería activo. Las dos.

QUÉ NO SE GUARDA, EN NINGÚN SITIO
-----------------------------------
Ni en `localStorage`, ni en `sessionStorage`, ni en IndexedDB, ni en la
dirección. Al salir de esta pantalla no queda nada: la cola, el detalle y el
documento viven en el estado del componente y se van con él. La Object URL la
revoca `VisorDePdf.svelte` en su propio efecto.



-->
<script>
  import { toast } from '../../comun/estado/toasts.svelte.js';
  import CabeceraDeRuta from '../../docente/piezas/CabeceraDeRuta.svelte';
  import PantallaDesplazable from '../../docente/piezas/PantallaDesplazable.svelte';
  import ColaDeEvidencias from '../piezas/ColaDeEvidencias.svelte';
  import DetalleDeEvidencia from '../piezas/DetalleDeEvidencia.svelte';
  import DialogoDeAprobacion from '../piezas/DialogoDeAprobacion.svelte';
  import DialogoDeRechazo from '../piezas/DialogoDeRechazo.svelte';
  import EstadoVacio from '../../docente/piezas/EstadoVacio.svelte';
  import * as api from '../../nucleo/api/evidencias.js';
  import { describir } from '../../nucleo/errores/degradacion.js';
  import { untrack } from 'svelte';

  // ── la cola ────────────────────────────────────────────────────────────
  let filtro = $state(api.FILTRO_POR_DEFECTO);
  let evidencias = $state([]);
  let cursor = $state(null);
  let hayMas = $state(false);
  let cargandoCola = $state(false);
  let falloCola = $state(null);

  // ── la evidencia abierta ───────────────────────────────────────────────
  let seleccionada = $state(0);
  let detalle = $state(null);
  let documento = $state(null);
  /** De QUÉ evidencia es `detalle`. `0` si no hay ninguno. */
  let detalleDe = $state(0);
  /** De QUÉ evidencia es `documento`. Ver «la identidad viaja con el dato». */
  let documentoDe = $state(0);
  let cargandoDetalle = $state(false);
  let cargandoArchivo = $state(false);
  let falloDetalle = $state(null);
  let falloArchivo = $state(null);
  let recibo = $state(null);

  // ── la decisión ────────────────────────────────────────────────────────
  let aprobacionAbierta = $state(false);
  let rechazoAbierto = $state(false);
  let resolviendo = $state(false);
  /** El identificador que el diálogo capturó AL ABRIRSE, o `0`. */
  let decidiendoSobre = $state(0);

  // ── las generaciones y sus cancelaciones ───────────────────────────────
  //
  // Dos contadores independientes porque son dos carreras distintas: cambiar
  // de filtro no tiene por qué vencer un PDF que se está trayendo, y abrir
  // otra evidencia no tiene por qué vencer la página que iba a llegar.
  //
  // No son `$state` a propósito: nadie las pinta y nadie deriva de ellas, y
  // hacerlas reactivas metería sus lecturas —que ocurren dentro de las mismas
  // funciones que el efecto del filtro llama— en el grafo de dependencias que
  // ese efecto documenta y evita con `untrack`.
  let generacionCola = 0;
  let generacionSeleccion = 0;
  /** @type {AbortController|null} */
  let controlCola = null;
  /** @type {AbortController|null} */
  let controlSeleccion = null;

  /**
   * Si una respuesta de cola todavía manda.
   *
   * Se comprueban las dos cosas y ninguna sobra: la generación cubre «llegó
   * otra petición después» y el filtro cubre «esto se pidió para otra cola».
   */
  const colaVigente = (generacion, estado) =>
    generacion === generacionCola && estado === filtro;

  /** Si una respuesta de la evidencia abierta todavía manda. */
  const seleccionVigente = (generacion) => generacion === generacionSeleccion;

  /**
   * Sólo en pantallas angostas: si se está viendo la lista o el detalle.
   *
   * En escritorio no se usa —las dos columnas están a la vez— y por eso no hay
   * ningún `matchMedia` aquí: quién se ve lo decide el CSS con una consulta de
   * medios, y esta bandera sólo gobierna las clases. Un `matchMedia` en el
   * guion habría duplicado el punto de corte en dos idiomas.
   */
  let viendoDetalleEnMovil = $state(false);

  /**
   * Estrena generación de cola y cancela la petición que hubiera en vuelo.
   *
   * Es el único sitio que toca `generacionCola`, para que no exista ningún
   * camino que empiece una petición de cola sin vencer la anterior.
   */
  function nuevaPeticionDeCola() {
    controlCola?.abort();
    controlCola = new AbortController();
    return { generacion: ++generacionCola, señal: controlCola.signal };
  }

  /** La primera página del filtro vigente. Reinicia todo lo acumulado. */
  async function cargarCola() {
    const estado = filtro;
    const { generacion, señal } = nuevaPeticionDeCola();
    cargandoCola = true;
    falloCola = null;
    try {
      const pagina = await api.listar({ estado, señal });
      // Una primera página sólo sustituye la cola si el filtro y la generación
      // que la pidieron siguen vigentes: la de «pendientes» pedida hace un
      // segundo no puede reemplazar la de «aprobadas» que se está mirando.
      if (!colaVigente(generacion, estado)) return;
      evidencias = pagina.evidencias;
      cursor = pagina.cursorSiguiente;
      hayMas = pagina.hayMas;
    } catch (e) {
      if (!colaVigente(generacion, estado)) return;
      // `EQ-024` · un 403 o un 503 NO se convierten en lista vacía. Se limpia
      // lo cargado para no dejar en pantalla una cola vieja bajo un error que
      // dice otra cosa, y el fallo se pinta con su clase.
      evidencias = [];
      cursor = null;
      hayMas = false;
      falloCola = describir(e);
    } finally {
      // El `finally` de una petición vencida tampoco apaga el indicador: sería
      // decir que terminó de cargar la cola que sigue en camino.
      if (colaVigente(generacion, estado)) cargandoCola = false;
    }
  }

  /** La siguiente página, con el cursor **que devolvió el servidor**. */
  async function cargarMas() {
    if (!cursor || cargandoCola) return;
    const estado = filtro;
    const desde = cursor;
    const { generacion, señal } = nuevaPeticionDeCola();
    cargandoCola = true;
    try {
      const pagina = await api.listar({ estado, cursor: desde, señal });
      // Anexar exige que sigan vigentes las tres cosas que originaron la
      // petición. Con el filtro cambiado, esto añadiría rechazadas al final de
      // la cola de aprobadas; con el cursor movido, repetiría un tramo.
      if (!colaVigente(generacion, estado) || cursor !== desde) return;
      // Se concatena: paginar por cursor es «lo que sigue», no «otra página que
      // sustituye a ésta». Y no se deduplica a mano —el cursor por clave de
      // orden garantiza que no se repita ninguna, y un `Set` aquí escondería
      // el día que dejara de garantizarlo—.
      evidencias = [...evidencias, ...pagina.evidencias];
      cursor = pagina.cursorSiguiente;
      hayMas = pagina.hayMas;
    } catch (e) {
      if (!colaVigente(generacion, estado) || cursor !== desde) return;
      falloCola = describir(e);
    } finally {
      if (colaVigente(generacion, estado)) cargandoCola = false;
    }
  }

  /**
   * Empieza una selección nueva —o la cierra, con `0`.
   *
   * Cancela lo que hubiera en vuelo, vence su generación y deja en cero todo
   * lo que describe la evidencia abierta ANTES de pedir nada: sin esto quedaría
   * un instante con el PDF de la anterior en pantalla y los botones abiertos
   * sobre la nueva. Es el único sitio que escribe `seleccionada`, para que no
   * haya ningún camino que la cambie sin vencer lo pedido para la anterior.
   */
  function reiniciarSeleccion(id) {
    controlSeleccion?.abort();
    controlSeleccion = new AbortController();
    seleccionada = id;
    detalle = null;
    detalleDe = 0;
    documento = null;
    documentoDe = 0;
    falloDetalle = null;
    falloArchivo = null;
    cargandoDetalle = false;
    cargandoArchivo = false;
    recibo = null;
    // Los diálogos abiertos eran de la evidencia anterior: confirmarlos después
    // de este punto resolvería una cosa mientras se enseña otra.
    cerrarDialogos();
    return ++generacionSeleccion;
  }

  /** Abre una evidencia: detalle primero, archivo después. Ver la cabecera. */
  async function seleccionar(id) {
    const generacion = reiniciarSeleccion(id);
    const señal = controlSeleccion?.signal;
    viendoDetalleEnMovil = true;

    cargandoDetalle = true;
    try {
      const abierta = await api.detalle(id, { señal });
      // La comprobación va DESPUÉS del `await`: entre pedir y recibir es donde
      // cambia la selección, y antes no hay nada que comprobar.
      if (!seleccionVigente(generacion)) return;
      detalle = abierta;
      detalleDe = id;
    } catch (e) {
      if (!seleccionVigente(generacion)) return;
      falloDetalle = describir(e);
      return;
    } finally {
      if (seleccionVigente(generacion)) cargandoDetalle = false;
    }

    // Y sólo la generación vigente empieza trabajo nuevo: un detalle vencido no
    // tiene por qué mandar a pedir un PDF que nadie va a poder mirar.
    await cargarArchivo(id, generacion, señal);
  }

  /**
   * El PDF. Separado para poder reintentarlo sin repetir el detalle.
   *
   * Recibe la generación y la señal en vez de leerlas: si las leyera aquí, una
   * respuesta tardía las tomaría ya renovadas y volvería a darse por vigente,
   * que es justo lo que hay que impedir.
   */
  async function cargarArchivo(id, generacion, señal) {
    cargandoArchivo = true;
    falloArchivo = null;
    try {
      const bytes = await api.archivo(id, { señal });
      if (!seleccionVigente(generacion)) return;
      documento = bytes;
      // El documento queda atado a SU evidencia. Ver «la identidad viaja con
      // el dato»: que haya `Blob` no dice de cuál es, y ésa es la pregunta que
      // decide si se puede aprobar.
      documentoDe = id;
    } catch (e) {
      if (!seleccionVigente(generacion)) return;
      // Cubre los cuatro desenlaces del almacenamiento —no configurado, caído,
      // reserva sin confirmar y archivo ausente—. Los cuatro llegan como 503 con
      // el motivo que redactó el servidor, y ninguno habilita nada.
      documento = null;
      documentoDe = 0;
      falloArchivo = describir(e);
    } finally {
      if (seleccionVigente(generacion)) cargandoArchivo = false;
    }
  }

  /**
   * Reintenta sólo el archivo, sin repetir el detalle.
   *
   * Estrena generación —la anterior queda vencida— y no toca `detalle`: lo que
   * falló fue el documento. Sin detalle vigente no se pide nada, porque no
   * habría a qué atar el PDF que llegara.
   */
  function reintentarArchivo() {
    const id = seleccionada;
    if (!id || detalleDe !== id) return;
    controlSeleccion?.abort();
    controlSeleccion = new AbortController();
    void cargarArchivo(id, ++generacionSeleccion, controlSeleccion.signal);
  }

  /** Cierra los dos diálogos y suelta el identificador que capturaron. */
  function cerrarDialogos() {
    aprobacionAbierta = false;
    rechazoAbierto = false;
    decidiendoSobre = 0;
  }

  /**
   * Abre un diálogo capturando sobre qué evidencia se va a decidir.
   *
   * Capturar al abrir y no al confirmar es la diferencia entre resolver la que
   * se está mirando y resolver «la que esté seleccionada cuando se pulse», que
   * puede ser otra si algo cambió por debajo.
   */
  function abrirDecision(cual) {
    const id = idDecidible;
    if (!id) return;
    decidiendoSobre = id;
    if (cual === 'aprobar') aprobacionAbierta = true;
    else rechazoAbierto = true;
  }

  /**
   * Aprobar o rechazar. Una sola función para las dos, porque el después es
   * idéntico y duplicarlo dejaría dos formas de recargar la cola.
   *
   * Recibe el identificador CAPTURADO por el diálogo y no lee `seleccionada`:
   * esa variable puede haber cambiado entre abrir y confirmar, y con ella la
   * escritura caería sobre la autorización de otro menor.
   */
  async function resolver(id, accion, tipo) {
    // La otra mitad de la defensa contra el doble envío. Ver la cabecera.
    if (resolviendo) return;
    // Los cuatro tienen que coincidir —capturado, seleccionado, el del detalle
    // y el del PDF— o no se escribe nada. Cuando no coinciden es que la
    // pantalla ya no enseña lo que este diálogo prometía, así que se cierra y
    // se deja la evidencia vigente tal como está.
    if (!id || id !== idDecidible) {
      cerrarDialogos();
      return;
    }
    const generacion = generacionSeleccion;
    const señal = controlSeleccion?.signal;
    resolviendo = true;
    try {
      const respuesta = await accion(id);
      (tipo === 'aprobar' ? toast.exito : toast.error)(tipo === 'aprobar'
        ? 'Autorización aprobada por doble custodia.' : 'Autorización devuelta para corrección.');
      cerrarDialogos();
      // El recibo y el estado nuevo son de ESTA evidencia: pintarlos sobre otra
      // que se abriera mientras se escribía diría que se resolvió la que está
      // en pantalla. La escritura sí ocurrió, y la cola de abajo la refleja.
      if (seleccionVigente(generacion) && seleccionada === id) {
        recibo = respuesta;
        // Se vuelve a pedir el detalle en vez de componerlo con el recibo: el
        // servidor es quien sabe el estado resultante, y darlo por hecho aquí
        // sería inventar el desenlace de una escritura que puede haber tenido
        // otro. Si esto falla, el recibo sigue en pantalla: la decisión SÍ se
        // registró y decir lo contrario sería peor.
        try {
          const fresco = await api.detalle(id, { señal });
          if (seleccionVigente(generacion) && seleccionada === id) {
            detalle = fresco;
            detalleDe = id;
          }
        } catch {
          // Se conserva el recibo y no se toca `falloDetalle`: la escritura fue
          // bien y lo que falló es una lectura de cortesía.
        }
      }
      // Y la cola se recarga entera: con el filtro «pendiente» la evidencia
      // resuelta desaparece de ella, que es lo correcto — el detalle sigue
      // abierto y enseña su estado nuevo. Va fuera de la comprobación porque la
      // cola no es de ninguna evidencia en particular, y `cargarCola()` toma el
      // filtro vigente al llegar aquí.
      await cargarCola();
    } catch (e) {
      cerrarDialogos();
      if (!seleccionVigente(generacion) || seleccionada !== id) return;
      falloDetalle = describir(e);
    } finally {
      // `resolviendo` sí se apaga siempre: la guarda de arriba garantiza que
      // sólo hay una escritura en vuelo, así que este `finally` nunca puede ser
      // el de una petición vencida.
      resolviendo = false;
    }
  }

  /**
   * Cambiar de filtro recarga desde la primera página.
   *
   * `untrack(cargarCola)` y no `cargarCola()`: la función lee `filtro`,
   * `cargandoCola` y `evidencias` de forma síncrona antes de su primer `await`,
   * y esas lecturas volverían a este efecto dependiente de su propio estado —
   * con lo que escribir `cargandoCola = true` lo dispararía otra vez. Es el
   * mismo bucle que `ColaDeSupervision.svelte` documentó y arregló igual.
   */
  $effect(() => {
    void filtro;
    untrack(() => {
      // Cambiar de filtro cierra el detalle y vence todo lo que se pidió para
      // él —detalle, archivo y diálogos—: la evidencia abierta puede no
      // pertenecer al filtro nuevo, y dejarla abierta daría a entender que sí.
      reiniciarSeleccion(0);
      viendoDetalleEnMovil = false;
      cargarCola();
    });
  });

  /**
   * Al salir de la pantalla se cancela lo que siga en vuelo.
   *
   * Y se vencen las dos generaciones, que no es lo mismo: una promesa YA
   * resuelta se entrega igual aunque su controlador se aborte un instante
   * después. Abortar ahorra red; vencer la generación es lo que impide que una
   * respuesta tardía escriba sobre un componente que ya no está.
   *
   * No se guarda nada al salir —ni en `localStorage`, ni en `sessionStorage`,
   * ni en IndexedDB—: la cola, el detalle y el documento se van con el
   * componente.
   */
  $effect(() => () => {
    controlCola?.abort();
    controlSeleccion?.abort();
    generacionCola += 1;
    generacionSeleccion += 1;
  });

  /** El detalle, sólo si es el de la evidencia que está abierta ahora. */
  const detalleVigente = $derived(
    detalleDe !== 0 && detalleDe === seleccionada ? detalle : null
  );

  /**
   * El PDF, sólo si es el de la MISMA evidencia que el detalle.
   *
   * `DetalleDeEvidencia.svelte` abre los botones cuando hay `Blob`, y esa
   * condición sólo es honesta si el `Blob` que recibe es del expediente que
   * tiene delante. La correspondencia se comprueba aquí, donde se conoce.
   */
  const documentoVigente = $derived(
    documento !== null && documentoDe !== 0 && documentoDe === seleccionada && documentoDe === detalleDe
      ? documento
      : null
  );

  /** Sobre qué evidencia se puede decidir ahora mismo, o `0`. */
  const idDecidible = $derived(
    seleccionada !== 0 &&
    detalleVigente?.estado === 'pendiente' &&
    documentoVigente !== null &&
    !cargandoArchivo
      ? seleccionada
      : 0
  );
</script>

<PantallaDesplazable anchoMaximo="min(90rem, 100%)">
  <CabeceraDeRuta
    titulo="Autorizaciones de representantes"
    icono="evidencias-institucionales"
    insignia="Revisión de evidencia">
    {#snippet nota()}
      Cada autorización se revisa <strong>después de abrir el documento</strong>.
      Los botones de decisión permanecen cerrados mientras no se haya podido
      recuperar el archivo.
    {/snippet}
  </CabeceraDeRuta>

  <div class="maestro-detalle" class:viendo-detalle={viendoDetalleEnMovil}>
    <div class="columna-cola">
      <ColaDeEvidencias
        {evidencias}
        bind:filtro
        {seleccionada}
        cargando={cargandoCola}
        {hayMas}
        fallo={falloCola}
        alSeleccionar={seleccionar}
        alCargarMas={cargarMas}
        alReintentar={cargarCola} />
    </div>

    <div class="columna-detalle">
      {#if seleccionada}
        <!-- Se pasan las versiones VIGENTES y no `detalle`/`documento` a secas:
             es lo que impide que un PDF que llegó tarde se pinte —y abra los
             botones— sobre una evidencia distinta de la suya. -->
        <DetalleDeEvidencia
          detalle={detalleVigente}
          documento={documentoVigente}
          {cargandoDetalle}
          {cargandoArchivo}
          {falloDetalle}
          {falloArchivo}
          {resolviendo}
          {recibo}
          alVolver={() => { viendoDetalleEnMovil = false; }}
          alReintentarArchivo={reintentarArchivo}
          alAprobar={() => abrirDecision('aprobar')}
          alRechazar={() => abrirDecision('rechazar')} />
      {:else}
        <EstadoVacio
          icono="datos"
          texto="Elija una autorización de la lista para revisarla."
          tono="neutro" />
      {/if}
    </div>
  </div>
</PantallaDesplazable>

<!--
  `decidiendoSobre` y no `seleccionada`: el identificador es el que se capturó
  al abrir el diálogo, y `resolver()` sólo escribe si sigue coincidiendo con lo
  que hay en pantalla. Ver «la identidad viaja con el dato».
-->
<DialogoDeAprobacion
  bind:abierto={aprobacionAbierta}
  intento={detalleVigente?.intento ?? 0}
  enviando={resolviendo}
  alConfirmar={() => resolver(decidiendoSobre, (id) => api.aprobar(id), 'aprobar')}
  alCancelar={cerrarDialogos} />

<DialogoDeRechazo
  bind:abierto={rechazoAbierto}
  intento={detalleVigente?.intento ?? 0}
  enviando={resolviendo}
  alConfirmar={(motivo) => resolver(decidiendoSobre, (id) => api.rechazar(id, motivo), 'rechazar')}
  alCancelar={cerrarDialogos} />

<style>
  /*
    ESCRITORIO: dos columnas. MÓVIL: una, y se alterna.

    El punto de corte vive SÓLO aquí, en CSS. La bandera del guion
    (`viendoDetalleEnMovil`) no sabe de anchos: dice qué se está mirando, y
    estas reglas deciden si eso importa. Con un `matchMedia` en el guion habría
    dos definiciones del mismo punto de corte en dos idiomas, y la que se
    olvidara de actualizar produciría una pantalla en blanco.
  */
  .maestro-detalle {
    display: grid;
    grid-template-columns: minmax(20rem, 26rem) minmax(0, 1fr);
    gap: var(--espacio-lg);
    align-items: start;
    /* `min-inline-size: 0` en la rejilla y en las dos columnas: sin esto un
       PDF ancho o una huella larga estiran su columna y la página entera
       adquiere scroll horizontal. */
    min-inline-size: 0;
  }

  .columna-cola,
  .columna-detalle { min-inline-size: 0; }

  @media (max-width: 60rem) {
    .maestro-detalle { grid-template-columns: minmax(0, 1fr); }

    /* Una sola columna a la vez, a pantalla completa. El botón «Volver a la
       lista» del detalle es el camino de vuelta, y sólo se pinta aquí porque
       en escritorio no hay nada a lo que volver. */
    .maestro-detalle.viendo-detalle .columna-cola { display: none; }
    .maestro-detalle:not(.viendo-detalle) .columna-detalle { display: none; }
  }
</style>
