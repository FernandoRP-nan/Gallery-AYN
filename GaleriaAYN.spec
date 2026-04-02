# -*- mode: python ; coding: utf-8 -*-
# Construir en Windows desde la raíz del repo:
#   cd webui && npm ci && npm run build && cd ..
#   pyinstaller --clean GaleriaAYN.spec
# Salida: dist/GaleriaAYN/  (carpeta portable: comprimir en .zip para tus amigos)

import sys
from pathlib import Path

block_cipher = None

# SPEC lo define PyInstaller: ruta absoluta al fichero .spec
ROOT = Path(SPEC).resolve().parent

webui_dist = ROOT / "webui" / "dist"
if not webui_dist.is_dir():
    print(
        "ERROR: Falta webui/dist. Ejecuta primero: cd webui && npm ci && npm run build",
        file=sys.stderr,
    )
    sys.exit(1)

datas = [(str(webui_dist), "webui/dist")]

hiddenimports = [
    "org_multimedia",
    "org_multimedia.app",
    "org_multimedia.app_webview",
    "org_multimedia.app_tk",
    "org_multimedia.web_api",
    "org_multimedia.settings",
    "org_multimedia.bundle_paths",
    "org_multimedia.cli",
    "org_multimedia.linux_gui_env",
    "org_multimedia.pywebview_bridge_return",
    "org_multimedia.pywebview_qt_json",
    "PIL",
    "PIL.Image",
]

extra_binaries = []
try:
    from PyInstaller.utils.hooks import collect_all, collect_submodules

    hiddenimports += collect_submodules("org_multimedia")
    d2, b2, h2 = collect_all("webview")
    datas += d2
    extra_binaries = b2
    hiddenimports += h2
except Exception:
    pass

a = Analysis(
    [str(ROOT / "packaging" / "windows_entry.py")],
    pathex=[str(ROOT)],
    binaries=extra_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GaleriaAYN",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GaleriaAYN",
)
