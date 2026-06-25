/** Punto de referencia para ordenar miniaturas (cursor o centro del tile activo). */
export type ThumbPointerAnchor = { x: number; y: number };

let galleryPointerAnchor: ThumbPointerAnchor | null = null;

export function setGalleryPointerAnchor(x: number, y: number) {
  galleryPointerAnchor = { x, y };
}

export function getGalleryPointerAnchor(): ThumbPointerAnchor | null {
  return galleryPointerAnchor;
}

export type ThumbPriorityOpts = {
  selector: string;
  attrName: string;
  scrollContainer?: HTMLElement | null;
  cursorPath?: string | null;
  pointer?: ThumbPointerAnchor | null;
  /** Orden completo de paths (p. ej. lista de la galería) para ítems fuera del DOM virtual. */
  pathOrder?: string[];
};

function resolveAnchor(
  nodeByPath: Map<string, HTMLElement>,
  opts: ThumbPriorityOpts
): ThumbPointerAnchor {
  const pointer = opts.pointer ?? galleryPointerAnchor;
  if (pointer) return pointer;

  const cursorPath = opts.cursorPath?.trim();
  if (cursorPath && nodeByPath.has(cursorPath)) {
    const r = nodeByPath.get(cursorPath)!.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }

  const scroll = opts.scrollContainer;
  if (scroll) {
    const b = scroll.getBoundingClientRect();
    return { x: b.left + b.width / 2, y: b.top + b.height / 2 };
  }

  return { x: window.innerWidth / 2, y: window.innerHeight / 2 };
}

function isInScrollViewport(
  rect: DOMRect,
  bounds: DOMRect,
  margin = 48
): boolean {
  return (
    rect.bottom > bounds.top - margin &&
    rect.top < bounds.bottom + margin &&
    rect.right > bounds.left - margin &&
    rect.left < bounds.right + margin
  );
}

function indexDistance(path: string, anchorPath: string | null | undefined, pathOrder: string[]): number {
  if (!pathOrder.length) return Number.MAX_SAFE_INTEGER;
  const idx = pathOrder.indexOf(path);
  if (idx < 0) return Number.MAX_SAFE_INTEGER;
  if (!anchorPath) return idx;
  const anchorIdx = pathOrder.indexOf(anchorPath);
  if (anchorIdx < 0) return idx;
  return Math.abs(idx - anchorIdx);
}

/**
 * Ordena paths: primero visibles cerca del cursor, luego resto por proximidad de índice.
 */
export function prioritizeThumbPaths(paths: string[], opts: ThumbPriorityOpts): string[] {
  if (paths.length <= 1) return paths;

  const bounds = (opts.scrollContainer ?? document.documentElement).getBoundingClientRect();

  const nodeByPath = new Map<string, HTMLElement>();
  const scope = opts.scrollContainer ?? document;
  for (const n of scope.querySelectorAll<HTMLElement>(opts.selector)) {
    const p = n.dataset[opts.attrName];
    if (p) nodeByPath.set(p, n);
  }

  const anchor = resolveAnchor(nodeByPath, opts);
  const pathOrder = opts.pathOrder ?? paths;
  const cursorPath = opts.cursorPath?.trim() || null;

  type Scored = { path: string; score: number };
  const scored: Scored[] = paths.map((path) => {
    const el = nodeByPath.get(path);
    if (el) {
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const dist = (cx - anchor.x) ** 2 + (cy - anchor.y) ** 2;
      const visible = isInScrollViewport(r, bounds);
      return { path, score: visible ? dist : dist + 1e12 };
    }
    const idxDist = indexDistance(path, cursorPath, pathOrder);
    return { path, score: 1e12 + idxDist * 1e6 };
  });

  scored.sort((a, b) => a.score - b.score);
  return scored.map((s) => s.path);
}
