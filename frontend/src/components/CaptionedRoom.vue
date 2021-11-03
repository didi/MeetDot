<template>
  <div class="flex-child">
    <ul>
      <li>room_id: {{ room !== null ? room.room_id : null }}</li>
    </ul>
    <div v-if="room">
      <button
        class="nice-button"
        v-on:click="disconnect()"
        key="change-settings-button"
      >
        Change Settings
      </button>
      <div class="translation-lines">
        <div class="captions" ref="captions">
          <div
            class="translation-line"
            v-for="line in translationLines"
            :key="line.index"
          >
            <span v-if="line.text.length">{{ line.text }}</span>
            <span class="highlighted" v-if="line.highlightedText.length">{{
              line.highlightedText
            }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-show="!room">
      <room-settings ref="settings"> </room-settings>
      <button
        class="nice-button"
        v-on:click="onFinalizeRoomSettings"
        key="finalize-button"
      >
        Finalize Settings
      </button>
    </div>
  </div>
</template>

<script>
import Vue from "vue";
import backendService from "../service/index.js";
import utils from "../utils.js";
import roomMixin from "../mixins/room.js";
import roomSettings from "./RoomSettings.vue";

export default {
  mixins: [roomMixin],
  components: { roomSettings },
  name: "Room",
  data() {
    return {
      translationLines: [],
    };
  },
  mounted() {},
  methods: {
    async clearTranslations() {
      if (this.translationLines && this.translationLines.length && this.room) {
        await this.onFinalizeRoomSettings();
      }
    },
    async onFinalizeRoomSettings() {
      await this.disconnectPromise();
      this.translationLines = [];
      await this._Start(this.$refs.settings.settings, this.$refs.settings.id);
    },
    onJoined() {
      const captionLanguage = this.captionLanguage;
      this.sockets.subscribe("/" + captionLanguage + "/translation", (msg) => {
        this.onTranslation(msg, captionLanguage);
      });
      this.stage = "6: subscribed";
    },
    onTranslation(msg, language) {
      if (msg.speaker_id !== this.user_id) {
        return;
      }
      if (language !== this.captionLanguage) {
        // Delayed message, received after unsubscribe
        return;
      }
      let lineAdded = false;
      let maxIndex = 0;
      for (let i = 0; i < msg.translation_lines.length; i++) {
        let text = msg.translation_lines[i];
        let highlightedText = "";

        if (msg.highlight_boundaries) {
          if (msg.highlight_boundaries[i] >= 0) {
            // highlight (fade out) the from hb[i] to the end characters
            // OR 0, which means highlight everything
            highlightedText = text.slice(msg.highlight_boundaries[i]);
            text = text.slice(0, msg.highlight_boundaries[i]);
          } // otherwise, -1, highlight nothing
        }

        const index = msg.line_index + i;
        maxIndex = Math.max(maxIndex, index);
        const line = { index, text, highlightedText };
        let lineFound = false;
        for (let j = 0; j < this.translationLines.length; j++) {
          if (index === this.translationLines[j].index) {
            this.$set(this.translationLines, j, line);
            lineFound = true;
          }
        }
        if (!lineFound) {
          this.translationLines.push(line);
          lineAdded = true;
        }
      }
      for (let j = 0; j < this.translationLines.length; j++) {
        if (maxIndex < this.translationLines[j].index) {
          // Clear later lines, if output has shrunk (rare)
          this.translationLines[j].text = "";
          this.translationLines[j].highlightedText = "";
        } else if (this.translationLines[j].index < msg.line_index) {
          // Remove highlight from older lines
          this.translationLines[j].text += this.translationLines[
            j
          ].highlightedText;
          this.translationLines[j].highlightedText = "";
        }
      }
      if (lineAdded) {
        // Scroll to the bottom of the translation
        this.$nextTick(() => {
          if (this.captions !== undefined) {
            // TODO figure out why the ref to captions can be undefined sometimes
            this.captions.lastElementChild.scrollIntoView({
              behavior: "smooth",
            });
          }
        });
      }
    },
  },
};
</script>

<style scoped lang="scss">
.translation-lines {
  flex: 2;
  scroll-behaviour: smooth;
  height: 100vh;
  overflow-y: scroll;
  box-sizing: border-box;
  background-color: rgba(0, 0, 0, 0.7);
  color: #ddd;
  font-weight: bold;
  font-size: 1.3vw;
  text-align: left;
  padding: 20px;

  &:empty {
    display: none;
  }

  .highlighted {
    font-weight: 600;
    color: #888;
  }
}

.flex-child {
  flex: 1;
  border: 2px solid yellow;
}

.flex-child:first-child {
  margin-right: 20px;
}
</style>
