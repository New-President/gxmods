export const DEFAULT_T3_URL = "https://t3.chat/";

function verifyAuthSyncInBackground() {
  if (!globalThis.chrome?.runtime?.sendMessage) {
    return;
  }
  chrome.runtime
    .sendMessage({ type: "SYNC_T3_AUTH" })
    .then((result) => {
      if (result?.changed) {
        const frame = document.getElementById("t3-frame");
        if (frame) {
          frame.src = DEFAULT_T3_URL;
        }
      }
    })
    .catch(() => {});
}

verifyAuthSyncInBackground();
