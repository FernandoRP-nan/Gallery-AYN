<script lang="ts">
  import { t } from "../../lib/i18n";

  export let keyboardShortcuts: Record<string, string>;
  export let defaultShortcuts: Record<string, string>;
</script>

<div class="settings-group">
  <h3 class="settings-group__title">{t("settings.sectionShortcuts")}</h3>
  <p class="settings-hint">{t("settings.shortcutsHint")}</p>
  <label class="field-label" for="set-shortcut-toggle">{t("settings.shortcutToggle")}</label>
  <input id="set-shortcut-toggle" class="om-input" type="text" bind:value={keyboardShortcuts.toggleMode} />
  <label class="field-label" for="set-shortcut-delete">{t("settings.shortcutDelete")}</label>
  <input id="set-shortcut-delete" class="om-input" type="text" bind:value={keyboardShortcuts.deleteAction} />
  <label class="field-label" for="set-shortcut-zoom-prev">{t("settings.shortcutZoomPrev")}</label>
  <input id="set-shortcut-zoom-prev" class="om-input" type="text" bind:value={keyboardShortcuts.zoomPrev} />
  <label class="field-label" for="set-shortcut-zoom-next">{t("settings.shortcutZoomNext")}</label>
  <input id="set-shortcut-zoom-next" class="om-input" type="text" bind:value={keyboardShortcuts.zoomNext} />
  <label class="field-label" for="set-shortcut-escape">{t("settings.shortcutEscape")}</label>
  <input id="set-shortcut-escape" class="om-input" type="text" bind:value={keyboardShortcuts.escape} />
  <div class="settings-preset-row">
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
      on:click={() => (keyboardShortcuts = { ...defaultShortcuts })}
    >{t("settings.shortcutsReset")}</button>
  </div>
</div>
