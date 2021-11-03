<template>
  <div v-if="active">
    <div class="summary" ref="summary">
      <div v-for="(utterance, i) in summary" :key="i" class="summary-line">
        <div class="text-line">
          <span class="segment-header"
            >{{ $t("Room.topic") }} {{ i + 1 }}
          </span>
          <span class="speaker-name">{{ utterance.speakers }}</span>
          <span> ({{ utterance.length }}) </span>
        </div>
        <p
          class="summary-header-properties"
          v-for="(
            [keyphrase, , leftContext, rightContext], i
          ) in utterance.key_snippets"
          :key="i"
        >
          <span>{{ leftContext }}</span>
          <span class="keyphrase"> {{ keyphrase }} </span>
          <span>{{ rightContext }}</span>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import backendService from "../service/index.js";
import utils from "../utils.js";

export default {
  name: "SummaryPanel",
  data() {
    return {
      summary: [],
    };
  },
  props: {
    active: Boolean,
    language: String,
    roomId: String,
  },
  methods: {
    update() {
      backendService()
        .get(`/summary/${this.roomId}/${this.language}`)
        .then((response) => {
          this.summary = response.data;
        });
    },
    download() {
      utils.downloadFile(
        backendService,
        `/download-summary/${this.roomId}/${this.language}`
      );
    },
  },
  watch: {
    async active(val) {
      if (val) {
        await this.$nextTick();
        this.$refs.summary.scrollTop = this.$refs.summary.scrollHeight;
      }
    },
    language() {
      this.update();
    },
  },
};
</script>

<style scoped lang="scss">
.summary-header {
  padding-bottom: 7px;
}

.summary {
  overflow-y: auto;
}
.summary-line {
  text-align: left;
  padding: 5px;

  .text-line {
    margin: 3px 0;
    border-bottom: black solid 1px;
    display: flex;

    .segment-header {
      font-weight: 700;
    }

    .speaker-name {
      flex: 1 1 auto;
      text-align: center;
    }
  }

  .summary-table {
    width: 100%;
  }
  .summary-header-properties {
    padding: 0 5px;

    & > span {
      display: inline-block;
    }
    & > .keyphrase {
      font-weight: 700;
    }
  }
}
</style>
