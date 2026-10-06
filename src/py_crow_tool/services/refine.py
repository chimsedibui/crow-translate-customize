from __future__ import annotations

from dataclasses import replace

from py_crow_tool.config import AppSettings
from py_crow_tool.core.models import TranslationError, TranslationException
from py_crow_tool.core.refine_models import RefineRequest, RefineResult
from py_crow_tool.providers.refiner import AzureOpenAiRefiner, ChatRefiner, OpenAiRefiner


class RefineService:
    """Rewrites a draft through Azure OpenAI, falling back to OpenAI.

    Unlike OCR, falling back here is the point: the user asked for backups. It does not
    send one service's credentials to the other -- each refiner only ever uses its own
    key -- so the reason OCR refuses to substitute does not apply.
    """

    def __init__(self, settings: AppSettings, refiners: list[ChatRefiner] | None = None):
        self._settings = settings
        if refiners is not None:
            self._refiners = refiners
            return
        self._azure = AzureOpenAiRefiner(
            settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
        )
        self._openai = OpenAiRefiner(settings.openai_api_key, model=settings.openai.refine_model)
        # Order is preference: Azure first, OpenAI as the backup.
        self._refiners = [self._azure, self._openai]

    def apply_settings(self) -> None:
        """Pick up keys saved in Settings without a restart, as OcrService does."""
        if not hasattr(self, "_azure"):
            return
        self._azure.configure(
            self._settings.azure_openai_api_key,
            endpoint=self._settings.azure_openai_endpoint,
            deployment=self._settings.azure_openai_deployment,
            api_version=self._settings.azure_openai_api_version,
        )
        self._openai.api_key = self._settings.openai_api_key.strip()
        self._openai.model = self._settings.openai.refine_model

    @property
    def configured(self) -> bool:
        return any(refiner.configured for refiner in self._refiners)

    async def refine(self, request: RefineRequest) -> RefineResult:
        chain = [refiner for refiner in self._refiners if refiner.configured]
        if not chain:
            raise TranslationException(
                TranslationError.CONFIGURATION,
                "Refine needs Azure OpenAI or an OpenAI API key. Add one under OCR in Settings.",
            )
        failures: list[tuple[str, TranslationException]] = []
        for refiner in chain:
            try:
                result = await refiner.refine(request)
            except TranslationException as error:
                if error.kind == TranslationError.CANCELLED:
                    raise
                failures.append((refiner.display_name, error))
                continue
            return replace(result, fallback_from=tuple(name for name, _ in failures))
        # Every service failed: name each one, because "Azure: 401" followed by an OpenAI
        # error alone would hide that the primary is the one that needs fixing.
        message = "; ".join(f"{name}: {error}" for name, error in failures)
        raise TranslationException(failures[-1][1].kind, message, retryable=failures[-1][1].retryable)

    async def close(self) -> None:
        for refiner in self._refiners:
            await refiner.close()
