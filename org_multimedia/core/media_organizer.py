"""Motor de organizacion por fecha, CBZ y tipos (sin dependencia de tkinter)."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
import hashlib
import os
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path


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
        group_similar_visual: bool = False,
        visual_similarity_min: float = 0.82,
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
        self.group_similar_visual = group_similar_visual
        self.visual_similarity_min = max(0.5, min(0.98, float(visual_similarity_min)))
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

        if not self.cancel_requested and self.group_similar_visual:
            if progress_callback:
                progress_callback(processed, total_files, "Postproceso: IA visual (similitud)...")
            self.stats.grouped_similar_images += self._group_similar_visual_images(cancel_event)

        if not self.cancel_requested and self.group_similar_images:
            if progress_callback:
                progress_callback(processed, total_files, "Postproceso: agrupando por nombre...")
            self.stats.grouped_similar_images += self._group_similar_named_images(cancel_event)

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

    def _group_similar_visual_images(self, cancel_event: threading.Event | None) -> int:
        """Agrupa por similitud visual (aHash) en Organizado/AAAA/MM/Agrupadas/Visual-NNN/."""
        from ..ia.mess_clusters import cluster_paths_list

        moved_count = 0
        month_roots: set[Path] = set()
        for image_path in self.target_media_root.rglob("*"):
            if not image_path.is_file():
                continue
            if image_path.suffix.lower() not in self.IMAGE_EXTENSIONS:
                continue
            month_root = self._extract_month_root(image_path)
            if month_root is not None:
                month_roots.add(month_root)

        for month_root in sorted(month_roots):
            if cancel_event and cancel_event.is_set():
                self.cancel_requested = True
                return moved_count

            candidates: list[Path] = []
            for p in month_root.rglob("*"):
                if not p.is_file() or p.suffix.lower() not in self.IMAGE_EXTENSIONS:
                    continue
                rel = p.relative_to(month_root).parts
                if rel and rel[0] == "Agrupadas":
                    continue
                candidates.append(p)

            if len(candidates) < 2:
                continue

            result = cluster_paths_list(
                candidates,
                self.visual_similarity_min,
                cancel_event=cancel_event,
            )
            if result.get("cancelled"):
                self.cancel_requested = True
                return moved_count

            multi = [c for c in result.get("clusters", []) if int(c.get("count", 0)) >= 2]
            for idx, cluster in enumerate(multi, start=1):
                if cancel_event and cancel_event.is_set():
                    self.cancel_requested = True
                    return moved_count
                target_folder = month_root / "Agrupadas" / f"Visual-{idx:03d}"
                target_folder.mkdir(parents=True, exist_ok=True)
                for path_str in cluster.get("paths", []):
                    try:
                        self._move_with_collision_handling(Path(path_str), target_folder)
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


