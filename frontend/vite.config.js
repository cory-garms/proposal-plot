import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // VITE_BASE_PATH is set by the GitHub Actions workflow to the repo subpath
  // e.g. /proposal-pilot for https://cory-garms.github.io/proposal-pilot/
  // Defaults to '/' for local development.
  base: process.env.VITE_BASE_PATH || '/',
})
