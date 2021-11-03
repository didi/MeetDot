from .interface import OcrRequest, OcrResponse


class FakeOcrProvider:
    async def call(self, request: OcrRequest) -> OcrResponse:
        return OcrResponse(text="The quick brown fox jumps over the lazy dog")


class OcrService:
    PROVIDERS = {"fake": FakeOcrProvider, "google": None, "tesseract": None}

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.provider = FakeOcrProvider()

    async def call(self, request: OcrRequest) -> OcrResponse:
        return await self.provider.call(request)
