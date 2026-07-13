<script lang="ts">
  import { t } from "../lib/i18n";
  import { frozenPagerState } from "../lib/chromeRemember";
  import { formatBytes, googlePageItems } from "../lib/pagerUtils";

  export type ActiveProcess = { id: string; label: string };

  export let thumbsPerPage: number;
  export let pageJumpDraft: number;
  export let status: string;
  export let scanSourceHint = "";
  export let previewVisible: boolean;
  export let previewRatio: number;
  export let thumbScale: number;
  export let activeProcesses: ActiveProcess[] = [];
  export let showProcesses = false;
  export let showScanHint = false;
  export let showBuildTag = false;

  export let goPage: (page: number) => void | Promise<void>;
  export let jumpToPageDraft: () => void | Promise<void>;
  export let togglePreviewVisible: () => void | Promise<void>;
  export let scheduleThumbScaleReload: () => void;
  export let flushThumbScaleOnRelease: () => void;

  let processPanelOpen = false;
  let processToggleEl: HTMLButtonElement | null = null;
  let processPanelStyle = "";

  function updateProcessPanelPosition() {
    if (!processToggleEl) return;
    const r = processToggleEl.getBoundingClientRect();
    const panelW = Math.min(360, Math.max(280, window.innerWidth * 0.72));
    const left = Math.min(Math.max(8, r.right - panelW), window.innerWidth - panelW - 8);
    const bottom = window.innerHeight - r.top + 8;
    processPanelStyle = `left:${left}px;bottom:${bottom}px;width:${panelW}px;`;
  }

  function toggleProcessPanel() {
    processPanelOpen = !processPanelOpen;
    if (processPanelOpen) {
      updateProcessPanelPosition();
    }
  }

  $: pager = $frozenPagerState;
  $: pageLinks = googlePageItems(Number(pager.page) || 1, Number(pager.totalPages) || 1);
  $: processCount = activeProcesses.length;

  function mediaCountLabel(state: typeof pager): string {
    const total = Number(state?.total ?? 0);
    const images = Number(state?.totalImages ?? total);
    const videos = Number(state?.totalVideos ?? 0);
    if (videos > 0) {
      return `${images} ${t("pager.imagesWord")} · ${videos} ${t("pager.videosWord")}`;
    }
    return `${total} ${t("pager.imagesWord")}`;
  }

  /** Etiqueta de progreso en modo ilimitado (ventana deslizante vs carga desde el inicio). */
  function unlimitedLoadedLabel(state: typeof pager): string {
    const total = Number(state?.total ?? 0);
    const end = Number(state?.endIndex ?? 0);
    const windowStart = Number(state?.windowStart ?? 0);
    if (windowStart > 0 && end > windowStart) {
      return `${t("pager.showingRange")} ${windowStart + 1}–${end} ${t("pager.ofWord")} ${total}`;
    }
    return `${t("pager.loadedPrefix")} ${end}/${total}`;
  }
</script>

