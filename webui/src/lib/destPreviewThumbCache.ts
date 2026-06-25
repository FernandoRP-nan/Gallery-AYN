import type { DestPreviewItem } from "./destPreviewThumbs";

type CachedThumb = {
  thumbDataUrl: string;
  thumbQuality: "lq" | "hq";
};

const byPath = new Map<string, CachedThumb>();

export function getDestPreviewThumb(path: string): CachedThumb | null {
  const key = String(path ?? "").trim();
  return key ? byPath.get(key) ?? null : null;
}

export function setDestPreviewThumb(
  path: string,
  thumbDataUrl: string,
  thumbQuality: "lq" | "hq"
) {
  const key = String(path ?? "").trim();
  const url = String(thumbDataUrl ?? "").trim();
  if (!key || !url) return;
  byPath.set(key, { thumbDataUrl: url, thumbQuality });
}

export function removeDestPreviewThumbs(paths: Iterable<string>) {
  for (const raw of paths) {
    const key = String(raw ?? "").trim();
    if (key) byPath.delete(key);
  }
}

export function renameDestPreviewThumb(oldPath: string, newPath: string) {
  const from = String(oldPath ?? "").trim();
  const to = String(newPath ?? "").trim();
  if (!from || !to || from === to) return;
  const entry = byPath.get(from);
  if (entry) {
    byPath.set(to, entry);
    byPath.delete(from);
  }
}

export function applyCachedDestPreviewThumbs(items: DestPreviewItem[]): DestPreviewItem[] {
  return items.map((it) => {
    const cached = getDestPreviewThumb(it.path);
    if (!cached) return it;
    return {
      ...it,
      thumbDataUrl: cached.thumbDataUrl,
      thumbQuality: cached.thumbQuality,
    };
  });
}

export function clearDestPreviewThumbCache() {
  byPath.clear();
}
