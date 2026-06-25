<script lang="ts">
  import { t } from "../lib/i18n";

  export let posterUrl: string | null = null;
  export let name = "";
  export let preparing = false;
  export let compact = false;
  export let onPlay: () => void;
</script>

<div class="preview-video-idle" class:preview-video-idle--compact={compact}>
  {#if posterUrl}
    <img class="preview-video-idle__poster" src={posterUrl} alt={name} decoding="async" />
  {:else}
    <div class="preview-video-idle__placeholder" aria-hidden="true"></div>
  {/if}
  <button
    type="button"
    class="preview-video-idle__play om-btn"
    title={t("preview.videoPlayTitle")}
    disabled={preparing}
    on:click|stopPropagation={onPlay}
  >
    {preparing ? "…" : "▶"}
  </button>
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

  .preview-video-idle__poster,
  .preview-video-idle__placeholder {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
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
</style>
