(() => {
  if (!globalThis.chrome?.runtime?.sendMessage) {
    return;
  }

  function requestCookieSync() {
    chrome.runtime
      .sendMessage({ type: "SYNC_T3_AUTH" })
      .then((response) => {
        if (response?.ok) {
          window.dispatchEvent(
            new CustomEvent("__GX_T3_COOKIE_SYNC__", {
              detail: {
                sessionId: response.sessionId || "",
                clientCookies: Array.isArray(response.clientCookies)
                  ? response.clientCookies
                  : [],
              },
            })
          );
        }
      })
      .catch(() => {});
  }

  requestCookieSync();
})();
