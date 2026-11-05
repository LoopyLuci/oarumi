"""Translate view: pick a source language and modality, then read the result."""

from __future__ import annotations

import json

from oarumi.pivot import phrasebook
from oarumi.types import TranslationRequest, TranslationResult
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from desktop.languages import language_name, modality_name, mood_name
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
        outer.setContentsMargins(24, 20, 24, 12)
        outer.setSpacing(14)

        title = QLabel("Translate")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        subtitle = QLabel(
            "Turn a phrase into Oarumi, then hear it, see it signed, or read it by touch."
        )
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(subtitle)

        outer.addWidget(self._build_input_card())
        outer.addWidget(self._build_result_card(), 1)

        self._status = QLabel("Ready.")
        self._status.setObjectName("statusLine")
        outer.addWidget(self._status)

    def _build_input_card(self) -> QFrame:
        card = _card()
        grid = QGridLayout(card)
        grid.setContentsMargins(20, 18, 20, 18)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        self._lang = QComboBox()
        for code in _SUPPORTED_LANGS:
            self._lang.addItem(language_name(code), code)
        _select_data(self._lang, "es")

        self._modality = QComboBox()
        for code in _MODALITIES:
            self._modality.addItem(modality_name(code), code)
        _select_data(self._modality, "spoken")

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a phrase, for example hola")
        self._input.setText("hola")
        self._input.setClearButtonEnabled(True)

        self._translate_btn = QPushButton("Translate to Oarumi")
        self._translate_btn.setObjectName("translate_btn")
        self._translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        grid.addWidget(_field_label("Source language"), 0, 0)
        grid.addWidget(_field_label("Target modality"), 0, 1)
        grid.addWidget(self._lang, 1, 0)
        grid.addWidget(self._modality, 1, 1)
        grid.addWidget(_field_label("Phrase"), 2, 0, 1, 2)
        grid.addWidget(self._input, 3, 0, 1, 2)
        grid.addWidget(self._translate_btn, 4, 0, 1, 2)
        return card

    def _build_result_card(self) -> QFrame:
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self._result_status = QLabel("No translation yet")
        self._result_status.setObjectName("resultStatus")
        header.addWidget(self._result_status)
        header.addStretch(1)
        self._degraded = QLabel("Degraded")
        self._degraded.setObjectName("badge_degraded")
        self._degraded.setProperty("severity", "warn")
        self._degraded.setVisible(False)
        header.addWidget(self._degraded)
        layout.addLayout(header)

        self._surface = QLabel("Your Oarumi sentence will appear here.")
        self._surface.setObjectName("surfaceText")
        self._surface.setWordWrap(True)
        self._surface.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._surface)

        meta = QGridLayout()
        meta.setHorizontalSpacing(32)
        meta.setVerticalSpacing(2)
        self._mood_value = _meta_value()
        self._meaning_value = _meta_value()
        self._output_value = _meta_value()
        for column, (key, value) in enumerate(
            (
                ("Mood", self._mood_value),
                ("Meaning", self._meaning_value),
                ("Output", self._output_value),
            )
        ):
            meta.addWidget(_meta_key(key), 0, column)
            meta.addWidget(value, 1, column)
        meta.setColumnStretch(3, 1)
        layout.addLayout(meta)

        self._details = QPlainTextEdit(readOnly=True)
        self._details.setPlaceholderText("Details appear after a translation.")
        self._trace = TraceView()
        self._tabs = QTabWidget()
        self._tabs.addTab(self._details, "Details")
        self._tabs.addTab(self._trace, "Trace")
        layout.addWidget(self._tabs, 1)
        return card

    def _wire(self) -> None:
        self._translate_btn.clicked.connect(self._on_translate)
        self._input.returnPressed.connect(self._on_translate)

    # --- slots ----------------------------------------------------------

    def _on_translate(self) -> None:
        text = self._input.text().strip()
        if not text:
            self.status_message.emit("Enter some text first.")
            return

        req = TranslationRequest(
            text=text,
            lang=_data(self._lang),
            modality=_data(self._modality),  # type: ignore[arg-type]
        )

        try:
            result = self._state.pipeline.translate(req)
        except Exception as exc:
            self._result_status.setText("Translation failed")
            _restyle(self._result_status, "warn")
            self._status.setText(f"Translation failed: {exc}")
            self.status_message.emit("Translation failed.")
            return

        self._state.set_last_result(result)
        self._render_result(result)
        self.result_ready.emit(result)
        self.status_message.emit(f"Translated ({'degraded' if result.degraded else 'ok'}).")

    def _render_result(self, result: TranslationResult) -> None:
        self._trace.show_result(result)
        self._details.setPlainText(_details_text(result))

        self._surface.setText(result.surface.to_string())
        self._mood_value.setText(mood_name(result.surface.mood))
        self._meaning_value.setText(f"{result.pivot['text']} ({result.pivot['source']})")
        self._output_value.setText(", ".join(modality_name(m) for m in result.modalities))

        self._degraded.setVisible(result.degraded)
        self._result_status.setText("Translated with fallback" if result.degraded else "Translated")
        _restyle(self._result_status, "warn" if result.degraded else "ok")
        self._status.setText("Translated." if not result.degraded else "Translated (degraded).")

    # --- test hooks -----------------------------------------------------

    def set_input(self, text: str) -> None:
        self._input.setText(text)

    def set_language(self, code: str) -> None:
        _select_data(self._lang, code)

    def set_modality(self, modality: str) -> None:
        _select_data(self._modality, modality)

    def click_translate(self) -> None:
        self._on_translate()

    @property
    def output_text(self) -> str:
        return self._details.toPlainText()


# --- helpers ----------------------------------------------------------------


def _details_text(result: TranslationResult) -> str:
    lines: list[str] = []
    lines.append(f"Surface:   {result.surface.to_string()}")
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

    return "\n".join(lines)


def _card() -> QFrame:
    card = QFrame()
    card.setObjectName("card")
    return card


def _field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    return label


def _meta_key(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("metaKey")
    return label


def _meta_value() -> QLabel:
    label = QLabel("—")
    label.setObjectName("metaValue")
    label.setWordWrap(True)
    return label


def _restyle(widget: QWidget, severity: str) -> None:
    """Apply a QSS ``severity`` property and re-polish so the new colour shows."""
    widget.setProperty("severity", severity)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _select_data(combo: QComboBox, data: str) -> None:
    idx = combo.findData(data)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def _data(combo: QComboBox) -> str:
    value = combo.currentData()
    return str(value) if value is not None else ""
