import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "0.0.0.0",
    port: 8080,
    // Improve HMR for large files
    hmr: {
      overlay: true,
    },
    // Watch options to reduce unnecessary reloads
    watch: {
      ignored: ['**/node_modules/**', '**/.git/**'],
    },
    // Proxy API requests to FastAPI backend during development
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  plugins: [
    react(),
    mode === 'development' &&
    componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve("./src"),
    },
  },
}));
