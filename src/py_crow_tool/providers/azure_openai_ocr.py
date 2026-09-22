from __future__ import annotations

import httpx

from py_crow_tool.core.ocr_models import OcrError, OcrException

from .azure_openai import AzureOpenAiProvider
from .openai_ocr import OpenAiOcrProvider


class AzureOpenAiOcrProvider(OpenAiOcrProvider):
    """Read text from an image with a vision-capable chat deployment on Azure OpenAI.

    Shares everything that matters with the OpenAI reader -- the prompt, the downscaling
    that keeps a full-desktop screenshot from being billed at full resolution, the
    payload and the result shape -- and differs only in how the deployment is addressed
    and authenticated. The deployment must be a vision model (gpt-4o and gpt-4o-mini
    are); a text-only one answers HTTP 400 on the image part of the message.
    """

    id = "azure-openai-vision"
    display_name = "Azure OpenAI Vision OCR"

    # One implementation of the endpoint tidy-up, shared with the translation provider,
    # so a URL pasted into Settings is accepted in exactly the same forms by both.
    _normalize_endpoint = staticmethod(AzureOpenAiProvider._normalize_endpoint)

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = "",
        deployment: str = "",
        api_version: str = "2025-01-01-preview",
        max_dimension: int = 1280,
        image_format: str = "png",
        jpeg_quality: int = 87,
        detail: str = "high",
        client: httpx.AsyncClient | None = None,
    ):
        super().__init__(
            api_key,
            # Azure names the model in the URL, so `model` carries the deployment name
            # here. It is still what the gpt-5 reasoning branch and OcrResult.model read.
            model=deployment,
            max_dimension=max_dimension,
            image_format=image_format,
            jpeg_quality=jpeg_quality,
            detail=detail,
            client=client,
        )
        self.endpoint = AzureOpenAiProvider._normalize_endpoint(endpoint)
        self.api_version = api_version.strip() or "2025-01-01-preview"

    @property
    def deployment(self) -> str:
        return self.model

    @deployment.setter
    def deployment(self, value: str) -> None:
        self.model = value

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.endpoint and self.model)

    def _endpoint_url(self) -> str:
        return f"{self.endpoint}/openai/deployments/{self.model}/chat/completions"

    def _query(self) -> dict[str, str]:
        return {"api-version": self.api_version}

    def _auth_headers(self) -> dict[str, str]:
        return {"api-key": self.api_key}

    def _model_field(self) -> dict[str, str]:
        # The deployment is already in the path; repeating it in the body is at best
        # ignored and at worst rejected when it does not match a real model name.
        return {}

    async def recognize(self, request):
        if not self.configured:
            missing = [
                name
                for name, value in (("endpoint", self.endpoint), ("deployment", self.model), ("API key", self.api_key))
                if not value
            ]
            raise OcrException(OcrError.CONFIGURATION, "Azure OpenAI OCR is missing its " + ", ".join(missing))
        return await super().recognize(request)
