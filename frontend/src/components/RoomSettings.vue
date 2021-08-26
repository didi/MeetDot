<template>
  <div>
    <TranslateSelector />
    <h1 v-t="'CreateRoom.title'"></h1>
    <div class="settings-section">
      <h3>
        {{ $t("CreateRoom.room_name")
        }}<input maxlength="20" class="room-name-input" v-model="id" />
      </h3>
    </div>
    <transition-group tag="div" name="smooth-list" v-if="defaultSettingsLoaded">
      <div class="settings-section" key="global-settings">
        <h2 v-t="'Settings.global_title'"></h2>
        <div class="setting-group">
          <input
            type="checkbox"
            id="captioning-active"
            value="captioning-active"
            v-model="settings.interface.captioning_active"
          />
          <label
            for="captioning-active"
            v-t="'Settings.enable_translation'"
          ></label>
        </div>
        <div>
          <label v-t="'Settings.max_participants'"></label>
          <div class="slider">
            <vue-slider
              v-model="settings.interface.max_participants"
              :min="2"
              :max="11"
              :interval="1"
              :adsorb="true"
              :marks="true"
            />
          </div>
        </div>
        <div>
          <label
            for="enable-screen-share"
            v-t="'Settings.enable_screen_share'"
          ></label>
          <input
            type="checkbox"
            id="enable-screen-share"
            v-model="settings.interface.screen_sharing"
          />
        </div>
        <div>
          <label
            for="enable-audio-logs"
            v-t="'Settings.save_audio_logs'"
          ></label>
          <input
            type="checkbox"
            id="enable-audio-logs"
            v-model="settings.save_audio_logs"
          />
        </div>
      </div>
      <div
        class="settings-section"
        v-if="settings.interface.captioning_active"
        key="asr-settings"
      >
        <h2 v-t="'Settings.asr_title'"></h2>
        <div class="setting-group">
          <h4 v-t="'Settings.asr_system'"></h4>
          <label for="wenet">Wenet (en, zh)</label>
          <input
            type="radio"
            id="wenet"
            value="wenet"
            v-model="settings.services.asr.provider"
          />
          <input
            type="radio"
            id="google-asr"
            value="google"
            v-model="settings.services.asr.provider"
          />
          <label for="google-asr">Google</label>
          <input
            type="radio"
            id="kaldi-asr"
            value="kaldi"
            v-model="settings.services.asr.provider"
          />
          <label for="kaldi-asr">Kaldi</label>
          <input
            type="radio"
            id="kaldi-http"
            value="kaldi HTTP (en, zh)"
            v-model="settings.services.asr.provider"
          />
          <label for="iflytek">iFlytek (en, zh)</label>
          <input
            type="radio"
            id="iflytek"
            value="iFlytek"
            v-model="settings.services.asr.provider"
          />
          <label for="iflytek">iFlytek (en, zh)</label>
        </div>
        {{ $t("Settings.stability_threshold") }}
        {{ settings.services.asr.stability_threshold }}
        <div class="slider">
          <vue-slider
            v-model="settings.services.asr.stability_threshold"
            :min="0"
            :max="1"
            :interval="0.01"
          />
        </div>
        <div class="checkbox">
          <input
            type="checkbox"
            id="language-detect"
            v-model="settings.services.asr.language_id.enabled"
          />
          <label
            for="language-detect"
            v-t="'Settings.enable_language_detect'"
          />
        </div>
      </div>
      <div
        class="settings-section"
        v-if="settings.interface.captioning_active"
        key="mt-settings"
      >
        <h2 v-t="'Settings.translation_title'"></h2>
        <div class="setting-group">
          <h4 v-t="'Settings.translation_system'"></h4>
          <input
            type="radio"
            id="google-mt"
            value="google"
            v-model="settings.services.translation.provider"
          />
          <label for="google-mt">Google</label>
          <input
            type="radio"
            id="didi-mt"
            value="didi"
            v-model="settings.services.translation.provider"
          />
          <label for="didi-mt">DiDi</label>
        </div>
        <div
          class="setting-group"
          v-if="settings.services.translation.provider == 'didi'"
        >
          <p>
            {{ $t("Settings.translation_bias_beta") }}
            {{ settings.services.translation.bias_beta }}
          </p>
          <div class="slider">
            <vue-slider
              v-model="settings.services.translation.bias_beta"
              :min="0"
              :max="1"
              :interval="0.1"
            />
          </div>
        </div>
        {{ $t("Settings.translation_min_interval_ms") }}
        {{ settings.services.translation.min_interval_ms }}
        <div class="slider">
          <vue-slider
            v-model="settings.services.translation.min_interval_ms"
            :min="0"
            :max="2000"
            :interval="100"
          />
        </div>
      </div>
      <div
        class="settings-section"
        v-if="settings.interface.captioning_active"
        key="post-translation-settings"
      >
        <h2 v-t="'Settings.post_translation_title'"></h2>
        <div
          class="slider"
          v-if="settings.services.captioning.strategy !== 'skype_style'"
        >
          <label for="mask-k">Mask-K {{ $t("Settings.mask_k_help") }}</label>
          <div class="slider">
            <vue-slider
              v-model="settings.services.post_translation.mask_k"
              :min="0"
              :max="6"
              :interval="1"
              :adsorb="true"
              :marks="true"
            />
          </div>
        </div>
        <div class="checkbox">
          <input
            type="checkbox"
            id="disable-masking-before-k"
            v-model="
              settings.services.post_translation.disable_masking_before_k
            "
          />
          <label
            for="disable-masking-before-k"
            v-t="'Settings.disable_masking_before_k'"
          />
        </div>
        <div
          class="slider"
          v-if="settings.services.captioning.strategy !== 'skype_style'"
        >
          <label for="translate-k"
            >Translate-K {{ $t("Settings.translate_k_help") }}</label
          >
          <div class="slider">
            <vue-slider
              v-model="settings.services.post_translation.translate_k"
              :min="0"
              :max="6"
              :interval="1"
              :adsorb="true"
              :marks="true"
            />
          </div>
        </div>
        <div class="checkbox">
          <input
            type="checkbox"
            id="remove-profanity"
            v-model="settings.services.post_translation.remove_profanity"
          />
          <label for="remove-profanity" v-t="'Settings.remove_profanity'" />
        </div>
        <div class="checkbox">
          <input
            type="checkbox"
            id="add-punctuation"
            v-model="settings.services.post_translation.add_punctuation"
          />
          <label for="add-punctuation" v-t="'Settings.add_punctuation'" />
        </div>
      </div>
      <div
        class="settings-section"
        v-if="settings.interface.captioning_active"
        key="captioning-settings"
      >
        <h2 v-t="'Settings.captioning_title'"></h2>
        <label for="num_lines" v-t="'Settings.number_lines'"></label>
        <div class="slider">
          <vue-slider
            v-model="settings.services.captioning.num_lines"
            :min="1"
            :max="4"
            :interval="1"
            :adsorb="true"
            :marks="true"
          />
        </div>
        <div class="setting-group">
          <h4 v-t="'Settings.captioning_system'"></h4>
          <input
            type="radio"
            id="word"
            value="wordwise_sliding_window"
            v-model="settings.services.captioning.strategy"
          />
          <label for="word" v-t="'Settings.sliding'"></label>
          <input
            type="radio"
            id="line"
            value="linewise_scroll"
            v-model="settings.services.captioning.strategy"
          />
          <label for="line" v-t="'Settings.scrolling'"></label>
          <input
            type="radio"
            id="line"
            value="skype_style"
            v-model="settings.services.captioning.strategy"
          />
          <label for="line">Skype-style</label>
          <input
            type="radio"
            id="line"
            value="punctuation_sensitive"
            v-model="settings.services.captioning.strategy"
          />
          <label for="line" v-t="'Settings.punc_sensitive'"></label>
        </div>
      </div>
      <div
        class="settings-section"
        v-if="settings.interface.captioning_active"
        key="game-settings"
      >
        <h2 v-t="'Settings.game_title'"></h2>
        <div class="setting-group">
          <input
            type="checkbox"
            id="word-guessing"
            value="word-guessing"
            v-model="settings.interface.games.word_guessing"
          />
          <label for="word-guessing" v-t="'Settings.game_on'"></label>
        </div>
        <div class="slider" v-if="settings.interface.games.word_guessing">
          <label for="game_duration" v-t="'Settings.game_duration'"></label>
          <div class="slider">
            <vue-slider
              v-model="settings.interface.games.game_duration"
              :data="{
                10: $t('General.seconds', { n: 10 }),
                30: $t('General.seconds', { n: 30 }),
                180: $t('General.minutes', { n: 3 }),
              }"
              :adsorb="true"
              :value="'180'"
            />
          </div>
        </div>
      </div>
      <div class="settings-section" key="audio-settings">
        <h2 v-t="'Settings.audio_title'"></h2>
        <div class="setting-group">
          <input
            type="checkbox"
            id="audio-distortion"
            value="audio-distortion"
            v-model="settings.interface.audio.distortion"
          />
          <label for="audio-distortion" v-t="'Settings.muffle'"></label>
        </div>
      </div>
      <div
        class="settings-section"
        v-if="settings.interface.captioning_active"
        key="chatbot-settings"
      >
        <h2 v-t="'Settings.chatbot_title'"></h2>
        <div class="setting-group">
          <input
            type="checkbox"
            id="chatbot-enabled"
            v-model="settings.interface.chatbot.enabled"
          />
          <label for="chatbot-enabled" v-t="'Settings.chatbot_on'"></label>
        </div>
        <div class="setting-group" v-if="settings.interface.chatbot.enabled">
          <input
            type="radio"
            id="chatbot-english"
            value="en-US"
            v-model="settings.interface.chatbot.language"
          />
          <label for="chatbot-english">{{ $t("General.english") }}</label>
          <input
            type="radio"
            id="chatbot-spanish"
            value="es-ES"
            v-model="settings.interface.chatbot.language"
          />
          <label for="chatbot-spanish">{{ $t("General.spanish") }}</label>
          <input
            type="radio"
            id="chatbot-chinese"
            value="zh"
            v-model="settings.interface.chatbot.language"
          />
          <label for="chatbot-chinese">{{ $t("General.chinese") }}</label>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script>
