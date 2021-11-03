import Vue from "vue";
import VueI18n from "vue-i18n";
import VueRouter from "vue-router";
import VueSocketIO from "vue-socket.io";
import VueToast from "vue-toast-notification";
import AudioVisual from "vue-audio-visual";
import router from "./router/index.js";
import App from "./App.vue";
import "vue-toast-notification/dist/theme-sugar.css";
import vmodal from "vue-js-modal";
import globalMixin from "./globals.js";
import throttle from "lodash/throttle";

// Load locale files for each language
// From: https://www.codeandweb.com/babeledit/tutorials/how-to-translate-your-vue-app-with-vue-i18n
function loadLocaleMessages() {
  const locales = require.context(
    "../locales",
    true,
    /[A-Za-z0-9-_,\s]+\.json$/i
  );
  const messages = {};
  locales.keys().forEach((key) => {
    const matched = key.match(/([A-Za-z0-9-_]+)\./i);
    if (matched && matched.length > 1) {
      const locale = matched[1];
      messages[locale] = locales(key);
    }
  });
  return messages;
}
Vue.use(VueI18n);
const i18n = new VueI18n({
  locale: localStorage.getItem("locale") || "en-US",
  messages: loadLocaleMessages(),
});

Vue.use(VueRouter);
Vue.use(AudioVisual);

// Set up sockets
Vue.use(
  new VueSocketIO({
    connection: process.env.VUE_APP_BACKEND_BASE_URL,
  })
);

// Set up toast library
Vue.use(VueToast, {
  position: "top",
});

// Set up modal
Vue.use(vmodal, { dialog: true });

Vue.config.productionTip = false;

// Set globals on all components
Vue.mixin(globalMixin);

new Vue({
  i18n,
  render: (h) => h(App),
  sockets: {
    error: function (err) {
      if (err.type === "TransportError" && err.description === 0) {
        // Catch error if socket closes when leaving page
        return;
      }
      console.error("Server error:", JSON.stringify(err));
      throttle(() => {
        Vue.$toast.error("Server error: " + JSON.stringify(err));
      }, 20_000);
    },
  },
  router,
}).$mount("#app");
