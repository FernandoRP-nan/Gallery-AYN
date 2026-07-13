<script lang="ts">
  import { t } from "../../lib/i18n";

  export let thumbsPerPage: number;
  export let galleryMasonryTightSpacing = false;
  export let settingsThumbPresetIdx: number;
  export let settingsThumbScaleDraft: number;
  export let galleryThumbQualityPreset: "balanced" | "sharp" | "hidpi" | "performance" = "balanced";
  export let galleryThumbDiskCacheEnabled = false;
  export let thumbGapPx: number;
  export let thumbImageRadiusPx: number;
  export let thumbTileRadiusPx: number;
  export let showAdvanced = false;

  const thumbScalePresets = [
    { id: "compacto", labelKey: "settings.thumbPresetCompact", value: 0.62 },
    { id: "medio", labelKey: "settings.thumbPresetMedium", value: 1.0 },
    { id: "comodo", labelKey: "settings.thumbPresetComfort", value: 1.18 },
    { id: "grande", labelKey: "settings.thumbPresetLarge", value: 1.45 },
    { id: "xgrande", labelKey: "settings.thumbPresetXL", value: 1.8 }
  ] as const;
</script>

<div class="settings-group">
  <p class="settings-lead">{t("settings.thumbsLead")}</p>

  <p class="settings-hint settings-hint--section">{t("settings.thumbsPagingTitle")}</p>
  {#if showAdvanced}
    <label class="field-label" for="set-thumbs-page">{t("settings.thumbsPerPageLabel")}</label>
    <input
      id="set-thumbs-page"
      class="om-input"
      type="number"
      min="0"
      placeholder={t("settings.thumbsPerPagePlaceholder")}
      bind:value={thumbsPerPage}
    />
  {/if}
  <div class="settings-preset-row">
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 24)}
      >{t("settings.presetHighPerf24")}</button
    >
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 48)}
      >{t("settings.presetPerf48")}</button
    >
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 96)}
      >{t("settings.presetBalanced96")}</button
    >
    {#if showAdvanced}
      <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 0)}
        >{t("settings.presetUnlimited0")}</button
      >
    {/if}
  </div>
  {#if showAdvanced && Number(thumbsPerPage) === 0}
    <p class="settings-hint settings-hint--warn">{t("settings.unlimitedWarn")}</p>
  {/if}

  <p class="settings-hint settings-hint--section">{t("settings.thumbsSizeTitle")}</p>
  <label class="field-label" for="set-thumb-preset">{t("settings.thumbSizePreset")}</label>
  <input
    id="set-thumb-preset"
    class="om-range"
    type="range"
    min="0"
    max={thumbScalePresets.length - 1}
    step="1"
    bind:value={settingsThumbPresetIdx}
    on:input={() => {
      const p = thumbScalePresets[Math.max(0, Math.min(thumbScalePresets.length - 1, Number(settingsThumbPresetIdx) || 0))];
      settingsThumbScaleDraft = p.value;
    }}
  />
  <div class="settings-preset-row">
    {#each thumbScalePresets as p, i}
      <button
        type="button"
        class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
        class:om-btn--primary={i === settingsThumbPresetIdx}
        on:click={() => {
          settingsThumbPresetIdx = i;
          settingsThumbScaleDraft = p.value;
        }}
      >{t(p.labelKey)}</button>
    {/each}
  </div>
  {#if showAdvanced}
    <label class="field-label" for="set-thumb-scale"
      >{t("settings.fineTune")} {Math.round(settingsThumbScaleDraft * 100)}%</label
    >
    <input
      id="set-thumb-scale"
      class="om-range"
      type="range"
      min="0.01"
      max="2.25"
      step="0.01"
      bind:value={settingsThumbScaleDraft}
    />

    <label class="field-label" for="set-thumb-quality">{t("settings.thumbQualityLabel")}</label>
    <select id="set-thumb-quality" class="om-input" bind:value={galleryThumbQualityPreset}>
      <option value="balanced">{t("settings.thumbQualityBalanced")}</option>
      <option value="sharp">{t("settings.thumbQualitySharp")}</option>
      <option value="hidpi">{t("settings.thumbQualityHidpi")}</option>
      <option value="performance">{t("settings.thumbQualityPerformance")}</option>
    </select>
    <p class="settings-hint">{t("settings.thumbQualityHint")}</p>
  {/if}

  <p class="settings-hint settings-hint--section">{t("settings.masonrySpacingTitle")}</p>
  <label class="check settings-check">
    <input type="checkbox" bind:checked={galleryMasonryTightSpacing} />
    {t("settings.masonryTightSpacing")}
  </label>
  <p class="settings-hint settings-hint--indent">{t("settings.masonryTightSpacingHint")}</p>

  {#if !galleryMasonryTightSpacing}
    <p class="settings-hint settings-hint--section">{t("settings.thumbsSpacingTitle")}</p>
    <label class="field-label" for="set-thumb-gap"
      >{t("settings.thumbGap")} {Math.round(thumbGapPx)}px</label
    >
    <input
      id="set-thumb-gap"
      class="om-range"
      type="range"
      min="0"
      max="20"
      step="1"
      bind:value={thumbGapPx}
    />
  {/if}

  {#if showAdvanced}
    <label class="field-label" for="set-thumb-radius"
      >{t("settings.thumbImageRadius")} {Math.round(thumbImageRadiusPx)}px</label
    >
    <input
      id="set-thumb-radius"
      class="om-range"
      type="range"
      min="0"
      max="18"
      step="1"
      bind:value={thumbImageRadiusPx}
    />
    <label class="field-label" for="set-tile-radius"
      >{t("settings.thumbTileRadius")} {Math.round(thumbTileRadiusPx)}px</label
    >
    <input
      id="set-tile-radius"
      class="om-range"
      type="range"
      min="0"
      max="28"
      step="1"
      bind:value={thumbTileRadiusPx}
    />
    <div class="settings-preset-row">
      <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbTileRadiusPx = 0)}
        >{t("settings.tileRadiusNone")}</button
      >
      <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbTileRadiusPx = 6)}
        >{t("settings.tileRadiusSoft")}</button
      >
      <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbTileRadiusPx = 12)}
        >{t("settings.tileRadiusMedium")}</button
      >
      <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbTileRadiusPx = 18)}
        >{t("settings.tileRadiusHigh")}</button
      >
    </div>

    <p class="settings-hint settings-hint--section">{t("settings.thumbDiskCacheTitle")}</p>
    <label class="settings-check">
      <input type="checkbox" bind:checked={galleryThumbDiskCacheEnabled} />
      <span>{t("settings.thumbDiskCacheEnabled")}</span>
    </label>
    <p class="settings-hint">{t("settings.thumbDiskCacheHint")}</p>
  {/if}
</div>

<style>
  .settings-hint--section {
    margin-top: 0.35rem;
    font-weight: 600;
    color: var(--om-text-secondary);
  }

  .settings-check {
    display: flex;
    align-items: center;
    gap: var(--om-space-2);
    margin-top: var(--om-space-1);
    cursor: pointer;
  }

  .settings-hint--indent {
    margin-left: 1.5rem;
    margin-top: 0.25rem;
  }
</style>
