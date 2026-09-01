from py_crow_tool.plugins import ProviderPlugin


def test_plugin_metadata_is_stable():
    plugin = ProviderPlugin("sample", "1.0", ("translate",), {"key": {"type": "string"}}, lambda settings: settings)
    assert plugin.id == "sample"
    assert plugin.capabilities == ("translate",)

