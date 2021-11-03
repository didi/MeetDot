<template>
  <div v-show="active" class="panel">
    <span class="material-icons download-icon" v-if="active" @click="download"
      >file_download</span
    >
    <span
      class="material-icons update-icon"
      v-if="active && activePanel === 'summary'"
      @click="update"
      >update</span
    >
    <span class="material-icons close-icon" @click="togglePanel(false)"
      >close</span
    >
    <h3 class="panel-header">
      <span
        class="header-title"
        :class="activePanel === 'history' ? 'selected' : ''"
        @click="activePanel = 'history'"
        v-t="'Room.history'"
      />
      <div class="separator" />
      <span
        class="header-title"
        :class="activePanel === 'summary' ? 'selected' : ''"
        @click="
          activePanel = 'summary';
          update();
        "
        v-t="'Room.summary'"
      />
    </h3>
    <HistoryPanel
      v-bind="$props"
      ref="historyPanel"
      :active="activePanel === 'history'"
      class="inner-panel"
    />
    <SummaryPanel
      v-bind="$props"
      ref="summaryPanel"
      :active="activePanel === 'summary'"
      class="inner-panel"
    />
  </div>
</template>

<script>
import backendService from "../service/index.js";
import HistoryPanel from "./HistoryPanel.vue";
import SummaryPanel from "./SummaryPanel.vue";

export default {
  name: "Panel",
  data() {
    return {
      active: false,
      activePanel: "history",
      timeout: null,
    };
  },
  props: {
    userId: String,
    language: String, // caption language
    roomId: String,
  },
  methods: {
    togglePanel(val = null, activePanel = null) {
      if (val === null) {
        this.active = !this.active;
      } else {
        this.active = !!val;
      }
      if (this.active) {
        // Scroll to the bottom on opened
        this.$nextTick(() => {
          this.update();
        });
      }
      this.activePanel = activePanel;

      this.$emit("toggle");
    },
    update() {
      if (this.activePanel === "summary" && this.$refs.summaryPanel) {
        this.$nextTick(this.$refs.summaryPanel.update);
        clearTimeout(this.timeout);
        this.timeout = setTimeout(() => {
          this.update();
        }, 5 * 60 * 1000);
      }
    },
    download() {
      this.$nextTick(this.activePanelRef.download);
    },
    onCompleteUtterance(msg) {
      this.$refs.historyPanel.onCompleteUtterance(msg);
    },
    setHistory(history, reactions) {
      this.$refs.historyPanel.setHistory(history, reactions);
    },
  },
  computed: {
    activePanelRef() {
      if (this.activePanel === "history") {
        return this.$refs.historyPanel;
      } else if (this.activePanel === "summary") {
        return this.$refs.summaryPanel;
      } else {
        throw "Unrecognized panel: " + this.activePanel;
      }
    },
  },
  components: {
    HistoryPanel,
    SummaryPanel,
  },
};
</script>

<style scoped lang="scss">
.panel {
  box-sizing: border-box;
  background-color: #333;
  color: white;
  position: relative;
  flex: 1 0 30%;
  display: flex;
  flex-direction: column;

  /* Mobile friendly layout */
  @media (max-width: 900px) {
    max-height: 300px;
    width: 100%;
  }

  @media (min-width: 900px) {
    border-left: 2px solid #666;
    min-width: 300px;
    max-width: 500px;
    height: 100%;
  }

  .close-icon {
    position: absolute;
    left: 0;
    top: 8px;
    padding: 10px;
  }
  .download-icon {
    position: absolute;
    right: 0;
    top: 8px;
    padding: 10px 12px;
  }
  .update-icon {
    position: absolute;
    right: 35px;
    top: 8px;
    padding: 10px 12px;
  }

  .inner-panel {
    display: contents;
  }

  .panel-header {
    padding: 7px;
    margin-top: 10px;
    font-weight: normal;
    color: darkgray;

    .separator {
      width: 1px;
      height: 12px;
      display: inline-block;
      background-color: #797979;
      margin: 0 10px;
    }

    .header-title {
      cursor: pointer;
      user-select: none;
    }

    .selected {
      font-weight: bold;
      color: white;
    }
  }
}
</style>
