#!/usr/bin/env python3
"""
Organizador multimedia cronologico.

Permite seleccionar una carpeta del sistema y reorganiza todo su contenido:
- Imagenes y videos -> Organizado/<Anio>/<Mes>/
- Otros archivos -> PendientesRevision/

Compatible con Fedora KDE al ejecutarse con Python 3 y tkinter.
"""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import hashlib
import json
import os
import queue
import re
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    from PIL import Image, ImageOps, ImageTk

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False
    Image = None  # type: ignore[misc, assignment]
    ImageOps = None  # type: ignore[misc, assignment]
    ImageTk = None  # type: ignore[misc, assignment]


@dataclass
class OrganizeStats:
    moved_media: int = 0
    moved_cbz: int = 0
    moved_other: int = 0
    deleted_duplicate_images: int = 0
    grouped_similar_images: int = 0
    deleted_dirs: int = 0
    errors: int = 0


class MediaOrganizer:
    """Organiza archivos multimedia por fecha en una estructura cronologica."""

    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".tif",
        ".tiff",
        ".heic",
        ".avif",
        ".svg",
    }
    VIDEO_EXTENSIONS = {
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".mpeg",
        ".mpg",
        ".3gp",
    }
    DOCUMENT_EXTENSIONS = {
        ".txt",
        ".md",
        ".rtf",
        ".doc",
        ".docx",
        ".odt",
        ".pdf",
        ".xls",
        ".xlsx",
        ".ods",
        ".ppt",
        ".pptx",
        ".odp",
        ".csv",
        ".epub",
    }
    INSTALLER_EXTENSIONS = {
        ".rpm",
        ".deb",
        ".pkg",
        ".apk",
        ".appimage",
        ".msi",
        ".exe",
        ".sh",
        ".run",
    }
    COMPRESSED_EXTENSIONS = {
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".tgz",
        ".tbz2",
        ".txz",
    }
    EXECUTABLE_EXTENSIONS = {
        ".bin",
        ".py",
        ".pl",
        ".rb",
        ".jar",
    }
    DATA_EXTENSIONS = {
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".ini",
        ".cfg",
        ".conf",
        ".sql",
        ".db",
        ".sqlite",
        ".sqlite3",
    }

    def __init__(
        self,
        source_root: Path,
        include_organized_scan: bool = False,
        include_comics_scan: bool = False,
        include_pending_scan: bool = False,
        remove_duplicate_images: bool = False,
        group_similar_images: bool = False,
        max_workers: int | None = None,
    ) -> None:
        self.source_root = source_root.resolve()
        self.target_media_root = self.source_root / "Organizado"
        self.target_comics_root = self.source_root / "ComicsCBZ"
        self.target_other_root = self.source_root / "PendientesRevision"
        self.include_organized_scan = include_organized_scan
        self.include_comics_scan = include_comics_scan
        self.include_pending_scan = include_pending_scan
        self.remove_duplicate_images = remove_duplicate_images
        self.group_similar_images = group_similar_images
        self.max_workers = max_workers or max(4, min(32, (os.cpu_count() or 4) * 4))
        self.stats = OrganizeStats()
        self.cancel_requested = False
        self.move_lock = threading.Lock()

    def organize(self, progress_callback=None, cancel_event: threading.Event | None = None) -> OrganizeStats:
        self._validate_source()
        self.target_media_root.mkdir(parents=True, exist_ok=True)
        self.target_comics_root.mkdir(parents=True, exist_ok=True)
        self.target_other_root.mkdir(parents=True, exist_ok=True)

        files = []
        self._collect_files_recursive(self.source_root, files)
        total_files = len(files)

        if progress_callback:
            progress_callback(0, total_files, "Preparando...")

        processed = 0
        pending_files = list(files)
        futures_map = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while pending_files or futures_map:
                if cancel_event and cancel_event.is_set():
                    self.cancel_requested = True
                    pending_files.clear()

                while pending_files and len(futures_map) < self.max_workers:
                    file_path = pending_files.pop()
                    future = executor.submit(self._process_single_file, file_path, cancel_event)
                    futures_map[future] = file_path

                if not futures_map:
                    break

                done, _ = wait(futures_map.keys(), return_when=FIRST_COMPLETED)
                for future in done:
                    file_path = futures_map.pop(future)
                    processed += 1
                    try:
                        result = future.result()
                        if result == "media":
                            self.stats.moved_media += 1
                        elif result == "cbz":
                            self.stats.moved_cbz += 1
                        elif result == "other":
                            self.stats.moved_other += 1
                        elif result == "cancelled":
                            self.cancel_requested = True
                    except Exception:
                        self.stats.errors += 1
                    finally:
                        if progress_callback:
                            progress_callback(processed, total_files, f"Procesando: {file_path.name}")

        if not self.cancel_requested and self.remove_duplicate_images:
            if progress_callback:
                progress_callback(processed, total_files, "Postproceso: buscando imagenes duplicadas...")
            self.stats.deleted_duplicate_images = self._remove_duplicate_images(cancel_event)

        if not self.cancel_requested and self.group_similar_images:
            if progress_callback:
                progress_callback(processed, total_files, "Postproceso: agrupando imagenes similares...")
            self.stats.grouped_similar_images = self._group_similar_named_images(cancel_event)

        self.stats.deleted_dirs = self._delete_empty_legacy_dirs()
        return self.stats

    def _process_single_file(self, file_path: Path, cancel_event: threading.Event | None) -> str:
        if cancel_event and cancel_event.is_set():
            return "cancelled"

        if self._is_media(file_path):
            target_dir = self._build_media_target_by_date(file_path)
            self._move_with_collision_handling(file_path, target_dir)
            return "media"
        if self._is_cbz(file_path):
            target_dir = self._build_cbz_target_by_series(file_path)
            self._move_with_collision_handling(file_path, target_dir)
            return "cbz"

        target_dir = self._build_other_target_by_type(file_path)
        self._move_with_collision_handling(file_path, target_dir)
        return "other"

    def _validate_source(self) -> None:
        if not self.source_root.exists() or not self.source_root.is_dir():
            raise ValueError("La ruta seleccionada no existe o no es una carpeta valida.")

    def _collect_files_recursive(self, current_path: Path, files: list[Path]) -> None:
        # Recursividad explicita para recorrer toda la jerarquia.
        for entry in current_path.iterdir():
            if entry == self.target_comics_root and not self.include_comics_scan:
                continue
            if entry == self.target_other_root and not self.include_pending_scan:
                continue
            if entry == self.target_media_root and not self.include_organized_scan:
                continue
            if entry.is_file():
                files.append(entry)
            elif entry.is_dir():
                self._collect_files_recursive(entry, files)

    def _is_media(self, file_path: Path) -> bool:
        ext = file_path.suffix.lower()
        return ext in self.IMAGE_EXTENSIONS or ext in self.VIDEO_EXTENSIONS

    @staticmethod
    def _is_cbz(file_path: Path) -> bool:
        return file_path.suffix.lower() == ".cbz"

    def _build_media_target_by_date(self, file_path: Path) -> Path:
        ts = file_path.stat().st_mtime
        dt = datetime.fromtimestamp(ts)
        year = f"{dt.year:04d}"
        month = f"{dt.month:02d}-{dt.strftime('%B')}"
        target = self.target_media_root / year / month
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _build_cbz_target_by_series(self, file_path: Path) -> Path:
        series_name = self._derive_series_name(file_path.stem)
        target = self.target_comics_root / series_name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _build_other_target_by_type(self, file_path: Path) -> Path:
        ext = file_path.suffix.lower()
        if ext in self.DOCUMENT_EXTENSIONS:
            category = "Documentos"
        elif ext in self.INSTALLER_EXTENSIONS:
            category = "Instaladores"
        elif ext in self.COMPRESSED_EXTENSIONS:
            category = "Comprimidos"
        elif ext in self.EXECUTABLE_EXTENSIONS:
            category = "Ejecutables"
        elif ext in self.DATA_EXTENSIONS:
            category = "Datos"
        else:
            category = "Otros"

        target = self.target_other_root / category
        target.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def _derive_series_name(filename_stem: str) -> str:
        # Homogeniza separadores y quita informacion de tomo/capitulo para agrupar por serie.
        normalized = filename_stem.lower()
        normalized = normalized.replace("_", " ").replace(".", " ")
        normalized = re.sub(r"\[[^\]]*\]|\([^\)]*\)", " ", normalized)

        series = re.sub(
            r"\b(ch|cap|chapter|episode|ep|vol|volume|tomo|tomo\.|parte|part)\s*[\-_:]?\s*\d+[a-z]?\b.*$",
            "",
            normalized,
        )
        series = re.sub(r"\b\d{1,4}\b.*$", "", series)
        series = re.sub(r"[^a-z0-9 ]+", " ", series)
        series = re.sub(r"\s+", " ", series).strip()

        if len(series) < 3:
            return "Serie_Desconocida"

        return " ".join(token.capitalize() for token in series.split())

    def _move_with_collision_handling(self, source_file: Path, target_dir: Path) -> None:
        # Se bloquea esta seccion para evitar colisiones de nombre en ejecucion paralela.
        with self.move_lock:
            target_file = target_dir / source_file.name
            # Evita renombrados innecesarios cuando el archivo ya esta exactamente en destino.
            if source_file.resolve() == target_file.resolve():
                return
            target_file = self._ensure_unique_path(target_file)
            shutil.move(str(source_file), str(target_file))

    def _ensure_unique_path(self, path: Path) -> Path:
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

    def _remove_duplicate_images(self, cancel_event: threading.Event | None) -> int:
        deleted = 0
        candidates_by_size: dict[int, list[Path]] = {}
        image_files = [
            p
            for p in self.target_media_root.rglob("*")
            if p.is_file() and p.suffix.lower() in self.IMAGE_EXTENSIONS
        ]
        for image_path in image_files:
            if cancel_event and cancel_event.is_set():
                self.cancel_requested = True
                return deleted
            try:
                file_size = image_path.stat().st_size
                candidates_by_size.setdefault(file_size, []).append(image_path)
            except OSError:
                self.stats.errors += 1

        known_hashes: dict[tuple[int, str], Path] = {}
        for file_size, same_size_files in candidates_by_size.items():
            if len(same_size_files) < 2:
                continue
            for image_path in same_size_files:
                if cancel_event and cancel_event.is_set():
                    self.cancel_requested = True
                    return deleted
                try:
                    digest = self._sha256_file(image_path)
                    key = (file_size, digest)
                    if key in known_hashes:
                        image_path.unlink(missing_ok=True)
                        deleted += 1
                    else:
                        known_hashes[key] = image_path
                except Exception:
                    self.stats.errors += 1
        return deleted

    @staticmethod
    def _sha256_file(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    def _group_similar_named_images(self, cancel_event: threading.Event | None) -> int:
        moved_count = 0
        month_groups: dict[Path, dict[str, list[Path]]] = {}
        image_files = [
            p
            for p in self.target_media_root.rglob("*")
            if p.is_file() and p.suffix.lower() in self.IMAGE_EXTENSIONS
        ]

        for image_path in image_files:
            if cancel_event and cancel_event.is_set():
                self.cancel_requested = True
                return moved_count
            month_root = self._extract_month_root(image_path)
            if month_root is None:
                continue
            rel_parts = image_path.relative_to(month_root).parts
            if rel_parts and rel_parts[0] == "Agrupadas":
                continue

            group_key = self._infer_image_group_key(image_path.stem)
            if not group_key:
                continue
            month_groups.setdefault(month_root, {}).setdefault(group_key, []).append(image_path)

        for month_root, groups in month_groups.items():
            if cancel_event and cancel_event.is_set():
                self.cancel_requested = True
                return moved_count
            for group_key, grouped_files in groups.items():
                # Solo agrupa cuando hay suficiente semejanza repetida.
                if len(grouped_files) < 3:
                    continue
                target_folder = month_root / "Agrupadas" / group_key
                target_folder.mkdir(parents=True, exist_ok=True)
                for source_file in grouped_files:
                    try:
                        self._move_with_collision_handling(source_file, target_folder)
                        moved_count += 1
                    except Exception:
                        self.stats.errors += 1
        return moved_count

    def _extract_month_root(self, file_path: Path) -> Path | None:
        try:
            relative = file_path.relative_to(self.target_media_root)
        except ValueError:
            return None
        if len(relative.parts) < 3:
            return None
        year = relative.parts[0]
        month = relative.parts[1]
        return self.target_media_root / year / month

    @staticmethod
    def _infer_image_group_key(stem: str) -> str:
        normalized = stem.lower().replace("_", " ").replace("-", " ").replace(".", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()

        if any(token in normalized for token in ("screenshot", "screen shot", "captura", "captura de pantalla")):
            return "Screenshots"
        if any(token in normalized for token in ("facebook", " fb ", "fb_", "fb-", "img_")):
            return "Facebook"
        if any(token in normalized for token in ("whatsapp", "wa ", "wa_", "wa-")):
            return "WhatsApp"
        if any(token in normalized for token in ("instagram", "insta ", "insta_", "insta-")):
            return "Instagram"

        base = re.sub(r"\[[^\]]*\]|\([^\)]*\)", " ", normalized)
        base = re.sub(r"\b\d{1,8}\b", " ", base)
        base = re.sub(r"[^a-z0-9 ]+", " ", base)
        tokens = [t for t in base.split() if len(t) >= 3]
        if len(tokens) < 2:
            return ""
        return " ".join(token.capitalize() for token in tokens[:2])

    def _delete_empty_legacy_dirs(self) -> int:
        deleted = 0
        for directory in sorted(self.source_root.rglob("*"), key=lambda d: len(str(d)), reverse=True):
            if not directory.is_dir():
                continue
            if directory in (self.target_media_root, self.target_comics_root, self.target_other_root):
                continue
            if self._is_inside(directory, self.target_media_root) or self._is_inside(
                directory, self.target_other_root
            ):
                continue
            if self._is_inside(directory, self.target_comics_root):
                continue
            try:
                directory.rmdir()
                deleted += 1
            except OSError:
                # Si queda algo dentro, no se borra.
                continue
        return deleted

    @staticmethod
    def _is_inside(path: Path, possible_parent: Path) -> bool:
        try:
            path.relative_to(possible_parent)
            return True
        except ValueError:
            return False


def _config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "organizador_multimedia"


def _settings_path() -> Path:
    return _config_dir() / "settings.json"


def load_app_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return {"destinations": [], "gallery_last_folder": "", "gallery_thumb_scale": 1.0}
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if "destinations" not in data:
            data["destinations"] = []
        if "gallery_last_folder" not in data:
            data["gallery_last_folder"] = ""
        if "gallery_thumb_scale" not in data:
            data["gallery_thumb_scale"] = 1.0
        else:
            # Migrar valores viejos (0.5) a rango usable
            gs = float(data["gallery_thumb_scale"])
            data["gallery_thumb_scale"] = max(0.75, min(2.25, gs))
        return data
    except (OSError, json.JSONDecodeError):
        return {"destinations": [], "gallery_last_folder": "", "gallery_thumb_scale": 1.0}


def save_app_settings(data: dict) -> None:
    _config_dir().mkdir(parents=True, exist_ok=True)
    with _settings_path().open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def apply_dark_theme(root: tk.Tk, style: ttk.Style) -> None:
    bg = "#1a1b26"
    fg = "#c0caf5"
    fg_dim = "#a9b1d6"
    accent = "#7aa2f7"
    surface = "#24283b"
    entry_bg = "#16161e"
    if "clam" in style.theme_names():
        style.theme_use("clam")
    root.configure(bg=bg)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TLabelframe", background=bg, foreground=fg)
    style.configure("TLabelframe.Label", background=bg, foreground=accent)
    style.configure("TButton", background=surface, foreground=fg)
    style.map("TButton", background=[("active", "#414868")])
    style.configure("TCheckbutton", background=bg, foreground=fg)
    style.configure("TEntry", fieldbackground=entry_bg, foreground=fg)
    style.configure("TNotebook", background=bg)
    style.configure("TNotebook.Tab", background=surface, foreground=fg_dim, padding=[12, 6])
    style.map("TNotebook.Tab", background=[("selected", "#414868")], foreground=[("selected", fg)])
    style.configure("Horizontal.TProgressbar", troughcolor=entry_bg, background=accent, thickness=8)
    style.configure("Card.TFrame", background=surface, relief="flat")
    style.configure("Dest.TLabel", background=surface, foreground=fg, font=("Sans", 10, "bold"))
    style.configure("DestPath.TLabel", background=surface, foreground=fg_dim, font=("Sans", 8))
    style.configure("GalleryThumb.TFrame", background=surface, relief="flat")
    style.configure("GalleryTitle.TLabel", background=bg, foreground=accent, font=("Sans", 14, "bold"))


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


class GalleryManualFrame(ttk.Frame):
    """Galeria con miniaturas, seleccion multiple y destinos por arrastre."""

    PREVIEW_MAX = (440, 480)
    BATCH_THUMBS = 400

    def __init__(self, parent: ttk.Frame, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.root = parent.winfo_toplevel()
        self._thumb_size_tuple: tuple[int, int] = (160, 160)
        self._layout_cols = 5
        self._thumb_gen = 0
        self._resize_after_id: str | None = None
        self._last_canvas_width = 0
        self._gallery_window_id: int | None = None
        self._preview_gen = 0
        self._preview_photo_large: object | None = None
        self.toggle_click_var = tk.BooleanVar(value=True)
        self.selection_count_var = tk.StringVar(value="0 imagenes seleccionadas")
        self.settings = load_app_settings()
        _ts = float(self.settings.get("gallery_thumb_scale", 1.0))
        self.thumb_scale_var = tk.DoubleVar(value=max(0.75, min(2.25, _ts)))
        self._scale_sched: str | None = None
        self.gallery_folder: Path | None = None
        self.ordered_paths: list[Path] = []
        self.selected: set[Path] = set()
        self.anchor_index: int | None = None
        self.thumb_refs: list[object] = []
        self.path_to_frame: dict[Path, tk.Widget] = {}
        self._thumb_queue: queue.Queue = queue.Queue()
        self._thumb_worker: threading.Thread | None = None
        self._drag_start: tuple[int, int] | None = None
        self._drag_active = False
        self._photos: dict[str, object] = {}
        self._thumb_offset = 0
        self.folder_var = tk.StringVar(value=self.settings.get("gallery_last_folder", ""))
        self.path_display_var = tk.StringVar(value="")
        self._subfolder_paths: list[Path] = []
        self.status_gallery = tk.StringVar(
            value="Elige una carpeta y pulsa Cargar: solo se listan imagenes de esa carpeta (no subcarpetas)."
        )
        self.dest_widgets: list[tk.Widget] = []
        self._gallery_cell_gap = 6
        self._cell_outer_w = 160
        self._build_ui()
        # Importante: el frame debe ocupar la pestaña del notebook; si no, no se ve nada.
        self.pack(fill=tk.BOTH, expand=True)
        self.root.bind("<ButtonRelease-1>", self._on_global_release, add="+")

    def _build_ui(self) -> None:
        bg = self.root.cget("bg")
        title = ttk.Label(self, text="Galeria manual", style="GalleryTitle.TLabel")
        title.pack(anchor="w", pady=(0, 4))
        sub = ttk.Label(
            self,
            text=(
                "Solo esta carpeta (no recursivo). Navega con Subcarpetas / Carpeta superior. "
                "Las miniaturas se adaptan al ancho de la ventana."
            ),
            wraplength=780,
        )
        sub.pack(anchor="w", pady=(0, 8))

        sel_bar = ttk.LabelFrame(self, text="Seleccion")
        sel_bar.pack(fill=tk.X, pady=(0, 8))
        sel_inner = ttk.Frame(sel_bar)
        sel_inner.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(sel_inner, text="Seleccionar todas", command=self._select_all).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(sel_inner, text="Quitar seleccion", command=self._select_none).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(sel_inner, text="Invertir seleccion", command=self._invert_selection).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Checkbutton(
            sel_inner,
            text="Un clic alterna (sin Ctrl): añade o quita de la seleccion",
            variable=self.toggle_click_var,
        ).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(sel_inner, textvariable=self.selection_count_var, foreground="#9ece6a", font=("Sans", 10, "bold")).pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        help_sel = ttk.Label(
            sel_bar,
            text=(
                "Si alternar esta desactivado: clic = una sola imagen + vista previa. "
                "Ctrl+clic = añadir o quitar. Shift+clic = rango. "
                "Arrastra la seleccion a un destino abajo o suelta sobre la tarjeta."
            ),
            wraplength=760,
            foreground="#565f89",
        )
        help_sel.pack(anchor="w", padx=8, pady=(0, 6))

        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row1, text="Carpeta:").pack(side=tk.LEFT)
        entry = ttk.Entry(row1, textvariable=self.folder_var, width=70)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(row1, text="Explorar...", command=self._browse_folder).pack(side=tk.LEFT)
        ttk.Button(row1, text="Cargar galeria", command=self._load_gallery).pack(side=tk.LEFT, padx=(4, 0))
        self.more_thumbs_btn = ttk.Button(row1, text="Mas miniaturas", command=self._load_more_thumbs, state=tk.DISABLED)
        self.more_thumbs_btn.pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(row1, text="Ajustes destinos...", command=self._open_settings).pack(side=tk.LEFT, padx=(8, 0))

        nav_row = ttk.Frame(self)
        nav_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(nav_row, text="Carpeta superior", command=self._nav_up).pack(side=tk.LEFT)
        ttk.Button(nav_row, text="Actualizar esta carpeta", command=self._reload_current_folder).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Label(nav_row, textvariable=self.path_display_var, wraplength=560, foreground="#a9b1d6").pack(
            side=tk.LEFT, padx=(12, 0), fill=tk.X, expand=True
        )

        sub_frame = ttk.LabelFrame(self, text="Subcarpetas (doble clic o Enter para entrar)")
        sub_frame.pack(fill=tk.X, pady=(0, 8))
        self.subfolder_lb = tk.Listbox(
            sub_frame,
            height=5,
            bg="#16161e",
            fg="#c0caf5",
            selectbackground="#414868",
            selectforeground="#c0caf5",
            relief=tk.FLAT,
            highlightthickness=0,
        )
        sf_scroll = ttk.Scrollbar(sub_frame, orient="vertical", command=self.subfolder_lb.yview)
        self.subfolder_lb.configure(yscrollcommand=sf_scroll.set)
        self.subfolder_lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=4)
        sf_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4, padx=(0, 4))
        self.subfolder_lb.bind("<Double-Button-1>", self._on_subfolder_activate)
        self.subfolder_lb.bind("<Return>", self._on_subfolder_activate)

        self.main_pane = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashwidth=5,
            bg="#1a1b26",
            sashrelief=tk.FLAT,
        )
        self.main_pane.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        gallery_wrap = ttk.Frame(self.main_pane)
        self.preview_column = ttk.Frame(self.main_pane, width=460)
        self.main_pane.add(gallery_wrap, minsize=420)
        self.main_pane.add(self.preview_column, minsize=360)

        zoom_row = ttk.Frame(gallery_wrap)
        zoom_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(zoom_row, text="Tamaño miniaturas:").pack(side=tk.LEFT, padx=(0, 8))
        self.thumb_scale_slider = ttk.Scale(
            zoom_row,
            from_=0.75,
            to=2.25,
            orient=tk.HORIZONTAL,
            length=260,
            variable=self.thumb_scale_var,
            command=self._on_thumb_scale_slider,
        )
        self.thumb_scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.thumb_scale_label = ttk.Label(zoom_row, text="", foreground="#a9b1d6", width=6)
        self.thumb_scale_label.pack(side=tk.LEFT, padx=(8, 0))
        self.thumb_scale_label.configure(text=f"{int(self.thumb_scale_var.get() * 100)}%")
        ttk.Label(
            zoom_row,
            text="(Derecha = menos columnas y mas grande | miniaturas recortan para llenar el cuadrado)",
            foreground="#565f89",
        ).pack(side=tk.LEFT, padx=(12, 0))

        self.gallery_canvas = tk.Canvas(gallery_wrap, bg="#16161e", highlightthickness=0, height=380)
        scroll_y = ttk.Scrollbar(gallery_wrap, orient="vertical", command=self.gallery_canvas.yview)
        self.gallery_inner = tk.Frame(self.gallery_canvas, bg="#16161e")
        self.gallery_inner.bind(
            "<Configure>",
            lambda _e: self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all")),
        )
        self._gallery_window_id = self.gallery_canvas.create_window((0, 0), window=self.gallery_inner, anchor="nw")
        self.gallery_canvas.configure(yscrollcommand=scroll_y.set)
        self.gallery_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.gallery_canvas.bind("<Configure>", self._on_gallery_canvas_configure)
        self.gallery_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.gallery_canvas.bind("<Button-4>", lambda e: self.gallery_canvas.yview_scroll(-2, "units"))
        self.gallery_canvas.bind("<Button-5>", lambda e: self.gallery_canvas.yview_scroll(2, "units"))

        preview_title = ttk.Label(self.preview_column, text="Vista previa", font=("Sans", 11, "bold"))
        preview_title.pack(anchor="w", pady=(0, 6))
        prev_box = tk.Frame(self.preview_column, bg="#16161e", height=self.PREVIEW_MAX[1], width=self.PREVIEW_MAX[0])
        prev_box.pack(fill=tk.X, pady=(0, 6))
        prev_box.pack_propagate(False)
        self.preview_image_label = tk.Label(
            prev_box,
            bg="#16161e",
            fg="#565f89",
            text="Clic en una miniatura",
            font=("Sans", 10),
        )
        self.preview_image_label.pack(expand=True, fill=tk.BOTH)
        self.preview_meta_label = tk.Label(
            self.preview_column,
            bg="#1a1b26",
            fg="#a9b1d6",
            font=("Sans", 8),
            wraplength=420,
            justify=tk.LEFT,
            text="",
        )
        self.preview_meta_label.pack(anchor="w", fill=tk.X)

        dest_frame = ttk.LabelFrame(self, text="Destinos rapidos (+ anade carpeta | arrastra o clic con seleccion)")
        dest_frame.pack(fill=tk.X, pady=(12, 0))
        dest_outer = ttk.Frame(dest_frame)
        dest_outer.pack(fill=tk.X, padx=4, pady=4)
        self.dest_hcanvas = tk.Canvas(dest_outer, bg="#1a1b26", height=104, highlightthickness=0)
        dest_hscroll = ttk.Scrollbar(dest_outer, orient="horizontal", command=self.dest_hcanvas.xview)
        self.dest_container = tk.Frame(self.dest_hcanvas, bg="#1a1b26")
        self.dest_hcanvas.create_window((0, 0), window=self.dest_container, anchor="nw")

        def _on_dest_configure(_event: tk.Event) -> None:
            self.dest_hcanvas.configure(scrollregion=self.dest_hcanvas.bbox("all"))

        self.dest_container.bind("<Configure>", _on_dest_configure)
        self.dest_hcanvas.pack(side=tk.TOP, fill=tk.X, expand=True)
        dest_hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.dest_hcanvas.configure(xscrollcommand=dest_hscroll.set)
        self._refresh_destinations()

        st = ttk.Label(self, textvariable=self.status_gallery, foreground="#7aa2f7")
        st.pack(anchor="w", pady=(8, 0))

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.gallery_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _effective_gallery_canvas_width(self, w: int | float) -> int:
        # Descarta anchos espurios durante reflow (frame vacio, eventos de Tk) que encogen la rejilla.
        try:
            iw = int(w)
        except (TypeError, ValueError):
            iw = 0
        last = int(self._last_canvas_width or 0)
        if iw < 80:
            return max(last, 400)
        if last >= 300 and iw < 120 and iw < (last * 22) // 100:
            return last
        return iw

    def _debounced_gallery_canvas_reflow(self) -> None:
        self._resize_after_id = None
        w = self._effective_gallery_canvas_width(self.gallery_canvas.winfo_width())
        self._apply_gallery_reflow(w, force=False)

    def _on_gallery_canvas_configure(self, event: tk.Event) -> None:
        w = int(event.width)
        eff = self._effective_gallery_canvas_width(w)
        if self._gallery_window_id is not None and eff > 2:
            # Mismo ancho efectivo que la metrica; evita encoger el create_window con event.width espurio.
            self.gallery_canvas.itemconfigure(self._gallery_window_id, width=max(1, eff - 3))
        if eff < 80:
            return
        if self._resize_after_id is not None:
            try:
                self.root.after_cancel(self._resize_after_id)
            except tk.TclError:
                pass
            self._resize_after_id = None
        self._resize_after_id = self.root.after(180, self._debounced_gallery_canvas_reflow)

    def _compute_layout_metrics(self, canvas_width: int) -> None:
        # Ancho util del area de rejilla (ya excluye scrollbar del canvas).
        safe_w = max(64, int(canvas_width) - 14)
        zoom = float(self.thumb_scale_var.get())
        zoom = max(0.75, min(2.25, zoom))
        gap = 6
        margin_lr = 10
        avail = max(48, safe_w - margin_lr)
        # Zoom SIEMPRE en el mismo sentido: valor alto => menos columnas => celdas mas anchas (mas ampliado).
        # (Antes el cociente entero (avail//(target+gap)) podia dejar el mismo cols al subir zoom.)
        cols_min = 2
        cols_max = min(16, max(3, avail // 48))
        cols_max = max(cols_max, cols_min)
        t = (zoom - 0.75) / (2.25 - 0.75)
        cols = int(round(cols_max - t * (cols_max - cols_min)))
        cols = max(cols_min, min(cols_max, cols))
        total_gap = (cols - 1) * gap
        cell_w = (avail - total_gap) // cols
        cell_w = max(48, cell_w)
        while cols > cols_min and cols * cell_w + total_gap > avail:
            cols -= 1
            total_gap = (cols - 1) * gap
            cell_w = (avail - total_gap) // cols
            cell_w = max(48, cell_w)
        inner_margin = 8
        thumb_side = max(48, cell_w - inner_margin)
        self._layout_cols = cols
        self._cell_outer_w = int(cell_w)
        self._thumb_size_tuple = (thumb_side, thumb_side)
        self._gallery_cell_gap = gap

    def _update_layout_metrics(self, canvas_width: int | None = None) -> None:
        if canvas_width is None or canvas_width < 80:
            canvas_width = self.gallery_canvas.winfo_width()
        canvas_width = self._effective_gallery_canvas_width(canvas_width)
        if canvas_width < 80:
            canvas_width = max(400, self._last_canvas_width or 720)
        self._compute_layout_metrics(canvas_width)

    def _prepare_grid_columns(self) -> None:
        n = max(2, self._layout_cols)
        for i in range(24):
            self.gallery_inner.columnconfigure(i, weight=0, minsize=0)
        for i in range(n):
            self.gallery_inner.columnconfigure(i, weight=1, uniform="gal_col", minsize=1)

    def _on_thumb_scale_slider(self, value: str | float) -> None:
        try:
            v = float(value)
        except (TypeError, ValueError):
            try:
                v = float(self.thumb_scale_var.get())
            except (TypeError, ValueError, tk.TclError):
                return
        v = max(0.75, min(2.25, v))
        self.thumb_scale_var.set(v)
        self.thumb_scale_label.configure(text=f"{int(round(v * 100))}%")
        self.settings["gallery_thumb_scale"] = v
        save_app_settings(self.settings)
        if self._scale_sched is not None:
            try:
                self.root.after_cancel(self._scale_sched)
            except tk.TclError:
                pass
        self._scale_sched = self.root.after(160, self._reflow_after_scale_change)

    def _reflow_after_scale_change(self) -> None:
        self._scale_sched = None
        w = self._effective_gallery_canvas_width(self.gallery_canvas.winfo_width())
        self._apply_gallery_reflow(w, force=True)

    def _apply_gallery_reflow(self, canvas_width: int, force: bool = False) -> None:
        self._resize_after_id = None
        canvas_width = self._effective_gallery_canvas_width(canvas_width)
        if canvas_width < 80:
            return
        if self._gallery_window_id is not None:
            self.gallery_canvas.itemconfigure(self._gallery_window_id, width=max(1, canvas_width - 3))
        self._compute_layout_metrics(canvas_width)
        self._last_canvas_width = canvas_width
        snap = (
            self._layout_cols,
            self._cell_outer_w,
            round(float(self.thumb_scale_var.get()), 2),
        )
        if (
            not force
            and snap == getattr(self, "_layout_snap", None)
            and abs(canvas_width - getattr(self, "_layout_snap_w", -999)) < 16
        ):
            return
        self._layout_snap = snap
        self._layout_snap_w = canvas_width
        if not self.path_to_frame:
            return
        if not self.ordered_paths:
            return
        while True:
            try:
                self._thumb_queue.get_nowait()
            except queue.Empty:
                break
        for w in self.gallery_inner.winfo_children():
            w.destroy()
        self.path_to_frame.clear()
        self._photos.clear()
        self.selected.clear()
        self.anchor_index = None
        self._thumb_offset = 0
        self._update_selection_label()
        self._start_thumb_worker(reset_offset=True)

    def _update_selection_label(self) -> None:
        n = len(self.selected)
        total = len(self.ordered_paths)
        self.selection_count_var.set(f"{n} de {total} seleccionadas")

    def _select_all(self) -> None:
        self.selected = set(self.ordered_paths)
        if self.ordered_paths:
            self.anchor_index = 0
        self._highlight_selection()
        self._update_selection_label()
        if self.ordered_paths:
            self._schedule_preview(self.ordered_paths[0])

    def _select_none(self) -> None:
        self.selected.clear()
        self.anchor_index = None
        self._highlight_selection()
        self._update_selection_label()

    def _invert_selection(self) -> None:
        self.selected = {p for p in self.ordered_paths if p not in self.selected}
        self._highlight_selection()
        self._update_selection_label()

    def _quick_add_destination(self) -> None:
        path = self._browse_dest_folder()
        if not path:
            return
        p = Path(path).expanduser().resolve()
        default_label = p.name
        label = simpledialog.askstring(
            "Nombre del destino",
            "Etiqueta visible en la barra:",
            initialvalue=default_label,
            parent=self.root,
        )
        if label is None:
            return
        label = label.strip() or default_label
        self.settings.setdefault("destinations", []).append({"label": label, "path": str(p)})
        save_app_settings(self.settings)
        self._refresh_destinations()

    def _browse_folder(self) -> None:
        initial = self.folder_var.get().strip() or os.path.expanduser("~")
        folder = filedialog.askdirectory(title="Carpeta de la galeria", initialdir=initial)
        if folder:
            self.folder_var.set(folder)
            self.settings["gallery_last_folder"] = folder
            save_app_settings(self.settings)

    def _browse_dest_folder(self) -> str | None:
        return filedialog.askdirectory(title="Elegir carpeta destino")

    def _refresh_destinations(self) -> None:
        for w in self.dest_container.winfo_children():
            w.destroy()
        self.dest_widgets.clear()

        plus = tk.Frame(self.dest_container, bg="#414868", padx=14, pady=18, cursor="hand2")
        plus.pack(side=tk.LEFT, padx=(0, 10), pady=4)
        tk.Label(plus, text="+", bg="#414868", fg="#c0caf5", font=("Sans", 22, "bold")).pack()
        tk.Label(plus, text="Anadir", bg="#414868", fg="#a9b1d6", font=("Sans", 8)).pack()
        for w in plus.winfo_children():
            w.bind("<ButtonRelease-1>", lambda _e: self._quick_add_destination())
        plus.bind("<ButtonRelease-1>", lambda _e: self._quick_add_destination())

        dests = self.settings.get("destinations", [])
        if not dests:
            hint = ttk.Label(
                self.dest_container,
                text="Ningun destino: pulsa + o 'Ajustes destinos...'",
                foreground="#565f89",
            )
            hint.pack(side=tk.LEFT, anchor="w")
            return
        for item in dests:
            label = item.get("label") or "Destino"
            path_str = item.get("path") or ""
            card = tk.Frame(self.dest_container, bg="#24283b", padx=14, pady=12, cursor="hand2")
            card.pack(side=tk.LEFT, padx=(0, 8), pady=4)
            card.gallery_dest_path = Path(path_str).expanduser()  # type: ignore[attr-defined]
            l1 = tk.Label(card, text=label, bg="#24283b", fg="#c0caf5", font=("Sans", 10, "bold"))
            l1.pack(anchor="w")
            short = path_str if len(path_str) < 42 else path_str[:19] + "..." + path_str[-18:]
            l2 = tk.Label(card, text=short, bg="#24283b", fg="#565f89", font=("Sans", 8))
            l2.pack(anchor="w")
            dest_path = card.gallery_dest_path

            def on_enter(_e: tk.Event, c: tk.Frame = card) -> None:
                c.configure(bg="#565f89")

            def on_leave(_e: tk.Event, c: tk.Frame = card) -> None:
                c.configure(bg="#24283b")

            for w in (card, l1, l2):
                w.bind("<ButtonRelease-1>", lambda e, p=dest_path: self._release_on_destination(p))
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)

    def _open_settings(self) -> None:
        top = tk.Toplevel(self.root)
        top.title("Destinos predefinidos")
        top.configure(bg="#1a1b26")
        top.geometry("520x320")
        ttk.Label(top, text="Etiqueta y ruta de cada carpeta destino:").pack(anchor="w", padx=12, pady=(12, 6))
        list_frame = ttk.Frame(top)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        scroll = ttk.Scrollbar(list_frame)
        lb = tk.Listbox(list_frame, height=10, bg="#16161e", fg="#c0caf5", selectbackground="#414868")
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=lb.yview)
        lb.config(yscrollcommand=scroll.set)

        def refresh_list() -> None:
            lb.delete(0, tk.END)
            for d in self.settings.get("destinations", []):
                lb.insert(tk.END, f"{d.get('label','')}  ->  {d.get('path','')}")

        refresh_list()

        btn_row = ttk.Frame(top)
        btn_row.pack(fill=tk.X, padx=12, pady=8)

        def add_dest() -> None:
            path = self._browse_dest_folder()
            if not path:
                return
            label = Path(path).name
            self.settings.setdefault("destinations", []).append({"label": label, "path": path})
            save_app_settings(self.settings)
            refresh_list()
            self._refresh_destinations()

        def remove_sel() -> None:
            sel = lb.curselection()
            if not sel:
                return
            idx = sel[0]
            dests = self.settings.get("destinations", [])
            if 0 <= idx < len(dests):
                dests.pop(idx)
                save_app_settings(self.settings)
                refresh_list()
                self._refresh_destinations()

        ttk.Button(btn_row, text="Anadir carpeta", command=add_dest).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="Quitar seleccionado", command=remove_sel).pack(side=tk.LEFT)
        ttk.Button(top, text="Cerrar", command=top.destroy).pack(anchor="e", padx=12, pady=12)

    def _load_gallery(self) -> None:
        raw = self.folder_var.get().strip()
        if not raw:
            messagebox.showwarning("Carpeta", "Indica una carpeta para la galeria.")
            return
        folder = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()
        if not folder.is_dir():
            messagebox.showerror("Carpeta", f"No existe o no es carpeta:\n{folder}")
            return
        self.gallery_folder = folder
        self.settings["gallery_last_folder"] = str(folder)
        save_app_settings(self.settings)
        self._reload_current_folder()

    def _reload_current_folder(self) -> None:
        if not self.gallery_folder:
            messagebox.showinfo("Galeria", "Primero pulsa 'Cargar galeria' y elige una carpeta.")
            return
        folder = self.gallery_folder.resolve()
        if not folder.is_dir():
            messagebox.showerror("Carpeta", f"La carpeta ya no existe o no es valida:\n{folder}")
            return
        self.gallery_folder = folder
        self.folder_var.set(str(folder))
        self.path_display_var.set(str(folder))
        self.settings["gallery_last_folder"] = str(folder)
        save_app_settings(self.settings)
        self._refresh_subfolder_list()
        self._clear_grid()
        self.ordered_paths = self._scan_images_flat(folder)
        self.selected.clear()
        self.anchor_index = None
        self._thumb_offset = 0
        self._update_selection_label()
        n_img = len(self.ordered_paths)
        n_sub = len(self._subfolder_paths)
        self.status_gallery.set(
            f"En esta carpeta: {n_img} imagen(es), {n_sub} subcarpeta(s). "
            "(Solo archivos directos; no se busca en subcarpetas.)"
        )
        self._start_thumb_worker(reset_offset=True)

    def _nav_up(self) -> None:
        if not self.gallery_folder:
            messagebox.showinfo("Galeria", "Carga una carpeta primero.")
            return
        parent = self.gallery_folder.parent
        if parent == self.gallery_folder:
            return
        if not parent.is_dir():
            return
        self.gallery_folder = parent.resolve()
        self.settings["gallery_last_folder"] = str(self.gallery_folder)
        save_app_settings(self.settings)
        self._reload_current_folder()

    def _on_subfolder_activate(self, _event: tk.Event | None = None) -> None:
        sel = self.subfolder_lb.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self._subfolder_paths):
            self.gallery_folder = self._subfolder_paths[idx].resolve()
            self.settings["gallery_last_folder"] = str(self.gallery_folder)
            save_app_settings(self.settings)
            self._reload_current_folder()

    def _refresh_subfolder_list(self) -> None:
        self.subfolder_lb.delete(0, tk.END)
        self._subfolder_paths = []
        if not self.gallery_folder:
            return
        for d in self._list_subdirs(self.gallery_folder):
            self.subfolder_lb.insert(tk.END, f"  {d.name}")
            self._subfolder_paths.append(d)

    @staticmethod
    def _list_subdirs(root: Path) -> list[Path]:
        out: list[Path] = []
        try:
            for p in root.iterdir():
                if p.is_dir():
                    out.append(p)
        except OSError:
            pass
        out.sort(key=lambda x: str(x).lower())
        return out

    @staticmethod
    def _scan_images_flat(root: Path) -> list[Path]:
        # Solo archivos en esta carpeta (no recursivo).
        exts = MediaOrganizer.IMAGE_EXTENSIONS
        out: list[Path] = []
        try:
            for p in root.iterdir():
                if p.is_file() and p.suffix.lower() in exts:
                    out.append(p)
        except OSError:
            pass
        out.sort(key=lambda x: str(x).lower())
        return out

    def _clear_grid(self) -> None:
        for w in self.gallery_inner.winfo_children():
            w.destroy()
        self.path_to_frame.clear()
        self.thumb_refs.clear()
        self._clear_preview()

    def _clear_preview(self) -> None:
        self._preview_gen += 1
        self._preview_photo_large = None
        self.preview_image_label.configure(image="", text="Clic en una miniatura", fg="#565f89")
        self.preview_meta_label.configure(text="")

    def _schedule_preview(self, path: Path) -> None:
        self._preview_gen += 1
        gen = self._preview_gen
        self.preview_meta_label.configure(text=str(path))
        self.preview_image_label.configure(image="", text="Cargando vista previa...", fg="#7aa2f7")
        if not _HAS_PIL:
            self.preview_image_label.configure(
                image="",
                text="Instala Pillow (pip install pillow)\npara vista previa grande.",
                fg="#e0af68",
            )
            return

        def worker() -> None:
            try:
                with Image.open(path) as im:
                    im = im.copy()
                    im.thumbnail(self.PREVIEW_MAX, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(im)
                self.root.after(0, lambda: self._apply_preview_image(gen, photo, path))
            except Exception:
                self.root.after(0, lambda: self._apply_preview_error(gen, path))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_preview_image(self, gen: int, photo: object, path: Path) -> None:
        if gen != self._preview_gen:
            return
        self._preview_photo_large = photo
        self.preview_image_label.configure(image=photo, text="")

        try:
            st = path.stat()
            size_mb = st.st_size / (1024 * 1024)
            meta = f"{path.name}\n{path.parent}\n{size_mb:.2f} MB"
        except OSError:
            meta = str(path)
        self.preview_meta_label.configure(text=meta)

    def _apply_preview_error(self, gen: int, path: Path) -> None:
        if gen != self._preview_gen:
            return
        self._preview_photo_large = None
        self.preview_image_label.configure(image="", text="No se pudo cargar la vista previa", fg="#f7768e")
        self.preview_meta_label.configure(text=str(path))

    def _load_more_thumbs(self) -> None:
        if not self.ordered_paths:
            return
        self._start_thumb_worker(reset_offset=False)

    def _start_thumb_worker(self, reset_offset: bool = False) -> None:
        if self._thumb_worker and self._thumb_worker.is_alive() and not reset_offset:
            return
        if reset_offset:
            self._thumb_gen += 1
            while True:
                try:
                    self._thumb_queue.get_nowait()
                except queue.Empty:
                    break
        gen = self._thumb_gen
        if reset_offset:
            self._thumb_offset = 0
        cw = self._effective_gallery_canvas_width(self.gallery_canvas.winfo_width())
        self._update_layout_metrics(cw)
        self._prepare_grid_columns()
        total = len(self.ordered_paths)
        if self._thumb_offset >= total:
            self.status_gallery.set("No hay mas miniaturas para cargar.")
            self.more_thumbs_btn.config(state=tk.DISABLED)
            return
        end = min(self._thumb_offset + self.BATCH_THUMBS, total)
        paths = self.ordered_paths[self._thumb_offset : end]
        self._thumb_offset = end

        def worker() -> None:
            for path in paths:
                if gen != self._thumb_gen:
                    return
                if not path.exists():
                    continue
                thumb_img = self._make_thumbnail_photo(path)
                self._thumb_queue.put(("thumb", gen, path, thumb_img))
            if gen != self._thumb_gen:
                return
            self._thumb_queue.put(("done", gen, len(paths), end, total))

        self._thumb_worker = threading.Thread(target=worker, daemon=True)
        self._thumb_worker.start()
        self.more_thumbs_btn.config(state=tk.DISABLED)
        self._poll_thumb_queue()

    def _make_thumbnail_photo(self, path: Path) -> object | None:
        if not _HAS_PIL:
            return None
        try:
            with Image.open(path) as im:
                im = im.convert("RGBA")
                size = (int(self._thumb_size_tuple[0]), int(self._thumb_size_tuple[1]))
                # Rellena el cuadrado (recorta bordes si hace falta); siempre tamano exacto = todo el hueco.
                if ImageOps is not None:
                    im = ImageOps.fit(
                        im,
                        size,
                        Image.Resampling.LANCZOS,
                        bleed=0.0,
                        centering=(0.5, 0.5),
                    )
                else:
                    im.thumbnail(size, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(im)
        except Exception:
            return None

    def _poll_thumb_queue(self) -> None:
        done_batch: tuple[int, int, int] | None = None
        try:
            while True:
                item = self._thumb_queue.get_nowait()
                if item[0] == "thumb":
                    _, gen, path, photo = item
                    if gen != self._thumb_gen:
                        continue
                    self._add_thumb_cell(path, photo)
                elif item[0] == "done":
                    _, gen, n, offset_end, total = item
                    if gen != self._thumb_gen:
                        continue
                    done_batch = (n, offset_end, total)
        except queue.Empty:
            pass
        if done_batch is not None:
            _n, offset_end, total = done_batch
            extra = "" if _HAS_PIL else " Instala Pillow: pip install pillow."
            remaining = max(0, total - offset_end)
            self.status_gallery.set(
                f"Miniaturas mostradas hasta {offset_end} de {total}.{extra}"
                + (f" Quedan {remaining}; pulsa 'Mas miniaturas'." if remaining > 0 else "")
            )
            if remaining > 0:
                self.more_thumbs_btn.config(state=tk.NORMAL)
            else:
                self.more_thumbs_btn.config(state=tk.DISABLED)
        if self._thumb_worker and self._thumb_worker.is_alive():
            self.root.after(80, self._poll_thumb_queue)
        elif not self._thumb_queue.empty():
            self.root.after(80, self._poll_thumb_queue)
        else:
            self._thumb_worker = None

    def _add_thumb_cell(self, path: Path, photo: object | None) -> None:
        cols = max(2, self._layout_cols)
        row = len(self.path_to_frame) // cols
        col = len(self.path_to_frame) % cols
        gap = getattr(self, "_gallery_cell_gap", 6)
        gx = max(1, gap // 2)
        thumb = self._thumb_size_tuple[0]
        outer = tk.Frame(self.gallery_inner, bg="#24283b", padx=2, pady=4)
        outer.grid(row=row, column=col, padx=(gx, gx), pady=4, sticky="nsew")
        self.path_to_frame[path] = outer
        # Caja cuadrada del tamano de la miniatura: ocupa el ancho asignado a la columna.
        img_box = tk.Frame(outer, bg="#24283b", width=thumb, height=thumb, highlightthickness=0)
        img_box.pack(anchor=tk.CENTER, pady=(0, 2))
        img_box.pack_propagate(False)
        if photo is not None:
            key = str(path)
            self._photos[key] = photo
            lbl = tk.Label(img_box, image=photo, bg="#24283b")
            lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            lbl = tk.Label(img_box, text="(sin vista previa)", bg="#24283b", fg="#565f89", font=("Sans", 8))
            lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        name = path.name if len(path.name) < 28 else path.name[:12] + "..." + path.name[-10:]
        wrap = max(60, thumb - 4)
        cap = tk.Label(outer, text=name, bg="#24283b", fg="#a9b1d6", font=("Sans", 8), wraplength=wrap)
        cap.pack(fill=tk.X, pady=(2, 0))
        for w in (outer, img_box, lbl, cap):
            w.bind("<Button-1>", lambda e, p=path: self._on_thumb_press(e, p))
            w.bind("<Shift-Button-1>", lambda e, p=path: self._on_thumb_press(e, p))
            w.bind("<Control-Button-1>", lambda e, p=path: self._on_thumb_press(e, p))
            w.bind("<B1-Motion>", self._on_thumb_motion)
        outer.bind("<ButtonRelease-1>", lambda e: self._on_thumb_release(e))

    def _index_of(self, path: Path) -> int | None:
        try:
            return self.ordered_paths.index(path)
        except ValueError:
            return None

    def _on_thumb_press(self, event: tk.Event, path: Path) -> None:
        self._drag_start = (event.x_root, event.y_root)
        self._drag_active = False
        idx = self._index_of(path)
        if idx is None:
            return
        if event.state & 0x0001:  # Shift
            if self.anchor_index is not None:
                a, b = sorted((self.anchor_index, idx))
                for i in range(a, b + 1):
                    self.selected.add(self.ordered_paths[i])
            else:
                self.selected.add(path)
                self.anchor_index = idx
        elif event.state & 0x0004:  # Control
            if path in self.selected:
                self.selected.discard(path)
            else:
                self.selected.add(path)
            self.anchor_index = idx
        elif self.toggle_click_var.get():
            if path in self.selected:
                self.selected.discard(path)
            else:
                self.selected.add(path)
            self.anchor_index = idx
        else:
            self.selected = {path}
            self.anchor_index = idx
        self._highlight_selection()
        self.status_gallery.set("Listo. Arrastra a un destino o usa los botones de seleccion.")
        self._schedule_preview(path)

    def _on_thumb_motion(self, event: tk.Event) -> None:
        if self._drag_start is None:
            return
        dx = event.x_root - self._drag_start[0]
        dy = event.y_root - self._drag_start[1]
        if (dx * dx + dy * dy) ** 0.5 > 10:
            self._drag_active = True

    def _on_thumb_release(self, _event: tk.Event) -> None:
        self._drag_start = None

    def _on_global_release(self, event: tk.Event) -> None:
        if not self._drag_active or not self.selected:
            self._drag_active = False
            return
        w = self.root.winfo_containing(event.x_root, event.y_root)
        dest_path = self._find_dest_path_widget(w)
        self._drag_active = False
        if dest_path:
            self._move_to_dest(dest_path)

    def _release_on_destination(self, dest_path: Path) -> None:
        self._drag_active = False
        if not self.selected:
            self.status_gallery.set("Selecciona imagenes en la galeria (usa 'Un clic alterna' o Ctrl+clic).")
            return
        self._move_to_dest(dest_path)

    def _find_dest_path_widget(self, w: tk.Misc | None) -> Path | None:
        while w is not None:
            p = getattr(w, "gallery_dest_path", None)
            if p is not None:
                return p  # type: ignore[no-any-return]
            try:
                parent_id = w.winfo_parent()
                if not parent_id or parent_id == ".":
                    break
                w = w.nametowidget(parent_id)
            except Exception:
                break
        return None

    def _highlight_selection(self) -> None:
        for path, frame in self.path_to_frame.items():
            col = "#414868" if path in self.selected else "#24283b"
            self._apply_bg_recursive(frame, col)
        self._update_selection_label()

    def _apply_bg_recursive(self, widget: tk.Misc, col: str) -> None:
        if isinstance(widget, (tk.Frame, tk.Label, tk.Canvas)):
            try:
                widget.configure(bg=col)
            except tk.TclError:
                pass
        for ch in widget.winfo_children():
            self._apply_bg_recursive(ch, col)

    def _move_to_dest(self, dest_dir: Path) -> None:
        if not self.selected:
            messagebox.showinfo("Galeria", "Selecciona al menos una imagen.")
            return
        dest_dir = dest_dir.expanduser().resolve()
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Destino", f"No se pudo crear o acceder:\n{e}")
            return
        moved = 0
        errors = 0
        for src in list(self.selected):
            try:
                target = dest_dir / src.name
                target = ensure_unique_destination(target)
                if src.resolve() == target.resolve():
                    continue
                shutil.move(str(src), str(target))
                moved += 1
            except Exception:
                errors += 1
        self.selected.clear()
        self._refresh_after_move()
        self.status_gallery.set(f"Movidas {moved} imagen(es). Errores: {errors}.")

    def _refresh_after_move(self) -> None:
        if not self.gallery_folder:
            return
        self._clear_grid()
        self.ordered_paths = self._scan_images_flat(self.gallery_folder)
        self.selected.clear()
        self.anchor_index = None
        self._thumb_offset = 0
        self._update_selection_label()
        self._start_thumb_worker(reset_offset=True)


class OrganizerApp:
    """Interfaz grafica simple para seleccionar ruta y ejecutar organizacion."""

    def __init__(self, parent: ttk.Frame) -> None:
        self.parent = parent
        self.root = parent.winfo_toplevel()
        self.root.title("Organizador Multimedia")
        self.root.geometry("900x620")
        self.root.minsize(800, 560)
        self.root.resizable(True, True)

        self.selected_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Estado: esperando ruta.")
        self.progress_text = tk.StringVar(value="Progreso: 0/0")
        self.elapsed_text = tk.StringVar(value="Tiempo transcurrido: 00:00")
        self.progress_value = tk.DoubleVar(value=0.0)
        self.include_organized_var = tk.BooleanVar(value=False)
        self.include_comics_var = tk.BooleanVar(value=False)
        self.include_pending_var = tk.BooleanVar(value=False)
        self.remove_duplicates_var = tk.BooleanVar(value=False)
        self.group_similar_images_var = tk.BooleanVar(value=False)
        self.is_running = False
        self.worker_thread: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self.ui_queue: queue.Queue = queue.Queue()
        self.run_btn: ttk.Button | None = None
        self.cancel_btn: ttk.Button | None = None
        self.run_started_at: float | None = None
        self.indeterminate_active = False
        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.parent, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            container,
            text="Organiza imagenes y videos por anio/mes",
            font=("Sans", 13, "bold"),
        )
        title.pack(anchor="w", pady=(0, 8))

        description = ttk.Label(
            container,
            text=(
                "Selecciona una carpeta. El programa movera archivos multimedia a "
                "'Organizado/Anio/Mes', los .cbz a 'ComicsCBZ/Serie' y todo lo demas "
                "a 'PendientesRevision/Tipo'."
            ),
            wraplength=640,
        )
        description.pack(anchor="w", pady=(0, 12))

        path_frame = ttk.Frame(container)
        path_frame.pack(fill=tk.X, pady=(0, 12))

        path_entry = ttk.Entry(path_frame, textvariable=self.selected_path, width=78)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        path_entry.bind("<Return>", lambda _event: self._run_organizer())

        choose_btn = ttk.Button(path_frame, text="Seleccionar carpeta", command=self._choose_folder)
        choose_btn.pack(side=tk.LEFT, padx=(8, 0))

        warning = ttk.Label(
            container,
            text=(
                "Importante: se moveran archivos y se intentaran borrar carpetas vacias "
                "anteriores para dejar estructura limpia."
            ),
            foreground="#e0af68",
            wraplength=640,
        )
        warning.pack(anchor="w", pady=(0, 16))

        tips = ttk.Label(
            container,
            text=(
                "Tip: tambien puedes pegar la ruta manualmente y pulsar Enter. "
                "Ejemplo: /home/usuario/Documentos o ~/Videos"
            ),
            wraplength=720,
        )
        tips.pack(anchor="w", pady=(0, 12))

        self.progress_bar = ttk.Progressbar(
            container,
            orient="horizontal",
            length=720,
            mode="determinate",
            variable=self.progress_value,
            maximum=100,
        )
        self.progress_bar.pack(anchor="w", fill=tk.X, pady=(0, 6))

        progress_label = ttk.Label(container, textvariable=self.progress_text)
        progress_label.pack(anchor="w", pady=(0, 4))

        elapsed_label = ttk.Label(container, textvariable=self.elapsed_text, foreground="#565f89")
        elapsed_label.pack(anchor="w", pady=(0, 12))

        include_organized = ttk.Checkbutton(
            container,
            text="Incluir carpeta 'Organizado' en esta ejecucion",
            variable=self.include_organized_var,
        )
        include_organized.pack(anchor="w", pady=(0, 10))

        include_comics = ttk.Checkbutton(
            container,
            text="Incluir carpeta 'ComicsCBZ' en esta ejecucion",
            variable=self.include_comics_var,
        )
        include_comics.pack(anchor="w", pady=(0, 6))

        include_pending = ttk.Checkbutton(
            container,
            text="Incluir carpeta 'PendientesRevision' en esta ejecucion",
            variable=self.include_pending_var,
        )
        include_pending.pack(anchor="w", pady=(0, 10))

        remove_duplicates = ttk.Checkbutton(
            container,
            text="Eliminar imagenes duplicadas (comparacion real por hash)",
            variable=self.remove_duplicates_var,
        )
        remove_duplicates.pack(anchor="w", pady=(0, 6))

        group_similar = ttk.Checkbutton(
            container,
            text="Agrupar imagenes por similitud de nombre (Screenshots/Facebook/etc.)",
            variable=self.group_similar_images_var,
        )
        group_similar.pack(anchor="w", pady=(0, 12))

        status = ttk.Label(container, textvariable=self.status_text, foreground="#7aa2f7")
        status.pack(anchor="w", pady=(0, 10))

        buttons_frame = ttk.Frame(container)
        buttons_frame.pack(anchor="e")
        self.cancel_btn = ttk.Button(buttons_frame, text="Cancelar", command=self._cancel_organizer, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))
        self.run_btn = ttk.Button(buttons_frame, text="Organizar ahora", command=self._run_organizer)
        self.run_btn.pack(side=tk.RIGHT)

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona la carpeta raiz a organizar")
        if folder:
            self.selected_path.set(folder)
            self.status_text.set(f"Estado: ruta seleccionada -> {folder}")
        else:
            self.status_text.set("Estado: no se selecciono carpeta.")

    @staticmethod
    def _normalize_input_path(raw_path: str) -> Path:
        # Permite usar "~" y variables de entorno en rutas escritas manualmente.
        expanded = os.path.expandvars(os.path.expanduser(raw_path.strip()))
        return Path(expanded).resolve()

    def _run_organizer(self) -> None:
        if self.is_running:
            return

        raw_folder = self.selected_path.get().strip()
        if not raw_folder:
            messagebox.showwarning("Falta ruta", "Selecciona una carpeta antes de ejecutar.")
            self.status_text.set("Estado: falta ruta para iniciar.")
            return

        folder_path = self._normalize_input_path(raw_folder)
        folder = str(folder_path)
        self.selected_path.set(folder)

        if not folder_path.exists() or not folder_path.is_dir():
            messagebox.showerror("Ruta invalida", f"La ruta no existe o no es carpeta:\n{folder}")
            self.status_text.set("Estado: ruta invalida, revisa el texto ingresado.")
            return

        confirm = messagebox.askyesno(
            "Confirmar reorganizacion",
            (
                "Se reorganizaran los archivos de esta ruta y sus subcarpetas.\n\n"
                f"Ruta: {folder}\n\n"
                "Deseas continuar?"
            ),
        )
        if not confirm:
            self.status_text.set("Estado: operacion cancelada por el usuario.")
            return

        try:
            self.is_running = True
            self.cancel_event.clear()
            self.run_started_at = time.time()
            self.progress_value.set(0)
            self.progress_text.set("Progreso: escaneando archivos...")
            self.elapsed_text.set("Tiempo transcurrido: 00:00")
            self.status_text.set("Estado: trabajando...")
            self._start_indeterminate_progress()
            if self.run_btn:
                self.run_btn.config(state=tk.DISABLED)
            if self.cancel_btn:
                self.cancel_btn.config(state=tk.NORMAL)

            def worker() -> None:
                try:
                    organizer = MediaOrganizer(
                        folder_path,
                        include_organized_scan=self.include_organized_var.get(),
                        include_comics_scan=self.include_comics_var.get(),
                        include_pending_scan=self.include_pending_var.get(),
                        remove_duplicate_images=self.remove_duplicates_var.get(),
                        group_similar_images=self.group_similar_images_var.get(),
                    )

                    def on_progress(current: int, total: int, detail: str) -> None:
                        self.ui_queue.put(("progress", current, total, detail))

                    stats = organizer.organize(progress_callback=on_progress, cancel_event=self.cancel_event)
                    self.ui_queue.put(("done", stats, organizer.cancel_requested))
                except Exception as exc:
                    self.ui_queue.put(("error", str(exc)))

            self.worker_thread = threading.Thread(target=worker, daemon=True)
            self.worker_thread.start()
            self._poll_ui_queue()
        except Exception as exc:
            self._finish_run()
            messagebox.showerror("Error", f"No se pudo completar el proceso:\n{exc}")
            self.status_text.set(f"Estado: error -> {exc}")

    def _poll_ui_queue(self) -> None:
        while not self.ui_queue.empty():
            item = self.ui_queue.get_nowait()
            item_type = item[0]
            if item_type == "progress":
                _, current, total, detail = item
                if self.indeterminate_active and total > 0:
                    self._stop_indeterminate_progress()
                percent = (current / total * 100.0) if total > 0 else 100.0
                self.progress_value.set(percent)
                self.progress_text.set(f"Progreso: {current}/{total}")
                self.status_text.set(f"Estado: {detail}")
            elif item_type == "done":
                _, stats, was_cancelled = item
                self._finish_run()
                if was_cancelled:
                    messagebox.showinfo(
                        "Proceso cancelado",
                        (
                            "La organizacion fue cancelada por el usuario.\n\n"
                            f"Multimedia movida: {stats.moved_media}\n"
                            f"CBZ agrupados: {stats.moved_cbz}\n"
                            f"Otros archivos movidos: {stats.moved_other}\n"
                            f"Imagenes duplicadas eliminadas: {stats.deleted_duplicate_images}\n"
                            f"Imagenes agrupadas por nombre: {stats.grouped_similar_images}\n"
                            f"Carpetas vacias eliminadas: {stats.deleted_dirs}\n"
                            f"Errores: {stats.errors}"
                        ),
                    )
                    self.status_text.set("Estado: proceso cancelado.")
                else:
                    messagebox.showinfo(
                        "Proceso completado",
                        (
                            "Organizacion finalizada.\n\n"
                            f"Multimedia movida: {stats.moved_media}\n"
                            f"CBZ agrupados: {stats.moved_cbz}\n"
                            f"Otros archivos movidos: {stats.moved_other}\n"
                            f"Imagenes duplicadas eliminadas: {stats.deleted_duplicate_images}\n"
                            f"Imagenes agrupadas por nombre: {stats.grouped_similar_images}\n"
                            f"Carpetas vacias eliminadas: {stats.deleted_dirs}\n"
                            f"Errores: {stats.errors}"
                        ),
                    )
                    self.status_text.set(
                        "Estado: completado. "
                        f"Multimedia={stats.moved_media}, CBZ={stats.moved_cbz}, "
                        f"Otros={stats.moved_other}, Duplicadas={stats.deleted_duplicate_images}, "
                        f"Agrupadas={stats.grouped_similar_images}, Errores={stats.errors}"
                    )
                    self.progress_value.set(100.0)
            elif item_type == "error":
                _, error_message = item
                self._finish_run()
                messagebox.showerror("Error", f"No se pudo completar el proceso:\n{error_message}")
                self.status_text.set(f"Estado: error -> {error_message}")

        if self.is_running:
            self._update_elapsed_time()
            self.root.after(120, self._poll_ui_queue)

    def _cancel_organizer(self) -> None:
        if not self.is_running:
            return
        self.cancel_event.set()
        self.status_text.set("Estado: cancelando proceso, espera...")
        if self.cancel_btn:
            self.cancel_btn.config(state=tk.DISABLED)

    def _finish_run(self) -> None:
        self.is_running = False
        self._stop_indeterminate_progress()
        self.run_started_at = None
        if self.run_btn:
            self.run_btn.config(state=tk.NORMAL)
        if self.cancel_btn:
            self.cancel_btn.config(state=tk.DISABLED)

    def _update_elapsed_time(self) -> None:
        if self.run_started_at is None:
            return
        elapsed_seconds = int(time.time() - self.run_started_at)
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        self.elapsed_text.set(f"Tiempo transcurrido: {minutes:02d}:{seconds:02d}")

    def _start_indeterminate_progress(self) -> None:
        if not self.indeterminate_active:
            self.progress_bar.config(mode="indeterminate")
            self.progress_bar.start(12)
            self.indeterminate_active = True

    def _stop_indeterminate_progress(self) -> None:
        if self.indeterminate_active:
            self.progress_bar.stop()
            self.progress_bar.config(mode="determinate")
            self.indeterminate_active = False


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    apply_dark_theme(root, style)
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    tab_auto = ttk.Frame(notebook, padding=4)
    tab_gallery = ttk.Frame(notebook, padding=4)
    notebook.add(tab_auto, text="  Organizacion automatica  ")
    notebook.add(tab_gallery, text="  Galeria manual  ")
    _auto = OrganizerApp(tab_auto)
    _gallery = GalleryManualFrame(tab_gallery)
    _ = (_auto, _gallery)
    root.mainloop()


if __name__ == "__main__":
    main()
