export const DEFAULT_T3_URL = "https://t3.chat/";
export const DEFAULT_ANON_SESSION_ID = "e48c8030-2d9b-4335-bf49-f545f54058de";

const AUTH_RESOURCE_TYPES = [
  "sub_frame",
  "main_frame",
  "xmlhttprequest",
  "script",
  "websocket",
  "ping",
  "other",
];

const COOKIE_SYNC_TARGETS = Object.freeze([
  {
    ruleId: 2001,
    host: "t3.chat",
    path: "/",
    requestDomains: ["t3.chat"],
  },
  {
    ruleId: 2002,
    host: "clerk.t3.chat",
    path: "/",
    requestDomains: ["clerk.t3.chat"],
  },
  {
    ruleId: 2003,
    host: "accounts.t3.chat",
    path: "/",
    requestDomains: ["accounts.t3.chat"],
  },
  {
    ruleId: 2004,
    host: "accounts.google.com",
    path: "/",
    requestDomains: ["accounts.google.com"],
  },
  {
    ruleId: 2005,
    host: "www.google.com",
    path: "/",
    requestDomains: ["www.google.com"],
  },
]);

const ALL_RULE_IDS = COOKIE_SYNC_TARGETS.map((target) => target.ruleId);

let lastSyncedSignature = null;
let lastSessionId = DEFAULT_ANON_SESSION_ID;
let lastClientCookies = [];
let syncInFlight = null;
let cookieSyncTimer = null;

function configureSidePanelBehavior() {
  if (globalThis.chrome?.sidePanel?.setPanelBehavior) {
    chrome.sidePanel
      .setPanelBehavior({ openPanelOnActionClick: true })
      .catch(() => {});
  }
}

function cookieMatchesTarget(cookie, host, targetPath) {
  const rawDomain = cookie.domain || "";
  if (cookie.hostOnly) {
    if (rawDomain !== host) {
      return false;
    }
  } else {
    const cleanDomain = rawDomain.startsWith(".") ? rawDomain.slice(1) : rawDomain;
    if (host !== cleanDomain && !host.endsWith(`.${cleanDomain}`)) {
      return false;
    }
  }

  const cookiePath = cookie.path || "/";
  if (cookiePath === "/") {
    return true;
  }
  if (!targetPath.startsWith(cookiePath)) {
    return false;
  }
  return (
    targetPath.length === cookiePath.length ||
    cookiePath.endsWith("/") ||
    targetPath[cookiePath.length] === "/"
  );
}

function buildRulesAndSignature(allCookies) {
  const sortedCookies = allCookies
    .slice()
    .sort((a, b) => (b.path?.length || 0) - (a.path?.length || 0));

  const addRules = [];
  const signatureParts = [];

  for (const target of COOKIE_SYNC_TARGETS) {
    const uniquePairs = new Map();
    for (const cookie of sortedCookies) {
      if (
        !uniquePairs.has(cookie.name) &&
        cookieMatchesTarget(cookie, target.host, target.path)
      ) {
        uniquePairs.set(cookie.name, `${cookie.name}=${cookie.value}`);
      }
    }

    if (uniquePairs.size === 0) {
      continue;
    }

    const cookieHeader = Array.from(uniquePairs.values()).join("; ");
    signatureParts.push(`${target.ruleId}:${cookieHeader}`);

    addRules.push({
      id: target.ruleId,
      priority: 100,
      action: {
        type: "modifyHeaders",
        requestHeaders: [
          {
            header: "Cookie",
            operation: "set",
            value: cookieHeader,
          },
        ],
      },
      condition: {
        requestDomains: target.requestDomains,
        resourceTypes: AUTH_RESOURCE_TYPES,
      },
    });
  }

  return {
    addRules,
    signature: signatureParts.join("\n"),
  };
}

async function hydrateExistingSignature() {
  if (lastSyncedSignature !== null || !globalThis.chrome?.declarativeNetRequest?.getDynamicRules) {
    return;
  }
  try {
    const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
    const parts = [];
    const sorted = existingRules
      .filter((rule) => ALL_RULE_IDS.includes(rule.id))
      .sort((a, b) => a.id - b.id);
    for (const rule of sorted) {
      const val = rule.action?.requestHeaders?.[0]?.value || "";
      if (val) {
        parts.push(`${rule.id}:${val}`);
      }
    }
    if (parts.length > 0) {
      lastSyncedSignature = parts.join("\n");
    }
  } catch (_) {}
}

