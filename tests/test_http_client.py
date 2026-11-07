import asyncio

from py_crow_tool.providers.google_v2 import GoogleV2Provider
from py_crow_tool.providers.http_client import new_async_client, shared_ssl_context
from py_crow_tool.providers.openai_ocr import OpenAiOcrProvider


def test_every_client_verifies_with_the_same_tls_context():
    """One parsed CA bundle for the whole app instead of one per client."""
    first, second = new_async_client(), new_async_client(timeout=5)
    try:
        for client in (first, second):
            assert client._transport._pool._ssl_context is shared_ssl_context()
    finally:
        asyncio.run(first.aclose())
        asyncio.run(second.aclose())


def test_providers_build_their_clients_on_the_shared_context():
    translate, ocr = GoogleV2Provider("key"), OpenAiOcrProvider("key")
    try:
        for provider in (translate, ocr):
            assert provider._client._transport._pool._ssl_context is shared_ssl_context()
    finally:
        asyncio.run(translate.close())
        asyncio.run(ocr.close())
