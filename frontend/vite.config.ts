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
  // Build optimizations for production
  build: {
    // Increase chunk size warning limit (optional)
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Manual chunk splitting for better caching and smaller initial load
        manualChunks: {
          // Vendor chunks - rarely change, cached long-term
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-ui": [
            "@radix-ui/react-dialog",
            "@radix-ui/react-tabs",
            "@radix-ui/react-tooltip",
            "@radix-ui/react-collapsible",
            "@radix-ui/react-select",
            "@radix-ui/react-slot",
            "@radix-ui/react-label",
            "@radix-ui/react-checkbox",
            "@radix-ui/react-radio-group",
            "@radix-ui/react-switch",
            "@radix-ui/react-slider",
            "@radix-ui/react-alert-dialog",
          ],
          "vendor-charts": ["recharts", "d3-scale", "d3-shape", "d3-path"],
          "vendor-motion": ["framer-motion"],
          "vendor-utils": ["clsx", "tailwind-merge", "class-variance-authority", "date-fns"],
        },
      },
    },
    // Enable source maps for production debugging (optional)
    sourcemap: false,
    // Minification settings
    minify: "esbuild" as const,
    target: "es2020",
  },
}));
