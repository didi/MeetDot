const wav_header_size = 44;

const languageCodes = {
  English: "en-US",
  Chinese: "zh",
  Spanish: "es-ES",
  Portuguese: "pt-BR",
};
const displayLanguages = {
  "en-US": "English",
  zh: "Chinese",
  "es-ES": "Spanish",
  "pt-BR": "Portuguese",
};

// Language names in their own language
const endonyms = {
  "en-US": "English (en)",
  "es-ES": "Español (es)",
  "pt-BR": "Português (pt)",
  zh: "中文 (zh)",
};

const sentenceDelimiters = {
  "en-US": ".?!",
  "es-ES": ".?!",
  "pt-BR": ".?!",
  zh: "。？！",
};
const spaceBetweenSentences = {
  "en-US": true,
  "es-ES": true,
  "pt-BR": true,
  zh: false,
};

const videoConstraints = {
  width: {
    min: 640,
    ideal: 640,
    max: 1280,
  },
  height: {
    min: 480,
    ideal: 480,
    max: 960,
  },
};

const globalMixin = {
  beforeCreate: function () {
    this.$globals = {
      wav_header_size,
      languageCodes,
      displayLanguages,
      endonyms,
      sentenceDelimiters,
      spaceBetweenSentences,
      videoConstraints,
    };
  },
};

export {
  wav_header_size,
  languageCodes,
  displayLanguages,
  endonyms,
  sentenceDelimiters,
  spaceBetweenSentences,
  videoConstraints,
};

export default globalMixin;
