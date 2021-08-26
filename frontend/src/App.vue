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
.material-design-icon {
  cursor: pointer;
  user-select: none;
}
</style>
