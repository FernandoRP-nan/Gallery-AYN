import { tick } from "svelte";

/** Espera a que haya tiles en el DOM antes de hidratar HQ (masonry / cambio de vista). */
export async function waitForGalleryTilesReady(
  scrollEl: HTMLElement | null,
  minTiles = 1,
  maxMs = 2500
): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    await tick();
    await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    if (!scrollEl) return;
    const count = scrollEl.querySelectorAll("[data-item-path].tile, .tile[data-item-path]").length;
    if (count >= minTiles) return;
  }
}
