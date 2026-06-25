<script lang="ts">
  /** Vista previa lateral: placeholder (miniatura) → imagen completa sin parpadeo. */
  export let placeholderUrl: string | null = null;
  export let fullUrl: string | null = null;
  export let alt = "";

  let fullDecoded = false;
  let trackedFull = "";

  $: if (fullUrl !== trackedFull) {
    trackedFull = fullUrl ?? "";
    fullDecoded = false;
  }

  function onFullLoad() {
    fullDecoded = true;
  }
</script>

<div class="preview-image-stack">
  {#if placeholderUrl && (!fullUrl || !fullDecoded || placeholderUrl !== fullUrl)}
    <img
      class="preview-image-stack__ph preview__img"
      src={placeholderUrl}
      {alt}
      decoding="async"
    />
  {/if}
  {#if fullUrl}
    <img
      class="preview-image-stack__full preview__img"
      class:preview-image-stack__full--visible={fullDecoded}
      src={fullUrl}
      {alt}
      decoding="async"
      on:load={onFullLoad}
    />
  {/if}
</div>

<style>
  .preview-image-stack {
    position: relative;
    width: 100%;
    flex: 1;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .preview-image-stack :global(.preview__img) {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }

  .preview-image-stack__ph {
    opacity: 1;
  }

  .preview-image-stack__full {
    position: absolute;
    inset: 0;
    margin: auto;
    width: auto;
    height: auto;
    max-width: 100%;
    max-height: 100%;
    opacity: 0;
    transition: opacity 0.22s ease;
  }

  .preview-image-stack__full--visible {
    opacity: 1;
  }
</style>
