/**
 * La única función que hace peticiones.
 *
 * Centraliza cabeceras, credenciales, tiempos de espera y traducción de
 * errores. Ningún otro archivo llama a la red directamente, para que la
 * degradación explícita de RP-17 esté en un solo sitio.
 *
 * «NINGÚN OTRO ARCHIVO» INCLUYE A `turno.js`
 * -------------------------------------------
 * Por eso aquí hay dos funciones y no una: `pedir()` para lo que devuelve un
 * documento, y `pedirPorPartes()` para la emisión de `DD-11`. Si `turno.js`
 * llamara a `fetch` por su cuenta para leer el flujo, la mitad del tráfico de
 * la aplicación —justo la mitad que importa— quedaría fuera del sitio donde
 * `RP-17` se cumple.
 *
 * LAS RUTAS SON UNA PROPUESTA, Y HAY QUE DECIRLO
 * -----------------------------------------------
 * `08-Contrato-del-Turno.md` §12 deja fuera del contrato «las rutas HTTP, los
 * verbos y los códigos de estado», porque son del adaptador entrante. Ese
 * adaptador todavía NO EXPONE HTTP: `adaptadores/entrantes/http/turno.py` es
 * una clase con un método `manejar()`, sin aplicación ni rutas. Las de `RUTAS`
 * son, por tanto, lo que este cliente pide; cuando se escriba el servidor,
 * o se conforma a esta tabla o se cambia esta tabla. Están juntas y con nombre
 * para que ese ajuste sea un archivo y no una búsqueda.
 *
 * Contrato en OE3-Implementacion/08-Contrato-del-Turno.md
 */
import { FalloDeRed, clasificarEstado } from '../errores/degradacion.js';

/**
 * El prefijo. `vite.config.js` lo aproxima al backend en desarrollo para que
 * el navegador vea UN SOLO ORIGEN y no haya que abrir CORS — una configuración
 * de CORS puesta «para desarrollar» es de las que acaban en producción.
 */
export const BASE = '/api';

/**
 * Las rutas que este cliente pide. Ver la nota de cabecera.
 *
 * ⚠️ **`consentimiento` no está, y su ausencia es la corrección de C1.**
 * `sesion.js` la referenciaba (`RUTAS.consentimiento`) sin que existiera, así
 * que `pedir(undefined)` habría pedido `/apiundefined`; la pantalla lo
 * esquivaba escribiendo `'/consentimiento'` a mano. Esa ruta responde hoy
 * **410** —`rutas/sesion.py::consentimiento_retirado`— y el recorrido vigente
 * son las cinco entradas de `consentimiento` de abajo. No se deja un alias de
 * compatibilidad: un alias que responde 410 no es compatibilidad.
 */
