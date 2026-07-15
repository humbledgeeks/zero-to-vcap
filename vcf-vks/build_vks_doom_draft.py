#!/usr/bin/env python3
"""Prepare the VKS/DOOM post for WordPress (image-heavy pattern).
  1. Upload each local screenshot in vks-images/ (the post-referenced vks-*.jpg) to
     the WP media library (cached so re-runs reuse).
  2. Emit a publish-ready markdown copy: YAML front matter + HTML comments stripped,
     an H1 injected from the front-matter title, local image paths rewritten to URLs.
Then:  python scripts/publish.py vcf-vks/_build-vks-doom-draft.md --no-images --tags "..."
       python vcf-vks/postprocess_wp.py <id> --cache vcf-vks/.wp-media-vks-map.json --src /dev/null
Modeled on vcf-license/build_ad_sso_draft.py.
"""
import base64, json, os, re, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

SRC = Path("vcf-vks/vcf-vks-kubernetes-doom.md")
BUILD = Path("vcf-vks/_build-vks-doom-draft.md")
CACHE = Path("vcf-vks/.wp-media-vks-map.json")
IMG_DIR = Path("vcf-vks")  # refs look like vks-images/<name>.jpg, relative to vcf-vks/

load_dotenv("/Users/ajohnson/_github/zero-to-vcap/.env")
WP = os.getenv("WORDPRESS_URL", "").rstrip("/")
USER = os.getenv("WORDPRESS_USERNAME", "")
APP = os.getenv("WORDPRESS_APP_PASSWORD", "")
if not (WP and USER and APP):
    sys.exit("[error] WORDPRESS_URL / USERNAME / APP_PASSWORD missing in .env")
HEADERS = {"Authorization": "Basic " + base64.b64encode(f"{USER}:{APP}".encode()).decode(),
           "User-Agent": "zero-to-vcap-publisher/1.0"}

raw = SRC.read_text(encoding="utf-8")
title = None
if raw.startswith("---"):
    fm_end = raw.find("\n---", 3)
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', raw[3:fm_end], flags=re.MULTILINE)
    if m:
        title = m.group(1).strip()
    raw = raw[fm_end + 4:]
if not title:
    sys.exit("[error] could not read title from front matter")

raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)   # strip both HTML comment blocks
body = f"# {title}\n\n{raw.lstrip()}"

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
imgs = list(dict.fromkeys(re.findall(r"vks-images/[A-Za-z0-9._-]+\.jpg", body)))
print(f"{len(imgs)} unique images referenced; {len(cache)} already uploaded.")

media_url = f"{WP}/wp-json/wp/v2/media"
for i, rel in enumerate(imgs, 1):
    if rel in cache:
        continue
    p = IMG_DIR / rel
    data = p.read_bytes()
    h = {**HEADERS, "Content-Disposition": f'attachment; filename="{p.name}"',
         "Content-Type": "image/jpeg"}
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
print(f"\nWrote {BUILD} (front matter + comments stripped, H1 injected, {len(imgs)} image URLs rewritten).")
