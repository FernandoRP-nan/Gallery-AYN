"""Parche pywebview: el retorno del bridge usa json.dumps entre comillas simples en evaluate_js.

Con rutas Unicode (p. ej. Imágenes) o caracteres problemáticos, el JS puede fallar al evaluar
y las promesas del API quedan sin resolver o con JSON.parse roto. Codificar el JSON en base64
y decodificar en el cliente con atob + UTF-8 evita romper el literal embebido.

Basado en webview.util.js_bridge_call (pywebview); solo cambia el cuerpo de _call().
"""

from __future__ import annotations

import base64
import json
import logging
import traceback
import urllib.parse
from threading import Thread
from typing import Any

from webview.dom import _dnd_state

from .core.fs_path import normalize_path_string

logger = logging.getLogger("pywebview")


def _normalize_bridge_params(param: Any) -> Any:
    if isinstance(param, list):
        return [_normalize_bridge_value(x) for x in param]
    if isinstance(param, dict):
        return {k: _normalize_bridge_value(v) for k, v in param.items()}
    return _normalize_bridge_value(param)


def _looks_like_fs_path(value: str) -> bool:
    s = value.strip()
    if not s or s.startswith(("http://", "https://", "data:")):
        return False
    return s.startswith(("/", "~", "file:")) or "\\" in s


def _normalize_bridge_value(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_path_string(value) if _looks_like_fs_path(value) else value
    if isinstance(value, list):
        return [_normalize_bridge_value(x) for x in value]
    if isinstance(value, dict):
        return {k: _normalize_bridge_value(v) for k, v in value.items()}
    return value


def patch_js_bridge_return_value() -> None:
    import webview.util as wu

    if getattr(wu, "_organizador_js_bridge_return_patch_done", False):
        return

    def js_bridge_call(window: Any, func_name: str, param: Any, value_id: str) -> None:
        def _b64_js_str(obj: Any) -> str:
            raw = json.dumps(obj, ensure_ascii=False)
            b64 = base64.b64encode(raw.encode("utf-8")).decode("ascii")
            return f"decodeURIComponent(escape(atob('{b64}')))"

        def _call() -> None:
            try:
                result = func(*func_params)
                inner = _b64_js_str(result)
                retval = f"{{value: {inner}}}"
            except Exception as e:
                logger.error(traceback.format_exc())
                error = {
                    "message": str(e),
                    "name": type(e).__name__,
                    "stack": traceback.format_exc(),
                }
                inner = _b64_js_str(error)
                retval = f"{{isError: true, value: {inner}}}"

            window.evaluate_js(
                f'window.pywebview._returnValuesCallbacks["{func_name}"]["{value_id}"]({retval})'
            )

        def get_nested_attribute(obj: object, attr_str: str) -> object | None:
            attributes = attr_str.split(".")
            for attr in attributes:
                obj = getattr(obj, attr, None)
                if obj is None:
                    return None
            return obj

        if func_name == "pywebviewMoveWindow":
            window.move(*param)
            return

        if func_name == "pywebviewEventHandler":
            event = param["event"]
            node_id = param["nodeId"]
            element = window.dom._elements.get(node_id)

            if not element:
                return

            if event["type"] == "drop":
                files = event["dataTransfer"].get("files", [])
                for file in files:
                    path = [
                        item
                        for item in _dnd_state["paths"]
                        if urllib.parse.unquote(item[0]) == file["name"]
                    ]
                    if len(path) == 0:
                        continue

                    file["pywebviewFullPath"] = urllib.parse.unquote(path[0][1])
                    _dnd_state["paths"].remove(path[0])

            for handler in element._event_handlers.get(event["type"], []):
                thread = Thread(target=handler, args=(event,))
                thread.start()

            return

        if func_name == "pywebviewAsyncCallback":
            value = json.loads(param) if param is not None else None

            if callable(window._callbacks[value_id]):
                window._callbacks[value_id](value)
            else:
                logger.error(
                    f"Async function executed and callback is not callable. Returned value {value}"
                )

            del window._callbacks[value_id]
            return

        if func_name == "pywebviewStateUpdate":
            window.state.__setattr__(param["key"], param["value"], False)
            return

        if func_name == "pywebviewStateDelete":
            special_key = "__pywebviewHaltUpdate__" + param
            delattr(window.state, special_key)
            return

        func = window._functions.get(func_name) or get_nested_attribute(window._js_api, func_name)

        if func is not None:
            try:
                func_params = _normalize_bridge_params(param)
                thread = Thread(target=_call)
                thread.start()
            except Exception:
                logger.exception("Error occurred while evaluating function %s", func_name)
        else:
            logger.error("Function %s() does not exist", func_name)

    wu.js_bridge_call = js_bridge_call
    wu._organizador_js_bridge_return_patch_done = True
