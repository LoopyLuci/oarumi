"""Translate view: pick source language, modality, and read the result."""

from __future__ import annotations

import json

from oarumi.pivot import phrasebook
from oarumi.types import TranslationRequest, TranslationResult
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from desktop.state import AppState
from desktop.widgets.trace_view import TraceView

_SUPPORTED_LANGS = ("en", *phrasebook.supported_languages())
_MODALITIES = ("spoken", "signed", "tactile")


class TranslateView(QWidget):
    result_ready = Signal(object)  # TranslationResult
    status_message = Signal(str)

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self._state = state
        self._build_ui()
        self._wire()

    # --- construction ---------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        self._lang = QComboBox()
        for code in _SUPPORTED_LANGS:
            self._lang.addItem(code)
        self._lang.setCurrentText("es")

        self._modality = QComboBox()
        for m in _MODALITIES:
            self._modality.addItem(m)
        self._modality.setCurrentText("spoken")

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a phrase, e.g. «hola»")
        self._input.setText("hola")

        form.addRow("Source language", self._lang)
        form.addRow("Target modality", self._modality)
        form.addRow("Input", self._input)
        outer.addLayout(form)

        self._translate_btn = QPushButton("Translate to Oarumi")
        self._translate_btn.setObjectName("translate_btn")
        outer.addWidget(self._translate_btn)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self._output = QPlainTextEdit(readOnly=True)
        self._output.setPlaceholderText("Output will appear here.")
        splitter.addWidget(self._output)

        self._trace = TraceView()
        splitter.addWidget(self._trace)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)

        self._status = QLabel("Ready.")
        outer.addWidget(self._status)

    def _wire(self) -> None:
        self._translate_btn.clicked.connect(self._on_translate)
        self._input.returnPressed.connect(self._on_translate)

    # --- slots ----------------------------------------------------------

    def _on_translate(self) -> None:
        text = self._input.text().strip()
        if not text:
            self.status_message.emit("Enter some text first.")
            return

        lang = self._lang.currentText()
        modality = self._modality.currentText()
        req = TranslationRequest(text=text, lang=lang, modality=modality)  # type: ignore[arg-type]

        try:
            result = self._state.pipeline.translate(req)
        except Exception as exc:
            self._status.setText(f"Translation failed: {exc}")
            self.status_message.emit("Translation failed.")
            return

        self._state.set_last_result(result)
        self._render_result(result)
        self.result_ready.emit(result)
        self.status_message.emit(f"Translated ({'degraded' if result.degraded else 'ok'}).")

    def _render_result(self, result: TranslationResult) -> None:
        self._trace.show_result(result)
        self._output.clear()

        lines: list[str] = []
        surface = result.surface.to_string()
        lines.append(f"Surface:   {surface}")
        lines.append(f"Mood:      {result.surface.mood}")
        lines.append(f"Pivot:     {result.pivot['text']} ({result.pivot['source']})")
        lines.append(f"Degraded:  {result.degraded}")

        for modality, payload in result.modalities.items():
            lines.append("")
            lines.append(f"[{modality}]")
            if modality == "spoken":
                lines.append(f"  audio_path: {payload.get('audio_path')}")
                lines.append(f"  backend:    {payload.get('backend')}")
                lines.append(f"  phonemes:   {' '.join(payload.get('phoneme_stream', []))}")
            elif modality == "signed":
                lines.append("  sigml:")
                for line in str(payload.get("sigml", "")).splitlines():
                    lines.append(f"    {line}")
            elif modality == "tactile":
                lines.append("  protocol:")
                for line in json.dumps(payload.get("protocol", {}), indent=2).splitlines():
                    lines.append(f"    {line}")
            else:
                lines.append(f"  {json.dumps(payload, indent=2)}")

        if result.failover_events:
            lines.append("")
            lines.append("Failover events:")
            for ev in result.failover_events:
                lines.append(f"  {ev.get('component')}: {ev.get('trigger')} @ {ev.get('t')}")

        self._output.setPlainText("\n".join(lines))
        self._status.setText("Translated." if not result.degraded else "Translated (degraded).")

    # --- test hooks -----------------------------------------------------

    def set_input(self, text: str) -> None:
        self._input.setText(text)

    def set_language(self, code: str) -> None:
        idx = self._lang.findText(code)
        if idx >= 0:
            self._lang.setCurrentIndex(idx)

    def set_modality(self, modality: str) -> None:
        idx = self._modality.findText(modality)
        if idx >= 0:
            self._modality.setCurrentIndex(idx)

    def click_translate(self) -> None:
        self._on_translate()

    @property
    def output_text(self) -> str:
        return self._output.toPlainText()
