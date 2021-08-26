<template>
  <div id="room-page" v-show="roomExistChecked">
    <v-dialog />
    <TranslateSelector v-if="!callActive" />
    <JoinRoom
      v-if="!callActive"
      ref="joinRoom"
      :room="room"
      :join="join"
      :joining="joining"
      :showWordGame="
        'interface' in room.settings &&
        room.settings.interface.games.word_guessing
      "
    />
    <div
      class="video-call-container"
      v-show="callActive"
      @keypress.m="toggleAudio"
      @keypress.v="toggleVideo"
      @keypress.s="toggleShareScreen"
      @keypress.l="toggleLanguageSettings"
      @keypress.p="$refs.historyPanel.toggleHistoryPanel(null)"
      @keypress.c="copyInviteLink"
      ref="callContainer"
      tabindex="0"
    >
      <div id="video-gallery" ref="gallery">
        <WordGuessingGame
          :roomId="room.room_id"
          :userId="userId"
          :participants="room.participants"
          v-if="
            'interface' in room.settings &&
            room.settings.interface.games.word_guessing
          "
          ref="wordGame"
        />
        <WebRTC
          ref="webrtc"
          :roomId="room.room_id"
          :participants="room.participants"
          :userId="userId"
          :distortion="
            Object.keys(room.settings).length != 0 &&
            'interface' in room.settings &&
            room.settings.interface.audio.distortion
          "
          @changeLayout="recalculateLayout"
        />
        <HistoryPanel
          :userId="userId"
          :language="captionLanguage"
          @toggle="onLayoutChanged"
          @download="downloadHistory"
          ref="historyPanel"
        />
      </div>
      <div class="video-gallery-bottom-bar">
        <b class="bottom-bar-text invite-link" @click="copyInviteLink"
          >{{ $t("Room.invite_link") }} <content-copy
        /></b>
        <div class="bottom-bar-icons">
          <button
            id="toggle-audio-share"
            :class="{ active: !audioEnabled }"
            @click="toggleAudio"
            :enabled="!joining"
            :title="$t('Room.mute')"
          >
            <div class="icon-wrapper">
              <img
                :src="
                  require('material-design-icons/av/2x_web/ic_mic_white_48dp.png')
                "
              />
            </div>
          </button>
          <button
            id="toggle-video-share"
            :class="{ active: !videoEnabled }"
            @click="toggleVideo"
            :enabled="!joining"
            :title="$t('Room.video')"
          >
            <div class="icon-wrapper">
              <img
                :src="
                  require('material-design-icons/av/2x_web/ic_videocam_white_48dp.png')
                "
              />
            </div>
          </button>
          <button
            id="toggle-screen-share"
            :class="{ active: sharingScreen }"
            @click="toggleShareScreen"
            :enabled="!joining"
            v-if="
              'interface' in room.settings &&
              room.settings.interface.screen_sharing
            "
            :title="$t('Room.share_screen')"
          >
            <div class="icon-wrapper">
              <img
                :src="
                  require('material-design-icons/communication/2x_web/ic_screen_share_white_48dp.png')
                "
              />
            </div>
          </button>
          <span class="language-settings-container">
            <div
              class="language-settings"
              ref="languageSettings"
              v-show="languageSettingsVisible"
            >
              <div class="setting">
                <label
                  for="spoken-language-dropdown"
                  v-t="'Room.spoken_language'"
                />
                <select v-model="spokenLanguage" id="spoken-language-dropdown">
                  <option
                    v-for="(val, key) in $globals.endonyms"
                    :key="key"
                    :value="key"
                  >
                    {{ val }}
                  </option>
                </select>
              </div>
              <div class="setting">
                <label
                  for="caption-language-dropdown"
                  v-t="'Room.caption_language'"
                />
                <select
                  v-model="captionLanguage"
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
            </div>
            <button
              id="translation-settings"
              @click="toggleLanguageSettings($event)"
              :enabled="!joining"
              :title="$t('Room.change_language')"
            >
              <div class="icon-wrapper">
                <img
                  :src="
                    require('material-design-icons/action/2x_web/ic_translate_white_48dp.png')
                  "
                />
              </div>
            </button>
          </span>
          <button
            id="end-call"
            @click="onEndCallButton"
            :title="$t('Room.end_call')"
          >
            <div class="icon-wrapper">
              <img
                :src="
                  require('material-design-icons/communication/2x_web/ic_call_end_white_48dp.png')
                "
              />
            </div>
          </button>
        </div>
        <div class="bottom-bar-right-buttons">
          <div @click="$refs.historyPanel.toggleHistoryPanel(null)">
            <span
              v-if="$refs.historyPanel && $refs.historyPanel.active"
              class="material-icons"
              :title="$t('Room.history_panel')"
            >
              speaker_notes_off
            </span>
            <span
              v-else
              class="material-icons"
              :title="$t('Room.history_panel')"
            >
              speaker_notes
            </span>
          </div>
          <span
            class="material-icons room-settings-cog"
            @click="showRoomSettings(room)"
            :title="$t('Room.settings')"
          >
            settings
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Vue from "vue";
import utils from "../utils.js";
import WebRTC from "../components/WebRTC.vue";
import RecordRTC from "recordrtc";
import backendService from "../service/index.js";
import JoinRoom from "../components/JoinRoom.vue";
import HistoryPanel from "../components/HistoryPanel.vue";
import WordGuessingGame from "../components/WordGuessingGame.vue";
import FeedbackModal from "../components/FeedbackModal.vue";
import RoomSettingsModal from "../components/RoomSettingsModal.vue";
import TranslateSelector from "../components/TranslateSelector.vue";
import debounce from "lodash/debounce";
import throttle from "lodash/throttle";
import ContentCopy from "vue-material-design-icons/ContentCopy.vue";
import DailyIFrame from "@daily-co/daily-js";

