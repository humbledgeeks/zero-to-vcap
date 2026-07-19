#!/usr/bin/env python3
"""Delete this post's uploaded media and clear the build cache, so build_wp_draft.py
re-uploads the current image files.

Needed after a redaction-policy change: the media library holds the OLD renderings and
WordPress has no REST endpoint for swapping an attachment's binary in place. Deleting
and re-uploading is the reliable path. Only touches attachment IDs recorded in this
post's own cache file, so it cannot disturb other posts' media.

Usage:  python VCF-9.1-Lifecycle-Upgrades/replace_media.py [--dry-run]
"""
import base64, json, os, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

CACHE = Path("VCF-9.1-Lifecycle-Upgrades/.wp-media-vcf91-lifecycle-map.json")
DRY = "--dry-run" in sys.argv

load_dotenv("/Users/ajohnson/_github/zero-to-vcap/.env")
WP = os.getenv("WORDPRESS_URL", "").rstrip("/")
USER = os.getenv("WORDPRESS_USERNAME", "")
APP = os.getenv("WORDPRESS_APP_PASSWORD", "")
if not (WP and USER and APP):
    sys.exit("[error] WORDPRESS_URL / USERNAME / APP_PASSWORD missing in .env")
H = {"Authorization": "Basic " + base64.b64encode(f"{USER}:{APP}".encode()).decode(),
     "User-Agent": "zero-to-vcap-publisher/1.0"}

if not CACHE.exists():
    sys.exit(f"[info] no cache at {CACHE} — nothing to delete; build will upload fresh.")

cache = json.loads(CACHE.read_text())
print(f"{len(cache)} attachments recorded in {CACHE.name}")
if DRY:
    for rel, info in cache.items():
        print(f"  would delete id={info['id']:6}  {rel}")
    sys.exit(0)

failed = []
for rel, info in cache.items():
    mid = info["id"]
    r = requests.delete(f"{WP}/wp-json/wp/v2/media/{mid}", headers=H,
                        params={"force": "true"}, timeout=60)
    if r.status_code == 200:
        print(f"  deleted id={mid:6}  {rel}")
    else:
        failed.append((mid, rel, r.status_code))
        print(f"  [warn] id={mid} {rel} -> HTTP {r.status_code}")

CACHE.unlink()
print(f"\nremoved {CACHE} — next build_wp_draft.py run uploads all images fresh.")
if failed:
    print(f"[warn] {len(failed)} deletions failed (orphaned media left in the library):")
    for mid, rel, code in failed:
        print(f"   id={mid} {rel} HTTP {code}")
