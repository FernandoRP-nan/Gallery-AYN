"""Utilidades de rutas de archivo reutilizables por la UI."""

from __future__ import annotations

from pathlib import Path


def ensure_unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def ensure_unique_folder_path(parent: Path, name: str) -> Path:
    """Subcarpeta libre bajo parent: name, name (1), name (2)..."""
    base = str(name or "").strip()
    if not base:
        raise ValueError("El nombre de carpeta no puede estar vacío.")
    parent = parent.expanduser().resolve()
    candidate = parent / base
    if not candidate.exists():
        return candidate
    counter = 1
    while True:
        alt = parent / f"{base} ({counter})"
        if not alt.exists():
            return alt
        counter += 1


