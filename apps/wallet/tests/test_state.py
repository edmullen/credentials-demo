from datetime import UTC, datetime

from app import state


def test_no_link_before_any_employer_added() -> None:
    assert state.get_link("p01", "meridian") is None


def test_add_employer_creates_link_on_first_touch() -> None:
    link = state.add_employer("p01", "meridian", "pinecrest")
    assert link.employers == ["pinecrest"]
    assert state.get_link("p01", "meridian") is link


def test_adding_the_same_employer_twice_leaves_one_entry() -> None:
    state.add_employer("p01", "meridian", "pinecrest")
    state.add_employer("p01", "meridian", "pinecrest")
    assert state.get_link("p01", "meridian").employers == ["pinecrest"]


def test_remove_link_deletes_everything() -> None:
    state.add_employer("p01", "meridian", "pinecrest")
    removed = state.remove_link("p01", "meridian")
    assert removed is not None
    assert state.get_link("p01", "meridian") is None


def test_remove_link_missing_is_a_noop() -> None:
    assert state.remove_link("p01", "meridian") is None


def test_events_are_ordered_and_isolated_per_person() -> None:
    at = datetime(2026, 9, 22, 18, 14, tzinfo=UTC)
    state.log("p01", "neutral", "first", at)
    state.log("p01", "verified", "second", at)
    assert [e.message for e in state.events_for("p01")] == ["first", "second"]
    assert state.events_for("p02") == []


def test_tokens_are_unique() -> None:
    assert state.new_token() != state.new_token()
