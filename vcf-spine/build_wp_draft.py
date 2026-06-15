#!/usr/bin/env python3
"""Prepare the Supervisor/NSX-spine post for WordPress:
  1. Upload each local screenshot to the WP media library (cached so re-runs reuse).
  2. Emit a publish-ready markdown copy: YAML front matter + HTML comments stripped,
     local image paths rewritten to their uploaded media URLs.
Then run:  python scripts/publish.py <build file> --no-images --tags "..."
"""
import base64, json, os, re, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

SRC = Path("vcf-spine/zero-to-vcap-vcf91-workload-domain-MERGED.md")
BUILD = Path("vcf-spine/_build-wp-draft.md")
CACHE = Path("vcf-spine/.wp-media-map.json")
IMG_DIR = Path("vcf-spine")

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

raw = SRC.read_text(encoding="utf-8")
# strip YAML front matter
if raw.startswith("---"):
    raw = raw[raw.find("\n---", 3) + 4:]
# strip HTML comments
raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
imgs = list(dict.fromkeys(re.findall(r"images/[A-Za-z0-9._-]+\.jpg", raw)))
print(f"{len(imgs)} unique images referenced; {len(cache)} already uploaded.")

media_url = f"{WP}/wp-json/wp/v2/media"
for i, rel in enumerate(imgs, 1):
    if rel in cache:
        continue
    p = IMG_DIR / rel
    fn = p.name
    data = p.read_bytes()
    h = {**HEADERS,
         "Content-Disposition": f'attachment; filename="{fn}"',
         "Content-Type": "image/jpeg"}
    r = requests.post(media_url, headers=h, data=data, timeout=120)
    r.raise_for_status()
    j = r.json()
    cache[rel] = {"id": j["id"], "url": j["source_url"]}
    CACHE.write_text(json.dumps(cache, indent=2))
    print(f"  [{i}/{len(imgs)}] uploaded {fn} -> {j['source_url']}")

# rewrite image paths -> uploaded URLs
out = raw
for rel, info in cache.items():
    out = out.replace(f"]({rel})", f"]({info['url']})")
BUILD.write_text(out, encoding="utf-8")
print(f"\nWrote {BUILD} (front matter stripped, {len(imgs)} image URLs rewritten).")
print("Next: python scripts/publish.py", BUILD, '--no-images --tags "..."')
