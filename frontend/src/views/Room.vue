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
      :class="mouseActive ? '' : 'mouse-inactive'"
      v-show="callActive"
      @keypress.m="toggleAudio"
      @keypress.v="toggleVideo"
      @keypress.s="toggleShareScreen"
      @keypress.l="toggleLanguageSettings"
      @keypress.p="$refs.panel.togglePanel(null, 'history')"
      @keypress.c="copyInviteLink"
      @keyup.ctrl.j="stopDaily"
      ref="callContainer"
      tabindex="0"
      @mousemove="resetMouseTimer"
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
        <div class="videos-container">
          <WebRTC
            ref="webrtc"
            :roomId="room.room_id"
            :participants="room.participants"
            :userId="userId"
            :captionsEnabled="captionsEnabled"
            :showSingleCaption="
              'interface' in room.settings &&
              room.settings.interface.single_caption
            "
            :distortion="
              Object.keys(room.settings).length != 0 &&
              'interface' in room.settings &&
              room.settings.interface.audio.distortion
            "
            :togglePanel="() => $refs.panel.togglePanel(null, 'history')"
            :viewMode="viewMode"
            :mouseActive="mouseActive"
            :captionLanguage="captionLanguage"
            @changeLayout="recalculateLayout"
          />
          <div class="meeting-id-overlay">
            <b class="meeting-id" @click="copyInviteLink">
              <span>{{ $t("Room.meeting_id") }}{{ room.room_id }}</span>
              <span class="material-icons share-icon">share</span>
            </b>
          </div>
          <div class="video-gallery-bottom-bar">
            <div class="bottom-bar-icons">
              <span class="mic-settings">
                <ul class="choices" v-show="micSettingsVisible">
                  <li
                    v-for="mic in availableAudioInputs"
                    :key="mic.deviceId"
                    :class="{
                      selected: mic.deviceId === selectedAudioInput.deviceId,
                    }"
                    @click="updateMicrophone(mic)"
                  >
                    {{ mic.label }}
                  </li>
                </ul>
                <button
                  id="toggle-audio-share"
                  :class="{ active: !audioEnabled }"
                  @click="toggleAudio"
                  :enabled="!joining"
                  :title="$t('Room.mute')"
                >
                  <div class="icon-wrapper">
                    <span class="material-icons">{{
                      audioEnabled ? "mic" : "mic_off"
                    }}</span>
                  </div>
                </button>
                <button
                  class="mic-settings-notch"
                  @click="
                    micSettingsVisible = !micSettingsVisible;
                    cameraSettingsVisible = false;
                    languageSettingsVisible = false;
                  "
                >
                  <div class="icon-wrapper">
                    <span class="material-icons notch">{{
                      micSettingsVisible ? "expand_more" : "expand_less"
                    }}</span>
                  </div>
                </button>
              </span>
              <span class="cam-settings">
                <ul class="choices" v-show="cameraSettingsVisible">
                  <li
                    v-for="cam in availableVideoInputs"
                    :key="cam.deviceId"
                    :class="{
                      selected: cam.deviceId === selectedVideoInput.deviceId,
                    }"
                    @click="updateCamera(cam)"
                  >
                    {{ cam.label }}
                  </li>
                </ul>
                <button
                  id="toggle-video-share"
                  :class="{ active: !videoEnabled }"
                  @click="toggleVideo"
                  :enabled="!joining"
                  :title="$t('Room.video')"
                >
                  <div class="icon-wrapper">
                    <span class="material-icons">{{
                      videoEnabled ? "videocam" : "videocam_off"
                    }}</span>
                  </div>
                </button>
                <button
                  class="mic-settings-notch"
                  @click="
                    cameraSettingsVisible = !cameraSettingsVisible;
                    micSettingsVisible = false;
                    languageSettingsVisible = false;
                  "
                >
                  <div class="icon-wrapper">
                    <span class="material-icons notch">{{
                      cameraSettingsVisible ? "expand_more" : "expand_less"
                    }}</span>
                  </div>
                </button>
              </span>
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
                  <span class="material-icons">{{
                    sharingScreen ? "stop_screen_share" : "screen_share"
                  }}</span>
                </div>
              </button>
              <button
                id="settings"
                @click="captionsEnabled = !captionsEnabled"
                :title="$t('Room.toggle_captions')"
              >
                <div class="icon-wrapper">
                  <span class="material-icons">{{
                    captionsEnabled
                      ? "closed_caption"
                      : "closed_caption_disabled"
                  }}</span>
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
                    <select
                      v-model="spokenLanguage"
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
                  @click.stop="toggleLanguageSettings($event)"
                  :enabled="!joining"
                  :title="$t('Room.change_language')"
                >
                  <div class="icon-wrapper">
                    <span class="material-icons">translate</span>
                  </div>
                </button>
              </span>
              <button
                id="settings"
                @click="showRoomSettings(room)"
                :title="$t('Room.settings')"
              >
                <div class="icon-wrapper">
                  <span class="material-icons">settings</span>
                </div>
              </button>
              <div class="vertical-sep" />
              <button
                id="end-call"
                @click="onEndCallButton"
                :title="$t('Room.end_call')"
              >
                <div class="icon-wrapper">
                  <span class="material-icons">call_end</span>
                </div>
              </button>
            </div>
          </div>
        </div>
        <Panel
          :userId="userId"
          :language="captionLanguage"
          :roomId="room.room_id"
          @toggle="() => $nextTick(onLayoutChanged)"
          ref="panel"
        />
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
import Panel from "../components/Panel.vue";
import WordGuessingGame from "../components/WordGuessingGame.vue";
import RoomSettingsModal from "../components/RoomSettingsModal.vue";
import TranslateSelector from "../components/TranslateSelector.vue";
import throttle from "lodash/throttle";
import DailyIFrame from "@daily-co/daily-js";

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
      captionsEnabled: true,
      micSettingsVisible: false,
      cameraSettingsVisible: false,
      languageSettingsVisible: false,
      availableAudioInputs: [],
      availableVideoInputs: [],
      selectedAudioInput: {},
      selectedVideoInput: {},
      lastRoomUpdate: 0,
      room: {
        participants: [],
        settings: {},
      },
      sharingScreen: false,
      recordRTC: null,
      mouseActive: true,
      viewMode: "grid",
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
      this.redirectToSummary();
    });
    this.resetMouseTimer();
  },
  beforeRouteLeave: function (to, from, next) {
    // Unsubscribe from socket before leaving room, to not get errors
    this.sockets.unsubscribe("room");
    this.sockets.unsubscribe("reconnect");
    this.sockets.unsubscribe("leave-room");
    this.sockets.unsubscribe("/transcript");
    this.sockets.unsubscribe("/update-language");
    this.sockets.unsubscribe(`/${this.captionLanguage}/utterance`);
    this.sockets.unsubscribe(`/${this.captionLanguage}/translation`);
    this.sockets.unsubscribe(`/${this.captionLanguage}/complete-utterance`);
    this.sockets.unsubscribe("chatbot-audio");

    // Reset some variables
    this.$refs.panel.setHistory([], {});

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
          captionLanguages: [this.captionLanguage],
          userId: this.userId,
          roomId: this.room.room_id,
        },
        this.onJoined
      );
      this.$nextTick(() => {
        this.$refs.callContainer.focus();
      });
    },
    initializeRecordRTC() {
      if (this.recordRTC) {
        this.recordRTC.stopRecording();
      }
      const chunkSize = this.room.settings.st_services.asr.chunk_size;
      const sampleRate = this.room.settings.st_services.asr.sample_rate_hertz;
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

      if (!this.audioEnabled) {
        this.recordRTC.pauseRecording();
      }
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
        this.initializeRecordRTC();
        this.$refs.panel.setHistory(history, reactions);

        this.callObject.enumerateDevices().then((res) => {
          this.availableAudioInputs = res.devices.filter((device) => {
            return device.kind === "audioinput";
          });
          this.availableVideoInputs = res.devices.filter((device) => {
            return device.kind === "videoinput";
          });
        });
        this.callObject.getInputDevices().then((devices) => {
          this.selectedAudioInput = devices.mic;
          this.selectedVideoInput = devices.camera;
        });

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
          `/${this.captionLanguage}/utterance`,
          this.onUtterance
        );
        this.sockets.subscribe(
          `/${this.captionLanguage}/complete-utterance`,
          this.$refs.panel.onCompleteUtterance
        );

        // Call join on word-game, if necessary
        if (this.$refs.wordGame !== undefined) {
          this.$refs.wordGame.onJoined();
        }
        this.onLayoutChanged();
      }
    },
    suggestLanguage: throttle(
      function (detectedLanguage) {
        // Return a string concatenated in the current language and another language
        function bilingual(i18nKey, lang2, kwargs = {}) {
          return (
            this.$t(i18nKey, kwargs) + " / " + this.$t(i18nKey, lang2, kwargs)
          );
        }
        bilingual = bilingual.bind(this);

        this.$modal.show("dialog", {
          text: bilingual("Room.suggest_language_change", detectedLanguage, {
            language: this.$globals.displayLanguages[detectedLanguage],
          }),
          buttons: [
            {
              title: bilingual("General.no", detectedLanguage),
              handler: () => {
                this.$modal.hide("dialog");
              },
            },
            {
              title: bilingual("General.yes", detectedLanguage),
              handler: () => {
                this.spokenLanguage = detectedLanguage;
                this.captionLanguage = detectedLanguage;
                this.$modal.hide("dialog");
              },
            },
          ],
        });
        // Only show once every 10 seconds maximum
      },
      10000,
      { trailing: false }
    ),
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
      this.webrtc.onTranslation(msg);
    },
    onUtterance(msg) {
      this.webrtc.onUtterance(msg);
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
    redirectToSummary() {
      this.$router.push({
        name: "PostMeeting",
        params: { id: this.$route.params.id },
      });
    },
    onLayoutChanged: throttle(function () {
      this.recalculateLayout();
      this.$forceUpdate();
    }, 100),
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
          Array.from(
            this.$refs.gallery.getElementsByClassName("video-in-gallery")
          ).filter(
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
      if (this.recordRTC) {
        if (this.audioEnabled) {
          this.recordRTC.pauseRecording();
        } else {
          this.recordRTC.resumeRecording();
        }
      }
      this.audioEnabled = !this.audioEnabled;
      this.callObject.setLocalAudio(this.audioEnabled);
    },
    toggleVideo() {
      this.videoEnabled = !this.videoEnabled;
      this.callObject.setLocalVideo(this.videoEnabled);
    },
    closeLanguageSettingsIfNeeded(e) {
      if (e.target == window && this.languageSettingsVisible) {
        this.languageSettingsVisible = this.$refs.languageSettings.contains(
          e.target
        );
      }
    },
    toggleLanguageSettings(e) {
      this.languageSettingsVisible = !this.languageSettingsVisible;
      this.micSettingsVisible = false;
      this.cameraSettingsVisible = false;
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
      this.redirectToSummary();
      this.endCall();
    },
    showRoomSettings() {
      this.$modal.show(
        RoomSettingsModal,
        {
          room: this.room,
        },
        {
          height: 800,
          width: 1000,
        }
      );
    },
    copyInviteLink() {
      utils.copyToClipboard(this.inviteLink);
      Vue.$toast.success(this.$t("Room.success_copied_invite"));
    },
    updateMicrophone(mic) {
      this.callObject
        .setInputDevicesAsync({
          audioSource: mic.deviceId,
        })
        .then((deviceInfos) => {
          this.selectedAudioInput = deviceInfos.mic;

          // Reset audio track for recordRTC, any time set input devices is called
          this.localAudioTrack = this.callObject.participants().local.audioTrack;
          this.initializeRecordRTC();
        });
    },
    updateCamera(camera) {
      this.callObject
        .setInputDevicesAsync({
          videoSource: camera.deviceId,
        })
        .then((deviceInfos) => {
          this.selectedVideoInput = deviceInfos.camera;

          // Reset audio track for recordRTC, any time set input devices is called
          this.localAudioTrack = this.callObject.participants().local.audioTrack;
          this.initializeRecordRTC();
        });
    },
    resetMouseTimer() {
      if (this.mouseInactiveTimeout) {
        clearTimeout(this.mouseInactiveTimeout);
      }
      this.mouseActive = true;
      this.mouseInactiveTimeout = setTimeout(() => {
        this.mouseActive = false;
      }, 5000);
    },
    /*
    Secret method to stop using daily api minutes. For UI testing
    unrelated to video and chat things
    */
    stopDaily() {
      this.callObject.leave();
      this.sockets.unsubscribe("leave-room");
    },
  },
  components: {
    TranslateSelector,
    JoinRoom,
    Panel,
    WordGuessingGame,
    WebRTC,
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
          languages: [newLanguage],
        },
        () => {
          this.sockets.unsubscribe(`/${oldLanguage}/utterance`);
          this.sockets.unsubscribe(`/${oldLanguage}/translation`);
          this.sockets.unsubscribe(`/${oldLanguage}/complete-utterance`);
          this.sockets.subscribe(`/${newLanguage}/utterance`, this.onUtterance);
          this.sockets.subscribe(
            `/${newLanguage}/translation`,
            this.onTranslation
          );
          this.sockets.subscribe(
            `/${newLanguage}/complete-utterance`,
            this.$refs.panel.onCompleteUtterance
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

.video-gallery-bottom-bar,
.meeting-id-overlay,
.view-mode {
  opacity: 1;
  transition: opacity 0.25s ease-in-out;
}

.mouse-inactive {
  cursor: none;

  .video-gallery-bottom-bar,
  .meeting-id-overlay,
  .view-mode {
    opacity: 0;
  }
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
  padding: 3px 0;
  justify-content: center;
  position: absolute;
  bottom: 10px;

  .language-settings-container {
    position: relative;

    .language-settings {
      position: absolute;
      border: solid thin #797979;
      bottom: 69px;
      left: -50%;
      color: #eee;
      background: #666;
      border-radius: 2px;
      padding: 10px;
      width: 300px;
      left: -100px;

      label {
        margin-right: 5px;
      }

      .setting select {
        background-color: #666;
        border: solid thin #222;
        border-radius: 3px;
        color: #eee;
      }
    }
  }

  .bottom-bar-icons {
    display: flex;
    flex-direction: row;
    background: rgba(0, 0, 0, 0.3);
    padding: 5px 10px;
    border-radius: 15px;
    margin-bottom: 12px;
    border: solid thin #797979;

    button {
      margin: 0 3px;
      width: 60px;
      cursor: pointer;
      border: none;
      border-radius: 3px;
      background: transparent;
      color: white;

      &:hover {
        color: lightgray;
      }

      .icon-wrapper {
        .material-icons {
          font-size: 38px;
          padding-top: 11px;
          box-sizing: border-box;
          height: 60px;
        }
      }

      span {
        flex-grow: 1;
      }
    }
  }

  .mic-settings,
  .cam-settings {
    display: flex;
    position: relative;

    .choices {
      margin: 0;
      padding: 0;
      text-align: left;
      list-style-type: none;
      position: absolute;
      bottom: 69px;
      border: solid thin #797979;
      left: -50%;
      background: #666;
      color: #eee;
      user-select: none;
      cursor: pointer;

      li {
        padding: 5px 10px;

        &:hover {
          background-color: #444;
        }
      }

      .selected {
        font-weight: bold;
        background-color: #444;
      }
    }

    .mic-settings-notch {
      margin-left: -25px;
      width: 30px;

      .notch {
        font-size: 25px !important;
      }
    }
  }

  .bottom-bar-right-buttons {
    color: white;
    width: 15%;
    height: 100%;
    padding-right: 10px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    flex-wrap: wrap;
    align-items: flex-end;
    align-content: flex-end;

    .material-icons {
      align-self: flex-end;
      margin: 2px;
      display: inline-block;

      &:hover {
        color: lightgray;
      }
    }

    .compress-off-icon {
      background: linear-gradient(
        to top right,
        rgba(0, 0, 0, 0) 0%,
        rgba(0, 0, 0, 0) calc(50% - 1.8px),
        white 50%,
        rgba(0, 0, 0, 0) calc(50% + 1.8px),
        rgba(0, 0, 0, 0) 100%
      );

      &:hover {
        background: linear-gradient(
          to top right,
          rgba(0, 0, 0, 0) 0%,
          rgba(0, 0, 0, 0) calc(50% - 1.8px),
          lightgray 50%,
          rgba(0, 0, 0, 0) calc(50% + 1.8px),
          rgba(0, 0, 0, 0) 100%
        );
      }
    }
  }

  .vertical-sep {
    width: 1px;
    background: #797979;
    margin: 5px 15px 0 5px;
    height: 50px;
  }

  #end-call {
    background: #b71c1c;
    border-radius: 50%;

    .icon-wrapper {
      width: 100%;
    }
  }
}
ul {
  margin: 0;
}
.meeting-id-overlay {
  position: absolute;
  left: 15px;
  top: 10px;
  background-color: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 10px 15px;
  border-radius: 30px;
  border: solid thin #797979;

  .share-icon {
    margin-left: 7px;
    font-size: 16px;
  }

  .meeting-id {
    cursor: pointer;
    user-select: none;
    &:hover {
      color: lightgray;
    }
    span {
      vertical-align: middle;
    }
  }
}

.videos-container {
  display: flex;
  flex: 1 1;
  position: relative;
  overflow: hidden;
  justify-content: center;
}
</style>
