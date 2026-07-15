#!/usr/bin/env python3
"""Prepare the FlexPod VCF 9.1 Licensing post for WordPress:
  1. Rewrite the 4 SVG diagram refs to their PNG renders (WP blocks SVG uploads).
  2. Upload each local screenshot/diagram to the WP media library (cached so re-runs reuse).
  3. Emit a publish-ready markdown copy: YAML front matter + HTML comments stripped,
     an H1 injected from the front-matter title (publish.py uses the H1 as the WP title),
     local image paths rewritten to their uploaded media URLs.
Then run:  python scripts/publish.py vcf-license/_build-wp-draft.md --no-images --tags "..."

Modeled on vcf-spine/build_wp_draft.py.
"""
import base64, json, os, re, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

SRC = Path("vcf-license/zero-to-vcap-flexpod-vcf91-licensing.md")
BUILD = Path("vcf-license/_build-wp-draft.md")
CACHE = Path("vcf-license/.wp-media-map.json")
IMG_DIR = Path("vcf-license")  # refs look like images/<name>.jpg, relative to vcf-license/

load_dotenv()
WP = os.getenv("WORDPRESS_URL", "").rstrip("/")
USER = os.getenv("WORDPRESS_USERNAME", "")
APP = os.getenv("WORDPRESS_APP_PASSWORD", "")
if not (WP and USER and APP):
    sys.exit("[error] WORDPRESS_URL / USERNAME / APP_PASSWORD missing in .env")

HEADERS = {
    "Authorization": "Basic " + base64.b64encode(f"{USER}:{APP}".encode()).decode(),
    "User-Agent": "zero-to-vcap-publisher/1.0",
}
CTYPE = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}

raw = SRC.read_text(encoding="utf-8")

# pull the title out of the YAML front matter, then strip the front matter
title = None
if raw.startswith("---"):
    fm_end = raw.find("\n---", 3)
    fm = raw[3:fm_end]
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', fm, flags=re.MULTILINE)
    if m:
        title = m.group(1).strip()
    raw = raw[fm_end + 4:]
if not title:
    sys.exit("[error] could not read title from front matter")

# strip HTML comments (the TODO screenshot placeholders)
raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)

# WP rejects SVG uploads by default -> point the 4 diagrams at their PNG renders.
# Use a versioned suffix (-v2) so the URL is new: replacing a file at the same URL
# leaves Cloudflare serving the old cached copy for up to a year (max-age=31536000).
raw = re.sub(r"(images/[A-Za-z0-9._-]+)\.svg", r"\1-v2.png", raw)

# publish.py uses the markdown H1 as the WP title; inject it
body = f"# {title}\n\n{raw.lstrip()}"

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
imgs = list(dict.fromkeys(re.findall(r"images/[A-Za-z0-9._-]+\.(?:jpe?g|png)", body)))
print(f"{len(imgs)} unique images referenced; {len(cache)} already uploaded.")

media_url = f"{WP}/wp-json/wp/v2/media"
for i, rel in enumerate(imgs, 1):
    if rel in cache:
        continue
    p = IMG_DIR / rel
    fn = p.name
    ext = p.suffix.lower()
    data = p.read_bytes()
    h = {**HEADERS,
         "Content-Disposition": f'attachment; filename="{fn}"',
         "Content-Type": CTYPE.get(ext, "application/octet-stream")}
    r = requests.post(media_url, headers=h, data=data, timeout=120)
    r.raise_for_status()
    j = r.json()
    cache[rel] = {"id": j["id"], "url": j["source_url"]}
    CACHE.write_text(json.dumps(cache, indent=2))
    print(f"  [{i}/{len(imgs)}] uploaded {fn} -> {j['source_url']}")

# rewrite image paths -> uploaded URLs
out = body
for rel, info in cache.items():
    out = out.replace(f"]({rel})", f"]({info['url']})")
BUILD.write_text(out, encoding="utf-8")
print(f"\nWrote {BUILD} (front matter stripped, H1 injected, {len(imgs)} image URLs rewritten).")
print("Next: python scripts/publish.py", BUILD, '--no-images --tags "..."')
