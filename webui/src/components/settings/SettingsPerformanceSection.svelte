<script lang="ts">
  import { t } from "../../lib/i18n";

  export let thumbsPerPage: number;
  export let galleryUnlimitedBatchSize: number;
  export let galleryWindowOverscanBefore: number;
  export let galleryWindowOverscanAfter: number;
  export let galleryThumbBuildWorkers: number;
  export let galleryThumbHqWorkers: number;
  export let galleryThumbHqVisibleSequential: number;

  function applyPerfPreset(kind: "conservative" | "balanced" | "aggressive" | "highEnd") {
    if (kind === "conservative") {
      galleryUnlimitedBatchSize = 48;
      galleryWindowOverscanBefore = 64;
      galleryWindowOverscanAfter = 96;
      galleryThumbBuildWorkers = 4;
      galleryThumbHqWorkers = 2;
      galleryThumbHqVisibleSequential = 8;
    } else if (kind === "highEnd") {
      galleryUnlimitedBatchSize = 96;
      galleryWindowOverscanBefore = 128;
      galleryWindowOverscanAfter = 192;
      galleryThumbBuildWorkers = 12;
      galleryThumbHqWorkers = 10;
      galleryThumbHqVisibleSequential = 20;
    } else if (kind === "aggressive") {
      galleryUnlimitedBatchSize = 128;
      galleryWindowOverscanBefore = 192;
      galleryWindowOverscanAfter = 256;
      galleryThumbBuildWorkers = 12;
      galleryThumbHqWorkers = 8;
      galleryThumbHqVisibleSequential = 24;
    } else {
      galleryUnlimitedBatchSize = 48;
      galleryWindowOverscanBefore = 96;
      galleryWindowOverscanAfter = 160;
      galleryThumbBuildWorkers = 8;
      galleryThumbHqWorkers = 4;
      galleryThumbHqVisibleSequential = 16;
    }
  }
</script>

<div class="settings-group">
  <h3 class="settings-group__title">{t("settings.sectionPerformance")}</h3>

  <label class="field-label" for="set-thumbs-page">{t("settings.thumbsPerPageLabel")}</label>
  <input
    id="set-thumbs-page"
    class="om-input"
    type="number"
    min="0"
    placeholder={t("settings.thumbsPerPagePlaceholder")}
    bind:value={thumbsPerPage}
  />
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
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => (thumbsPerPage = 0)}
      >{t("settings.presetUnlimited0")}</button
    >
  </div>
  {#if Number(thumbsPerPage) === 0}
    <p class="settings-hint settings-hint--warn">{t("settings.unlimitedWarn")}</p>
  {/if}

  <p class="settings-hint settings-hint--section">{t("settings.perfMemoryTitle")}</p>
  <div class="settings-preset-row">
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => applyPerfPreset("conservative")}
      >{t("settings.perfPresetConservative")}</button
    >
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => applyPerfPreset("balanced")}
      >{t("settings.perfPresetBalanced")}</button
    >
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => applyPerfPreset("highEnd")}
      >{t("settings.perfPresetHighEnd")}</button
    >
    <button type="button" class="om-btn om-btn--ghost om-btn--compact settings-preset-chip" on:click={() => applyPerfPreset("aggressive")}
      >{t("settings.perfPresetAggressive")}</button
    >
  </div>

  <label class="field-label" for="set-batch-size">{t("settings.unlimitedBatchLabel")}</label>
  <input id="set-batch-size" class="om-input" type="number" min="24" max="256" bind:value={galleryUnlimitedBatchSize} />

  <div class="settings-grid-2">
    <div>
      <label class="field-label" for="set-overscan-before">{t("settings.windowOverscanBefore")}</label>
      <input id="set-overscan-before" class="om-input" type="number" min="32" max="512" bind:value={galleryWindowOverscanBefore} />
    </div>
    <div>
      <label class="field-label" for="set-overscan-after">{t("settings.windowOverscanAfter")}</label>
      <input id="set-overscan-after" class="om-input" type="number" min="32" max="512" bind:value={galleryWindowOverscanAfter} />
    </div>
  </div>

  <div class="settings-grid-2">
    <div>
      <label class="field-label" for="set-build-workers">{t("settings.thumbBuildWorkers")}</label>
      <input id="set-build-workers" class="om-input" type="number" min="2" max="16" step="1" bind:value={galleryThumbBuildWorkers} />
    </div>
    <div>
      <label class="field-label" for="set-hq-workers">{t("settings.thumbHqWorkers")}</label>
      <input id="set-hq-workers" class="om-input" type="number" min="1" max="16" step="1" bind:value={galleryThumbHqWorkers} />
    </div>
  </div>

  <label class="field-label" for="set-hq-visible">{t("settings.thumbHqVisibleSequential")}</label>
  <input id="set-hq-visible" class="om-input" type="number" min="4" max="32" bind:value={galleryThumbHqVisibleSequential} />

  <p class="settings-hint">{t("settings.perfMemoryHint")}</p>
  <p class="settings-hint">{t("settings.perfHint")}</p>
</div>

<style>
  .settings-hint--section {
    margin-top: 0.35rem;
    font-weight: 600;
    color: var(--om-text-secondary);
  }
  .settings-grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--om-space-2);
  }
</style>
