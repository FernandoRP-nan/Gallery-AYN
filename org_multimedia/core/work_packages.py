"""Paquetes de obra: agrupación por firma regex del nombre + orden natural con desempate temporal."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path

from .gallery_paths import natural_sort_key, normalize_filename_for_sort
from .image_exif import path_photo_timestamp_ns, prefetch_exif_timestamps
from .name_masks import MaskFolderRegistry, parse_stem, extract_numeric_indices_from_tokens

WORK_PACKAGE_GAP_NS = 5 * 60 * 1_000_000_000
NUMERADOS_LABEL = "Numerados"
_OUTER_QUOTES = ('"', "'")

_PURE_NUM_RE = re.compile(r"^\d+$")
_XY_SPACE_PAREN_RE = re.compile(r"^(\d+)\s+\((\d+)\)$")
_XY_SPACE_PAREN_Z_RE = re.compile(r"^(\d+)\s+\((\d+)\)_(\d+)$")
_XY_PAREN_RE = re.compile(r"^(\d+)\((\d+)\)$")
_XY_PAREN_Z_RE = re.compile(r"^(\d+)\((\d+)\)_(\d+)$")
_VOL_CHAPTER_RE = re.compile(r"^(\d+)_(\d+)")
_TEXT_SERIES_RE = re.compile(r"^([A-Za-z]+-\d+)")
_TEXT_UNDERSCORE_RE = re.compile(r"^((?:[A-Za-z]+_)+)")
_DASH_PAIR_RE = re.compile(r"^(\d+)\s*[-_.]\s*(\d+)$")
_SPACE_PAIR_RE = re.compile(r"^(\d+)\s+(\d+)$")


@dataclass(frozen=True)
class WorkPackageSortConfig:
    use_dynamic_regex: bool = False
    mask_registry: MaskFolderRegistry | None = None
    prefer_exif_timestamp: bool = False

    def with_paths(self, paths: list[Path]) -> WorkPackageSortConfig:
        if not self.use_dynamic_regex:
            return self
        return WorkPackageSortConfig(
            use_dynamic_regex=True,
            mask_registry=MaskFolderRegistry.from_paths(paths),
            prefer_exif_timestamp=self.prefer_exif_timestamp,
        )


def path_effective_timestamp_ns(path: Path) -> int:
    """EXIF DateTimeOriginal/DateTime; respaldo ctime → mtime."""
    return path_photo_timestamp_ns(str(path))


def path_timestamp_ns(path: Path) -> int:
    return path_effective_timestamp_ns(path)


def temporal_base_from_ns(ts_ns: int) -> str:
    if ts_ns <= 0:
        return "unknown-date"
    try:
        return datetime.fromtimestamp(ts_ns / 1_000_000_000).strftime("%Y-%m-%d")
    except (OSError, OverflowError, ValueError):
        return "unknown-date"


def _grouping_stem(path: Path) -> str:
    """Stem sin normalizar copias del navegador; preserva series «X (Y)»."""
    text = str(path.name or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in _OUTER_QUOTES:
        text = text[1:-1].strip()
    return Path(text).stem


def _normalized_stem(path: Path) -> str:
    return Path(normalize_filename_for_sort(path.name)).stem


def text_series_key(stem: str) -> str | None:
    text = str(stem or "")
    if not text or text[0].isdigit():
        return None
    if m := _TEXT_SERIES_RE.match(text):
        return m.group(1)
    if m := _TEXT_UNDERSCORE_RE.match(text):
        return m.group(1)
    return None


def _filename_numeric_indices_standard(stem: str) -> tuple[int | None, int | None, int]:
    """Extracción fija de base/sufijo (rápida; comportamiento por defecto)."""
    text = str(stem or "").strip()
    if not text:
        return None, None, 0

    if m := _XY_SPACE_PAREN_Z_RE.match(text):
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    if m := _XY_SPACE_PAREN_RE.match(text):
        return int(m.group(1)), int(m.group(2)), 0
    if m := _XY_PAREN_Z_RE.match(text):
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    if m := _XY_PAREN_RE.match(text):
        return int(m.group(1)), int(m.group(2)), 0
    if m := _VOL_CHAPTER_RE.match(text):
        return int(m.group(1)), int(m.group(2)), 0

    m_first = re.search(r"\d+", text)
    base = int(m_first.group()) if m_first else None

    suffix: int | None = None
    if m := re.search(r"\((\d+)\)", text):
        suffix = int(m.group(1))
    elif m := re.search(r"[\s\-_](\d+)\s*$", text):
        cand = int(m.group(1))
        if base is None or cand != base:
            suffix = cand

    return base, suffix, 0


def _filename_numeric_indices_from_mask(stem: str) -> tuple[int | None, int | None, int]:
    """Inferencia por tokenización/máscara (sin regex fijos)."""
    tokens = parse_stem(stem).tokens
    return extract_numeric_indices_from_tokens(tokens)


def filename_numeric_indices(
    stem: str,
    config: WorkPackageSortConfig | None = None,
) -> tuple[int | None, int | None, int]:
    """Índices numéricos; máscaras automáticas solo si use_dynamic_regex."""
    cfg = config or WorkPackageSortConfig()
    if cfg.use_dynamic_regex:
        if cfg.mask_registry is not None:
            # Búsqueda por stem en el registro del escaneo actual
            for parsed in cfg.mask_registry.by_path.values():
                if parsed.stem == stem:
                    return extract_numeric_indices_from_tokens(parsed.tokens)
        return _filename_numeric_indices_from_mask(stem)
    return _filename_numeric_indices_standard(stem)


NAME_CLUSTER_PRIMARY_KEYS = frozenset({"name", "name_base", "name_suffix"})


def should_cluster_after_sort(
    sort_keys: list[tuple[str, bool]],
    *,
    allow_cluster: bool = True,
) -> bool:
    """Evita empaquetado global si hay mes EXIF o si el primario no es nombre."""
    if not allow_cluster or not sort_keys:
        return False
    if any(sk == "exif_month" for sk, _ in sort_keys):
        return False
    return sort_keys[0][0] in NAME_CLUSTER_PRIMARY_KEYS


def directed_number_key(value: int | None, desc: bool) -> tuple[int, int]:
    """Tupla ordenable; ausente siempre al final."""
    if value is None:
        return (1, 0)
    return (0, -value if desc else value)


def _series_inner_sort_tuple(
    stem: str,
    config: WorkPackageSortConfig | None = None,
) -> tuple[int, int, int, int] | None:
    """Compatibilidad interna: series con base/sufijo/terciario."""
    base, suffix, tertiary = filename_numeric_indices(stem, config)
    if suffix is None and tertiary == 0:
        return None
    spaced = bool(_XY_SPACE_PAREN_RE.match(stem) or _XY_SPACE_PAREN_Z_RE.match(stem))
    return (
        1 if spaced else 0,
        base if base is not None else 0,
        suffix if suffix is not None else 0,
        tertiary,
    )


def grouping_stem(path: Path) -> str:
    """Stem para índices numéricos (preserva «X (Y)»)."""
    return _grouping_stem(path)


def padding_signature(stem: str) -> str:
    """Llave primaria de agrupación: firma regex del nombre (sin fecha)."""
    text = str(stem or "").strip()
    if not text:
        return "empty"

    if m := _XY_SPACE_PAREN_Z_RE.match(text):
        return f"series-spaced-{m.group(1)}"
    if m := _XY_SPACE_PAREN_RE.match(text):
        return f"series-spaced-{m.group(1)}"

    if m := _XY_PAREN_Z_RE.match(text):
        return f"series-{m.group(1)}"
    if m := _XY_PAREN_RE.match(text):
        return f"series-{m.group(1)}"

    if _PURE_NUM_RE.fullmatch(text):
        if len(text) == 1:
            return "digit-pad-1"
        if len(text) == 2 and text[0] == "0":
            return "digit-pad-2"
        return "numerados"

    if m := _VOL_CHAPTER_RE.match(text):
        vol = m.group(1).lstrip("0") or "0"
        return f"vol:{vol}"

    if key := text_series_key(text):
        return f"text:{key}"

    return f"other:{text[:32]}"


def nomenclature_signature(stem: str) -> str:
    return padding_signature(stem)


def group_key_for_path(path: Path, config: WorkPackageSortConfig | None = None) -> str:
    cfg = config or WorkPackageSortConfig()
    if cfg.use_dynamic_regex and cfg.mask_registry is not None:
        return cfg.mask_registry.group_key(path)
    return padding_signature(_grouping_stem(path))


def package_name_key(stem: str) -> str:
    return padding_signature(stem)


def stem_structure_fingerprint(stem: str) -> str:
    return padding_signature(stem)


def signature_display(sig: str) -> str:
    if sig == "digit-pad-1":
        return f"{NUMERADOS_LABEL} (1 dígito)"
    if sig == "digit-pad-2":
        return f"{NUMERADOS_LABEL} (01-09)"
    if sig == "numerados":
        return NUMERADOS_LABEL
    if sig.startswith("series-spaced-"):
        return f"{sig[14:]} (serie)"
    if sig.startswith("series-"):
        return f"{sig[7:]}(serie)"
    if sig.startswith("vol:"):
        return f"Vol {sig[4:]}"
    if sig.startswith("text:"):
        return sig[5:]
    if sig.startswith("other:"):
        return sig[6:]
    return sig


def work_category_for_stem(stem: str) -> str:
    return signature_display(padding_signature(stem))


def path_package_timestamp_ns(path: Path, *, prefer_exif: bool) -> int:
    if prefer_exif:
        return path_effective_timestamp_ns(path)
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _package_sort_key(path: Path, config: WorkPackageSortConfig | None = None) -> tuple:
    """Orden interno de paquete: base → sufijo → terciario → fecha."""
    cfg = config or WorkPackageSortConfig()
    if cfg.use_dynamic_regex and cfg.mask_registry is not None:
        base, suffix, tertiary = cfg.mask_registry.numeric_indices_for_path(path)
    else:
        stem = _grouping_stem(path)
        base, suffix, tertiary = filename_numeric_indices(stem, cfg)
    return (
        base if base is not None else 2**31,
        suffix if suffix is not None else 2**31,
        tertiary,
        path_package_timestamp_ns(path, prefer_exif=cfg.prefer_exif_timestamp),
    )


def _signature_sort_key(sig: str) -> tuple:
    if sig == "digit-pad-1":
        return (0, 0, "")
    if sig == "digit-pad-2":
        return (0, 1, "")
    if sig == "numerados":
        return (0, 2, "")
    if sig.startswith("series-spaced-"):
        return (1, 0, natural_sort_key(sig[14:]))
    if sig.startswith("series-"):
        return (1, 1, natural_sort_key(sig[7:]))
    if sig.startswith("vol:"):
        return (2, 0, natural_sort_key(sig[4:]))
    if sig.startswith("text:"):
        return (3, 0, sig[5:].casefold())
    return (4, 0, sig.casefold())


def _mask_sort_key(sig: str) -> tuple:
    if sig.startswith("mask:"):
        return (5, 0, sig[5:])
    return _signature_sort_key(sig)


def cluster_work_packages(
    paths: list[Path],
    *,
    gap_ns: int = WORK_PACKAGE_GAP_NS,
    sort_config: WorkPackageSortConfig | None = None,
    prefetch_exif: bool = False,
) -> list[list[Path]]:
    del gap_ns
    if not paths:
        return []

    cfg = (sort_config or WorkPackageSortConfig()).with_paths(paths)
    if prefetch_exif or cfg.prefer_exif_timestamp:
        prefetch_exif_timestamps(paths)
    pkg_key = partial(_package_sort_key, config=cfg)

    buckets: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        buckets[group_key_for_path(path, cfg)].append(path)

    sort_sig = _mask_sort_key if cfg.use_dynamic_regex else _signature_sort_key
    packages: list[list[Path]] = []
    for key in sorted(buckets.keys(), key=sort_sig):
        packages.append(sorted(buckets[key], key=pkg_key))
    return packages


def work_package_section_key(
    package: list[Path],
    index: int,
    config: WorkPackageSortConfig | None = None,
) -> str:
    if not package:
        return f"empty:{index}"
    sig = group_key_for_path(package[0], config)
    safe = re.sub(r"[^\w.\-+]+", "_", sig)[:64]
    return f"{safe}:{index}"


def work_package_section_label(
    package: list[Path],
    config: WorkPackageSortConfig | None = None,
) -> str:
    if not package:
        return "?"
    cfg = config or WorkPackageSortConfig()
    if cfg.use_dynamic_regex and cfg.mask_registry is not None:
        return cfg.mask_registry.section_label(package)
    return signature_display(group_key_for_path(package[0], cfg))


def _section_anchor_ts(package: list[Path]) -> int:
    if not package:
        return 0
    return max(path_effective_timestamp_ns(p) for p in package)


def section_summary_from_paths(
    package: list[Path],
    category: str | None = None,
    sort_config: WorkPackageSortConfig | None = None,
) -> dict:
    cfg = sort_config or WorkPackageSortConfig()
    pkg_key = partial(_package_sort_key, config=cfg)
    sorted_pkg = sorted(package, key=pkg_key)
    names = [p.name for p in sorted_pkg]
    sig = group_key_for_path(sorted_pkg[0], cfg) if sorted_pkg else ""
    anchor_ts = _section_anchor_ts(sorted_pkg)
    return {
        "category": category or work_package_section_label(sorted_pkg, cfg),
        "count": len(names),
        "first": names[0] if names else "",
        "last": names[-1] if names else "",
        "files": names,
        "sample": None,
        "sortType": "Máscara + numérico" if cfg.use_dynamic_regex else "Natural + fecha",
        "groupKey": sig,
        "paddingSignature": sig,
        "temporalBase": temporal_base_from_ns(anchor_ts),
    }


def sort_section_summaries_by_recent_date(summaries: list[dict]) -> list[dict]:
    """Prioriza secciones con fecha de ancla más reciente (solo para informes)."""

    def _key(row: dict) -> tuple:
        base = str(row.get("temporalBase") or "unknown-date")
        if base == "unknown-date":
            return ("", str(row.get("groupKey") or row.get("category") or ""))
        return (base, str(row.get("groupKey") or row.get("category") or ""))

    return sorted(summaries, key=_key, reverse=True)


def reorder_paths_into_work_packages(
    ordered: list[Path],
    *,
    gap_ns: int = WORK_PACKAGE_GAP_NS,
    sort_config: WorkPackageSortConfig | None = None,
    prefetch_exif: bool = False,
) -> tuple[list[Path], list[tuple[int, int, str, str]]]:
    cfg = (sort_config or WorkPackageSortConfig()).with_paths(ordered)
    packages = cluster_work_packages(ordered, gap_ns=gap_ns, sort_config=cfg, prefetch_exif=prefetch_exif)
    pkg_key = partial(_package_sort_key, config=cfg)
    position = {id(path): idx for idx, path in enumerate(ordered)}

    def _first_pos(pkg: list[Path]) -> int:
        return min(position.get(id(path), 10**12) for path in pkg)

    packages.sort(key=_first_pos)

    flat: list[Path] = []
    spans: list[tuple[int, int, str, str]] = []
    for index, package in enumerate(packages):
        start = len(flat)
        inner = sorted(package, key=pkg_key)
        flat.extend(inner)
        spans.append(
            (
                start,
                len(flat),
                work_package_section_key(inner, index, cfg),
                work_package_section_label(inner, cfg),
            )
        )
    return flat, spans


def flatten_work_packages(
    packages: list[list[Path]],
    *,
    sort_config: WorkPackageSortConfig | None = None,
) -> list[Path]:
    cfg = sort_config or WorkPackageSortConfig()
    pkg_key = partial(_package_sort_key, config=cfg)
    out: list[Path] = []
    for package in packages:
        out.extend(sorted(package, key=pkg_key))
    return out
