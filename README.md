# Custom Opera GX mods workspace

This repository is a dedicated workspace for building, testing, and maintaining custom Opera GX mods and sidebar extensions.

## Repository layout

```text
d:\gxmods\
├── README.md                              # Workspace overview and mod creation guide
├── mods/                                  # Custom Opera GX mods and sidebar extensions
│   ├── Gemini_Enterprise_Sidebar/         # Google Cloud Gemini Enterprise (Vertex AI) sidebar panel
│   └── T3_Chat_Sidebar/                   # T3 Chat (https://t3.chat/) sidebar panel
└── reference/                             # Official Opera GX reference materials and samples
    ├── README.md                          # Original Opera GX repository README
    ├── documentation/
    │   ├── Mod_Template/                  # Starter template for declarative Opera GX mods
    │   ├── mods.md                        # Manifest schema and feature reference
    │   ├── guidelines.md                  # Asset specifications (audio, icons, wallpapers, shaders)
    │   └── shaders.md                     # SkSL fragment shader uniform and filter reference
    ├── images/                            # Reference documentation assets
    ├── mods/                              # 28 official Opera GX sample mods
    └── tools/
        └── livepreview/                   # Local HTTP hot-reload preview server for SkSL shaders
```

## Custom mods (`mods/`)

### 1. [Gemini Enterprise Sidebar](mods/Gemini_Enterprise_Sidebar/README.md)

Embeds Google Cloud Gemini Enterprise (`https://vertexaisearch.cloud.google.com/us/home/cid/a553b3f6-6377-415d-bde8-6ba45fdaa472?hl=en_US`) directly into the Opera GX left sidebar.

- **Path**: `mods/Gemini_Enterprise_Sidebar`
- **Features**:
  - Native Opera GX crimson red (`#FA1E4E`) transparent line-art Gemini star icon (`16px` to `512px`).
  - Full-bleed Vertex AI sidebar panel with native Opera GX drag resizing and `0 ms` JS blocking boot via static HTML `src` and `preconnect` hints.
  - Automatic `declarativeNetRequest` `Sec-Fetch-*` header rewriting and batched, signature-cached first-party Google cookie synchronization.
- **Verify build**:
  ```powershell
  python mods/Gemini_Enterprise_Sidebar/scripts/build_and_verify.py
  ```

### 2. [T3 Chat Sidebar](mods/T3_Chat_Sidebar/README.md)

Embeds T3 Chat (`https://t3.chat/`) directly into the Opera GX left sidebar.

- **Path**: `mods/T3_Chat_Sidebar`
- **Features**:
  - Native Opera GX crimson red (`#FA1E4E`) transparent line-art `T3` chat bubble icon (`16px` to `512px`).
  - Full-bleed T3 Chat sidebar panel with native Opera GX drag resizing and `0 ms` JS blocking boot via static HTML `src` and `preconnect` hints.
  - Automatic `declarativeNetRequest` `Sec-Fetch-*` header rewriting and batched, signature-cached first-party cookie synchronization across `t3.chat`, `clerk.t3.chat`, `accounts.t3.chat`, and `accounts.google.com`.
- **Verify build**:
  ```powershell
  python mods/T3_Chat_Sidebar/scripts/build_and_verify.py
  ```

## Creating a new mod in `mods/`

### Option A. Declarative Opera GX mod (themes, web modding CSS, shaders, sounds, wallpapers)

1. Copy `reference/documentation/Mod_Template` to `mods/<Your_Mod_Name>`.
2. Edit `mods/<Your_Mod_Name>/manifest.json` and trim `mod.payload` to the features your mod uses (`page_styles`, `theme`, `wallpaper`, `shaders`, `keyboard_sounds`, `browser_sounds`, or `background_music`).
3. See [reference/documentation/mods.md](reference/documentation/mods.md) for manifest fields and [reference/documentation/guidelines.md](reference/documentation/guidelines.md) for asset bitrates and dimensions.
4. For SkSL shaders, test locally with `python reference/tools/livepreview/livepreview.py` and refer to [reference/documentation/shaders.md](reference/documentation/shaders.md).

### Option B. Opera GX sidebar extension (`sidebar_action`)

1. Copy `mods/T3_Chat_Sidebar` or `mods/Gemini_Enterprise_Sidebar` to `mods/<Your_Sidebar_Name>` as a base Manifest V3 sidebar template.
2. Update `manifest.json`, `sidepanel/panel.html`, and `background/service-worker.js` with your target application URL and host permissions.

## Loading and packing in Opera GX

1. Open `opera://extensions` in Opera GX and enable **Developer mode** in the top-right corner.
2. Click **Load unpacked** and select `mods/<Your_Mod_Name>`.
3. Declarative GX mods appear in `opera://mods`, while sidebar extensions pin directly to the left Opera GX sidebar.
4. To package a `.crx` archive for distribution, click **Pack extension** in `opera://extensions` and select `mods/<Your_Mod_Name>`.
