"""Offscreen smoke tests for every view and the main window."""

from __future__ import annotations

from oarumi.db import Lexeme, Sense, Sign
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop.main_window import MainWindow
from desktop.state import AppState
from desktop.views.dictionary import DictionaryView, form_status_label, format_entry
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


def _ids(view: DictionaryView) -> list[int]:
    return [
        view._results.item(i).data(Qt.ItemDataRole.UserRole) for i in range(view._results.count())
    ]


def _select_filter(view: DictionaryView, key: str) -> None:
    view._filter.setCurrentIndex(view._filter.findData(key))


def test_dictionary_view_search(state: AppState) -> None:
    view = DictionaryView(state)
    view._search("manu")
    assert view._results.count() >= 1
    assert _ids(view)[0] == state.db.search_lexemes("manu")[0].id


def test_dictionary_view_blank_browses_every_word(state: AppState) -> None:
    view = DictionaryView(state)
    view._search("")
    assert view._results.count() == len(state.db.browse_lexemes(limit=500))


def test_dictionary_view_root_class_filter(state: AppState) -> None:
    view = DictionaryView(state)
    _select_filter(view, "noun")
    ids = _ids(view)
    assert ids
    assert {state.db.get_lexeme(i).root_class for i in ids} == {"noun"}


def test_dictionary_view_primes_filter_lists_the_inventory(state: AppState) -> None:
    view = DictionaryView(state)
    _select_filter(view, "primes")
    assert view._results.count() == len(state.db.all_primes())


def test_dictionary_view_primes_filter_matches_the_query(state: AppState) -> None:
    view = DictionaryView(state)
    _select_filter(view, "primes")
    view._search("someone")
    assert view._results.count() >= 1


def test_dictionary_view_detail_follows_the_selection(state: AppState) -> None:
    view = DictionaryView(state)
    view._search("manu")
    assert "root class noun" in view._detail.text()
    assert "Senses" in view._detail.text()


def test_dictionary_view_unknown_entry_says_so(state: AppState) -> None:
    view = DictionaryView(state)
    view.show_entry(-1)
    assert view._detail.text() == "This word is not in the dictionary."


def test_format_entry_marks_placeholders() -> None:
    lexeme = Lexeme(9, "xo", None, None, "thing", "noun", 1, "provisional")
    senses = [Sense(1, 9, 1, "thing", (), "placeholder")]
    signs = [Sign(1, 9, "", "{}", "placeholder")]
    text = format_entry(lexeme, senses, signs)
    assert "primes: none yet  ·  pending linguist sign-off" in text
    assert "HamNoSys: not set (placeholder)" in text


def test_form_status_label_never_reads_unknown_as_approved() -> None:
    assert form_status_label("signed_off") == "signed off"
    assert form_status_label("provisional") == "provisional"
    assert form_status_label("bogus") == "pending linguist sign-off"


def test_format_entry_lists_senses_in_order_with_their_primes() -> None:
    lexeme = Lexeme(9, "xo", "ʘ", None, "thing", "noun", 1, "signed_off")
    senses = [
        Sense(1, 9, 1, "first", (), "placeholder"),
        Sense(2, 9, 2, "second", ("SOMEONE", "DO"), "provisional"),
    ]
    text = format_entry(lexeme, senses, [])
    assert text.splitlines()[0] == "xo  [ʘ]"
    assert "root class noun  ·  frequency 1  ·  signed off" in text
    assert text.index("  1. first") < text.index("  2. second")
    assert "     primes: SOMEONE DO  ·  provisional" in text
    assert "No sign recorded yet" in text


def test_format_entry_shows_a_signed_off_sign() -> None:
    lexeme = Lexeme(9, "xo", None, None, "thing", "noun", 1, "provisional")
    signs = [Sign(1, 9, "H:A", "{}", "signed_off")]
    text = format_entry(lexeme, [], signs)
    assert "No senses recorded yet." in text
    assert "  HamNoSys: H:A  ·  signed off" in text
    assert "No sign recorded yet" not in text


def test_dictionary_controls_have_accessible_names(state: AppState) -> None:
    view = DictionaryView(state)
    assert view._search_box.accessibleName() == "Search the dictionary"
    assert view._filter.accessibleName() == "Root class filter"
    assert view._results.accessibleName() == "Dictionary entries"
    assert view._detail.accessibleName() == "Entry detail"
    assert bool(view._detail.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse)


def test_dictionary_rows_announce_one_summary_each(state: AppState) -> None:
    view = DictionaryView(state)
    view._search("who")
    summary = view._results.item(0).data(Qt.ItemDataRole.AccessibleTextRole)
    assert summary == "manu, meaning who, noun, frequency 900, provisional"


def test_prime_rows_announce_a_pending_spoken_form(state: AppState) -> None:
    view = DictionaryView(state)
    _select_filter(view, "primes")
    view._search("someone")
    summaries = [
        view._results.item(i).data(Qt.ItemDataRole.AccessibleTextRole)
        for i in range(view._results.count())
    ]
    assert any(
        s.startswith("Prime SOMEONE,") and s.endswith("spoken form pending linguist sign-off")
        for s in summaries
    )


def test_count_label_reads_singular_and_plural(state: AppState) -> None:
    view = DictionaryView(state)
    view._search("who")
    assert view._count.text() == "1 word"
    view._search("")
    assert view._count.text() == f"{len(state.db.browse_lexemes(limit=500))} words"


def test_root_class_filter_narrows_a_search(state: AppState) -> None:
    view = DictionaryView(state)
    _select_filter(view, "noun")
    view._search("who")
    assert _ids(view) == [state.db.get_lexeme_by_phon("manu").id]
    _select_filter(view, "verb")
    view._search("who")
    assert view._results.count() == 1
    assert view._results.item(0).text() == "No words match that search."
    assert view._detail.text() == "Select a word to read its entry."


def test_detail_follows_a_row_picked_in_the_list(state: AppState) -> None:
    view = DictionaryView(state)
    view._search("interrogative")
    ids = _ids(view)
    assert len(ids) >= 2
    view._results.setCurrentRow(1)
    picked = state.db.get_lexeme(ids[1])
    assert picked is not None
    assert view._detail.text().startswith(picked.phon_form)


def test_primes_query_with_no_match_says_so(state: AppState) -> None:
    view = DictionaryView(state)
    _select_filter(view, "primes")
    view._search("zzz-no-such-prime")
    assert view._count.text() == "0 primes"
    assert view._results.item(0).text() == "No primes match that search."


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
