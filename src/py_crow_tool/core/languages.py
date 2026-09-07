from __future__ import annotations

LANGUAGES: tuple[tuple[str, str], ...] = (
    ("auto", "Detect language"),
    ("ar", "Arabic"),
    ("zh-CN", "Chinese (Simplified)"),
    ("zh-TW", "Chinese (Traditional)"),
    ("nl", "Dutch"),
    ("en", "English"),
    ("fr", "French"),
    ("de", "German"),
    ("hi", "Hindi"),
    ("id", "Indonesian"),
    ("it", "Italian"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("pl", "Polish"),
    ("pt", "Portuguese"),
    ("ru", "Russian"),
    ("es", "Spanish"),
    ("th", "Thai"),
    ("tr", "Turkish"),
    ("uk", "Ukrainian"),
    ("vi", "Vietnamese"),
)


def normalize_language(code: str) -> str:
    value = code.strip()
    if value.lower() == "auto":
        return "auto"
    aliases = {"zh": "zh-CN", "zh-cn": "zh-CN", "zh-tw": "zh-TW", "iw": "he"}
    return aliases.get(value.lower(), value.lower())


_DISPLAY_NAMES = dict(LANGUAGES)


def language_display_name(code: str) -> str:
    """English name for a language code (e.g. "vi" -> "Vietnamese"), for prompts aimed at a
    human-language model rather than a code-driven API. Falls back to the code itself."""
    return _DISPLAY_NAMES.get(normalize_language(code), code)

