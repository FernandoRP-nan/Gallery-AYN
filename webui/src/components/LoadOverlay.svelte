<script lang="ts">
  import { t } from "../lib/i18n";

  export let message = "";
  export let detail = "";
  export let done: number | null = null;
  export let total: number | null = null;

  $: showProgress =
    total != null && total > 0 && done != null && Number.isFinite(done) && Number.isFinite(total);
  $: progressPct = showProgress ? Math.max(0, Math.min(100, Math.round((done! / total!) * 100))) : 0;
</script>

<div class="load-overlay" aria-busy="true" aria-live="polite">
  <div class="load-overlay__spinner"></div>
  {#if message}
    <span class="load-overlay__text">{message}</span>
  {/if}
  {#if detail}
    <span class="load-overlay__detail">{detail}</span>
  {/if}
  {#if showProgress}
    <div
      class="load-overlay__progress"
      role="progressbar"
      aria-valuemin="0"
      aria-valuemax={total}
      aria-valuenow={done}
      aria-label={t("loadOverlay.progressAria")}
    >
      <div class="load-overlay__progress-fill" style={`width:${progressPct}%`}></div>
    </div>
    <span class="load-overlay__progress-label">
      {t("loadOverlay.progressCount").replace("{done}", String(done)).replace("{total}", String(total))}
    </span>
  {/if}
</div>

<style>
  .load-overlay {
    position: fixed;
    inset: 0;
    z-index: var(--om-z-load);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--om-space-2);
    background: rgb(4 6 14 / 0.42);
    pointer-events: all;
    padding: var(--om-space-4);
    text-align: center;
  }

  .load-overlay__spinner {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: 3px solid rgb(255 255 255 / 0.18);
    border-top-color: var(--om-accent);
    animation: load-overlay-spin 0.7s linear infinite;
  }

  .load-overlay__text {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--om-text-secondary);
    max-width: min(92vw, 28rem);
  }

  .load-overlay__detail {
    font-size: 0.75rem;
    font-weight: 500;
    color: color-mix(in oklab, var(--om-text-muted) 88%, transparent);
    max-width: min(92vw, 32rem);
    word-break: break-word;
    line-height: 1.35;
  }

  .load-overlay__progress {
    width: min(280px, 72vw);
    height: 6px;
    border-radius: 999px;
    background: rgb(255 255 255 / 0.12);
    overflow: hidden;
    margin-top: var(--om-space-1);
  }

  .load-overlay__progress-fill {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--om-accent), color-mix(in oklab, var(--om-accent) 65%, white));
    transition: width 0.25s ease;
  }

  .load-overlay__progress-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--om-text-muted);
  }

  @keyframes load-overlay-spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
