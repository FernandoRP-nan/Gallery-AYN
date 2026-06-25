"""Lista imágenes planas de la carpeta desorden (sugerencias en galería)."""

from __future__ import annotations

from pathlib import Path

from ..core.gallery_paths import scan_images_flat
from ..core.media_organizer import MediaOrganizer


def list_mess_image_paths(folder: Path, max_files: int = 400) -> dict:
    cap = max(20, min(2000, int(max_files)))
    paths = scan_images_flat(folder, MediaOrganizer.IMAGE_EXTENSIONS)
    total = len(paths)
    truncated = total > cap
    if truncated:
        paths = paths[:cap]
    return {
        "paths": [str(p.resolve()) for p in paths],
        "total": total,
        "truncated": truncated,
        "shown": len(paths),
    }