import "vue-material-design-icons/styles.css";

// ISSUE 5: https://github.com/westonsoftware/vue-webrtc/issues/5
import * as io from "socket.io-client";
window.io = io;
//

export default {
  name: "Room",
  data() {
    return {
      inviteLink: window.location.href,
      spokenLanguage: "",
      captionLanguage: "",
      callActive: false,
      joining: false,
      userId: "",
      sentHeader: false,
      socketURL: process.env.VUE_APP_BACKEND_BASE_URL + "/",
      userVideoElementId: "",
      roomExistChecked: false,
      audioEnabled: true,
      videoEnabled: true,
      languageSettingsVisible: false,
      lastRoomUpdate: 0,
      room: {
        participants: [],
        settings: {},
      },
      sharingScreen: false,
      recordRTC: null,
    };
  },
  mounted() {
    const roomId = this.$route.params.id;
    this.$socket.emit("on-page", "room/" + roomId);
    let that = this;
    this.webrtc = this.$refs.webrtc;
    backendService()
      .get("/rooms/" + roomId)
      .then((response) => {
        const room = response.data.room;
        if (room !== null) {
          that.room = room;
          that.lastRoomUpdate = response.data.time;
          that.roomExistChecked = true;
          that.$nextTick(() => {
            that.$refs.joinRoom.focusUserInput();
          });
        } else {
          // Redirect if room does not exist
          Vue.$toast.info(this.$t("Room.error_does_not_exist", { roomId }));
          that.returnHome();
        }
      });
    this.sockets.subscribe("room", (data) => {
      if (data.room !== null) {
        if (data.time > this.lastRoomUpdate) {
          that.room = data.room;
        }
        this.lastRoomUpdate = data.time;
      } else {
        // Redirect if room does not exist
        Vue.$toast.info(this.$t("Room.error_no_longer_exists", { roomId }));
        that.returnHome();
      }
    });
    this.sockets.subscribe("chatbot-audio", (data) => {
      this.webrtc.receivedChatbotAudio(data);
    });

    // Instantiate daily.co call object
    this.callObject = DailyIFrame.createCallObject();
    this.callObject
      .on("joined-meeting", this.joinedMeeting)
      .on("participant-joined", this.handleNewParticipantState)
      .on("participant-updated", this.handleNewParticipantState)
      .on("participant-left", this.handleNewParticipantState);
    const DAILY_BASE_URL = "https://didi.daily.co";
    this.callObject.load({
      url: DAILY_BASE_URL + "/" + roomId,
    });
    this.sockets.subscribe("reconnect", () => {
      this.$socket.emit("/rejoin", {
        userId: this.userId,
        roomId: this.room.room_id,
      });
    });
    this.sockets.subscribe("leave-room", (message) => {
      Vue.$toast.info(message);
      this.endCall();
      this.returnHome();
    });
  },
  beforeRouteLeave: function (to, from, next) {
    // Unsubscribe from socket before leaving room, to not get errors
    this.sockets.unsubscribe("room");
    this.sockets.unsubscribe("reconnect");
    this.sockets.unsubscribe("leave-room");
    this.sockets.unsubscribe("/transcript");
    this.sockets.unsubscribe("/update-language");
    this.sockets.unsubscribe(`/${this.captionLanguage}/translation`);
    this.sockets.unsubscribe(`/${this.captionLanguage}/complete-utterance`);
    this.sockets.unsubscribe("chatbot-audio");

    // Reset some variables
    this.$refs.historyPanel.set([]);

    if (this.$refs.wordGame) {
      this.$refs.wordGame.cleanUp();
    }

    next();
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      vm.fromRoute = from;
    });
  },
  methods: {
    join(name, spokenLanguage, captionLanguage) {
      this.joining = true;
      this.name = name;
      this.spokenLanguage = spokenLanguage;
      this.captionLanguage = captionLanguage;
      this.callObject.join({ userName: name });

      window.addEventListener("beforeunload", this.endCall);
      window.addEventListener("popstate", this.endCall);
      window.addEventListener("resize", this.onLayoutChanged);
      window.addEventListener("click", this.closeLanguageSettingsIfNeeded);
    },
    handleNewParticipantState() {
      const participants = this.callObject.participants();
      this.sharingScreen = participants.local.screen;
      this.webrtc.updateCallItems(participants);
    },
    joinedMeeting(e) {
      this.userId = e.participants.local.user_id;
      this.localAudioTrack = e.participants.local.audioTrack;

      // Temporarily add self to room participants so that name
      // is visible immediately, will get overwritten
      this.room.participants.push({
        name: this.name,
        user_id: this.userId,
        spoken_language: this.spokenLanguage,
        caption_language: this.captionLanguage,
      });
      this.webrtc.updateCallItems(e.participants);

      this.joining = false;
      this.callActive = true;
      this.onLayoutChanged();
      this.$socket.emit(
        "/join",
        {
          name: this.name,
          spokenLanguage: this.spokenLanguage,
          captionLanguage: this.captionLanguage,
          userId: this.userId,
          roomId: this.room.room_id,
        },
        this.onJoined
      );
      this.$nextTick(() => {
        this.$refs.callContainer.focus();
      });
    },
    onJoined(couldJoin, errorMessage, history, reactions) {
      if (!couldJoin) {
        Vue.$toast.error(
          this.$t("Room.error_join", {
            roomId: this.room.room_id,
            errorMessage,
          })
        );
        this.returnHome();
      } else {
        const chunkSize = this.room.settings.services.asr.chunk_size;
        const sampleRate = this.room.settings.services.asr.sample_rate_hertz;
        const timeSliceMs = (chunkSize / sampleRate) * 1000;
        this.recordRTC = RecordRTC(new MediaStream([this.localAudioTrack]), {
          type: "audio",
          mimeType: "audio/wav",
          recorderType: RecordRTC.StereoAudioRecorder,
          desiredSampRate: sampleRate,
          numberOfAudioChannels: 1,
          timeSlice: timeSliceMs,
          ondataavailable: this.onAudioData,
          disableLogs: true,
        });
        this.recordRTC.startRecording();

        this.$refs.historyPanel.set(history, reactions);

        // onTranscript is called for audio fragments in the original spoken language
        // onTranslation is called for these fragments, but translated into the caption language
        // onCompleteUtterance is called on audio sentences when ASR returns "isFinal"
        this.sockets.subscribe("/transcript", this.onTranscript);
        this.sockets.subscribe(
          "/update-language",
          this.onLanguageDetectionUpdate
        );
        this.sockets.subscribe(
          `/${this.captionLanguage}/translation`,
          this.onTranslation
        );
        this.sockets.subscribe(
          `/${this.captionLanguage}/complete-utterance`,
          this.$refs.historyPanel.onCompleteUtterance
        );

        // Call join on word-game, if necessary
        if (this.$refs.wordGame !== undefined) {
          this.$refs.wordGame.onJoined();
        }
        this.onLayoutChanged();
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
    onLanguageDetectionUpdate(msg) {
      if (
        msg.session_id === this.userId &&
        msg.detected_language !== this.spokenLanguage
      ) {
        this.suggestLanguage(msg.detected_language);
      }
    },
    onTranscript(msg) {
      this.webrtc.receivedTranscript(msg.speaker_id, msg.transcript);
    },
    onTranslation(msg) {
      this.webrtc.setTranslation(
        msg.speaker_id,
        msg.translation_lines,
        msg.line_index,
        this.room.settings.services.captioning.enable_highlight
          ? msg.highlight_boundaries
          : null
      );
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
      if (this.fromRoute.name === null) {
        // Joined with invite link, return to home page
        this.$router.push({ name: "Home" });
      } else if (this.fromRoute.name === "CreateRoom") {
        // Joined from create page, take back to admin
        this.$router.push({ name: "Admin" });
      } else if (this.fromRoute.name === "Room") {
        // Joined from room page, take back to home
        this.$router.push({ name: "Home" });
      } else {
        // Otherwise just go back to previous page
        this.$router.go(-1);
      }
    },
    onLayoutChanged: debounce(function () {
      this.recalculateLayout();
      this.$forceUpdate();
    }, 50),
    recalculateLayout(videoCount) {
      // Snippet from: https://dev.to/antondosov/building-a-video-gallery-just-like-in-zoom-4mam
      const aspectRatio = 16 / 9;

      const screenWidth = this.webrtc.$el.offsetWidth;
      const screenHeight = this.webrtc.$el.offsetHeight;

      let bestLayout = {
        area: 0,
        cols: 0,
        rows: 0,
        width: 0,
        height: 0,
      };

      if (this.$refs.gallery === undefined) {
        return;
      }
      if (videoCount === undefined) {
        videoCount = Math.max(
          Array.from(this.$refs.gallery.getElementsByTagName("video")).filter(
            (el) => el.offsetParent !== null // check that element is visible
          ).length +
            Array.from(this.$refs.gallery.getElementsByTagName("img")).filter(
              (el) => el.offsetParent !== null // check that element is visible
            ).length,
          1
        );
      }
      for (let cols = 1; cols <= videoCount; cols++) {
        const rows = Math.ceil(videoCount / cols);
        const hScale = screenWidth / (cols * aspectRatio);
        const vScale = screenHeight / rows;
        let width;
        let height;
        if (hScale <= vScale) {
          width = Math.floor(screenWidth / cols);
          height = Math.floor(width / aspectRatio);
        } else {
          height = Math.floor(screenHeight / rows);
          width = Math.floor(height * aspectRatio);
        }
        const area = width * height;
        if (area > bestLayout.area) {
          bestLayout = { area, width, height, rows, cols };
        }
      }

      this.$el.style.setProperty("--width", bestLayout.width + "px");
      this.$el.style.setProperty("--height", bestLayout.height + "px");
      this.$el.style.setProperty("--cols", bestLayout.cols + "");
    },
    toggleAudio() {
      if (this.audioEnabled) {
        this.recordRTC.pauseRecording();
      } else {
        this.recordRTC.resumeRecording();
      }
      this.audioEnabled = !this.audioEnabled;
      this.callObject.setLocalAudio(this.audioEnabled);
    },
    toggleVideo() {
      this.videoEnabled = !this.videoEnabled;
      this.callObject.setLocalVideo(this.videoEnabled);
    },
    closeLanguageSettingsIfNeeded(e) {
      if (this.languageSettingsVisible) {
        this.languageSettingsVisible = this.$refs.languageSettings.contains(
          e.target
        );
      }
    },
    toggleLanguageSettings(e) {
      e.stopPropagation();
      this.languageSettingsVisible = !this.languageSettingsVisible;
    },
    toggleShareScreen() {
      if (!this.sharingScreen) {
        this.callObject.startScreenShare();
      } else {
        this.callObject.stopScreenShare();
      }
    },
    endCall() {
      this.$socket.emit("disconnect-user", { userId: this.userId });
      if (this.callActive) {
        this.callObject.leave();
        this.callActive = false;
        if (this.recordRTC) {
          this.recordRTC.stopRecording();
        }
      }
    },
    onEndCallButton() {
      this.showFeedback();

      this.endCall();
      this.returnHome();
    },
    showFeedback() {
      this.$modal.show(
        FeedbackModal,
        { roomId: this.room.room_id },
        { height: "auto" }
      );
    },
    showRoomSettings() {
      this.$modal.show(
        RoomSettingsModal,
        {
          room: this.room,
        },
        {
          height: 600,
          width: 800,
        }
      );
    },
    copyInviteLink() {
      utils.copyToClipboard(this.inviteLink);
      Vue.$toast.success(this.$t("Room.success_copied_invite"));
    },
    downloadHistory() {
      backendService()
        .get(`/full_transcript/${this.room.room_id}/${this.captionLanguage}`, {
          responseType: "blob",
        })
        .then((response) => {
          const url = window.URL.createObjectURL(new Blob([response.data]));
          const link = document.createElement("a");
          link.href = url;
          link.setAttribute(
            "download",
            `transcript-${this.captionLanguage}.txt`
          ); //or any other extension
          document.body.appendChild(link);
          link.click();
        });
    },
  },
  components: {
    TranslateSelector,
    JoinRoom,
    HistoryPanel,
    WordGuessingGame,
    WebRTC,
    ContentCopy,
  },
  computed: {
    otherPlayerName: function () {
      if (this.room.participants.length === 2) {
        return this.room.participants.find((p) => p.user_id !== this.userId)
          .name;
      } else {
        return "";
      }
    },
  },
  watch: {
    captionLanguage: function (newLanguage, oldLanguage) {
      if (oldLanguage === "") {
        return;
      }
      this.$socket.emit(
        "/caption-language-changed",
        {
          userId: this.userId,
          roomId: this.room.room_id,
          language: newLanguage,
        },
        () => {
          this.sockets.unsubscribe(`/${oldLanguage}/translation`);
          this.sockets.unsubscribe(`/${oldLanguage}/complete-utterance`);
          this.sockets.subscribe(
            `/${newLanguage}/translation`,
            this.onTranslation
          );
          this.sockets.subscribe(
            `/${newLanguage}/complete-utterance`,
            this.$refs.historyPanel.onCompleteUtterance
          );
          this.$i18n.locale = newLanguage;
        }
      );
    },
    spokenLanguage(newLanguage, oldLanguage) {
      if (oldLanguage === "") {
        return;
      }
      this.$socket.emit("/spoken-language-changed", {
        userId: this.userId,
        roomId: this.room.room_id,
        language: newLanguage,
      });
    },
  },
};
</script>

<style scoped lang="scss">
.video-call-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

#video-gallery {
  display: flex;
  margin: 0 auto;
  flex: 1 1 auto;
  width: 100%;
  overflow: hidden;

  /* Mobile friendly */
  @media (max-width: 900px) {
    flex-direction: column;
  }

  @media (min-width: 900px) {
    flex-direction: row;
  }
}

