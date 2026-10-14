(() => {
  const DEFAULT_ANON_SESSION_ID = "e48c8030-2d9b-4335-bf49-f545f54058de";
  const STORAGE_KEY = "gx_t3_convex_session_id";
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  function readCookieValue(name) {
    const raw = document.cookie || "";
    const parts = raw.split(";");
    for (const part of parts) {
      const eqIdx = part.indexOf("=");
      if (eqIdx === -1) {
        continue;
      }
      const k = part.slice(0, eqIdx).trim();
      if (k === name) {
        return decodeURIComponent(part.slice(eqIdx + 1).trim());
      }
    }
    return "";
  }

  function writeCrossFrameCookie(name, value, path = "/") {
    if (!name || value === undefined || value === null) {
      return;
    }
    try {
      document.cookie = `${name}=${value}; path=${path}; max-age=31536000; SameSite=None; Secure`;
    } catch (_) {}
  }

  function resolveInitialSessionId() {
    const fromCookie = readCookieValue("convex-session-id");
    if (UUID_RE.test(fromCookie)) {
      try {
        localStorage.setItem(STORAGE_KEY, fromCookie);
      } catch (_) {}
      return fromCookie;
    }
    try {
      const fromStorage = localStorage.getItem(STORAGE_KEY) || "";
      if (UUID_RE.test(fromStorage)) {
        return fromStorage;
      }
      localStorage.setItem(STORAGE_KEY, DEFAULT_ANON_SESSION_ID);
    } catch (_) {}
    return DEFAULT_ANON_SESSION_ID;
  }

  let activeSessionId = resolveInitialSessionId();
  writeCrossFrameCookie("convex-session-id", activeSessionId, "/");

  window.addEventListener("__GX_T3_COOKIE_SYNC__", (event) => {
    const detail = event?.detail;
    if (!detail || typeof detail !== "object") {
      return;
    }
    if (typeof detail.sessionId === "string" && UUID_RE.test(detail.sessionId)) {
      activeSessionId = detail.sessionId;
      try {
        localStorage.setItem(STORAGE_KEY, activeSessionId);
      } catch (_) {}
      writeCrossFrameCookie("convex-session-id", activeSessionId, "/");
    }
    if (Array.isArray(detail.clientCookies)) {
      for (const cookie of detail.clientCookies) {
        if (cookie?.name && typeof cookie.value === "string") {
          writeCrossFrameCookie(cookie.name, cookie.value, cookie.path || "/");
        }
      }
    }
  });

  function patchConvexQueryModifications(modifications) {
    if (!Array.isArray(modifications)) {
      return false;
    }
    let batchSessionId = readCookieValue("convex-session-id") || activeSessionId;
    for (const mod of modifications) {
      const arg0 = mod?.args?.[0];
      if (arg0 && typeof arg0.sessionId === "string" && UUID_RE.test(arg0.sessionId)) {
        batchSessionId = arg0.sessionId;
        activeSessionId = batchSessionId;
        break;
      }
    }
    if (!UUID_RE.test(batchSessionId)) {
      batchSessionId = DEFAULT_ANON_SESSION_ID;
    }

    let mutated = false;
    for (const mod of modifications) {
      if (
        mod?.type === "Add" &&
        typeof mod.udfPath === "string" &&
        (mod.udfPath.startsWith("account:") || mod.udfPath.startsWith("profiles:")) &&
        Array.isArray(mod.args) &&
        mod.args.length === 1 &&
        mod.args[0] &&
        typeof mod.args[0] === "object" &&
        !mod.args[0].sessionId
      ) {
        mod.args[0].sessionId = batchSessionId;
        mutated = true;
      }
    }
    return mutated;
  }

  const nativeWsSend = WebSocket.prototype.send;
  WebSocket.prototype.send = function (data) {
    if (typeof data === "string" && data.includes('"ModifyQuerySet"')) {
      try {
        const parsed = JSON.parse(data);
        if (
          parsed?.type === "ModifyQuerySet" &&
          patchConvexQueryModifications(parsed.modifications)
        ) {
          return nativeWsSend.call(this, JSON.stringify(parsed));
        }
      } catch (_) {}
    }
    return nativeWsSend.call(this, data);
  };
})();
