<script>
  import { preferencias } from '../../nucleo/preferencias/preferencias.svelte.js';
  import AlternarAnimaciones from './AlternarAnimaciones.svelte';
  import SelectorDePreferencia from './SelectorDePreferencia.svelte';

  const TEMAS = [
    { id: 'claro', nombre: 'Claro' },
    { id: 'oscuro', nombre: 'Oscuro' },
    { id: 'sistema', nombre: 'Automático' }
  ];
  const ESCALAS = [
    { id: 'normal', nombre: 'Normal', pista: '100%' },
    { id: 'comoda', nombre: 'Cómoda', pista: '110%' },
    { id: 'grande', nombre: 'Fórmulas grandes', pista: '125%' }
  ];
</script>

<div class="apariencia">
  <SelectorDePreferencia titulo="Tema de la pantalla" icono="sol" nombre="tema"
    opciones={TEMAS} valor={preferencias.tema}
    alElegir={(tema) => preferencias.elegirTema(tema)} />
  <SelectorDePreferencia titulo="Tamaño de lectura" icono="fuente" nombre="escala"
    opciones={ESCALAS} valor={preferencias.escalaTexto} variante="escala"
    alElegir={(escala) => preferencias.elegirEscala(escala)} />
  <AlternarAnimaciones />
</div>

<style>
  .apariencia { display:grid; gap:1.25rem; min-inline-size:0; }
</style>
