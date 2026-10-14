export const DEFAULT_GEMINI_URL =
  "https://vertexaisearch.cloud.google.com/us/home/cid/a553b3f6-6377-415d-bde8-6ba45fdaa472?hl=en_US";

function verifyAuthSyncInBackground() {
  if (!globalThis.chrome?.runtime?.sendMessage) {
    return;
  }
  chrome.runtime
    .sendMessage({ type: "SYNC_GOOGLE_AUTH" })
    .then((result) => {
      if (result?.changed) {
        const frame = document.getElementById("gemini-frame");
        if (frame) {
          frame.src = DEFAULT_GEMINI_URL;
        }
      }
    })
    .catch(() => {});
}

verifyAuthSyncInBackground();
