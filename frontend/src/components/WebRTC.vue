<!--
    WebRTC video calling implementation using daily.co APIs
-->

<template>
  <div class="videos">
    <Video
      class="focused-video"
      v-if="focusedVideo !== null"
      v-bind="videos[focusedVideo]"
      :focused="true"
      :displayName="getDisplayName(focusedVideo)"
      :muted="videos[focusedVideo].muted"
      :key="focusedVideo + 'focus'"
      ref="focusedVideo"
      @click.native.stop="unfocusVideo"
    />
    <span
      v-if="focusedVideo !== null"
      class="material-icons exit-focus"
      @click="unfocusVideo"
    >
      close_fullscreen
    </span>

    <Video
      class="video-in-gallery"
      v-show="focusedVideo === null"
      v-for="video in videos"
      v-bind="video"
      :focused="false"
      :key="video.id"
      :displayName="getDisplayName(video.id)"
      :muted="video.muted"
      ref="videos"
      @click.native.stop="focusVideo(video.id)"
    />
  </div>
</template>

<script>
import Video from "./Video.vue";
import Vue from "vue";
require("adapterjs");

const SCREEN_SHARE_SUFFIX = "-screen-share";

function addDistortion(videoElement) {
  if (this.audioContext === null) {
    this.audioContext = new AudioContext();

    // One second of white noise
    this.whiteNoiseBuffer = new AudioBuffer({
      numberOfChannels: 1,
      sampleRate: this.audioContext.sampleRate,
      length: this.audioContext.sampleRate,
    });
  }

  // Fill the buffer with white noise;
  // just random values between -1.0 and 1.0
  for (
    var channel = 0;
    channel < this.whiteNoiseBuffer.numberOfChannels;
    channel++
  ) {
    var nowBuffering = this.whiteNoiseBuffer.getChannelData(channel);
    for (var i = 0; i < this.whiteNoiseBuffer.length; i++) {
      nowBuffering[i] = Math.random() * 2 - 1;
    }
  }
  if (videoElement.muted) {
    return;
  }

  if (videoElement.srcObject === null) {
    // Try again in another half-second if video is not yet loaded
    setTimeout(() => addDistortion.call(this, videoElement), 500);
    return;
  }
  if (videoElement.srcObject.getAudioTracks().length === 0) {
    return;
  }
  const source = new MediaStreamAudioSourceNode(this.audioContext, {
    mediaStream: videoElement.srcObject,
  });

  var convolver = new ConvolverNode(this.audioContext, {
    buffer: this.whiteNoiseBuffer,
  });

  var lowpass = new BiquadFilterNode(this.audioContext, {
    type: "lowpass",
    frequency: 100,
  });

  var highshelf = new BiquadFilterNode(this.audioContext, {
    type: "highshelf",
    frequency: 100,
    gain: -20,
  });

  var gain = new GainNode(this.audioContext, {
    gain: 80,
  });

  source
    .connect(convolver)
    .connect(gain)
    .connect(highshelf)
    .connect(lowpass)
    .connect(this.audioContext.destination);

  videoElement.muted = true;
}

