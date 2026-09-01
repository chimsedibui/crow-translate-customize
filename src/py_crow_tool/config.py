from __future__ import annotations

import os
import stat
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import tomli_w
from platformdirs import user_config_path


@dataclass(slots=True)
class GoogleV2Settings:
    api_key: str = ""


@dataclass(slots=True)
class GoogleV3Settings:
    project_id: str = ""
    location: str = "global"
    credentials_file: str = ""


@dataclass(slots=True)
class AppSettings:
    version: int = 1
    source_language: str = "auto"
    target_language: str = "en"
    auto_translate: bool = False
    history_limit: int = 100
    tesseract_command: str = ""
    google_v2: GoogleV2Settings = field(default_factory=GoogleV2Settings)
    google_v3: GoogleV3Settings = field(default_factory=GoogleV3Settings)
    enabled_plugins: list[str] = field(default_factory=list)

    @property
    def v2_api_key(self) -> str:
        return os.getenv("PY_CROW_GOOGLE_API_KEY", self.google_v2.api_key)

    @property
    def v3_project_id(self) -> str:
        return os.getenv("GOOGLE_CLOUD_PROJECT", self.google_v3.project_id)

    @property
    def v3_credentials_file(self) -> str:
        return os.getenv("GOOGLE_APPLICATION_CREDENTIALS", self.google_v3.credentials_file)


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = path or user_config_path("PyCrowTool", "CrowTranslate") / "settings.toml"

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        with self.path.open("rb") as stream:
            data = tomllib.load(stream)
        return self._decode(data)

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(tomli_w.dumps(asdict(settings)), encoding="utf-8")
        try:
            temporary.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        temporary.replace(self.path)

    @staticmethod
    def _decode(data: dict[str, Any]) -> AppSettings:
        return AppSettings(
            version=int(data.get("version", 1)),
            source_language=str(data.get("source_language", "auto")),
            target_language=str(data.get("target_language", "en")),
            auto_translate=bool(data.get("auto_translate", False)),
            history_limit=max(0, int(data.get("history_limit", 100))),
            tesseract_command=str(data.get("tesseract_command", "")),
            google_v2=GoogleV2Settings(**data.get("google_v2", {})),
            google_v3=GoogleV3Settings(**data.get("google_v3", {})),
            enabled_plugins=list(data.get("enabled_plugins", [])),
        )


SECRET_KEYS = {"api_key", "authorization", "credentials", "token", "password"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("<redacted>" if key.lower() in SECRET_KEYS else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
