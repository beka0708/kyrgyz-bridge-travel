import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

// Built files go to Django's static dir; django-vite reads the manifest to inject tags.
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  base: "/static/dist/",
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    strictPort: true,
    origin: "http://localhost:5173",
  },
  build: {
    outDir: "../backend/static/dist",
    emptyOutDir: true,
    manifest: "manifest.json",
    target: "es2022",
    // maplibre-gl is ~1 MB by itself; it is lazy-loaded only near the map.
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      input: {
        main: "src/entries/main.ts",
        "route-editor": "src/entries/route-editor.ts",
        "route-map": "src/entries/route-map.ts",
      },
    },
  },
});
