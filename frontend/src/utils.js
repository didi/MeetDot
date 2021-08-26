import { displayLanguages } from "./globals.js";

function randomString(len) {
  let str = "";
  let i = 0;
  const min = 36;
  const max = 62;
  for (; i++ < len; ) {
    let r = (Math.random() * (max - min) + min) << 0;
    str += String.fromCharCode((r += r > 9 ? (r < 36 ? 55 : 61) : 48));
  }
  return str;
}

function createRoomId() {
  return randomString(3) + "-" + randomString(4) + "-" + randomString(3);
}

function getDisplayName(name, language) {
  return `${name} (${displayLanguages[language]})`;
}

function copyToClipboard(value) {
  const el = document.createElement("textarea");
  el.value = value;
  el.setAttribute("readonly", "");
  el.style.position = "absolute";
  el.style.left = "-9999px";
  document.body.appendChild(el);
  const selected =
    document.getSelection().rangeCount > 0
      ? document.getSelection().getRangeAt(0)
      : false;
  el.select();
  document.execCommand("copy");
  document.body.removeChild(el);
  if (selected) {
    document.getSelection().removeAllRanges();
    document.getSelection().addRange(selected);
  }
}

export default { randomString, createRoomId, getDisplayName, copyToClipboard };
