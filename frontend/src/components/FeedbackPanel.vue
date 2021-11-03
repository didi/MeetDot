<template>
  <div v-if="!submitted">
    <div class="feedback-row">
      <h3>{{ $t("Feedback.rate_us") }}</h3>
    </div>
    <div class="feedback-row" id="rating-panel">
      <table class="feedback-ratings">
        <tr v-for="metric in Object.keys(feedbackValues)" :key="metric">
          <th>{{ $t(`Feedback.${metric}`) }}</th>
          <td class="material-icons">
            <span
              :class="{
                'thumb-down-icon': true,
                selected: feedbackValues[metric] === false,
              }"
              @click="select(metric, false)"
            >
              thumb_down
            </span>
            <span
              :class="{
                'thumb-up-icon': true,
                selected: feedbackValues[metric] === true,
              }"
              @click="select(metric, true)"
            >
              thumb_up
            </span>
          </td>
        </tr>
      </table>
    </div>

    <div class="feedback-row">
      <textarea
        type="text"
        class="freetext"
        v-model="feedbackText"
        :placeholder="$t('Feedback.comments')"
      ></textarea>
    </div>

    <div class="feedback-row">
      <input
        type="text"
        v-model="contact"
        :placeholder="$t('Feedback.contact')"
      />
    </div>

    <div class="feedback-row">
      <button
        @click="submit"
        :disabled="
          Object.values(this.feedbackValues).every((x) => x === undefined) &&
          this.feedbackText.length === 0
        "
      >
        {{ $t("General.submit") }}
      </button>
    </div>
  </div>
  <div v-else>
    {{ $t("Feedback.thanks") }}
  </div>
</template>

<script>
import backendService from "../service/index.js";

export default {
  name: "FeedbackPanel",
  props: {
    roomId: {
      type: String,
      required: true,
    },
  },
  data() {
    const feedbackValues = {
      asr: null,
      mt: null,
      call_quality: null,
      latency: null,
    };

    return {
      feedbackValues,
      feedbackText: "",
      contact: "",
      submitted: false,
    };
  },
  methods: {
    select(metric, value) {
      if (this.feedbackValues[metric] !== value) {
        this.$set(this.feedbackValues, metric, value);
      } else {
        this.$set(this.feedbackValues, metric, undefined);
      }
    },
    submit() {
      backendService()
        .post("/feedback", {
          roomId: this.roomId,
          feedbackValues: this.feedbackValues,
          feedbackText: this.feedbackText,
          contact: this.contact,
        })
        .then(() => {
          this.$toast.success(this.$t("Feedback.received"));
        });

      this.submitted = true;
      this.$forceUpdate();
    },
  },
};
</script>

<style lang="scss" scoped>
span {
  user-select: none;
}

table.feedback-ratings {
  width: 100%;
  padding: 0 50px;

  td {
    padding: 5px 0;
  }
}

.feedback-row {
  margin-bottom: 10px;
}

#close {
  position: absolute;
  top: 5px;
  right: 5px;
}

.thumb-up-icon {
  color: #6a6;
  border-radius: 3px;
  padding: 3px;

  &:hover {
    background-color: #bdb;
  }
  &.selected {
    color: #080;
    background-color: #bdb;
  }
}
.thumb-down-icon {
  border-radius: 3px;
  padding: 3px 0 3px 3px;
  margin-right: 10px;

  color: #a66;

  &:hover {
    background-color: #dbb;
  }
  &.selected {
    color: #800;
    background-color: #dbb;
  }
}

.freetext {
  height: 350px;
  max-height: 30vh;
  width: 80%;
}

button {
  width: 100px;
  height: 40px;
  margin: 0 5px;

  background-color: blue;
  border: none;
  border-radius: 5px;
  color: white;
  cursor: pointer;
}
</style>