<footer class="pager om-panel pager--bar app-chrome app-chrome--footer" aria-label={t("pager.footerAria")}>
  {#if thumbsPerPage !== 0}
    <button type="button" class="om-btn om-btn--ghost om-btn--icon" title={t("pager.firstPage")} on:click={() => goPage(1)}>|«</button>
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--icon"
      title={t("pager.prevPage")}
      on:click={() => goPage(Math.max(1, pager.page - 1))}>‹</button
    >
    {#each pageLinks as item}
      {#if item === "gap"}
        <span class="pager__gap" aria-hidden="true">…</span>
      {:else}
        <button
          type="button"
          class="om-btn om-btn--ghost pager__num"
          class:om-btn--primary={item === pager.page}
          title={t("pager.goPageTitle").replace("{n}", String(item))}
          on:click={() => goPage(item)}>{item}</button
        >
      {/if}
    {/each}
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--icon"
      title={t("pager.nextPage")}
      on:click={() => goPage(Math.min(pager.totalPages, pager.page + 1))}>›</button
    >
    <button type="button" class="om-btn om-btn--ghost om-btn--icon" title={t("pager.lastPage")} on:click={() => goPage(pager.totalPages)}>»|</button>
    <span class="pager__google-line"
      >{mediaCountLabel(pager)} · {t("pager.pageWord")}
      {pager.page}
      {t("pager.ofWord")}
      {pager.totalPages}</span
    >
    <label class="pager__jump">
      <input
        class="om-input pager__jump-input"
        type="number"
        min="1"
        max={pager.totalPages}
        bind:value={pageJumpDraft}
        on:keydown={(e) => e.key === "Enter" && jumpToPageDraft()}
      />
      <span class="pager__jump-total">/ {pager.totalPages}</span>
    </label>
    <button type="button" class="om-btn om-btn--primary om-btn--compact" on:click={jumpToPageDraft}>{t("pager.goJump")}</button>
  {:else}
    <span class="pager__google-line">
      {unlimitedLoadedLabel(pager)}
      · {mediaCountLabel(pager)} ·
      {Number(pager?.totalElements ?? Number(pager?.total ?? 0) + Number(pager?.subfoldersCount ?? 0))}
      {t("pager.elementsWord")} · {t("pager.totalWeight")}
      {Number(pager?.totalBytes ?? -1) < 0 ? t("pager.calculating") : formatBytes(Number(pager?.totalBytes ?? 0))}
    </span>
  {/if}
  <div class="grow"></div>
  {#if showProcesses}
  <div class="pager__process-wrap">
    <button
      type="button"
      class="om-btn om-btn--ghost om-btn--compact pager__process-toggle"
      class:pager__process-toggle--active={processCount > 0}
      bind:this={processToggleEl}
      aria-expanded={processPanelOpen}
      title={processPanelOpen ? t("pager.processToggleHide") : t("pager.processToggle")}
      on:click={toggleProcessPanel}
    >
      <span class="pager__process-dot" class:pager__process-dot--on={processCount > 0} aria-hidden="true"></span>
      {t("pager.processToggle")}{processCount > 0 ? ` (${processCount})` : ""}
    </button>
    {#if processPanelOpen}
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <div class="pager__process-backdrop" role="presentation" on:click={() => (processPanelOpen = false)}></div>
      <div
        class="pager__process-panel om-panel om-panel--lift"
        role="status"
        aria-live="polite"
        style={processPanelStyle}
      >
        {#if activeProcesses.length === 0}
          <p class="pager__process-empty">{t("pager.processEmpty")}</p>
        {:else}
          <ul class="pager__process-list">
            {#each activeProcesses as proc (proc.id)}
              <li class="pager__process-item">{proc.label}</li>
            {/each}
          </ul>
        {/if}
      </div>
    {/if}
  </div>
  {/if}
  <span class="status-line">{status}</span>
  {#if showScanHint && scanSourceHint}
    <span class="status-line status-line--scan" title={scanSourceHint}>{scanSourceHint}</span>
  {/if}
  {#if showBuildTag}
  <span class="webui-build-tag" title={t("pager.buildTagTitle")}>{__WEBUI_BUILD__.slice(0, 10)}</span>
  {/if}
  <button
    type="button"
    class="om-btn om-btn--ghost om-btn--compact"
    title={previewVisible ? t("pager.previewHide") : t("pager.previewShow")}
    on:click={togglePreviewVisible}>{previewVisible ? t("pager.previewOn") : t("pager.previewOff")}</button
  >
  <span class="field-label pager__split-label" title={t("pager.splitHint")}
    >{t("preview.panelRight")} ~{Math.round(previewRatio * 100)}%</span
  >
  <label class="field-label pager__thumb-label" for="route-thumb-scale-footer"
    >{t("pager.thumbsLabel")} {Math.round(thumbScale * 100)}%</label
  >
  <input
    id="route-thumb-scale-footer"
    class="om-range pager__thumb-range"
    type="range"
    min="0.01"
    max="2.25"
    step="0.01"
    bind:value={thumbScale}
    on:input={scheduleThumbScaleReload}
    on:change={flushThumbScaleOnRelease}
  />
</footer>

<style>
  .pager__process-wrap {
    position: relative;
    display: inline-flex;
    align-items: center;
    z-index: 1;
  }
  .pager__process-toggle {
    gap: 6px;
    min-height: 1.75rem;
  }
  .pager__process-toggle--active {
    color: var(--om-accent, #007acc);
  }
  .pager__process-dot {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: var(--om-text-muted);
    opacity: 0.45;
    flex-shrink: 0;
  }
  .pager__process-dot--on {
    background: var(--om-accent, #007acc);
    opacity: 1;
    box-shadow: 0 0 0 2px color-mix(in oklab, var(--om-accent, #007acc) 30%, transparent);
    animation: process-pulse 1.4s ease-in-out infinite;
  }
  @keyframes process-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.55; }
  }
  .pager__process-backdrop {
    position: fixed;
    inset: 0;
    z-index: 198;
    background: transparent;
  }
  .pager__process-panel {
    position: fixed;
    z-index: 200;
    min-width: min(280px, 72vw);
    max-width: 360px;
    max-height: min(220px, 40vh);
    overflow: auto;
    padding: 8px 10px;
    box-shadow: var(--om-shadow-lg);
  }
  .pager__process-empty {
    margin: 0;
    font-size: 0.78rem;
    color: var(--om-text-muted);
  }
  .pager__process-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .pager__process-item {
    font-size: 0.78rem;
    color: var(--om-text-secondary);
    padding: 4px 6px;
    border-radius: 4px;
    background: color-mix(in oklab, var(--om-surface-2) 70%, transparent);
    line-height: 1.35;
  }
</style>
