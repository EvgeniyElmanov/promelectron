import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

const proxyTarget = process.env.VITE_PROXY_API || 'http://127.0.0.1:8000'
const wsTarget = proxyTarget.replace(/^http/, 'ws')

export default defineConfig({
  cacheDir: '/tmp/vite-cache-evgeniy',
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    host: '0.0.0.0',
    allowedHosts: ['frontend', 'frontend-dev', 'localhost', '127.0.0.1'],
    watch: {
      ignored: ['**/playwright-report/**', '**/test-results/**'],
    },
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
      '/ws': {
        target: wsTarget,
        changeOrigin: true,
        ws: true,
      },
      '/uploads': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
})
