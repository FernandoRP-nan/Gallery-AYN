<script lang="ts">
  import { onDestroy } from "svelte";
  import { resolveBgDisplayUrl } from "../lib/bgBlurBitmap";

  /** Muestra imagen + velo. */
  export let active = false;
  export let imageUrl = "";
  export let blurPx = 0;

  let displayUrl = "";
  let resolveGen = 0;
  let blurDebounce: ReturnType<typeof setTimeout> | null = null;
  let lastImageUrl = "";

  async function applyDisplayUrl(src: string, blur: number): Promise<void> {
    if (!src || !active) {
      displayUrl = "";
      return;
    }
    const gen = ++resolveGen;
    const resolved = await resolveBgDisplayUrl(src, blur);
    if (gen === resolveGen) displayUrl = resolved;
  }

  function queueDisplayUrl(src: string, blur: number, immediate: boolean): void {
    if (blurDebounce !== null) {
      clearTimeout(blurDebounce);
      blurDebounce = null;
    }
    if (!src || !active) {
      resolveGen++;
      displayUrl = "";
      return;
    }
    if (immediate) {
      void applyDisplayUrl(src, blur);
      return;
    }
    blurDebounce = setTimeout(() => {
      blurDebounce = null;
      void applyDisplayUrl(src, blur);
    }, 140);
  }

  $: {
    const src = active && imageUrl ? imageUrl : "";
    const blur = Math.max(0, Math.min(24, Math.round(Number(blurPx) || 0)));
    const imageChanged = src !== lastImageUrl;
    lastImageUrl = src;
    queueDisplayUrl(src, blur, imageChanged || blur <= 0);
  }

  onDestroy(() => {
    if (blurDebounce !== null) clearTimeout(blurDebounce);
  });
</script>

<div class="app-bg-stack" class:app-bg-stack--off={!active} aria-hidden="true">
  {#if imageUrl}
    <img
      class="app-bg-stack__image"
      src={displayUrl || imageUrl}
      alt=""
      decoding="async"
      draggable="false"
    />
  {/if}
  <div class="app-bg-stack__scrim"></div>
</div>
