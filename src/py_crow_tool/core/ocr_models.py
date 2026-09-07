from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class OcrError(StrEnum):
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    QUOTA = "quota"
    INVALID_REQUEST = "invalid_request"
    SERVICE = "service"
    PARSING = "parsing"
    CANCELLED = "cancelled"


class OcrException(Exception):
    def __init__(self, kind: OcrError, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class OcrRequest:
    image: bytes
    request_id: str = field(default_factory=lambda: str(uuid4()))
    language_hint: str | None = None
    provider_id: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OcrResult:
    text: str
    provider_id: str
    model: str | None = None
    confidence: float | None = None
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
