"""
Google cloud translation service class (using Python client library)
"""
from google.cloud import translate

from .interface import TranslationConfig, TranslationRequest, TranslationResponse
from .translator import Translator


class GoogleTranslator(Translator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = translate.TranslationServiceClient()
        # TODO: remove hardcoded Google Cloud constants
        self.project_id = "speech2text-260220"
        self.location = "us-central1"
        self.parent = f"projects/{self.project_id}/locations/{self.location}"

    def translate(self, request: TranslationRequest):
        if request.source_language == request.target_language:
            return request.text, None

        if len(request.text) == 0:
            # Return empty output for empty input
            return request.text, None

        response = self.client.translate_text(
            request={
                "parent": self.parent,
                "contents": [request.text],
                "mime_type": "text/plain",  # mime types: text/plain, text/html
                "source_language_code": request.source_language,
                "target_language_code": request.target_language,
            }
        )
        translation_candidates = []
        # Display the translation for each input text provided

        for translation in response.translations:
            translation_candidates.append(translation.translated_text)

        if len(translation_candidates) == 0:
            self.logger.error(
                "No translation candidates from Google translator service"
            )
            raise ValueError("No translation candidates from Google translator service")

        # now only return top 1 translation candidate

        return translation_candidates[0], None
