import json
import random
import re
import time
import uuid
from enum import Enum
from typing import List, Set, Optional

from room.participant import Participant
from utils import remove_chinese_punctuation, sum_dict

from .word_bank import Word, WordBank


class WordGuessingGameRole(str, Enum):
    GUESSER = "guesser"
    GIVER = "giver"


class WordResult(str, Enum):
    SKIPPED = "skipped"
    GUESSED = "guessed"
    GUESSED_BACKTRANSLATE = "guessed-in-backtranslate"
    INCOMPLETE = "incomplete"
    PENALIZED = "penalized"


class WordGameState(str, Enum):
    LOBBY = "LOBBY"
    ROUND_ACTIVE = "ROUND_ACTIVE"
    ROUND_FINISHED = "ROUND_FINISHED"
    GAME_FINISHED = "GAME_FINISHED"


INITIAL_SCORE = {
    "skipped": 0,
    "guessed": 0,
    "penalized": 0,
    "described": 0,
    "total_score": 0,
}


class WordGuessingGameRound:
    def __init__(self, roles, word_results, score):
        self.score = score
        self.word_results = word_results
        self.roles = roles

    def to_dict(self):
        return {
            "score": self.score,
            "word_results": [
                {"word": word.translations, "result": result.value}
                for word, result in self.word_results
            ],
            "roles": self.roles,
        }


