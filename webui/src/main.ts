import "./styles/design-tokens.css";
import "./styles/om-theme-overrides.css";
import { mount } from "svelte";
import App from "./App.svelte";
import { applyUiThemeToDocument, readCachedUiTheme } from "./lib/uiTheme";

applyUiThemeToDocument(readCachedUiTheme());

const target = document.getElementById("app");
if (!target) {
  throw new Error("No se encontró #app");
}

const app = mount(App, { target });

export default app;
