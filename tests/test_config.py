from pathlib import Path

from py_crow_tool.config import AppSettings, GoogleV2Settings, SettingsStore, redact


def test_settings_round_trip(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.toml")
    expected = AppSettings(
        source_language="vi",
        target_language="en",
        start_with_system=True,
        clipboard_hotkey="ctrl+alt+c",
        quick_translate_hotkey="ctrl+alt+q",
        google_v2=GoogleV2Settings("secret"),
    )
    store.save(expected)
    assert store.load() == expected


def test_settings_load_ignores_a_leftover_v3_section(tmp_path: Path):
    path = tmp_path / "settings.toml"
    path.write_text('[google_v3]\nproject_id = "old-project"\n[google_v2]\napi_key = "secret"\n', encoding="utf-8")
    settings = SettingsStore(path).load()
    assert settings.google_v2.api_key == "secret"
    assert not hasattr(settings, "google_v3")


def test_redact_nested_secrets():
    assert redact({"api_key": "secret", "nested": {"token": "token", "ok": 4}}) == {
        "api_key": "<redacted>",
        "nested": {"token": "<redacted>", "ok": 4},
    }