export const RUTAS = Object.freeze({
  turno: '/turno',
  sesion: '/sesion',
  sesionGoogle: '/sesion/google',
  reautenticar: '/sesion/reautenticar',
  renovar: '/sesion/renovar',
  reiniciarSesion: '/sesion/reiniciar',
  conceptos: '/conceptos',
  graficadora: '/graficadora/curvas',
  historial: '/historial',

  // ── `EQ-013` · la biblioteca de fuentes · Fase 5 ────────────────────────
  //
  // Dos prefijos y ninguna ruta con archivo. El camino de una parte se compone
  // en `fuentes.js` con `encodeURIComponent`, de modo que un nombre raro no
  // puede salirse de la ruta — el mismo criterio que `textoDeVersion`.
  fuentesObras: '/fuentes/obras',
  fuentesFragmentos: '/fuentes/fragmentos',

  // ── onboarding y consentimiento versionado · `EQ-020` / `EQ-021` ────────
  onboardingEstado: '/onboarding/estado',
  onboardingPerfil: '/onboarding/perfil',
  versiones: '/consentimiento/versiones',
  // `§8` · el DOCUMENTO de una version, por codigo. Es una funcion y no una
  // cadena porque el codigo es parte del camino; se codifica al construirlo,
  // asi que un codigo raro no puede salirse de la ruta.
  textoDeVersion: (codigo) =>
    `/consentimiento/version/${encodeURIComponent(codigo)}/texto`,

  // `D1B` · LA ÚNICA ACCIÓN VISIBLE, Y LA ÚNICA ESCRITURA DE ACEPTACIÓN.
  //
  // ⚠️ Aquí estaban `consentimientoTitular: '/consentimiento/titular'` y
  // `asentimiento: '/consentimiento/asentimiento'`. Las dos responden **410**
  // desde `D1B`: permitían decisiones parciales, y para un menor llamarlas una
  // detrás de otra era la forma de dejar la mitad de su decisión escrita.
  //
  // No se conservan como entrada «por si acaso». Una ruta en esta tabla es una
  // invitación a llamarla, y `D0` §10.10 descarta exactamente esa solución.
  decisionConjunta: '/consentimiento/decision-conjunta',

  // Las revocaciones NO cambian: `EQ-022` les da su propia regla de versión y
  // `EQ-016` declara las dimensiones independientes.
  revocarTitular: '/consentimiento/titular/revocar',
  revocarAsentimiento: '/consentimiento/asentimiento/revocar',
  formatoRepresentante: '/representante/formato',
  evidencia: '/representante/evidencia',

  // ── consola del investigador · `EQ-023` / C2B ───────────────────────────
  //
  // PLURAL, y no es un descuido: `evidencia` (singular) es lo que hace el
  // titular con la suya —cargarla— y `evidencias` es la colección que ve quien
  // revisa. La distinción se lee en la dirección y viene del backend.
  //
  // El detalle y el archivo NO están aquí porque llevan un identificador
  // dentro: se componen en `api/evidencias.js` a partir de esta entrada, para
  // que no haya dos formas de escribir el mismo camino.
  evidencias: '/representante/evidencias',

  // ── derechos del titular · `RP-19` / `EQ-022` ───────────────────────────
  datosPersonales: '/datos-personales',
  exportarDatos: '/datos-personales/exportar',
  preferenciasNotificacion: '/preferencias-notificacion',
  configuracionSondeos: '/sondeos/configuracion',
  supresion: '/datos/supresion',
  retencion: '/datos/retencion'
});

/**
 * Cuánto se espera antes de dejar de esperar.
 *
 * No es un número de gusto. `RNF-EFI-01` presupone ≤300 ms para el filtro de
 * recuperación, y la cadena completa medida el 2026-08-10 ronda los 95 ms de
 * recuperación más la generación. Treinta segundos deja sitio de sobra a un
 * turno lento y sigue siendo poco para alguien mirando una pantalla quieta:
 * pasado ese punto el estudiante ya no está esperando, está preguntándose si
 * se rompió, y `RP-17` dice que eso se le cuenta en vez de dejarlo en blanco.
 */
export const ESPERA_MS = 30_000;

/** Lo que toda petición lleva, esté donde esté. */
function cabeceras(extra) {
  return { 'Content-Type': 'application/json', Accept: 'application/json', ...extra };
}

/**
 * Un `AbortController` que se aborta solo al agotarse el tiempo.
 *
 * El motivo se anota en el propio controlador porque el navegador da el mismo
 * `AbortError` a un tiempo agotado y a una cancelación deliberada, y al
 * estudiante hay que decirle cosas distintas. Ver `clasificar()`.
 */
function conTiempoLimite(ms, señalExterna) {
  const control = new AbortController();
  const reloj = setTimeout(() => {
    control.motivo = 'tiempo';
    control.abort();
  }, ms);
  señalExterna?.addEventListener('abort', () => control.abort(), { once: true });
  return {
    señal: control.signal,
    motivo: () => control.motivo,
    soltar: () => clearTimeout(reloj)
  };
}

/** Marca el `AbortError` con el motivo, para que `clasificar()` lo distinga. */
function conMotivo(error, motivo) {
  if (error?.name === 'AbortError' && motivo) error.motivo = motivo;
  return error;
}

