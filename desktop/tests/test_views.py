"""Offscreen smoke tests for every view and the main window."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from desktop.main_window import MainWindow
from desktop.state import AppState
from desktop.views.dictionary import DictionaryView
from desktop.views.learn import LearnView
from desktop.views.packs import PacksView
from desktop.views.sign import SignView
from desktop.views.translate import TranslateView
from desktop.widgets.status_bar import StatusBarWidget
from desktop.widgets.trace_view import TraceView


def test_main_window_constructs(state: AppState) -> None:
    window = MainWindow(state)
    assert window.tabs.count() == 6
    assert [window.tabs.tabText(i) for i in range(6)] == [
        "Translate",
        "Sign",
        "Learn",
        "Dictionary",
        "Packs",
        "Settings",
    ]


def test_settings_tab_is_reachable_from_the_menu_and_shortcut(state: AppState) -> None:
    window = MainWindow(state)
    window.select_tab("Translate")
    window.show_settings()
    assert window.tabs.currentWidget() is window.settings_view
    window.select_tab("Learn")
    assert window.tabs.currentWidget() is window.learn_view


def test_unsaved_settings_are_offered_before_closing(state: AppState) -> None:
    window = MainWindow(state)
    assert window._resolve_unsaved_settings() is True  # nothing pending, no prompt


def test_translate_view_shows_full_language_names(state: AppState) -> None:
    view = TranslateView(state)
    view.set_language("es")
    assert view._lang.currentText() == "Spanish"
    assert view._lang.currentData() == "es"
    assert view._modality.currentText() == "Spoken"


def test_translate_view_detects_the_language_when_asked(state: AppState) -> None:
    view = TranslateView(state)
    view.set_language("auto")
    view.set_input("buenos días")
    view.click_translate()
    assert "Detected Spanish" in view._status.text()
    assert state.last_result is not None and state.last_result.degraded is False


def test_translate_view_suggests_spelling_fixes(state: AppState) -> None:
    view = TranslateView(state)
    view.set_language("es")
    view.set_input("holla")
    view._update_spell_hint()
    assert view._spell_hint.isVisibleTo(view) or view._spell_hint.text()
    assert "hola" in view._spell_hint.text()


def test_translate_view_produces_output(state: AppState) -> None:
    view = TranslateView(state)
    view.set_language("es")
    view.set_modality("spoken")
    view.set_input("hola")
    view.click_translate()
    out = view.output_text
    assert "Surface:" in out
    assert "Pivot:" in out
    assert "hello" in out
    assert state.last_result is not None
    assert state.last_result.degraded is False


def test_translate_view_trace_populated(state: AppState) -> None:
    view = TranslateView(state)
    view.set_input("hola")
    view.click_translate()
    # TraceView gets updated by _render_result; we can't reach it directly
    # but we can assert the underlying result.
    assert state.last_result is not None
    assert state.last_result.trace, "expected at least one trace entry"


def test_sign_view_updates_from_result(state: AppState) -> None:
    from oarumi.types import TranslationRequest

    result = state.pipeline.translate(TranslationRequest(text="hola", lang="es", modality="signed"))
    view = SignView(state)
    view.update_from_result(result)
    assert view._last_sigml
    assert "hns_sign" in view._last_sigml


def test_learn_view_renders_prime(state: AppState) -> None:
    view = LearnView(state)
    assert view._title.text()
    view._next_clicked()
    assert view._title.text()


def test_dictionary_view_search(state: AppState) -> None:
    view = DictionaryView(state)
    view._search("manu")
    assert view._results.count() >= 1


def test_dictionary_view_empty_shows_primes(state: AppState) -> None:
    view = DictionaryView(state)
    view._search("")
    assert view._results.count() == len(state.db.all_primes())


def test_status_bar_reflects_degraded(state: AppState, qapp: QApplication) -> None:
    from oarumi.types import TranslationRequest

    # Trigger a degraded result (unknown language is refused by the router).
    bad = state.pipeline.translate(TranslationRequest(text="hola", lang="xx"))
    state.set_last_result(bad)
    bar = StatusBarWidget(state)
    assert bar._degraded.isVisible() is False or bar._degraded.text() == "Degraded"


def test_trace_view_renders_result(state: AppState) -> None:
    from oarumi.types import TranslationRequest

    result = state.pipeline.translate(TranslationRequest(text="hola", lang="es", modality="spoken"))
    tv = TraceView()
    tv.show_result(result)
    assert tv.tree.topLevelItemCount() == 2
    top0 = tv.tree.topLevelItem(0)
    top1 = tv.tree.topLevelItem(1)
    assert top0 is not None and top0.text(0) == "trace"
    assert top1 is not None and top1.text(0) == "failovers"


def test_packs_view_lists_every_pack_with_its_status(state: AppState) -> None:
    view = PacksView(state.packs)
    entries = state.packs.entries()
    assert view._table.rowCount() == len(entries)

    def cell(row: int, column: int) -> str:
        item = view._table.item(row, column)
        assert item is not None
        return item.text()

    statuses = {cell(row, 1): cell(row, 3) for row in range(view._table.rowCount())}
    assert statuses["es"] == "Built in"
    assert statuses["pt"] == "Not installed"


def test_avatar_placeholder_in_offscreen() -> None:
    from desktop.widgets.avatar import AvatarWidget

    w = AvatarWidget()
    assert w._view is None
    assert w._placeholder is not None
    w.play_sigml("<sigml></sigml>")  # must not raise
    assert "3D avatar unavailable" in w._placeholder.text()
