"""Learn view: NSM prime flashcards."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.state import AppState

_FACT_KEYS = (
    ("Category", "category"),
    ("Spoken form", "spoken_form"),
    ("Signed form", "signed_form"),
    ("Tactile form", "tactile_form"),
    ("Combinators", "combinators"),
    ("NSM version", "nsm_version"),
)


class LearnView(QWidget):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self._state = state
        self._primes = state.db.all_primes()
        self._idx = 0
        self._build_ui()
        self._render()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 12)
        outer.setSpacing(14)

        title = QLabel("Learn")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        subtitle = QLabel(
            "Practise the primes, the small set of meanings that every Oarumi sentence is built from."
        )
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(6)

        self._title = QLabel("NSM prime")
        self._title.setObjectName("prime_title")
        card_layout.addWidget(self._title)

        self._gloss = QLabel()
        self._gloss.setObjectName("prime_gloss")
        self._gloss.setWordWrap(True)
        card_layout.addWidget(self._gloss)

        card_layout.addSpacing(18)

        facts = QGridLayout()
        facts.setHorizontalSpacing(24)
        facts.setVerticalSpacing(8)
        self._fact_values: dict[str, QLabel] = {}
        for index, (label, key) in enumerate(_FACT_KEYS):
            key_label = QLabel(label)
            key_label.setObjectName("factKey")
            value = QLabel()
            value.setObjectName("factValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            facts.addWidget(key_label, index, 0)
            facts.addWidget(value, index, 1)
            self._fact_values[key] = value
        facts.setColumnStretch(1, 1)
        card_layout.addLayout(facts)
        card_layout.addStretch(1)

        outer.addWidget(card, 1)

        row = QHBoxLayout()
        self._prev = QPushButton("← Previous")
        self._prev.setObjectName("secondaryButton")
        self._next = QPushButton("Next →")
        self._prev.clicked.connect(self._prev_clicked)
        self._next.clicked.connect(self._next_clicked)
        row.addWidget(self._prev)
        row.addStretch(1)
        self._count = QLabel()
        self._count.setObjectName("countLabel")
        row.addWidget(self._count)
        row.addStretch(1)
        row.addWidget(self._next)
        outer.addLayout(row)

    def _render(self) -> None:
        if not self._primes:
            self._title.setText("No primes loaded")
            self._gloss.setText("Run ./scripts/bootstrap.sh to build the language database.")
            for value in self._fact_values.values():
                value.setText("")
            self._count.setText("")
            return
        prime = self._primes[self._idx]
        self._title.setText(prime.id)
        self._gloss.setText(prime.gloss)
        self._fact_values["category"].setText(prime.category)
        self._fact_values["spoken_form"].setText(prime.spoken_form)
        self._fact_values["signed_form"].setText(prime.signed_form)
        self._fact_values["tactile_form"].setText(prime.tactile_form)
        self._fact_values["combinators"].setText(", ".join(prime.combinators) or "none")
        self._fact_values["nsm_version"].setText(prime.nsm_version)
        self._count.setText(f"{self._idx + 1} of {len(self._primes)}")

    def _prev_clicked(self) -> None:
        if not self._primes:
            return
        self._idx = (self._idx - 1) % len(self._primes)
        self._render()

    def _next_clicked(self) -> None:
        if not self._primes:
            return
        self._idx = (self._idx + 1) % len(self._primes)
        self._render()
