<template>
  <div id="meeting-landing">
    <h2 class="room-header">
      {{ $t("JoinRoom.room_name") }} <b>{{ $route.params.id }}</b>
      <span class="material-icons room-settings" @click="showRoomSettings(room)"
        >settings</span
      >
    </h2>
    <div class="join-form">
      <div class="setting-group">
        <div class="setting">
          <label
            ref="userNameInput"
            for="user-name-input"
            v-t="'JoinRoom.your_name'"
          ></label>
          <input
            maxlength="25"
            v-model.trim="name"
            v-on:keyup.enter="joinIfPossible"
            id="user-name-input"
          />
        </div>
        <div class="setting">
          <label
            for="spoken-language-dropdown"
            v-t="'JoinRoom.spoken_language'"
          />
          <select
            v-model="spoken_language"
            @change="updateCaptionLanguage"
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
        <div class="setting captions">
          <div class="caption-label">
            <label
              for="caption-language-dropdown"
              v-t="'JoinRoom.caption_language'"
            />
          </div>
          <div class="caption-dropdown">
            <input
              v-model="languages_same"
              @change="updateCaptionLanguage"
              type="checkbox"
              id="same-checkbox"
            />
            <label
              class="no-select"
              for="same-checkbox"
              v-t="'JoinRoom.same_as_spoken'"
            />
            <div class="parent">
              <select
                :disabled="languages_same"
                v-model="caption_language"
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
        </div>
        <div class="setting">
          {{ $t("JoinRoom.currently_in_room") }}: {{ participantsList }}
        </div>
      </div>

      <div class="join-button-container">
        <button
          class="nice-button-big join-button"
          :disabled="!readyToJoin || joining"
          v-on:click="joinIfPossible"
        >
          {{ $t("JoinRoom.join_button") }}
          <span class="material-icons login-icon">login</span>
        </button>
      </div>
    </div>
    <p>
      {{ $t("Room.invite_link") }}:
      <b class="invite-link" @click="copyInviteLink">
        {{ inviteLink }} <span class="material-icons">content_copy</span>
      </b>
    </p>

    <div>
      <div class="setting"><h4 v-t="'JoinRoom.troubleshooting_title'" /></div>
      <ul>
        <li>
          {{ $t("JoinRoom.troubleshooting_bullets[0]") }}
        </li>
        <li>
          {{ $t("JoinRoom.troubleshooting_bullets[1]") }}
        </li>
        <li>
          {{ $t("JoinRoom.troubleshooting_bullets[2]") }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import Vue from "vue";
import utils from "../utils.js";
import RoomSettingsModal from "../components/RoomSettingsModal.vue";

export default {
  name: "JoinRoom",
  props: {
    room: Object,
    join: Function,
    joining: Boolean,
    showWordGame: Boolean,
  },
  computed: {
    participantsList: function () {
      if (this.room.participants.length === 0) {
        return "(empty)";
      } else {
        return this.room.participants
          .map(function (p) {
            return utils.getDisplayName(p.name, p.spoken_language);
          })
          .join(", ");
      }
    },
    readyToJoin: function () {
      return (
        0 < this.name.length &&
        this.name.length <= 30 &&
        !this.name.includes("/")
      );
    },
  },
  data() {
    return {
      inviteLink: window.location.href,
      name: "",
      spoken_language: this.$i18n.locale,
      caption_language: this.$i18n.locale,
      languages_same: true,
    };
  },
  methods: {
    updateCaptionLanguage() {
      if (this.languages_same) {
        this.caption_language = this.spoken_language;
      }
    },
    copyInviteLink() {
      utils.copyToClipboard(this.inviteLink);
      Vue.$toast.success(this.$t("JoinRoom.success_copied_invite"));
    },
    joinIfPossible: function () {
      if (this.readyToJoin) {
        this.join(this.name, this.spoken_language, this.caption_language);
      }
    },
    focusUserInput: function () {
      this.$refs.userNameInput.focus();
    },
    showRoomSettings() {
      this.$modal.show(
        RoomSettingsModal,
        {
          room: this.room,
        },
        {
          height: 600,
        }
      );
    },
  },
  watch: {
    caption_language(newLang) {
      this.$i18n.locale = newLang;
    },
  },
};
</script>
<style scoped lang="scss">
.room-header {
  margin: 15px auto;
  font-weight: normal;
}
h4 {
  margin-bottom: 10px;
}

label {
  margin-right: 10px;
}

#meeting-landing {
  max-width: 650px;
  padding: 0 10px;
  margin: 0 auto;
  padding-top: 45px;
  text-align: left;
  font-size: 20px;

  .setting {
    margin-bottom: 10px;

    input,
    select {
      font-size: 18px;
    }
  }
}
.join-form {
  display: flex;
  flex-direction: row;
  border-bottom: solid thin;
}
.join-button-container {
  width: 30%;
  display: flex;
  align-items: center;
}
.join-button {
  margin-left: auto;
}
.content-copy-icon {
  margin-left: 10px;
}
.room-settings {
  float: right;
}
.setting-group {
  width: 70%;
}
.material-icons {
  vertical-align: bottom;
}
.no-select {
  user-select: none;
  padding-left: 3px;
  margin-bottom: 10px;
}
.captions {
  display: flex;
}
#caption-language-dropdown {
  margin-top: 5px;
  transition: color ease-in-out 0.1s;
}
</style>
