"""Sign view: play the last signed result in the avatar WebView."""

from __future__ import annotations

from oarumi.types import TranslationResult
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from desktop.state import AppState
from desktop.widgets.avatar import AvatarWidget


class SignView(QWidget):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self._state = state
        self._last_sigml: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self._hint = QLabel("Run a translation with target modality = signed, then press Play.")
        outer.addWidget(self._hint)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self._avatar = AvatarWidget()
        splitter.addWidget(self._avatar)

        self._sigml_box = QPlainTextEdit(readOnly=True)
        self._sigml_box.setPlaceholderText("SiGML will appear here.")
        splitter.addWidget(self._sigml_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)

        row = QHBoxLayout()
        self._play_btn = QPushButton("Play sign")
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self._play)
        row.addWidget(self._play_btn)
        row.addStretch(1)
        outer.addLayout(row)

    def update_from_result(self, result: TranslationResult) -> None:
        payload = result.modalities.get("signed")
        if not payload:
            return
        sigml = str(payload.get("sigml", ""))
        self._last_sigml = sigml
        self._sigml_box.setPlainText(sigml)
        self._play_btn.setEnabled(bool(sigml))
        self._hint.setText(f"Last result ready ({payload.get('gloss', '?')}). Press Play.")
        if sigml:
            self._avatar.play_sigml(sigml)

    def _play(self) -> None:
        if self._last_sigml:
            self._avatar.play_sigml(self._last_sigml)
