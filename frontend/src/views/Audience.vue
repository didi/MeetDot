<template>
  <div id="audience-page" v-show="roomExistChecked">
    <div class="translation-lines">
      <div class="captions" ref="captions">
        <div class="translation-line" v-if="translationLines.length === 0">
          <span class="highlighted" v-t="'Live.empty_lines'" />
        </div>
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

    <div class="settings">
      <div class="setting captions">
        <label for="caption-language-dropdown" v-t="'Audience.language'" />:
        <select
          value="captionLanguage"
          @change="captionLanguageChanged(captionLanguage, $event)"
          id="caption-language-dropdown"
        >
          <option
            v-for="(val, key) in $globals.endonyms"
            :key="key"
            :value="key"
          >
            {{ val }}
          </option>
        </select>
      </div>
      <button
        class="nice-button-big end-button"
        @click="endLive"
        v-t="'Audience.end'"
      />
      <div class="home-link">
        {{ $t("Audience.home_link") }}
        <a href="https://meet.didi-nlp.xyz/">meet.didi-nlp.xyz</a>
      </div>
    </div>
  </div>
</template>

<script>
import Vue from "vue";
import backendService from "../service/index.js";
import utils from "../utils.js";
import RoomSettingsModal from "../components/RoomSettingsModal.vue";

export default {
  name: "Audience",
  data() {
    return {
      roomExistChecked: false,
      joining: false,
      translationLines: [],
      captionLanguage: this.$i18n.locale,
      userId: "audience-" + utils.randomString(8),
    };
  },
  mounted() {
    this.captions = this.$refs.captions;
    const roomId = this.$route.params.id;
    this.$socket.emit("on-page", "room/" + roomId);
    let that = this;
    backendService()
      .get("/rooms/" + roomId)
      .then((response) => {
        const room = response.data.room;
        if (room !== null) {
          that.roomExistChecked = true;
          that.room = room;
          // TODO - check if user already is in it
          that.join();
        } else {
          // Redirect if room does not exist
          Vue.$toast.info(this.$t("Room.error_does_not_exist", { roomId }));
          that.returnHome();
        }
      });
    this.sockets.subscribe("reconnect", () => {
      this.$socket.emit("/rejoin", {
        userId: this.userId,
        roomId: this.room.room_id,
      });
    });
    this.sockets.subscribe("leave-room", (message) => {
      Vue.$toast.info(message);
      this.endLive();
      this.returnHome();
    });
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      vm.fromRoute = from;
    });
  },
  methods: {
    join() {
      this.joining = true;
      this.$socket.emit(
        "/join",
        {
          captionLanguage: this.captionLanguage,
          name: this.userId,
          userId: this.userId,
          roomId: this.room.room_id,
          isAudience: true,
        },
        this.onJoined
      );
      window.addEventListener("beforeunload", this.endLive);
      window.addEventListener("popstate", this.endLive);
    },
    onJoined(couldJoin, errorMessage) {
      if (!couldJoin) {
        Vue.$toast.error(
          this.$t("Room.error_join", {
            roomId: this.room.room_id,
            errorMessage,
          })
        );
        this.returnHome();
      } else {
        const captionLanguage = this.captionLanguage;
        this.sockets.subscribe("/" + captionLanguage + "/translation", (msg) =>
          this.onTranslation(msg, captionLanguage)
        );
        this.joining = false;
      }
    },
    onTranslation(msg, language) {
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
          this.captions.lastElementChild.scrollIntoView({ behavior: "smooth" });
        });
      }
    },
    returnHome() {
      this.$router.push({ name: "Home" }).catch((err) => {
        if (err.name !== "NavigationDuplicated") {
          throw err;
        }
      });
    },
    endLive() {
      this.$socket.emit("disconnect-user", { userId: this.userId });
      this.returnHome();
    },
    captionLanguageChanged(originalLanguage, e) {
      const newLanguage = e.target.value;
      this.$i18n.locale = newLanguage;
      this.$socket.emit(
        "/caption-language-changed",
        {
          userId: this.userId,
          roomId: this.room.room_id,
          language: newLanguage,
        },
        (success) => {
          if (!success) {
            Vue.$toast.error(this.$t("Room.error_could_not_change_language"));
            this.captionLanguage = originalLanguage;
          } else {
            this.sockets.unsubscribe(`/${originalLanguage}/translation`);
            this.translationLines = [];
            this.captionLanguage = newLanguage;
            this.sockets.subscribe(`/${newLanguage}/translation`, (msg) =>
              this.onTranslation(msg, newLanguage)
            );
          }
        }
      );
    },
  },
};
</script>

<style scoped lang="scss">
#audience-page {
  display: flex;
  text-align: left;
  height: 100vh;
}
.settings {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 10px;

  & > div {
    margin: 20px 0;
  }
}
.translation-lines {
  flex: 2;
  scroll-behaviour: smooth;
  height: 100vh;
  overflow-y: scroll;
  box-sizing: border-box;
  background-color: rgba(0, 0, 0, 0.7);
  color: #ddd;
  font-weight: bold;
  font-size: 1.6vw;
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
#caption-language-dropdown {
  margin-left: 5px;
}
.end-button {
  background-color: #e60000;
  margin: 0;
  width: 200px;
}
</style>