/**
 * El JSON que acompaña a un rechazo, o `null`.
 *
 * Existe porque el backend de la Fase 3 dice en el cuerpo cosas que el código
 * de estado no distingue —`sin_version`, `reautenticacion_requerida`,
 * `reserva_pendiente`, `sin_concesion`— y sin ellas el cliente tendría que
 * adivinar. Adivinar aquí significa, en el peor caso, dejar aceptar un
 * documento que no existe.
 *
 * Nunca lanza: ya estamos construyendo un error, y sustituirlo por otro
 * perdería el motivo original —el mismo criterio que `_compensar()` sigue en
 * el servidor—. Un cuerpo ausente o ilegible es simplemente `null`.
 */
async function cuerpoDeError(respuesta) {
  try {
    const documento = await respuesta.json();
    return documento && typeof documento === 'object' ? documento : null;
  } catch {
    return null;
  }
}

/**
 * Una petición cuyo CUERPO ES BINARIO · `EQ-021`, evidencia del representante.
 *
 * `POST /api/representante/evidencia` recibe el PDF tal cual, con
 * `Content-Type: application/pdf`, y lo valida por contenido —`pdf.py`— antes
 * de reservar nada. **No se transforma a JSON ni a base64**: base64 crece un
 * tercio, obliga a tener el archivo entero dos veces en memoria y le quitaría
 * al servidor la única comprobación que de verdad demuestra que es un PDF.
 *
 * Vive aquí, y no en el módulo de consentimiento, por la razón de la cabecera:
 * si la carga llamara a `fetch` por su cuenta, el trozo de tráfico que lleva un
 * documento firmado sería justo el que queda fuera del sitio donde `RP-17`, el
 * tiempo límite y `credentials: 'include'` se cumplen.
 *
 * Devuelve el JSON de la respuesta. Un 2xx sin cuerpo legible se declara como
 * `turno-interrumpido`, igual que en `pedir()`: aquí un éxito a medias sería
 * peor que en ningún otro sitio.
 *
 * @param {string} ruta
 * @param {{contenido: Blob|ArrayBuffer|Uint8Array, tipo: string,
 *          señal?: AbortSignal, espera?: number}} opciones
 */
export async function pedirBinario(
  ruta,
  { contenido, tipo, metodo = 'POST', señal, espera = ESPERA_MS } = {}
) {
  const reloj = conTiempoLimite(espera, señal);
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, {
      method: metodo,
      // Sin `Content-Type: application/json`: el servidor lee esta cabecera
      // para decidir si acepta el archivo, y mandar la de JSON con bytes
      // dentro le haría rechazarlo con un motivo que no es el real.
      headers: { 'Content-Type': tipo, Accept: 'application/json' },
      credentials: 'include',
      body: contenido,
      signal: reloj.señal
    });
  } catch (e) {
    throw new FalloDeRed(
      conMotivo(e, reloj.motivo())?.motivo === 'tiempo' ? 'tiempo-agotado' : 'sin-red',
      { causa: e }
    );
  } finally {
    reloj.soltar();
  }

  if (!respuesta.ok) {
    throw new FalloDeRed(clasificarEstado(respuesta.status), {
      estado: respuesta.status,
      cuerpo: await cuerpoDeError(respuesta)
    });
  }
  try {
    return await respuesta.json();
  } catch (e) {
    throw new FalloDeRed('turno-interrumpido', { estado: respuesta.status, causa: e });
  }
}

