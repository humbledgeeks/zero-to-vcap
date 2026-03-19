#!/usr/bin/env python3
"""
upload_screenshots_and_prep.py
Upload screenshots from infra-automation to WordPress media library and
produce a modified blog post with WordPress URLs replacing local paths.

Run from the zero-to-vcap repo root:
    python3 scripts/upload_screenshots_and_prep.py
"""

import base64
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config — paths relative to this script's location
# ---------------------------------------------------------------------------

REPO_ROOT       = Path(__file__).parent.parent          # zero-to-vcap/
INFRA_REPO      = REPO_ROOT.parent / "infra-automation"
SCREENSHOTS_DIR = INFRA_REPO / "Cisco/UCS/PowerShell/HumbledGeeks/screenshots"
BLOG_POST_SRC   = INFRA_REPO / "Cisco/UCS/PowerShell/HumbledGeeks/blog-post-draft.md"
BLOG_POST_OUT   = REPO_ROOT / "blog-posts/flexpod-vcf-ucs-foundation.md"

# ---------------------------------------------------------------------------
# Load credentials from .env
# ---------------------------------------------------------------------------

load_dotenv(REPO_ROOT / ".env")

WP_URL      = os.getenv("WORDPRESS_URL", "").rstrip("/")
WP_USER     = os.getenv("WORDPRESS_USERNAME", "")
WP_APP_PASS = os.getenv("WORDPRESS_APP_PASSWORD", "")

if not all([WP_URL, WP_USER, WP_APP_PASS]):
    print("[error] Missing WordPress credentials in .env")
    sys.exit(1)

token = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {token}",
    "User-Agent": "zero-to-vcap-publisher/1.0",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def upload_image(path: Path) -> str:
    """Upload a PNG to WP media library; return its source URL (or '' on error)."""
    url = f"{WP_URL}/wp-json/wp/v2/media"
    headers = {
        **HEADERS,
        "Content-Disposition": f'attachment; filename="{path.name}"',
        "Content-Type": "image/png",
    }
    with open(path, "rb") as f:
        data = f.read()
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=60)
    except requests.RequestException as e:
        print(f"  [FAIL] {path.name}: {e}")
        return ""
    if not resp.ok:
        print(f"  [FAIL] {path.name}: HTTP {resp.status_code} — {resp.text[:300]}")
        return ""
    media_url = resp.json().get("source_url", "")
    print(f"  [OK]   {path.name}")
    print(f"         → {media_url}")
    return media_url


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Validate paths
    if not SCREENSHOTS_DIR.exists():
        print(f"[error] Screenshots dir not found: {SCREENSHOTS_DIR}")
        sys.exit(1)
    if not BLOG_POST_SRC.exists():
        print(f"[error] Blog post not found: {BLOG_POST_SRC}")
        sys.exit(1)

    screenshots = sorted(SCREENSHOTS_DIR.glob("*.png"))
    print(f"\nFound {len(screenshots)} screenshots in:\n  {SCREENSHOTS_DIR}\n")
    print(f"Uploading to {WP_URL} ...\n")

    url_map = {}   # filename → wp URL
    for img in screenshots:
        wp_url = upload_image(img)
        if wp_url:
            url_map[img.name] = wp_url

    print(f"\n{'='*60}")
    print(f"Uploaded {len(url_map)} / {len(screenshots)} screenshots.")
    print(f"{'='*60}\n")

    if len(url_map) == 0:
        print("[error] No images uploaded — aborting.")
        sys.exit(1)

    # --- Rewrite blog post ---
    print(f"Reading source: {BLOG_POST_SRC}")
    content = BLOG_POST_SRC.read_text(encoding="utf-8")

    replacements = 0

    def replace_img(match):
        nonlocal replacements
        alt   = match.group(1)
        path  = match.group(2)
        fname = Path(path).name
        wp    = url_map.get(fname)
        if wp:
            replacements += 1
            return f"![{alt}]({wp})"
        print(f"  [warn] No WP URL for {fname} — keeping local path")
        return match.group(0)

    modified = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_img, content)

    BLOG_POST_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLOG_POST_OUT.write_text(modified, encoding="utf-8")

    print(f"Output written: {BLOG_POST_OUT}")
    print(f"  {replacements} image URLs replaced with WordPress media URLs.\n")
    print("Next step:")
    print(f"  cd {REPO_ROOT}")
    print(f"  python3 scripts/publish.py blog-posts/flexpod-vcf-ucs-foundation.md --tags 'Cisco UCS,NetApp,FlexPod,FC,Fibre Channel,NetApp ASA,PowerShell'")
    print()


if __name__ == "__main__":
    main()
