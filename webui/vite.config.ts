import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  // Rutas relativas: PyWebView abre dist/index.html como file://; con "/" los JS no cargan.
  base: "./",
  plugins: [svelte()],
  server: {
    host: "127.0.0.1",
    port: 5173
  }
});
