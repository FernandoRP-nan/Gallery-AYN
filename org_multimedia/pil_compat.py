"""Carga opcional de Pillow para miniaturas y vista previa."""

try:
    from PIL import Image, ImageOps, ImageTk

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None  # type: ignore[misc, assignment]
    ImageOps = None  # type: ignore[misc, assignment]
    ImageTk = None  # type: ignore[misc, assignment]
