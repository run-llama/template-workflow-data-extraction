import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const base = env.LLAMA_DEPLOY_NEXTJS_BASE_PATH ?? '/';

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 3000,
      host: true,
      hmr: {
        port: 3000
      }
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
    base: base,
    envPrefix: ['VITE_'],
  }
})