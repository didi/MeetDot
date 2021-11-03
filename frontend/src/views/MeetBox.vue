<template>
  <div id="meetbox-page">
    <div
      v-for="captionLang in captionLanguages"
      :key="captionLang"
      class="caption-group"
    >
      <div
        v-for="spokenLang in spokenLanguages"
        :key="spokenLang"
        class="caption-container"
      >
        {{ spokenLang }} → {{ captionLang }}
        <AnimatedLines
          class="captions"
          :indexedTranslationLines="
            indexedTranslationLines[captionLang][spokenLang]
          "
        />
      </div>
    </div>
  </div>
</template>

<script>
import Vue from "vue";
import AnimatedLines from "../components/AnimatedLines.vue";
import RecordRTC from "recordrtc";
import captioning from "../utils/captioning.js";
import utils from "../utils.js";
import backendService from "../service/index.js";

export default {
  name: "MeetBox",
  data() {
    const captionLanguages = ["en-US", "zh"];
    const spokenLanguages = ["en-US", "zh"];
    // 2d object. accessed with: tl[captionLanguage][originalLanguage]
    const indexedTranslationLines = {};
    for (const i of captionLanguages) {
      indexedTranslationLines[i] = {};
      for (const j of spokenLanguages) {
        indexedTranslationLines[i][j] = [];
      }
    }

    return {
      spokenLanguages,
      captionLanguages,
      indexedTranslationLines,
      userId: "meetbox-" + utils.randomString(8),
    };
  },
  async mounted() {
    this.captions = this.$refs.captions;
    const roomId = utils.createRoomId();
    const that = this;

    // Create backend room
    var languages_to_providers = {};
    for (var spoken_language in this.spokenLanguages) {
      languages_to_providers[spoken_language] = "wenet";
    }

    await backendService().post(
      "/rooms",
      JSON.stringify({
        roomId,
        roomType: "live",
        settings: {
          services: {
            asr: {
              middleware_provider: "basic",
              providers: languages_to_providers,
              language_id: { enabled: false },
            },
            post_translation: { add_punctuation: false },
            captioning: { num_lines: 5 },
          },
        },
      }),
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
    this.$socket.emit("on-page", "room/" + roomId);
    const response = await backendService().get("/rooms/" + roomId);

    const room = response.data.room;
    if (room !== null) {
      that.room = room;
      that.join();
    } else {
      // Redirect if room does not exist
      Vue.$toast.info(this.$t("Room.error_does_not_exist", { roomId }));
    }

    this.sockets.subscribe("reconnect", () => {
      this.$socket.emit("/rejoin", {
        userId: this.userId,
        roomId: roomId,
      });
    });
    this.sockets.subscribe("leave-room", (message) => {
      Vue.$toast.info(message);
    });
  },
  methods: {
    join() {
      this.$socket.emit(
        "/join",
        {
          spokenLanguage: "en-US", // TODO: change me to none when merging with multiple ASR language change
          captionLanguages: this.captionLanguages,
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

        this.captionLanguages.forEach((lang) => {
          this.sockets.subscribe(`/${lang}/translation`, (msg) =>
            this.onTranslation(msg, lang)
          );
        });
      }
    },
    gotDevices(deviceInfos) {
      this.audioInputs = deviceInfos.filter(
        (info) => info.kind === "audioinput"
      );

      if (this.audioInputs.length === 0) {
        Vue.$toast.error("No audio inputs found. Please plug in a microphone");
      }

      // Microphones aren't named at first. Reload until they are
      const interval = setInterval(() => {
        const targetMicrophones = [
          "OSM09 Analog Mono",
          "USB PnP Audio Device Analog Mono",
        ];
        const usbMicrophone = this.audioInputs.find((info) =>
          targetMicrophones.includes(info.label)
        );
        if (usbMicrophone !== undefined) {
          this.audioInputChanged(this.audioInput, {
            target: { value: usbMicrophone.deviceId },
          });
          clearInterval(interval);
        }
      }, 1000);
    },
    onTranslation(msg, captionLang) {
      const newLines = captioning.indexTranslationLines(
        msg.translation_lines,
        msg.highlight_boundaries,
        msg.line_index
      );
      this.$set(
        this.indexedTranslationLines[captionLang],
        msg.original_language,
        newLines
      );
    },
    onAudioData(blob) {
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
    failureCallback(error) {
      Vue.$toast.error(this.$t("Room.error_user_media"));
      this.$socket.emit("disconnect-user", { userId: this.userId });
    },
    successCallback(stream) {
      const chunkSize = this.room.settings.st_services.asr.chunk_size;
      const sampleRate = this.room.settings.st_services.asr.sample_rate_hertz;
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
    },
    beforeRouteLeave: function (to, from, next) {
      // Unsubscribe from socket before leaving room, to not get errors
      this.sockets.unsubscribe("reconnect");
      this.sockets.unsubscribe("leave-room");
      this.sockets.unsubscribe("/update-language");
      this.sockets.unsubscribe(`/${this.captionLanguage}/translation`);
      next();
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
  },
  components: {
    AnimatedLines,
  },
};
</script>

<style scoped lang="scss">
#meetbox-page {
  background-color: #222;
  height: 100%;

  display: flex;
  flex-direction: column;
}

.caption-group {
  border-bottom: solid 1px #bbb;
  margin: 10px;
  color: #bbb;

  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  align-items: center;

  .caption-container {
    flex: 1 1 0;
    width: 1000px;

    .captions {
      font-size: 24px;
      font-weight: bold;
      text-align: left;
    }
  }
}
</style>
