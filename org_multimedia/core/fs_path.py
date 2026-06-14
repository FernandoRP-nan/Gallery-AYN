"""Resolución de rutas del sistema con acentos y variantes Unicode (NFC/NFD)."""

from __future__ import annotations

import os
import unicodedata
import urllib.parse
from pathlib import Path


def _expand_raw_path(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    if s.lower().startswith("file:"):
        s = urllib.parse.unquote(urllib.parse.urlparse(s).path)
    if "%" in s:
        s = urllib.parse.unquote(s)
    s = os.path.expandvars(os.path.expanduser(s))
    return unicodedata.normalize("NFC", s)


def repair_mojibake_path(raw: str) -> str:
    """UTF-8 mal interpretado como Latin-1 (p. ej. ImÃ¡genes → Imágenes)."""
    s = (raw or "").strip()
    if not s:
        return s
    try:
        fixed = s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return unicodedata.normalize("NFC", s)
    return unicodedata.normalize("NFC", fixed)


def normalize_path_string(raw: str) -> str:
    """Normaliza una ruta recibida del bridge JS antes de usarla."""
    expanded = _expand_raw_path(raw)
    if not expanded:
        return expanded
    repaired = repair_mojibake_path(expanded)
    if repaired != expanded:
        try:
            if Path(repaired).exists() or not Path(expanded).exists():
                return repaired
        except OSError:
            return repaired
    return expanded


def _path_names_match(a: str, b: str) -> bool:
    if a == b:
        return True
    a_strip, b_strip = a.strip(), b.strip()
    if a_strip == b_strip:
        return True
    for form in ("NFC", "NFD"):
        if unicodedata.normalize(form, a_strip) == unicodedata.normalize(form, b_strip):
            return True
    return False


def _resolve_existing_child(parent: Path, name: str) -> Path | None:
    if not parent.is_dir() or not name:
        return None
    try:
        for child in parent.iterdir():
            if child.is_dir() and _path_names_match(child.name, name):
                return child.resolve()
    except OSError:
        return None
    return None


def _path_variants(raw: str) -> list[str]:
    expanded = normalize_path_string(raw)
    if not expanded:
        return []
    variants: list[str] = [expanded]
    nfd = unicodedata.normalize("NFD", expanded)
    if nfd not in variants:
        variants.append(nfd)
    repaired = repair_mojibake_path(raw)
    if repaired and repaired not in variants:
        variants.append(repaired)
    return variants


def _resolve_dir_segments(expanded: str) -> Path | None:
    parts = Path(expanded).parts
    if not parts:
        return None

    current = Path(parts[0])
    for part in parts[1:]:
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        direct = current / part
        if direct.is_dir():
            current = direct
            continue
        matched = _resolve_existing_child(current, part)
        if matched is None:
            return None
        current = matched

    try:
        resolved = current.resolve()
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_dir() else None


def resolve_dir_path(raw: str) -> Path:
    """Carpeta existente: tolera file://, % encoding, NFC/NFD y mojibake."""
    if not (raw or "").strip():
        raise ValueError("Ruta vacía")

    for candidate in _path_variants(raw):
        resolved = _resolve_dir_segments(candidate)
        if resolved is not None:
            return resolved

    raise ValueError(f"No existe o no es carpeta: {raw}")


def resolve_file_path(raw: str) -> Path:
    """Archivo existente con la misma tolerancia Unicode que resolve_dir_path."""
    if not (raw or "").strip():
        raise ValueError("Ruta vacía")

    for candidate in _path_variants(raw):
        parts = Path(candidate).parts
        if not parts:
            continue
        parent = Path(candidate).parent
        name = Path(candidate).name
        direct = Path(candidate)
        if direct.is_file():
            return direct.resolve()
        if parent.is_dir() and name:
            try:
                for child in parent.iterdir():
                    if child.is_file() and _path_names_match(child.name, name):
                        return child.resolve()
            except OSError:
                pass

    raise ValueError(f"Archivo no encontrado: {raw}")
