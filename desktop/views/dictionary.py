"""Dictionary view: search lexemes, or browse the NSM primes when the search is empty."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
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
        outer.setContentsMargins(24, 20, 24, 12)
        outer.setSpacing(14)

        title = QLabel("Dictionary")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        subtitle = QLabel(
            "Search Oarumi words and their glosses. Leave the search empty to browse the primes."
        )
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(subtitle)

        row = QHBoxLayout()
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search words, for example who or manu")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.textChanged.connect(self._search)
        row.addWidget(self._search_box, 1)

        self._count = QLabel()
        self._count.setObjectName("countLabel")
        row.addWidget(self._count)
        outer.addLayout(row)

        self._results = QListWidget()
        self._results.setObjectName("entryList")
        self._results.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._results.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        outer.addWidget(self._results, 1)

    def focus_search(self) -> None:
        self._search_box.setFocus()

    def _search(self, query: str) -> None:
        self._results.clear()
        if query.strip():
            lexemes = self._state.db.search_lexemes(query, limit=100)
            self._count.setText(f"{len(lexemes)} match{'es' if len(lexemes) != 1 else ''}")
            for lx in lexemes:
                meta = f"{lx.root_class}  ·  frequency {lx.frequency}"
                if lx.click:
                    meta = f"{meta}  ·  {lx.click}"
                self._add_entry(lx.phon_form, lx.gloss, meta)
            if not lexemes:
                self._add_message("No words match that search.")
        else:
            primes = self._state.db.all_primes()
            self._count.setText(f"{len(primes)} primes")
            for prime in primes:
                self._add_entry(prime.spoken_form, prime.gloss, f"Prime  ·  {prime.id}")

    def _add_entry(self, title: str, gloss: str, meta: str) -> None:
        item = QListWidgetItem(self._results)
        row = _entry_widget(title, gloss, meta)
        item.setSizeHint(row.sizeHint())
        self._results.setItemWidget(item, row)

    def _add_message(self, text: str) -> None:
        item = QListWidgetItem(text, self._results)
        item.setFlags(Qt.ItemFlag.NoItemFlags)


def _entry_widget(title: str, gloss: str, meta: str) -> QWidget:
    # The outer widget only adds the gap between rows; the card carries the look.
    row = QWidget()
    row.setObjectName("entryRow")
    outer = QVBoxLayout(row)
    outer.setContentsMargins(0, 4, 0, 4)

    card = QFrame()
    card.setObjectName("entryCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(2)

    head = QLabel(title)
    head.setObjectName("entryTitle")
    layout.addWidget(head)

    body = QLabel(gloss)
    body.setObjectName("entryGloss")
    layout.addWidget(body)

    foot = QLabel(meta)
    foot.setObjectName("entryMeta")
    layout.addWidget(foot)

    outer.addWidget(card)
    return row
