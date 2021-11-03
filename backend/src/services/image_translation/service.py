import asyncio
import time

from PIL import Image

from .interface import (
    ImageTranslationConfig,
    ImageTranslationRequest,
    ImageTranslationResponse,
    OcrRequest,
    OcrResponse,
    SubstitutionRequest,
    SubstitutionResponse,
)
from .ocr_service import OcrService
from ..translation.interface import TranslationRequest, TranslationResponse
from ..translation.service import TranslationService

# from .substitution_service import SubstitutionService # TODO [LS]: Implement this


class ImageTranslationService:
    def __init__(self, config: ImageTranslationConfig, logger):
        self.config = config
        self.logger = logger
        self.count = 1

        self.start_time = time.time()

        # TODO [LS]: Lazy evaluate these so they're not initialized until they're actually used
        self.ocr_service = OcrService(config, logger)
        self.mt_service = TranslationService(config.mt, None, logger)
        # self.substitution_service = SubstitutionService(config, logger)
        # TODO [LS]: Add this later. This is what will put the text on the image.
        # You can copy the skeleton from the ocr_service

    async def call(self, request: ImageTranslationRequest) -> ImageTranslationResponse:
        ocr_request = OcrRequest(
            source_language=request.source_language,
            target_language=request.target_language,
            source_image=request.source_image,
        )
        ocr_response = await self.ocr_service.call(ocr_request)
        source_image_path = self.logger.log_image(
            request.source_image, f"input-{self.count}-{request.source_language}.png"
        )
        self.logger.info(
            f"Calling image translation from {request.source_language} to "
            f"{request.target_language}. Saving at {source_image_path.name}"
        )

        mt_request = TranslationRequest(
            session_id=request.session_id,
            message_id=int((time.time() - self.start_time) * 1000),
            text=ocr_response.text,
            source_language=request.source_language,
            target_language=request.target_language,
        )
        mt_response = await self.mt_service.call(mt_request)

        sub_request = SubstitutionRequest(
            text=mt_response.translation,
            source_image=request.source_image,
        )

        # ### TEMPORARY, DUMMY IMPLEMENTATION ###
        # this just flips the image
        flipped_image = sub_request.source_image.transpose(Image.FLIP_TOP_BOTTOM)
        sub_response = SubstitutionResponse(
            text=sub_request.text, result_image=flipped_image
        )  # TODO: do some simple operation on this
        # ### REPLACE IT WITH THIS WHEN YOU IMPLEMENT A SUB SERVICE ###
        # sub_response = await self.substitution_service()
        # ### END

        response = ImageTranslationResponse(**sub_response.__dict__)

        dst_image_path = self.logger.log_image(
            response.result_image, f"output-{self.count}-{request.target_language}.png"
        )
        self.logger.info(f"Saving result to {dst_image_path}")
        self.count += 1

        return response

    def cleanup(self, session_id):
        self.mt_service.end_session(session_id, False)
