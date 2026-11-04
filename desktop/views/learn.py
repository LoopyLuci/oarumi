"""Learn view: NSM prime flashcards."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.state import AppState


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
        outer.setContentsMargins(24, 24, 24, 24)

        self._title = QLabel("NSM prime")
        self._title.setObjectName("prime_title")
        outer.addWidget(self._title)

        self._gloss = QLabel()
        self._gloss.setObjectName("prime_gloss")
        outer.addWidget(self._gloss)

        self._details = QLabel()
        self._details.setWordWrap(True)
        self._details.setObjectName("prime_details")
        outer.addWidget(self._details)

        outer.addStretch(1)

        row = QHBoxLayout()
        self._prev = QPushButton("← Previous")
        self._next = QPushButton("Next →")
        self._prev.clicked.connect(self._prev_clicked)
        self._next.clicked.connect(self._next_clicked)
        row.addWidget(self._prev)
        row.addStretch(1)
        self._count = QLabel()
        row.addWidget(self._count)
        row.addStretch(1)
        row.addWidget(self._next)
        outer.addLayout(row)

    def _render(self) -> None:
        if not self._primes:
            self._title.setText("No primes loaded")
            self._gloss.setText("Run ./scripts/bootstrap.sh")
            self._details.setText("")
            self._count.setText("")
            return
        prime = self._primes[self._idx]
        self._title.setText(prime.id)
        self._gloss.setText(prime.gloss)
        self._details.setText(
            f"category: {prime.category}\n"
            f"spoken form: {prime.spoken_form}\n"
            f"signed form: {prime.signed_form}\n"
            f"tactile form: {prime.tactile_form}\n"
            f"combinators: {', '.join(prime.combinators)}\n"
            f"nsm version: {prime.nsm_version}"
        )
        self._count.setText(f"{self._idx + 1} / {len(self._primes)}")

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
