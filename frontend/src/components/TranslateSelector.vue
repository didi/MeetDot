<template>
  <div class="translation-panel">
    <div id="translate-icon">
      <img
        :src="
          require('material-design-icons/action/2x_web/ic_translate_black_48dp.png')
        "
      />
    </div>

    <select id="menu" v-model="$i18n.locale">
      <option
        v-for="(val, key) in $i18n.messages"
        :key="key"
        :value="key"
        @click="setLang(key)"
      >
        {{ $globals.endonyms[key] }}
      </option>
    </select>
  </div>
</template>

<script>
export default {
  name: "TranslationPanel",
  methods: {
    setLang(langCode) {
      localStorage.setItem("locale", langCode);
    },
  },
};
</script>

<style scoped lang="scss">
.translation-panel {
  position: fixed;
  top: 5px;
  right: 5px;
  text-align: right;
  margin: 5px;
  padding: 0;
  line-height: 0;
  display: flex;

  background: #ddd;
  border-radius: 3px 3px;

  z-index: 10;
}

div#translate-icon {
  width: 100%;
  display: inline-block;
  border-radius: 3px 0 0 3px;
  background: #ccc;

  img {
    height: 30px;
    padding: 3px;
  }
}

#menu {
  list-style-type: none;
  line-height: 1.5;
  padding: 0;
  margin: 5px 0;
  appearance: none;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 1em;

  li {
    margin: 0;
    padding: 0 5px;
  }

  li:hover {
    background: #888;
  }
}
</style>
