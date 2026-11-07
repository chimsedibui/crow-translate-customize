from __future__ import annotations

import ssl
from functools import lru_cache
from typing import Any

import httpx


@lru_cache(maxsize=1)
def shared_ssl_context() -> ssl.SSLContext:
    """The one TLS context every HTTP client in the app verifies with.

    httpx builds a fresh context per AsyncClient by default, and each one parses the
    whole certifi CA bundle again -- one to two and a half MB apiece, for seven clients
    that all trust exactly the same roots. The settings are httpx's own defaults.
    """
    return httpx.create_ssl_context()


def new_async_client(**kwargs: Any) -> httpx.AsyncClient:
    kwargs.setdefault("verify", shared_ssl_context())
    return httpx.AsyncClient(**kwargs)
