import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000", // Your Django server
        changeOrigin: false,
        // rewrite: (path) => path.replace(/^\/api/, ''), //  Not needed if your Django URLs start with /api
      },
      // Proxy for the new verification API endpoints
      "/verify/": {
        target: "http://localhost:8000",
        changeOrigin: false,
        // rewrite: (path) => path.replace(/^\/verify/, ''),
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name].js`,
        chunkFileNames: `assets/[name].js`,
        assetFileNames: `assets/[name].[ext]`,
      },
    },
  },
});
