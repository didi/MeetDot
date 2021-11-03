<template>
  <div class="word-guessing-game">
    <h2 class="game-title" v-t="'WordGuessingGame.word_guessing_title'" />
    <div class="card" v-if="state === GameStates.LOBBY">
      <div class="player-ready-container">
        <table class="player-ready-table">
          <thead>
            <tr>
              <th v-t="'WordGuessingGame.player'"></th>
              <th v-t="'WordGuessingGame.is_ready'"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="participant in participants" :key="participant.user_id">
              <td>{{ participant.name }}</td>
              <td v-if="readyStates[participant.user_id]">✔</td>
              <td v-else>✗</td>
            </tr>
          </tbody>
        </table>
        <div>
          <button
            :disabled="readyStates[userId]"
            v-on:click="onReady"
            class="nice-button"
            v-t="'WordGuessingGame.ready'"
          />
        </div>
        <p
          v-if="participants.length < 2"
          v-t="'WordGuessingGame.need_more_people'"
        />
      </div>
      <div class="rules-container">
        <h4 v-t="'WordGuessingGame.rules_title'"></h4>
        <ul>
          <li>
            {{ $t("WordGuessingGame.game_rules_bullets[0]") }}
          </li>
          <li>
            {{ $t("WordGuessingGame.game_rules_bullets[1]") }}
          </li>
          <li>
            {{ $t("WordGuessingGame.game_rules_bullets[2]") }}
          </li>
          <li>
            {{ $t("WordGuessingGame.game_rules_bullets[3]") }}
          </li>
          <li>
            {{ $t("WordGuessingGame.game_rules_bullets[4]") }}
          </li>
          <li>
            {{ $t("WordGuessingGame.game_rules_bullets[5]") }}
          </li>
          <li>
            {{ $t("WordGuessingGame.game_rules_bullets[6]") }}
          </li>
          <li>
            {{ $t("WordGuessingGame.game_rules_bullets[7]") }}
          </li>
          <li>
            {{ $t("WordGuessingGame.game_rules_bullets[8]") }}
          </li>
          <li>
            {{ $t("WordGuessingGame.game_rules_bullets[9]") }}
          </li>
        </ul>
      </div>
    </div>

    <div v-if="state === GameStates.COUNTDOWN" class="card">
      <div class="countdown-title" v-t="'WordGuessingGame.countdown_title'" />
      <div class="countdown-number">{{ secondsToRoundStart }}</div>
      <div>
        {{ $t("WordGuessingGame.role_assignment", { role }) }}
      </div>
      <div v-if="role !== 'giver'">
        {{ $t("WordGuessingGame.giver_role_assignment", { giverName }) }}
      </div>
      <div
        v-if="role === 'giver'"
        v-t="'WordGuessingGame.giver_instructions'"
      />
      <div
        v-if="role === 'guesser'"
        v-t="'WordGuessingGame.guesser_instructions'"
      />
    </div>

    <div
      v-if="state === GameStates.ROUND_ACTIVE"
      class="card"
      :class="[
        (lastResult.justSkipped ||
          lastResult.otherJustGuessed ||
          lastResult.otherJustPenalized) &&
          'blink-neutral',
        lastResult.justGuessed && 'blink-good',
        lastResult.justPenalized && 'blink-bad',
      ]"
    >
      <div class="time-remaining-countdown">
        {{ minutesToRoundEnd.toString().padStart(2, "0") }}:{{
          secondsToRoundEnd.toString().padStart(2, "0")
        }}
      </div>
      <p>
        {{ $t("WordGuessingGame.role_assignment", { role }) }}
      </p>
      <div
        v-if="role !== 'giver'"
        v-t="{
          path: 'WordGuessingGame.giver_role_assignment',
          args: { giverName },
        }"
      />
      <div v-if="role === 'giver'">
        <div v-t="'WordGuessingGame.word_prompt'" />
        <div class="word-to-guess">{{ currentWord }}</div>
        <div class="nice-button-container">
          <button
            v-on:click="skipWord"
            :disabled="roundScore[userId].skipped >= maxSkips"
            class="nice-button"
            v-t="'WordGuessingGame.skip_word'"
          />
        </div>
        <div v-t="'WordGuessingGame.giver_instructions'" />
      </div>
      <div v-if="role === 'guesser'">
        <p v-t="'WordGuessingGame.guesser_instructions'" />
      </div>
      <div class="game-score">
        <div>
          {{
            $t("WordGuessingGame.correct_count", {
              n:
                role === "guesser"
                  ? roundScore[userId].guessed
                  : roundScore[userId].described,
            })
          }}
        </div>
        <div>
          {{
            $t("WordGuessingGame.skips_left_count", {
              n: maxSkips - roundScore[giverId].skipped,
            })
          }}
        </div>
      </div>
      <WordGameScoreboard
        :userId="userId"
        :participants="participants"
        :gameScore="gameScore"
        :roundScore="roundScore"
        :currentRound="currentRound"
        :roundsToPlay="roundsToPlay"
      />
    </div>

    <div
      v-if="
        state === GameStates.ROUND_ACTIVE &&
        (lastResult.justSkipped ||
          lastResult.justGuessed ||
          lastResult.justPenalized ||
          lastResult.otherJustGuessed ||
          lastResult.otherJustPenalized)
      "
      class="game-popup"
    >
      <template v-if="role === 'giver'">
        <p v-if="lastResult.reason === 'skipped'">
          {{ $t("WordGuessingGame.you_skipped", { word: lastResult.word }) }}
        </p>
        <p
          v-if="
            lastResult.reason === 'guessed' ||
            lastResult.reason === 'guessed-in-backtranslate'
          "
          v-t="{
            path: 'WordGuessingGame.got_it',
            args: { name: lastResult.name, word: lastResult.word },
          }"
        />
        <p v-if="lastResult.reason === 'penalized'">
          {{ $t("WordGuessingGame.you_penalized", { word: lastResult.word }) }}
        </p>
      </template>
      <template v-if="role === 'guesser'">
        <p v-if="lastResult.reason === 'skipped'">
          {{
            $t("WordGuessingGame.giver_skipped", {
              name: lastResult.name,
              word: lastResult.word,
            })
          }}
        </p>
        <p v-if="lastResult.reason === 'guessed' && lastResult.me">
          {{
            $t("WordGuessingGame.you_got_word", {
              word: lastResult.word,
            })
          }}
        </p>
        <p v-if="lastResult.reason === 'guessed' && !lastResult.me">
          {{
            $t("WordGuessingGame.got_word", {
              name: lastResult.name,
              word: lastResult.word,
            })
          }}
        </p>
        <!-- If the word was only found in backtranslation, don't show it, because the guesser probably said a word that's not in our list -->
        <p
          v-if="
            lastResult.reason === 'guessed-in-backtranslate && lastResult.me'
          "
        >
          {{ $t("WordGuessingGame.you_got_it") }}
        </p>
        <p
          v-if="
            lastResult.reason === 'guessed-in-backtranslate && !lastResult.me'
          "
        >
          {{ $t("WordGuessingGame.got_it", { name: lastResult.name }) }}
        </p>
        <p v-if="lastResult.reason === 'penalized'">
          {{
            $t("WordGuessingGame.penalized", {
              name: lastResult.name,
              word: lastResult.word,
            })
          }}
        </p>
      </template>
    </div>

    <div v-if="state === GameStates.ROUND_FINISHED" class="card">
      <div class="player-ready-container">
        <table class="player-ready-table">
          <thead>
            <tr>
              <th v-t="'WordGuessingGame.player'"></th>
              <th v-t="'WordGuessingGame.is_ready'"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="participant in participants" :key="participant.user_id">
              <td>{{ participant.name }}</td>
              <td v-if="readyStates[participant.user_id]">✔</td>
              <td v-else>✗</td>
            </tr>
          </tbody>
        </table>
        <div>
          <button
            :disabled="readyStates[userId]"
            v-on:click="onReady"
            class="nice-button"
            v-t="'WordGuessingGame.play_another_round'"
          />
        </div>
      </div>
      <WordGameScoreboard
        :userId="userId"
        :participants="participants"
        :gameScore="gameScore"
        :roundScore="roundScore"
        :currentRound="currentRound"
        :roundsToPlay="roundsToPlay"
      />
    </div>

    <div v-if="state === GameStates.GAME_FINISHED" class="card">
      <WordGameScoreboard
        :userId="userId"
        :participants="participants"
        :gameScore="gameScore"
        :roundScore="roundScore"
        :currentRound="currentRound"
        :roundsToPlay="roundsToPlay"
      />
      <button
        v-on:click="playAgain"
        class="nice-button"
        v-t="'WordGuessingGame.play_again'"
      />
    </div>
  </div>
