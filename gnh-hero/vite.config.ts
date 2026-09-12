import { defineConfig } from 'vite'
import { resolve } from 'node:path'

export default defineConfig({
  base: './',   // links relativos: publicável na raiz OU em subpasta (preview)
  build: {
    target: 'es2020',
    rollupOptions: {
      input: {
        // /institucional/ é reaproveitado de gnh-redesign.html (self-contained),
        // colocado pós-build — não passa pelo Vite.
        gateway: resolve(__dirname, 'index.html'),
        ventas: resolve(__dirname, 'ventas/index.html'),
      },
    },
  },
})
