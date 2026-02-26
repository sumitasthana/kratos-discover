import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': '/src'
    }
  },
  server: {
    fs: {
      // Allow serving files from the outputs directory
      allow: ['..']
    }
  },
  publicDir: 'public'
})
