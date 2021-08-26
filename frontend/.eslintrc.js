module.exports = {
  extends: ["plugin:vue/essential", "plugin:@intlify/vue-i18n/base"],
  rules: {
    // Optional.
    "@intlify/vue-i18n/no-unused-keys": [
      "error",
      {
        extensions: [".js", ".vue"],
      },
    ],
    "@intlify/vue-i18n/no-duplicate-keys-in-locale": [
      "error",
      {
        ignoreI18nBlock: false,
      },
    ],
    "@intlify/vue-i18n/no-missing-keys-in-other-locales": "error",
    "@intlify/vue-i18n/no-unused-keys": "error",
  },
  settings: {
    "vue-i18n": {
      localeDir: "./locales/*.json",

      // Specify the version of `vue-i18n` you are using.
      // If not specified, the message will be parsed twice.
      messageSyntaxVersion: "^9.0.0",
    },
  },
  parserOptions: {
    parser: "babel-eslint",
  },
  overrides: [
    {
      files: ["*.json"],
      extends: ["plugin:@intlify/vue-i18n/base"],
    },
  ],
  plugins: ["vue"],
};
