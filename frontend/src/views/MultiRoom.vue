<template>
  <div>
    <span class="settings">
      <div class="setting">
        <label for="spoken-language-dropdown" v-t="'Room.spoken_language'" />
        <select
          v-model="spokenLanguage"
          id="spoken-language-dropdown"
          @change="languageChanged"
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
        <label for="caption-language-dropdown" v-t="'Room.caption_language'" />
        <select
          v-model="captionLanguage"
          id="caption-language-dropdown"
          @change="languageChanged"
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
        <label for="audio-input-dropdown" v-t="'Live.audio_input'" />
        <select
          v-model="selectedInput"
          id="input-source-dropdown"
          @change="selectedInputChanged"
        >
          <option
            v-for="(choice, index) in inputChoices"
            :key="index"
            :value="index"
          >
            {{ choice }}
          </option>
        </select>
      </div>
      <div class="setting">
        <label for="wav_upload">Upload wav file(s)</label>
        <input
          type="file"
          multiple
          accept="audio/wav"
          ref="wav_upload"
          id="wav_upload"
          @change="handleWavUpload"
        />
      </div>
    </span>
    <button
      class="nice-button-big"
      id="toggle-second-window-button"
      @click="numRooms = numRooms === 1 ? 2 : 1"
    >
      Toggle Second Window
    </button>
    <div v-if="selectedInput !== 0">
      <button
        v-if="!audio || paused"
        class="nice-button-big"
        id="play-button"
        @click="playAudio"
      >
        {{ "PlayWavFile" }}
      </button>
      <button v-else class="nice-button-big" id="pause-button" @click="pause">
        Pause
      </button>
    </div>
    <div v-else>
      <button
        v-if="!stream || paused"
        class="nice-button-big"
        id="record-button"
        @click="recordMic"
      >
        {{ "StartRecording" }}
      </button>
      <button
        v-else
        class="nice-button-big"
        id="mic-pause-button"
        @click="pause"
      >
        Pause
      </button>
    </div>
    <div class="flex-container">
      <room
        v-for="i of Array(numRooms).keys()"
        v-bind:key="i"
        v-bind:spokenLanguage="spokenLanguage"
        v-bind:captionLanguage="captionLanguage"
        roomType="live"
        userIdPrefix="multi"
        ref="rooms"
      ></room>
    </div>
  </div>
</template>

<script>
import Room from "../components/CaptionedRoom.vue";
import RecordRTC from "recordrtc";

var timeSliceMs = 300; // milliseconds
// TODO change to timeSliceMs = (chunkSize / sampleRate) * 1000;
// chunkSize and sampleRate come from the ASR config.  However,
// the speech-translation rooms below that we're comparing may
// have different ASR configs.  So we'll need to think of a way
// to have a separate timeSliceMs parameter for each room, which
// means we'll need a separate stream recorder for each room.
// Currently both rooms share one recorder.

