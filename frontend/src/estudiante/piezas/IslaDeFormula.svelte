<!--
Una fórmula que se edita ya renderizada. `PM-F2x` fase 6.

Envuelve `<math-field>` de MathLive —único lugar del árbol que importa
`'mathlive'`, porque el import registra el elemento personalizado una vez
por caché de módulos ESM; que cada isla lo reimportara sería reflexionar
sobre reintentos de registro sin necesidad—. `Redactor.svelte` nunca toca
la API de MathLive directamente: habla con esta pieza por `valor` y por los
eventos nativos del elemento.



-->
<script>
  import { MathfieldElement } from 'mathlive';

  MathfieldElement.fontsDirectory = '/tipografias-mathlive';

  let {
    /** El LaTeX SIN los delimitadores `$...$` — esos los pone quien
        serializa el campo completo, no esta pieza. */
    valor = $bindable(''),
    /** Se invoca con `'forward'` o `'backward'` cuando una flecha llega al
        borde de la fórmula y no tiene más adónde ir DENTRO de ella.
        @type {((direccion: 'forward'|'backward') => void) | undefined} */
    alSalir,
    /** Se invoca cuando se borra toda la fórmula y se presiona Retroceso. */
    alEliminar,
    /** Se invoca cuando se presiona Enter para enviar. */
    alEnviar,
    /** Un toque debe reabrir el teclado aunque MathLive conserve el foco. */
    alInteractuar,
    ...resto
  } = $props();

  /** @param {any} nodo */
  function isla(nodo) {
    nodo.menuItems = [];
    // El redactor ofrece un único teclado matemático propio en teléfonos.
    // MathLive sigue editando la fórmula, pero no abre otro panel encima.
    nodo.mathVirtualKeyboardPolicy = 'manual';
    if (typeof nodo.setOptions === 'function') {
      nodo.setOptions({
        virtualKeyboardMode: 'manual',
        menuItems: []
      });
    }

    $effect(() => {
      if (nodo.value !== valor) nodo.value = valor;
    });

    $effect(() => {
      const alEscribir = () => { valor = nodo.value; };
      nodo.addEventListener('input', alEscribir);
      return () => nodo.removeEventListener('input', alEscribir);
    });

    $effect(() => {
      const alTocar = () => alInteractuar?.();
      nodo.addEventListener('pointerdown', alTocar);
      return () => nodo.removeEventListener('pointerdown', alTocar);
    });

    $effect(() => {
      /** @param {CustomEvent<{direction: 'forward'|'backward'}>} evento */
      const alSalirDelCampo = (evento) => alSalir?.(evento.detail.direction);
      nodo.addEventListener('move-out', alSalirDelCampo);
      return () => nodo.removeEventListener('move-out', alSalirDelCampo);
    });

    $effect(() => {
      /** @param {KeyboardEvent} evento */
      const alTeclear = (evento) => {
        if (evento.isComposing || evento.keyCode === 229) return;
        if (evento.key === 'Enter' && !evento.shiftKey) {
          evento.preventDefault();
          if (globalThis.matchMedia?.('(pointer: coarse)').matches) alSalir?.('forward');
          else alEnviar?.();
          return;
        }

        if (evento.key === 'Backspace') {
          const val = (nodo.value ?? '').trim();
          if (val === '' || val === '\\placeholder{}' || val === '{}') {
            evento.preventDefault();
            alEliminar?.();
            return;
          }
        }

        if (evento.key === 'ArrowRight' && !evento.shiftKey) {
          try {
            const sel = nodo.selection;
            if (sel && sel.ranges && sel.ranges[0] && sel.ranges[0][0] === sel.ranges[0][1]) {
              const endOffset = nodo.offsetFromPosition?.(nodo.lastPosition) ?? 0;
              if (sel.ranges[0][0] >= endOffset) {
                evento.preventDefault();
                alSalir?.('forward');
                return;
              }
            }
          } catch {
            // fallback
          }
        }

        if (evento.key === 'ArrowLeft' && !evento.shiftKey) {
          try {
            const sel = nodo.selection;
            if (sel && sel.ranges && sel.ranges[0] && sel.ranges[0][0] === 0 && sel.ranges[0][1] === 0) {
              evento.preventDefault();
              alSalir?.('backward');
              return;
            }
          } catch {
            // fallback
          }
        }
      };

      nodo.addEventListener('keydown', alTeclear);
      return () => nodo.removeEventListener('keydown', alTeclear);
    });
  }
</script>

<math-field use:isla {...resto}></math-field>

<style>
  /*
    LOS TOKENS DEL PROYECTO, NO LOS DE FÁBRICA DE MATHLIVE.
    Caret visible y espacios de reemplazo destacados con precisión métrica nativa.
  */
  math-field {
    caret-color: var(--accent-main);
    --primary: var(--accent-main);
    --caret-color: var(--accent-main);
    --caret-width: 2px;
    --selection-color: var(--accent-main);
    --selection-background-color: var(--accent-surface);
    --placeholder-color: var(--accent-main);
    --placeholder-opacity: 0.9;
    --highlight-color: var(--accent-surface);
    --smart-fence-color: var(--accent-main);
    --text-font-family: var(--fuente-texto);
    display: inline-block;
    vertical-align: middle;
    min-inline-size: 1.5rem;
    padding: 1px 5px;
    border: 1.5px solid var(--accent-main);
    border-radius: var(--radius-xs);
    background: var(--accent-surface);
    transition: var(--transition-fast);
    color: var(--ink-primary);
    font-size: 1.05em;
  }

  math-field:focus,
  math-field:focus-within,
  math-field:focus-visible {
    outline: none;
    border-color: var(--accent-main);
    box-shadow: 0 0 0 2px var(--accent-glow);
  }

  math-field::part(virtual-keyboard-toggle),
  math-field::part(menu-toggle),
  math-field::part(toggle) {
    display: none !important;
  }

  math-field::part(placeholder) {
    opacity: 0.9;
  }
</style>
