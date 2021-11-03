<template>
  <div id="post-meeting-page">
    <h1>{{ $t("PostMeeting.title") }}</h1>
    <div id="content">
      <div class="column">
        <SummaryPanel
          :active="true"
          :language="language"
          :roomId="roomId"
          ref="summary_panel"
        />
        <button @click="downloadSummary">
          {{ $t("PostMeeting.download_summary") }}
        </button>
        <button @click="downloadHistory">
          {{ $t("PostMeeting.download_history") }}
        </button>
      </div>
      <FeedbackPanel :roomId="$route.params.id" class="column" />
    </div>
    <button class="exit-button" @click="$router.push({ name: 'Home' })">
      {{ $t("General.exit") }}
    </button>
  </div>
</template>

<script>
import backendService from "../service/index.js";
import utils from "../utils.js";

import SummaryPanel from "../components/SummaryPanel.vue";
import FeedbackPanel from "../components/FeedbackPanel.vue";

export default {
  name: "PostMeeting",
  data() {
    return {
      roomId: this.$route.params.id,
      language: this.$i18n.locale,
    };
  },
  mounted() {
    this.$refs.summary_panel.update();
  },
  components: {
    SummaryPanel,
    FeedbackPanel,
  },
  methods: {
    downloadSummary() {
      utils.downloadFile(
        backendService,
        `/download-summary/${this.roomId}/${this.language}`
      );
    },
    downloadHistory() {
      utils.downloadFile(
        backendService,
        `/download-history/${this.roomId}/${this.language}`
      );
    },
  },
};
</script>

<style scoped lang="scss">
#post-meeting-page {
  padding: 0 20px;
}

#content {
  display: flex;
}

.column {
  display: block;
  flex: 1 1 0;
}

.exit-button {
  background-color: #e60000;
  font-size: 14pt;
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
