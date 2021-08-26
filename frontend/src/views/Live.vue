<template>
  <div id="transcription-page" v-show="roomExistChecked">
    <v-dialog />
    <TranslateSelector />
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
      <div class="setting">
        <label for="audio-input-dropdown" v-t="'Live.audio_input'" />
        <select
          @change="audioInputChanged(audioInput, $event)"
          value="audioInput"
          id="audio-input-dropdown"
        >
          <option
            v-for="val in audioInputs"
            :key="val.deviceId"
            :value="val.deviceId"
          >
            {{ val.label }}
          </option>
        </select>
      </div>
      <div class="setting">
        <label for="spoken-language-dropdown" v-t="'Live.spoken_language'" />
        <select
          value="spokenLanguage"
          @change="spokenLanguageChanged(spokenLanguage, $event)"
          id="spoken-language-dropdown"
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
      <div class="setting captions">
        <label for="caption-language-dropdown" v-t="'Live.caption_language'" />
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
      <av-media :media="stream" type="frequ" />
      <div>
        <button
          class="nice-button-big end-button"
          @click="endLive"
          v-t="'Live.end'"
        />
        <button
          class="nice-button-big"
          @click="copyAudienceLink"
          v-t="'Live.copy_audience_invite'"
        />
      </div>
      <div class="instructions">
        <h3 v-t="'Live.how_to'" />
        <span v-t="'Live.download'" />
        <a href="https://vb-audio.com/Cable/index.htm">Virtual Audio Cable</a>
        <div class="platform-instruction">
          <h4>Windows 10</h4>
          <ol>
            <li v-t="'Live.extract_zip'" />
            <li v-t="'Live.set_input'" />
            <li v-t="'Live.set_output'" />
            <li v-t="'Live.finish'" />
          </ol>
        </div>
        <div class="platform-instruction">
          <h4>Mac</h4>
          <ol>
            <li v-t="'Live.locate_installer'" />
            <li v-t="'Live.audio_midi'" />
            <li v-t="'Live.click_plus'" />
            <li v-t="'Live.use_device'" />
            <li v-t="'Live.select_output_mac'" />
          </ol>
        </div>
      </div>
      <div class="room-settings">
        <cog @click="showRoomSettings(room)" />
      </div>
    </div>
  </div>
</template>

<script>
import Vue from "vue";
import RecordRTC from "recordrtc";
import backendService from "../service/index.js";
import utils from "../utils.js";
import TranslateSelector from "../components/TranslateSelector.vue";
import RoomSettingsModal from "../components/RoomSettingsModal.vue";
import Cog from "vue-material-design-icons/Cog.vue";
import throttle from "lodash/throttle";

