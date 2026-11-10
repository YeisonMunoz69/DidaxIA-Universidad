import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { presentacionIntegrada } from './empaquetado/presentacion-integrada.js';

const ENTRADA = fileURLToPath(new URL('./indice.html', import.meta.url));

const MODO_PUBLICO = 'publico';

const MODO_PRUEBAS = 'test';

const PUERTO_APLICACION = 5173;
const PUERTO_PUBLICO = 5174;

export function esCaminoDeApi(url) {
  const camino = String(url ?? '/').split('?')[0];
  return camino === '/api' || camino.startsWith('/api/');
}

export const CUERPO_SIN_API = 'El API del tutor no se sirve en esta superficie.';

export function fronteraDeApi() {
  return function cerrarApi(peticion, respuesta, siguiente) {
    if (!esCaminoDeApi(peticion?.url)) return siguiente();
    respuesta.statusCode = 404;
    respuesta.setHeader('Content-Type', 'text/plain; charset=utf-8');
    respuesta.end(CUERPO_SIN_API);
    return undefined;
  };
}

export function fronteraPublica(activa) {
  return {
    name: 'frontera-publica',
    apply: 'serve',
    configureServer(servidor) {
      if (!activa) return;
      servidor.middlewares.use(fronteraDeApi());
    }
  };
}

export function proxyDeApi(esPublico) {
  if (esPublico) return undefined;
  return {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true
    }
  };
}

function entradaEnEspanol() {
  return {
    name: 'entrada-en-espanol',
    configureServer(servidor) {
      servidor.middlewares.use((peticion, _respuesta, siguiente) => {
        const camino = (peticion.url ?? '/').split('?')[0];
        const esArchivo = camino.includes('.');
        const interno = camino.startsWith('/@') || camino.startsWith('/node_modules');
        const alBackend = esCaminoDeApi(camino);
        if (!esArchivo && !interno && !alBackend) peticion.url = '/indice.html';
        else if (camino === '/index.html') peticion.url = '/indice.html';
        siguiente();
      });
    }
  };
}

const CLIENTE_GOOGLE = process.env.GOOGLE_CLIENT_ID ?? '';

const DOMINIO_INSTITUCIONAL = process.env.DOMINIO_INSTITUCIONAL ?? 'unimayor.edu.co';

const ORIGENES_DE_PRODUCCION = Object.freeze({
  publico: 'https://didaxia.pro',
  aplicacion: 'https://app.didaxia.pro'
});

const ORIGENES_LOCALES = Object.freeze({
  publico: `http://localhost:${PUERTO_PUBLICO}`,
  aplicacion: `http://localhost:${PUERTO_APLICACION}`
});

export function origenesPara(comando) {
  const respaldo = comando === 'serve' ? ORIGENES_LOCALES : ORIGENES_DE_PRODUCCION;
  return {
    publico: process.env.ORIGEN_PUBLICO || respaldo.publico,
    aplicacion: process.env.ORIGEN_APLICACION || respaldo.aplicacion
  };
}

const CORREO_PRIVACIDAD = process.env.CORREO_PRIVACIDAD ?? '';

export default defineConfig(({ command, mode }) => {
  const esPublico = mode === MODO_PUBLICO;

  const origenes = origenesPara(mode === MODO_PRUEBAS ? 'build' : command);

  return {
    plugins: [svelte(), fronteraPublica(esPublico), entradaEnEspanol(), presentacionIntegrada()],

    publicDir: 'publico',

    define: {
      'import.meta.env.VITE_GOOGLE_CLIENT_ID': JSON.stringify(CLIENTE_GOOGLE),
      'import.meta.env.VITE_DOMINIO_INSTITUCIONAL': JSON.stringify(DOMINIO_INSTITUCIONAL),
      'import.meta.env.VITE_ORIGEN_PUBLICO': JSON.stringify(origenes.publico),
      'import.meta.env.VITE_ORIGEN_APLICACION': JSON.stringify(origenes.aplicacion),
      'import.meta.env.VITE_CORREO_PRIVACIDAD': JSON.stringify(CORREO_PRIVACIDAD),
      'import.meta.env.VITE_SUPERFICIE': JSON.stringify(esPublico ? 'publica' : '')
    },


    build: {
      rollupOptions: { input: ENTRADA }
    },

    server: {
      port: esPublico ? PUERTO_PUBLICO : PUERTO_APLICACION,
      proxy: proxyDeApi(esPublico)
    }
  };
});
