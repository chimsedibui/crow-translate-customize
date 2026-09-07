from __future__ import annotations

import base64
from io import BytesIO

import httpx
from PIL import Image

from py_crow_tool.core.languages import language_display_name
from py_crow_tool.core.ocr_models import OcrError, OcrException, OcrRequest, OcrResult

from .ocr_base import HttpOcrProvider

_PROMPT = (
    "Extract only the visible text from this image, exactly as it appears, preserving line "
    "breaks and original spelling/diacritics. Do not translate, summarize, or add any commentary. "
    "Reply with the extracted text only. If there is no legible text, reply with an empty string."
)


def _prepare_image(image: bytes, *, max_dimension: int, image_format: str, jpeg_quality: int) -> tuple[bytes, str]:
    """Downscale to max_dimension on the longest side and re-encode, so a full-desktop
    screenshot doesn't get uploaded (and billed as vision tokens) at full resolution.
    A crop already under the cap passes through re-encoded but otherwise unchanged."""
    with Image.open(BytesIO(image)) as img:
        img.load()
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = (max(1, round(img.width * ratio)), max(1, round(img.height * ratio)))
            img = img.resize(new_size, Image.LANCZOS)

        buffer = BytesIO()
        if image_format == "jpeg":
            if img.mode in ("RGBA", "LA", "P"):
                rgba = img.convert("RGBA")
                flattened = Image.new("RGB", img.size, (255, 255, 255))
                flattened.paste(rgba, mask=rgba.split()[-1])
                img = flattened
            elif img.mode != "RGB":
                img = img.convert("RGB")
            img.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
            return buffer.getvalue(), "image/jpeg"

        img.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue(), "image/png"


class OpenAiOcrProvider(HttpOcrProvider):
    id = "openai-vision"
    display_name = "OpenAI Vision OCR"
    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-4o-mini",
        max_dimension: int = 1280,
        image_format: str = "png",
        jpeg_quality: int = 87,
        detail: str = "high",
        reasoning_effort: str = "minimal",
        client: httpx.AsyncClient | None = None,
    ):
        super().__init__(client=client)
        self.api_key = api_key.strip()
        self.model = model
        self.max_dimension = max_dimension
        self.image_format = image_format
        self.jpeg_quality = jpeg_quality
        self.detail = detail
        self.reasoning_effort = reasoning_effort

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def recognize(self, request: OcrRequest) -> OcrResult:
        if not self.configured:
            raise OcrException(OcrError.CONFIGURATION, "OpenAI API key is not configured")

        async def operation() -> OcrResult:
            try:
                prepared, mime = _prepare_image(
                    request.image,
                    max_dimension=self.max_dimension,
                    image_format=self.image_format,
                    jpeg_quality=self.jpeg_quality,
                )
            except Exception as error:  # noqa: BLE001 - corrupt/unsupported image data
                raise OcrException(OcrError.INVALID_REQUEST, f"Could not decode image: {error}") from error

            data_uri = f"data:{mime};base64," + base64.b64encode(prepared).decode("ascii")
            prompt = _PROMPT
            if request.language_hint and request.language_hint != "auto":
                prompt += f" The text is expected to be in: {language_display_name(request.language_hint)}."
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri, "detail": self.detail}},
                        ],
                    }
                ],
            }
            # GPT-5-family models on /chat/completions reject any explicit temperature other
            # than their default (1); only the GPT-4o family accepts (and benefits from) 0.
            if self.model.startswith("gpt-5"):
                # Without this, GPT-5 models spend hundreds-thousands of hidden reasoning
                # tokens "thinking" about a plain OCR read -- measured 13-24s latency at the
                # default effort vs ~1.5s at "minimal" for the same image, for no accuracy gain.
                if self.reasoning_effort:
                    payload["reasoning_effort"] = self.reasoning_effort
            else:
                payload["temperature"] = 0
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await self._request("POST", self.endpoint, headers=headers, json=payload)
            self._raise_for_response(response)
            try:
                body = response.json()
                text = body["choices"][0]["message"]["content"].strip()
                usage = body.get("usage", {})
                return OcrResult(
                    text=text,
                    provider_id=self.id,
                    model=self.model,
                    metadata={
                        "usage": usage,
                        "image_bytes_sent": len(prepared),
                        "image_bytes_original": len(request.image),
                    },
                )
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise OcrException(OcrError.PARSING, "Unexpected OpenAI response") from error

        return await self._run(request.request_id, operation())
