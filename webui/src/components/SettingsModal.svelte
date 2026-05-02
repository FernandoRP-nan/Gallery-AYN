<script lang="ts">
  import "./settings/panel.css";
  import { t } from "../lib/i18n";
  import { galleryGridCellPx } from "../lib/thumbScale";
  import type { UiThemeId } from "../lib/uiTheme";
  import SettingsAppearanceSection from "./settings/SettingsAppearanceSection.svelte";
  import SettingsPerformanceSection from "./settings/SettingsPerformanceSection.svelte";
  import SettingsShortcutsSection from "./settings/SettingsShortcutsSection.svelte";
  import SettingsThumbsSection from "./settings/SettingsThumbsSection.svelte";

  export let thumbsPerPage: number;
  export let settingsThumbPresetIdx: number;
  export let settingsThumbScaleDraft: number;
  export let thumbGapPx: number;
  export let thumbImageRadiusPx: number;
  export let thumbTileRadiusPx: number;
  export let uiTheme: UiThemeId;
  export let showThumbLabels: boolean;
  export let thumbFrameVisible: boolean;
  export let thumbCardStyle: "soft" | "flat" | "outlined";
  export let keyboardShortcuts: Record<string, string>;
  export let defaultShortcuts: Record<string, string>;

  export let themeNameLabel: (id: UiThemeId) => string;
  export let onCancel: () => void;
  export let onSave: () => void;

  $: previewCellPx = galleryGridCellPx(settingsThumbScaleDraft);
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<div class="sm-backdrop" role="presentation" on:click|self={onCancel}>
  <div
    class="modal modal--settings om-panel om-panel--lift sm-dialog"
    role="dialog"
    aria-modal="true"
    aria-labelledby="settings-title"
    tabindex="-1"
    on:click|stopPropagation={() => undefined}
  >
    <header class="modal__head">
      <strong id="settings-title">{t("settings.modalTitle")}</strong>
      <button
        type="button"
        class="om-btn om-btn--ghost om-btn--close"
        aria-label={t("common.closeModalAria")}
        title={t("common.close")}
        on:click={onCancel}>✕</button
      >
    </header>
    <section class="settings-body">
      <SettingsPerformanceSection bind:thumbsPerPage />
      <SettingsThumbsSection
        bind:settingsThumbPresetIdx
        bind:settingsThumbScaleDraft
        bind:thumbGapPx
        bind:thumbImageRadiusPx
        bind:thumbTileRadiusPx
      />
      <SettingsAppearanceSection
        bind:uiTheme
        bind:showThumbLabels
        bind:thumbFrameVisible
        bind:thumbCardStyle
        {previewCellPx}
        {thumbGapPx}
        {thumbImageRadiusPx}
        {thumbTileRadiusPx}
        {themeNameLabel}
      />
      <SettingsShortcutsSection bind:keyboardShortcuts {defaultShortcuts} />
    </section>
    <div class="settings-actions">
      <button type="button" class="om-btn om-btn--ghost" on:click={onCancel}>{t("common.cancel")}</button>
      <button type="button" class="om-btn om-btn--primary" on:click={onSave}>{t("common.save")}</button>
    </div>
  </div>
</div>
