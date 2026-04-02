"""Entrada única para PyInstaller en Windows (no importar desde org_multimedia.__main__)."""

from __future__ import annotations

if __name__ == "__main__":
    from org_multimedia.cli import main

    main()
