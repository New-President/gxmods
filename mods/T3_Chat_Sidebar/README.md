# T3 Chat sidebar for Opera GX

This extension adds T3 Chat (`https://t3.chat/`) directly into the Opera GX left sidebar.

## Target application

`https://t3.chat/`

## Features

- Native Opera GX crimson red (`#FA1E4E`) transparent line-art T3 Chat icon that matches built-in sidebar icons.
- Full-bleed T3 Chat panel with no extra top menu, native Opera GX sidebar resizing, and zero-blocking HTML iframe startup.
- Automatic `declarativeNetRequest` `Sec-Fetch-*` header rewriting (`Sec-Fetch-Dest: document`, `Sec-Fetch-Site: none`) and batched first-party cookie synchronization so `t3.chat` and its authentication providers load inside the extension panel without cross-origin framing blocks.
- Cross-frame Convex session bridge (`content/t3-session-bridge.js` and `content/t3-cookie-sync.js`) that synchronizes `convex-session-id` with `SameSite=None; Secure` in `document.cookie` and normalizes `ModifyQuerySet` WebSocket payloads so `account:getUserConfiguration` never fails with a missing session ID inside the sidebar iframe.

## Installation in Opera GX

1. Open `opera://extensions` in Opera GX.
2. Enable **Developer mode** in the top-right corner.
3. Click **Load unpacked** and select `d:\gxmods\mods\T3_Chat_Sidebar`.
4. Click the crimson T3 Chat icon in the left Opera GX sidebar to open the panel.
