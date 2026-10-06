from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

# The tone is a preset rather than free text: the four cover how a message to a client
# actually varies (a chat with a regular contact, an email to a new one, a status ping,
# and "leave my voice alone"), and a preset is one click where a prompt is a sentence.
REFINE_TONES: tuple[tuple[str, str], ...] = (
    ("friendly", "Friendly"),
    ("formal", "Formal"),
    ("concise", "Concise"),
    ("keep", "My voice"),
)
DEFAULT_REFINE_TONE = "friendly"


@dataclass(frozen=True, slots=True)
class RefineRequest:
    text: str
    tone: str = DEFAULT_REFINE_TONE
    request_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True, slots=True)
class RefineOption:
    label: str
    text: str


@dataclass(frozen=True, slots=True)
class RefineResult:
    options: tuple[RefineOption, ...]
    notes: tuple[str, ...]
    provider_id: str
    # Display names of the services that were tried and failed before this one answered,
    # so the UI can say "via OpenAI" without it reading as though Azure was never asked.
    fallback_from: tuple[str, ...] = ()
