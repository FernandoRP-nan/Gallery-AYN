"""Similitud puntual respecto a una imagen ancla (panel Desorden)."""

from __future__ import annotations

from pathlib import Path

from .perceptual_hash import compute_ahash, hamming_similarity


def find_similar_paths(
    anchor_path: str | Path,
    candidate_paths: list[str | Path],
    min_similarity: float = 0.82,
    limit: int = 32,
) -> list[dict]:
    """Devuelve candidatos ordenados por similitud con `anchor_path`."""
    min_sim = max(0.5, min(0.98, float(min_similarity)))
    cap = max(1, min(128, int(limit)))
    anchor = Path(anchor_path).resolve()
    anchor_hash = compute_ahash(anchor)
    if anchor_hash is None:
        return []

    anchor_key = str(anchor)
    scored: list[dict] = []
    seen: set[str] = {anchor_key}

    for raw in candidate_paths:
        p = Path(raw).resolve()
        key = str(p)
        if key in seen or not p.is_file():
            continue
        seen.add(key)
        h = compute_ahash(p)
        if h is None:
            continue
        sim = hamming_similarity(anchor_hash, h)
        if sim >= min_sim:
            scored.append({"path": key, "similarity": round(sim, 4)})

    scored.sort(key=lambda x: (-float(x["similarity"]), x["path"].lower()))
    return scored[:cap]
