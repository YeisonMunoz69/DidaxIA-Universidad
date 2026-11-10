import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess({ style: !process.env.VITEST }),

  compilerOptions: {
    runes: true
  }
};
