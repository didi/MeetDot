from flask import jsonify, Response

from ..namespace import Namespace
from .history_summarizer import history_summary, create_summary_string
from .history_download import prepare_history


class PostMeetingNamespace(Namespace):
    def register_rest_endpoints(self, app):
        @app.route("/summary/<room_id>/<lang>", methods=["GET"])
        def summary(room_id, lang):
            room = self.rooms.get(room_id, include_archived=True)
            translations = room.manager.translations
            summary_config = room.settings.interface["summarizer"]
            summary_config["language"] = lang
            max_segments = summary_config["max_segments"]
            segment_length_minutes = summary_config["segment_length_minutes"]
            logger = room.logger
            history = [
                (utter["speaker_name"], lang, utter["text"])
                for utter in translations[lang]
            ]
            seconds_elapsed = (
                0
                if len(translations[lang]) == 0
                else translations[lang][-1]["timestamp"]
                - translations[lang][0]["timestamp"]
            )
            segment_duration_threshold = (
                segment_length_minutes * 60
            )  # each segment roughly SEGMENT_LENGTH_MINUTES minutes long,

            num_segments = int(
                min(seconds_elapsed // segment_duration_threshold + 1, max_segments)
            )
            logger.info(
                f"[SUMMARIZER] seconds elapsed: {seconds_elapsed:.2f}; "
                f"number of segments: {num_segments}"
            )
            summary = history_summary(history, summary_config, logger, num_segments)
            return jsonify(summary)

        @app.route("/download-summary/<room_id>/<lang>", methods=["GET"])
        def download_summary(room_id, lang):
            summary_response = summary(room_id, lang).get_json()

            return Response(
                create_summary_string(summary_response),
                mimetype="text/plain",
                headers={
                    "Content-disposition": f"attachment;filename=summary-{lang}.txt"
                },
            )

        @app.route("/download-history/<room_id>/<lang>", methods=["GET"])
        def download_history(room_id, lang):
            room = self.rooms.get(room_id, include_archived=True)
            history = prepare_history(
                lang, room.manager.translations, room.manager.reactions
            )
            return Response(
                history,
                mimetype="text/plain",
                headers={
                    "Content-disposition": f"attachment;filename=history-{lang}.txt"
                },
            )

        # Bind all methods so they can be called for testing
        PostMeetingNamespace.summary = staticmethod(summary)
        PostMeetingNamespace.download_summary = staticmethod(download_summary)
        PostMeetingNamespace.download_history = staticmethod(download_history)
