"""Dictionary view: search words, browse them by root class, and read one entry.

Entry model and labels: docs/DICTIONARY.md. The Android Dictionary screen shows the
same fields, so the status wording here matches ui/dictionary/FormStatus.kt.
"""

from __future__ import annotations

from oarumi.db import Lexeme, Prime, Sense, Sign
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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

PRIMES = "primes"
# (label, key). A key is a root class, None for every word, or PRIMES for the inventory.
FILTERS: tuple[tuple[str, str | None], ...] = (
    ("All", None),
    ("Nouns", "noun"),
    ("Verbs", "verb"),
    ("Modifiers", "modifier"),
    ("Particles", "particle"),
    ("Primes", PRIMES),
)
_ID_ROLE = Qt.ItemDataRole.UserRole
# Screen readers announce this text for a row; the visible card is split over three labels.
_ACCESSIBLE_ROLE = Qt.ItemDataRole.AccessibleTextRole


def form_status_label(status: str) -> str:
    """Same wording as the Android app. Anything unknown reads as pending, never approved."""
    if status == "signed_off":
        return "signed off"
    if status == "provisional":
        return "provisional"
    return "pending linguist sign-off"


def lexeme_summary(lexeme: Lexeme) -> str:
    """One sentence per word, the same wording as lexemeSummary in EntryText.kt."""
    click = f", click {lexeme.click}" if lexeme.click else ""
    return (
        f"{lexeme.phon_form}{click}, meaning {lexeme.gloss}, {lexeme.root_class}, "
        f"frequency {lexeme.frequency}, {form_status_label(lexeme.form_status)}"
    )


def prime_summary(prime: Prime) -> str:
    """One sentence per prime, the same wording as primeSummary in EntryText.kt."""
    return (
        f"Prime {prime.id}, meaning {prime.gloss}, "
        f"spoken form {form_status_label(prime.form_status)}"
    )


def prime_matches(prime: Prime, query: str) -> bool:
    needle = query.strip().lower()
    if not needle:
        return True
    return any(needle in text.lower() for text in (prime.id, prime.gloss, prime.spoken_form))


def format_entry(lexeme: Lexeme, senses: list[Sense], signs: list[Sign]) -> str:
    """Plain-text entry: headword, gloss, metadata, senses with primes, and signs."""
    click = f"  [{lexeme.click}]" if lexeme.click else ""
    lines = [
        f"{lexeme.phon_form}{click}",
        lexeme.gloss,
        f"root class {lexeme.root_class}  ·  frequency {lexeme.frequency}"
        f"  ·  {form_status_label(lexeme.form_status)}",
        "",
        "Senses",
    ]
    if not senses:
        lines.append("  No senses recorded yet.")
    for sense in senses:
        primes = " ".join(sense.primes) if sense.primes else "none yet"
        lines.append(f"  {sense.sense_no}. {sense.gloss}")
        lines.append(f"     primes: {primes}  ·  {form_status_label(sense.decomp_status)}")
    lines += ["", "Signs"]
    if not signs:
        lines.append("  No sign recorded yet. Placeholder, pending linguist sign-off.")
    for sign in signs:
        hamnosys = sign.hamnosys or "not set (placeholder)"
        lines.append(f"  HamNoSys: {hamnosys}  ·  {form_status_label(sign.form_status)}")
    return "\n".join(lines)


