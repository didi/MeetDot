class Participant:
    def __init__(
        self, user_id, spoken_language, caption_languages, name=None, is_audience=False
    ):
        self.user_id = user_id
        self.spoken_language = spoken_language
        self.caption_languages = caption_languages
        self.is_audience = is_audience  # if set to True, we don't listen to it, no st.
        self.name = name or self.user_id

        # Room gets set once participant joins
        self.room = None

    def __repr__(self):
        return f"{self.name} ({self.spoken_language})"

    def __str__(self):
        return self.__repr__()

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if k != "room"}


class AudienceMember(Participant):
    """
    Audience members don't send or receive audio streams, and don't count against the
    participant limit. They also don't have names, and only have a user_id and no name
    """

    def __init__(self, caption_languages):
        super().__init__(
            None, None, caption_languages=caption_languages, is_audience=True
        )

    def __repr__(self):
        return f"{self.user_id} (audience, {self.caption_languages})"
