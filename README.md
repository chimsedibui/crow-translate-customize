# Crow Tool

This repository contains two desktop translation applications built from the Crow Translate codebase.

| Version | Stack | Status | Best for |
|---|---|---|---|
| [`c_crow_tool`](c_crow_tool/) | C++17, Qt 5, CMake | Mature application | Full desktop integration, multiple translation engines, OCR, TTS, shortcuts, and Linux support |
| [`py_crow_tool`](py_crow_tool/) | Python 3.11, PySide 6, QML | New implementation | Official Google Cloud APIs, Python plugins, QML development, and a simpler extension model |

The applications are independent. Build and configure only the version you intend to run.

## Choose a version

Use the **C++ version** when you need the broadest existing feature set or compatibility with the original Crow Translate workflows. It supports Google, Yandex, Bing, LibreTranslate, and Lingva through QOnlineTranslator. When a Google Cloud API key is configured, its Google engine uses the official Cloud Translation Basic v2 API.

Use the **Python version** when you want a Python/QML codebase and official Google Cloud integration. It supports Google Cloud Advanced v3 and Basic v2, prefers v3 when both are configured, and exposes a Python provider plugin contract.

## Documentation

### C++ / Qt 5

- [Overview and development](c_crow_tool/README.md)
- [Build and deployment](c_crow_tool/DEPLOY.md)
- [Windows deployment](c_crow_tool/WINDOWS_DEPLOY.md)
- [Translation architecture](c_crow_tool/TRANSLATION_MECHANISM.md)

### Python / PySide 6

- [Overview and development](py_crow_tool/README.md)
- [Windows deployment](py_crow_tool/WINDOWS_DEPLOY.md)

## Credentials

Neither application should contain embedded Google credentials. Configuration files can contain plaintext API keys or credential paths, so keep them outside version control and restrict access to the current user.

