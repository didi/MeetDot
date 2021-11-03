import re
from io import BytesIO

from flask import request, send_file
from PIL import Image

from ..namespace import Namespace


class ImageTranslationNamespace(Namespace):
    def register_rest_endpoints(self, app):
        @app.route(
            "/image_translation/<room_id>/<source_language>/<target_language>",
            methods=["GET", "PUT"],
        )
        async def translate_image(room_id, source_language, target_language):
            """Send an image to the backend and return a new one"""

            payload = request.form
            img_file = request.files["image"]
            img = Image.open(img_file.stream)

            room = self.rooms.get(room_id)
            result = await room.manager.on_image_data(
                payload["userId"], source_language, target_language, img
            )

            # Create a virtual file so it can be sent to the frontend
            iostream = BytesIO()
            result.result_image.save(iostream, format="PNG")
            iostream.seek(0)

            # if I need the metadata on the frontend, I will need to b64 encode the image
            return send_file(iostream, mimetype="image/png")
