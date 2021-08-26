<template>
  <div v-if="active" class="history-panel">
    <Close @click="toggleHistoryPanel(false)" />
    <FileDownload @click="downloadHistory" />
    <h3 class="history-header" v-t="'Room.history'"></h3>
    <div class="history" ref="history">
      <div
        v-for="(utterance, i) in history"
        :key="i"
        class="history-line"
        @mouseenter="reactSelector = i"
        @mouseleave="reactSelector = null"
      >
        <div class="text-line">
          <b>{{ utterance.speaker_name }}: </b>{{ utterance.text }}
        </div>
        <div class="reactions">
          <span
            :class="{
              'emoji-and-count': true,
              selected: utterance.reactions[userId] == emoji,
            }"
            v-for="{ emoji, count } in reactionCount(
              utterance.reactions || {},
              reactSelector == i
            )"
            @click="addReact(emoji, i)"
            :key="emoji"
            >{{ emoji }} {{ count }}</span
          >
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Close from "vue-material-design-icons/Close.vue";
import FileDownload from "vue-material-design-icons/FileDownload.vue";

// Analagous to collections.Counter, turn [a,b,a] into {a: 2, b: 1}
function counter(arr) {
  const result = {};
  arr.forEach((val) => {
    if (result[val] === undefined) {
      result[val] = 0;
    }
    result[val] += 1;
  });
  return result;
}

export default {
  name: "HistoryPanel",
  data() {
    return {
      active: false,
      reactions: {},
      history: [],
      reactSelector: null,
      defaultReactions: ["👍", "👎", "🤣", "😢", "🐶", "❓"],
    };
  },
  props: {
    userId: String,
    language: String,
  },
  mounted() {
    this.sockets.subscribe("reaction", (data) => {
      const message = this.history.find(
        (msg) => msg.message_id == data.messageId
      );
      if (message) {
        this.$set(message.reactions, data.userId, data.reaction);
      }
    });
  },
  unmounted() {
    this.sockets.unsubscribe("reaction");
  },
  components: {
    Close,
    FileDownload,
  },
  methods: {
    toggleHistoryPanel(val = null) {
      if (val == null) {
        this.active = !this.active;
      } else {
        this.active = !!val;
      }
      if (this.active) {
        // Scroll to the bottom on opened
        this.$nextTick(() => {
          this.$refs.history.scrollTop = this.$refs.history.scrollHeight;
        });
      }
      this.$emit("toggle");
    },
    set(history, reactions = {}) {
      this.history = this.collapseConsecutiveUtterances(history);
      this.history.forEach((message) => {
        message.reactions = reactions[message.message_id] || [];
      });
    },
    showReact(i) {
      this.reactSelector = i;
    },
    addReact(reaction, i) {
      const utterance = this.history[i];
      if (utterance.reactions[this.userId] == reaction) {
        reaction = null;
      }
      this.$set(utterance.reactions, this.userId, reaction);
      const roomId = this.$route.params.id;
      this.$socket.emit("reaction", {
        roomId,
        userId: this.userId,
        reaction,
        messageId: utterance.message_id,
      });
    },
    counter,
    collapseConsecutiveUtterances(history) {
      let collapsedHistory = [];
      for (let i = 0; i < history.length; i++) {
        const message = history[i];
        let lastMessage = collapsedHistory[collapsedHistory.length - 1];
        if (lastMessage && lastMessage.speaker_id === message.speaker_id) {
          lastMessage.text = this.joinUtterances(
            lastMessage.text,
            message.text
          );
        } else {
          collapsedHistory.push(message);
        }
      }
      return collapsedHistory;
    },
    joinUtterances(original, text) {
      const lastCharacter = original[original.length - 1];
      const delimiterToAdd = this.$globals.sentenceDelimiters[
        this.language
      ].includes(lastCharacter)
        ? ""
        : this.$globals.sentenceDelimiters[this.language][0];
      const spaceToAdd =
        !original.endsWith(" ") &&
        this.$globals.spaceBetweenSentences[this.language]
          ? " "
          : "";
      return original + delimiterToAdd + spaceToAdd + text;
    },
    onCompleteUtterance(msg) {
      // Search from the end for the right index to insert the utterance into.
      // It should be near the end.
      // Maintains a time-sorted order.
      let i = this.history.length - 1;
      for (; i >= 0; i--) {
        if (this.history[i].timestamp < msg.timestamp) {
          break;
        }
      }
      if (
        i >= 0 &&
        this.history[i].speaker_id == msg.speaker_id &&
        this.history[i].text.length < 300
      ) {
        // Collapse consecutive utterances from a speaker for easier to read display
        this.history[i].text = this.joinUtterances(
          this.history[i].text,
          msg.text
        );
      } else {
        this.history.splice(i + 1, 0, msg);
      }
      this.$nextTick(() => {
        if (this.active && this.reactSelector === null) {
          this.$refs.history.scrollTop = this.$refs.history.scrollHeight;
        }
      });

      // TODO: merge together consecutive utterances by the same speaker
    },
    reactionCount(reactions, showAll = false) {
      const count = counter(Object.values(reactions));
      return this.defaultReactions
        .map((emoji) => {
          if (!showAll && !count[emoji]) {
            return undefined;
          } else {
            return { emoji, count: count[emoji] || 0 };
          }
        })
        .filter((x) => x);
    },
    downloadHistory() {
      this.$emit("download");
    },
  },
};
</script>

<style scoped lang="scss">
.history-panel {
  box-sizing: border-box;
  background-color: lightgrey;
  position: relative;
  flex: 1 0 30%;
  display: flex;
  flex-direction: column;

  /* Mobile friendly layout */
  @media (max-width: 900px) {
    max-height: 300px;
    width: 100%;
  }

  @media (min-width: 900px) {
    border-left: 2px solid #666;
    min-width: 300px;
    max-width: 500px;
    height: 100%;
  }

  .material-design-icon {
    cursor: pointer;
  }

  .close-icon {
    position: absolute;
    left: 0;
    padding: 10px;
  }
  .file-download-icon {
    position: absolute;
    right: 0;
    padding: 10px 12px;
  }

  .history-header {
    padding-bottom: 7px;
    box-shadow: 0 8px 4px -4px #bbb;
  }

  .history {
    overflow-y: auto;
    padding-left: 15px;
  }
  .history-line {
    text-align: left;
    padding: 5px;

    &:hover {
      background-color: silver;
    }

    .text-line {
      margin: 3px 0;
    }

    .reactions {
      margin-right: 10px;

      .emoji-and-count {
        padding: 4px;
        margin-right: 4px;
        border: solid 1px #b8b8b8;
        border-radius: 5px;
        display: inline-block;
        cursor: pointer;

        &.selected {
          background-color: #bbd;
        }
      }
    }
    // Add a spacer to make the last message not jump around when adding a reaction
    &:last-child {
      min-height: 60px;
    }
  }
}
</style>