import Vue from "vue";
import VueSlider from "vue-slider-component";
import "vue-slider-component/theme/antd.css";
import backendService from "../service/index.js";
import utils from "../utils.js";
import TranslateSelector from "./TranslateSelector.vue";

export default {
  name: "roomSettings",
  components: {
    VueSlider,
    TranslateSelector,
  },
  data() {
    return {
      id: "",
      defaultSettingsLoaded: false,
      settings: {},
    };
  },
  mounted() {
    this.id = utils.createRoomId();
    backendService()("/settings").then((response) => {
      this.settings = response.data;
      this.defaultSettingsLoaded = true;
    });
  },
};
</script>

<style scoped>
.settings-section {
  width: 100%;
}

.room-name-input {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  color: #2c3e50;
  font-size: 14px;
}

.slider {
  margin: 10px auto;
  padding-bottom: 20px;
  min-width: 200px;
  width: 20%;
}

.setting-group {
  margin-bottom: 15px;
}

.setting-group h4 {
  margin-bottom: 5px;
}

.nice-button {
  margin-bottom: 20px;
}

/* Transitions for list */
.smooth-list-enter,
.smooth-list-leave-to {
  opacity: 0;
}
.smooth-list-leave-active {
  position: absolute;
}
.smooth-list-move {
  transition: transform 0.5s;
}
</style>
