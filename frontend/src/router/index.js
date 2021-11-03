import Vue from "vue";
import VueRouter from "vue-router";

const routes = [
  {
    path: "/admin",
    name: "Admin",
    component: () => import("../views/Admin.vue"),
    meta: { title: "MeetDot: Admin" },
  },
  {
    path: "/create",
    name: "CreateRoom",
    component: () => import("../views/CreateRoom.vue"),
    meta: { title: "MeetDot: Create room" },
  },
  {
    path: "/room/:id",
    name: "Room",
    component: () =>
      import(/* webpackChunkName: "group-main" */ "../views/Room.vue"),
    meta: { title: "MeetDot: Room" },
  },
  {
    path: "/live",
    name: "Live",
    component: () =>
      import(/* webpackChunkName: "group-main" */ "../views/Live.vue"),
    meta: { title: "MeetDot: Live translator" },
  },
  {
    path: "/meetbox",
    name: "MeetBox",
    component: () =>
      import(/* webpackChunkName: "group-main" */ "../views/MeetBox.vue"),
    meta: { title: "Conference room translator" },
  },
  {
    path: "/audience/:id",
    name: "Audience",
    component: () =>
      import(/* webpackChunkName: "group-main" */ "../views/Audience.vue"),
    meta: { title: "MeetDot: Audience view" },
  },
  {
    path: "/multi",
    name: "MultiRoom",
    component: () => import("../views/MultiRoom.vue"),
    meta: {
      title: "Side-by-Side comparison of two speech-translation configs",
    },
  },
  {
    path: "/post-meeting/:id",
    name: "PostMeeting",
    component: () =>
      import(/* webpackChunkName: "group-main" */ "../views/PostMeeting.vue"),
    meta: { title: "MeetDot: Post-meeting" },
  },
  {
    path: "/",
    name: "Home",
    component: () =>
      import(/* webpackChunkName: "group-main" */ "../views/Home.vue"),
    meta: { title: "MeetDot" },
  },
  {
    path: "*",
    redirect: { name: "Home" },
  },
];

const router = new VueRouter({
  mode: "history",
  routes,
});

// Change page header
router.afterEach((to) => {
  Vue.nextTick(() => {
    document.title = to.meta.title || "MeetDot";
  });
});
export default router;
