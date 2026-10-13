from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx
from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from py_crow_tool import __version__
from py_crow_tool.services.async_runner import AsyncLoopRunner

# Releases are published here by .github/workflows/release.yml when a v* tag is
# pushed. The repository is public, so checking needs no token.
REPOSITORY = "chimsedibui/crow-translate-customize"
# The release page, not the REST API. The API allows 60 unauthenticated requests an
# hour per IP address, and an office shares one address between everyone in it: the
# limit ran out during testing. This page answers with a redirect to the latest
# release's tag (or to the bare release list when there is none), which is all the
# check needs, and the download links follow from the tag.
LATEST_RELEASE_URL = f"https://github.com/{REPOSITORY}/releases/latest"
_RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
INSTALLER_ASSET = "PyCrowTool-Setup.exe"
CHECKSUM_ASSET = INSTALLER_ASSET + ".sha256"
_TEMP_PREFIX = "pycrow-update-"

# Run by a detached PowerShell once the app has exited. It has to wait: the
# installer cannot replace PyCrowTool.exe while either PyInstaller process (the
# bootloader holds the exe, the app runs under it) is still alive.
_UPDATE_SCRIPT = """param([int]$AppPid, [int]$LauncherPid, [string]$Installer)
foreach ($id in @($AppPid, $LauncherPid)) {
    if ($id -gt 0) { Wait-Process -Id $id -Timeout 60 -ErrorAction SilentlyContinue }
}
Start-Process -FilePath $Installer -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/RELAUNCH=1'
"""


def parse_version(text: str) -> tuple[int, ...] | None:
    """"v1.2.3" or "1.2.3" -> (1, 2, 3); anything else, a pre-release included, -> None."""
    parts = text.strip().removeprefix("v").split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def is_newer(candidate: str, current: str) -> bool:
    new, old = parse_version(candidate), parse_version(current)
    if new is None or old is None:
        return False
    width = max(len(new), len(old))
    return new + (0,) * (width - len(new)) > old + (0,) * (width - len(old))


@dataclass(frozen=True, slots=True)
class Release:
    version: str
    installer_url: str
    checksum_url: str
    page_url: str


def release_from_redirect(location: str) -> Release | None:
    """The release the latest-release page redirected to, or None when it points
    anywhere but a version tag -- no release yet, or a tag that is not vX.Y.Z.

    GitHub never sends drafts or pre-releases here. Whether the installer and its
    checksum were actually attached shows up as a failed download, not here.
    """
    prefix = _RELEASES_URL + "/tag/"
    if not location.startswith(prefix):
        return None
    tag = location[len(prefix):].strip("/")
    version = tag.removeprefix("v")
    if parse_version(version) is None:
        return None
    download = f"{_RELEASES_URL}/download/{tag}/"
    return Release(version, download + INSTALLER_ASSET, download + CHECKSUM_ASSET, location)


def _describe(error: Exception) -> str:
    """One short line for the UI. httpx's own messages run to several lines and
    end with a link to MDN, which is not something to put in a settings dialog."""
    if isinstance(error, httpx.HTTPStatusError):
        return f"GitHub answered {error.response.status_code}"
    if isinstance(error, (httpx.ConnectError, httpx.TimeoutException)):
        return "GitHub could not be reached. Check the internet connection"
    return str(error).splitlines()[0] if str(error) else type(error).__name__


def can_self_install() -> bool:
    """Only the installed, frozen app can replace itself. Run from source there is
    no installed copy to update -- the checkout is updated with git instead."""
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def remove_old_downloads() -> None:
    """Installers from earlier updates; by the time the updated app starts, the
    installer that launched it is done with its own file."""
    for path in Path(tempfile.gettempdir()).glob(_TEMP_PREFIX + "*"):
        shutil.rmtree(path, ignore_errors=True)


