<!--
El juego de iconos.

UNO SOLO Y DIBUJADO A MANO, NO UNA BIBLIOTECA. `package.json` exige
justificación escrita para cada dependencia y `DD-05` decidió HTML nativo antes
que bibliotecas de componentes: un juego de iconos son doce trazos SVG, y
traerse un paquete entero para eso sería pagar una dependencia por algo que
cabe en un archivo.

SON DECORATIVOS SALVO QUE SE DIGA LO CONTRARIO
-----------------------------------------------
`aria-hidden` por defecto, porque el icono acompaña a un texto que ya dice lo
mismo y anunciarlo dos veces es peor que no anunciarlo. Cuando un control NO
lleva texto visible —solo el icono—, el nombre accesible lo pone quien lo usa
con `aria-label` en el botón, no aquí: el botón es el control, el icono no.

⚠️ `13-Lenguaje-de-Diseno.md` pide trazo simple y aspecto dibujado, y prohíbe
la iconografía «extremadamente moderna». De ahí salen las tres reglas de este
archivo: trazo de 1.75, extremos y uniones redondeados, y ni un relleno.



-->
<script>
  let {
    /** La clave del trazo. Si no existe, no se pinta nada. */
    nombre,
    /** Tamaño en píxeles del lado. */
    medida = 18
  } = $props();

  /**
   * Cada icono es el contenido de su `<svg>`, sin el envoltorio.
   *
   * El lienzo es 24x24 para todos: mezclando lienzos, dos iconos del mismo
   * tamaño declarado se ven de tamaños distintos y no hay forma de cuadrarlo
   * después salvo a ojo.
   */
  const TRAZOS = {
    'mas-vertical': '<circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>',
    notificaciones: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M9 20h6M20 3l2 3M4 3 2 6"/>',
    recursos: '<rect x="3" y="4" width="7" height="7" rx="1.5"/><rect x="14" y="4" width="7" height="7" rx="1.5"/><path d="M3 15h7v6H3zM14 15h7v6h-7z"/><path d="M6.5 6v3M5 7.5h3M16 7.5h3"/>',
    encuesta: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2h6v2M10 9h6M10 14h6M10 18h4"/><path d="m7 9 .7.7L9 8M7 14h1M7 18h1"/>',
    diapositivas: '<rect x="3" y="3" width="18" height="12" rx="1.5"/><path d="M12 15v3m-5 3 5-3 5 3M3 7h18M6 10h4m-4 2h7"/><path d="m16 9 3 2-3 2z"/>',
    guardar: '<path d="M4 3h13l4 4v14H3V3zM7 3v6h10V3M7 21v-8h10v8M14 5v2"/>',
    deshacer: '<path d="m9 5-6 6 6 6M3 11h11a7 7 0 0 1 7 7"/>',
    rehacer: '<path d="m15 5 6 6-6 6m6-6H10a7 7 0 0 0-7 7"/>',
    exportar: '<path d="M14 3h7v7m0-7L10 14M8 3H3v18h18v-5"/>',
    enlace: '<path d="m10 14 4-4m-7 6-2 2a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m0 0 2-2a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" transform="translate(4 -1)"/>',
    compartir: '<circle cx="18" cy="4" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="20" r="3"/><path d="m9 10 6-4m-6 8 6 4"/>',
    publicar: '<path d="m3 9 14-5v14L3 13zM7 14l2 7h4l-2-6M21 7v8M3 9v4"/>',
    archivar: '<path d="M4 8h16v13H4zM3 3h18v5H3zM9 12h6"/>',
    pagina: '<path d="M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h5"/>',
    pregunta: '<path d="M8 8a4 4 0 1 1 7 2.6c-2 1.4-3 1.9-3 4.4M12 19h.01"/><path d="M4 3h16v18H4z"/>',
    imagen: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8" cy="9" r="1.5"/><path d="m4 18 5-5 3 3 4-6 4 8"/>',
    subir: '<path d="m6 10 6-6 6 6M12 4v16"/>',
    bajar: '<path d="m6 14 6 6 6-6M12 4v16"/>',
    importar: '<path d="M14 3h5v18H5v-5M13 3v5h6M3 10h9m-3-3 3 3-3 3"/>',
    'teclado-cerrar': '<rect x="3" y="3" width="18" height="11" rx="2"/><path d="M6 7h1m3 0h1m3 0h1m3 0h0M7 10h10m-9 8 4 3 4-3"/>',
    conversacion: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    nueva:        '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    buscar:       '<circle cx="11" cy="11" r="7"/><line x1="20" y1="20" x2="16.5" y2="16.5"/>',
    historial:    '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>',
    practica:     '<path d="M6.5 6.5v11"/><path d="M17.5 6.5v11"/><path d="M3.5 9v6"/><path d="M20.5 9v6"/><line x1="6.5" y1="12" x2="17.5" y2="12"/>',
    conceptos:    '<path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H19v14.5H5.5A1.5 1.5 0 0 0 4 20z"/><line x1="8" y1="8" x2="15" y2="8"/><line x1="8" y1="11.5" x2="13" y2="11.5"/>',
    biblioteca:   '<path d="M3.5 5.5A2.5 2.5 0 0 1 6 3h5v16H6a2.5 2.5 0 0 0-2.5 2z"/><path d="M20.5 5.5A2.5 2.5 0 0 0 18 3h-5v16h5a2.5 2.5 0 0 1 2.5 2z"/>',
    clase:        '<path d="M16 20v-1.5a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4V20"/><circle cx="9" cy="7" r="3.2"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="16" y1="11" x2="22" y2="11"/>',
    datos:        '<path d="M13.5 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.5z"/><polyline points="13.5 3 13.5 8.5 19 8.5"/><line x1="8.5" y1="13" x2="15.5" y2="13"/><line x1="8.5" y1="16.5" x2="13" y2="16.5"/>',
    descargar:    '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 17v4h16v-4"/>',
    reloj:        '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    ajustes:      '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .32 1.8l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.6 1.6 0 0 0-1.8-.32 1.6 1.6 0 0 0-1 1.47V21a2 2 0 0 1-4 0v-.1A1.6 1.6 0 0 0 9 19.4a1.6 1.6 0 0 0-1.8.32l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.6 1.6 0 0 0 4.7 15a1.6 1.6 0 0 0-1.47-1H3a2 2 0 0 1 0-4h.1A1.6 1.6 0 0 0 4.6 9a1.6 1.6 0 0 0-.32-1.8l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.6 1.6 0 0 0 9 4.7a1.6 1.6 0 0 0 1-1.47V3a2 2 0 0 1 4 0v.1a1.6 1.6 0 0 0 1 1.47 1.6 1.6 0 0 0 1.8-.32l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.6 1.6 0 0 0 19.4 9a1.6 1.6 0 0 0 1.47 1H21a2 2 0 0 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/>',
    menu:         '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
    // Distinto de `menu` a propósito: los dos pueden convivir en la misma
    // cabecera de teléfono —uno abre el carril, el otro las secciones— y un
    // mismo trazo para los dos sería confuso para quien ve, no solo para
    // quien no distingue el `aria-label`.
    mas:          '<circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/>',
    // Las dos columnas del marco. El trazo dice CUÁL se pliega: la línea va
    // del lado del panel que el botón gobierna, como en el mockup.
    'panel-izq':  '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/>',
    'panel-der':  '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="15" y1="3" x2="15" y2="21"/>',
    tema:         '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>',
    sol:          '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    cerrar:       '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    visible:      '<path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6S2 12 2 12z"/><circle cx="12" cy="12" r="2.5"/>',
    duplicar:     '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
    eliminar:     '<path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6"/>',
    pantalla:     '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>',
    ampliar:      '<path d="M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5"/><path d="m3 3 6 6m12-6-6 6M3 21l6-6m12 6-6-6"/>',
    reducir:      '<path d="M3 9h6V3M21 9h-6V3M9 21v-6H3M15 21v-6h6"/><path d="m3 3 6 6m12-6-6 6M3 21l6-6m12 6-6-6"/>',
    grafica:      '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
    // Ejes, proyecciones discontinuas y punto de intersección; adapta su
    // color al tema mediante currentColor, como el resto de la cabecera.
    graficadora: '<path d="M5 5v14h14"/><path d="m3.6 7 1.4-2 1.4 2M17 17.6l2 1.4-2 1.4"/><path d="M5 10h10M15 10v9" stroke-dasharray="2 2"/><path d="M13.5 10h3M15 8.5v3"/>',
    fuente:       '<polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/>',
    reiniciar:    '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    supervision:  '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5.5h13l3.5 6.5v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
    clases:       '<path d="M17 20v-1.6a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4V20"/><circle cx="9.5" cy="7" r="3.2"/><path d="M22 20v-1.6a4 4 0 0 0-3-3.87"/><path d="M16 3.6a4 4 0 0 1 0 7.75"/>',
    grupo:        '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20v-1a6 6 0 0 1 12 0v1"/><path d="M15 14.5a5 5 0 0 1 6 4.8V20"/>',
    estudiante:   '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    perfil:       '<circle cx="12" cy="8" r="3.5"/><path d="M5 21v-1.5a7 7 0 0 1 14 0V21"/><path d="M18.5 4.5l1 1 2-2"/>',
    analitica:    '<path d="M4 19V9"/><path d="M10 19V5"/><path d="M16 19v-7"/><path d="M22 19H2"/><path d="m4 7 6-4 6 6 6-5"/>',
    equipo:       '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20v-1a6 6 0 0 1 12 0v1"/><path d="M15 14.5a5 5 0 0 1 6 4.8V20"/>',
    evidencias:   '<path d="M6 2h9l4 4v16H6z"/><path d="M14 2v5h5"/><path d="m9 15 2 2 4-5"/>',
    solicitudes:  '<path d="M4 5h16v14H4z"/><path d="M8 9h8"/><path d="M8 13h5"/><circle cx="18.5" cy="18.5" r="3.5" fill="var(--surface-paper)"/><path d="M18.5 17v3M17 18.5h3"/>',
    correo:       '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',
    enviar:       '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    google:       '<path d="M12 2a10 10 0 1 0 9.5 13.2h-9.5v-3.5h5.8a6.5 6.5 0 1 1-1.8-5.7l2.5-2.5A9.9 9.9 0 0 0 12 2z"/>',
    escudo:       '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    candado:      '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    check:        '<polyline points="20 6 9 17 4 12"/>',
    copiar:       '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    chispa:       '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z"/>',
    descarga:     '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    basura:       '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    editar:       '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    lapiz:        '<path d="M4 20l3.2-8.4L16.8 2a1.8 1.8 0 0 1 2.5 0l2.7 2.7a1.8 1.8 0 0 1 0 2.5l-9.6 9.6z"/><line x1="7.2" y1="11.6" x2="12.4" y2="16.8"/><line x1="16.2" y1="2.6" x2="21.4" y2="7.8"/><path d="m4 20 4.1-1.5-2.6-2.6z" fill="currentColor" stroke="none"/>',
    'flecha-izq': '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    'flecha-der': '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    volver:       '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    // `rutas.js` declara `icono: 'contexto'` para `/contexto` desde el
    // principio, pero esta clave nunca existió: sin `trazo`, el `{#if}` de
    // abajo no pinta nada y el hueco pasaba desapercibido porque el rótulo de
    // texto sigue ahí. Brújula: «contexto curricular» es orientar al sistema
    // sobre qué se está viendo, no un ajuste de cuenta ni un dato personal.
    contexto:     '<circle cx="12" cy="12" r="9"/><polygon points="14.5 9.5 12 12 9.5 14.5 12 12 14.5 9.5"/>',
    didaxia:      '<path d="M8 6L5 2"/><path d="M16 6L19 2"/><rect x="1" y="10" width="2" height="6" rx="1" fill="currentColor"/><rect x="21" y="10" width="2" height="6" rx="1" fill="currentColor"/><rect x="3" y="6" width="18" height="15" rx="5.5"/><path d="M12 11.5C10 9 6.5 9 6.5 11.5C6.5 14 10 14 12 11.5C14 9 17.5 9 17.5 11.5C17.5 14 14 14 12 11.5Z" stroke-width="1.5"/><path d="M9.5 16.8c1.5 1.8 3.5 1.8 5 0"/>',
    robot:        '<path d="M8 6L5 2"/><path d="M16 6L19 2"/><rect x="1" y="10" width="2" height="6" rx="1" fill="currentColor"/><rect x="21" y="10" width="2" height="6" rx="1" fill="currentColor"/><rect x="3" y="6" width="18" height="15" rx="5.5"/><path d="M12 11.5C10 9 6.5 9 6.5 11.5C6.5 14 10 14 12 11.5Z" stroke-width="1.5"/><path d="M9.5 16.8c1.5 1.8 3.5 1.8 5 0"/>'
  };

  const ICONOS_DE_SECCION = {
    'cerrar-sesion': {
      viewBox: '0 0 24 24', grosor: 2.5, relleno: 'none', trazoColor: 'currentColor',
      trazo: '<path d="M15 3.5H5.5A2.5 2.5 0 0 0 3 6v12a2.5 2.5 0 0 0 2.5 2.5H15"/><path d="M9 12h12"/><path d="m15.5 6.5 5.5 5.5-5.5 5.5"/>'
    },
    'auditoria-institucional': {
      viewBox: '0 0 200 200',
      grosor: 0,
      relleno: 'none',
      trazoColor: 'none',
      trazo: '<polyline points="45,135 80,75 120,102 155,55" fill="none" stroke="var(--brand-auditoria)" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/><circle cx="45" cy="135" r="12" fill="var(--brand-icono-fondo)" stroke="var(--brand-icono-tinta)" stroke-width="7"/><circle cx="80" cy="75" r="12" fill="var(--brand-icono-fondo)" stroke="var(--brand-icono-tinta)" stroke-width="7"/><circle cx="120" cy="102" r="12" fill="var(--brand-icono-fondo)" stroke="var(--brand-icono-tinta)" stroke-width="7"/><circle cx="155" cy="55" r="12" fill="var(--brand-icono-fondo)" stroke="var(--brand-icono-tinta)" stroke-width="7"/>'
    },
    'evidencias-institucionales': {
      viewBox: '0 0 24 24',
      grosor: 1.8,
      relleno: 'none',
      trazoColor: 'currentColor',
      // Un solo contorno y una firma legible también a 18 px. No depende de
      // variables de marca que cambien de contraste entre temas.
      trazo: '<rect x="4" y="4" width="14" height="17" rx="2"/><path d="M9 4.5V3h4v1.5M7.5 9h7M7.5 12h5"/><path d="m10 16 1.6 1.6L16 13.5"/>'
    },
    'perfil-institucional': {
      viewBox: '0 0 100 100',
      grosor: 0,
      relleno: 'none',
      trazoColor: 'none',
      trazo: '<circle cx="50" cy="50" r="40" fill="none" stroke="var(--brand-perfil)" stroke-width="6"/><circle cx="50" cy="40" r="13.5" fill="var(--brand-perfil)" stroke="none"/><path d="M 32 68 C 32 60, 40 54, 50 54 C 60 54, 68 60, 68 68 C 68 76, 32 76, 32 68 Z" fill="var(--brand-perfil)" stroke="none"/>'
    },
    'consumo-ia': {
      viewBox: '0 0 24 24',
      grosor: 0,
      relleno: 'var(--brand-consumo-ia)',
      trazoColor: 'none',
      trazo: '<path d="M23.748 4.482c-.254-.124-.364.113-.512.234-.051.039-.094.09-.137.136-.372.397-.806.657-1.373.626-.829-.046-1.537.214-2.163.848-.133-.782-.575-1.248-1.247-1.548-.352-.156-.708-.311-.955-.65-.172-.241-.219-.51-.305-.774-.055-.16-.11-.323-.293-.35-.2-.031-.278.136-.356.276-.313.572-.434 1.202-.422 1.84.027 1.436.633 2.58 1.838 3.393.137.093.172.187.129.323-.082.28-.18.552-.266.833-.055.179-.137.217-.329.14a5.526 5.526 0 0 1-1.736-1.18c-.857-.828-1.631-1.742-2.597-2.458a11.365 11.365 0 0 0-.689-.471c-.985-.957.13-1.743.388-1.836.27-.098.093-.432-.779-.428-.872.004-1.67.295-2.687.684a3.055 3.055 0 0 1-.465.137 9.597 9.597 0 0 0-2.883-.102c-1.885.21-3.39 1.102-4.497 2.623C.082 8.606-.231 10.684.152 12.85c.403 2.284 1.569 4.175 3.36 5.653 1.858 1.533 3.997 2.284 6.438 2.14 1.482-.085 3.133-.284 4.994-1.86.47.234.962.327 1.78.397.63.059 1.236-.03 1.705-.128.735-.156.684-.837.419-.961-2.155-1.004-1.682-.595-2.113-.926 1.096-1.296 2.746-2.642 3.392-7.003.05-.347.007-.565 0-.845-.004-.17.035-.237.23-.256a4.173 4.173 0 0 0 1.545-.475c1.396-.763 1.96-2.015 2.093-3.517.02-.23-.004-.467-.247-.588zM11.581 18c-2.089-1.642-3.102-2.183-3.52-2.16-.392.024-.321.471-.235.763.09.288.207.486.371.739.114.167.192.416-.113.603-.673.416-1.842-.14-1.897-.167-1.361-.802-2.5-1.86-3.301-3.307-.774-1.393-1.224-2.887-1.298-4.482-.02-.386.093-.522.477-.592a4.696 4.696 0 0 1 1.529-.039c2.132.312 3.946 1.265 5.468 2.774.868.86 1.525 1.887 2.202 2.891.72 1.066 1.494 2.082 2.48 2.914.348.292.625.514.891.677-.802.09-2.14.11-3.054-.614zm1-6.44a.306.306 0 0 1 .415-.287.302.302 0 0 1 .2.288.306.306 0 0 1-.31.307.303.303 0 0 1-.304-.308zm3.11 1.596c-.2.081-.399.151-.59.16a1.245 1.245 0 0 1-.798-.254c-.274-.23-.47-.358-.552-.758a1.73 1.73 0 0 1 .016-.588c.07-.327-.008-.537-.239-.727-.187-.156-.426-.199-.688-.199a.559.559 0 0 1-.254-.078.253.253 0 0 1-.114-.358c.028-.054.16-.186.192-.21.356-.202.767-.136 1.146.016.352.144.618.408 1.001.782.391.451.462.576.685.914.176.265.336.537.445.848.067.195-.019.354-.25.452z"/>'
    },
    'analitica-institucional': {
      viewBox: '0 0 48 48',
      grosor: 1.75,
      trazo: '<path d="M5.5 35.562h3.854V42.5H5.5zm8.287-7.708h3.854v14.645h-3.854zm8.286-7.708h3.854v22.353h-3.854zm8.287-7.708h3.854v30.061h-3.855zM38.646 5.5H42.5v37h-3.854z"/>'
    },
    'equipo-institucional': {
      viewBox: '0 0 512 512',
      grosor: 0,
      relleno: 'currentColor',
      trazoColor: 'none',
      trazo: '<path d="M496 128v16a8 8 0 0 1-8 8h-24v12c0 6.627-5.373 12-12 12H60c-6.627 0-12-5.373-12-12v-12H24a8 8 0 0 1-8-8v-16a8 8 0 0 1 4.941-7.392l232-88a8 8 0 0 1 6.118 0l232 88A8 8 0 0 1 496 128m-24 304H40c-13.255 0-24 10.745-24 24v16a8 8 0 0 0 8 8h464a8 8 0 0 0 8-8v-16c0-13.255-10.745-24-24-24M96 192v192H60c-6.627 0-12 5.373-12 12v20h416v-20c0-6.627-5.373-12-12-12h-36V192h-64v192h-64V192h-64v192h-64V192z"/>'
    },
    clases: {
      viewBox: '0 0 500 500',
      grosor: 16,
      trazo: '<path d="M165 170V98c0-10 8-18 18-18h242c10 0 18 8 18 18v164c0 8-6 14-13 14H188"/><line x1="184" y1="288" x2="449" y2="288"/><rect x="366" y="247" width="38" height="20" rx="4" stroke-width="15"/><line x1="230" y1="192" x2="290" y2="132" stroke-width="15"/><circle cx="120" cy="140" r="28"/><path d="M108 178c-20 6-36 26-40 60l-3 60c-1 16 25 22 29 4l4-70"/><line x1="93" y1="305" x2="93" y2="385"/><path d="M126 178c19 2 34 12 52 28l48 9c16 3 22-23 6-27l-50-12c-24-4-40 0-48 2"/><line x1="156" y1="232" x2="156" y2="310"/><path d="M116 182h8l4 12-8 6-8-6z" stroke-width="11"/><path d="M115 200h10l4 40-9 28-9-28z" stroke-width="11"/><circle cx="150" cy="355" r="27"/><path d="M103 455c0-47 29-63 47-63s47 16 47 63z"/><circle cx="256" cy="355" r="27"/><path d="M209 455c0-47 29-63 47-63s47 16 47 63z"/><circle cx="362" cy="355" r="27"/><path d="M315 455c0-47 29-63 47-63s47 16 47 63z"/>'
    },
    contexto: {
      viewBox: '0 0 500 500',
      grosor: 12,
      trazo: '<path d="M136 415 12 135 246 12l104 52"/><path d="M136 422 78 74l256-58 32 48"/><rect x="135" y="65" width="345" height="415" rx="52" stroke-width="16"/><rect x="156" y="86" width="303" height="373" rx="36" stroke-width="7"/><rect x="232" y="138" width="150" height="82" stroke-width="9"/><line x1="252" y1="160" x2="362" y2="160" stroke-width="6.5"/><line x1="252" y1="176" x2="362" y2="176" stroke-width="6.5"/><line x1="252" y1="192" x2="362" y2="192" stroke-width="6.5"/>'
    }
  };

  const definicion = $derived(
    ICONOS_DE_SECCION[nombre] ?? {
      viewBox: '0 0 24 24',
      grosor: 1.75,
      relleno: 'none',
      trazoColor: 'currentColor',
      trazo: TRAZOS[nombre] ?? null
    }
  );
</script>

{#if definicion.trazo}
  <svg class="icono" width={medida} height={medida} viewBox={definicion.viewBox}
       fill={definicion.relleno ?? 'none'} stroke={definicion.trazoColor ?? 'currentColor'} stroke-width={definicion.grosor}
       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    {@html definicion.trazo}
  </svg>
{/if}

<style>
  /* `flex-shrink: 0` para que el icono no se aplaste cuando el texto de al
     lado se recorta, que es exactamente lo que pasa en el carril estrecho. */
  .icono { flex-shrink: 0; display: block; }
</style>
