#!/usr/bin/env python3
"""Prepare the "VCF vs VVF" post for WordPress (image-heavy pattern).

This post already carries its own H1 and has NO YAML front matter, and its four
diagrams are already PNG (rendered from the source SVGs), so unlike the other
build scripts this one does NOT inject an H1 or rewrite .svg -> .png. It only:
  1. Uploads each local PNG in blog-posts/images/ to the WP media library
     (cached in .wp-media-vcf-vs-vvf-map.json so re-runs reuse the same media).
  2. Emits a publish-ready copy with the local image paths rewritten to their
     uploaded media URLs.

Then run (see blog-posts/PUBLISH-STEPS-vcf-vs-vvf.md):
  python scripts/publish.py blog-posts/_build-vcf-vs-vvf-draft.md --no-images --tags "..."
  python vcf-license/postprocess_wp.py <post_id> --cache blog-posts/.wp-media-vcf-vs-vvf-map.json --src /dev/null

Modeled on vcf-license/build_wp_draft.py.
"""
import base64, json, os, re, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

SRC = Path("blog-posts/zero-to-vcap-vcf-vs-vvf.md")
BUILD = Path("blog-posts/_build-vcf-vs-vvf-draft.md")
CACHE = Path("blog-posts/.wp-media-vcf-vs-vvf-map.json")
IMG_DIR = Path("blog-posts")  # refs look like images/<name>.png, relative to blog-posts/

load_dotenv("/Users/ajohnson/_github/zero-to-vcap/.env")
WP = os.getenv("WORDPRESS_URL", "").rstrip("/")
USER = os.getenv("WORDPRESS_USERNAME", "")
APP = os.getenv("WORDPRESS_APP_PASSWORD", "")
if not (WP and USER and APP):
    sys.exit("[error] WORDPRESS_URL / USERNAME / APP_PASSWORD missing in .env")

HEADERS = {
    "Authorization": "Basic " + base64.b64encode(f"{USER}:{APP}".encode()).decode(),
    "User-Agent": "zero-to-vcap-publisher/1.0",
}

raw = SRC.read_text(encoding="utf-8")

# Safety: strip any HTML comments (this post carries none, but keep the pattern).
raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)

# Source already begins with its H1 + has no front matter -> publish.py reads the
# H1 as the WP title. Leave the body exactly as-is aside from the image rewrite.
body = raw.lstrip()

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
imgs = list(dict.fromkeys(re.findall(r"images/[A-Za-z0-9._-]+\.png", body)))
print(f"{len(imgs)} unique images referenced; {len(cache)} already uploaded.")

media_url = f"{WP}/wp-json/wp/v2/media"
for i, rel in enumerate(imgs, 1):
    if rel in cache:
        continue
    p = IMG_DIR / rel
    data = p.read_bytes()
    h = {**HEADERS,
         "Content-Disposition": f'attachment; filename="{p.name}"',
         "Content-Type": "image/png"}
    r = requests.post(media_url, headers=h, data=data, timeout=120)
    r.raise_for_status()
    j = r.json()
    cache[rel] = {"id": j["id"], "url": j["source_url"]}
    CACHE.write_text(json.dumps(cache, indent=2))
    print(f"  [{i}/{len(imgs)}] uploaded {p.name} -> {j['source_url']}")

out = body
for rel, info in cache.items():
    out = out.replace(f"]({rel})", f"]({info['url']})")
BUILD.write_text(out, encoding="utf-8")
print(f"\nWrote {BUILD} ({len(imgs)} image URLs rewritten; H1 kept as WP title).")
print('Next: python scripts/publish.py', BUILD, '--no-images --tags "VVF,vSphere Foundation,Migration,vMotion,Workload Domain"')