.video-gallery-bottom-bar {
  z-index: 3;
  display: flex;
  margin: 0 auto;
  width: 100%;
  height: 60px;
  padding: 3px 0;
  background: #444;
  align-items: center;

  .bottom-bar-text {
    margin: 10px auto;
    width: 15%;
    color: white;
    text-align: left;
    padding-left: 10px;
    box-sizing: border-box;
  }

  .language-settings-container {
    position: relative;

    .language-settings {
      position: absolute;
      border: solid thin;
      bottom: 67px;
      left: -50%;
      background: #ddd;
      border-radius: 2px;
      padding: 10px;
      width: 250px;
      left: -100px;

      label {
        margin-right: 5px;
      }
    }
  }

  .bottom-bar-icons {
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: stretch;
    flex: 1;

    button {
      margin: 0 3px;
      padding: 3px;
      width: 60px;
      cursor: pointer;
      border: none;
      border-radius: 3px;
      background: #444;
      color: white;
      display: flex;
      flex-direction: column;

      &:hover {
        background: #777;
      }

      &.active .icon-wrapper {
        background: #b71c1c;
      }
      &:not(.active) .icon-wrapper {
        background: #2e7d32;
      }

      .icon-wrapper {
        border-radius: 50%;
        padding: 2px;
        margin-bottom: 3px;
        border: none;

        img {
          width: 100%;
          height: 100%;
          padding: 5px;
          box-sizing: border-box;
        }
      }

      span {
        flex-grow: 1;
      }
    }
  }

  .bottom-bar-right-buttons {
    color: white;
    width: 15%;
    padding-right: 10px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    align-items: flex-end;

    .material-icons,
    .material-design-icon {
      align-self: flex-end;
      padding: 2px;

      &:hover {
        color: lightgray;
      }
    }
  }

  #end-call .icon-wrapper {
    background: #b71c1c;
  }
}

.room-header {
  margin: 15px auto;
}
.room-settings-cog {
  float: right;
}
ul {
  margin: 0;
}
.content-copy-icon {
  margin-left: 10px;
}
.invite-link {
  cursor: pointer;
  &:hover {
    color: lightgray;
  }
}
</style>
