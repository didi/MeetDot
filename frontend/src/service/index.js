import axios from "axios";
import Vue from "vue";

export default () => {
  const options = {
    baseURL: process.env.VUE_APP_BACKEND_BASE_URL,
  };
  const instance = axios.create(options);

  instance.interceptors.response.use(null, function (error) {
    if (!error.response) {
      Vue.$toast.error(
        "No response from the backend. Check that a backend is running at " +
          process.env.VUE_APP_BACKEND_BASE_URL
      );
    }
    return Promise.reject(error);
  });
  return instance;
};