class WordGuessingGame:
    COUNTDOWN_TIME_SECONDS = 3
    MIN_PLAYERS = 2

    def __init__(self, participants, emit_fn, logger):
        self.participants = participants
        self.emit_fn = emit_fn
        self.logger = logger.word_game_logger
        self.log_dir = logger.word_game_log_dir
        self.initialize()

    @property
    def guesser_languages(self):
        return set(g.spoken_language for g in self.guessers)

    @property
    def giver_language(self):
        return self.giver.spoken_language

    @property
    def ready_to_start(self):
        return (
            all(self.ready_states.get(p, False) for p in self.participants)
            and len(self.ready_states) >= WordGuessingGame.MIN_PLAYERS
        )

    @property
    def rounds_to_play(self):
        """
        Total number of rounds to play in the game, accounting for people who may have
        left part-way through
        """

        return len(self.rounds) + sum(
            p not in self.finished_givers_set for p in self.participants
        )

    def initialize(self):
        self.rounds = []
        self.word_bank = None
        self.ready_players = set()
        self.game_id = str(uuid.uuid4())[:8]
        self.ready_states = {p: False for p in self.participants}
        self.game_state = WordGameState.LOBBY

        self.word = None  # the word set being guessed right now
        self.displayed_word = None  # the specific word the giver sees
        self.start_time = 0
        self.end_time = 0
        self.players_to_roles = {}
        self.giver: Optional[Participant] = None
        self.guessers: List[Participant] = []
        self.word_results = []
        self.finished_givers_set = set()
        # Score for each player in this round (skipped score should be counted up)
        self.round_score = {
            user_id: INITIAL_SCORE.copy() for user_id in self.participants
        }
        # Score for all rounds so far
        self.game_score = {
            user_id: INITIAL_SCORE.copy() for user_id in self.participants
        }

        self.logger.info(f"Created word guessing game {self.game_id}")

    def players_changed(self):
        """
        Called when the set of players in the room has changed
        """
        self.ready_states = {
            p: self.ready_states.get(p, False) for p in self.participants
        }
        self.game_score = {
            p: self.game_score.get(p, INITIAL_SCORE.copy()) for p in self.participants
        }
        self.round_score = {
            p: self.round_score.get(p, INITIAL_SCORE.copy()) for p in self.participants
        }
        self.emit_fn(
            "game-state-changed",
            {
                "ready_states": self.ready_states,
                "rounds_to_play": self.rounds_to_play,
                "game_score": self.game_score,
                "round_score": self.round_score,
            },
        )

        if (
            self.game_state != WordGameState.LOBBY
            and len(self.participants) < WordGuessingGame.MIN_PLAYERS
        ):
            # If only one player remains, end the game
            self.initialize()
            self.emit_fn("game-ended", {})

        # TODO: if the giver left mid-round, end the round right away

    def player_ready(self, player_id):
        self.ready_states[player_id] = True
        self.emit_fn(
            "game-state-changed",
            {"ready_states": self.ready_states, "rounds_to_play": self.rounds_to_play},
        )

    def start_round(self, duration_seconds=10, max_skips=3):
        self.start_time = time.time() + WordGuessingGame.COUNTDOWN_TIME_SECONDS
        self.end_time = self.start_time + int(duration_seconds)
        self.max_skips = max_skips

        # init score for current round
        self.round_score = {
            p: self.round_score.get(p, INITIAL_SCORE.copy()) for p in self.participants
        }

        potential_givers = list(
            set(self.participants).difference(self.finished_givers_set)
        )
        giver_id = random.choice(potential_givers)
        guessers = list(filter(lambda p: p != giver_id, self.participants))
        self.players_to_roles = {
            giver_id: WordGuessingGameRole.GIVER,
            **{user_id: WordGuessingGameRole.GUESSER for user_id in guessers},
        }
        self.guessers = [self.participants[guesser_id] for guesser_id in guessers]
        self.giver = self.participants[giver_id]

        self.game_state = WordGameState.ROUND_ACTIVE

        game_languages = set([*self.guesser_languages, self.giver_language])
        self.word_bank = WordBank.get_word_bank(game_languages)
        self.word = self.word_bank.get_next()
        self.displayed_word = random.choice(self.word.translations[self.giver_language])
        self.word_results.append((self.word, WordResult.INCOMPLETE))

        self.logger.info(f"Starting round {len(self.rounds) + 1}")
        self.logger.info(f"Guessers: {self.guessers}")
        self.logger.info(f"Giver: {self.giver}")
        self.logger.info(f'Word is "{self.word}"')

        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "round_number": len(self.rounds) + 1,
            "max_skips": self.max_skips,
            "roles": {p: r.value for p, r in self.players_to_roles.items()},
            "round_score": self.round_score,
            "game_score": self.game_score,
            "word": self.displayed_word,
        }

    def send_new_word(self, reason: WordResult, speaker_id: str):
        """
        speaker_id: the speaker's ID who is responsible for the reason.
        """

        if reason == WordResult.SKIPPED:
            for score in (self.round_score, self.game_score):
                score[speaker_id]["skipped"] += 1
            self.logger.info(f'Skipped word "{self.word}"')
        elif reason == WordResult.GUESSED:
            for score in (self.round_score, self.game_score):
                score[speaker_id]["guessed"] += 1
                score[self.giver.user_id]["described"] += 1
            self.logger.info(f'Correctly guessed word "{self.word}"')
        elif reason == WordResult.GUESSED_BACKTRANSLATE:
            for score in (self.round_score, self.game_score):
                score[speaker_id]["guessed"] += 1
                score[self.giver.user_id]["described"] += 1
            self.logger.info(
                f'Correctly guessed word "{self.word}" (found in back translation)'
            )
        elif reason == WordResult.PENALIZED:
            for score in (self.round_score, self.game_score):
                score[speaker_id]["penalized"] += 1
            self.logger.info(
                f'Giver mentioned word "{self.word}", got one score penalized. Jump to next word.'
            )
        self.calculate_total_score()
        self.word_results[-1] = (self.word_results[-1][0], reason)

        prev_word = self.word.translations

        self.word = self.word_bank.get_next()
        self.displayed_word = random.choice(self.word.translations[self.giver_language])
        self.word_results.append((self.word, WordResult.INCOMPLETE))
        self.logger.info(f'Word is "{self.word}"')

        self.emit_fn(
            "new-word",
            {
                "round_score": self.round_score,
                "game_score": self.game_score,
                "word": self.displayed_word,
                "previous_word": prev_word,
                "reason": reason.value,
                "actor": speaker_id,
            },
        )

    def find_word(self, word: str, text: str, language: str) -> bool:
        """
        Check if a word is in the transcript `text` using a match tailored for each language
        """
        lang2match = {"en-US": "prefix", "es-ES": "prefix", "zh": "substring"}
        match_type = lang2match[language]

        # Normalize text
        word = word.lower()
        text = text.lower()

        if match_type == "prefix":
            # Prefix check: "son" will match "sons" but not "poisonous"

            return re.search("\\b" + word, text)
        elif match_type == "substring":
            # Substring check: "son" will match "sons" and "poison"

            # remove punctuations for Chinese
            text = remove_chinese_punctuation(text)

            return word in text

    def on_transcript(self, speaker_id, transcript):
        if time.time() > self.end_time:
            return
        speaker = self.participants.get(speaker_id)

        if speaker is None:
            # Speaker has left the call, unlikely but possible

            return

        speaker_language = speaker.spoken_language

        # check if giver mentions word accidentally

        if speaker_id == self.giver.user_id and self.find_word(
            self.displayed_word, transcript, speaker_language
        ):
            self.send_new_word(reason=WordResult.PENALIZED, speaker_id=speaker_id)

            return

        for word in self.word.translations[speaker_language]:
            if self.find_word(word, transcript, speaker_language):
                self.send_new_word(reason=WordResult.GUESSED, speaker_id=speaker_id)

                break

    def on_translation(self, speaker_id, language, translation):
        if (
            time.time() > self.end_time
            or self.players_to_roles.get(speaker_id, None)
            != WordGuessingGameRole.GUESSER
            or language != self.giver_language
        ):
            return

        # Working with the guesser's transcript in the giver's language

        for word in self.word.translations[language]:
            if self.find_word(word, translation, language):
                self.send_new_word(
                    reason=WordResult.GUESSED_BACKTRANSLATE, speaker_id=speaker_id
                )

                break

    def skip_word(self):
        if time.time() > self.end_time:
            return
        if self.round_score[self.giver.user_id]["skipped"] >= self.max_skips:
            return
        self.send_new_word(reason=WordResult.SKIPPED, speaker_id=self.giver.user_id)

    def end_round(self):
        if self.game_state == WordGameState.ROUND_ACTIVE:
            self.finished_givers_set.add(self.giver.user_id)
            is_final = all(p in self.finished_givers_set for p in self.participants)
            self.game_state = (
                WordGameState.GAME_FINISHED
                if is_final
                else WordGameState.ROUND_FINISHED
            )
            self.ready_states = {k: False for k in self.ready_states}
            self.rounds.append(
                WordGuessingGameRound(
                    roles={p: r.value for p, r in self.players_to_roles.items()},
                    word_results=self.word_results,
                    score=self.round_score.copy(),
                )
            )

            self.emit_fn(
                "game-state-changed",
                {
                    "ready_states": self.ready_states,
                    "rounds_to_play": self.rounds_to_play,
                },
            )

            self.reset_round_score()
            # Log score after round
            self.save_logs()

            self.word_results = []

            self.emit_fn(
                "round-ended",
                {"is_final": is_final},
            )

    def calculate_total_score(self):
        for score_type in (self.game_score, self.round_score):
            for speaker, score in score_type.items():
                score_type[speaker]["total_score"] = (
                    score["guessed"] + score["described"] - score["penalized"]
                )

    def reset_round_score(self):
        self.round_score = {
            user_id: INITIAL_SCORE.copy() for user_id in self.participants
        }

    def restart_if_necessary(self):
        """
        Restart the game if it is at the end of the game
        """

        if self.game_state != WordGameState.GAME_FINISHED:
            return

        self.initialize()

    def save_logs(self):
        self.logger.info(
            f"End of round {len(self.rounds)}, score is {self.round_score}"
        )
        self.logger.info(
            f"End of round {len(self.rounds)}, total score is {self.game_score}"
        )

        with open(self.log_dir / f"{self.game_id}.json", "w") as log_file:
            json.dump(
                {
                    "game_id": self.game_id,
                    "players": [
                        self.participants[player_id].to_dict()
                        if player_id in self.participants
                        else player_id
                        for player_id in self.players_to_roles
                    ],
                    "rounds": [r.to_dict() for r in self.rounds],
                },
                log_file,
                indent=2,
                ensure_ascii=False,
            )
