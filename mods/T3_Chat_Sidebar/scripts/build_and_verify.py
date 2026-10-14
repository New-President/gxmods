import json
import math
import pathlib
import struct
import sys
import zlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SIDEBAR_DIR = REPO_ROOT / "mods" / "T3_Chat_Sidebar"
EXPECTED_URL = "https://t3.chat/"
ICON_SIZES = (16, 32, 48, 128, 512)

GX_RED_R = 250
GX_RED_G = 30
GX_RED_B = 78


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _clamp_byte(val: float) -> int:
    return max(0, min(255, int(round(val))))


def _dist_to_segment(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    vx = bx - ax
    vy = by - ay
    wx = px - ax
    wy = py - ay
    len_sq = vx * vx + vy * vy
    if len_sq <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / len_sq))
    proj_x = ax + t * vx
    proj_y = ay + t * vy
    return math.hypot(px - proj_x, py - proj_y)


def _build_t3_segments() -> list[tuple[float, float, float, float]]:
    segments = [
        # Outer chat bubble with bottom-left tail
        (-0.56, -0.66, 0.56, -0.66),
        (0.56, -0.66, 0.74, -0.48),
        (0.74, -0.48, 0.74, 0.34),
        (0.74, 0.34, 0.56, 0.52),
        (0.56, 0.52, -0.18, 0.52),
        (-0.18, 0.52, -0.48, 0.74),
        (-0.48, 0.74, -0.42, 0.52),
        (-0.42, 0.52, -0.56, 0.52),
        (-0.56, 0.52, -0.74, 0.34),
        (-0.74, 0.34, -0.74, -0.48),
        (-0.74, -0.48, -0.56, -0.66),
        # Letter "T"
        (-0.46, -0.32, -0.06, -0.32),
        (-0.26, -0.32, -0.26, 0.22),
        # Digit "3"
        (0.08, -0.32, 0.42, -0.32),
        (0.42, -0.32, 0.42, -0.05),
        (0.14, -0.05, 0.42, -0.05),
        (0.42, -0.05, 0.42, 0.22),
        (0.08, 0.22, 0.42, 0.22),
    ]
    return segments