var WebRTC = {
  name: "WebRTC",
  data() {
    return {
      audioContext: null,
      whiteNoiseBuffer: null,
      videos: {},
      canvas: null,
      focusedVideo: null,
    };
  },
  props: {
    userId: {
      type: String,
    },
    roomId: {
      type: String,
      default: "public-room",
    },
    autoplay: {
      type: Boolean,
      default: true,
    },
    screenshotFormat: {
      type: String,
      default: "image/jpeg",
    },
    participants: Array,
    distortion: Boolean,
  },
  mounted() {
    this.addDistortionIfNecessary();
  },
  computed: {
    videoLength() {
      return Object.keys(this.videos).length;
    },
  },
  watch: {
    videoLength(newLength) {
      if (this.focusedVideo === null) {
        this.$emit("changeLayout", newLength);
      }
    },
  },
  methods: {
    updateCallItems(dailyParticipants) {
      let videos = {};
      const chatbotId = "chatbot";
      let chatbotParticipant = this.participants.find(
        (p) => p.user_id == chatbotId
      );
      if (chatbotParticipant) {
        // Special case of video for the chatbot
        videos[chatbotId] = {
          id: chatbotId,
          isLocal: false,
          callItem: {
            videoTrackState: null,
            audioTrackState: null,
            staticImageURL:
              "https://cdn.pixabay.com/photo/2019/03/21/15/51/chatbot-4071274_1280.jpg",
          },
          muted: false,
          isSpeaking: this.videos[chatbotId]
            ? this.videos[chatbotId].isSpeaking
            : false,
          indexedTranslationLines: this.videos[chatbotId]
            ? this.videos[chatbotId].indexedTranslationLines
            : [],
          transcript: this.videos[chatbotId]
            ? this.videos[chatbotId].transcript
            : "",
        };
      }
      for (const participant of Object.values(dailyParticipants)) {
        let id = participant.user_id;
        videos[id] = {
          id: id,
          isLocal: participant.local,
          callItem: {
            videoTrackState: participant.tracks.video,
            audioTrackState: participant.tracks.audio,
          },
          muted: !participant.audio,
          isSpeaking: this.videos[id] ? this.videos[id].isSpeaking : false,
          indexedTranslationLines: this.videos[id]
            ? this.videos[id].indexedTranslationLines
            : [],
          transcript: this.videos[id] ? this.videos[id].transcript : "",
        };
        if (this.isScreenShare(participant)) {
          id = participant.user_id + SCREEN_SHARE_SUFFIX;
          videos[id] = {
            id: id,
            isLocal: participant.local,
            callItem: {
              videoTrackState: participant.tracks.screenVideo,
              audioTrackState: participant.tracks.screenAudio,
            },
            muted: !participant.audio,
            isSpeaking: this.videos[id] ? this.videos[id].isSpeaking : false,
            indexedTranslationLines: this.videos[id]
              ? this.videos[id].indexedTranslationLines
              : [],
            transcript: this.videos[id] ? this.videos[id].transcript : "",
          };
          if (
            participant.user_id !== this.userId &&
            this.videos[id] === undefined
          ) {
            // Auto-focus screen sharing for other participants
            // TODO: localize toast message
            Vue.$toast.info(
              this.getDisplayName(participant.user_id) +
                " is sharing their screen"
            );
            this.focusVideo(participant.user_id + SCREEN_SHARE_SUFFIX);
          }
        }
      }
      if (videos[this.focusedVideo] === undefined) {
        this.unfocusVideo();
      }

      this.videos = videos;
    },
    isScreenShare(participant) {
      const trackStatesForInclusion = ["loading", "playable", "interrupted"];
      return (
        trackStatesForInclusion.includes(
          participant.tracks.screenVideo.state
        ) ||
        trackStatesForInclusion.includes(participant.tracks.screenAudio.state)
      );
    },
    focusVideo(userId) {
      this.$emit("changeLayout", 1);
      this.focusedVideo = userId;
    },
    unfocusVideo() {
      this.$emit("changeLayout", this.videoLength);
      this.focusedVideo = null;
    },
    getDisplayName(userId) {
      let participant = this.participants.find((p) => p.user_id == userId);
      if (participant !== undefined) {
        return (
          participant.name +
          " (" +
          this.$globals.displayLanguages[participant.spoken_language] +
          ")"
        );
      } else if (userId.endsWith(SCREEN_SHARE_SUFFIX)) {
        // Screen share - put appropriate name
        participant = this.participants.find(
          (p) => p.user_id + SCREEN_SHARE_SUFFIX == userId
        );
        if (participant !== undefined) {
          return participant.name + " (screen share)";
        } else {
          return "";
        }
      } else {
        return "";
      }
    },
    receivedTranscript(userId, transcript) {
      const video = this.videos[userId];

      if (video === undefined) {
        return;
      }
      // Set active speaker box, that fades out after no new ASR has been received for a certain amount of time
      this.$set(video, "isSpeaking", true);
      this.$set(video, "transcript", transcript);

      setTimeout(() => {
        if (video.transcript === transcript) {
          if (this.videos[userId] !== undefined) {
            this.$set(this.videos[userId], "isSpeaking", false);
          }
        }
      }, 2000);
    },
    setTranslation(userId, translationLines, lineIndex, highlightBoundaries) {
      const video = this.videos[userId];

      if (video === undefined) {
        return;
      }

      const indexedTranslationLines = [];
      for (let i = 0; i < translationLines.length; i++) {
        let text = translationLines[i];
        let highlightedText = "";

        if (highlightBoundaries) {
          if (highlightBoundaries[i] >= 0) {
            // highlight (fade out) the from hb[i] to the end characters
            // OR 0, which means highlight everything
            highlightedText = text.slice(highlightBoundaries[i]);
            text = text.slice(0, highlightBoundaries[i]);
          } // otherwise, -1, highlight nothing
        }

        indexedTranslationLines.push({
          index: lineIndex + i,
          text,
          highlightedText,
        });
      }
      this.$set(video, "indexedTranslationLines", indexedTranslationLines);

      // Also update the subtitles for a shared screen
      if (this.videos[userId + SCREEN_SHARE_SUFFIX] !== undefined) {
        this.$set(
          this.videos[userId + SCREEN_SHARE_SUFFIX],
          "indexedTranslationLines",
          indexedTranslationLines
        );
      }
    },
    receivedChatbotAudio(audio) {
      let audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      let source = audioCtx.createBufferSource();
      audioCtx.decodeAudioData(audio, function (buffer) {
        source.buffer = buffer;
        source.connect(audioCtx.destination);
        source.start();
      });
    },
    addDistortionIfNecessary() {
      if (this.distortion) {
        if (this.$refs.videos) {
          this.$refs.videos.forEach(addDistortion.bind(this));
        } else {
          addDistortion.call(this, this.videos[this.$refs.focusedVideo]);
        }
      }
    },
  },
  components: {
    Video,
  },
};
var install = function (Vue) {
  Vue.component(WebRTC.name, WebRTC);
};
WebRTC.install = install;

export default WebRTC;
</script>

<style scoped lang="scss">
.focused-video {
  background-color: white;
}

.exit-focus {
  position: absolute;
  right: 0;
  padding: 10px;
  font-size: 40px;
}

.videos {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  flex: 1 1 auto;
  align-items: center;
  overflow: hidden;
  position: relative;
}
</style>
