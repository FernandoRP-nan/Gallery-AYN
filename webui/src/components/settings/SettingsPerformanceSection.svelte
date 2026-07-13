<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { bridge } from "../../lib/api";
  import { t } from "../../lib/i18n";

  export let galleryWarmIndexOnStartup = false;
  export let galleryWarmIncludeChildren = true;
  export let galleryWarmMaxDepth = 2;
  export let galleryScanCacheMax = 20;
  export let galleryScanCacheTtlS = 600;
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
  export let galleryCompactIndicesAfterMove = true;

  type WarmStatus = {
    running: boolean;
    done: number;
    total: number;
    currentPath: string;
    errors: Array<{ path: string; error: string }>;
    cancelled: boolean;
  };

  let warmStatus: WarmStatus = {
    running: false,
    done: 0,
    total: 0,
    currentPath: "",
    errors: [],
    cancelled: false,
  };
  let warmPollTimer: ReturnType<typeof setTimeout> | null = null;

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
      galleryWarmIndexOnStartup = true;
      galleryScanCacheMax = 24;
      galleryScanCacheTtlS = 900;
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

  async function pollWarmStatus() {
    try {
      const st = await bridge.galleryIndexWarmStatus();
      warmStatus = {
        running: Boolean(st?.running),
        done: Number(st?.done ?? 0),
        total: Number(st?.total ?? 0),
        currentPath: String(st?.currentPath ?? ""),
        errors: Array.isArray(st?.errors) ? st.errors : [],
        cancelled: Boolean(st?.cancelled),
      };
      if (warmStatus.running) {
        warmPollTimer = setTimeout(() => void pollWarmStatus(), 500);
      }
    } catch {
      warmStatus = { ...warmStatus, running: false };
    }
  }

  async function startWarmIndex() {
    galleryWarmMaxDepth = Math.max(0, Math.min(6, Math.round(Number(galleryWarmMaxDepth) || 0)));
    await bridge.settingsPatch({
      gallery_warm_include_children: Boolean(galleryWarmIncludeChildren),
      gallery_warm_max_depth: galleryWarmMaxDepth,
    });
    await bridge.galleryIndexWarmStart(null, galleryWarmIncludeChildren);
    warmStatus = { ...warmStatus, running: true, done: 0, total: 0, errors: [], cancelled: false };
    void pollWarmStatus();
  }

  async function cancelWarmIndex() {
    await bridge.galleryIndexWarmCancel();
    void pollWarmStatus();
  }

  onDestroy(() => {
    if (warmPollTimer !== null) clearTimeout(warmPollTimer);
  });

  onMount(() => {
    void bridge.galleryIndexWarmStatus().then((st) => {
      if (!st?.running) return;
      warmStatus = {
        running: true,
        done: Number(st.done ?? 0),
        total: Number(st.total ?? 0),
        currentPath: String(st.currentPath ?? ""),
        errors: Array.isArray(st.errors) ? st.errors : [],
        cancelled: Boolean(st.cancelled),
      };
      void pollWarmStatus();
    });
  });
</script>

<div class="settings-group">
  <p class="settings-lead">{t("settings.warmIndexLead")}</p>

  <label class="settings-check">
    <input type="checkbox" bind:checked={galleryWarmIndexOnStartup} />
    <span>{t("settings.warmIndexOnStartup")}</span>
  </label>
  <label class="settings-check">
    <input type="checkbox" bind:checked={galleryWarmIncludeChildren} />
    <span>{t("settings.warmIndexIncludeChildren")}</span>
  </label>

  <label class="field-label" for="set-warm-depth">{t("settings.warmIndexMaxDepth")}</label>
  <input
    id="set-warm-depth"
    class="om-input"
    type="number"
    min="0"
    max="6"
    step="1"
    bind:value={galleryWarmMaxDepth}
    disabled={!galleryWarmIncludeChildren}
  />
  <p class="settings-hint">{t("settings.warmIndexMaxDepthHint")}</p>

  <div class="settings-preset-row">
    <button
      type="button"
      class="om-btn om-btn--primary om-btn--compact"
      disabled={warmStatus.running}
      on:click={() => void startWarmIndex()}
    >
      {t("settings.warmIndexRunNow")}
    </button>
    {#if warmStatus.running}
      <button type="button" class="om-btn om-btn--ghost om-btn--compact" on:click={() => void cancelWarmIndex()}>
        {t("settings.warmIndexCancel")}
      </button>
    {/if}
  </div>

  {#if warmStatus.running}
    <p class="settings-hint settings-hint--warm">
      {t("settings.warmIndexProgress")
        .replace("{done}", String(warmStatus.done))
        .replace("{total}", String(warmStatus.total))}
      {#if warmStatus.currentPath}
        <br />
        <span class="warm-index-path">{t("settings.warmIndexCurrent").replace("{path}", warmStatus.currentPath)}</span>
      {/if}
    </p>
  {:else if warmStatus.done > 0 && !warmStatus.cancelled}
    <p class="settings-hint settings-hint--ok">
      {t("settings.warmIndexDone").replace("{done}", String(warmStatus.done))}
      {#if warmStatus.errors.length > 0}
        {" · "}{t("settings.warmIndexErrors").replace("{count}", String(warmStatus.errors.length))}
      {/if}
    </p>
  {/if}

  <hr class="settings-divider" />

  <p class="settings-subtitle">{t("settings.scanCacheTitle")}</p>
  <div class="settings-grid-2">
    <div>
      <label class="field-label" for="set-scan-cache-max">{t("settings.scanCacheMaxLabel")}</label>
      <input id="set-scan-cache-max" class="om-input" type="number" min="4" max="64" bind:value={galleryScanCacheMax} />
    </div>
    <div>
      <label class="field-label" for="set-scan-cache-ttl">{t("settings.scanCacheTtlLabel")}</label>
      <input id="set-scan-cache-ttl" class="om-input" type="number" min="60" max="7200" step="60" bind:value={galleryScanCacheTtlS} />
    </div>
  </div>
  <p class="settings-hint">{t("settings.scanCacheMaxHint")}</p>
  <p class="settings-hint">{t("settings.scanCacheTtlHint")}</p>
  <p class="settings-hint">{t("settings.perfHighEndWarmHint")}</p>

  <hr class="settings-divider" />

  <p class="settings-lead settings-lead--sub">{t("settings.perfAdvancedLead")}</p>

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

  <label class="settings-check">
    <input type="checkbox" bind:checked={galleryCompactIndicesAfterMove} />
    <span>{t("settings.compactIndicesAfterMove")}</span>
  </label>
  <p class="settings-hint">{t("settings.compactIndicesAfterMoveHint")}</p>

  <p class="settings-hint">{t("settings.perfMemoryHint")}</p>
</div>

<style>
  .settings-hint--section {
    margin-top: 0.35rem;
    font-weight: 600;
    color: var(--om-text-secondary);
  }
  .settings-lead--sub {
    margin-top: 0.25rem;
    font-size: 0.95rem;
  }
  .settings-divider {
    border: none;
    border-top: 1px solid var(--om-border-subtle, rgb(255 255 255 / 0.08));
    margin: 1rem 0;
  }
  .settings-hint--warm {
    color: var(--om-accent, #7eb8ff);
  }
  .settings-hint--ok {
    color: var(--om-text-secondary);
  }
  .warm-index-path {
    word-break: break-all;
    opacity: 0.9;
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
