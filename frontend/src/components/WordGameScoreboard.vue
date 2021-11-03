<template>
  <div class="scoreboard-container">
    <div class="scoreboard-header">
      <div>
        {{
          $t("WordGuessingGame.round_number", {
            roundNumber: currentRound,
            roundsToPlay: roundsToPlay,
          })
        }}
      </div>
      <div
        :class="gameScoreSelected && 'title-selected'"
        class="scoreboard-title"
        @click="selectGameScore"
        v-t="'WordGuessingGame.game_score_title'"
      />
      <div
        :class="!gameScoreSelected && 'title-selected'"
        class="scoreboard-title"
        @click="selectRoundScore"
        v-t="'WordGuessingGame.round_score_title'"
      />
    </div>
    <table class="scoreboard">
      <thead>
        <tr>
          <th></th>
          <th v-t="'WordGameScoreboard.described'" />
          <th>+</th>
          <th v-t="'WordGameScoreboard.guessed'" />
          <th>-</th>
          <th v-t="'WordGameScoreboard.given_away'" />
          <th>=</th>
          <th v-t="'WordGameScoreboard.total_score'" />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="participant in rankedParticipants"
          :key="participant.user_id"
          :class="participant.user_id === userId && 'player-row'"
        >
          <th>{{ participant.name }}:</th>
          <td>
            {{
              gameScoreSelected
                ? gameScore[participant.user_id].described
                : roundScore[participant.user_id].described
            }}
          </td>
          <td>+</td>
          <td>
            {{
              gameScoreSelected
                ? gameScore[participant.user_id].guessed
                : roundScore[participant.user_id].guessed
            }}
          </td>
          <td>-</td>
          <td>
            {{
              gameScoreSelected
                ? gameScore[participant.user_id].penalized
                : roundScore[participant.user_id].penalized
            }}
          </td>
          <td>=</td>
          <td>
            {{
              gameScoreSelected
                ? gameScore[participant.user_id].total_score
                : roundScore[participant.user_id].total_score
            }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import utils from "../utils.js";

export default {
  name: "WordGameScoreboard",
  props: {
    userId: {
      type: String,
      required: true,
    },
    participants: {
      type: Array,
      required: true,
    },
    gameScore: {
      type: Object,
      required: true,
    },
    roundScore: {
      type: Object,
      required: true,
    },
    currentRound: {
      type: Number,
      required: true,
    },
    roundsToPlay: {
      type: Number,
      required: true,
    },
  },
  data() {
    return {
      gameScoreSelected: false,
    };
  },
  methods: {
    getDisplayName: utils.getDisplayName,
    selectGameScore() {
      this.gameScoreSelected = true;
    },
    selectRoundScore() {
      this.gameScoreSelected = false;
    },
  },
  computed: {
    rankedParticipants: function () {
      return this.participants
        .filter((p) => p.user_id in this.gameScore)
        .slice()
        .sort(
          (p1, p2) =>
            this.gameScore[p1.user_id].total_score <
            this.gameScore[p2.user_id].total_score
        );
    },
  },
};
</script>

<style scoped lang="scss">
.scoreboard-container {
  flex: 0 1 60%;
  margin-top: auto;
}

.scoreboard {
  width: 100%;
  text-align: center;
  margin-top: 15px;
  font-size: 20px;
  border-collapse: collapse;

  td,
  th {
    padding: 1px;
  }

  thead {
    font-size: 14px;
  }

  th:first-child {
    text-align: left;
    padding-left: 3px;
  }

  .player-row {
    background: rgba(0, 0, 0, 0.1);
  }
}
.scoreboard-title {
  display: inline-block;
  padding: 5px 10px;
  cursor: pointer;
  margin-top: 5px;
  border-radius: 3px;
}
.title-selected {
  background-color: darkgray;
  font-weight: bold;
}
</style>