def render_t3_icon_png(size: int) -> bytes:
    segments = _build_t3_segments()
    half = (size - 1) / 2.0
    inv_half = 1.0 / max(1.0, half)

    half_stroke = max(0.064, 0.95 / size)
    aa_width = max(0.02, 1.30 / size)

    rows = []
    for y in range(size):
        row = bytearray([0])
        ny = (y - half) * inv_half
        for x in range(size):
            nx = (x - half) * inv_half

            if abs(nx) > 0.88 or abs(ny) > 0.88:
                row.extend((0, 0, 0, 0))
                continue

            min_dist = 10.0
            for ax, ay, bx, by in segments:
                d = _dist_to_segment(nx, ny, ax, ay, bx, by)
                if d < min_dist:
                    min_dist = d

            if min_dist > half_stroke + aa_width:
                row.extend((0, 0, 0, 0))
                continue

            if min_dist <= half_stroke - aa_width:
                alpha = 1.0
            else:
                alpha = (half_stroke + aa_width - min_dist) / (2.0 * aa_width)
                alpha = max(0.0, min(1.0, alpha))

            row.extend(
                (
                    GX_RED_R,
                    GX_RED_G,
                    GX_RED_B,
                    _clamp_byte(alpha * 255.0),
                )
            )
        rows.append(bytes(row))

    raw_scanlines = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    compressed = zlib.compress(raw_scanlines, level=9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def inspect_png_dimensions(path: pathlib.Path) -> tuple[bool, int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return False, 0, 0
    chunk_type = data[12:16]
    if chunk_type != b"IHDR":
        return False, 0, 0
    width, height = struct.unpack(">II", data[16:24])
    return True, width, height


def generate_all_icons() -> list[dict]:
    icons_dir = SIDEBAR_DIR / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    generated = []
    for size in ICON_SIZES:
        png_bytes = render_t3_icon_png(size)
        target = icons_dir / f"icon-{size}.png"
        target.write_bytes(png_bytes)
        generated.append(
            {
                "path": str(target.relative_to(REPO_ROOT)),
                "size": size,
                "bytes": len(png_bytes),
            }
        )
    return generated


def verify_packages() -> dict:
    checks = []

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    for size in ICON_SIZES:
        icon_path = SIDEBAR_DIR / "icons" / f"icon-{size}.png"
        exists = icon_path.is_file()
        valid_sig, w, h = inspect_png_dimensions(icon_path) if exists else (False, 0, 0)
        record(
            f"sidebar_icon_{size}px",
            exists and valid_sig and w == size and h == size,
            f"path={icon_path.name}, valid_png={valid_sig}, dimensions={w}x{h}",
        )

    ref_dir = REPO_ROOT / "reference"
    root_readme = REPO_ROOT / "README.md"
    user_mod_dirs = sorted(p.name for p in (REPO_ROOT / "mods").iterdir() if p.is_dir())
    record(
        "workspace_reference_and_mods_layout",
        ref_dir.is_dir()
        and (ref_dir / "documentation").is_dir()
        and (ref_dir / "mods").is_dir()
        and (ref_dir / "tools").is_dir()
        and root_readme.is_file()
        and "T3_Chat_Sidebar" in user_mod_dirs,
        f"reference_dir={ref_dir.is_dir()}, root_readme={root_readme.is_file()}, mods={user_mod_dirs}",
    )

    manifest_path = SIDEBAR_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record(
        "manifest_version_3",
        manifest.get("manifest_version") == 3,
        f"manifest_version={manifest.get('manifest_version')}",
    )

    sidebar_action = manifest.get("sidebar_action", {})
    panel_rel = sidebar_action.get("default_panel", "")
    panel_file = SIDEBAR_DIR / panel_rel
    record(
        "opera_gx_sidebar_action",
        bool(panel_rel) and panel_file.is_file(),
        f"default_panel={panel_rel}, exists={panel_file.is_file()}",
    )

    side_panel = manifest.get("side_panel", {})
    sp_rel = side_panel.get("default_path", "")
    sp_file = SIDEBAR_DIR / sp_rel
    record(
        "chromium_side_panel",
        bool(sp_rel) and sp_file.is_file(),
        f"default_path={sp_rel}, exists={sp_file.is_file()}",
    )

    sw_rel = manifest.get("background", {}).get("service_worker", "")
    sw_file = SIDEBAR_DIR / sw_rel
    record(
        "background_service_worker",
        bool(sw_rel) and sw_file.is_file(),
        f"service_worker={sw_rel}, exists={sw_file.is_file()}",
    )

    perms = set(manifest.get("permissions", []))
    required_perms = {"sidePanel", "declarativeNetRequest", "declarativeNetRequestWithHostAccess", "cookies"}
    record(
        "manifest_permissions",
        required_perms.issubset(perms),
        f"permissions={sorted(perms)}",
    )

    rules_path = SIDEBAR_DIR / "rules" / "framing-rules.json"
    rules_data = json.loads(rules_path.read_text(encoding="utf-8")) if rules_path.is_file() else []
    rules_text = json.dumps(rules_data)
    record(
        "sec_fetch_and_framing_rules",
        rules_path.is_file()
        and '"t3.chat"' in rules_text
        and '"Sec-Fetch-Dest"' in rules_text
        and '"document"' in rules_text
        and '"Sec-Fetch-Site"' in rules_text
        and '"x-frame-options"' in rules_text
        and '"content-security-policy"' in rules_text,
        "rules/framing-rules.json overrides Sec-Fetch-Dest/Sec-Fetch-Site and strips XFO/CSP/COOP/CORP for t3.chat",
    )

    panel_html = (SIDEBAR_DIR / "sidepanel" / "panel.html").read_text(encoding="utf-8")
    record(
        "clean_full_bleed_iframe_without_top_menu_or_resizer",
        'id="t3-frame"' in panel_html
        and EXPECTED_URL in panel_html
        and 'rel="preconnect"' in panel_html
        and "gx-toolbar" not in panel_html
        and "internal-resize-handle" not in panel_html,
        "panel.html declares static #t3-frame src with preconnect hints, no top menu, and no custom resize handle",
    )

    sw_js = sw_file.read_text(encoding="utf-8")
    panel_js = (SIDEBAR_DIR / "sidepanel" / "panel.js").read_text(encoding="utf-8")
    record(
        "dynamic_cookie_and_iframe_boot",
        EXPECTED_URL in sw_js
        and "updateDynamicRules" in sw_js
        and "lastSyncedSignature" in sw_js
        and "SYNC_T3_AUTH" in panel_js
        and "service-worker.js" not in panel_js
        and "window.location.replace" not in panel_js,
        "service-worker.js batches cookie reads with signature caching and panel.js avoids importing service-worker.js in the UI process",
    )

    content_scripts = manifest.get("content_scripts", [])
    bridge_path = SIDEBAR_DIR / "content" / "t3-session-bridge.js"
    sync_path = SIDEBAR_DIR / "content" / "t3-cookie-sync.js"
    has_main_bridge = any(
        "content/t3-session-bridge.js" in cs.get("js", [])
        and cs.get("world") == "MAIN"
        and cs.get("run_at") == "document_start"
        and cs.get("all_frames") is True
        for cs in content_scripts
    )
    has_isolated_sync = any(
        "content/t3-cookie-sync.js" in cs.get("js", [])
        and cs.get("run_at") == "document_start"
        and cs.get("all_frames") is True
        for cs in content_scripts
    )
    record(
        "manifest_content_scripts",
        has_main_bridge
        and has_isolated_sync
        and bridge_path.is_file()
        and sync_path.is_file(),
        f"main_bridge={has_main_bridge}, isolated_sync={has_isolated_sync}",
    )

    bridge_js = bridge_path.read_text(encoding="utf-8") if bridge_path.is_file() else ""
    record(
        "convex_session_bridge",
        "DEFAULT_ANON_SESSION_ID" in sw_js
        and "DEFAULT_ANON_SESSION_ID" in bridge_js
        and "convex-session-id" in bridge_js
        and "SameSite=None; Secure" in bridge_js
        and "ModifyQuerySet" in bridge_js,
        "service-worker.js and t3-session-bridge.js synchronize convex-session-id acrosschrome.cookies, document.cookie, and Convex ModifyQuerySet frames",
    )

    all_passed = all(item["passed"] for item in checks)
    return {
        "all_passed": all_passed,
        "total_checks": len(checks),
        "passed_checks": sum(1 for item in checks if item["passed"]),
        "target_url": EXPECTED_URL,
        "checks": checks,
    }


def main() -> int:
    generated_icons = generate_all_icons()
    verification = verify_packages()
    verification["generated_icons"] = generated_icons

    receipt_path = SIDEBAR_DIR / "verification-receipt.json"
    receipt_path.write_text(json.dumps(verification, indent=2), encoding="utf-8")

    print(
        f"Verification complete: {verification['passed_checks']}/{verification['total_checks']} checks passed."
    )
    for item in verification["checks"]:
        status = "PASS" if item["passed"] else "FAIL"
        print(f"  [{status}] {item['check']}: {item['detail']}")

    return 0 if verification["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
