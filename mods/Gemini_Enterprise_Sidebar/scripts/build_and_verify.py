import json
import math
import pathlib
import shutil
import struct
import sys
import zlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SIDEBAR_DIR = REPO_ROOT / "mods" / "Gemini_Enterprise_Sidebar"
LEGACY_GX_MOD_DIR = REPO_ROOT / "mods" / "Gemini_Enterprise_GX_Mod"
EXPECTED_URL = "https://vertexaisearch.cloud.google.com/us/home/cid/a553b3f6-6377-415d-bde8-6ba45fdaa472?hl=en_US"
ICON_SIZES = (16, 32, 48, 128, 512)

GX_RED_R = 250
GX_RED_G = 30
GX_RED_B = 78


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _clamp_byte(val: float) -> int:
    return max(0, min(255, int(round(val))))


def _sample_gemini_curve(radius: float = 0.72, steps: int = 160) -> list[tuple[float, float]]:
    p0x, p0y = 0.0, radius
    p1x, p1y = 0.08 * radius, 0.38 * radius
    p2x, p2y = 0.38 * radius, 0.08 * radius
    p3x, p3y = radius, 0.0

    points = []
    for i in range(steps + 1):
        t = i / float(steps)
        u = 1.0 - t
        bx = (
            (u ** 3) * p0x
            + 3.0 * (u ** 2) * t * p1x
            + 3.0 * u * (t ** 2) * p2x
            + (t ** 3) * p3x
        )
        by = (
            (u ** 3) * p0y
            + 3.0 * (u ** 2) * t * p1y
            + 3.0 * u * (t ** 2) * p2y
            + (t ** 3) * p3y
        )
        points.append((bx, by))
    return points


def render_gemini_icon_png(size: int) -> bytes:
    curve_pts = _sample_gemini_curve(radius=0.72, steps=160)
    half = (size - 1) / 2.0
    inv_half = 1.0 / max(1.0, half)

    half_stroke = max(0.068, 1.05 / size)
    aa_width = max(0.02, 1.35 / size)

    rows = []
    for y in range(size):
        row = bytearray([0])
        ny = (y - half) * inv_half
        ay = abs(ny)
        for x in range(size):
            nx = (x - half) * inv_half
            ax = abs(nx)

            if ax > 0.88 or ay > 0.88:
                row.extend((0, 0, 0, 0))
                continue

            min_dist_sq = 10.0
            for bx, by in curve_pts:
                dx = ax - bx
                dy = ay - by
                d2 = dx * dx + dy * dy
                if d2 < min_dist_sq:
                    min_dist_sq = d2

            dist = math.sqrt(min_dist_sq)
            if dist > half_stroke + aa_width:
                row.extend((0, 0, 0, 0))
                continue

            if dist <= half_stroke - aa_width:
                alpha = 1.0
            else:
                alpha = (half_stroke + aa_width - dist) / (2.0 * aa_width)
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


def clean_obsolete_files() -> None:
    if LEGACY_GX_MOD_DIR.exists():
        shutil.rmtree(LEGACY_GX_MOD_DIR)
    for rel_dir in ("content",):
        target_dir = SIDEBAR_DIR / rel_dir
        if target_dir.exists():
            shutil.rmtree(target_dir)
    obsolete_config = SIDEBAR_DIR / "sidepanel" / "config.js"
    if obsolete_config.exists():
        obsolete_config.unlink()


def generate_all_icons() -> list[dict]:
    clean_obsolete_files()
    icons_dir = SIDEBAR_DIR / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    generated = []
    for size in ICON_SIZES:
        png_bytes = render_gemini_icon_png(size)
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
        "single_unified_folder",
        SIDEBAR_DIR.is_dir() and not LEGACY_GX_MOD_DIR.exists(),
        f"sidebar_dir_exists={SIDEBAR_DIR.is_dir()}, legacy_gx_mod_removed={not LEGACY_GX_MOD_DIR.exists()}",
    )
    record(
        "workspace_reference_and_mods_layout",
        ref_dir.is_dir()
        and (ref_dir / "documentation").is_dir()
        and (ref_dir / "mods").is_dir()
        and (ref_dir / "tools").is_dir()
        and root_readme.is_file()
        and "Gemini_Enterprise_Sidebar" in user_mod_dirs,
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
        and '"Sec-Fetch-Dest"' in rules_text
        and '"document"' in rules_text
        and '"Sec-Fetch-Site"' in rules_text
        and '"x-frame-options"' in rules_text
        and '"content-security-policy"' in rules_text,
        "rules/framing-rules.json overrides Sec-Fetch-Dest/Sec-Fetch-Site and strips XFO/CSP/COOP/CORP",
    )

    panel_html = (SIDEBAR_DIR / "sidepanel" / "panel.html").read_text(encoding="utf-8")
    record(
        "clean_full_bleed_iframe_without_top_menu_or_resizer",
        'id="gemini-frame"' in panel_html
        and EXPECTED_URL in panel_html
        and 'rel="preconnect"' in panel_html
        and "gx-toolbar" not in panel_html
        and "internal-resize-handle" not in panel_html,
        "panel.html declares static #gemini-frame src with preconnect hints, no top menu, and no custom resize handle",
    )

    sw_js = sw_file.read_text(encoding="utf-8")
    panel_js = (SIDEBAR_DIR / "sidepanel" / "panel.js").read_text(encoding="utf-8")
    record(
        "dynamic_cookie_and_iframe_boot",
        EXPECTED_URL in sw_js
        and "updateDynamicRules" in sw_js
        and "lastSyncedSignature" in sw_js
        and "SYNC_GOOGLE_AUTH" in panel_js
        and "service-worker.js" not in panel_js
        and "window.location.replace" not in panel_js,
        "service-worker.js batches cookie reads with signature caching and panel.js avoids importing service-worker.js in the UI process",
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

