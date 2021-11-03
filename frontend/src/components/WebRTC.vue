<!--
    WebRTC video calling implementation using daily.co APIs
-->

<template>
  <div class="videos">
    <Video
      class="video-in-gallery"
      v-show="viewMode === VIEW_MODES.GRID || video.id === focusedUser"
      v-for="video in videos"
      v-bind="video"
      :key="video.id"
      :lockable="viewMode === VIEW_MODES.GRID"
      :displayName="getDisplayNameFromId(video.id)"
      :muted="video.muted"
      :captionsEnabled="captionsEnabled && !showSingleCaption"
      :borderEnabled="captionsEnabled"
      ref="videos"
      @click.native.stop="focusVideo(video.id, true)"
      @translateScreenshot="translateScreenshot"
      @close="closeScreenshot"
    />

    <div class="small-videos-overlay" v-if="focusedUser !== null">
      <div v-show="smallVideosVisible">
        <div
          class="icon-wrapper"
          :class="{ visible: smallVideosStartIndex > 0 }"
          @click="smallVideosStartIndex--"
        >
          <span class="material-icons white contrast-icon">expand_less</span>
        </div>
        <Video
          class="small-video"
          v-for="videoId in smallVideos"
          v-bind="videos[videoId]"
          :focused="false"
          :key="videoId + '-small'"
          :displayName="getDisplayNameFromId(videoId)"
          :muted="videos[videoId].muted"
          :captionsEnabled="false"
          :borderEnabled="false"
          :lockable="true"
          @click.native.stop="focusVideo(videoId, true)"
          @translateScreenshot="translateScreenshot"
          @close="closeScreenshot"
          ref="smallVideos"
        />
        <div
          class="icon-wrapper"
          :class="{
            visible:
              unfocusedVideos.length >
              smallVideosStartIndex + smallVideosMaxLength,
          }"
          @click="smallVideosStartIndex++"
        >
          <span class="material-icons white contrast-icon">expand_more</span>
        </div>
      </div>
      <div
        class="toggle-videos"
        v-if="Object.keys(videos).length > 1"
        @click="smallVideosVisible = !smallVideosVisible"
      >
        <span class="material-icons white contrast-icon">{{
          smallVideosVisible ? "chevron_right" : "chevron_left"
        }}</span>
      </div>
    </div>

    <div
      class="captions"
      :class="{ 'captions--mouse-inactive': !mouseActive }"
      v-if="showSingleCaption"
      v-show="captionsEnabled && combinedSortedUtterances.length > 0"
    >
      <div class="captions-list dark-scrollbar">
        <div
          v-for="utterance in combinedSortedUtterances"
          :key="utterance.message_id"
          class="utterance"
        >
          <SpeakerBubble
            :speakerId="utterance.speaker_id"
            :speakerName="utterance.speaker_name"
          />
          <div class="message">
            <div class="speaker-label">
              {{
                getDisplayName(
                  utterance.speaker_name,
                  utterance.speaker_language
                )
              }}
            </div>
            <div class="message-text">
              {{ utterance.text }}
            </div>
          </div>
        </div>
        <div ref="captionEnd" />
      </div>
      <div class="caption-settings">
        <span @click="togglePanel" class="material-icons">chat</span>
      </div>
    </div>

    <div class="view-mode">
      <span
        class="material-icons"
        v-if="viewMode === VIEW_MODES.ACTIVE"
        @click="viewMode = VIEW_MODES.LOCKED"
      >
        lock_open
      </span>
      <span
        class="material-icons selected"
        v-if="viewMode === VIEW_MODES.LOCKED"
        @click="viewMode = VIEW_MODES.ACTIVE"
      >
        lock
      </span>
      <span
        @click="viewMode !== VIEW_MODES.GRID && unfocusVideo()"
        class="material-icons"
        :class="{ selected: viewMode === VIEW_MODES.GRID }"
        >grid_view</span
      >
      <span
        @click="viewMode === VIEW_MODES.GRID && focusVideo(undefined, false)"
        class="material-icons"
        :class="{ selected: viewMode !== VIEW_MODES.GRID }"
        >view_sidebar</span
      >
    </div>
  </div>
</template>

<script>
import throttle from "lodash/throttle";
import SpeakerBubble from "./SpeakerBubble.vue";
import Video from "./Video.vue";
import Vue from "vue";
import utils from "../utils.js";
import captioning from "../utils/captioning.js";
import backendService from "../service/index.js";
import SpeakerRingBuffer from "./SpeakerRingBuffer.js";
require("adapterjs");

