<!--
La tarjeta «inicia sesión para…», compartida.

⚠️ **ERA UNA INVITACIÓN Y HOY ES UNA PUERTA.** Aquí decía que `RP-02` abre
sesión anónima a quien llega y que `RL-04` no condiciona el tutor a
identificarse, «así que esta tarjeta nunca es una puerta». `EQ-020` retiró las
dos premisas: sólo se entra con cuenta institucional. La tarjeta sigue diciendo
qué función concreta se pide desde cada pantalla —el texto de cada sitio dice
cuál— pero ya no es opcional identificarse.

Sacada el 2026-08-22 de tres copias casi idénticas —`Conversacion.svelte`,
`MisDatos.svelte`, `UnirseAClase.svelte`— que habían empezado a divergir en
detalles de relleno sin que nadie lo decidiera (0.8rem de espacio aquí,
0.85rem allá). Una sola fuente para el trazo visual; el título, el icono y
el texto siguen siendo de quien la usa, porque eso sí es de cada pantalla.



-->
<script>
  import Icono from '../base/Icono.svelte';

  let {
    /** La clave del trazo, la misma que recibe `Icono`. */
    icono,
    titulo,
    /** El párrafo de la invitación, y —donde aplique, ver
        `Conversacion.svelte`— un botón de entrada además del de la barra
        lateral. Es contenido de quien nos usa: solo esta pantalla sabe si
        vale la pena repetir el botón aquí o basta con el del carril. */
    children
  } = $props();
</script>

<div class="bloqueo-autenticacion" role="region" aria-label="Inicio de sesión">
  <div class="tarjeta-bloqueo">
    <Icono nombre={icono} medida={36} />
    <h2>{titulo}</h2>
    {@render children?.()}
  </div>
</div>

<style>
  .bloqueo-autenticacion {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 2.5rem 1rem;
    margin: auto 0;
  }

  .tarjeta-bloqueo {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    max-inline-size: 460px;
    padding: 2.2rem 1.8rem;
    background: var(--surface-paper);
    border: 1px solid var(--trazo-suave);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-card);
    gap: 0.85rem;
  }

  .tarjeta-bloqueo h2 {
    font-size: var(--texto-lg);
    font-weight: 600;
    color: var(--ink-primary);
    margin: 0;
  }

  /* `:global()`: el párrafo llega por `children`, y ese marcado lo escribe
     quien nos usa —vive con SU hash de scope, no con el de aquí—. Sin esto
     la regla no alcanzaría ningún `<p>` de verdad. */
  .tarjeta-bloqueo :global(p) {
    font-size: var(--texto-sm);
    color: var(--ink-secondary);
    line-height: 1.5;
    margin: 0;
  }
</style>
