<script lang="ts">
  /** 0–100 mientras transcodifica; null solo si no aplica. */
  export let progress: number | null = 0;

  $: pct = progress === null ? 0 : Math.min(100, Math.max(0, Math.round(progress)));
  $: fillWidth = `${pct}%`;
</script>

<div class="video-transcode-overlay" aria-live="polite" aria-busy="true">
  <div
    class="video-transcode-overlay__panel"
    role="progressbar"
    aria-valuemin="0"
    aria-valuemax="100"
    aria-valuenow={pct}
  >
    <div class="video-transcode-overlay__track">
      <div class="video-transcode-overlay__fill" style={`width:${fillWidth}`}></div>
    </div>
    <span class="video-transcode-overlay__pct">{pct}%</span>
  </div>
</div>

<style>
  .video-transcode-overlay {
    position: absolute;
    inset: 0;
    z-index: 4;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.25rem;
    background: rgb(0 0 0 / 0.55);
    pointer-events: none;
  }

  .video-transcode-overlay__panel {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
    width: min(22rem, 90%);
  }

  .video-transcode-overlay__track {
    width: 100%;
    height: 0.55rem;
    border-radius: 999px;
    background: rgb(255 255 255 / 0.14);
    overflow: hidden;
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.1);
  }

  .video-transcode-overlay__fill {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, rgb(124 140 255 / 0.98), rgb(94 228 212 / 0.92));
    transition: width 0.35s ease;
  }

  .video-transcode-overlay__pct {
    align-self: center;
    font-size: 1rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.05em;
    color: var(--om-text-primary, #f1f5f9);
  }
</style>
