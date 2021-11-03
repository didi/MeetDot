import Vue from "vue";
import backendService from "../service/index.js";
import utils from "../utils.js";

export default {
  name: "roomMixin",
  props: ["spokenLanguage", "captionLanguage", "roomType", "userIdPrefix"],
  data() {
    return {
      room: null,
      stage: null,
      user_id: null,
    };
  },
  mounted() {},
  methods: {
    async _Start(settings, room_id) {
      this.stage = "1: create room in backend";
      this.user_id = this.userIdPrefix + "-" + utils.randomString(8);
      await backendService()
        .post(
          "/rooms",
          JSON.stringify({
            roomId: room_id,
            roomType: this.roomType,
            settings,
          }),
          {
            headers: {
              "Content-Type": "application/json",
            },
          }
        )
        .then((response) => {
          this.stage = "2: on-page, setting up sockets";
          this.$socket.emit("on-page", "room/" + room_id);
          this.stage = "3: getting room";
          return backendService().get("/rooms/" + room_id);
        })
        .then((response) => {
          const room = response.data.room;
          if (room !== null) {
            this.room = room;
            this.stage = "4: joining room";
            this.$socket.emit(
              "/join",
              {
                spokenLanguage: this.spokenLanguage,
                captionLanguages: [this.captionLanguage],
                name: this.user_id,
                userId: this.user_id,
                roomId: this.room.room_id,
              },
              this._onJoined
            );
            window.addEventListener("beforeunload", this.disconnect);
            window.addEventListener("popstate", this.disconnect);
          } else {
            throw new Error(
              "Room.error_got_null_room_when_joining, room_id: " + room_id
            );
          }
        })
        .catch((err) => {
          console.log("caught error:" + err);
          Vue.$toast.error(
            "Error starting room, current stage: " +
              this.stage +
              ", error: " +
              err
          );
          this.disconnect();
        });
    },
    _onJoined(couldJoin, errorMessage) {
      if (!couldJoin) {
        throw new Error(
          this.$t("Room.error_join", {
            roomId: this.room.room_id,
            errorMessage,
          })
        );
      }
      this.stage = "5: joined room";
      this.onJoined();
    },
    onJoined() {
      // Override this in your component to do extra stuff after joining.
    },
    _disconnect(resolve, reject) {
      if (this.user_id !== null) {
        this.$socket.emit(
          "disconnect-user",
          { userId: this.user_id },
          (disconnectAck) => {
            if (disconnectAck) {
              this.room = null;
              this.user_id = null;
              this.stage = null;
              resolve();
            } else {
              reject(
                this.$t(
                  "Failed to disconnect user_id: " +
                    this.user_id +
                    " from room_id: " +
                    this.room_id
                )
              );
            }
          }
        );
      } else {
        resolve();
      }
    },
    disconnect() {
      this._disconnect(
        () => true,
        (err) => {
          throw new Error(err);
        }
      );
    },
    disconnectPromise() {
      return new Promise((resolve, reject) => {
        this._disconnect(resolve, reject);
      });
    },
  },
};
