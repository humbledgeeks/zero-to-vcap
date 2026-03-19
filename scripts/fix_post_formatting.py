#!/usr/bin/env python3
"""
fix_post_formatting.py
Patches draft post 1794 to match the HumbledGeeks.com post format:
  1. Image blocks get real WP media IDs, clickable <a> links, wp-image-{id} classes
  2. H2 headings use plain <!-- wp:heading --> (no level attribute)
  3. H3 headings keep {"level":3}
"""

import base64
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
load_dotenv(REPO_ROOT / ".env")

WP_URL      = os.getenv("WORDPRESS_URL", "").rstrip("/")
WP_USER     = os.getenv("WORDPRESS_USERNAME", "")
WP_APP_PASS = os.getenv("WORDPRESS_APP_PASSWORD", "")
POST_ID     = 1794

token = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {token}",
    "Content-Type": "application/json",
    "User-Agent": "zero-to-vcap-publisher/1.0",
}
GET_HEADERS = {"Authorization": f"Basic {token}", "User-Agent": "zero-to-vcap-publisher/1.0"}

# ---------------------------------------------------------------------------
# Step 1 — Fetch all uploaded screenshot media IDs
# ---------------------------------------------------------------------------

def fetch_media_map():
    """Return dict of filename → {id, url} for all our uploaded screenshots."""
    media_map = {}
    page = 1
    while True:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/media",
            params={"per_page": 100, "page": page},
            headers=GET_HEADERS, timeout=15
        )
        if not r.ok:
            break
        batch = r.json()
        if not batch:
            break
        for m in batch:
            fname = m.get("source_url", "").split("/")[-1]
            if re.match(r"^(0[1-9]|1[0-9]|2[0-7])-", fname):
                media_map[fname] = {
                    "id":  m["id"],
                    "url": m["source_url"],
                }
        if len(batch) < 100:
            break
        page += 1
    return media_map


# ---------------------------------------------------------------------------
# Step 2 — Fetch current draft content
# ---------------------------------------------------------------------------

def fetch_draft():
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts/{POST_ID}?context=edit", headers=GET_HEADERS, timeout=15)
    r.raise_for_status()
    return r.json().get("content", {}).get("raw", "")


# ---------------------------------------------------------------------------
# Step 3 — Fix image blocks
# ---------------------------------------------------------------------------

def fix_image_blocks(content, media_map):
    """Replace placeholder wp:image blocks with fully attributed ones."""
    fixes = 0

    def replace_image(match):
        nonlocal fixes
        block = match.group(0)

        # Extract src from the block
        src_m = re.search(r'src="([^"]+)"', block)
        alt_m = re.search(r'alt="([^"]*)"', block)
        if not src_m:
            return block

        src = src_m.group(1)
        alt = alt_m.group(1) if alt_m else ""
        fname = src.split("/")[-1]

        media = media_map.get(fname)
        if not media:
            print(f"  [warn] No media ID found for {fname}")
            return block

        mid = media["id"]
        url = media["url"]

        fixes += 1
        return (
            f'<!-- wp:image {{"id":{mid},"sizeSlug":"large","linkDestination":"media"}} -->\n'
            f'<figure class="wp-block-image size-large">'
            f'<a href="{url}">'
            f'<img src="{url}" alt="{alt}" class="wp-image-{mid}"/>'
            f'</a></figure>\n'
            f'<!-- /wp:image -->'
        )

    content = re.sub(
        r'<!-- wp:image.*?<!-- /wp:image -->',
        replace_image,
        content,
        flags=re.DOTALL
    )
    print(f"  Fixed {fixes} image blocks")
    return content


# ---------------------------------------------------------------------------
# Step 4 — Fix heading levels
# ---------------------------------------------------------------------------

def fix_headings(content):
    """
    Existing posts use <!-- wp:heading --> for H2 (no level attr).
    H3 keeps {"level":3}.
    """
    before = content

    # H2: remove {"level":2} attribute
    content = content.replace(
        '<!-- wp:heading {"level":2} -->',
        '<!-- wp:heading -->'
    )
    content = content.replace(
        '<!-- /wp:heading {"level":2} -->',
        '<!-- /wp:heading -->'
    )

    h2_fixes = before.count('<!-- wp:heading {"level":2} -->')
    print(f"  Fixed {h2_fixes} H2 heading blocks")
    return content


# ---------------------------------------------------------------------------
# Step 5 — Patch WordPress
# ---------------------------------------------------------------------------

def patch_post(content):
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts/{POST_ID}",
        json={"content": content},
        headers=HEADERS,
        timeout=30
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"\nFetching media map from {WP_URL} ...")
    media_map = fetch_media_map()
    print(f"  Found {len(media_map)} screenshot media entries\n")

    print(f"Fetching draft post {POST_ID} ...")
    content = fetch_draft()
    print(f"  Content length: {len(content)} chars\n")

    print("Fixing image blocks ...")
    content = fix_image_blocks(content, media_map)

    print("\nFixing heading blocks ...")
    content = fix_headings(content)

    # Verify
    images   = len(re.findall(r'<!-- wp:image', content))
    with_id  = len(re.findall(r'wp:image \{"id":\d+', content))
    headings = len(re.findall(r'<!-- wp:heading -->', content))
    h2_wrong = len(re.findall(r'wp:heading \{"level":2\}', content))
    codes    = len(re.findall(r'<!-- wp:code', content))

    print(f"\nVerification:")
    print(f"  Image blocks    : {images}  (with media ID: {with_id})")
    print(f"  H2 headings     : {headings} plain  ({h2_wrong} still have level:2 — should be 0)")
    print(f"  Code blocks     : {codes}")

    print(f"\nPatching post {POST_ID} ...")
    data = patch_post(content)
    print(f"\n{'='*55}")
    print(f"  Done!")
    print(f"  Post ID : {data.get('id')}")
    print(f"  Preview : {data.get('link')}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