</template>

<script>
import utils from "../utils.js";
import WordGameScoreboard from "../components/WordGameScoreboard.vue";

const GameStates = {
  LOBBY: 0,
  COUNTDOWN: 1,
  ROUND_ACTIVE: 2,
  ROUND_FINISHED: 3,
  GAME_FINISHED: 4,
};

export default {
  name: "WordGuessingGame",
  props: {
    userId: {
      type: String,
      required: true,
    },
    roomId: {
      type: String,
      required: true,
    },
    participants: {
      type: Array,
      required: true,
    },
  },
  components: {
    WordGameScoreboard,
  },
  data() {
    return {
      currentWord: "",
      currentRound: 0,
      roundsToPlay: 0,
      roundStartTime: 0,
      roundEndTime: 0,
      secondsToRoundStart: 0,
      totalSecondsToRoundEnd: 0,
      roundScore: {},
      gameScore: {},
      lastResult: {
        justSkipped: false,
        justGuessed: false,
        otherJustGuessed: false,
        justPenalized: false,
        otherJustPenalized: false,
        reason: "",
        word: "",
        actorName: "",
      },
      GameStates: GameStates,
      role: null,
      state: GameStates.LOBBY,
      readyStates: this.initializeReadyStates(),
    };
  },
  methods: {
    onReady: function () {
      this.$socket.emit("player-ready", {
        userId: this.userId,
        roomId: this.roomId,
      });
    },
    playAgain: function () {
      this.$socket.emit("play-again", {
        roomId: this.roomId,
      });
      this.state = GameStates.LOBBY;
    },
    skipWord: function () {
      this.$socket.emit("skip-word", {
        userId: this.userId,
        roomId: this.roomId,
      });
    },
    updateCountdownVariables: function () {
      // Update countdown timer while game is active
      if (this.roundEndTime > Date.now() / 1000) {
        this.secondsToRoundStart = Math.ceil(
          this.roundStartTime - Date.now() / 1000
        );
        this.totalSecondsToRoundEnd = Math.ceil(
          this.roundEndTime - Date.now() / 1000
        );
        setTimeout(this.updateCountdownVariables, 100);
      }
    },
    initializeReadyStates: function () {
      let readyStates = {};
      for (let i = 0; i < this.participants.length; i++) {
        readyStates[this.participants[i].user_id] = false;
      }
      return readyStates;
    },
    getDisplayName: utils.getDisplayName,
    onJoined: function () {
      let that = this;
      this.language = this.participants.find(
        (p) => p.user_id == this.userId
      ).spoken_language;

      this.$socket.emit(
        "player-joined",
        {
          roomId: this.roomId,
          userId: this.userId,
        },
        (msg) => {
          that.state = GameStates[msg.state];
          if (that.state == GameStates.LOBBY) {
            return;
          }
          that.currentRound = msg.round_number;
          that.roundScore = msg.round_score;
          that.gameScore = msg.game_score;
          if (that.state == GameStates.ROUND_ACTIVE) {
            that.roundStartTime = msg.start_time;
            that.roundEndTime = msg.end_time;
            that.totalSecondsToRoundEnd = Math.ceil(
              that.roundEndTime - Date.now() / 1000
            );
            that.maxSkips = msg.max_skips;
            that.currentWord = msg.word;
            that.role = msg.roles[that.userId];
            that.giverId = Object.keys(msg.roles).find(
              (p) => msg.roles[p] == "giver"
            );
            that.updateGiverName();
            setTimeout(function () {
              that.$socket.emit("end-round", {
                userId: that.userId,
                roomId: that.roomId,
              });
            }, that.totalSecondsToRoundEnd * 1000);
          }
        }
      );
    },
    onNewWord: function (msg) {
      let lastResult = this.lastResult;
      lastResult.word = msg.previous_word[this.language];
      lastResult.reason = msg.reason;
      lastResult.me = msg.actor === this.userId;
      lastResult.name = this.participants.find(
        (p) => p.user_id == msg.actor
      ).name;

      setTimeout(() => {
        if (lastResult.word == msg.previous_word[this.language]) {
          lastResult.word = undefined;
          lastResult.reason = undefined;
        }
      }, 5000);

      // Blink the message with the last result
      const BLINK_TIME = 2500;
      if (msg.reason === "skipped") {
        lastResult.justSkipped = true;
        setTimeout(function () {
          lastResult.justSkipped = false;
        }, BLINK_TIME);
      } else if (
        (msg.reason === "guessed" ||
          msg.reason === "guessed-in-backtranslate") &&
        lastResult.me
      ) {
        lastResult.justGuessed = true;
        setTimeout(function () {
          lastResult.justGuessed = false;
        }, BLINK_TIME);
      } else if (
        (msg.reason === "guessed" ||
          msg.reason === "guessed-in-backtranslate") &&
        !lastResult.me
      ) {
        lastResult.otherJustGuessed = true;
        setTimeout(function () {
          lastResult.otherJustGuessed = false;
        }, BLINK_TIME);
      } else if (msg.reason === "penalized" && lastResult.me) {
        lastResult.justPenalized = true;
        setTimeout(function () {
          lastResult.justPenalized = false;
        }, BLINK_TIME);
      } else if (msg.reason === "penalized" && !lastResult.me) {
        lastResult.justPenalized = true;
        setTimeout(function () {
          lastResult.justPenalized = false;
        }, BLINK_TIME);
      }
      this.roundScore = msg.round_score;
      this.gameScore = msg.game_score;
      this.currentWord = msg.word;
    },
    cleanUp() {
      this.sockets.unsubscribe("game-state-changed");
      this.sockets.unsubscribe("round-started");
      this.sockets.unsubscribe("round-ended");
      this.sockets.unsubscribe("game-ended");
      this.sockets.unsubscribe("new-word");
    },
    updateGiverName: function () {
      const participant = this.participants.find(
        (p) => p.user_id == this.giverId
      );
      if (participant !== undefined) {
        this.giverName = participant.name;
      } else {
        this.giverName = this.$t("WordGuessingGame.giver");
      }
    },
  },
  mounted() {
    let that = this;

    this.sockets.subscribe("game-state-changed", function (msg) {
      that.readyStates = msg.ready_states;
      that.roundsToPlay = msg.rounds_to_play;
      if (msg.game_score !== undefined) {
        that.gameScore = msg.game_score;
      }
      if (msg.round_score !== undefined) {
        that.roundScore = msg.round_score;
      }
    });
    this.sockets.subscribe("round-started", function (msg) {
      this.roundStartTime = msg.start_time;
      this.roundEndTime = msg.end_time;
      this.maxSkips = msg.max_skips;
      this.currentRound = msg.round_number;
      this.role = msg.roles[this.userId];
      this.giverId = Object.keys(msg.roles).find(
        (p) => msg.roles[p] == "giver"
      );
      this.updateGiverName();
      this.currentWord = msg.word;
      this.roundScore = msg.round_score;
      this.gameScore = msg.game_score;
      this.state = GameStates.COUNTDOWN;
      this.updateCountdownVariables();
      setTimeout(function () {
        that.state = GameStates.ROUND_ACTIVE;
      }, this.secondsToRoundStart * 1000);
      setTimeout(function () {
        that.$socket.emit("end-round", {
          userId: that.userId,
          roomId: that.roomId,
        });
      }, this.totalSecondsToRoundEnd * 1000);
    });
    this.sockets.subscribe("round-ended", function (msg) {
      if (msg.is_final) {
        that.state = GameStates.GAME_FINISHED;
      } else {
        that.state = GameStates.ROUND_FINISHED;
      }
    });
    this.sockets.subscribe("game-ended", function () {
      that.state = GameStates.GAME_FINISHED;
    });
    this.sockets.subscribe("new-word", this.onNewWord);
  },
  computed: {
    minutesToRoundEnd: function () {
      return Math.max(0, Math.floor(this.totalSecondsToRoundEnd / 60));
    },
    secondsToRoundEnd: function () {
      return Math.max(0, Math.ceil(this.totalSecondsToRoundEnd % 60));
    },
  },
};
</script>

