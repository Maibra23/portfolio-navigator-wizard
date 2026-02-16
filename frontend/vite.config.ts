import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(() => ({
  server: {
    host: "localhost",
    port: 8080,
    strictPort: true,
    // HMR settings optimized for OneDrive-synced folders
    hmr: {
      host: "localhost",
      port: 8080,
      overlay: true,
      timeout: 10000,
    },
    // Watch options to reduce unnecessary reloads and prevent EIO errors from OneDrive
    watch: {
      ignored: [
        "**/node_modules/**",
        "**/.git/**",
        "**/.OneDrive*/**",
        "**/~$*",
      ],
      usePolling: true, // More stable with cloud-synced folders like OneDrive
      interval: 1500, // Check every 1.5 seconds
      binaryInterval: 3000,
    },
    // Proxy API requests to FastAPI backend during development
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve("./src"),
    },
  },
}));
