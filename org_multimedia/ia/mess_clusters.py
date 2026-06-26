"""Agrupa imágenes por similitud visual (aHash)."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable

from ..core.gallery_paths import scan_images_flat
from ..core.media_organizer import MediaOrganizer
from .perceptual_hash import compute_ahash, hamming_similarity

MAX_MESS_FILES = 400


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def cluster_paths_list(
    paths: list[Path],
    min_similarity: float = 0.82,
    progress: Callable[[int, int, str], None] | None = None,
    cancel_event=None,
) -> dict:
    """Agrupa una lista de imágenes ya recopiladas."""
    min_sim = max(0.5, min(0.98, float(min_similarity)))
    resolved = [p.resolve() for p in paths if p.is_file()]
    total = len(resolved)
    if total == 0:
        return {
            "cancelled": False,
            "clusters": [],
            "totalFiles": 0,
            "truncated": False,
            "clusterCount": 0,
            "multiClusterCount": 0,
        }

    hashes: list[int | None] = []
    valid_idx: list[int] = []

    for i, p in enumerate(resolved):
        if cancel_event is not None and cancel_event.is_set():
            return {"cancelled": True, "clusters": [], "totalFiles": total, "truncated": False}
        if progress:
            progress(i + 1, total, f"Analizando {p.name}")
        h = compute_ahash(p)
        hashes.append(h)
        if h is not None:
            valid_idx.append(i)

    uf = _UnionFind(total)
    n_valid = len(valid_idx)
    for ai in range(n_valid):
        if cancel_event is not None and cancel_event.is_set():
            return {"cancelled": True, "clusters": [], "totalFiles": total, "truncated": False}
        i = valid_idx[ai]
        hi = hashes[i]
        if hi is None:
            continue
        for bi in range(ai + 1, n_valid):
            j = valid_idx[bi]
            hj = hashes[j]
            if hj is None:
                continue
            if hamming_similarity(hi, hj) >= min_sim:
                uf.union(i, j)

    groups: dict[int, list[str]] = defaultdict(list)
    for i, p in enumerate(resolved):
        groups[uf.find(i)].append(str(p))

    clusters_raw = [g for g in groups.values() if g]
    clusters_raw.sort(key=lambda g: (-len(g), g[0].lower()))

    clusters = [
        {"id": f"c{idx}", "paths": group, "count": len(group)}
        for idx, group in enumerate(clusters_raw)
    ]

    return {
        "cancelled": False,
        "clusters": clusters,
        "totalFiles": total,
        "truncated": False,
        "clusterCount": len(clusters),
        "multiClusterCount": sum(1 for c in clusters if c["count"] > 1),
    }


def cluster_image_paths(
    folder: Path,
    min_similarity: float = 0.82,
    progress: Callable[[int, int, str], None] | None = None,
    cancel_event=None,
    max_files: int | None = None,
) -> dict:
    """Escanea imágenes planas en `folder` y devuelve clusters."""
    cap = max(50, min(2000, int(max_files if max_files is not None else MAX_MESS_FILES)))
    paths = scan_images_flat(folder, MediaOrganizer.IMAGE_EXTENSIONS)
    truncated = len(paths) > cap
    if truncated:
        paths = paths[:cap]
    out = cluster_paths_list(paths, min_similarity, progress, cancel_event)
    out["truncated"] = truncated
    return out