<style scoped lang="scss">
.word-guessing-game {
  box-sizing: border-box;
  padding: 10px;
  background-color: lightgrey;
  overflow: auto;
  position: relative;
  flex: 0 0 400px;
  border-left: 2px solid #666;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.game-title {
  margin: 5px;
}

ul {
  text-align: left;
}

.blink-neutral {
  background-color: lightblue;
}

.blink-good {
  background-color: lightgreen;
}

.blink-bad {
  background-color: pink;
}

.confirm-game-title {
  font-weight: bold;
  margin: 10px 0;
}

.countdown-title {
  font-size: 18px;
  margin-top: 20px;
}

.countdown-number {
  font-size: 48px;
  margin-bottom: 10px;
}

.time-remaining-countdown {
  font-weight: bold;
  font-size: 18px;
  width: 100%;
}

.word-to-guess {
  font-size: 32px;
  text-transform: uppercase;
  font-weight: bold;
  margin: 5px 0;
}

.game-score {
  width: 75%;
  text-align: left;
  font-size: 24px;
  margin-top: 15px;
  display: inline-block;
}

.game-popup {
  -webkit-text-stroke: 1px black;
  color: white;
  font-weight: bold;
  position: absolute;
  top: calc(50% - 48px / 2);
  width: 80%;
  text-align: center;
  font-size: 48px;
  box-sizing: border-box;
}

.role {
  font-size: 20px;
}
.nice-button {
  margin: 10px auto;
}

.card {
  display: flex;
  flex-direction: column;
  flex: 1;
  transition: background-color 0.3s ease-in-out;
}

.player-ready-container {
  margin-top: 15px;

  .player-ready-table {
    width: 80%;
    th,
    tr {
      text-align: left;
    }
  }
}
</style>
