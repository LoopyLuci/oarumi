"""Restart Oarumi so settings that apply at start-up take effect."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication

import desktop


def restart_application() -> bool:
    """Start a fresh copy of the app, then quit this one.

    The new copy runs from the project folder, so ``-m desktop.app`` resolves the
    same way it did for the original launch. Returns False if it could not start,
    in which case this copy keeps running.
    """
    project = Path(desktop.__file__).resolve().parent.parent
    result: object = QProcess.startDetached(sys.executable, ["-m", "desktop.app"], str(project))
    if isinstance(result, tuple):  # PySide6 versions differ in the return shape
        result = result[0]
    started = bool(result)
    if started:
        QApplication.quit()
    return started
