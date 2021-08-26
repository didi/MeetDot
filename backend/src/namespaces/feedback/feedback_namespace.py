import datetime
from email.message import EmailMessage
import os
import smtplib
from textwrap import dedent

from flask import jsonify, request

from ..namespace import Namespace


class FeedbackNamespace(Namespace):
    def register_rest_endpoints(self, app):
        @app.route("/feedback", methods=["POST"])
        def feedback():
            payload = request.json
            room_id = payload["roomId"]
            ratings = payload["feedbackValues"]
            text = payload["feedbackText"] or "none"
            contact = payload["contact"] or "none"

            body = f"""
                Feedback for room {room_id}:

                Contact: {contact}
                Ratings:
                    ASR: {ratings['asr']},
                    MT: {ratings['mt']},
                    Call quality: {ratings['call_quality']},
                    Latency: {ratings['latency']},
                Timestamp: {datetime.datetime.now().isoformat()}
                Text: {text}

                ==================================================
                """

            # Save feedback to a file
            with open(os.getenv("FEEDBACK_LOG"), "a") as fh:
                fh.write(dedent(body).lstrip())

            self.send_email(body)

            return jsonify({"success": True})

    def send_email(self, contents):
        """
        Sends an email with feedback contents via gmail's SMTP server.
        Supporting this is low priority, but it's nice to have
        so we don't have to check the logs.
        """

        if not os.getenv("FEEDBACK_EMAIL"):
            return

        gmail_user = os.getenv("GMAIL_ADDRESS")
        gmail_password = os.getenv("GMAIL_PASSWORD")

        msg = EmailMessage()
        msg["Subject"] = "MeetDot Feedback"
        msg["From"] = gmail_user
        msg["To"] = os.getenv("FEEDBACK_EMAIL")
        msg.set_content(contents)

        s = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        s.ehlo()
        s.login(gmail_user, gmail_password)
        s.send_message(msg, gmail_user)
        s.close()
