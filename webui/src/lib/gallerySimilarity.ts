import type { GalleryItem } from "./api";

export type SimilarityCluster = {
  id: string;
  count: number;
  paths: string[];
};

const VIDEO_EXT = new Set([
  ".mp4",
  ".mkv",
  ".avi",
  ".mov",
  ".webm",
  ".m4v",
  ".wmv",
  ".flv",
  ".mpeg",
  ".mpg",
]);

export function mediaKindFromPath(path: string): "image" | "video" {
  const dot = path.lastIndexOf(".");
  if (dot < 0) return "image";
  return VIDEO_EXT.has(path.slice(dot).toLowerCase()) ? "video" : "image";
}

export function pathBaseName(p: string): string {
  const n = p.replace(/\\/g, "/").split("/").pop();
  return n || p;
}

export function clusterPaths(c: SimilarityCluster): string[] {
  return (c.paths ?? []).filter(Boolean);
}

export function clusterCount(c: SimilarityCluster): number {
  return c.count || clusterPaths(c).length;
}

export function normalizeSimilarityCluster(raw: Record<string, unknown>): SimilarityCluster {
  const paths = Array.isArray(raw.paths) ? (raw.paths as string[]).filter(Boolean) : [];
  return {
    id: String(raw.id ?? `c-${paths[0] ?? "empty"}`),
    count: Number(raw.count ?? paths.length),
    paths,
  };
}

export function filterVisibleClusters(clusters: SimilarityCluster[], hideSingletons: boolean): SimilarityCluster[] {
  return hideSingletons ? clusters.filter((c) => clusterCount(c) > 1) : clusters;
}

/** Convierte clusters en ítems de galería (secciones + medios). */
export function clustersToGalleryItems(clusters: SimilarityCluster[], hideSingletons = true): GalleryItem[] {
  const items: GalleryItem[] = [];
  for (const c of filterVisibleClusters(clusters, hideSingletons)) {
    const paths = clusterPaths(c);
    if (!paths.length) continue;
    items.push({
      kind: "section",
      name: `Grupo · ${paths.length}`,
      path: `section:similarity:${c.id}`,
      sectionFolder: c.id,
    });
    for (const p of paths) {
      items.push({
        kind: mediaKindFromPath(p),
        name: pathBaseName(p),
        path: p,
      });
    }
  }
  return items;
}

export function movePathBetweenClusters(
  clusters: SimilarityCluster[],
  path: string,
  fromId: string,
  toId: string
): SimilarityCluster[] {
  if (!path || fromId === toId) return clusters;
  const next: SimilarityCluster[] = [];
  for (const c of clusters) {
    if (c.id === fromId) {
      const paths = clusterPaths(c).filter((p) => p !== path);
      if (paths.length) next.push({ ...c, paths, count: paths.length });
    } else if (c.id === toId) {
      const paths = [...clusterPaths(c), path];
      next.push({ ...c, paths, count: paths.length });
    } else {
      next.push(c);
    }
  }
  return next;
}

export function findClusterIdForPath(clusters: SimilarityCluster[], path: string): string | null {
  for (const c of clusters) {
    if (clusterPaths(c).includes(path)) return c.id;
  }
  return null;
}

export function allPathsFromClusters(clusters: SimilarityCluster[]): string[] {
  return clusters.flatMap((c) => clusterPaths(c));
}

export function isSimilaritySectionFolder(sectionFolder: string | undefined): boolean {
  return Boolean(sectionFolder && !sectionFolder.includes("/") && !sectionFolder.includes("\\"));
}
