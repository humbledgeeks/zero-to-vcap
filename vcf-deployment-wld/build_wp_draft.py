#!/usr/bin/env python3
"""Prepare the VCF 9.1 Workload Domain post for WordPress:
  1. Upload each local screenshot to the WP media library (cached so re-runs reuse).
  2. Emit a publish-ready markdown copy: HTML comments stripped, local image
     paths rewritten to their uploaded media URLs.
Then run:  python scripts/publish.py vcf-deployment-wld/_build-wp-draft.md --no-images --tags "..."

Modeled on vcf-spine/build_wp_draft.py.
"""
import base64, json, os, re, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

SRC = Path("blog-posts/zero-to-vcap-vcf91-workload-domain.md")
BUILD = Path("vcf-deployment-wld/_build-wp-draft.md")
CACHE = Path("vcf-deployment-wld/.wp-media-map.json")
REPO = Path(".")  # local image paths in the post are ../vcf-deployment-wld/*.jpg, relative to blog-posts/

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
# strip HTML comments (the URL TODO placeholders)
raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
# image refs look like: ../vcf-deployment-wld/vcf-wld-...jpg
imgs = list(dict.fromkeys(re.findall(r"\.\./vcf-deployment-wld/[A-Za-z0-9._-]+\.jpg", raw)))
print(f"{len(imgs)} unique images referenced; {len(cache)} already uploaded.")

media_url = f"{WP}/wp-json/wp/v2/media"
for i, rel in enumerate(imgs, 1):
    if rel in cache:
        continue
    # rel is ../vcf-deployment-wld/<name>.jpg ; the actual file lives at vcf-deployment-wld/<name>.jpg
    p = Path("vcf-deployment-wld") / Path(rel).name
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
print(f"\nWrote {BUILD} ({len(imgs)} image URLs rewritten).")
print("Next: python scripts/publish.py", BUILD, '--no-images --tags "..."')
