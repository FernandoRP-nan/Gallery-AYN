import { derived, writable } from "svelte/store";
import type { TreeFolder } from "./itemTree";

export type FolderFlyoutEntry = {
  id: string;
  node: TreeFolder;
  anchorRect: { top: number; left: number; right: number; bottom: number };
};

export const moveRootHovered = writable(false);
export const folderFlyoutStack = writable<FolderFlyoutEntry[]>([]);

export const moveDestPanelOpen = derived(
  [moveRootHovered, folderFlyoutStack],
  ([root, stack]) => root || stack.length > 0
);

let closeTimer: ReturnType<typeof setTimeout> | null = null;

export function cancelMoveMenuClose() {
  if (closeTimer) {
    clearTimeout(closeTimer);
    closeTimer = null;
  }
}

export function resetMoveFlyoutState() {
  cancelMoveMenuClose();
  moveRootHovered.set(false);
  folderFlyoutStack.set([]);
}

export function setFolderFlyoutDepth(
  depth: number,
  node: TreeFolder,
  anchor: HTMLElement
) {
  cancelMoveMenuClose();
  const r = anchor.getBoundingClientRect();
  folderFlyoutStack.update((stack) => {
    const next = stack.slice(0, depth);
    next.push({
      id: node.id,
      node,
      anchorRect: { top: r.top, left: r.left, right: r.right, bottom: r.bottom },
    });
    return next;
  });
}

export function scheduleTrimFlyoutStack(depth: number) {
  cancelMoveMenuClose();
  closeTimer = setTimeout(() => {
    folderFlyoutStack.update((stack) => stack.slice(0, depth));
    closeTimer = null;
  }, 180);
}

export function scheduleMoveRootClose() {
  cancelMoveMenuClose();
  closeTimer = setTimeout(() => {
    moveRootHovered.set(false);
    closeTimer = null;
  }, 180);
}

export function isMoveMenuElement(el: EventTarget | null): boolean {
  if (!(el instanceof Element)) return false;
  return Boolean(
    el.closest(".dest-move-flyout-fixed") ||
      el.closest(".ctx-menu__submenu--dest-tree") ||
      el.closest(".ctx-menu__submenu-wrap") ||
      el.closest(".dest-move-tree__folder-row")
  );
}

export function onMoveMenuPointerLeave(e: PointerEvent, trimDepth: number) {
  if (isMoveMenuElement(e.relatedTarget)) return;
  scheduleTrimFlyoutStack(trimDepth);
}

export function onMoveRootPointerLeave(e: PointerEvent) {
  if (isMoveMenuElement(e.relatedTarget)) return;
  scheduleMoveRootClose();
}

export function flyoutStyleFor(entry: FolderFlyoutEntry, index: number): string {
  const r = entry.anchorRect;
  const gap = 4;
  const pad = 8;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const fw = 200;
  const fh = Math.min(280, Math.floor(vh * 0.5));

  let left = r.right + gap;
  if (left + fw + pad > vw) left = r.left - fw - gap;
  if (left < pad) left = pad;

  let top = r.top;
  if (top + fh + pad > vh) top = Math.max(pad, vh - fh - pad);
  if (top < pad) top = pad;

  return [
    `left:${Math.round(left)}px`,
    `top:${Math.round(top)}px`,
    `min-width:11rem`,
    `max-height:min(50vh,280px)`,
    `z-index:${150 + index}`,
  ].join(";");
}
