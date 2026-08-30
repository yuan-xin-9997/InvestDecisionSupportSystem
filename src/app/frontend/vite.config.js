import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发模式代理到后端；生产构建产物由 FastAPI 直接托管
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8620',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1500,
  },
})
