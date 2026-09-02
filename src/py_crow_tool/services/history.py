from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from platformdirs import user_data_path


@dataclass(frozen=True, slots=True)
class HistoryItem:
    source: str
    translation: str
    source_language: str
    target_language: str
    provider_id: str
    created_at: str


class HistoryStore:
    def __init__(self, path: Path | None = None, limit: int = 100):
        self.path = path or user_data_path("PyCrowTool", "CrowTranslate") / "history.json"
        self.limit = limit
        self._cache: list[HistoryItem] | None = None

    def load(self) -> list[HistoryItem]:
        if self._cache is None:
            self._cache = self._read()
        return self._cache

    def _read(self) -> list[HistoryItem]:
        if not self.path.exists():
            return []
        try:
            return [HistoryItem(**item) for item in json.loads(self.path.read_text(encoding="utf-8"))]
        except (OSError, ValueError, TypeError):
            return []

    def add(self, source: str, translation: str, source_language: str, target_language: str, provider_id: str) -> HistoryItem:
        """Update the in-memory list immediately; call flush() to persist off the UI thread."""
        item = HistoryItem(source, translation, source_language, target_language, provider_id, datetime.now(UTC).isoformat())
        if self.limit <= 0:
            return item
        self._cache = [item, *self.load()][: self.limit]
        return item

    def flush(self) -> None:
        if self._cache is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(entry) for entry in self._cache], ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        self._cache = []
        if self.path.exists():
            self.path.unlink()
