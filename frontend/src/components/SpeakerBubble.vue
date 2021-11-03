<template>
  <div class="user-name-bubble" :class="getColor(speakerId)">
    {{ firstLetter }}
  </div>
</template>

<script>
export default {
  name: "SpeakerBubble",
  props: {
    speakerName: String,
    speakerId: String,
    size: Number,
  },
  mounted() {
    this.$el.style.setProperty("--bubble-size", (this.size || 30) + "px");
  },
  methods: {
    getColor(speakerId) {
      // Get a hash from the speaker ID
      let hash = 0;
      for (let i = 0; i < speakerId.length; i++) {
        let character = speakerId.charCodeAt(i);
        hash = (hash << 5) - hash + character;
        hash = hash & hash; // Convert to 32bit integer
      }

      const colors = [
        "blue",
        "orange",
        "green",
        "pink",
        "red",
        "purple",
        "brown",
        "yellow",
      ];

      return colors[Math.abs(hash) % colors.length];
    },
  },
  computed: {
    firstLetter() {
      return this.speakerName[0] ? this.speakerName[0].toUpperCase() : "?";
    },
  },
};
</script>

<style scoped lang="scss">
.user-name-bubble {
  --bubble-size: 20px;

  color: white;
  user-select: none;
  flex: 0 0 var(--bubble-size);
  height: var(--bubble-size);
  font-size: calc(var(--bubble-size) / 2 + 8px);
  text-align: center;
  line-height: var(--bubble-size);
  border-radius: 50%;
  padding: 10px;
}
// Background colors for different user bubble colors
.blue {
  background-color: #219ebc;
}

.orange {
  background-color: #fb8500;
}

.green {
  background-color: #40916c;
}

.pink {
  background-color: #f72585;
}

.red {
  background-color: #d00000;
}

.purple {
  background-color: #7209b7;
}

.brown {
  background-color: #7f4f24;
}

.yellow {
  background-color: #fdc500;
}
</style>
