import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 3000,
    open: true,
    proxy: {
      // 后端 API（含 UEditor /api/ueditor/）统一转发 Django
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        // UEditorPlus 走 public/ 不进 rollup（A3 修正，勿加 ueditor-vendor）
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router'],
          'element-vendor': ['element-plus', '@element-plus/icons-vue'],
          'axios-vendor': ['axios']
        }
      }
    }
  }
})
