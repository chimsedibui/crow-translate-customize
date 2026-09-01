from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TranslationError(StrEnum):
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    QUOTA = "quota"
    INVALID_REQUEST = "invalid_request"
    SERVICE = "service"
    PARSING = "parsing"
    CANCELLED = "cancelled"


class TranslationException(Exception):
    def __init__(self, kind: TranslationError, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class TranslationRequest:
    text: str
    target_language: str
    source_language: str = "auto"
    provider_id: str | None = None
    request_id: str = field(default_factory=lambda: str(uuid4()))
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DetectedLanguage:
    language: str
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class TranslationResult:
    translated_text: str
    source_language: str
    target_language: str
    provider_id: str
    transliteration: str | None = None
    alternatives: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