class DictionaryView(QWidget):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self._state = state
        self._query = ""
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 12)
        outer.setSpacing(14)

        title = QLabel("Dictionary")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        subtitle = QLabel(
            "Search words and their glosses, or browse by root class. "
            "Select a word to read its senses and signs."
        )
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(subtitle)

        row = QHBoxLayout()
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search words, for example who, manu or interrogative")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setAccessibleName("Search the dictionary")
        self._search_box.setAccessibleDescription(
            "Matches words, glosses and sense glosses. Leave blank to browse."
        )
        self._search_box.textChanged.connect(self._search)
        row.addWidget(self._search_box, 1)

        self._filter = QComboBox()
        self._filter.setObjectName("dictionaryFilter")
        self._filter.setAccessibleName("Root class filter")
        for label, key in FILTERS:
            self._filter.addItem(label, key)
        self._filter.currentIndexChanged.connect(self._on_filter_changed)
        row.addWidget(self._filter)

        self._count = QLabel()
        self._count.setObjectName("countLabel")
        row.addWidget(self._count)
        outer.addLayout(row)

        body = QHBoxLayout()
        self._results = QListWidget()
        self._results.setObjectName("entryList")
        self._results.setAccessibleName("Dictionary entries")
        self._results.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self._results.currentItemChanged.connect(self._on_pick)
        body.addWidget(self._results, 2)

        self._detail = QLabel()
        self._detail.setObjectName("entryDetail")
        self._detail.setAccessibleName("Entry detail")
        self._detail.setWordWrap(True)
        self._detail.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.addWidget(self._detail, 3)
        outer.addLayout(body, 1)

        self._show_detail(None)

    def focus_search(self) -> None:
        self._search_box.setFocus()

    def _on_filter_changed(self, _index: int) -> None:
        self._refresh()

    def _search(self, query: str) -> None:
        self._query = query
        self._refresh()

    def _refresh(self) -> None:
        self._results.clear()
        key = self._filter.currentData()
        if key == PRIMES:
            self._fill_primes()
        else:
            self._fill_lexemes(key)
        if self._results.count():
            self._results.setCurrentRow(0)
        else:
            self._show_detail(None)

    def _fill_lexemes(self, root_class: str | None) -> None:
        db = self._state.db
        if self._query.strip():
            lexemes = db.search_lexemes(self._query, limit=100, root_class=root_class)
        else:
            lexemes = db.browse_lexemes(root_class, limit=500)
        self._set_count(len(lexemes), "word")
        for lx in lexemes:
            meta = f"{lx.root_class}  ·  frequency {lx.frequency}"
            if lx.click:
                meta = f"{meta}  ·  {lx.click}"
            if lx.form_status != "signed_off":
                meta = f"{meta}  ·  {form_status_label(lx.form_status)}"
            item = self._add_entry(lx.phon_form, lx.gloss, meta)
            item.setData(_ID_ROLE, lx.id)
            item.setData(_ACCESSIBLE_ROLE, lexeme_summary(lx))
        if not lexemes:
            self._add_message(
                "No words match that search."
                if self._query.strip()
                else "No words in this class yet."
            )

    def _fill_primes(self) -> None:
        primes = [p for p in self._state.db.all_primes() if prime_matches(p, self._query)]
        self._set_count(len(primes), "prime")
        for prime in primes:
            meta = f"Prime  ·  {prime.id}  ·  spoken form {form_status_label(prime.form_status)}"
            item = self._add_entry(prime.spoken_form, prime.gloss, meta)
            item.setData(_ACCESSIBLE_ROLE, prime_summary(prime))
        if not primes:
            self._add_message("No primes match that search.")

    def _set_count(self, n: int, noun: str) -> None:
        self._count.setText(f"{n} {noun}{'' if n == 1 else 's'}")

    def _on_pick(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        lexeme_id = current.data(_ID_ROLE) if current is not None else None
        self._show_detail(lexeme_id)

    def show_entry(self, lexeme_id: int) -> None:
        """Show one word in the detail pane, whatever the search currently holds."""
        self._show_detail(lexeme_id)

    def _show_detail(self, lexeme_id: int | None) -> None:
        if lexeme_id is None:
            self._detail.setText("Select a word to read its entry.")
            return
        db = self._state.db
        lexeme = db.get_lexeme(lexeme_id)
        if lexeme is None:
            self._detail.setText("This word is not in the dictionary.")
            return
        self._detail.setText(
            format_entry(lexeme, db.senses_for(lexeme_id), db.signs_for(lexeme_id))
        )

    def _add_entry(self, title: str, gloss: str, meta: str) -> QListWidgetItem:
        item = QListWidgetItem(self._results)
        row = _entry_widget(title, gloss, meta)
        item.setSizeHint(row.sizeHint())
        self._results.setItemWidget(item, row)
        return item

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
