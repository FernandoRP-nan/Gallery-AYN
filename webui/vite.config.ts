import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig(() => ({
  // Rutas relativas: PyWebView abre dist/index.html como file://; con "/" los JS no cargan.
  base: "./",
  plugins: [svelte()],
  // Cambia en cada `npm run build`: sirve para comprobar que el .exe empaqueta la UI nueva.
  define: {
    __WEBUI_BUILD__: JSON.stringify(new Date().toISOString())
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/media": {
        target: "http://127.0.0.1:51234",
        changeOrigin: true
      },
      "/om-media": {
        target: "http://127.0.0.1:51234",
        changeOrigin: true
      },
      "/om-transcode": {
        target: "http://127.0.0.1:51234",
        changeOrigin: true
      },
      "/om-webm": {
        target: "http://127.0.0.1:51234",
        changeOrigin: true
      }
    }
  }
}));
