import { execSync } from 'node:child_process'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

function getGitVersion(): string {
  if (process.env.APP_VERSION) return process.env.APP_VERSION
  try {
    return execSync('git describe --tags --always --dirty').toString().trim().replace(/^v/, '')
  } catch {
    return '0.0.0-unknown'
  }
}

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  define: {
    __APP_VERSION__: JSON.stringify(getGitVersion()),
    __REPO_URL__: JSON.stringify(
      process.env.REPO_URL !== undefined
        ? process.env.REPO_URL
        : 'https://github.com/Xitee1/package-tracker',
    ),
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': 'http://backend:8000',
    },
  },
})
