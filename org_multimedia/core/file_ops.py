"""Operaciones de sistema de archivos (mover, borrar, renombrar)."""

import shutil
from pathlib import Path

def ensure_unique_path(path: Path) -> Path:
    """Si el archivo existe, añade un sufijo numérico."""
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

def safe_move(source: Path, target_dir: Path) -> Path:
    """Mueve un archivo manejando colisiones."""
    target_path = target_dir / source.name
    if source.resolve() == target_path.resolve():
        return target_path
    
    unique_target = ensure_unique_path(target_path)
    shutil.move(str(source), str(unique_target))
    return unique_target

def delete_empty_dirs_recursive(root: Path, exclude: list[Path] | None = None) -> int:
    """Borra directorios vacíos de forma recursiva."""
    deleted = 0
    exclude = exclude or []
    # Usamos rglob("*") y ordenamos por longitud de cadena invertida para procesar hijos antes que padres.
    for directory in sorted(root.rglob("*"), key=lambda d: len(str(d)), reverse=True):
        if not directory.is_dir():
            continue
        if any(directory == ex or _is_inside(directory, ex) for ex in exclude):
            continue
        try:
            # rmdir solo funciona si está vacío.
            directory.rmdir()
            deleted += 1
        except OSError:
            continue
    return deleted

def _is_inside(path: Path, possible_parent: Path) -> bool:
    try:
        path.relative_to(possible_parent)
        return True
    except ValueError:
        return False
