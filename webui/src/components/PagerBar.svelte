<script lang="ts">
  import { t } from "../lib/i18n";
  import { frozenPagerState } from "../lib/chromeRemember";
  import { formatBytes, googlePageItems } from "../lib/pagerUtils";

  export let thumbsPerPage: number;
  export let pageJumpDraft: number;
  export let status: string;
  export let previewVisible: boolean;
  export let previewRatio: number;
  export let thumbScale: number;

  export let goPage: (page: number) => void | Promise<void>;
  export let jumpToPageDraft: () => void | Promise<void>;
  export let togglePreviewVisible: () => void | Promise<void>;
  export let scheduleThumbScaleReload: () => void;
  export let flushThumbScaleOnRelease: () => void;

  $: pager = $frozenPagerState;
  $: pageLinks = googlePageItems(Number(pager.page) || 1, Number(pager.totalPages) || 1);

  function mediaCountLabel(state: typeof pager): string {
    const total = Number(state?.total ?? 0);
    const images = Number(state?.totalImages ?? total);
    const videos = Number(state?.totalVideos ?? 0);
    if (videos > 0) {
      return `${images} ${t("pager.imagesWord")} · ${videos} ${t("pager.videosWord")}`;
    }
    return `${total} ${t("pager.imagesWord")}`;
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
      {t("pager.loadedPrefix")}
      {Number(pager?.endIndex ?? 0)}/{Number(pager?.total ?? 0)}
      · {mediaCountLabel(pager)} ·
      {Number(pager?.totalElements ?? Number(pager?.total ?? 0) + Number(pager?.subfoldersCount ?? 0))}
      {t("pager.elementsWord")} · {t("pager.totalWeight")}
      {Number(pager?.totalBytes ?? -1) < 0 ? t("pager.calculating") : formatBytes(Number(pager?.totalBytes ?? 0))}
    </span>
  {/if}
  <div class="grow"></div>
  <span class="status-line">{status}</span>
  <span class="webui-build-tag" title={t("pager.buildTagTitle")}>{__WEBUI_BUILD__.slice(0, 10)}</span>
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
