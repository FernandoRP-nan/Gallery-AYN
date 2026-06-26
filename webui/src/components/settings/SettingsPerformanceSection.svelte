<script lang="ts">
  import { t } from "../../lib/i18n";

  export let galleryUnlimitedBatchSize: number;
  export let galleryWindowOverscanBefore: number;
  export let galleryWindowOverscanAfter: number;
  export let galleryJumpCoreOverscanBefore: number;
  export let galleryJumpCoreOverscanAfter: number;
  export let gallerySlidingWindowEnabled: boolean;
  export let gallerySlidingWindowMaxItems: number;
  export let galleryThumbBuildWorkers: number;
  export let galleryThumbHqWorkers: number;
  export let galleryThumbHqVisibleSequential: number;

  function applyJumpCoreAggressivePreset() {
    galleryJumpCoreOverscanBefore = 32;
    galleryJumpCoreOverscanAfter = 48;
  }

  function applyPerfPreset(kind: "conservative" | "balanced" | "aggressive" | "highEnd") {
    if (kind === "conservative") {
      galleryUnlimitedBatchSize = 48;
      galleryWindowOverscanBefore = 64;
      galleryWindowOverscanAfter = 96;
      galleryJumpCoreOverscanBefore = 24;
      galleryJumpCoreOverscanAfter = 40;
      gallerySlidingWindowEnabled = false;
      gallerySlidingWindowMaxItems = 640;
      galleryThumbBuildWorkers = 4;
      galleryThumbHqWorkers = 2;
      galleryThumbHqVisibleSequential = 8;
    } else if (kind === "highEnd") {
      galleryUnlimitedBatchSize = 96;
      galleryWindowOverscanBefore = 128;
      galleryWindowOverscanAfter = 192;
      galleryJumpCoreOverscanBefore = 32;
      galleryJumpCoreOverscanAfter = 48;
      gallerySlidingWindowEnabled = true;
      gallerySlidingWindowMaxItems = 896;
      galleryThumbBuildWorkers = 12;
      galleryThumbHqWorkers = 10;
      galleryThumbHqVisibleSequential = 20;
    } else if (kind === "aggressive") {
      galleryUnlimitedBatchSize = 128;
      galleryWindowOverscanBefore = 192;
      galleryWindowOverscanAfter = 256;
      galleryJumpCoreOverscanBefore = 24;
      galleryJumpCoreOverscanAfter = 32;
      gallerySlidingWindowEnabled = true;
      gallerySlidingWindowMaxItems = 768;
      galleryThumbBuildWorkers = 12;
      galleryThumbHqWorkers = 8;
      galleryThumbHqVisibleSequential = 24;
    } else {
      galleryUnlimitedBatchSize = 48;
      galleryWindowOverscanBefore = 96;
      galleryWindowOverscanAfter = 160;
      galleryJumpCoreOverscanBefore = 32;
      galleryJumpCoreOverscanAfter = 48;
      gallerySlidingWindowEnabled = true;
      gallerySlidingWindowMaxItems = 896;
      galleryThumbBuildWorkers = 8;
      galleryThumbHqWorkers = 4;
      galleryThumbHqVisibleSequential = 16;
    }
  }
</script>

<div class="settings-group">
  <p class="settings-lead">{t("settings.perfAdvancedLead")}</p>

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
  <p class="settings-hint">{t("settings.unlimitedBatchHint")}</p>

  <p class="settings-hint settings-hint--section">{t("settings.perfOverscanTitle")}</p>
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

  <p class="settings-hint settings-hint--section">{t("settings.jumpCoreTitle")}</p>
  <p class="settings-hint">{t("settings.jumpCoreHint")}</p>
  <div class="settings-preset-row">
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--compact settings-preset-chip"
      on:click={applyJumpCoreAggressivePreset}>{t("settings.perfPresetJumpCoreAggressive")}</button
    >
  </div>
  <div class="settings-grid-2">
    <div>
      <label class="field-label" for="set-jump-core-before">{t("settings.jumpCoreOverscanBefore")}</label>
      <input
        id="set-jump-core-before"
        class="om-input"
        type="number"
        min="16"
        max="128"
        bind:value={galleryJumpCoreOverscanBefore}
      />
    </div>
    <div>
      <label class="field-label" for="set-jump-core-after">{t("settings.jumpCoreOverscanAfter")}</label>
      <input
        id="set-jump-core-after"
        class="om-input"
        type="number"
        min="24"
        max="160"
        bind:value={galleryJumpCoreOverscanAfter}
      />
    </div>
  </div>

  <label class="settings-check">
    <input type="checkbox" bind:checked={gallerySlidingWindowEnabled} />
    <span>{t("settings.slidingWindowEnabled")}</span>
  </label>
  {#if gallerySlidingWindowEnabled}
    <label class="field-label" for="set-sliding-max">{t("settings.slidingWindowMaxItems")}</label>
    <input
      id="set-sliding-max"
      class="om-input"
      type="number"
      min="320"
      max="4096"
      bind:value={gallerySlidingWindowMaxItems}
    />
    <p class="settings-hint">{t("settings.slidingWindowHint")}</p>
  {/if}

  <p class="settings-hint settings-hint--section">{t("settings.perfWorkersTitle")}</p>
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
  .settings-check {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0.5rem 0;
    cursor: pointer;
  }
</style>
