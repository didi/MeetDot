class Participant:
    def __init__(self, name, spoken_language, caption_language, is_audience=False):
        self.name = name
        self.spoken_language = spoken_language
        self.caption_language = caption_language
        self.is_audience = is_audience  # if set to True, we don't listen to it, no st.

        # Room and user_id get set once participant joins
        self.room = None
        self.user_id = None

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

    def __init__(self, caption_language):
        super().__init__(
            None, None, caption_language=caption_language, is_audience=True
        )

    def __repr__(self):
        return f"{self.user_id} (audience, {self.caption_language})"
