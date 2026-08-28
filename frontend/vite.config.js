import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  base: '/react-assets/',
  build: { outDir: '../app/react_dist', emptyOutDir: true }
})
