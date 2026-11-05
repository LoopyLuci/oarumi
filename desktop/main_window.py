"""Main window: tabbed workspace, menus and a persistent status bar."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import QMainWindow, QMessageBox, QTabWidget

from desktop import __version__
from desktop.restart import restart_application
from desktop.settings import EnvManager, default_manager
from desktop.state import AppState
from desktop.views.dictionary import DictionaryView
from desktop.views.learn import LearnView
from desktop.views.packs import PacksView
from desktop.views.settings import SettingsView
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

        self.tabs = QTabWidget(self)
        self.translate_view = TranslateView(state)
        self.sign_view = SignView(state)
        self.learn_view = LearnView(state)
        self.dictionary_view = DictionaryView(state)
        self.packs_view = PacksView(state.packs)
        self.settings_view = SettingsView(self._env_manager)

        self.tabs.addTab(self.translate_view, "Translate")
        self.tabs.addTab(self.sign_view, "Sign")
        self.tabs.addTab(self.learn_view, "Learn")
        self.tabs.addTab(self.dictionary_view, "Dictionary")
        self.tabs.addTab(self.packs_view, "Packs")
        self.tabs.addTab(self.settings_view, "Settings")
        self.setCentralWidget(self.tabs)

        self.status = StatusBarWidget(state)
        self.statusBar().addPermanentWidget(self.status, 1)

        self._build_menu()

        # Wire cross-view updates.
        self.translate_view.result_ready.connect(self.sign_view.update_from_result)
        self.translate_view.result_ready.connect(self._on_result)
        self.translate_view.status_message.connect(self._show_message)
        self.settings_view.status_message.connect(self._show_message)
        self.packs_view.status_message.connect(self._show_message)
        self.packs_view.packs_changed.connect(self.translate_view.refresh_language_support)
        self.settings_view.restart_requested.connect(self._restart)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    # --- menus ----------------------------------------------------------

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(
            self._action("&Open settings folder", self.settings_view.open_settings_folder)
        )
        file_menu.addSeparator()
        file_menu.addAction(self._action("&Quit", self.close, "Ctrl+Q"))

        view_menu = self.menuBar().addMenu("&View")
        for index in range(self.tabs.count()):
            label = self.tabs.tabText(index)
            view_menu.addAction(
                self._action(
                    f"&{index + 1}  {label}", self._select_index(index), f"Ctrl+{index + 1}"
                )
            )

        settings_menu = self.menuBar().addMenu("&Settings")
        settings_menu.addAction(self._action("&Preferences…", self.show_settings, "Ctrl+,"))

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self._action("&About Oarumi", self._about))

    def _select_index(self, index: int) -> Callable[[], None]:
        def select() -> None:
            self.tabs.setCurrentIndex(index)

        return select

    def _action(
        self, text: str, slot: Callable[[], object], shortcut: str | None = None
    ) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(lambda *_: slot())
        return action

    def show_settings(self) -> None:
        self.select_tab("Settings")

    def select_tab(self, label: str) -> None:
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == label:
                self.tabs.setCurrentIndex(index)
                return

    def _about(self) -> None:
        backend = self._env_manager.secret_backend_name() or "not available"
        QMessageBox.about(
            self,
            "About Oarumi",
            f"Oarumi {__version__}\n\n"
            f"Settings file: {self._env_manager.settings_path}\n"
            f"Keychain: {backend}",
        )

    # --- unsaved settings -------------------------------------------------

    def _resolve_unsaved_settings(self) -> bool:
        """Ask what to do with unsaved settings. True means carry on."""
        if not self.settings_view.has_pending_changes():
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved settings")
        box.setText("You have settings changes that are not saved.")
        box.setInformativeText("Save them before continuing?")
        save = box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save:
            return self.settings_view.save()
        if clicked is discard:
            self.settings_view.revert()
            return True
        return False

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override name)
        if not self._resolve_unsaved_settings():
            event.ignore()
            return
        super().closeEvent(event)

    def _restart(self) -> None:
        if not self._resolve_unsaved_settings():
            return
        if not restart_application():
            QMessageBox.warning(
                self,
                "Restart",
                "Oarumi could not start a new copy. Close it and open it again.",
            )

    # --- slots ----------------------------------------------------------

    def _show_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 6000)

    def _on_result(self, result) -> None:  # type: ignore[no-untyped-def]
        self.status.refresh()

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.widget(index) is self.dictionary_view:
            self.dictionary_view.focus_search()
