"""Hash perceptual (aHash) para agrupar imágenes visualmente similares."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

_AHASH_SIZE = 8
_HASH_BITS = _AHASH_SIZE * _AHASH_SIZE


def compute_ahash(path: str | Path) -> int | None:
    """Hash de 64 bits; None si no se puede leer la imagen."""
    if Image is None:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        with Image.open(p) as im:
            im = im.convert("L").resize((_AHASH_SIZE, _AHASH_SIZE), Image.Resampling.LANCZOS)
            pixels = list(im.getdata())
    except OSError:
        return None
    avg = sum(pixels) / len(pixels)
    bits = 0
    for i, px in enumerate(pixels):
        if px >= avg:
            bits |= 1 << i
    return bits


def hamming_similarity(hash_a: int, hash_b: int) -> float:
    """Similitud 0–1 según bits distintos entre dos hashes."""
    diff = (hash_a ^ hash_b).bit_count()
    return 1.0 - diff / _HASH_BITS
