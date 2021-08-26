<template>
  <div>
    <h3>
      {{ $t("RoomSettings.room_name") }}
      <b>{{ room.room_id }}</b>
      <close class="close-icon" @click="hide" />
    </h3>
    <div class="settings-section">
      <h4 v-t="'Settings.global_title'" />
      <p>
        {{ $t("Settings.enable_translation") }}:
        <b>{{
          room.settings.interface.captioning_active
            ? $t("General.yes")
            : $t("General.no")
        }}</b>
      </p>
      <p>
        {{ $t("Settings.max_participants") }}:
        <b>{{ room.settings.interface.max_participants }}</b>
      </p>
    </div>
    <div
      v-show="room.settings.interface.captioning_active"
      class="captioning-settings"
    >
      <div class="settings-section">
        <h4 v-t="'Settings.asr_title'" />
        <div class="setting-group">
          <p>
            {{ $t("Settings.asr_system") }}:
            <b>{{ room.settings.services.asr.provider }}</b>
          </p>
        </div>
        <p>
          {{ $t("Settings.stability_threshold") }}:
          <b>{{ room.settings.services.asr.stability_threshold }}</b>
        </p>
        <p>
          {{ $t("Settings.enable_language_detect") }}:
          <b>{{
            room.settings.services.asr.language_detect
              ? $t("General.yes")
              : $t("General.no")
          }}</b>
        </p>
      </div>
      <div class="settings-section">
        <h4 v-t="'Settings.translation_title'" />
        <div class="setting-group">
          <p>
            {{ $t("Settings.translation_system") }}:
            <b>{{ room.settings.services.translation.provider }}</b>
          </p>
        </div>
      </div>
      <div class="settings-section">
        <h4 v-t="'Settings.post_translation_title'" />
        <p>
          Mask-K: <b>{{ room.settings.services.post_translation.mask_k }}</b>
        </p>
        <p>
          Disable masking before k:
          <b>{{
            room.settings.services.post_translation.disable_masking_before_k
          }}</b>
        </p>
        <p>
          Translate-K:
          <b>{{ room.settings.services.post_translation.translate_k }}</b>
        </p>
        <p>
          Remove profanity:
          <b>{{ room.settings.services.post_translation.remove_profanity }}</b>
        </p>
        <p>
          Add punctuation and capitalization:
          <b>{{ room.settings.services.post_translation.add_punctuation }}</b>
        </p>
      </div>
      <div class="settings-section">
        <h4 v-t="'Settings.captioning_title'" />
        <p for="num_lines">
          {{ $t("Settings.number_lines") }}:
          <b>{{ room.settings.services.captioning.num_lines }}</b>
        </p>
        <p>
          {{ $t("Settings.captioning_system") }}:
          <b>{{ room.settings.services.captioning.strategy }}</b>
        </p>
      </div>
      <div class="settings-section">
        <h4 v-t="'Settings.game_title'" />
        <p>
          {{ $t("Settings.game_on") }}:
          <b>{{
            room.settings.interface.games.word_guessing
              ? $t("General.yes")
              : $t("General.no")
          }}</b>
        </p>
        <p>
          {{ $t("Settings.game_duration") }}:
          <b>{{ room.settings.interface.games.game_duration }} seconds</b>
        </p>
      </div>
    </div>
    <div class="settings-section">
      <h4 v-t="'Settings.audio_title'" />
      <p>
        {{ $t("Settings.muffle") }}:
        <b>{{
          room.settings.interface.audio.distortion
            ? $t("General.yes")
            : $t("General.no")
        }}</b>
      </p>
    </div>
  </div>
</template>

<script>
import Close from "vue-material-design-icons/Close.vue";
import "vue-material-design-icons/styles.css";

export default {
  name: "RoomSettingsModal",
  components: {
    Close,
  },
  props: {
    room: {
      type: Object,
      required: true,
    },
  },
  methods: {
    hide: function () {
      this.$modal.hide(this.$parent.name);
    },
  },
};
</script>

<style scoped>
.settings-section {
  display: inline-block;
  float: left;
  width: 30%;
  margin: 1%;
  height: 150px;
  margin-bottom: 20px;
}
p {
  margin: 5px;
}
h4 {
  margin: 0;
}
.close-icon {
  cursor: pointer;
  padding-right: 20px;
  float: right;
}
</style>
