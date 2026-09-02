from py_crow_tool.services.history import HistoryStore


def test_add_updates_cache_without_touching_disk(tmp_path):
    path = tmp_path / "history.json"
    store = HistoryStore(path, limit=10)

    store.add("hello", "xin chao", "en", "vi", "fake")

    assert not path.exists()
    assert len(store.load()) == 1


def test_flush_persists_and_a_fresh_store_reads_it_back(tmp_path):
    path = tmp_path / "history.json"
    store = HistoryStore(path, limit=10)
    store.add("hello", "xin chao", "en", "vi", "fake")

    store.flush()

    assert path.exists()
    reloaded = HistoryStore(path, limit=10)
    items = reloaded.load()
    assert len(items) == 1
    assert items[0].source == "hello"
    assert items[0].translation == "xin chao"


def test_limit_truncates_oldest_entries(tmp_path):
    store = HistoryStore(tmp_path / "history.json", limit=2)
    store.add("a", "a2", "en", "vi", "fake")
    store.add("b", "b2", "en", "vi", "fake")
    store.add("c", "c2", "en", "vi", "fake")

    assert [item.source for item in store.load()] == ["c", "b"]


def test_limit_zero_never_persists(tmp_path):
    path = tmp_path / "history.json"
    store = HistoryStore(path, limit=0)

    store.add("a", "a2", "en", "vi", "fake")
    store.flush()

    assert not path.exists()


def test_clear_empties_cache_and_deletes_file(tmp_path):
    path = tmp_path / "history.json"
    store = HistoryStore(path, limit=10)
    store.add("a", "a2", "en", "vi", "fake")
    store.flush()
    assert path.exists()

    store.clear()

    assert store.load() == []
    assert not path.exists()


def test_load_survives_corrupt_file(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("not json", encoding="utf-8")
    store = HistoryStore(path, limit=10)

    assert store.load() == []
