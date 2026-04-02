import { mount } from "svelte";
import App from "./App.svelte";

const target = document.getElementById("app");
if (!target) {
  throw new Error("No se encontró #app");
}

const app = mount(App, { target });

export default app;
