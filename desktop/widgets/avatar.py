"""WebView wrapper around the bundled SiGML viewer.

If QtWebEngine cannot start (headless CI without sandbox), degrade to a
placeholder so the rest of the app still works.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

AVATAR_HTML = Path(__file__).resolve().parent.parent / "resources" / "avatar" / "index.html"


def _webengine_allowed() -> bool:
    if os.environ.get("OARUMI_DISABLE_AVATAR") == "1":
        return False
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return False
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401

        return True
    except ImportError:
        return False


class AvatarWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._view = None
        self._placeholder = None

        if _webengine_allowed():
            try:
                from PySide6.QtWebEngineWidgets import QWebEngineView

                self._view = QWebEngineView(self)
                self._view.load(QUrl.fromLocalFile(str(AVATAR_HTML)))
                layout.addWidget(self._view)
                return
            except Exception:
                self._view = None

        self._placeholder = QLabel(
            "3D avatar unavailable in this environment.\n"
            "SiGML is still produced and can be inspected below.",
            self,
        )
        self._placeholder.setWordWrap(True)
        layout.addWidget(self._placeholder)

    def play_sigml(self, xml: str) -> None:
        if self._view is not None:
            payload = json.dumps(xml)
            self._view.page().runJavaScript(f"window.playSigML({payload});")
        elif self._placeholder is not None:
            self._placeholder.setText("3D avatar unavailable. Last SiGML:\n\n" + xml[:400])
