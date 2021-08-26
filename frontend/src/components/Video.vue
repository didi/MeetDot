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
    <div
      class="translation-lines"
      v-if="indexedTranslationLines.length && !translationMinimized"
    >
      <span
        class="material-icons expand-more-icon"
        @click.stop="translationMinimized = true"
        >expand_more</span
      >
      <transition-group tag="div" class="captions" name="captions">
        <div
          class="translation-line"
          v-for="line in indexedTranslationLines"
          :key="line.index"
        >
          <span v-if="line.text.length">{{ line.text }}</span>
          <span class="highlighted" v-if="line.highlightedText.length">{{
            line.highlightedText
          }}</span>
        </div>
      </transition-group>
    </div>
    <span
      class="material-icons expand-less-icon"
      v-if="translationMinimized"
      @click.stop="translationMinimized = false"
      >expand_less</span
    >
    <span class="material-icons enter-focus" v-if="!focused">open_in_full</span>
    <div
      :class="{ 'speaker-border': true, 'active-speaker-border': isSpeaking }"
    ></div>
  </div>
</template>

<script>
import "vue-material-design-icons/styles.css";

export default {
  name: "Video",
  data() {
    return {
      translationMinimized: false,
    };
  },
  props: {
    id: String,
    displayName: String,
    isLocal: Boolean,
    isSpeaking: Boolean,
    indexedTranslationLines: Array,
    callItem: Object,
    focused: Boolean,
    muted: Boolean,
    transcript: String, // for computing active speaker
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
  },
};
</script>

<style scoped lang="scss">
video {
  height: 100%;
  width: 100%;
}

.video-item {
  width: var(--width);
  height: var(--height);
  background-color: #aaaaaa;
  position: relative;

  .enter-focus {
    font-size: 40px;
    position: absolute;
    top: calc(50% - 20px);
    right: 10px;
    display: none;
  }

  &:hover .enter-focus {
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
  background: rgba(40, 40, 40, 0.8);
  text-align: left;
  box-sizing: border-box;
  color: white;
  margin: 8px;
  min-width: 120px;
  border-radius: 10px;
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

  .highlighted {
    font-weight: 600;
    color: #888;
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

.captions-move {
  transition: transform 0.5s;
}
.captions-enter {
  opacity: 0.5;
}
.captions-enter-active {
  transition: opacity 0.25s ease-in-out;
}
.captions-leave-active {
  position: absolute;
  transition: opacity 0.25s ease-in-out;
}
.captions-leave-to {
  opacity: 0;
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
