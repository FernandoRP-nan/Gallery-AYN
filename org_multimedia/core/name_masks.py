"""Tokenización y máscaras lógicas de nombres (modo «Normalizar patrones»)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_SEP_CHAR_TO_MASK: dict[str, str] = {
    "(": "PARENTESIS_ABRE",
    ")": "PARENTESIS_CIERRA",
    "_": "GUION_BAJO",
    "-": "GUION",
    " ": "ESPACIO",
    ".": "PUNTO",
}

_MASK_DISPLAY: dict[str, str] = {
    "DIGITOS": "n",
    "LETRAS": "a",
    "PARENTESIS_ABRE": "(",
    "PARENTESIS_CIERRA": ")",
    "GUION_BAJO": "_",
    "GUION": "-",
    "ESPACIO": " ",
    "PUNTO": ".",
    "OTRO": "?",
}

UNIQUE_PATTERN_LABEL = "Patrón Único"


@dataclass(frozen=True)
class NameToken:
    kind: str
    value: str


@dataclass(frozen=True)
class ParsedName:
    stem: str
    tokens: tuple[NameToken, ...]
    mask_key: str


def tokenize_stem(stem: str) -> tuple[NameToken, ...]:
    """Descompone el stem en DIGITOS, LETRAS y separadores."""
    text = str(stem or "").strip()
    if not text:
        return ()

    out: list[NameToken] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isdigit():
            j = i + 1
            while j < len(text) and text[j].isdigit():
                j += 1
            out.append(NameToken("DIGITOS", text[i:j]))
            i = j
            continue
        if ch.isalpha():
            j = i + 1
            while j < len(text) and text[j].isalpha():
                j += 1
            out.append(NameToken("LETRAS", text[i:j]))
            i = j
            continue
        kind = _SEP_CHAR_TO_MASK.get(ch, "OTRO")
        out.append(NameToken(kind, ch))
        i += 1
    return tuple(out)


def mask_key_from_tokens(tokens: tuple[NameToken, ...]) -> str:
    if not tokens:
        return "VACIO"
    return "+".join(t.kind for t in tokens)


def mask_key_to_display(mask_key: str) -> str:
    parts = mask_key.split("+")
    return "".join(_MASK_DISPLAY.get(p, p) for p in parts)


def parse_stem(stem: str) -> ParsedName:
    tokens = tokenize_stem(stem)
    return ParsedName(stem=stem, tokens=tokens, mask_key=mask_key_from_tokens(tokens))


def extract_numeric_indices_from_tokens(
    tokens: tuple[NameToken, ...],
) -> tuple[int | None, int | None, int]:
    """Base = 1.er dígito, subíndice = 2.º, terciario = 3.er (orden matemático int)."""
    digits = [int(t.value) for t in tokens if t.kind == "DIGITOS"]
    base = digits[0] if len(digits) >= 1 else None
    suffix = digits[1] if len(digits) >= 2 else None
    tertiary = digits[2] if len(digits) >= 3 else 0
    return base, suffix, tertiary


def _path_key(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


@dataclass
class MaskFolderRegistry:
    """Índice de máscaras inferidas para una carpeta (escaneo actual)."""

    by_path: dict[str, ParsedName]
    mask_counts: dict[str, int]

    @classmethod
    def from_stems(cls, stems: list[str]) -> MaskFolderRegistry:
        by_path: dict[str, ParsedName] = {}
        counts: dict[str, int] = {}
        for stem in stems:
            parsed = parse_stem(stem)
            by_path[stem] = parsed
            counts[parsed.mask_key] = counts.get(parsed.mask_key, 0) + 1
        return cls(by_path=by_path, mask_counts=counts)

    @classmethod
    def from_paths(cls, paths: list[Path]) -> MaskFolderRegistry:
        entries: dict[str, ParsedName] = {}
        counts: dict[str, int] = {}
        for path in paths:
            stem = Path(path.name).stem
            if len(stem) >= 2 and stem[0] == stem[-1] and stem[0] in ('"', "'"):
                stem = stem[1:-1].strip()
            parsed = parse_stem(stem)
            entries[_path_key(path)] = parsed
            counts[parsed.mask_key] = counts.get(parsed.mask_key, 0) + 1
        return cls(by_path=entries, mask_counts=counts)

    def parsed_for_path(self, path: Path) -> ParsedName:
        return self.by_path[_path_key(path)]

    def group_key(self, path: Path) -> str:
        parsed = self.parsed_for_path(path)
        return f"mask:{parsed.mask_key}"

    def is_unique_mask(self, path: Path) -> bool:
        parsed = self.parsed_for_path(path)
        return self.mask_counts.get(parsed.mask_key, 0) == 1

    def section_label(self, package: list[Path]) -> str:
        if not package:
            return "?"
        parsed = self.parsed_for_path(package[0])
        if self.mask_counts.get(parsed.mask_key, 0) == 1:
            return f"{UNIQUE_PATTERN_LABEL} · {parsed.stem}"
        display = mask_key_to_display(parsed.mask_key)
        return f"Máscara · {display}"

    def numeric_indices_for_path(self, path: Path) -> tuple[int | None, int | None, int]:
        parsed = self.parsed_for_path(path)
        return extract_numeric_indices_from_tokens(parsed.tokens)
