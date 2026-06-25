"""API bridge para árbol de marcadores (rutas ancladas)."""

from __future__ import annotations

from pathlib import Path

from ..core.fs_path import resolve_dir_path
from ..core.item_tree import (
    KIND_MARKER,
    find_folder,
    flatten_marker_paths,
    get_children_list,
    migrate_flat_markers,
    new_folder_id,
    normalize_tree,
    prune_invalid_toolbar_folder,
    remove_folder,
)
from ..core.settings import save_app_settings


class MarkersBridgeMixin:
    def _markers_tree(self) -> list:
        raw = self.settings.get("marker_tree")
        if isinstance(raw, list) and raw:
            tree = normalize_tree(raw, KIND_MARKER)
        else:
            pins = self.settings.get("gallery_pinned_folders")
            labels = self.settings.get("web_pinned_folder_labels")
            tree = migrate_flat_markers(
                pins if isinstance(pins, list) else [],
                labels if isinstance(labels, dict) else {},
            )
            self.settings["marker_tree"] = tree
        return tree

    def _sync_legacy_pins(self, tree: list) -> None:
        """Mantiene gallery_pinned_folders plano para compatibilidad."""
        self.settings["gallery_pinned_folders"] = flatten_marker_paths(tree)[:40]
        labels: dict[str, str] = {}
        for path in self.settings["gallery_pinned_folders"]:
            labels[path] = self._marker_label_for_path(tree, path)
        self.settings["web_pinned_folder_labels"] = labels

    def _marker_label_for_path(self, tree: list, path: str) -> str:
        target = str(path or "").strip()

        def walk(nodes: list) -> str:
            for node in nodes or []:
                if not isinstance(node, dict):
                    continue
                if node.get("kind") == KIND_MARKER and str(node.get("path", "")) == target:
                    return str(node.get("label") or target)
                if node.get("kind") == "folder":
                    found = walk(node.get("children") if isinstance(node.get("children"), list) else [])
                    if found:
                        return found
            return target

        return walk(tree if isinstance(tree, list) else [])

    def _markers_payload(self) -> dict:
        tree = self._markers_tree()
        toolbar_id = prune_invalid_toolbar_folder(
            tree, self.settings.get("web_marker_toolbar_folder_id")
        )
        if toolbar_id != self.settings.get("web_marker_toolbar_folder_id"):
            if toolbar_id:
                self.settings["web_marker_toolbar_folder_id"] = toolbar_id
            else:
                self.settings.pop("web_marker_toolbar_folder_id", None)
        return {
            "markers": tree,
            "toolbarFolderId": toolbar_id or "",
            "pinnedFolders": flatten_marker_paths(tree),
        }

    def markers_get(self) -> dict:
        return self._markers_payload()

    def markers_save_tree(self, tree: list) -> dict:
        normalized = normalize_tree(tree if isinstance(tree, list) else [], KIND_MARKER)
        self.settings["marker_tree"] = normalized
        self._sync_legacy_pins(normalized)
        save_app_settings(self.settings)
        return self._markers_payload()

    def markers_set_toolbar_folder(self, folder_id: str = "") -> dict:
        fid = str(folder_id or "").strip()
        tree = self._markers_tree()
        if fid and not find_folder(tree, fid):
            fid = ""
        if fid:
            self.settings["web_marker_toolbar_folder_id"] = fid
        else:
            self.settings.pop("web_marker_toolbar_folder_id", None)
        save_app_settings(self.settings)
        return self._markers_payload()

    def markers_add(self, path: str, label: str = "", parent_id: str = "") -> dict:
        p = str(resolve_dir_path(path))
        label = (label or "").strip() or Path(p).name
        tree = self._markers_tree()
        container = get_children_list(tree, str(parent_id or "").strip() or None)
        for x in container:
            if isinstance(x, dict) and x.get("kind") == KIND_MARKER and str(x.get("path", "")) == p:
                return self._markers_payload()
        container.insert(0, {"kind": KIND_MARKER, "label": label, "path": p})
        self.settings["marker_tree"] = tree
        self._sync_legacy_pins(tree)
        save_app_settings(self.settings)
        return self._markers_payload()

    def markers_remove(self, parent_id: str, idx: int) -> dict:
        tree = self._markers_tree()
        container = get_children_list(tree, str(parent_id or "").strip() or None)
        if 0 <= int(idx) < len(container):
            container.pop(int(idx))
            self.settings["marker_tree"] = tree
            self._sync_legacy_pins(tree)
            save_app_settings(self.settings)
        return self._markers_payload()

    def markers_edit(self, parent_id: str, idx: int, label: str, path: str) -> dict:
        tree = self._markers_tree()
        container = get_children_list(tree, str(parent_id or "").strip() or None)
        i = int(idx)
        if 0 <= i < len(container):
            node = container[i]
            if isinstance(node, dict) and node.get("kind") == KIND_MARKER:
                p = str(resolve_dir_path(path))
                label = (label or "").strip() or Path(p).name
                container[i] = {"kind": KIND_MARKER, "label": label, "path": p}
                self.settings["marker_tree"] = tree
                self._sync_legacy_pins(tree)
                save_app_settings(self.settings)
        return self._markers_payload()

    def markers_reorder(self, parent_id: str, from_idx: int, to_idx: int) -> dict:
        tree = self._markers_tree()
        container = get_children_list(tree, str(parent_id or "").strip() or None)
        n = len(container)
        fi, ti = int(from_idx), int(to_idx)
        if n <= 1 or not (0 <= fi < n and 0 <= ti < n) or fi == ti:
            return self._markers_payload()
        item = container.pop(fi)
        container.insert(ti, item)
        self.settings["marker_tree"] = tree
        self._sync_legacy_pins(tree)
        save_app_settings(self.settings)
        return self._markers_payload()

    def markers_folder_add(self, label: str, parent_id: str = "") -> dict:
        label = (label or "").strip() or "Carpeta"
        tree = self._markers_tree()
        container = get_children_list(tree, str(parent_id or "").strip() or None)
        folder = {"kind": "folder", "id": new_folder_id(), "label": label, "children": []}
        container.append(folder)
        self.settings["marker_tree"] = tree
        self._sync_legacy_pins(tree)
        save_app_settings(self.settings)
        payload = self._markers_payload()
        payload["folderId"] = folder["id"]
        return payload

    def markers_folder_edit(self, folder_id: str, label: str) -> dict:
        tree = self._markers_tree()
        folder = find_folder(tree, str(folder_id or "").strip())
        if folder:
            folder["label"] = (label or "").strip() or folder.get("label") or "Carpeta"
            self.settings["marker_tree"] = tree
            save_app_settings(self.settings)
        return self._markers_payload()

    def markers_folder_remove(self, folder_id: str) -> dict:
        tree = self._markers_tree()
        fid = str(folder_id or "").strip()
        if fid and remove_folder(tree, fid):
            if self.settings.get("web_marker_toolbar_folder_id") == fid:
                self.settings.pop("web_marker_toolbar_folder_id", None)
            self.settings["marker_tree"] = tree
            self._sync_legacy_pins(tree)
            save_app_settings(self.settings)
        return self._markers_payload()

    def gallery_pin_folder(self, raw_path: str) -> dict:
        return self.markers_add(raw_path, "", "")

    def gallery_unpin_folder(self, raw_path: str) -> dict:
        p = str(resolve_dir_path(raw_path))
        tree = self._markers_tree()

        def remove_path(nodes: list) -> bool:
            for idx, node in enumerate(list(nodes)):
                if not isinstance(node, dict):
                    continue
                if node.get("kind") == KIND_MARKER and str(node.get("path", "")) == p:
                    nodes.pop(idx)
                    return True
                if node.get("kind") == "folder":
                    children = node.get("children")
                    if isinstance(children, list) and remove_path(children):
                        return True
            return False

        if remove_path(tree):
            self.settings["marker_tree"] = tree
            self._sync_legacy_pins(tree)
            save_app_settings(self.settings)
        return {"pinnedFolders": flatten_marker_paths(tree)}
