import gevent

from .interface import CaptioningConfig, CaptioningRequest, CaptioningResponse
from .linewise_scroll import LinewiseScrollStrategy
from .skype_style import SkypeStyleStrategy
from .word_level_sliding import WordLevelSlidingStrategy

CAPTION_STRATEGIES = {
    "linewise_scroll": LinewiseScrollStrategy,
    "wordwise_sliding_window": WordLevelSlidingStrategy,
    "skype_style": SkypeStyleStrategy,
}


class CaptioningService:
    def __init__(self, config: CaptioningConfig, logger, callback_fn):
        self.config = config
        self.logger = logger
        self.strategy = CAPTION_STRATEGIES[config.strategy](config)
        self.callback_fn = callback_fn

    def __call__(self, request: CaptioningRequest) -> CaptioningResponse:
        # sync way return response
        # return self.strategy.__call__(request)

        # async way return response through callback function
        response, delay_time = self.strategy(request)

        if delay_time and delay_time > 0.0:
            gevent.spawn_later(
                delay_time,
                self.callback_fn,
                service_request=request,
                service_response=response,
            )
        else:
            self.callback_fn(
                service_request=request,
                service_response=response,
            )

    def end_session(self, session_id):
        """
        Clear utterances after session
        """
        keys_to_pop = []

        for key in self.strategy.completed_utterances:
            if key[0] == session_id:
                keys_to_pop.append(key)

        for key in keys_to_pop:
            self.strategy.completed_utterances.pop(key)
