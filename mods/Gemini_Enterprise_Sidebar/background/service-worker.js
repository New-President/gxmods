export const DEFAULT_GEMINI_URL =
  "https://vertexaisearch.cloud.google.com/us/home/cid/a553b3f6-6377-415d-bde8-6ba45fdaa472?hl=en_US";

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
    ruleId: 1001,
    host: "vertexaisearch.cloud.google.com",
    path: "/us/home/cid/a553b3f6-6377-415d-bde8-6ba45fdaa472",
    requestDomains: ["vertexaisearch.cloud.google.com"],
  },
  {
    ruleId: 1002,
    host: "accounts.google.com",
    path: "/",
    requestDomains: ["accounts.google.com"],
  },
  {
    ruleId: 1003,
    host: "ogs.google.com",
    path: "/",
    requestDomains: ["ogs.google.com"],
  },
  {
    ruleId: 1004,
    host: "apis.google.com",
    path: "/",
    requestDomains: ["apis.google.com"],
  },
  {
    ruleId: 1005,
    host: "clients6.google.com",
    path: "/",
    requestDomains: ["clients6.google.com"],
  },
  {
    ruleId: 1006,
    host: "www.google.com",
    path: "/",
    requestDomains: ["www.google.com"],
  },
]);

const ALL_RULE_IDS = COOKIE_SYNC_TARGETS.map((target) => target.ruleId);

let lastSyncedSignature = null;
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

function buildRulesAndSignature(allGoogleCookies) {
  const sortedCookies = allGoogleCookies
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

async function performCookieRuleSync() {
  if (!globalThis.chrome?.cookies || !globalThis.chrome?.declarativeNetRequest) {
    return { ok: false, changed: false, rulesUpdated: 0 };
  }

  await hydrateExistingSignature();

  let allGoogleCookies = [];
  try {
    allGoogleCookies = await chrome.cookies.getAll({ domain: "google.com" });
  } catch (err) {
    return { ok: false, changed: false, error: String(err) };
  }

  const { addRules, signature } = buildRulesAndSignature(allGoogleCookies);
  if (signature === lastSyncedSignature) {
    return { ok: true, changed: false, rulesUpdated: 0 };
  }

  try {
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: ALL_RULE_IDS,
      addRules,
    });
    lastSyncedSignature = signature;
    return { ok: true, changed: true, rulesUpdated: addRules.length };
  } catch (err) {
    return { ok: false, changed: false, error: String(err) };
  }
}

export function syncGoogleAuthRules() {
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
    if (!domain.includes("google.com")) {
      return;
    }
    if (cookieSyncTimer !== null) {
      clearTimeout(cookieSyncTimer);
    }
    cookieSyncTimer = setTimeout(() => {
      cookieSyncTimer = null;
      syncGoogleAuthRules().catch(() => {});
    }, 600);
  });
}

if (globalThis.chrome?.runtime?.onInstalled) {
  chrome.runtime.onInstalled.addListener(() => {
    configureSidePanelBehavior();
    syncGoogleAuthRules().catch(() => {});
  });
}

if (globalThis.chrome?.runtime?.onStartup) {
  chrome.runtime.onStartup.addListener(() => {
    configureSidePanelBehavior();
    syncGoogleAuthRules().catch(() => {});
  });
}

if (globalThis.chrome?.runtime?.onMessage) {
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "SYNC_GOOGLE_AUTH") {
      syncGoogleAuthRules()
        .then((result) => sendResponse(result))
        .catch((err) => sendResponse({ ok: false, changed: false, error: String(err) }));
      return true;
    }
    return false;
  });
}

configureSidePanelBehavior();
syncGoogleAuthRules().catch(() => {});
