import { defineConfig } from 'vite'
import { resolve } from 'node:path'

export default defineConfig({
  base: './',   // links relativos: publicável na raiz OU em subpasta (preview)
  build: {
    target: 'es2020',
    rollupOptions: {
      input: {
        gateway: resolve(__dirname, 'index.html'),
        ventas: resolve(__dirname, 'ventas/index.html'),
        institucional: resolve(__dirname, 'institucional/index.html'),
      },
    },
  },
})
