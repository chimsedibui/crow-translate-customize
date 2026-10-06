from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from platformdirs import user_data_path

from py_crow_tool.core.refine_models import RefineResult


@dataclass(frozen=True, slots=True)
class RefineHistoryItem:
    source: str
    tone: str
    # Every version, not just one: the user picks which to send after reading them all,
    # and a history that kept only the first would lose the one they actually chose.
    options: list[dict[str, str]]
    notes: list[str] = field(default_factory=list)
    provider_id: str = ""
    created_at: str = ""
    # The restore key. Not created_at: the Windows clock can hand two entries made in
    # quick succession the same timestamp.
    id: str = field(default_factory=lambda: uuid4().hex)


class RefineHistoryStore:
    """Refine results, kept apart from translation history.

    Same shape of API as HistoryStore -- add() in memory, flush() off the UI thread --
    but its own file: a refine entry has several outputs and a tone rather than one
    output and a language pair, and mixing the two would make both lists harder to scan.
    """

    def __init__(self, path: Path | None = None, limit: int = 100):
        self.path = path or user_data_path("PyCrowTool", "CrowTranslate") / "refine_history.json"
        self.limit = limit
        self._cache: list[RefineHistoryItem] | None = None

    def load(self) -> list[RefineHistoryItem]:
        if self._cache is None:
            self._cache = self._read()
        return self._cache

    def _read(self) -> list[RefineHistoryItem]:
        if not self.path.exists():
            return []
        try:
            return [RefineHistoryItem(**item) for item in json.loads(self.path.read_text(encoding="utf-8"))]
        except (OSError, ValueError, TypeError):
            return []

    def add(self, source: str, tone: str, result: RefineResult) -> RefineHistoryItem:
        item = RefineHistoryItem(
            source=source,
            tone=tone,
            options=[{"label": option.label, "text": option.text} for option in result.options],
            notes=list(result.notes),
            provider_id=result.provider_id,
            created_at=datetime.now(UTC).isoformat(),
        )
        if self.limit <= 0:
            return item
        self._cache = [item, *self.load()][: self.limit]
        return item

    def find(self, item_id: str) -> RefineHistoryItem | None:
        return next((item for item in self.load() if item.id == item_id), None)

    def flush(self) -> None:
        if self._cache is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(entry) for entry in self._cache], ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        self._cache = []
        if self.path.exists():
            self.path.unlink()