export default {
  name: "Live",
  components: {
    Cog,
    TranslateSelector,
  },
  data() {
    return {
      roomExistChecked: false,
      joining: false,
      callActive: false,
      sentHeader: false,
      translationLines: [],
      spokenLanguage: this.$i18n.locale,
      captionLanguage: this.$i18n.locale,
      userId: "live-" + utils.randomString(8),
      audioInput: null,
      audioInputs: [],
      stream: null,
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
    this.sockets.subscribe("/update-language", this.onLanguageDetectionUpdate);
    this.sockets.subscribe("leave-room", (message) => {
      Vue.$toast.info(message);
      this.endLive();
    });
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      vm.fromRoute = from;
    });
  },
  beforeRouteLeave: function (to, from, next) {
    // Unsubscribe from socket before leaving room, to not get errors
    this.sockets.unsubscribe("reconnect");
    this.sockets.unsubscribe("leave-room");
    this.sockets.unsubscribe("/update-language");
    this.sockets.unsubscribe(`/${this.captionLanguage}/translation`);
    next();
  },
  methods: {
    join() {
      this.joining = true;
      this.$socket.emit(
        "/join",
        {
          spokenLanguage: this.spokenLanguage,
          captionLanguage: this.captionLanguage,
          name: this.userId,
          userId: this.userId,
          roomId: this.room.room_id,
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
        navigator.mediaDevices
          .getUserMedia({ audio: true })
          .then(this.successCallback)
          .catch(this.failureCallback);

        // Load list of microphones
        navigator.mediaDevices
          .enumerateDevices()
          .then(this.gotDevices)
          .catch(this.failureCallback);

        const captionLanguage = this.captionLanguage;
        this.sockets.subscribe("/" + captionLanguage + "/translation", (msg) =>
          this.onTranslation(msg, captionLanguage)
        );
        this.joining = false;
      }
    },
    gotDevices(deviceInfos) {
      this.audioInputs = deviceInfos.filter(
        (info) => info.kind === "audioinput"
      );
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
    onAudioData: function (blob) {
      let that = this;
      const reader = new FileReader();
      reader.onloadend = function () {
        let base64 = (/.+;\s*base64\s*,\s*(.+)$/i.exec(reader.result) || [])[1];
        if (that.sentHeader) {
          base64 = btoa(atob(base64).slice(that.$globals.wav_header_size));
        }
        if (that.room.room_id !== undefined) {
          that.$socket.emit("/audio/stream", {
            userId: that.userId,
            roomId: that.room.room_id,
            data: base64,
          });
          that.sentHeader = true;
        }
      };
      reader.readAsDataURL(blob);
    },
    returnHome() {
      this.$router.push({ name: "Home" }).catch((err) => {
        if (err.name !== "NavigationDuplicated") {
          throw err;
        }
      });
    },
    failureCallback(error) {
      Vue.$toast.error(this.$t("Room.error_user_media"));
      this.$socket.emit("disconnect-user", { userId: this.userId });
      console.error(JSON.stringify(error));
    },
    successCallback(stream) {
      const chunkSize = this.room.settings.services.asr.chunk_size;
      const sampleRate = this.room.settings.services.asr.sample_rate_hertz;
      const timeSliceMs = (chunkSize / sampleRate) * 1000;
      this.recordRTC = RecordRTC(stream, {
        type: "audio",
        mimeType: "audio/wav",
        recorderType: RecordRTC.StereoAudioRecorder,
        desiredSampRate: sampleRate,
        numberOfAudioChannels: 1,
        timeSlice: timeSliceMs,
        ondataavailable: this.onAudioData,
        disableLogs: true,
      });
      this.stream = stream;
      this.audioInput = this.stream.getAudioTracks()[0].getSettings().deviceId;
      this.recordRTC.startRecording();
      this.callActive = true;
    },
    endLive() {
      this.$socket.emit("disconnect-user", { userId: this.userId });
      if (this.callActive) {
        this.recordRTC.stopRecording();
        this.stream.getTracks().forEach(function (track) {
          track.stop();
        });
        this.callActive = false;
      }
      this.returnHome();
    },
    audioInputChanged(originalAudioInput, e) {
      const newAudioInput = e.target.value;
      this.recordRTC.stopRecording();
      this.stream.getAudioTracks()[0].stop();
      navigator.mediaDevices
        .getUserMedia({ audio: { deviceId: { exact: newAudioInput } } })
        .then(this.successCallback)
        .catch((error) => {
          this.failureCallback(error);
          this.audioInput = originalAudioInput;
        });
    },
    spokenLanguageChanged(originalLanguage, e) {
      const newLanguage = e.target.value;
      this.$socket.emit(
        "/spoken-language-changed",
        {
          userId: this.userId,
          roomId: this.room.room_id,
          language: newLanguage,
        },
        (success) => {
          if (!success) {
            Vue.$toast.error(this.$t("Room.error_could_not_change_language"));
            this.spokenLanguage = originalLanguage;
          } else {
            this.translationLines = [];
            this.spokenLanguage = newLanguage;
          }
        }
      );
    },
    captionLanguageChanged(originalLanguage, e) {
      const newLanguage = e.target.value;
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
    copyAudienceLink() {
      const roomId = this.$route.params.id;
      const audienceLink = `${window.location.origin}/audience/${roomId}`;
      utils.copyToClipboard(audienceLink);
      Vue.$toast.success(this.$t("Room.success_copied_invite"));
    },
    showRoomSettings() {
      this.$modal.show(
        RoomSettingsModal,
        {
          room: this.room,
        },
        {
          height: 600,
        }
      );
    },
    onLanguageDetectionUpdate(msg) {
      if (
        msg.session_id === this.userId &&
        msg.detected_language !== this.spokenLanguage
      ) {
        this.suggestLanguage(msg.detected_language);
      }
    },
    suggestLanguage: throttle(function (detectedLanguage) {
      this.$modal.show("dialog", {
        text: this.$t("Room.suggest_language_change", {
          language: this.$globals.displayLanguages[detectedLanguage],
        }),
        buttons: [
          {
            title: this.$t("General.no"),
            handler: () => {
              this.$modal.hide("dialog");
            },
          },
          {
            title: this.$t("General.yes"),
            handler: () => {
              this.spokenLanguage = detectedLanguage;
              this.captionLanguage = detectedLanguage;
              this.$modal.hide("dialog");
            },
          },
        ],
      });
      // Only show once every 10 seconds maximum
    }, 10000),
  },
};
</script>

<style scoped lang="scss">
#transcription-page {
  display: flex;
  text-align: left;
  height: 100vh;
}
.settings {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 10px;
  overflow-y: scroll;
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
#caption-language-dropdown,
#spoken-language-dropdown {
  margin-left: 5px;
}
.end-button {
  background-color: #e60000;
  margin: 0;
  width: 200px;
}
.instructions {
  flex-grow: 1;

  h4 {
    margin: 10px 0;
  }
  ol {
    font-size: 14px;
    margin-bottom: 0;
  }
}
.room-settings {
  text-align: right;
}
</style>
