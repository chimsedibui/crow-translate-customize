from pathlib import Path

from py_crow_tool.config import AppSettings, GoogleV2Settings, GoogleV3Settings, SettingsStore, redact


def test_settings_round_trip(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.toml")
    expected = AppSettings(
        source_language="vi",
        target_language="en",
        start_with_system=True,
        clipboard_hotkey="ctrl+alt+c",
        quick_translate_hotkey="ctrl+alt+q",
        google_v2=GoogleV2Settings("secret"),
        google_v3=GoogleV3Settings("project", "us-central1", "credentials.json"),
    )
    store.save(expected)
    assert store.load() == expected


def test_redact_nested_secrets():
    assert redact({"api_key": "secret", "nested": {"token": "token", "ok": 4}}) == {
        "api_key": "<redacted>",
        "nested": {"token": "<redacted>", "ok": 4},
    }

