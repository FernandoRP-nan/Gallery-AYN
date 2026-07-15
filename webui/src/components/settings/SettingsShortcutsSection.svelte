<script lang="ts">
  import { t } from "../../lib/i18n";

  export let keyboardShortcuts: Record<string, string>;
  export let defaultShortcuts: Record<string, string>;

  const fixedShortcuts = [
    { keys: "Enter", labelKey: "settings.shortcutOpen" },
    { keys: "← → ↑ ↓ / WASD", labelKey: "settings.shortcutGalleryNav" },
    { keys: "Espacio", labelKey: "settings.shortcutSpace" },
    { keys: "Ctrl + flechas", labelKey: "settings.shortcutCtrlRange" },
    { keys: "Ctrl + arrastre", labelKey: "settings.shortcutCtrlDrag" },
  ] as const;
</script>

<div class="settings-group">
  <p class="settings-lead">{t("settings.shortcutsLead")}</p>
  <p class="settings-hint">{t("settings.shortcutsHint")}</p>

  <h4 class="settings-subtitle">{t("settings.shortcutsFixedTitle")}</h4>
  <ul class="shortcuts-fixed-list">
    {#each fixedShortcuts as row}
      <li class="shortcuts-fixed-row">
        <kbd class="shortcuts-kbd">{row.keys}</kbd>
        <span>{t(row.labelKey)}</span>
      </li>
    {/each}
  </ul>
  <p class="settings-hint shortcuts-ctrl-hint">{t("settings.shortcutCtrlDragHint")}</p>

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

<style>
  .settings-subtitle {
    margin: 1rem 0 0.5rem;
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--om-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .shortcuts-fixed-list {
    list-style: none;
    margin: 0 0 0.5rem;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .shortcuts-fixed-row {
    display: flex;
    align-items: baseline;
    gap: 0.65rem;
    font-size: 0.82rem;
    color: var(--om-text-primary);
  }

  .shortcuts-kbd {
    flex: 0 0 auto;
    min-width: 6.5rem;
    font-family: ui-monospace, "Cascadia Code", "Source Code Pro", Menlo, monospace;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.2rem 0.45rem;
    border-radius: var(--om-radius-sm);
    border: 1px solid var(--om-border-default);
    background: var(--om-surface-2);
    color: var(--om-text-secondary);
    white-space: nowrap;
  }

  .shortcuts-ctrl-hint {
    margin-bottom: 0.75rem;
  }
</style>
