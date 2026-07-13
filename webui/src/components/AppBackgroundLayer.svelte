<script lang="ts">
  /** Muestra imagen + velo; false cuando está pausado (scroll/modales). */
  export let active = false;
</script>

{#if active}
  <div class="app-bg-stack" aria-hidden="true">
    <div class="app-bg-stack__image"></div>
    <div class="app-bg-stack__scrim"></div>
  </div>
{/if}
