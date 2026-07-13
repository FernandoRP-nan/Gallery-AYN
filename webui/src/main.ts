import "./styles/app.css";
import "./styles/design-tokens.css";
import "./styles/om-theme-overrides.css";
import "./lib/chromeRemember";
import { mount } from "svelte";
import App from "./App.svelte";
import { applyAppearanceToDocument, defaultAppearance, readCachedAppearance } from "./lib/uiAppearance";

applyAppearanceToDocument({ ...defaultAppearance(), ...readCachedAppearance() });

const target = document.getElementById("app");
if (!target) {
  throw new Error("No se encontró #app");
}

const app = mount(App, { target });

export default app;
