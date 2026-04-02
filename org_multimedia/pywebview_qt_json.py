"""Parche PyWebView + Qt WebEngine: QJsonValue.toString() devuelve '' en arrays/objetos.

Solo se reemplaza BrowserView._convert_string. NO se toca JSBridge.call: sustituirlo rompe
los @Slot de Qt y el canal con JavaScript (Examinar, rutas recientes, etc.).
"""

from __future__ import annotations

import json
import os
import sys


def patch_qt_qjson_bridge() -> None:
    if os.environ.get("PYWEBVIEW_GUI", "").lower() != "qt":
        return
    try:
        from qtpy.QtCore import QJsonDocument
        from webview.platforms.qt import BrowserView
    except Exception as e:
        print(f"[organizador] pywebview Qt: sin módulo qt ({e})", file=sys.stderr)
        return
    if getattr(BrowserView, "_organizador_qt_patch_done", False):
        return

    def _qjson_to_json_text(result: object) -> str | None:
        if result is None:
            return None
        if isinstance(result, (bytes, bytearray)):
            return result.decode("utf-8", errors="replace")
        if isinstance(result, str):
            return result
        if isinstance(result, bool):
            return json.dumps(result)
        if isinstance(result, (int, float)) and not isinstance(result, bool):
            return json.dumps(result)
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)
        if hasattr(result, "isNull") and callable(result.isNull):
            try:
                if result.isNull():
                    return None
                if result.isBool():
                    return json.dumps(result.toBool())
                if result.isDouble():
                    return json.dumps(result.toDouble())
                if result.isString():
                    return result.toString()
                if result.isArray():
                    return bytes(QJsonDocument(result.toArray()).toJson()).decode("utf-8").strip()
                if result.isObject():
                    return bytes(QJsonDocument(result.toObject()).toJson()).decode("utf-8").strip()
            except Exception:
                pass
        return str(result) if result is not None else None

    def _convert_string_fixed(result: object) -> object:
        return _qjson_to_json_text(result)

    BrowserView._convert_string = staticmethod(_convert_string_fixed)
    BrowserView._organizador_qt_patch_done = True

    print("[organizador] Parche Qt: solo _convert_string (QJson array/objeto).", file=sys.stderr)
