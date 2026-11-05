"""Main window: tabbed workspace + persistent status bar."""

from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QTabWidget

from desktop.settings import EnvManager, default_manager
from desktop.settings.dialog import SettingsDialog
from desktop.state import AppState
from desktop.views.dictionary import DictionaryView
from desktop.views.learn import LearnView
from desktop.views.sign import SignView
from desktop.views.translate import TranslateView
from desktop.widgets.status_bar import StatusBarWidget


class MainWindow(QMainWindow):
    def __init__(self, state: AppState, env_manager: EnvManager | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Oarumi")
        self.resize(1100, 720)

        self._state = state
        self._env_manager = env_manager or default_manager()
        self._build_menu()

        self.tabs = QTabWidget(self)
        self.translate_view = TranslateView(state)
        self.sign_view = SignView(state)
        self.learn_view = LearnView(state)
        self.dictionary_view = DictionaryView(state)

        self.tabs.addTab(self.translate_view, "Translate")
        self.tabs.addTab(self.sign_view, "Sign")
        self.tabs.addTab(self.learn_view, "Learn")
        self.tabs.addTab(self.dictionary_view, "Dictionary")

        self.setCentralWidget(self.tabs)

        self.status = StatusBarWidget(state)
        self.statusBar().addPermanentWidget(self.status, 1)

        # Wire cross-view updates.
        self.translate_view.result_ready.connect(self.sign_view.update_from_result)
        self.translate_view.result_ready.connect(self._on_result)
        self.translate_view.status_message.connect(
            lambda msg: self.statusBar().showMessage(msg, 4000)
        )
        self.tabs.currentChanged.connect(self._on_tab_changed)

    # --- menus ----------------------------------------------------------

    def _build_menu(self) -> None:
        settings_menu = self.menuBar().addMenu("&Settings")
        env_action = QAction("&Environment variables…", self)
        env_action.setShortcut(QKeySequence("Ctrl+,"))
        env_action.triggered.connect(self.open_environment_settings)
        settings_menu.addAction(env_action)

    def open_environment_settings(self) -> None:
        SettingsDialog(self._env_manager, self).exec()

    # --- slots ----------------------------------------------------------

    def _on_result(self, result) -> None:  # type: ignore[no-untyped-def]
        self.status.refresh()

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.widget(index) is self.dictionary_view:
            self.dictionary_view.focus_search()
