<!--
Pixel-wise scrolling for caption lines.
This only makes sense for the linewise-scrolling strategy.
-->

<template>
  <transition-group tag="div" class="captions" name="captions">
    <div
      class="translation-line"
      v-for="line in indexedTranslationLines"
      :key="line.index"
    >
      <span v-if="line.text.length">{{ line.text }}</span>
      <span class="highlighted" v-if="line.highlightedText.length">{{
        line.highlightedText
      }}</span>
    </div>
  </transition-group>
</template>

<script>
export default {
  name: "AnimatedLines",
  props: {
    indexedTranslationLines: Array,
  },
};
</script>

<style scoped lang="scss">
.highlighted {
  font-weight: 600;
  color: #888;
}

.captions-move {
  transition: transform 0.5s;
}
.captions-enter {
  opacity: 0.5;
}
.captions-enter-active {
  transition: opacity 0.25s ease-in-out;
}
.captions-leave-active {
  position: absolute;
  transition: opacity 0.25s ease-in-out;
}
.captions-leave-to {
  opacity: 0;
}
</style>
