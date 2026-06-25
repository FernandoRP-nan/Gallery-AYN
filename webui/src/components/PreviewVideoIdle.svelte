<script lang="ts">
  import { t } from "../lib/i18n";

  export let posterUrl: string | null = null;
  export let name = "";
  export let preparing = false;
  export let playLocked = false;
  export let statusMessage = "";
  export let compact = false;
  export let onPlay: () => void;

  /** Bloqueo local hasta desmontar (evita doble clic antes del re-render del padre). */
  let pointerLock = false;

  $: busy = playLocked || preparing || pointerLock;

  function handlePointerDown(e: PointerEvent) {
    if (busy) {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    pointerLock = true;
    e.preventDefault();
    e.stopPropagation();
    onPlay();
  }

  function blockIdlePointerWhenBusy(e: PointerEvent) {
    if (!busy) return;
    e.preventDefault();
    e.stopPropagation();
  }
</script>

<div
  class="preview-video-idle"
  class:preview-video-idle--compact={compact}
  class:preview-video-idle--busy={busy}
  role="presentation"
  on:pointerdown|stopPropagation={blockIdlePointerWhenBusy}
>
  {#if posterUrl}
    <img class="preview-video-idle__poster" src={posterUrl} alt={name} decoding="async" />
  {:else}
    <div class="preview-video-idle__placeholder" aria-hidden="true"></div>
  {/if}

  {#if busy}
    <div class="preview-video-idle__overlay" aria-live="polite">
      <div class="preview-video-idle__spinner" aria-hidden="true"></div>
      <p class="preview-video-idle__status">{statusMessage || t("preview.videoStarting")}</p>
    </div>
  {:else}
    <button
      type="button"
      class="preview-video-idle__play om-btn"
      title={t("preview.videoPlayTitle")}
      aria-busy={busy}
      disabled={busy}
      on:pointerdown|stopPropagation={handlePointerDown}
    >
      ▶
    </button>
  {/if}
</div>

<style>
  .preview-video-idle {
    position: relative;
    flex: 1 1 0;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--om-radius-md);
    border: 1px solid var(--om-border-subtle);
    background: rgb(0 0 0 / 0.35);
    overflow: hidden;
  }

  .preview-video-idle--compact {
    flex: 1 1 auto;
    width: 100%;
    height: 100%;
    border: none;
    border-radius: 0;
    background: transparent;
  }

  .preview-video-idle--busy .preview-video-idle__poster,
  .preview-video-idle--busy .preview-video-idle__placeholder {
    filter: brightness(0.55);
  }

  .preview-video-idle__poster,
  .preview-video-idle__placeholder {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
    transition: filter 0.12s ease;
  }

  .preview-video-idle__placeholder {
    background: var(--om-bg-base);
  }

  .preview-video-idle__play {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    min-width: 3.25rem;
    min-height: 3.25rem;
    border-radius: 999px;
    font-size: 1.25rem;
    line-height: 1;
    padding: 0;
    box-shadow: 0 8px 24px rgb(0 0 0 / 0.45);
  }

  .preview-video-idle__play:disabled {
    opacity: 0.55;
    cursor: not-allowed;
    pointer-events: none;
  }

  .preview-video-idle__overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 1rem;
    background: rgb(0 0 0 / 0.42);
    pointer-events: all;
    z-index: 2;
  }

  .preview-video-idle__status {
    margin: 0;
    font-size: 0.82rem;
    line-height: 1.35;
    text-align: center;
    color: var(--om-text-muted, #cbd5e1);
    max-width: 18rem;
  }

  .preview-video-idle__spinner {
    width: 2.25rem;
    height: 2.25rem;
    border-radius: 999px;
    border: 3px solid rgb(255 255 255 / 0.22);
    border-top-color: var(--om-accent, #60a5fa);
    animation: preview-video-spin 0.75s linear infinite;
  }

  @keyframes preview-video-spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
