import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiProxyTarget = process.env.KELEBEK_API_PROXY_TARGET ?? 'http://127.0.0.1:5000'

export default defineConfig({
  plugins: [react()],
  server: {
    // Geliştirme sunucusu yalnızca bu bilgisayarda dinler (çevrimdışı yerel çalışma kararı).
    host: '127.0.0.1',
    proxy: {
      '/api': apiProxyTarget,
    },
  },
})
