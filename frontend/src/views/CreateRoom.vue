<template>
  <div>
    <room-settings ref="settings"> </room-settings>
    <button
      class="nice-button"
      v-on:click="create"
      key="create-button"
      v-t="'Settings.create_room'"
    ></button>
  </div>
</template>

<script>
import Vue from "vue";
import backendService from "../service/index.js";
import utils from "../utils.js";
import roomSettings from "../components/RoomSettings.vue";

export default {
  name: "CreateRoom",
  components: {
    roomSettings,
  },
  data() {
    return {};
  },
  methods: {
    create() {
      let self = this;
      let room_id = self.$refs.settings.id;
      backendService()
        .post(
          "/rooms",
          JSON.stringify({
            roomId: room_id,
            roomType: "meeting",
            settings: self.$refs.settings.settings,
          }),
          {
            headers: {
              "Content-Type": "application/json",
            },
          }
        )
        .then((response) => {
          if (response.data.success) {
            self.$router.push({ name: "Room", params: { id: room_id } });
          }
        })
        .catch((err) => {
          Vue.$toast.error(err.response.data.description);
        });
      return true;
    },
  },
  mounted() {
    this.$socket.emit("on-page", "create");
  },
};
</script>