class UpdateService(QObject):
    """Checks GitHub for a newer release and installs it on request.

    state is one of: idle, checking, up-to-date, available, downloading,
    installing, error. message says the same in words for the UI.
    """

    stateChanged = Signal()
    # A background check found a newer release; the tray uses it.
    updateFound = Signal(str)
    # Asks the app to quit so the installer can replace it. The app connects it to
    # QApplication.quit -- the service does not reach for the application itself.
    quitRequested = Signal()
    # Results come back on the async loop's thread; these carry them to the GUI thread.
    _checked = Signal(object, bool)
    _checkFailed = Signal(str, bool)
    _progress = Signal(float)
    _downloaded = Signal(str)
    _downloadFailed = Signal(str)

    def __init__(self, loop_runner: AsyncLoopRunner | None = None, client: httpx.AsyncClient | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._loop_runner = loop_runner
        self._client = client
        self._state = "idle"
        self._message = ""
        self._progress_value = 0.0
        self._release: Release | None = None
        self._checked.connect(self._on_checked, Qt.ConnectionType.QueuedConnection)
        self._checkFailed.connect(self._on_check_failed, Qt.ConnectionType.QueuedConnection)
        self._progress.connect(self._on_progress, Qt.ConnectionType.QueuedConnection)
        self._downloaded.connect(self._on_downloaded, Qt.ConnectionType.QueuedConnection)
        self._downloadFailed.connect(self._on_download_failed, Qt.ConnectionType.QueuedConnection)

    # -- what QML reads -----------------------------------------------------------

    @Property(str, constant=True)
    def currentVersion(self):
        return __version__

    @Property(str, notify=stateChanged)
    def latestVersion(self):
        return self._release.version if self._release else ""

    @Property(str, notify=stateChanged)
    def releaseUrl(self):
        return self._release.page_url if self._release else f"https://github.com/{REPOSITORY}/releases/latest"

    @Property(str, notify=stateChanged)
    def state(self):
        return self._state

    @Property(str, notify=stateChanged)
    def message(self):
        return self._message

    @Property(float, notify=stateChanged)
    def progress(self):
        return self._progress_value

    @Property(bool, constant=True)
    def canInstall(self):
        return can_self_install()

    def _set(self, state: str, message: str = "") -> None:
        self._state, self._message = state, message
        self.stateChanged.emit()

    def _submit(self, coro) -> None:
        if self._loop_runner is not None:
            self._loop_runner.submit(coro)
        else:
            asyncio.run(coro)

    def _http(self) -> httpx.AsyncClient:
        # Created on the async loop, where it is used: an httpx client belongs to
        # the loop that first opens a connection with it.
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30, follow_redirects=True, headers={"User-Agent": f"PyCrowTool/{__version__}"})
        return self._client

    # -- checking -----------------------------------------------------------------

    @Slot()
    @Slot(bool)
    def checkForUpdates(self, silent: bool = False) -> None:
        """Ask GitHub for the latest release. A silent check (at startup, and daily)
        keeps quiet about failures: a laptop opened offline is not news."""
        if self._state in ("checking", "downloading", "installing"):
            return
        if not silent:
            self._set("checking", "Checking for updates…")

        async def _operation() -> None:
            try:
                # Not followed: the redirect target is the answer.
                response = await self._http().get(LATEST_RELEASE_URL, follow_redirects=False)
                if not response.is_redirect:
                    raise httpx.HTTPStatusError(f"GitHub answered {response.status_code}", request=response.request, response=response)
                self._checked.emit(release_from_redirect(response.headers.get("Location", "")), silent)
            except httpx.HTTPError as error:
                self._checkFailed.emit(f"Could not check for updates: {_describe(error)}", silent)

        self._submit(_operation())

    def _on_checked(self, release: Release | None, silent: bool) -> None:
        if release is not None and is_newer(release.version, __version__):
            self._release = release
            self._set("available", f"PyCrow {release.version} is available. You have {__version__}.")
            # A check the user asked for answers on screen; only the background ones
            # need the tray to say something.
            if silent:
                self.updateFound.emit(release.version)
        elif not silent or self._state == "checking":
            self._set("up-to-date", f"You have the latest version ({__version__}).")

    def _on_check_failed(self, message: str, silent: bool) -> None:
        if silent and self._state != "checking":
            return
        self._set("error", message)

    # -- installing ---------------------------------------------------------------

    @Slot()
    def installUpdate(self) -> None:
        release = self._release
        if release is None or self._state in ("downloading", "installing"):
            return
        if not can_self_install():
            self._set("error", "Updates install only into the installed app. Run the installer from the release page instead.")
            return
        self._progress_value = 0.0
        self._set("downloading", f"Downloading PyCrow {release.version}…")
        folder = Path(tempfile.mkdtemp(prefix=_TEMP_PREFIX))

        async def _operation() -> None:
            try:
                path = await self._download(release, folder)
            except (httpx.HTTPError, OSError, ValueError) as error:
                shutil.rmtree(folder, ignore_errors=True)
                self._downloadFailed.emit(f"The update could not be downloaded: {_describe(error)}")
                return
            self._downloaded.emit(str(path))

        self._submit(_operation())

    async def _download(self, release: Release, folder: Path) -> Path:
        client = self._http()
        checksum = await client.get(release.checksum_url)
        checksum.raise_for_status()
        expected = checksum.text.split()[0].strip().lower() if checksum.text.split() else ""
        if len(expected) != 64:
            raise ValueError("the release's checksum file is malformed")

        path = folder / INSTALLER_ASSET
        digest = hashlib.sha256()
        async with client.stream("GET", release.installer_url) as response:
            response.raise_for_status()
            total = int(response.headers.get("Content-Length") or 0)
            received = 0
            last_reported = 0.0
            with path.open("wb") as stream:
                async for chunk in response.aiter_bytes(64 * 1024):
                    stream.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    # A signal per chunk would be over a thousand repaints for nothing.
                    if total and received / total - last_reported >= 0.01:
                        last_reported = received / total
                        self._progress.emit(last_reported)
        # Never run what was not published: a truncated or tampered download stops here.
        if digest.hexdigest() != expected:
            raise ValueError("the downloaded file does not match the published checksum")
        return path

    def _on_progress(self, value: float) -> None:
        if self._state == "downloading":
            self._progress_value = value
            self.stateChanged.emit()

    def _on_download_failed(self, message: str) -> None:
        self._set("error", message)

    def _on_downloaded(self, installer: str) -> None:
        self._progress_value = 1.0
        self._set("installing", "Installing the update. PyCrow will restart by itself.")
        script = Path(installer).with_name("update.ps1")
        script.write_text(_UPDATE_SCRIPT, encoding="utf-8")
        command = [
            "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
            "-File", str(script),
            "-AppPid", str(os.getpid()), "-LauncherPid", str(os.getppid()), "-Installer", installer,
        ]
        # CREATE_NO_WINDOW, not DETACHED_PROCESS: PowerShell given no console at all
        # exits before running a line, which is how the first release's updates died
        # silently after closing the app. A hidden console keeps it alive, and it
        # outlives the app either way. Breaking away from the app's job object is
        # asked for in case one would take PowerShell down with the app; where the
        # job forbids it, the plain launch is the fallback.
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            try:
                subprocess.Popen(command, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, close_fds=True)
            except PermissionError:
                subprocess.Popen(command, creationflags=flags, close_fds=True)
        except OSError as error:
            self._set("error", f"The installer could not be started: {error}")
            return
        self.quitRequested.emit()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
