from py_crow_tool.core.refine_models import RefineOption, RefineResult
from py_crow_tool.services.refine_history import RefineHistoryStore


def _result(*texts):
    return RefineResult(tuple(RefineOption(f"V{i}", text) for i, text in enumerate(texts)), ("ghi chú",), "azure-openai")


def test_add_keeps_every_version_and_flush_round_trips_unicode(tmp_path):
    path = tmp_path / "refine_history.json"
    store = RefineHistoryStore(path)
    store.add("bên em fix xong rồi", "friendly", _result("We fixed it.", "We've fixed the issue."))
    assert not path.exists()
    store.flush()
    item = RefineHistoryStore(path).load()[0]
    assert item.source == "bên em fix xong rồi"
    assert item.tone == "friendly"
    assert [option["text"] for option in item.options] == ["We fixed it.", "We've fixed the issue."]
    assert item.notes == ["ghi chú"]
    # Written as UTF-8 text, not \u escapes, so the file stays readable by hand.
    assert "bên em" in path.read_text(encoding="utf-8")


def test_newest_first_limit_and_find(tmp_path):
    store = RefineHistoryStore(tmp_path / "h.json", limit=2)
    first = store.add("a", "friendly", _result("A"))
    store.add("b", "formal", _result("B"))
    third = store.add("c", "concise", _result("C"))
    assert [item.source for item in store.load()] == ["c", "b"]
    assert store.find(third.id).source == "c"
    assert store.find(first.id) is None
    assert first.id != third.id


def test_corrupt_file_reads_as_empty_and_clear_removes_it(tmp_path):
    path = tmp_path / "h.json"
    path.write_text("{not json", encoding="utf-8")
    store = RefineHistoryStore(path)
    assert store.load() == []
    store.clear()
    assert not path.exists()
