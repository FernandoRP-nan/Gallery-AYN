<script lang="ts">
  /** Muestra imagen + velo. */
  export let active = false;
  export let imageUrl = "";
</script>

<div class="app-bg-stack" class:app-bg-stack--off={!active} aria-hidden="true">
  {#if imageUrl}
    <img
      class="app-bg-stack__image"
      src={imageUrl}
      alt=""
      decoding="async"
      draggable="false"
    />
  {/if}
  <div class="app-bg-stack__scrim"></div>
</div>
