"""``python -m desktop.settings``: CLI when given arguments, otherwise the GUI."""

from __future__ import annotations

import sys


def _gui() -> int:
    from PySide6.QtWidgets import QApplication

    from desktop.settings.dialog import SettingsDialog
    from desktop.settings.manager import default_manager

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Oarumi")
    dialog = SettingsDialog(default_manager())
    dialog.exec()
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        from desktop.settings.cli import main

        raise SystemExit(main(sys.argv[1:]))
    raise SystemExit(_gui())
