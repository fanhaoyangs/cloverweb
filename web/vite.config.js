import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import ueditorMiddleware from './src/middlewares/ueditor.js'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())

  return {
    plugins: [
      vue(),
      ueditorMiddleware()
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    server: {
      port: 3000,
      open: true,
      proxy: {
        '/api/ueditor': {
          target: 'http://localhost:3000',
          changeOrigin: true
        },
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true
        }
      }
    },
    define: {
      'import.meta.env.VITE_CLOUDBASE_ENV_ID': JSON.stringify(env.VITE_CLOUDBASE_ENV_ID)
    }
  }
})
