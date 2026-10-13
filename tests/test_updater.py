import hashlib

import httpx
import pytest

from py_crow_tool import __version__
from py_crow_tool.services import updater as updater_module
from py_crow_tool.services.updater import (
    CHECKSUM_ASSET,
    INSTALLER_ASSET,
    LATEST_RELEASE_URL,
    Release,
    UpdateService,
    is_newer,
    parse_release,
    parse_version,
)


def test_parse_version():
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("1.0") == (1, 0)
    assert parse_version("1.0.0-beta") is None
    assert parse_version("") is None


def test_is_newer_compares_numerically():
    assert is_newer("1.0.10", "1.0.9")
    assert is_newer("v2.0.0", "1.9.9")
    assert is_newer("1.0.1", "1.0")
    assert not is_newer("1.0.0", "1.0")
    assert not is_newer("1.0.0", "1.0.0")
    assert not is_newer("0.9.0", "1.0.0")
    assert not is_newer("garbage", "1.0.0")


def _release_json(tag="v9.0.0", assets=(INSTALLER_ASSET, CHECKSUM_ASSET), **extra):
    return {
        "tag_name": tag,
        "html_url": f"https://github.com/example/releases/tag/{tag}",
        "assets": [{"name": name, "browser_download_url": f"https://downloads.test/{name}"} for name in assets],
        **extra,
    }


def test_parse_release_reads_version_and_assets():
    release = parse_release(_release_json())
    assert release == Release("9.0.0", f"https://downloads.test/{INSTALLER_ASSET}", f"https://downloads.test/{CHECKSUM_ASSET}", "https://github.com/example/releases/tag/v9.0.0")


@pytest.mark.parametrize("data", [
    _release_json(assets=(INSTALLER_ASSET,)),       # no checksum: never installed blind
    _release_json(assets=(CHECKSUM_ASSET,)),
    _release_json(tag="nightly"),
    _release_json(prerelease=True),
    _release_json(draft=True),
])
def test_parse_release_rejects_what_cannot_be_installed(data):
    assert parse_release(data) is None


def _service(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)
    return UpdateService(client=client)


def _latest(response):
    def handler(request: httpx.Request):
        assert str(request.url) == LATEST_RELEASE_URL
        return response
    return handler


def test_check_finds_a_newer_release(qapp, qtbot):
    service = _service(_latest(httpx.Response(200, json=_release_json("v99.0.0"))))
    found = []
    service.updateFound.connect(found.append)
    service.checkForUpdates()
    qtbot.waitUntil(lambda: service.state == "available")
    assert service.latestVersion == "99.0.0"
    assert "99.0.0" in service.message
    assert found == []  # asked for on screen, so the tray stays quiet


def test_silent_check_tells_the_tray(qapp, qtbot):
    service = _service(_latest(httpx.Response(200, json=_release_json("v99.0.0"))))
    found = []
    service.updateFound.connect(found.append)
    service.checkForUpdates(True)
    qtbot.waitUntil(lambda: found == ["99.0.0"])
    assert service.state == "available"


@pytest.mark.parametrize("response", [
    httpx.Response(200, json=_release_json(f"v{__version__}")),
    httpx.Response(200, json=_release_json("v0.0.1")),
    httpx.Response(404, json={"message": "Not Found"}),  # nothing released yet
])
def test_check_reports_up_to_date(qapp, qtbot, response):
    service = _service(_latest(response))
    service.checkForUpdates()
    qtbot.waitUntil(lambda: service.state == "up-to-date")
    assert service.latestVersion == ""


def test_failed_check_is_reported_only_when_asked_for(qapp, qtbot):
    def offline(request):
        raise httpx.ConnectError("offline")

    service = _service(offline)
    service.checkForUpdates(True)
    qtbot.wait(50)
    assert service.state == "idle" and service.message == ""
    service.checkForUpdates()
    qtbot.waitUntil(lambda: service.state == "error")
    assert "offline" in service.message


def test_install_refuses_outside_the_installed_app(qapp, qtbot, monkeypatch):
    service = _service(_latest(httpx.Response(200, json=_release_json("v99.0.0"))))
    service.checkForUpdates()
    qtbot.waitUntil(lambda: service.state == "available")
    monkeypatch.setattr(updater_module, "can_self_install", lambda: False)
    service.installUpdate()
    assert service.state == "error"


def _downloads(installer: bytes, checksum: str):
    def handler(request: httpx.Request):
        if request.url.path.endswith(CHECKSUM_ASSET):
            return httpx.Response(200, text=checksum)
        return httpx.Response(200, content=installer, headers={"Content-Length": str(len(installer))})
    return handler


RELEASE = Release("99.0.0", f"https://downloads.test/{INSTALLER_ASSET}", f"https://downloads.test/{CHECKSUM_ASSET}", "")


async def test_download_keeps_a_file_that_matches_its_checksum(tmp_path):
    payload = b"installer bytes" * 1000
    service = _service(_downloads(payload, f"{hashlib.sha256(payload).hexdigest()}  {INSTALLER_ASSET}"))
    path = await service._download(RELEASE, tmp_path)
    assert path.read_bytes() == payload
    await service.close()


@pytest.mark.parametrize("checksum", ["0" * 64, "not a checksum", ""])
async def test_download_refuses_a_mismatched_or_missing_checksum(tmp_path, checksum):
    service = _service(_downloads(b"tampered", checksum))
    with pytest.raises(ValueError):
        await service._download(RELEASE, tmp_path)
    await service.close()
