import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const proxyConfig = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/ws': {
    target: 'ws://127.0.0.1:8000',
    ws: true,
  },
};

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  // strictPort: a busy port 3000 must fail instead of moving to 3001 (the backend only accepts the
  // origins http://localhost:3000 and http://127.0.0.1:3000). No `host` key: listen on localhost only.
  server: {
    port: 3000,
    strictPort: true,
    proxy: proxyConfig,
  },
  preview: {
    port: 3000,
    strictPort: true,
    proxy: proxyConfig,
  },
});
