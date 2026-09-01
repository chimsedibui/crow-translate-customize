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

    def load(self) -> list[HistoryItem]:
        if not self.path.exists():
            return []
        try:
            return [HistoryItem(**item) for item in json.loads(self.path.read_text(encoding="utf-8"))]
        except (OSError, ValueError, TypeError):
            return []

    def add(self, source: str, translation: str, source_language: str, target_language: str, provider_id: str) -> HistoryItem:
        item = HistoryItem(source, translation, source_language, target_language, provider_id, datetime.now(UTC).isoformat())
        if self.limit <= 0:
            return item
        items = [item, *self.load()][: self.limit]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(entry) for entry in items], ensure_ascii=False, indent=2), encoding="utf-8")
        return item

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

