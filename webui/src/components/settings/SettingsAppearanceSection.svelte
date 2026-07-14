<script lang="ts">
  import { t } from "../../lib/i18n";
  import {
    THEME_COLOR_FIELDS,
    UI_FONT_IDS,
    UI_THEME_IDS,
    BG_SCOPE_IDS,
    duplicatePresetAsCustom,
    generateThemeId,
    isCustomThemeActive,
    PRESET_COLORS,
    PRESET_SWATCH,
    type BgScopeId,
    type CustomTheme,
    type ThemeColorField,
    type ThemeColors,
    type ThemeSelection,
    type UiFontId,
  } from "../../lib/uiAppearance";
  import type { UiThemeId } from "../../lib/uiTheme";
  import SettingsBgImagePicker from "./SettingsBgImagePicker.svelte";
  import SettingsThumbPreview from "./SettingsThumbPreview.svelte";

  export let themeSelection: ThemeSelection;
  export let customThemes: CustomTheme[];
  export let uiFont: UiFontId;
  export let uiBgImagePath: string;
  export let uiBgBlur: number;
  export let uiBgScope: BgScopeId;
  export let galleryFolder: string;
  export let recentFolders: string[] = [];
  export let pinnedFolders: string[] = [];
  export let pinnedFolderLabels: Record<string, string> = {};
  export let onBrowseBgFolder: (path: string) => void;
  export let showThumbLabels: boolean;
  export let thumbFrameVisible: boolean;
  export let thumbCardStyle: "soft" | "flat" | "outlined";
  export let previewCellPx: number;
  export let thumbGapPx: number;
  export let thumbImageRadiusPx: number;
  export let thumbTileRadiusPx: number;
  export let themeNameLabel: (id: UiThemeId) => string;

  const colorLabelKey = (field: ThemeColorField): string => `settings.themeColor.${field}`;

  function selectPreset(id: UiThemeId) {
    themeSelection = id;
  }

  function personalizePreset(id: UiThemeId) {
    const n = customThemes.length + 1;
    const theme = duplicatePresetAsCustom(`${t("settings.customThemeDefaultPrefix")} ${n}`, id);
    customThemes = [...customThemes, theme];
    themeSelection = `custom:${theme.id}`;
  }

  function addBlankCustomTheme() {
    const id = generateThemeId();
    const n = customThemes.length + 1;
    customThemes = [
      ...customThemes,
      { id, name: `${t("settings.customThemeDefaultPrefix")} ${n}`, colors: { ...PRESET_COLORS.midnight } },
    ];
    themeSelection = `custom:${id}`;
  }

  function removeCustomTheme(id: string) {
    customThemes = customThemes.filter((row) => row.id !== id);
    if (themeSelection === `custom:${id}`) {
      const fallback = customThemes[0];
      themeSelection = fallback ? (`custom:${fallback.id}` as ThemeSelection) : "midnight";
    }
  }

  function updateCustomName(id: string, name: string) {
    customThemes = customThemes.map((row) => (row.id === id ? { ...row, name } : row));
  }

  function updateCustomColor(id: string, field: ThemeColorField, value: string) {
    customThemes = customThemes.map((row) => {
      if (row.id !== id) return row;
      const colors: ThemeColors = { ...row.colors, [field]: value };
      return { ...row, colors };
    });
  }

  const fontSample = (id: UiFontId): string =>
    (
      {
        outfit: "settings.fontSampleOutfit",
        system: "settings.fontSampleSystem",
        inter: "settings.fontSampleInter",
        serif: "settings.fontSampleSerif",
        mono: "settings.fontSampleMono",
      } as const
    )[id];
</script>

<p class="settings-lead">{t("settings.appearanceLead")}</p>

