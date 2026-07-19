#!/usr/bin/env python3
"""Replace the two leaking images in the LIVE VKS/DOOM post (2256) with redacted copies.

vks-55 and vks-56 published the Kubedoom LoadBalancer address 10.103.50.9 in a VNC
dialog. redact_leftovers.py fixed the local files; this pushes the fix to the live post.

Deliberately surgical: it swaps two image URLs and their block ids inside the existing
post content and does NOT regenerate the post from markdown. A full republish of a live
post would rewrite every block and risk changing formatting readers already see.

New filenames are used on purpose. Re-uploading under the same name yields the same URL,
and the CDN keeps serving the cached (leaking) image — that exact trap already bit the
VCF 9.1 post this session.

Old attachments are deleted last, so the leaking URLs stop resolving.

Usage:  python vcf-vks/swap_leaked_media.py [--dry-run]
"""
import base64, json, os, re, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

POST_ID = 2256
IMG = Path("vcf-vks/vks-images")
CACHE = Path("vcf-vks/.wp-media-vks-map.json")
DRY = "--dry-run" in sys.argv

SWAPS = [  # (cache key, local file, new upload filename)
    ("vks-images/vks-55-tightvnc-connect.jpg", "vks-55-tightvnc-connect.jpg",
     "vks-55-tightvnc-connect-r2.jpg"),
    ("vks-images/vks-56-vnc-auth.jpg", "vks-56-vnc-auth.jpg",
     "vks-56-vnc-auth-r2.jpg"),
]

load_dotenv("/Users/ajohnson/_github/zero-to-vcap/.env")
WP = os.getenv("WORDPRESS_URL", "").rstrip("/")
USER, APP = os.getenv("WORDPRESS_USERNAME", ""), os.getenv("WORDPRESS_APP_PASSWORD", "")
if not (WP and USER and APP):
    sys.exit("[error] WORDPRESS_URL / USERNAME / APP_PASSWORD missing in .env")
H = {"Authorization": "Basic " + base64.b64encode(f"{USER}:{APP}".encode()).decode(),
     "User-Agent": "zero-to-vcap-publisher/1.0"}
POST = f"{WP}/wp-json/wp/v2/posts/{POST_ID}"

cache = json.loads(CACHE.read_text())
content = requests.get(POST, headers=H, params={"context": "edit"}, timeout=60).json()["content"]["raw"]
orig = content
retired = []

for key, local, newname in SWAPS:
    old = cache[key]
    old_id, old_url = old["id"], old["url"]
    if old_url not in content:
        print(f"[warn] {old_url} not found in post body; skipping")
        continue
    if DRY:
        print(f"would upload {local} as {newname}, then replace id={old_id} / {old_url}")
        continue
    data = (IMG / local).read_bytes()
    r = requests.post(f"{WP}/wp-json/wp/v2/media", headers={
        **H, "Content-Disposition": f'attachment; filename="{newname}"',
        "Content-Type": "image/jpeg"}, data=data, timeout=180)
    r.raise_for_status()
    j = r.json()
    new_id, new_url = j["id"], j["source_url"]
    content = content.replace(old_url, new_url)
    content = content.replace(f'"id":{old_id}', f'"id":{new_id}')
    content = content.replace(f"wp-image-{old_id}", f"wp-image-{new_id}")
    cache[key] = {"id": new_id, "url": new_url}
    retired.append((old_id, old_url))
    print(f"uploaded {newname} -> id={new_id}")
    print(f"   swapped {old_url}\n        -> {new_url}")

if DRY:
    sys.exit(0)

if content == orig:
    sys.exit("[error] post content unchanged — aborting without deleting anything")

r = requests.post(POST, headers={**H, "Content-Type": "application/json"},
                  json={"content": content}, timeout=60)
r.raise_for_status()
CACHE.write_text(json.dumps(cache, indent=2))
print(f"\npatched live post {POST_ID}")

for old_id, old_url in retired:   # only after the post no longer references them
    d = requests.delete(f"{WP}/wp-json/wp/v2/media/{old_id}", headers=H,
                        params={"force": "true"}, timeout=60)
    print(f"deleted old attachment {old_id}: HTTP {d.status_code}")
