/**
 * Configuración del compilador de Svelte.
 *
 * Solo compilador. Ninguna decisión de producto vive aquí.
 *
 */
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  /**
   * Bajo pruebas se salta el preprocesado del CSS. Y no es un capricho:
   *
   * `vitePreprocess()` pasa cada `<style>` por `preprocessCSS` de Vite, y ese
   * puente se rompe dentro de Vitest —«Cannot create proxy with a non-object
   * as target or handler»—, de modo que importar CUALQUIER componente con
   * estilos fallaba antes de compilar. Es el mismo defecto de entorno que el
   * 2026-08-10 obligó a cargar las rutas con `import()` diferido.
   *
   * Saltarlo no cambia nada de lo que estas pruebas miran —miden el DOM y el
   * comportamiento, no la hoja de estilos— y NO TOCA EL EMPAQUETADO: fuera de
   * Vitest el preprocesador sigue puesto tal cual. El contraste se comprueba
   * aparte, leyendo el CSS del árbol.
   */
  preprocess: vitePreprocess({ style: !process.env.VITEST }),

  compilerOptions: {
    // Los avisos de accesibilidad del compilador NO se silencian.
    // DD-05 compromete WCAG 2.2 AA y estos avisos son la primera red.
    runes: true
  }
};