async function ensureConvexSessionCookie(t3Cookies) {
  const existing = t3Cookies.find(
    (cookie) => cookie.name === "convex-session-id" && Boolean(cookie.value)
  );
  const oneYearFromNow = Math.floor(Date.now() / 1000) + 31536000;

  if (!existing) {
    try {
      await chrome.cookies.set({
        url: DEFAULT_T3_URL,
        name: "convex-session-id",
        value: DEFAULT_ANON_SESSION_ID,
        path: "/",
        secure: true,
        sameSite: "no_restriction",
        expirationDate: oneYearFromNow,
      });
    } catch (_) {}
    const seeded = {
      name: "convex-session-id",
      value: DEFAULT_ANON_SESSION_ID,
      domain: "t3.chat",
      hostOnly: true,
      path: "/",
      httpOnly: false,
      secure: true,
      sameSite: "no_restriction",
    };
    t3Cookies.push(seeded);
    return DEFAULT_ANON_SESSION_ID;
  }

  if (existing.sameSite !== "no_restriction") {
    try {
      await chrome.cookies.set({
        url: DEFAULT_T3_URL,
        name: "convex-session-id",
        value: existing.value,
        path: existing.path || "/",
        secure: true,
        sameSite: "no_restriction",
        expirationDate: existing.expirationDate || oneYearFromNow,
      });
    } catch (_) {}
  }
  return existing.value;
}

async function performCookieRuleSync() {
  if (!globalThis.chrome?.cookies || !globalThis.chrome?.declarativeNetRequest) {
    return {
      ok: false,
      changed: false,
      rulesUpdated: 0,
      sessionId: lastSessionId,
      clientCookies: lastClientCookies,
    };
  }

  await hydrateExistingSignature();

  let allCookies = [];
  try {
    const [t3Cookies, googleCookies] = await Promise.all([
      chrome.cookies.getAll({ domain: "t3.chat" }),
      chrome.cookies.getAll({ domain: "google.com" }),
    ]);
    lastSessionId = await ensureConvexSessionCookie(t3Cookies);
    lastClientCookies = t3Cookies
      .filter((cookie) => !cookie.httpOnly && cookie.name && cookie.value)
      .map((cookie) => ({
        name: cookie.name,
        value: cookie.value,
        path: cookie.path || "/",
      }));
    allCookies = [...t3Cookies, ...googleCookies];
  } catch (err) {
    return { ok: false, changed: false, error: String(err) };
  }

  const { addRules, signature } = buildRulesAndSignature(allCookies);
  if (signature === lastSyncedSignature) {
    return {
      ok: true,
      changed: false,
      rulesUpdated: 0,
      sessionId: lastSessionId,
      clientCookies: lastClientCookies,
    };
  }

  try {
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: ALL_RULE_IDS,
      addRules,
    });
    lastSyncedSignature = signature;
    return {
      ok: true,
      changed: true,
      rulesUpdated: addRules.length,
      sessionId: lastSessionId,
      clientCookies: lastClientCookies,
    };
  } catch (err) {
    return { ok: false, changed: false, error: String(err) };
  }
}

export function syncT3AuthRules() {
  if (!syncInFlight) {
    syncInFlight = performCookieRuleSync().finally(() => {
      syncInFlight = null;
    });
  }
  return syncInFlight;
}

if (globalThis.chrome?.cookies?.onChanged) {
  chrome.cookies.onChanged.addListener((changeInfo) => {
    if (changeInfo?.cause === "overwrite") {
      return;
    }
    const domain = changeInfo?.cookie?.domain || "";
    if (!domain.includes("t3.chat") && !domain.includes("google.com")) {
      return;
    }
    if (cookieSyncTimer !== null) {
      clearTimeout(cookieSyncTimer);
    }
    cookieSyncTimer = setTimeout(() => {
      cookieSyncTimer = null;
      syncT3AuthRules().catch(() => {});
    }, 600);
  });
}

if (globalThis.chrome?.runtime?.onInstalled) {
  chrome.runtime.onInstalled.addListener(() => {
    configureSidePanelBehavior();
    syncT3AuthRules().catch(() => {});
  });
}

if (globalThis.chrome?.runtime?.onStartup) {
  chrome.runtime.onStartup.addListener(() => {
    configureSidePanelBehavior();
    syncT3AuthRules().catch(() => {});
  });
}

if (globalThis.chrome?.runtime?.onMessage) {
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "SYNC_T3_AUTH") {
      syncT3AuthRules()
        .then((result) => sendResponse(result))
        .catch((err) => sendResponse({ ok: false, changed: false, error: String(err) }));
      return true;
    }
    return false;
  });
}

configureSidePanelBehavior();
syncT3AuthRules().catch(() => {});
