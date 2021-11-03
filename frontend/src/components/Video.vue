<template>
  <div :class="['video-item', { 'my-video': isLocal }]">
    <video
      v-show="staticImageURL === null"
      autoplay
      muted
      playsinline
      disablePictureInPicture
      :id="id"
      ref="video"
    />
    <div v-if="videoTrack === null" class="bubble-container">
      <SpeakerBubble :speakerName="displayName" :speakerId="id" :size="50" />
    </div>
    <audio v-if="!isLocal" autoplay playsinline :id="id" ref="audio" />
    <img
      class="static-image"
      :src="staticImageURL"
      v-if="staticImageURL !== null"
    />
    <label class="video-label">
      {{ displayName }}
      <span class="material-icons muted-icon" v-if="muted === true"
        >mic_off</span
      >
    </label>
    <button
      class="translate-video material-icons"
      @click="translateScreenshot"
      v-if="isScreenShare && false"
    >
      translate
    </button>
    <button
      class="close material-icons"
      @click="$emit('close', id)"
      v-if="closable"
    >
      close
    </button>
    <div
      class="translation-lines"
      v-if="
        indexedTranslationLines.length &&
        !translationMinimized &&
        captionsEnabled
      "
    >
      <span
        class="material-icons expand-more-icon"
        @click.stop="translationMinimized = true"
        >expand_more</span
      >
      <AnimatedLines
        :indexedTranslationLines="indexedTranslationLines"
        ref="lines"
      />
    </div>
    <span
      class="material-icons expand-less-icon"
      v-if="translationMinimized"
      @click.stop="translationMinimized = false"
      >expand_less</span
    >
    <span class="material-icons-two-tone white lock-icon" v-if="lockable"
      >lock</span
    >
    <div
      :class="{
        'speaker-border': borderEnabled,
        'active-speaker-border': borderEnabled && isSpeaking,
      }"
    ></div>
  </div>
</template>

<script>
import AnimatedLines from "./AnimatedLines.vue";
import SpeakerBubble from "./SpeakerBubble.vue";
import Vue from "vue";

export default {
  name: "Video",
  data() {
    return {
      translationMinimized: false,
    };
  },
  props: {
    id: String,
    rootId: String,
    displayName: String,
    isLocal: Boolean,
    isSpeaking: Boolean,
    indexedTranslationLines: Array,
    callItem: Object,
    muted: Boolean,
    lockable: Boolean,
    captionsEnabled: Boolean,
    borderEnabled: Boolean,
    isScreenShare: Boolean,
    closable: Boolean,
  },
  computed: {
    videoTrack() {
      return this.callItem.videoTrackState &&
        this.callItem.videoTrackState.state === "playable"
        ? this.callItem.videoTrackState.track
        : null;
    },
    audioTrack() {
      return this.callItem.audioTrackState &&
        this.callItem.audioTrackState.state === "playable"
        ? this.callItem.audioTrackState.track
        : null;
    },
    staticImageURL() {
      return this.callItem.videoTrackState == null &&
        this.callItem.staticImageURL
        ? this.callItem.staticImageURL
        : null;
    },
  },
  mounted() {
    if (this.videoTrack !== null) {
      this.$refs.video.srcObject = new MediaStream([this.videoTrack]);
    }
    if (this.audioTrack !== null && !this.isLocal) {
      this.$refs.audio.srcObject = new MediaStream([this.audioTrack]);
    }
  },
  methods: {
    translateScreenshot() {
      // Get a screenshot
      let video = this.$refs.video;
      if (video !== null && !this.ctx) {
        let canvas = document.createElement("canvas");
        canvas.height = video.clientHeight;
        canvas.width = video.clientWidth;
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");
      }
      const { ctx, canvas } = this;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const data = canvas.toDataURL("image/png");

      this.$emit("translateScreenshot", data, this.rootId);
    },
  },
  watch: {
    videoTrack(newTrack, oldTrack) {
      if (newTrack != oldTrack && newTrack !== null) {
        this.$refs.video.srcObject = new MediaStream([newTrack]);
      }
    },
    audioTrack(newTrack, oldTrack) {
      if (newTrack != oldTrack && !this.isLocal && newTrack !== null) {
        this.$refs.audio.srcObject = new MediaStream([newTrack]);
      }
    },
    indexedTranslationLines() {
      this.$refs.lines && this.$refs.lines.$forceUpdate();
    },
  },
  components: {
    AnimatedLines,
    SpeakerBubble,
  },
};
</script>

<style scoped lang="scss">
video {
  height: 100%;
  width: 100%;
}
.bubble-container {
  position: absolute;
  height: 100%;
  width: 100%;
  top: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.video-item {
  width: var(--width);
  height: var(--height);
  background-color: black;
  position: relative;

  .translate-video,
  .close {
    position: absolute;
    top: 4px;
    left: 4px;
  }

  .lock-icon {
    font-size: 30px;
    position: absolute;
    top: calc(50% - 20px);
    right: 10px;
    display: none;
  }

  &:hover .lock-icon {
    display: initial;
  }

  .speaker-border {
    height: 100%;
    width: 100%;
    position: absolute;
    box-sizing: border-box;
    border: solid black 2px;
    top: 0;
    pointer-events: none;
  }

  .active-speaker-border {
    border: solid yellow 3px;
  }

  &.my-video {
    order: -1;
  }
}

.video-label {
  position: absolute;
  top: 0;
  right: 0;
  padding: 3px 10px;
  background-color: rgba(0, 0, 0, 0.6);
  border: solid thin #797979;
  text-align: left;
  box-sizing: border-box;
  color: white;
  margin: 8px;
  min-width: 120px;
  border-radius: 15px;
  font-weight: bold;
}

.translation-lines {
  --padding: 10px;
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  box-sizing: border-box;
  background-color: rgba(0, 0, 0, 0.7);
  color: #ddd;
  font-weight: bold;
  font-size: calc(var(--width) * 0.02);
  text-align: left;
  padding: var(--padding);

  &:empty {
    display: none;
  }
}

.expand-more-icon {
  position: absolute;
  right: 0;
  bottom: 0;
}
.expand-less-icon {
  position: absolute;
  bottom: 0;
  right: 0;
  background-color: rgba(0, 0, 0, 0.7);
  color: #ddd;
}

.muted-icon {
  color: red;
  vertical-align: bottom;
  font-size: 22px;
}
.static-image {
  width: 100%;
  height: 100%;
}
</style>