export default {
  name: "MultiRoom",
  components: {
    Room,
  },
  data() {
    return {
      sentHeader: false,
      spokenLanguage: this.$i18n.locale,
      captionLanguage: "zh",
      numRooms: 1,
      audio: null,
      recorder: null,
      stream: null,
      paused: false,
      inputChoices: ["mic"],
      selectedInput: 0, // stores the *index* of the selected element in inputChoices
      // the 0-index always points to "mic"
    };
  },
  methods: {
    reset() {
      this.sentHeader = false;
      this.audio = null;
      this.recorder = null;
      this.stream = null;
      this.paused = false;
      this.dataStreamed = 0;
    },
    async languageChanged() {
      if (this.recorder) {
        this.recorder.stopRecording();
      }
      if (this.stream) {
        this.stream.getAudioTracks()[0].stop();
      }
      let disconnect_promises = [];
      for (const i of Array(this.numRooms).keys()) {
        disconnect_promises.push(this.$refs.rooms[i].disconnectPromise());
      }
      await Promise.all(disconnect_promises);
      this.numRooms = 0; // This line is needed to gracefully reset the first room in a reactive way.
      this.numRooms = 1;
      this.reset();
    },
    handleWavUpload(e) {
      let input_choices = ["mic"];
      for (let f of e.target.files) {
        input_choices.push(f.name);
      }
      this.inputChoices = input_choices;
    },
    async selectedInputChanged() {
      if (this.audio) {
        this.audio.pause();
      }
      if (this.recorder) {
        this.recorder.stopRecording();
      }
      if (this.stream) {
        this.stream.getAudioTracks()[0].stop();
      }
      await this.resetTranslations();
      this.reset();
    },
    pause() {
      if (this.selectedInput !== 0 && this.audio) {
        this.audio.pause();
      }
      this.recorder.pauseRecording();
      this.paused = true;
    },
    async resume() {
      if (this.selectedInput !== 0) {
        await this.audio.play();
      }
      await this.recorder.resumeRecording();
      this.paused = false;
    },
    async resetTranslations() {
      let clear_translation_promises = [];
      for (const i of Array(this.numRooms).keys()) {
        clear_translation_promises.push(
          this.$refs.rooms[i].clearTranslations()
        );
      }
      await Promise.all(clear_translation_promises);
    },
    async recordMic() {
      if (this.paused) {
        await this.resume();
        return;
      }
      navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
        this.stream = stream;
        this.recorder = this.createRecorder(stream);
        this.dataStreamed = 0;
        this.recorder.startRecording();
      });
    },
    async playAudio() {
      if (this.paused) {
        await this.resume();
        return;
      }
      await this.resetTranslations();
      this.sentHeader = false;
      const wav_file = URL.createObjectURL(
        this.$refs.wav_upload.files[this.selectedInput - 1]
      );
      const audio = new Audio(wav_file);
      let stream = audio.captureStream();
      const recordRTC = this.createRecorder(stream);
      let that = this;
      audio.onended = function (event) {
        var recorder = that.recorder;
        var dataStreamed = that.dataStreamed;
        recorder.stopRecording(function () {
          let entire_blob = recorder.getBlob();
          let last_timeslice_blob = entire_blob.slice(
            dataStreamed,
            entire_blob.size,
            "audio/wav"
          );
          that.onAudioData(last_timeslice_blob);
        });

        that.reset();
      };
      that.dataStreamed = 0;
      audio
        .play()
        .then(() => recordRTC.startRecording())
        .then(() => {
          that.recorder = recordRTC;
          that.stream = stream;
          that.audio = audio;
        });
    },
    createRecorder(stream) {
      return RecordRTC(stream, {
        type: "audio",
        mimeType: "audio/wav",
        recorderType: RecordRTC.StereoAudioRecorder,
        bufferSize: 2048,
        desiredSampRate: 16000,
        numberOfAudioChannels: 1,
        timeSlice: timeSliceMs,
        ondataavailable: this.onAudioData,
        disableLogs: true,
      });
    },
    onAudioData: function (blob) {
      this.dataStreamed += blob.size;
      let end_utterance = false;
      if (
        this.selectedInput !== 0 &&
        (this.audio === null || this.audio === undefined || this.audio.ended)
      ) {
        end_utterance = true;
      }
      const reader = new FileReader();
      reader.onloadend = () => {
        let base64 = (/.+;\s*base64\s*,\s*(.+)$/i.exec(reader.result) || [])[1];
        if (this.sentHeader) {
          base64 = btoa(atob(base64).slice(this.$globals.wav_header_size));
        }
        for (const i of Array(this.numRooms).keys()) {
          let r = this.$refs.rooms[i];
          if (r.user_id && r.room) {
            this.$socket.emit("/audio/stream", {
              userId: r.user_id,
              roomId: r.room.room_id,
              data: base64,
              end_utterance: end_utterance,
            });
            this.sentHeader = true;
          }
        }
      };
      reader.readAsDataURL(blob);
    },
  },
};
</script>

<style scoped lang="scss">
.flex-container {
  display: flex;
}
.settings {
  font-size: 25px;
}
</style>
