<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script>
export default {
  name: "App",
};
</script>

<style lang="scss">
@import "https://fonts.googleapis.com/icon?family=Material+Icons|Material+Icons+Two+Tone";

#app,
#modals-container {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}

#app {
  height: 100vh;
  overflow: auto;
}

body {
  margin: 0;
}

.nice-button {
  font-size: 14px;
  padding: 10px;
  border: none;
  border-radius: 4px;
  background-color: blue;
  color: white;
  font-weight: bold;
  border: solid thin transparent;

  &:not(:disabled):hover {
    cursor: pointer;
  }

  &:disabled:hover {
    cursor: not-allowed;
  }

  &:disabled {
    border: solid thin darkgrey;
    background-color: lightgrey;
  }
}
.nice-button-big {
  font-size: 22px;
  padding: 14px;
  margin: 0 10px;
  border: solid thin transparent;
  border-radius: 4px;
  background-color: blue;
  color: white;

  &:not(:disabled):hover {
    cursor: pointer;
  }

  &:disabled:hover {
    cursor: not-allowed;
  }

  &:disabled {
    border: solid thin darkgrey;
    background-color: lightgrey;
  }
}

.material-icons,
.material-icons-two-tone {
  cursor: pointer;
  user-select: none;
}
.material-icons.white {
  color: #fff;
}
.material-icons-two-tone.white {
  /* This filter is generated automatically by the link in this answer:
  https://stackoverflow.com/questions/60778658 */
  filter: invert(97%) sepia(3%) saturate(876%) hue-rotate(235deg)
    brightness(123%) contrast(100%);
}

// Dark scrollbar that overrides Chrome's (ugly) default
.dark-scrollbar {
  scrollbar-color: #666 #111; // Firefox

  // Webkit browsers e.g. Chrome
  &::-webkit-scrollbar {
    background-color: #111;
    width: 10px;
  }
  &::-webkit-scrollbar-thumb {
    background-color: #666;
    border-radius: 5px;
  }
}
</style>
