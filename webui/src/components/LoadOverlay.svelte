<script lang="ts">
  export let message = "";
</script>

<div class="load-overlay" aria-busy="true" aria-live="polite">
  <div class="load-overlay__spinner"></div>
  {#if message}
    <span class="load-overlay__text">{message}</span>
  {/if}
</div>

<style>
  .load-overlay {
    position: fixed;
    inset: 0;
    z-index: 150;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--om-space-3);
    background: rgb(4 6 14 / 0.42);
    pointer-events: all;
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
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--om-text-secondary);
  }

  @keyframes load-overlay-spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