const VIEW_MODES = { GRID: 0, ACTIVE: 1, LOCKED: 2 };
const SCREEN_SHARE_SUFFIX = "-screen-share";
const SCREENSHOT_SUFFIX = "-screenshot";

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
      utterances: {},
      smallVideosVisible: true,
      smallVideosStartIndex: 0,
      smallVideosMaxLength: 3,
      focusedUser: null,
      viewMode: VIEW_MODES.GRID,
      VIEW_MODES,
      translatedScreenshots: {},
      speakerBuffer: new SpeakerRingBuffer(8),
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
    participants: Array,
    distortion: Boolean,
    captionsEnabled: Boolean,
    showSingleCaption: Boolean,
    togglePanel: Function,
    mouseActive: Boolean,
    captionLanguage: String,
  },
  mounted() {
    this.addDistortionIfNecessary();
  },
  computed: {
    unfocusedVideos() {
      return Object.keys(this.videos).filter((k) => k !== this.focusedUser);
    },
    smallVideos() {
      if (this.focusedUser !== null) {
        return Object.keys(this.videos)
          .filter((k) => k !== this.focusedUser)
          .slice(
            this.smallVideosStartIndex,
            this.smallVideosStartIndex + this.smallVideosMaxLength
          );
      }
      return [];
    },
    videoLength() {
      return Object.keys(this.videos).length;
    },
    combinedSortedUtterances() {
      // List of utterances to be displayed
      let combinedUtterances = [];
      let sortedUtterances = Object.keys(this.utterances).sort((t1, t2) => {
        t1 = parseFloat(t1);
        t2 = parseFloat(t2);

        if (t1 == t2) {
          return 0;
        } else if (t1 > t2) {
          return 1;
        } else if (t1 < t2) {
          return -1;
        }
      });
      let lastUtterance = {};
      const sentenceSeparator = this.captionLanguage === "zh" ? "" : " ";
      for (let utteranceId of sortedUtterances) {
        const utterance = this.utterances[utteranceId];
        if (
          lastUtterance.speaker_id === utterance.speaker_id &&
          lastUtterance.speaker_language === utterance.speaker_language
        ) {
          // Combine consecutive utterances from the same speaker into one
          lastUtterance.text =
            lastUtterance.text + sentenceSeparator + utterance.text;
        } else {
          lastUtterance = JSON.parse(JSON.stringify(utterance));
          combinedUtterances.push(lastUtterance);
        }
      }
      return combinedUtterances;
    },
  },
  watch: {
    videoLength(newLength) {
      if (this.focusedUser === null) {
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
          rootId: id,
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
          isScreenShare: false,
        };
        if (this.isScreenShare(participant)) {
          id = participant.user_id + SCREEN_SHARE_SUFFIX;
          videos[id] = {
            id: id,
            rootId: participant.user_id,
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
            isScreenShare: true,
          };
          if (
            participant.user_id !== this.userId &&
            this.videos[id] === undefined
          ) {
            // Auto-focus screen sharing for other participants
            // TODO: localize toast message
            Vue.$toast.info(
              this.getDisplayNameFromId(participant.user_id) +
                " is sharing their screen"
            );
            this.focusVideo(participant.user_id + SCREEN_SHARE_SUFFIX, true);
          }
        }
      }
      if (videos[this.focusedUser] === undefined) {
        this.unfocusVideo();
      }
      this.updateScreenshotParticipants();
      this.videos = videos;
    },
    updateScreenshotParticipants() {
      for (const id in this.translatedScreenshots) {
        this.$set(this.videos, id + SCREENSHOT_SUFFIX, {
          id: id + SCREENSHOT_SUFFIX,
          rootId: id,
          isLocal: false,
          callItem: {
            staticImageURL: this.translatedScreenshots[id],
          },
          indexedTranslationLines: [],
          closable: true,
        });
      }
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

    /* For focused video, we have three modes:
      grid, active speaker and locked speaker view.
      This function sends us to either active speaker or locked speaker view.

      grid view. shows all videos in a grid.
      active speaker mode. shows the last person speaking
      locked speaker mode. always shows a certain person
    */
    focusVideo(userId = undefined, lock = false) {
      // If we're already focusing the correct user, do nothing
      if (this.focusedUser === userId && userId !== null) {
        return;
      }

      // If we're locked, do nothing. Also, if we lock a new video, we switch
      // the active speaker to the newly locked one.
      if (this.viewMode === VIEW_MODES.LOCKED && !lock) {
        return;
      }

      // If no other options, focus own video. TODO: Switch priority to any screenshares first
      this.focusedUser = userId || this.userId;

      this.$emit("changeLayout", 1);
      this.smallVideosVisible = true;
      this.viewMode = lock ? VIEW_MODES.LOCKED : VIEW_MODES.ACTIVE;
    },
    /* Implement smoothing for active speaker video */
    softFocusVideo(userId) {
      this.speakerBuffer.push(userId);
      const activeSpeaker = this.speakerBuffer.getActiveSpeaker();
      if (activeSpeaker !== null) {
        this.focusVideo(activeSpeaker);
      }
    },
    switchUser: throttle(
      function (userId) {
        this.focusedUser = userId;
      },
      2000,
      { trailing: false }
    ),
    unfocusVideo() {
      this.$emit("changeLayout", this.videoLength);
      this.focusedUser = null;
      this.viewMode = VIEW_MODES.GRID;
    },
    getDisplayName: utils.getDisplayName,
    getDisplayNameFromId(userId) {
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

      if (this.viewMode === VIEW_MODES.ACTIVE) {
        this.softFocusVideo(userId);
      }

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
    onTranslation(msg) {
      const userId = msg.speaker_id;
      const video = this.videos[userId];

      if (video === undefined) {
        return;
      }

      video.indexedTranslationLines = captioning.indexTranslationLines(
        msg.translation_lines,
        msg.highlight_boundaries,
        msg.line_index
      );

      // Also update the subtitles for a shared screen
      if (this.videos[userId + SCREEN_SHARE_SUFFIX] !== undefined) {
        this.videos[
          userId + SCREEN_SHARE_SUFFIX
        ].indexedTranslationLines = captioning.indexTranslationLines(
          msg.translation_lines,
          msg.highlight_boundaries,
          msg.line_index
        );
      }
    },
    onUtterance(utterance) {
      this.$set(this.utterances, utterance.message_id, utterance);
      // Scroll to bottom
      if (this.$refs.captionEnd !== undefined) {
        this.$refs.captionEnd.scrollIntoView({ behavior: "smooth" });
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
          addDistortion.call(this, this.videos[this.$refs.focusedUser]);
        }
      }
    },
    async translateScreenshot(imageData, id) {
      function dataURLtoFile(dataurl, filename) {
        var arr = dataurl.split(","),
          mime = arr[0].match(/:(.*?);/)[1],
          bstr = atob(arr[1]),
          n = bstr.length,
          u8arr = new Uint8Array(n);
        while (n--) {
          u8arr[n] = bstr.charCodeAt(n);
        }
        return new File([u8arr], filename, { type: "image/png" });
      }
      function fileToDataURL(blob) {
        return new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result);
          reader.onerror = reject;
          reader.readAsDataURL(blob);
        });
      }

      const imageFile = dataURLtoFile(imageData, "image.png");

      const fd = new FormData();
      fd.append("image", imageFile, "image.png");
      fd.append("userId", id);

      const participant = this.participants.find((p) => p.user_id === id);
      const blob = await backendService().put(
        `/image_translation/${this.roomId}/${participant.spoken_language}/${this.captionLanguage}`,
        fd,
        { headers: fd.getHeaders, responseType: "blob" }
      );
      const dataURL = await fileToDataURL(blob.data);
      this.translatedScreenshots[id] = dataURL;
      this.$set(this.translatedScreenshots, id, dataURL);
      this.updateScreenshotParticipants();
    },
    closeScreenshot(id) {
      this.$delete(this.translatedScreenshots, id);
      this.$delete(this.videos, id);
    },
  },
  components: {
    SpeakerBubble,
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
.videos {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  flex: 1 1 auto;
  align-items: center;
  overflow: hidden;
  position: relative;
  background: black;
}

.captions--mouse-inactive {
  bottom: 10px !important;
}

.captions {
  position: absolute;
  color: white;
  bottom: 100px;
  max-width: 800px;
  display: flex;
  flex-direction: row;
  width: 60%;
  background-color: rgba(0, 0, 0, 0.6);
  border-radius: 30px;
  border: solid thin #797979;
  padding: 10px 15px;
  transition: bottom 0.25s ease-in-out;

  .captions-list {
    overflow-y: auto;
    scrollbar-color: #666 #111;
    max-height: 200px;
    border-right: solid thin #797979;
    flex: 1;
  }

  .caption-settings {
    align-self: center;
    padding-left: 20px;
  }

  .utterance {
    margin: 3px 0;
    display: flex;
    flex-direction: row;
  }

  .message {
    padding: 0 10px 10px 10px;
    flex: 1;
    text-align: left;

    .message-text {
      overflow-wrap: anywhere;
    }
  }

  .speaker-label {
    font-weight: bold;
    margin-bottom: 5px;
  }
}

.small-videos-overlay {
  position: absolute;
  right: 20px;
  top: 100px;
  display: flex;
  height: calc(100vh - 100px);

  .visible {
    visibility: visible !important;
  }

  .icon-wrapper {
    padding: 10px;
    visibility: hidden;
  }

  .toggle-videos {
    align-self: center;
  }

  .material-icons {
    font-size: 36px;
  }

  .video-item {
    width: 320px;
    height: 180px;
    margin: 10px 0;
    border-radius: 20px;
    overflow: hidden;
  }
}

.view-mode {
  background-color: black;
  border-radius: 15px;
  border: solid thin #797979;
  position: absolute;
  top: 10px;
  right: 15px;
  color: #888;

  .material-icons {
    padding: 5px 10px;
    border-right: solid thin #797979;

    &:last-child {
      border-right: none;
    }
  }

  .selected {
    color: white;
    cursor: auto;
  }
}

.contrast-icon {
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.2);
}
</style>