/**
 * Una petición cuya RESPUESTA es binaria · `EQ-021`, el PDF del representante.
 *
 * La simétrica de `pedirBinario()`: aquélla manda bytes, ésta los recibe.
 * Devuelve un `Blob` y **nunca** una dirección: quien la llama construye su
 * `URL.createObjectURL()` y se encarga de revocarla, que es la única forma de
 * que el documento no sobreviva a la pantalla que lo enseña.
 *
 * Vive aquí y no en `api/evidencias.js` por la razón de la cabecera de este
 * archivo: si el visor llamara a `fetch` por su cuenta, el trozo de tráfico que
 * lleva una autorización firmada por un representante legal sería justo el que
 * queda fuera del sitio donde `RP-17`, el tiempo límite y `credentials:
 * 'include'` se cumplen.
 *
 * TRES COMPROBACIONES QUE NO SON PARANOIA
 * ----------------------------------------
 * 1. **el código de estado** — un 403 o un 503 se convierten en `FalloDeRed`
 *    con su clase, igual que en `pedir()`. Nunca en un documento vacío;
 * 2. **el tipo declarado** — si no es `application/pdf`, se rechaza. El
 *    servidor de desarrollo devuelve `indice.html` para cualquier camino que no
 *    reconozca, así que un error de configuración del proxy llegaría aquí como
 *    un «PDF» de 3 KB que el visor pintaría en blanco;
 * 3. **el tamaño** — cero bytes no es un documento. `EQ-024` prohíbe el éxito
 *    parcial, y en esta pantalla un éxito parcial significa habilitar los
 *    botones de aprobar y rechazar sobre algo que nadie llegó a ver.
 *
 * @param {string} ruta
 * @param {{tipo?: string, señal?: AbortSignal, espera?: number}} opciones
 * @returns {Promise<Blob>}
 */
export async function pedirArchivo(
  ruta,
  { tipo = 'application/pdf', metodo = 'GET', cuerpo, señal, espera = ESPERA_MS } = {}
) {
  const reloj = conTiempoLimite(espera, señal);
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, {
      method: metodo,
      headers: cuerpo === undefined
        ? { Accept: tipo }
        : { Accept: tipo, 'Content-Type': 'application/json' },
      credentials: 'include',
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
      signal: reloj.señal
    });
  } catch (e) {
    throw new FalloDeRed(
      conMotivo(e, reloj.motivo())?.motivo === 'tiempo' ? 'tiempo-agotado' : 'sin-red',
      { causa: e }
    );
  } finally {
    reloj.soltar();
  }

  if (!respuesta.ok) {
    throw new FalloDeRed(clasificarEstado(respuesta.status), {
      estado: respuesta.status,
      cuerpo: await cuerpoDeError(respuesta)
    });
  }

  const declarado = respuesta.headers?.get?.('content-type') ?? '';
  if (!declarado.toLowerCase().startsWith(tipo)) {
    throw new FalloDeRed('turno-interrumpido', { estado: respuesta.status });
  }

  const documento = await respuesta.blob();
  if (!documento || documento.size === 0) {
    throw new FalloDeRed('turno-interrumpido', { estado: respuesta.status });
  }
  return documento;
}

/**
 * Una petición que devuelve un documento.
 *
 * Nunca deja salir un error crudo: todo sale como `FalloDeRed` con su clase,
 * que es lo que permite que la degradación se decida en un solo sitio.
 *
 * @param {string} ruta   una de `RUTAS`, o cualquier camino bajo `BASE`
 * @param {{metodo?: string, cuerpo?: unknown, señal?: AbortSignal,
 *          espera?: number}} opciones
 */
export async function pedir(ruta, { metodo = 'GET', cuerpo, señal, espera = ESPERA_MS } = {}) {
  const reloj = conTiempoLimite(espera, señal);
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, {
      method: metodo,
      headers: cabeceras(),
      // Cookie de sesión. `RP-02` obliga a asignarla y conservarla, y el
      // navegador no la manda sola en peticiones que el código origina.
      credentials: 'include',
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
      signal: reloj.señal
    });
  } catch (e) {
    throw new FalloDeRed(
      conMotivo(e, reloj.motivo())?.motivo === 'tiempo' ? 'tiempo-agotado' : 'sin-red',
      { causa: e }
    );
  } finally {
    reloj.soltar();
  }

  if (!respuesta.ok) {
    throw new FalloDeRed(clasificarEstado(respuesta.status), {
      estado: respuesta.status,
      cuerpo: await cuerpoDeError(respuesta)
    });
  }
  if (respuesta.status === 204) return null;

  try {
    return await respuesta.json();
  } catch (e) {
    // Un 200 con cuerpo ilegible es un servidor que se rompió a medio
    // responder, no una respuesta vacía. Se declara en vez de devolver null.
    throw new FalloDeRed('turno-interrumpido', { estado: respuesta.status, causa: e });
  }
}

