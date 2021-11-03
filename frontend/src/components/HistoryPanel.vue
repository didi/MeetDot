<template>
  <div v-if="active" class="inner-panel">
    <div class="history dark-scrollbar" ref="history">
      <div
        v-for="(utterance, i) in history"
        :key="utterance.text"
        class="history-line"
        @mouseenter="reactSelector = i"
        @mouseleave="reactSelector = null"
      >
        <div
          class="text-line"
          :class="utterance.speaker_id === userId ? 'me' : 'them'"
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
            <div class="message-text" v-html="utterance.html" />
          </div>
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
    <div class="text-input">
      <textarea
        @keypress.stop
        @keypress.enter.prevent="submitChat"
        v-model="chat"
      />
    </div>
  </div>
</template>

<script>
import backendService from "../service/index.js";
import utils from "../utils.js";
import SpeakerBubble from "./SpeakerBubble.vue";

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
  components: {
    SpeakerBubble,
  },
  data() {
    return {
      reactions: {},
      history: [], // contains all messages in all languages
      reactSelector: null,
      defaultReactions: ["👍", "👎", "🤣", "😢", "🐶", "❓"],
      chat: "",
    };
  },
  props: {
    active: Boolean,
    roomId: String,
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
  methods: {
    setHistory(history, reactions = {}) {
      this.history = history;
      this.history.forEach((message) => {
        message.reactions = reactions[message.message_id] || [];
      });
    },
    addReact(reaction, i) {
      const utterance = this.history[i];
      if (utterance.reactions[this.userId] == reaction) {
        reaction = null;
      }
      this.$set(utterance.reactions, this.userId, reaction);
      this.$socket.emit("reaction", {
        roomId: this.roomId,
        userId: this.userId,
        reaction,
        messageId: utterance.message_id,
      });
    },
    async onCompleteUtterance(msg) {
      // Inserts msg into this.history in time-sorted order.
      // Try inserting the message at the end first for O(1) complexity
      if (
        this.history.length === 0 ||
        this.history[this.history.length - 1].message_id < msg.message_id
      ) {
        this.history.push(msg);
      } else {
        // Otherwise, try from the end
        let inserted = false;
        for (let i = this.history.length - 1; i >= 0; i--) {
          const prevMsg = this.history[i];

          // Replace an old message
          if (
            prevMsg.message_id === msg.message_id &&
            prevMsg.speaker_id === msg.speaker_id
          ) {
            this.history[i] = msg;
            inserted = true;
            break;
          }

          // Otherwise splice it in
          else if (prevMsg.message_id < msg.message_id) {
            this.history.splice(i + 1, 0, msg);
            inserted = true;
            break;
          }
        }
        if (!inserted) {
          this.history.splice(0, 0, msg);
        }

        this.$forceUpdate();
      }

      await this.$nextTick();
      if (this.active && this.reactSelector === null) {
        this.$refs.history.scrollTop = this.$refs.history.scrollHeight;
      }
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
    download() {
      utils.downloadFile(
        backendService,
        `/download-history/${this.roomId}/${this.language}`
      );
    },
    getDisplayName: utils.getDisplayName,
    submitChat() {
      this.$socket.emit("chat", {
        roomId: this.roomId,
        userId: this.userId,
        text: this.chat,
        language: this.language, // currently set to captionLanguage
      });
      this.chat = "";
    },
  },
  watch: {
    async active(val) {
      if (val) {
        await this.$nextTick();
        this.$refs.history.scrollTop = this.$refs.history.scrollHeight;
      }
    },
    async language(new_lang) {
      const newHistory = await backendService().get(
        `/history/${this.roomId}/${new_lang}`
      );
      newHistory.data.forEach(this.onCompleteUtterance);
    },
  },
};
</script>

<style scoped lang="scss">
.inner-panel {
  display: flex;
  flex-direction: column;

  .history {
    overflow-y: auto;
    padding: 0 10px;

    flex: 1 1 auto;
  }
  .text-input {
    flex: 0 0 72px;

    textarea {
      width: 90%;
      background: black;
      border: solid thin #797979;
      color: white;
      font-size: 16px;
      font-family: inherit;
    }
  }
}

.history-line {
  text-align: left;
  padding: 5px;

  &:hover {
    background-color: #666;
  }

  .text-line {
    margin: 3px 0;
    display: flex;
  }

  .me {
    flex-direction: row-reverse;

    & .message {
      text-align: right;
    }
  }

  .them {
    flex-direction: row;
  }

  .message {
    padding: 0 10px 10px 10px;
    flex: 1;

    .message-text {
      overflow-wrap: anywhere;
    }

    .message-text::v-deep a {
      color: lightblue;
    }
  }

  .speaker-label {
    font-weight: bold;
    margin-bottom: 5px;
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
</style>
