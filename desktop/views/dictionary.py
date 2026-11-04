"""Dictionary view: search lexemes and primes."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.state import AppState


class DictionaryView(QWidget):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self._state = state
        self._build_ui()
        self._search("")

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search lexemes (e.g. «who», «manu»)")
        self._search_box.textChanged.connect(self._search)
        outer.addWidget(self._search_box)

        self._results = QListWidget()
        outer.addWidget(self._results, 1)

    def focus_search(self) -> None:
        self._search_box.setFocus()

    def _search(self, query: str) -> None:
        self._results.clear()
        if query.strip():
            lexemes = self._state.db.search_lexemes(query, limit=100)
            for lx in lexemes:
                click = f" [{lx.click}]" if lx.click else ""
                QListWidgetItem(
                    f"{lx.phon_form}{click}  —  {lx.gloss}  ({lx.root_class}, freq {lx.frequency})",
                    self._results,
                )
            if not lexemes:
                QListWidgetItem("(no lexeme matches)", self._results)
        else:
            for prime in self._state.db.all_primes():
                QListWidgetItem(
                    f"{prime.spoken_form}  —  {prime.gloss}  [prime: {prime.id}]",
                    self._results,
                )
