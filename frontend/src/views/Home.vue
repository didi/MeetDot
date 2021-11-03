<template>
  <div
    class="home-page"
    @keypress.m="createDefault"
    @keypress.g="createGame"
    @keypress.l="createTranscription"
    tabindex="0"
    ref="home"
  >
    <TranslateSelector />
    <div id="header">
      <img id="logo" src="meetdot-logo.svg" />
      <h1 v-t="'Home.title'"></h1>
    </div>
    <div class="button-container">
      <button
        class="nice-button-big"
        id="new-meeting-button"
        :disabled="!canCreate"
        @click="createDefault"
        v-t="'Home.new_meeting_button'"
      ></button>
      <button
        class="nice-button-big"
        id="new-meeting-button"
        :disabled="!canCreate"
        @click="createGame"
        v-t="'Home.new_game_button'"
      ></button>
      <button
        class="nice-button-big"
        id="new-meeting-button"
        :disabled="!canCreate"
        @click="createTranscription"
        v-t="'Home.live_translation_button'"
      ></button>
    </div>
    <img id="demo-img" src="../../public/demo-img.png" />
    <div id="instructions">
      <p v-t="'Home.beta_warning'"></p>
      <ul>
        <li>
          {{ $t("Home.instructions[0]") }}
        </li>
        <li>
          {{ $t("Home.instructions[1]") }}
        </li>
        <li>
          {{ $t("Home.instructions[2]") }}
        </li>
      </ul>
      <p v-if="$i18n.locale == 'pt-BR'">
        <i>{{ $t("Home.translation_help") }}</i>
      </p>
    </div>
</template>

<script>
import Vue from "vue";
import backendService from "../service/index.js";
import utils from "../utils.js";
import TranslateSelector from "../components/TranslateSelector.vue";

export default {
  name: "Home",
  components: {
    TranslateSelector,
  },
  data() {
    return {
      canCreate: true,
    };
  },
  methods: {
    create(settings, roomType = "meeting", nextPage = "Room") {
      if (!this.canCreate) {
        Vue.$toast.error(
          "Cannot create a new room. Creation already in progress"
        );
        return;
      }

      let that = this;
      this.canCreate = false;
      let roomId = utils.createRoomId();
      backendService()
        .post(
          "/rooms",
          JSON.stringify({
            roomId: roomId,
            roomType: roomType,
            settings,
          }),
          {
            headers: {
              "Content-Type": "application/json",
            },
          }
        )
        .then((response) => {
          that.canCreate = true;
          if (response.data.success) {
            that.$router.push({
              name: nextPage,
              params: { id: roomId },
            });
          }
        })
        .catch((err) => {
          that.canCreate = true;
          Vue.$toast.error(
            "Could not create meeting: " + err.response
              ? err.response.data.description
              : err
          );
        });
    },
    createGame() {
      this.create(
        {
          services: {
            post_translation: {
              mask_k: 0,
            },
          },
          interface: {
            games: {
              word_guessing: true,
            },
          },
        },
        "meeting"
      );
    },
    createTranscription() {
      this.$router.push("/live");
    },
    createDefault() {
      this.create({});
    },
  },
  mounted() {
    this.$socket.emit("on-page", "home");
    this.$refs.home.focus();
  },
};
</script>

<style>
body {
  height: 100vh;
}
</style>

<style scoped lang="scss">
.home-page {
  height: 100%;
  overflow: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 10px;
}

#header {
  align-items: center;
  display: flex;
}
#logo {
  height: 50px;
  margin-right: 10px;
}

#demo-img {
  max-height: 40%;
  max-width: 95%;
  display: block;
  margin: 30px auto 30px auto;
}

#instructions {
  max-width: 700px;
  line-height: 1.7;
  text-align: left;
}

#credits {
  margin-top: auto;
  text-align: center;
}
</style>
