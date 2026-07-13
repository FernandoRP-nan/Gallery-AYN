"""Utilidades para árboles de destinos y marcadores en settings.json."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

KIND_FOLDER = "folder"
KIND_DEST = "dest"
KIND_MARKER = "marker"


def new_folder_id() -> str:
    return uuid.uuid4().hex[:12]


def _as_str(v: Any) -> str:
    return str(v or "").strip()


def _normalize_folder(node: dict) -> dict | None:
    label = _as_str(node.get("label")) or "Carpeta"
    fid = _as_str(node.get("id")) or new_folder_id()
    raw_children = node.get("children")
    children = normalize_tree(raw_children if isinstance(raw_children, list) else [], KIND_DEST)
    return {"kind": KIND_FOLDER, "id": fid, "label": label, "children": children}


def _normalize_dest(node: dict) -> dict | None:
    path = _as_str(node.get("path"))
    if not path:
        return None
    label = _as_str(node.get("label")) or path
    return {"kind": KIND_DEST, "label": label, "path": path}


def _normalize_marker(node: dict) -> dict | None:
    path = _as_str(node.get("path"))
    if not path:
        return None
    label = _as_str(node.get("label")) or path
    return {"kind": KIND_MARKER, "label": label, "path": path}


def normalize_tree(items: list | None, leaf_kind: str) -> list[dict]:
    """Normaliza nodos según el tipo hoja esperado (dest o marker)."""
    if not isinstance(items, list):
        return []
    leaf_fn = _normalize_dest if leaf_kind == KIND_DEST else _normalize_marker
    out: list[dict] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        kind = _as_str(raw.get("kind"))
        if kind == KIND_FOLDER:
            folder = _normalize_folder(raw)
            if folder:
                out.append(folder)
            continue
        # Compatibilidad: entradas planas sin kind
        if leaf_kind == KIND_DEST and ("path" in raw or "folder" in raw or "dir" in raw):
            path = _as_str(raw.get("path") or raw.get("folder") or raw.get("dir"))
            if path:
                label = _as_str(raw.get("label")) or path
                out.append({"kind": KIND_DEST, "label": label, "path": path})
            continue
        if kind == leaf_kind:
            leaf = leaf_fn(raw)
            if leaf:
                out.append(leaf)
    return out


def migrate_flat_destinations(flat: list) -> list[dict]:
    return normalize_tree(flat, KIND_DEST)


def migrate_flat_markers(
    pins: list[str],
    labels: dict[str, str] | None,
) -> list[dict]:
    lbl_map = labels if isinstance(labels, dict) else {}
    out: list[dict] = []
    for raw in pins or []:
        path = _as_str(raw)
        if not path:
            continue
        label = _as_str(lbl_map.get(path)) or path
        out.append({"kind": KIND_MARKER, "label": label, "path": path})
    return out


def flatten_marker_paths(items: list) -> list[str]:
    paths: list[str] = []

    def walk(nodes: list) -> None:
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            kind = _as_str(node.get("kind"))
            if kind == KIND_MARKER:
                p = _as_str(node.get("path"))
                if p and p not in paths:
                    paths.append(p)
            elif kind == KIND_FOLDER:
                walk(node.get("children") if isinstance(node.get("children"), list) else [])

    walk(items if isinstance(items, list) else [])
    return paths


def flatten_dest_paths(items: list) -> list[str]:
    """Rutas planas de destinos (kind=dest) en el árbol."""
    paths: list[str] = []

    def walk(nodes: list) -> None:
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            kind = _as_str(node.get("kind"))
            if kind == KIND_DEST:
                p = _as_str(node.get("path"))
                if p and p not in paths:
                    paths.append(p)
            elif kind == KIND_FOLDER:
                walk(node.get("children") if isinstance(node.get("children"), list) else [])

    walk(items if isinstance(items, list) else [])
    return paths


def _append_child_dirs(
    root_path: str,
    *,
    max_depth: int,
    seen: set[str],
    out: list[str],
) -> None:
    """Añade subcarpetas hasta max_depth bajo root_path."""
    if max_depth <= 0:
        return
    from pathlib import Path

    from .gallery_paths import list_subdirs

    try:
        root = Path(root_path).expanduser().resolve()
    except OSError:
        return
    if not root.is_dir():
        return
    for sub in list_subdirs(root):
        key = str(sub)
        if key not in seen:
            seen.add(key)
            out.append(key)
        _append_child_dirs(key, max_depth=max_depth - 1, seen=seen, out=out)


def collect_warm_paths(
    markers: list,
    destinations: list,
    *,
    recent: list[str] | None = None,
    include_children: bool = True,
    max_depth: int = 2,
) -> list[str]:
    """Unión única: marcadores, destinos, recientes y subcarpetas."""
    out: list[str] = []
    seen: set[str] = set()
    depth = max(0, min(6, int(max_depth or 0)))

    def add_path(raw: str) -> None:
        text = _as_str(raw)
        if not text or text in seen:
            return
        seen.add(text)
        out.append(text)
        if include_children and depth > 0:
            _append_child_dirs(text, max_depth=depth, seen=seen, out=out)

    for p in flatten_marker_paths(markers):
        add_path(p)
    for p in flatten_dest_paths(destinations):
        add_path(p)
    for p in recent or []:
        add_path(str(p))
    return out


def find_folder(items: list, folder_id: str) -> dict | None:
    fid = _as_str(folder_id)
    if not fid:
        return None

    def walk(nodes: list) -> dict | None:
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            if _as_str(node.get("kind")) == KIND_FOLDER:
                if _as_str(node.get("id")) == fid:
                    return node
                found = walk(node.get("children") if isinstance(node.get("children"), list) else [])
                if found:
                    return found
        return None

    return walk(items if isinstance(items, list) else [])


def get_children_list(items: list, parent_id: str | None) -> list[dict]:
    """Devuelve la lista hija editable; None/'' = raíz."""
    pid = _as_str(parent_id)
    if not pid:
        return items if isinstance(items, list) else []
    folder = find_folder(items, pid)
    if not folder:
        return []
    children = folder.get("children")
    if not isinstance(children, list):
        folder["children"] = []
        return folder["children"]
    return children


def folder_exists(items: list, folder_id: str) -> bool:
    return find_folder(items, folder_id) is not None


def remove_folder(items: list, folder_id: str) -> bool:
    """Elimina carpeta y promueve sus hijos al contenedor padre."""
    fid = _as_str(folder_id)
    if not fid:
        return False

    def walk(nodes: list, parent_children: list | None) -> bool:
        for idx, node in enumerate(list(nodes)):
            if not isinstance(node, dict):
                continue
            if _as_str(node.get("kind")) != KIND_FOLDER:
                continue
            if _as_str(node.get("id")) == fid:
                promoted = node.get("children") if isinstance(node.get("children"), list) else []
                nodes.pop(idx)
                for offset, child in enumerate(promoted):
                    nodes.insert(idx + offset, child)
                return True
            children = node.get("children")
            if isinstance(children, list) and walk(children, nodes):
                return True
        return False

    root = items if isinstance(items, list) else []
    return walk(root, None)


def prune_invalid_toolbar_folder(items: list, folder_id: str | None) -> str | None:
    fid = _as_str(folder_id)
    if not fid:
        return None
    return fid if folder_exists(items, fid) else None
