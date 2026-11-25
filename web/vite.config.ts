import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  base: '/capitol-lens/',
  plugins: [react()],
  server: {
    host: '127.0.0.1', port: 5173, strictPort: true,
    proxy: { '/capitol-lens/api': {
      target: 'http://127.0.0.1:8787', changeOrigin: true,
      // Local development only: the separate fixture verifies this test identity.
      // Neither Vite nor this cookie injection is included in production assets.
      configure(proxy) {
        proxy.on('proxyReq', (outgoing, incoming) => {
          outgoing.setHeader('Cookie', 'admin_token=local-preview-only');
          if (incoming.headers.origin === 'http://127.0.0.1:5173') outgoing.setHeader('Origin', 'http://127.0.0.1:8787');
        });
      },
    } },
  },
  build: { sourcemap: false },
});
