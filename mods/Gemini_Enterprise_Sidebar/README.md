# Gemini Enterprise sidebar for Opera GX

This extension adds Google Cloud Gemini Enterprise (Vertex AI Search) directly into the Opera GX left sidebar.

## Target application

`https://vertexaisearch.cloud.google.com/us/home/cid/a553b3f6-6377-415d-bde8-6ba45fdaa472?hl=en_US`

## Features

- Native Opera GX crimson red (`#FA1E4E`) transparent line-art Gemini star icon that matches built-in sidebar icons.
- Full-bleed Vertex AI panel with no extra top menu and native Opera GX sidebar resizing.
- Automatic `declarativeNetRequest` `Sec-Fetch-*` header rewriting (`Sec-Fetch-Dest: document`, `Sec-Fetch-Site: none`) and first-party Google cookie synchronization so `vertexaisearch.cloud.google.com` loads inside the extension panel without returning HTTP 403 or blocking cross-origin navigation.

## Installation in Opera GX

1. Open `opera://extensions` in Opera GX.
2. Enable **Developer mode** in the top-right corner.
3. Click **Load unpacked** and select `d:\gxmods\mods\Gemini_Enterprise_Sidebar` (or click **Reload** if it is already loaded).
4. Click the crimson Gemini star icon in the left Opera GX sidebar to open the panel.