<section class="settings-group" aria-labelledby="set-theme-examples">
  <h3 id="set-theme-examples" class="settings-group__title">{t("settings.themeExamplesTitle")}</h3>
  <p class="settings-hint">{t("settings.themeExamplesHint")}</p>
  <div class="settings-preset-row settings-theme-swatches" role="group" aria-label={t("settings.themeExamplesTitle")}>
    {#each UI_THEME_IDS as tid (tid)}
      <div class="settings-theme-example">
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--compact settings-theme-swatch"
          class:om-btn--primary={themeSelection === tid}
          title={themeNameLabel(tid)}
          on:click={() => selectPreset(tid)}
        >
          <span class="settings-theme-swatch__dot" style={`background:${PRESET_SWATCH[tid]}`} aria-hidden="true"></span>
          <span class="settings-theme-swatch__label">{themeNameLabel(tid)}</span>
        </button>
        <button
          type="button"
          class="om-btn om-btn--ghost om-btn--compact settings-theme-example__copy"
          title={t("settings.themePersonalizeHint")}
          on:click={() => personalizePreset(tid)}
        >{t("settings.themePersonalize")}</button>
      </div>
    {/each}
  </div>
</section>

<section class="settings-group" aria-labelledby="set-theme-custom">
  <h3 id="set-theme-custom" class="settings-group__title">{t("settings.customThemesTitle")}</h3>
  <p class="settings-hint">{t("settings.customThemesHint")}</p>
  {#if customThemes.length === 0}
    <p class="settings-example">{t("settings.customThemesEmpty")}</p>
  {:else}
    <ul class="settings-custom-themes">
      {#each customThemes as row (row.id)}
        <li class="settings-custom-theme-card" class:settings-custom-theme-card--active={isCustomThemeActive(themeSelection, row.id)}>
          <div class="settings-custom-theme-card__head">
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact"
              class:om-btn--primary={isCustomThemeActive(themeSelection, row.id)}
              on:click={() => (themeSelection = `custom:${row.id}`)}
            >
              {t("settings.customThemeUse")}
            </button>
            <input
              class="settings-custom-theme__name"
              type="text"
              value={row.name}
              aria-label={t("settings.customThemeNameAria")}
              on:input={(e) => updateCustomName(row.id, e.currentTarget.value)}
            />
            <button
              type="button"
              class="om-btn om-btn--ghost om-btn--compact"
              title={t("settings.customThemeRemove")}
              on:click={() => removeCustomTheme(row.id)}
            >×</button>
          </div>
          <div class="settings-color-grid">
            {#each THEME_COLOR_FIELDS as field (field)}
              <label class="settings-color-field">
                <span class="settings-color-field__label">{t(colorLabelKey(field))}</span>
                <input
                  type="color"
                  value={row.colors[field]}
                  on:input={(e) => updateCustomColor(row.id, field, e.currentTarget.value)}
                />
              </label>
            {/each}
          </div>
        </li>
      {/each}
    </ul>
  {/if}
  <button type="button" class="om-btn om-btn--ghost om-btn--compact" on:click={addBlankCustomTheme}>
    {t("settings.customThemeAdd")}
  </button>
</section>

<section class="settings-group" aria-labelledby="set-bg">
  <h3 id="set-bg" class="settings-group__title">{t("settings.bgTitle")}</h3>
  <p class="settings-hint">{t("settings.bgHint")}</p>
  <label class="settings-bg-scope" for="set-bg-scope">
    <span class="field-label">{t("settings.bgScopeLabel")}</span>
    <select id="set-bg-scope" class="om-input settings-bg-scope__select" bind:value={uiBgScope}>
      {#each BG_SCOPE_IDS as scopeId (scopeId)}
        <option value={scopeId}>{t(`settings.bgScope.${scopeId}`)}</option>
      {/each}
    </select>
  </label>
  <p class="settings-hint">{t(`settings.bgScopeHint.${uiBgScope}`)}</p>
  <SettingsBgImagePicker
    bind:uiBgImagePath
    bind:uiBgBlur
    {galleryFolder}
    {recentFolders}
    {pinnedFolders}
    {pinnedFolderLabels}
    onBrowseFolder={onBrowseBgFolder}
  />
</section>

<section class="settings-group" aria-labelledby="set-font">
  <h3 id="set-font" class="settings-group__title">{t("settings.fontTitle")}</h3>
  <p class="settings-hint">{t("settings.fontHint")}</p>
  <div class="settings-preset-row settings-font-row" role="group" aria-label={t("settings.fontTitle")}>
    {#each UI_FONT_IDS as fid (fid)}
      <button
        type="button"
        class="om-btn om-btn--ghost om-btn--compact settings-font-chip"
        class:om-btn--primary={uiFont === fid}
        on:click={() => (uiFont = fid)}
      >
        <span class="settings-font-chip__name">{t(`settings.fontNames.${fid}`)}</span>
        <span class="settings-font-chip__sample">{t(fontSample(fid))}</span>
      </button>
    {/each}
  </div>
</section>

<section class="settings-group" aria-labelledby="set-thumbs-style">
  <h3 id="set-thumbs-style" class="settings-group__title">{t("settings.thumbStyleTitle")}</h3>
  <p class="settings-hint">{t("settings.thumbStyleHint")}</p>
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
  <p class="settings-hint">{t("settings.cardStyleHint")}</p>
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
  <p class="settings-hint">{t("settings.appearanceThumbsHint")}</p>
</section>
