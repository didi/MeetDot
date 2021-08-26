<template>
  <div class="admin-page">
    <TranslateSelector />
    <h1 class="header">
      Video-conference with live translated captions - admin
    </h1>
    <v-dialog />
    <router-link :to="{ name: 'CreateRoom' }">Create new room</router-link>
    <div class="rooms">
      <table v-if="rooms.length" class="rooms-list">
        <tr>
          <th class="room-name">Room</th>
          <th class="room-participants">Room participants</th>
        </tr>
        <tr v-for="room in rooms" :key="room.room_id">
          <td class="room-name">
            <div>{{ room.room_id }}</div>
            <router-link
              :to="{ name: 'Room', params: { id: room.room_id } }"
              class="room-enter"
              ><login
            /></router-link>
            <cog @click="showRoomSettings(room)" />
            <close @click="closeRoom(room)" />
          </td>
          <td class="room-participants">
            {{
              room.participants.length === 0
                ? "(empty)"
                : room.participants
                    .map((e) => getDisplayName(e.name, e.spoken_language))
                    .join(", ")
            }}
          </td>
        </tr>
      </table>

      <div v-else-if="roomsLoaded">
        <p>There are no active rooms.</p>
      </div>
      <div v-else>
        <p>Loading rooms...</p>
      </div>
    </div>
  </div>
</template>

<script>
import backendService from "../service/index.js";
import utils from "../utils.js";
import RoomSettingsModal from "../components/RoomSettingsModal.vue";
import Cog from "vue-material-design-icons/Cog.vue";
import Close from "vue-material-design-icons/Close.vue";
import Login from "vue-material-design-icons/Login.vue";
import TranslateSelector from "../components/TranslateSelector.vue";
import "vue-material-design-icons/styles.css";

export default {
  name: "Home",
  components: {
    Cog,
    Close,
    Login,
    TranslateSelector,
  },
  data() {
    return {
      rooms: [],
      roomsLoaded: false,
      lastRoomsUpdate: 0,
    };
  },
  mounted() {
    this.$socket.emit("on-page", "admin");
    backendService()
      .get("/rooms")
      .then((response) => {
        this.roomsLoaded = true;
        if (response.data.time > this.lastRoomsUpdate) {
          this.rooms = response.data.rooms;
        }
        this.lastRoomsUpdate = response.data.time;
      });
    this.sockets.subscribe("rooms", (data) => {
      if (data.time > this.lastRoomsUpdate) {
        this.rooms = data.rooms;
      }
      this.lastRoomsUpdate = data.time;
    });
  },
  methods: {
    showRoomSettings(room) {
      this.$modal.show(
        RoomSettingsModal,
        {
          room: room,
        },
        {
          height: 600,
        }
      );
    },
    closeRoom(room) {
      this.$modal.show("dialog", {
        text:
          "Are you sure you want to close room " +
          room.room_id +
          "? This will kick out all active participants.",
        buttons: [
          {
            title: "Cancel",
            handler: () => {
              this.$modal.hide("dialog");
            },
          },
          {
            title: "Close",
            handler: () => {
              this.$socket.emit("/close", room.room_id);
              this.$modal.hide("dialog");
            },
          },
        ],
      });
    },
    getDisplayName: utils.getDisplayName,
  },
};
</script>

<style scoped lang="scss">
.header {
  margin-top: 0;
  padding-top: 0.67em;
}
.admin-page {
  padding: 0 10px;
}
.rooms-list {
  max-height: 500px;
  margin: 0 auto;
}
.room-name {
  font-size: 20px;
  min-width: 150px;
}
.room-enter {
  margin-left: 5px;
  display: inline-block;
}

a {
  color: #42b983;
}
.close-icon {
  color: red;
  &:hover {
    color: darkred;
  }
}
</style>
