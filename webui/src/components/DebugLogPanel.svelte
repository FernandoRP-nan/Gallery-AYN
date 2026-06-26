<script lang="ts">
  import { t } from "../lib/i18n";
  import {
    clearGalleryDebugLog,
    copyGalleryDebugLog,
    formatGalleryDebugLogText,
    galleryDebugLogEntries,
    galleryDebugLogEnabled,
    setGalleryDebugLogEnabled,
  } from "../lib/galleryDebugLog";

  let collapsed = false;
  let copyOk: boolean | null = null;
  let logEl: HTMLPreElement | null = null;

  $: rows = $galleryDebugLogEntries;

  async function onCopy() {
    copyOk = await copyGalleryDebugLog();
    if (copyOk) setTimeout(() => (copyOk = null), 2000);
  }

  function onClear() {
    clearGalleryDebugLog();
  }

  function onToggleEnabled() {
    setGalleryDebugLogEnabled(!$galleryDebugLogEnabled);
  }

  $: if (logEl && rows.length > 0) {
    requestAnimationFrame(() => {
      if (logEl) logEl.scrollTop = logEl.scrollHeight;
    });
  }
</script>

{#if $galleryDebugLogEnabled}
  <aside class="debug-log" class:debug-log--collapsed={collapsed} aria-label={t("debug.panelAria")}>
    <header class="debug-log__head">
      <strong>{t("debug.panelTitle")}</strong>
      <span class="debug-log__count">{rows.length}</span>
      <div class="debug-log__actions">
        <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={() => (collapsed = !collapsed)}>
          {collapsed ? t("debug.expand") : t("debug.collapse")}
        </button>
        <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={onCopy}>
          {copyOk ? t("debug.copied") : t("debug.copy")}
        </button>
        <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={onClear}>{t("debug.clear")}</button>
        <button type="button" class="om-btn om-btn--ghost om-btn--mini" on:click={onToggleEnabled} title={t("debug.disable")}
          >✕</button
        >
      </div>
    </header>
    {#if !collapsed}
      <pre class="debug-log__body" bind:this={logEl}>{formatGalleryDebugLogText(rows) || t("debug.empty")}</pre>
    {/if}
  </aside>
{/if}

<style>
  .debug-log {
    position: fixed;
    right: 12px;
    bottom: 52px;
    z-index: 42;
    width: min(520px, calc(100vw - 24px));
    max-height: min(42vh, 360px);
    display: flex;
    flex-direction: column;
    border: 1px solid color-mix(in oklab, var(--om-accent) 35%, var(--om-border-default));
    border-radius: var(--om-radius-md);
    background: color-mix(in oklab, var(--om-surface-1) 92%, #000);
    box-shadow: var(--om-shadow-lg);
    font-size: 0.68rem;
    pointer-events: auto;
  }
  .debug-log--collapsed {
    max-height: none;
  }
  .debug-log__head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border-bottom: 1px solid var(--om-border-subtle);
    flex-shrink: 0;
  }
  .debug-log__count {
    font-size: 0.65rem;
    color: var(--om-text-muted);
  }
  .debug-log__actions {
    margin-left: auto;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    justify-content: flex-end;
  }
  .debug-log__body {
    margin: 0;
    padding: 8px;
    overflow: auto;
    flex: 1;
    min-height: 120px;
    max-height: min(36vh, 300px);
    white-space: pre-wrap;
    word-break: break-word;
    font-family: ui-monospace, "Cascadia Code", monospace;
    color: var(--om-text-secondary);
    line-height: 1.35;
  }
</style>
