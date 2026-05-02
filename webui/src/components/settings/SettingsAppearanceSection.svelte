<script lang="ts">
  import { t } from "../../lib/i18n";
  import { UI_THEME_IDS, type UiThemeId } from "../../lib/uiTheme";
  import SettingsThumbPreview from "./SettingsThumbPreview.svelte";

  export let uiTheme: UiThemeId;
  export let showThumbLabels: boolean;
  export let thumbFrameVisible: boolean;
  export let thumbCardStyle: "soft" | "flat" | "outlined";
  export let previewCellPx: number;
  export let thumbGapPx: number;
  export let thumbImageRadiusPx: number;
  export let thumbTileRadiusPx: number;
  export let themeNameLabel: (id: UiThemeId) => string;
</script>

<div class="settings-group">
  <h3 class="settings-group__title">{t("settings.sectionAppearance")}</h3>
  <label class="field-label" for="set-theme-midnight">{t("settings.themeTitle")}</label>
  <p class="settings-hint">{t("settings.themeHint")}</p>
  <div class="settings-preset-row" role="group" aria-label={t("settings.themeTitle")}>
    {#each UI_THEME_IDS as tid (tid)}
      <button
        type="button"
        id={tid === "midnight" ? "set-theme-midnight" : undefined}
        class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
        class:om-btn--primary={uiTheme === tid}
        on:click={() => (uiTheme = tid)}>{themeNameLabel(tid)}</button
      >
    {/each}
  </div>
  <div class="settings-preset-row">
    <label class="check"
      ><input type="checkbox" bind:checked={showThumbLabels} /> {t("settings.showThumbLabels")}</label
    >
  </div>
  <div class="settings-preset-row">
    <label class="check"
      ><input type="checkbox" bind:checked={thumbFrameVisible} /> {t("settings.showThumbFrame")}</label
    >
  </div>
  <div class="settings-preset-row">
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
      class:om-btn--primary={thumbCardStyle === "soft"}
      on:click={() => (thumbCardStyle = "soft")}
    >{t("settings.cardStyleSoft")}</button>
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
      class:om-btn--primary={thumbCardStyle === "flat"}
      on:click={() => (thumbCardStyle = "flat")}
    >{t("settings.cardStyleFlat")}</button>
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
      class:om-btn--primary={thumbCardStyle === "outlined"}
      on:click={() => (thumbCardStyle = "outlined")}
    >{t("settings.cardStyleOutlined")}</button>
  </div>
  <SettingsThumbPreview
    {previewCellPx}
    {thumbGapPx}
    {thumbImageRadiusPx}
    {thumbTileRadiusPx}
    {showThumbLabels}
    {thumbFrameVisible}
    {thumbCardStyle}
  />
</div>
