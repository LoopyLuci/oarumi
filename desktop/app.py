"""Desktop application entry point.

python -m desktop.app
oarumi-desktop
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from desktop.main_window import MainWindow
from desktop.settings import (
    EnvManager,
    SettingsError,
    default_manager,
    install_redaction,
    secrets_from_environ,
)
from desktop.state import AppState


def load_settings() -> EnvManager:
    """Load stored settings into the environment and install log redaction.

    Redaction is installed first, so nothing logged after this point can leak a
    stored secret. A bad settings file is reported and skipped, not fatal.
    """
    manager = default_manager()
    secrets = secrets_from_environ(os.environ)
    try:
        report = manager.apply()
        if report.skipped_secret:
            logging.getLogger(__name__).warning(
                "secure storage unavailable; skipped: %s", ", ".join(report.skipped_secret)
            )
        secrets += manager.secret_values()
    except SettingsError as exc:
        logging.getLogger(__name__).warning("settings not loaded: %s", exc)
    install_redaction(secrets)
    return manager


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parent.parent, *here.parents):
        if (candidate / "language" / "oarumi.db").exists():
            return candidate
    return here.parent.parent


def build_state() -> AppState:
    root = Path(os.environ.get("OARUMI_HOME", _find_repo_root())).resolve()
    return AppState.from_env(repo_root=root)


def main(argv: list[str] | None = None, *, start_tab: str | None = None) -> int:
    app = QApplication.instance() or QApplication(argv or sys.argv)
    assert isinstance(app, QApplication)
    app.setApplicationName("Oarumi")
    app.setOrganizationName("Oarumi")

    qss = Path(__file__).parent / "resources" / "style.qss"
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))

    env_manager = load_settings()

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

    window = MainWindow(state, env_manager=env_manager)
    if start_tab is not None:
        window.select_tab(start_tab)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
