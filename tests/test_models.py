from py_crow_tool.core.languages import normalize_language
from py_crow_tool.core.models import TranslationRequest, TranslationResult


def test_language_normalization():
    assert normalize_language("ZH-cn") == "zh-CN"
    assert normalize_language("AUTO") == "auto"
    assert normalize_language("VI") == "vi"


def test_result_serializes_tuples():
    result = TranslationResult("hello", "vi", "en", "google-v3", alternatives=("hi",))
    assert result.to_dict()["alternatives"] == ("hi",)


def test_request_ids_are_unique():
    assert TranslationRequest("a", "en").request_id != TranslationRequest("a", "en").request_id