/**
 * Una petición cuya respuesta llega POR PARTES · `DD-11`.
 *
 * Llama a `alParte(objeto)` con cada documento JSON que va llegando y devuelve
 * el último. Acepta las dos formas sin que quien llama tenga que saber cuál
 * vino, y esto es deliberado: §12 del contrato declara que el mecanismo de
 * emisión por partes «es una decisión posterior», así que el cliente no puede
 * depender de que se haya tomado.
 *
 *   · línea a línea (`application/x-ndjson`, `text/event-stream`) — un objeto
 *     por línea, saltándose el prefijo `data:` cuando lo trae;
 *   · un solo documento (`application/json`) — se entrega entero como una
 *     única parte.
 *
 * El caso del documento único NO es un apaño: es lo que el backend de hoy
 * puede dar. `AdaptadorTurno.manejar()` construye las fases y el cuerpo y los
 * devuelve juntos, y su propio docstring dice que conectarlos a un flujo real
 * es del adaptador HTTP «que todavía no existe». La interfaz de arriba no
 * cambia el día que exista.
 */
export async function pedirPorPartes(ruta, { cuerpo, alParte, señal, espera = ESPERA_MS } = {}) {
  const reloj = conTiempoLimite(espera, señal);
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, {
      method: 'POST',
      headers: cabeceras({ Accept: 'application/x-ndjson, text/event-stream, application/json' }),
      credentials: 'include',
      body: JSON.stringify(cuerpo),
      signal: reloj.señal
    });
  } catch (e) {
    throw new FalloDeRed(
      conMotivo(e, reloj.motivo())?.motivo === 'tiempo' ? 'tiempo-agotado' : 'sin-red',
      { causa: e }
    );
  }

  try {
    if (!respuesta.ok) {
      throw new FalloDeRed(clasificarEstado(respuesta.status), {
        estado: respuesta.status,
        cuerpo: await cuerpoDeError(respuesta)
      });
    }

    const tipo = respuesta.headers?.get?.('content-type') ?? '';
    const porLineas = tipo.includes('ndjson') || tipo.includes('event-stream');

    if (!porLineas || !respuesta.body?.getReader) {
      const documento = await respuesta.json();
      alParte?.(documento);
      return documento;
    }

    return await leerLineas(respuesta.body, alParte);
  } catch (e) {
    if (e instanceof FalloDeRed) throw e;
    // Un flujo que se corta a mitad ES el turno interrumpido de §8.3, y por eso
    // no se confunde con «servidor caído»: aquí sí hubo fases, y la última
    // dice dónde se quedó. Es la primera utilidad práctica de `DD-11`.
    throw new FalloDeRed(
      conMotivo(e, reloj.motivo())?.motivo === 'tiempo' ? 'tiempo-agotado' : 'turno-interrumpido',
      { causa: e }
    );
  } finally {
    reloj.soltar();
  }
}

/** Lee un flujo de líneas JSON y entrega cada una. Devuelve la última. */
async function leerLineas(cuerpo, alParte) {
  const lector = cuerpo.getReader();
  const decodificador = new TextDecoder();
  let pendiente = '';
  let ultima = null;

  const entregar = (linea) => {
    const limpia = linea.trim().replace(/^data:\s*/, '');
    if (!limpia || limpia === '[DONE]') return;
    let objeto;
    try {
      objeto = JSON.parse(limpia);
    } catch {
      // Una línea ilegible se descarta y el turno sigue. Cortar aquí perdería
      // las fases que ya llegaron, que son justo lo que hace específica a la
      // degradación si el resto falla.
      return;
    }
    ultima = objeto;
    alParte?.(objeto);
  };

  for (;;) {
    const { done, value } = await lector.read();
    if (done) break;
    pendiente += decodificador.decode(value, { stream: true });
    const lineas = pendiente.split('\n');
    pendiente = lineas.pop() ?? '';
    for (const l of lineas) entregar(l);
  }
  if (pendiente) entregar(pendiente);
  return ultima;
}
