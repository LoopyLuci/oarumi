"""Desktop application entry point.

python -m desktop.app
oarumi-desktop
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from desktop.main_window import MainWindow
from desktop.state import AppState


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parent.parent, *here.parents):
        if (candidate / "language" / "oarumi.db").exists():
            return candidate
    return here.parent.parent


def build_state() -> AppState:
    root = Path(os.environ.get("OARUMI_HOME", _find_repo_root())).resolve()
    return AppState.from_env(repo_root=root)


def main(argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(argv or sys.argv)
    assert isinstance(app, QApplication)
    app.setApplicationName("Oarumi")
    app.setOrganizationName("Oarumi")

    qss = Path(__file__).parent / "resources" / "style.qss"
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))

    try:
        state = build_state()
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Oarumi — startup failed",
            f"Could not initialise the engine.\n\n{exc}\n\n"
            f"Run ./scripts/bootstrap.sh if you have not yet seeded the language DB.",
        )
        traceback.print_exc()
        return 1

    window = MainWindow(state)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
